import re

from app.security import digest

SCORING_VERSION = "deterministic-1"
PATTERNS = {
    "scope": [
        r"strateg",
        r"portfolio",
        r"(?:lead|led|manag)\w* (?:a |global |matrix |cross-functional )*team",
        r"budget|investment",
        r"roadmap",
        r"stakeholder|executive",
    ],
    "function": [
        r"r&d|research.{0,5}development",
        r"formulat",
        r"product.{0,15}develop",
        r"innovat",
        r"technolog",
        r"digital.{0,5}r&d",
    ],
    "sector": [
        r"home.?care|household|cleaning",
        r"consumer|fmcg",
        r"chemic",
        r"coating|material",
        r"ingredient|fragrance",
    ],
    "capability": [
        r"scale.up|commercial",
        r"patent|\bip\b",
        r"regulator|safety",
        r"digital|predictive|data.driven",
        r"partner|supplier",
        r"phd|chemical engineering",
    ],
}


def snippet(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.I)
    if not match:
        return ""
    return text[max(0, match.start() - 60) : min(len(text), match.end() + 120)].strip()


def deterministic(job: dict, profile: dict, config: dict) -> dict:
    text = job["title"] + ". " + job.get("description", "")
    title = job["title"].lower()
    evidence = profile.get("evidence", [])
    hard = []
    if re.search(r"\b(junior|intern|internship|graduate|technician|entry.level)\b", title):
        hard.append("Explicit junior or excluded role scope")
    if re.search(r"software|backend|frontend|full.stack|devops", title) and not re.search(
        r"r&d|research|formulation|scientific", title
    ):
        hard.append("Unrelated software engineering function")
    for exclusion in config["exclusions"]:
        if re.search(r"\b" + re.escape(exclusion.lower()) + r"\b", title):
            hard.append(f"Excluded title term: {exclusion}")
    countries = set(job.get("countries", []))
    if countries and config["countries"] and not countries.intersection(config["countries"]):
        hard.append("Confirmed location outside configured countries")
    dimensions, reasons = {}, []
    for dimension, patterns in PATTERNS.items():
        hits = []
        for pattern in patterns:
            excerpt = snippet(text, pattern)
            profile_item = next((e for e in evidence if re.search(pattern, e["text"], re.I)), None)
            if excerpt and profile_item:
                hits.append(
                    {
                        "dimension": dimension,
                        "job_excerpt": excerpt,
                        "profile_evidence_id": profile_item["id"],
                        "profile_excerpt": profile_item["text"],
                        "reason": f"Shared evidence for {dimension}: {re.search(pattern, text, re.I).group()}",
                    }
                )
        # Distinct concepts count once. Repeated keywords cannot increase the score.
        ratio = min(
            1, len(hits) / {"scope": 3, "function": 3, "sector": 2, "capability": 3}[dimension]
        )
        if dimension == "scope" and not re.search(
            r"director|head of|\bvp\b|vice president|global.{0,20}lead|regional.{0,20}lead|directeur|leiter",
            title,
            re.I,
        ):
            ratio = min(ratio, 0.7)
        dimensions[dimension] = round(config["weights"][dimension] * ratio)
        reasons.extend(hits[:3])
    dimensions["geography"] = (
        config["weights"]["geography"] if countries.intersection(config["countries"]) else 0
    )
    unknowns = []
    if not countries:
        unknowns.append("Work location is unknown")
    if job.get("work_mode") == "remote":
        unknowns.append("Confirm that remote work from the preferred country is permitted")
    unknowns.append("Work authorization and sponsorship are unverified")
    language_requirement = re.search(
        r"(?:fluent|proficien\w*|native|mandatory|required).{0,30}(?:german|french|dutch|english)|(?:german|french|dutch|english).{0,30}(?:required|mandatory|fluent)",
        text,
        re.I,
    )
    if language_requirement:
        unknowns.append("Review stated language requirement: " + language_requirement.group())
    else:
        unknowns.append("Required languages are not specified")
    gaps = [
        f"Limited shared evidence for {key}"
        for key in PATTERNS
        if dimensions[key] < config["weights"][key] / 2
    ]
    coverage = len(job.get("description", "")) >= 240 and not job.get("provisional", False)
    score = 0 if hard else sum(dimensions.values())
    return {
        "score": score,
        "dimensions": dimensions,
        "reasons": reasons,
        "gaps": gaps,
        "unknowns": unknowns,
        "hard_filters": sorted(set(hard)),
        "provisional": not coverage,
        "evidence_coverage": "sufficient" if coverage else "limited evidence",
        "method": "deterministic",
        "version": SCORING_VERSION,
        "recommendation": "excluded"
        if hard
        else "high match"
        if score >= config["high_threshold"] and coverage
        else "review"
        if score >= config["review_threshold"]
        else "low match",
        "limitations": "Heuristic ranking based on shared concepts; review the original job requirements.",
    }


def cache_key(job: dict, profile_id: int, config: dict) -> str:
    from app.config import settings

    return digest(
        {
            "job": job,
            "profile": profile_id,
            "scoring": SCORING_VERSION,
            "config": {
                k: config[k]
                for k in [
                    "weights",
                    "countries",
                    "exclusions",
                    "high_threshold",
                    "review_threshold",
                    "llm_enabled",
                    "external_model_consent",
                ]
            },
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "prompt": "evidence-1",
        }
    )
