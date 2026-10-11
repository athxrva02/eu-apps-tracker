import hashlib
import html
import http.client
import ipaddress
import json
import random
import re
import socket
import ssl
import time
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.timeutils import utcnow

MAX_RESPONSE = 5 * 1024 * 1024
BLOCKED_HOSTS = ("linkedin.com", "lnkd.in")


def plain_text(value: str) -> str:
    soup = BeautifulSoup(html.unescape(html.unescape(str(value))), "html.parser")
    for element in soup(["script", "style", "iframe", "object"]):
        element.decompose()
    return re.sub(r"[ \t]+", " ", soup.get_text(" ", strip=True)).strip()


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def redact_contacts(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", text)
    text = re.sub(r"(?:https?://)?(?:www\.)?linkedin\.com/\S+", "[profile link removed]", text)
    return re.sub(r"(?<!\w)(?:\+\d[\d ()-]{8,}\d)(?!\w)", "[phone removed]", text)


def validated_url(url: str, allow_linkedin: bool = False) -> tuple[str, int]:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").encode("idna").decode().lower().rstrip(".")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except (ValueError, UnicodeError):
        raise ValueError("Invalid URL") from None
    if parsed.scheme not in ("http", "https") or not host or parsed.username or parsed.password:
        raise ValueError("Only public HTTP(S) URLs without credentials are allowed")
    if port not in (80, 443) or any(c in url for c in ("\r", "\n", "\x00", "\\")):
        raise ValueError("Unsafe URL or port")
    if not allow_linkedin and any(host == h or host.endswith("." + h) for h in BLOCKED_HOSTS):
        raise ValueError("Automated LinkedIn requests are disabled; use email or manual imports")
    if host == "localhost" or host.endswith((".local", ".localhost", ".internal")):
        raise ValueError("Private hosts are not allowed")
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            raise ValueError("Private network destinations are not allowed")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
    return host, port


def resolve_public(host: str, port: int) -> str:
    answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = {answer[4][0] for answer in answers}
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("DNS resolved to a private or unsafe destination")
    return sorted(addresses)[0]


def canonical_url(url: str) -> str:
    validated_url(url, allow_linkedin=True)
    p = urlsplit(url)
    query = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
        and k.lower() not in {"trk", "trackingid", "fbclid", "gclid"}
    ]
    return urlunsplit(
        (
            p.scheme.lower(),
            p.netloc.lower(),
            p.path.rstrip("/") or "/",
            urlencode(sorted(query)),
            "",
        )
    )


class FetchError(ValueError):
    pass


class SafeHTTP:
    """Bounded GET client: resolve/validate every hop, then pin the socket to that IP.

    TLS still verifies the original hostname. No environment proxies, cookies,
    automatic redirects, LinkedIn requests or unvalidated secondary resolution.
    """

    def __init__(self, allowed_hosts: set[str], host_lease=None, sleeper=time.sleep):
        self.allowed_hosts = {host.lower().rstrip(".") for host in allowed_hosts}
        self.host_lease = host_lease
        self.sleep = sleeper
        self.requests = 0
        self.cache: dict[str, tuple[dict, bytes]] = {}

    def get(self, url: str) -> bytes:
        for _ in range(6):
            host, port = validated_url(url)
            if host not in self.allowed_hosts:
                raise FetchError("Redirect or URL host is not in the source allowlist")
            response_headers, body, status = self._retry(url, host, port)
            if status in (301, 302, 303, 307, 308):
                target = response_headers.get("location")
                if not target:
                    raise FetchError("Redirect has no location")
                url = urljoin(url, target)
                continue
            if status == 304:
                if url not in self.cache:
                    raise FetchError("304 response without cached content")
                return self.cache[url][1]
            if status != 200:
                label = (
                    "blocked access"
                    if status in (401, 403)
                    else "bad identifier/URL"
                    if status == 404
                    else "HTTP error"
                )
                raise FetchError(f"{label} ({status})")
            self.cache[url] = (response_headers, body)
            return body
        raise FetchError("Too many redirects")

    def _retry(self, url: str, host: str, port: int):
        for attempt in range(4):
            lease = self.host_lease(host) if self.host_lease else None
            entered = False
            try:
                if lease:
                    lease.__enter__()
                    entered = True
                result = self._request(url, host, port)
                if result[2] not in (429, 500, 502, 503, 504):
                    return result
                if attempt == 3:
                    return result
                delay = self.retry_delay(result[0].get("retry-after"), attempt)
            except (OSError, http.client.HTTPException) as exc:
                if attempt == 3:
                    raise FetchError("Network request failed after bounded retries") from exc
                delay = 2**attempt + random.random()
            finally:
                if entered:
                    lease.__exit__(None, None, None)
            self.sleep(delay)
        raise FetchError("Request failed")

    @staticmethod
    def retry_delay(raw: str | None, attempt: int) -> float:
        if raw:
            try:
                delay = float(raw)
            except ValueError:
                try:
                    delay = (parsedate_to_datetime(raw) - utcnow()).total_seconds()
                except (TypeError, ValueError):
                    delay = 2**attempt
            # Long Retry-After is deferred to the next scan instead of shortened.
            if delay > 60:
                raise FetchError(f"Rate limited; retry after {int(delay)} seconds on a later scan")
            return max(0, delay)
        return 2**attempt + random.random()

    def _request(self, url: str, host: str, port: int):
        ip = resolve_public(host, port)
        parsed = urlsplit(url)
        connection = http.client.HTTPConnection(host, port, timeout=20)
        sock = socket.create_connection((ip, port), timeout=20)
        if parsed.scheme == "https":
            try:
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            except Exception:
                sock.close()
                raise
        connection.sock = sock
        headers = {
            "User-Agent": "EuropeanJobAgent/0.1 (configured public career sources)",
            "Accept-Encoding": "identity",
        }
        if url in self.cache:
            cached = self.cache[url][0]
            if cached.get("etag"):
                headers["If-None-Match"] = cached["etag"]
            if cached.get("last-modified"):
                headers["If-Modified-Since"] = cached["last-modified"]
        self.requests += 1
        try:
            connection.request(
                "GET", urlunsplit(("", "", parsed.path or "/", parsed.query, "")), headers=headers
            )
            response = connection.getresponse()
            content = response.read(MAX_RESPONSE + 1)
            if len(content) > MAX_RESPONSE:
                raise FetchError("Response exceeds 5 MB limit")
            return {k.lower(): v for k, v in response.getheaders()}, content, response.status
        finally:
            connection.close()

    def json(self, url: str):
        try:
            return json.loads(self.get(url))
        except (ValueError, UnicodeError) as exc:
            raise FetchError("Malformed JSON response") from exc
