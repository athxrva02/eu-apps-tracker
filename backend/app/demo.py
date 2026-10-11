import argparse
import json
from datetime import timedelta

from sqlalchemy import select

from app.config import REPO, settings
from app.connectors import NormalizedJob
from app.db import Session
from app.models import ProfileVersion, Source
from app.services.jobs import approved_profile
from app.services.scans import run_scan
from app.services.settings import save_settings
from app.timeutils import iso, timestamp, utcnow


def fixture(name):
    return json.loads((REPO / "fixtures" / name).read_text())


def demo_jobs(stage=0):
    records = fixture("vacancies.json")
    if stage:
        records.append(fixture("new-vacancy.json"))
    jobs = []
    for index, record in enumerate(records):
        raw = dict(record)
        raw.pop("label", None)
        age = raw.pop("publication_age_hours")
        raw["publication"] = timestamp(
            iso(utcnow() - timedelta(hours=age)), provenance="synthetic fixture time"
        )
        if index % 4 == 1:
            raw["publication"] = timestamp(None, provenance="synthetic missing publication")
        elif index % 5 == 2:
            raw["publication"] = timestamp(
                str(utcnow().date()), "Europe/Berlin", "synthetic date-only fixture"
            )
        jobs.append(NormalizedJob.model_validate(raw))
    return jobs


def seed():
    if not settings.demo_mode:
        raise ValueError(
            "Demo seeding requires DEMO_MODE=true; use a separate database for live data"
        )
    with Session.begin() as session:
        if not approved_profile(session):
            session.add(ProfileVersion(data=fixture("profile.json"), approved=True))
        save_settings(session, {"role_aliases": fixture("role-aliases.json")})
        source = session.scalar(select(Source).where(Source.name == "Synthetic demo board"))
        if source is None:
            source = Source(
                name="Synthetic demo board",
                company="Synthetic employers",
                kind="demo",
                enabled=True,
                config={"stage": 0},
                capability={"supported": True, "demo": True, "publication": "synthetic examples"},
            )
            session.add(source)
            session.flush()
        identity = source.id
    seed_targets()
    run_scan(identity)
    return identity


def seed_targets():
    """Create a disabled checklist without adding a candidate or fake vacancies."""
    with Session.begin() as session:
        targets_path = REPO / "fixtures" / "target-companies.json"
        for target in json.loads(targets_path.read_text()) if targets_path.exists() else []:
            if session.scalar(select(Source.id).where(Source.name == target["name"])):
                continue
            session.add(
                Source(
                    name=target["name"],
                    company=target["name"],
                    kind="unsupported",
                    url=target["url"],
                    enabled=False,
                    config={"priority_countries": target["countries"]},
                    capability={
                        "supported": False,
                        "entry_page_found": True,
                        "checked_on": "2026-10-11",
                        "note": "Official careers entry identified; connector/access/pagination not validated. Use manual import.",
                    },
                )
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed", "advance", "evaluate", "targets"])
    args = parser.parse_args()
    if args.command == "targets":
        seed_targets()
        print("Disabled employer checklist added; no sources enabled.")
    elif args.command == "seed":
        print(f"Demo board {seed()} seeded. All displayed vacancies are synthetic.")
    elif args.command == "advance":
        if not settings.demo_mode:
            raise ValueError("Demo mode is disabled")
        with Session.begin() as session:
            source = session.scalar(select(Source).where(Source.kind == "demo"))
            if not source:
                raise ValueError("Seed first")
            source.config = source.config | {"stage": 1}
            identity = source.id
        print(f"Scan {run_scan(identity)} completed")
    else:
        from app.matching.scoring import deterministic
        from app.services.settings import DEFAULTS

        records = fixture("vacancies.json")
        profile = fixture("profile.json")
        ranked = sorted(
            [(deterministic(j, profile, DEFAULTS)["score"], j) for j in records],
            key=lambda x: x[0],
            reverse=True,
        )
        correct = sum(j["label"] == "relevant" for _, j in ranked[:10])
        for score, job in ranked[:10]:
            print(f"{score:3} {job['title']} [{job['label']}]")
        print(
            f"Synthetic fixture precision@10: {correct}/10; quality gate: {'PASS' if correct >= 8 else 'FAIL'}"
        )
        print(
            "This measures synthetic fixture ordering, not real-world accuracy. Adjacent/uncertain jobs require manual review."
        )


if __name__ == "__main__":
    main()
