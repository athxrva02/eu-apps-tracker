import re
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(UTC)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def iso(value: datetime | None) -> str | None:
    return aware(value).isoformat() if value else None


def timestamp(raw: str | None, timezone: str = "UTC", provenance: str = "source") -> dict:
    result = {
        "raw": raw,
        "precision": "unknown",
        "timezone": timezone,
        "provenance": provenance,
        "start": None,
        "end": None,
    }
    if not raw:
        return result
    try:
        value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo(timezone))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(raw)):
            result.update(precision="date", start=iso(value), end=iso(value + timedelta(days=1)))
        else:
            result.update(precision="instant", start=iso(value), end=iso(value))
    except (ValueError, TypeError):
        pass
    return result


def recently_published(evidence: dict, hours: int, now: datetime) -> bool:
    if not evidence.get("start") or not evidence.get("end"):
        return False
    lower = datetime.fromisoformat(evidence["start"])
    upper = datetime.fromisoformat(evidence["end"])
    return now - timedelta(hours=hours) <= lower <= upper <= now


def quiet_until(now: datetime, timezone: str, start: int | None, end: int | None) -> datetime:
    if start is None or end is None or start == end:
        return now
    local = now.astimezone(ZoneInfo(timezone))
    hour = local.hour
    quiet = start <= hour < end if start < end else hour >= start or hour < end
    if not quiet:
        return now
    day = local.date() + timedelta(days=int(start > end and hour >= start))
    return datetime.combine(day, time(end), tzinfo=ZoneInfo(timezone)).astimezone(UTC)
