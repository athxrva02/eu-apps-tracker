from copy import deepcopy
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models import Config

DEFAULTS = {
    "countries": ["NL", "DE", "GB", "CH", "FR", "BE"],
    "weights": {"scope": 25, "function": 25, "sector": 20, "capability": 20, "geography": 10},
    "high_threshold": 80,
    "review_threshold": 65,
    "timezone": "Europe/Berlin",
    "digest_hour": 8,
    "quiet_start": 22,
    "quiet_end": 8,
    "notifications_enabled": False,
    "recipient": "",
    "llm_enabled": False,
    "external_model_consent": False,
    "monthly_budget_usd": 10.0,
    "email_retention_days": 30,
    "log_retention_days": 30,
    "exclusions": ["intern", "internship", "graduate programme", "laboratory technician"],
    "role_aliases": [],
}


def get_settings(session) -> dict:
    row = session.get(Config, "settings")
    return deepcopy(DEFAULTS) | (row.value if row else {})


def save_settings(session, changes: dict) -> dict:
    unknown = set(changes) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown settings: {', '.join(sorted(unknown))}")
    value = get_settings(session) | changes
    try:
        ZoneInfo(value["timezone"])
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValueError("Invalid display timezone") from None
    weights = value["weights"]
    if not isinstance(weights, dict) or (
        set(weights) != set(DEFAULTS["weights"])
        or any(not isinstance(v, int) or v < 0 for v in weights.values())
        or sum(weights.values()) != 100
    ):
        raise ValueError("Scoring weights must be nonnegative integers totaling 100")
    if (
        any(type(value[key]) is not int for key in ("review_threshold", "high_threshold"))
        or not 0 <= value["review_threshold"] <= value["high_threshold"] <= 100
    ):
        raise ValueError("Thresholds must satisfy 0 ≤ review ≤ high ≤ 100")
    for key in ["digest_hour", "quiet_start", "quiet_end"]:
        if key == "digest_hour" and value[key] is None:
            raise ValueError("digest_hour must be an hour from 0 to 23")
        if value[key] is not None and (
            not isinstance(value[key], int) or not 0 <= value[key] <= 23
        ):
            raise ValueError(f"{key} must be an hour from 0 to 23")
    for key in ["email_retention_days", "log_retention_days"]:
        if not isinstance(value[key], int) or not 1 <= value[key] <= 3650:
            raise ValueError(f"{key} must be between 1 and 3650 days")
    if (
        not isinstance(value["monthly_budget_usd"], (int, float))
        or not 0 <= value["monthly_budget_usd"] <= 10000
    ):
        raise ValueError("Monthly model budget must be between 0 and 10000 USD")
    for key in ["notifications_enabled", "llm_enabled", "external_model_consent"]:
        if not isinstance(value[key], bool):
            raise ValueError(f"{key} must be a boolean")
    if not isinstance(value["countries"], list) or not all(
        isinstance(v, str) and len(v) == 2 and v.isupper() for v in value["countries"]
    ):
        raise ValueError("Countries must be a list of two-letter uppercase codes")
    for key in ["exclusions", "role_aliases"]:
        if not isinstance(value[key], list) or not all(
            isinstance(v, str) and v.strip() for v in value[key]
        ):
            raise ValueError(f"{key} must be a list of nonempty strings")
    import re

    recipient = value["recipient"]
    if not isinstance(recipient, str) or (
        recipient and not re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", recipient)
    ):
        raise ValueError("Enter one valid recipient address")
    if value["notifications_enabled"] and not recipient:
        raise ValueError("Configure a recipient before enabling notifications")
    if value["llm_enabled"] and not value["external_model_consent"]:
        raise ValueError("Consent is required to send selected evidence to the model provider")
    row = session.get(Config, "settings") or Config(key="settings")
    row.value = value
    session.add(row)
    return value
