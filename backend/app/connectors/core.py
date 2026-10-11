import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator
from soupsieve import compile as compile_selector
from soupsieve.util import SelectorSyntaxError

from app.security import FetchError, SafeHTTP, canonical_url, plain_text, validated_url
from app.timeutils import timestamp


class NormalizedJob(BaseModel):
    external_id: str = Field(min_length=1, max_length=300)
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    url: str
    description: str = Field(default="", max_length=250000)
    locations: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    work_mode: str = "unknown"
    employment_type: str = "unknown"
    language: str = "unknown"
    requisition_id: str | None = None
    publication: dict = Field(default_factory=lambda: timestamp(None))
    updated: dict = Field(default_factory=lambda: timestamp(None))
    received: dict = Field(default_factory=lambda: timestamp(None))
    provisional: bool = False
    closed: bool = False
    demo: bool = False

    @field_validator("url")
    @classmethod
    def safe_link(cls, value):
        return canonical_url(value)

    @field_validator("title", "company", "description")
    @classmethod
    def clean(cls, value):
        return plain_text(value)


@dataclass
class ConnectorResult:
    jobs: list[NormalizedJob]
    complete: bool = True
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


COUNTRIES = {
    "netherlands": "NL",
    "nederland": "NL",
    "amsterdam": "NL",
    "rotterdam": "NL",
    "wageningen": "NL",
    "germany": "DE",
    "deutschland": "DE",
    "hamburg": "DE",
    "düsseldorf": "DE",
    "berlin": "DE",
    "united kingdom": "GB",
    " uk": "GB",
    "london": "GB",
    "hull": "GB",
    "england": "GB",
    "switzerland": "CH",
    "schweiz": "CH",
    "geneva": "CH",
    "basel": "CH",
    "zurich": "CH",
    "france": "FR",
    "paris": "FR",
    "belgium": "BE",
    "brussels": "BE",
    "belgique": "BE",
    "denmark": "DK",
    "sweden": "SE",
    "spain": "ES",
    "italy": "IT",
    "ireland": "IE",
    "poland": "PL",
    "united states": "US",
    "singapore": "SG",
    "dubai": "AE",
    "india": "IN",
    "china": "CN",
}


def infer_countries(locations: list[str]) -> list[str]:
    codes = set()
    for location in locations:
        for token, code in COUNTRIES.items():
            if token in location.lower():
                codes.add(code)
        for code in set(COUNTRIES.values()):
            if re.search(rf"(?:^|[,\s]){code}$", location):
                codes.add(code)
    return sorted(codes)


def board_token(config: dict) -> str:
    token = config.get("board", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", token):
        raise FetchError("A valid board identifier is required")
    return token


def greenhouse(source, client) -> ConnectorResult:
    board = board_token(source.config)
    data = client.json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise FetchError("Malformed Greenhouse job list")
    jobs = []
    for row in data["jobs"]:
        try:
            locations = [row["location"]["name"]]
            jobs.append(
                NormalizedJob(
                    external_id=str(row["id"]),
                    company=source.company,
                    title=row["title"],
                    url=row["absolute_url"],
                    description=row.get("content", ""),
                    locations=locations,
                    countries=infer_countries(locations),
                    requisition_id=row.get("requisition_id") or None,
                    publication=timestamp(
                        row.get("first_published"), provenance="Greenhouse first_published"
                    ),
                    updated=timestamp(row.get("updated_at"), provenance="Greenhouse updated_at"),
                    language=row.get("language", "unknown"),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise FetchError("Malformed Greenhouse job; scan is not complete") from exc
    total = data.get("meta", {}).get("total")
    complete = total is None or total == len(jobs)
    return ConnectorResult(
        jobs, complete, [] if complete else ["Reported total differs from returned jobs"]
    )


def lever(source, client) -> ConnectorResult:
    board = board_token(source.config)
    host = "api.eu.lever.co" if source.config.get("region") == "eu" else "api.lever.co"
    limit = min(100, max(1, int(source.config.get("page_size", 100))))
    jobs, seen = [], set()
    max_pages = min(100, max(1, int(source.config.get("max_pages", 50))))
    for page in range(max_pages):
        data = client.json(
            f"https://{host}/v0/postings/{board}?"
            + urlencode({"mode": "json", "skip": page * limit, "limit": limit})
        )
        if not isinstance(data, list):
            raise FetchError("Malformed Lever job list")
        for row in data:
            try:
                identity = str(row["id"])
                if identity in seen:
                    raise FetchError("Lever pagination repeated a job; incomplete extraction")
                seen.add(identity)
                category = row.get("categories", {})
                locations = category.get("allLocations") or [category.get("location", "Unknown")]
                description = row.get("descriptionPlain") or row.get("description", "")
                for section in row.get("lists", []):
                    description += " " + section.get("text", "") + " " + section.get("content", "")
                description += " " + row.get("additionalPlain", row.get("additional", ""))
                jobs.append(
                    NormalizedJob(
                        external_id=identity,
                        company=source.company,
                        title=row["text"],
                        url=row.get("applyUrl") or row["hostedUrl"],
                        description=description,
                        locations=locations,
                        countries=infer_countries(locations),
                        employment_type=category.get("commitment", "unknown"),
                        work_mode=row.get("workplaceType", "unknown"),
                        # Public Postings API documents no reliable publication timestamp.
                        publication=timestamp(None, provenance="Lever publication unavailable"),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise FetchError("Malformed Lever job; scan is not complete") from exc
        if len(data) < limit:
            return ConnectorResult(jobs)
    return ConnectorResult(jobs, False, ["Pagination cap reached"])


def jsonld_nodes(value):
    if isinstance(value, list):
        for node in value:
            yield from jsonld_nodes(node)
    elif isinstance(value, dict):
        if "JobPosting" in (
            [value.get("@type")] if isinstance(value.get("@type"), str) else value.get("@type", [])
        ):
            yield value
        if "@graph" in value:
            yield from jsonld_nodes(value["@graph"])


def jsonld_job(row: dict, source, page_url: str) -> NormalizedJob:
    locations, countries = [], []
    raw_locations = row.get("jobLocation", [])
    if isinstance(raw_locations, dict):
        raw_locations = [raw_locations]
    for place in raw_locations:
        address = place.get("address", {})
        if isinstance(address, str):
            locations.append(address)
            continue
        country = address.get("addressCountry", "")
        if isinstance(country, dict):
            country = country.get("name", "")
        locations.append(
            ", ".join(
                str(v)
                for v in [address.get("addressLocality"), address.get("addressRegion"), country]
                if v
            )
        )
        if len(country) == 2:
            countries.append(country.upper())
    identifier = row.get("identifier", {})
    identity = identifier.get("value") if isinstance(identifier, dict) else identifier
    link = urljoin(page_url, row.get("url", page_url))
    return NormalizedJob(
        external_id=str(identity or link),
        requisition_id=str(identity) if identity else None,
        company=source.company,
        title=row["title"],
        url=link,
        description=row.get("description", ""),
        locations=locations,
        countries=countries or infer_countries(locations),
        employment_type=str(row.get("employmentType", "unknown")),
        work_mode="remote" if row.get("jobLocationType") == "TELECOMMUTE" else "unknown",
        publication=timestamp(
            row.get("datePosted"), source.config.get("timezone", "UTC"), "JSON-LD datePosted"
        ),
    )


def html_source(source, client) -> ConnectorResult:
    config = source.config
    try:
        for key, value in config.items():
            if key.endswith("_selector") and value:
                compile_selector(value)
    except (SelectorSyntaxError, TypeError) as exc:
        raise FetchError("Invalid CSS selector configuration") from exc
    if not config.get("single_page") and not config.get("next_selector"):
        raise FetchError("HTML source must declare single_page or a next-page selector")
    url = source.url
    jobs, seen_pages = [], set()
    max_pages = min(100, max(1, int(config.get("max_pages", 30))))
    for _ in range(max_pages):
        if url in seen_pages:
            raise FetchError("Pagination loop detected")
        seen_pages.add(url)
        soup = BeautifulSoup(client.get(url), "html.parser")
        current = []
        try:
            for script in soup.select('script[type="application/ld+json"]'):
                for row in jsonld_nodes(json.loads(script.get_text())):
                    current.append(jsonld_job(row, source, url))
            if not current and config.get("item_selector"):
                for item in soup.select(config["item_selector"]):
                    title = item.select_one(config["title_selector"])
                    link = item.select_one(config["link_selector"])
                    if title is None or link is None or not link.get("href"):
                        raise FetchError("Configured title/link selector no longer matches")
                    description = item.select_one(
                        config.get("description_selector") or ".description"
                    )
                    location = item.select_one(config.get("location_selector") or ".location")
                    publication = item.select_one(config.get("date_selector") or "time")
                    locations = [location.get_text(" ", strip=True)] if location else []
                    link_url = urljoin(url, link["href"])
                    current.append(
                        NormalizedJob(
                            external_id=item.get("data-id") or link_url,
                            company=source.company,
                            title=title.get_text(" ", strip=True),
                            url=link_url,
                            description=description.get_text(" ", strip=True)
                            if description
                            else "",
                            locations=locations,
                            countries=infer_countries(locations),
                            provisional=description is None,
                            publication=timestamp(
                                publication.get("datetime") or publication.get_text()
                                if publication
                                else None,
                                config.get("timezone", "UTC"),
                                "configured HTML date",
                            ),
                        )
                    )
        except (KeyError, TypeError, ValueError, SelectorSyntaxError) as exc:
            raise FetchError(
                "HTML/JSON-LD extraction failed; scan is not a valid empty board"
            ) from exc
        if not current and not (
            config.get("empty_selector") and soup.select_one(config["empty_selector"])
        ):
            raise FetchError("No jobs or explicit empty marker matched; parser failure")
        jobs.extend(current)
        next_link = (
            soup.select_one(config["next_selector"]) if config.get("next_selector") else None
        )
        if not next_link:
            return ConnectorResult(jobs)
        if not next_link.get("href"):
            raise FetchError("Next page link has no URL")
        url = urljoin(url, next_link["href"])
    return ConnectorResult(jobs, False, ["HTML pagination cap reached"])


def fetch_source(source, client=None, host_lease=None) -> ConnectorResult:
    if source.kind == "demo":
        from app.demo import demo_jobs

        return ConnectorResult(demo_jobs(source.config.get("stage", 0)), stats={"demo": True})
    if source.kind not in {"greenhouse", "lever", "html"}:
        raise FetchError("Unsupported automated source; use a supported connector or manual import")
    if not source.config.get("access_reviewed"):
        raise FetchError("Record robots and terms/access review before fetching")
    if source.kind == "greenhouse":
        hosts = {"boards-api.greenhouse.io"}
    elif source.kind == "lever":
        hosts = {"api.eu.lever.co" if source.config.get("region") == "eu" else "api.lever.co"}
    else:
        host, _ = validated_url(source.url)
        hosts = {host} | set(source.config.get("allowed_hosts", []))
    client = client or SafeHTTP(hosts, host_lease)
    result = {"greenhouse": greenhouse, "lever": lever, "html": html_source}[source.kind](
        source, client
    )
    result.stats |= {"requests": getattr(client, "requests", 0), "pages_complete": result.complete}
    return result
