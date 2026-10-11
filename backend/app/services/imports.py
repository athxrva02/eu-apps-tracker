import hashlib
import re
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
from sqlalchemy import select

from app.connectors import NormalizedJob
from app.models import ImportedMessage, Source
from app.security import canonical_url
from app.timeutils import iso, timestamp, utcnow


def parse_email(content: bytes) -> tuple[dict, list[NormalizedJob]]:
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Email exceeds 10 MB")
    message = BytesParser(policy=policy.default).parsebytes(content)
    if not message.get("From"):
        raise ValueError("Invalid email: sender header is missing")
    try:
        received = parsedate_to_datetime(message.get("Date", ""))
        if received.tzinfo is None:
            received = utcnow()
    except (ValueError, TypeError):
        received = utcnow()
    # A Date header is sender time, not verified mailbox receipt. Keep both distinct.
    identity = str(message.get("Message-ID") or "").strip()
    metadata = {
        "identity": hashlib.sha256(identity.encode() if identity else content).hexdigest(),
        "sender": str(message.get("From")),
        "received_at": utcnow(),
        "sender_date": iso(received),
        "receipt_basis": "local import time",
        "jobs": 0,
    }
    jobs, seen = [], set()
    for part in message.walk():
        if (
            part.get_content_type() not in {"text/html", "text/plain"}
            or part.get_content_disposition() == "attachment"
        ):
            continue
        text = part.get_content()
        if not isinstance(text, str):
            continue
        if part.get_content_type() == "text/html":
            soup = BeautifulSoup(text, "html.parser")
            links = [
                (a.get("href", ""), a.get_text(" ", strip=True), a.get("data-company"))
                for a in soup.select("a[href]")
            ]
        else:
            links = [(u, "Imported vacancy", None) for u in re.findall(r"https?://[^\s<>]+", text)]
        for url, title, company in links:
            # Only actual job links from the provided message; never follow tracking redirects.
            if not re.search(
                r"(?:linkedin\.com/(?:comm/)?jobs/view/|/jobs?/|/careers?/|[?&](?:gh_jid|jobId|job_id)=)",
                url,
                re.I,
            ):
                continue
            try:
                url = canonical_url(url)
            except ValueError:
                continue
            if url in seen or not title:
                continue
            seen.add(url)
            jobs.append(
                NormalizedJob(
                    external_id=hashlib.sha256(url.encode()).hexdigest(),
                    company=company or "Employer unspecified in imported alert",
                    title=title[:500],
                    url=url,
                    provisional=True,
                    received=timestamp(
                        iso(metadata["received_at"]), provenance="local email import time"
                    ),
                )
            )
    metadata["jobs"] = len(jobs)
    if not jobs:
        raise ValueError(
            "No supported job links found in this message; use structured manual import"
        )
    return metadata, jobs


def import_source(session, kind: str) -> Source:
    name = "Imported alert emails" if kind == "email" else "Manual structured imports"
    source = session.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(
            name=name,
            company="Multiple employers",
            kind=kind,
            enabled=False,
            capability={
                "supported": True,
                "scheduled": False,
                "publication": "input evidence only",
            },
        )
        session.add(source)
        session.flush()
    return source


def register_email(session, metadata: dict) -> bool:
    if session.scalar(
        select(ImportedMessage.id).where(ImportedMessage.identity == metadata["identity"])
    ):
        return False
    session.add(
        ImportedMessage(
            identity=metadata["identity"],
            sender=metadata["sender"],
            received_at=metadata["received_at"],
            data={
                "sender_date": metadata["sender_date"],
                "receipt_basis": metadata["receipt_basis"],
                "jobs": metadata["jobs"],
            },
        )
    )
    return True
