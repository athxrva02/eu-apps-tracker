from datetime import timedelta

from sqlalchemy import select

from app.connectors import NormalizedJob
from app.models import (
    DeliveryAttempt,
    Job,
    JobVersion,
    Match,
    Notification,
    Observation,
    ProfileVersion,
    Source,
)
from app.security import digest
from app.timeutils import aware, utcnow


def approved_profile(session):
    return session.scalar(
        select(ProfileVersion)
        .where(ProfileVersion.approved.is_(True))
        .order_by(ProfileVersion.id.desc())
        .limit(1)
    )


def substantive(data: dict) -> dict:
    return {
        k: v
        for k, v in data.items()
        if k not in {"external_id", "received", "updated", "publication", "closed"}
    }


def ingest(
    session, source: Source, records: list[NormalizedJob], complete: bool, now=None
) -> tuple[list[int], list[int]]:
    now = now or utcnow()
    new_ids, changed_ids, seen = [], [], set()
    for record in records:
        raw = record.model_dump()
        observation = session.scalar(
            select(Observation).where(
                Observation.source_id == source.id, Observation.external_id == record.external_id
            )
        )
        job = session.get(Job, observation.job_id) if observation else None
        if job is None:
            # Employer + authoritative identity; title similarity never silently merges jobs.
            if record.requisition_id:
                job = session.scalar(
                    select(Job)
                    .where(
                        Job.company == record.company, Job.requisition_id == record.requisition_id
                    )
                    .limit(1)
                )
            if job is None:
                job = next(
                    (
                        candidate
                        for candidate in session.scalars(select(Job).where(Job.url == record.url))
                        if not (
                            record.requisition_id
                            and candidate.requisition_id
                            and record.requisition_id != candidate.requisition_id
                        )
                    ),
                    None,
                )
        is_new = job is None
        if is_new:
            job = Job(
                company=record.company,
                title=record.title,
                url=record.url,
                requisition_id=record.requisition_id,
                data=raw,
                content_hash=digest(substantive(raw)),
                first_seen_at=now,
                last_seen_at=now,
                discovery_event=source.baseline_complete,
                availability="unverified" if source.kind == "email" else "open",
            )
            session.add(job)
            session.flush()
            if source.baseline_complete:
                new_ids.append(job.id)
        # Partial email observations cannot overwrite richer employer descriptions.
        should_update = (
            is_new
            or (not record.provisional and source.kind != "email")
            or len(record.description) > len(job.data.get("description", ""))
        )
        if should_update:
            content_hash = digest(substantive(raw))
            if is_new or content_hash != job.content_hash:
                job.title, job.url, job.data, job.content_hash = (
                    record.title,
                    record.url,
                    raw,
                    content_hash,
                )
                if source.kind != "email":
                    job.company = record.company
                if record.requisition_id:
                    job.requisition_id = record.requisition_id
                version = session.scalar(
                    select(JobVersion).where(
                        JobVersion.job_id == job.id, JobVersion.content_hash == content_hash
                    )
                )
                if not version:
                    session.add(JobVersion(job_id=job.id, content_hash=content_hash, data=raw))
                changed_ids.append(job.id)
            else:
                # Timestamp evidence can change independently of the scoring content.
                job.data = job.data | {k: raw[k] for k in ["publication", "updated", "received"]}
        job.last_seen_at = now
        if source.kind != "email":
            job.availability = "closed" if record.closed else "open"
        if observation is None:
            observation = Observation(
                source_id=source.id,
                job_id=job.id,
                external_id=record.external_id,
                data=raw,
                first_seen_at=now,
                last_seen_at=now,
                missing_count=0,
            )
            session.add(observation)
        else:
            observation.data, observation.last_seen_at, observation.missing_count = raw, now, 0
        seen.add(record.external_id)
    if complete and source.kind not in {"email", "manual"}:
        observations = session.scalars(
            select(Observation).where(Observation.source_id == source.id)
        ).all()
        for observation in observations:
            if observation.external_id not in seen:
                observation.missing_count += 1
                job = session.get(Job, observation.job_id)
                if observation.missing_count >= 3:
                    # A second authoritative source still observing this job keeps it open.
                    others = session.scalars(
                        select(Observation)
                        .join(Source, Source.id == Observation.source_id)
                        .where(
                            Observation.job_id == job.id,
                            Observation.source_id != source.id,
                            Source.kind.notin_(["email", "manual"]),
                            Observation.missing_count < 3,
                        )
                    ).all()
                    if not others:
                        job.availability = "closed"
    if complete:
        source.baseline_complete = True
    session.flush()
    return list(dict.fromkeys(new_ids)), list(dict.fromkeys(changed_ids))


def save_match(session, job: Job, profile: ProfileVersion, config: dict, result: dict):
    from app.matching.scoring import cache_key

    key = cache_key(substantive(job.data), profile.id, config)
    existing = session.scalar(
        select(Match).where(
            Match.job_id == job.id, Match.profile_id == profile.id, Match.cache_key == key
        )
    )
    if existing:
        return existing
    match = Match(
        job_id=job.id, profile_id=profile.id, cache_key=key, score=result["score"], result=result
    )
    session.add(match)
    session.flush()
    return match


def enqueue_discovery(session, job: Job, match: Match, config: dict, batch_key: str):
    from app.config import settings
    from app.timeutils import quiet_until

    result = match.result
    if not settings.demo_mode and not config["notifications_enabled"]:
        return
    if (
        result["score"] < config["high_threshold"]
        or result["provisional"]
        or result["hard_filters"]
    ):
        return
    identity = f"candidate:1:job:{job.id}:discovery:email"
    if session.scalar(select(Notification.id).where(Notification.identity == identity)):
        return
    due = quiet_until(utcnow(), config["timezone"], config["quiet_start"], config["quiet_end"])
    session.add(
        Notification(
            identity=identity,
            job_id=job.id,
            event_type="discovery",
            due_at=due,
            batch_key=batch_key,
            payload={
                "title": job.title,
                "company": job.company,
                "locations": job.data.get("locations", []),
                "score": match.score,
                "reasons": [r["reason"] for r in result["reasons"][:3]],
                "gaps": result["gaps"],
                "unknowns": result["unknowns"],
                "url": job.url,
                "freshness": "newly discovered",
                "source": batch_key,
                "demo": job.data.get("demo", False),
            },
        )
    )


def latest_match(session, job_id: int, profile_id: int | None):
    if profile_id is None:
        return None
    return session.scalar(
        select(Match)
        .where(Match.job_id == job_id, Match.profile_id == profile_id)
        .order_by(Match.id.desc())
        .limit(1)
    )


def serialization_context(session, profile_id=None):
    matches = {}
    if profile_id is not None:
        for match in session.scalars(
            select(Match).where(Match.profile_id == profile_id).order_by(Match.id.desc())
        ):
            matches.setdefault(match.job_id, match)
    observations = {}
    for observation, source in session.execute(select(Observation, Source).join(Source)):
        observations.setdefault(observation.job_id, []).append((observation, source))
    return matches, observations


def serialize_job(session, job: Job, profile_id=None, context=None) -> dict:
    from app.timeutils import iso

    match = context[0].get(job.id) if context else latest_match(session, job.id, profile_id)
    observations = (
        context[1].get(job.id, [])
        if context
        else session.execute(
            select(Observation, Source).join(Source).where(Observation.job_id == job.id)
        ).all()
    )
    return {
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "url": job.url,
        "data": job.data,
        "first_seen_at": iso(job.first_seen_at),
        "last_seen_at": iso(job.last_seen_at),
        "availability": job.availability,
        "candidate_status": job.candidate_status,
        "feedback": job.feedback,
        "match": match.result if match else None,
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "kind": s.kind,
                "url": o.data["url"],
                "publication": o.data.get("publication"),
                "updated": o.data.get("updated"),
                "received": o.data.get("received"),
                "first_seen_at": iso(o.first_seen_at),
            }
            for o, s in observations
        ],
    }


def merge_jobs(session, target: Job, duplicate: Job):
    if target.id == duplicate.id:
        raise ValueError("Choose two different jobs")
    for observation in session.scalars(
        select(Observation).where(Observation.job_id == duplicate.id)
    ):
        observation.job_id = target.id
    # Collapse discovery events and retain any delivery evidence to prevent resends.
    for event in session.scalars(
        select(Notification).where(Notification.job_id == duplicate.id)
    ).all():
        identity = event.identity.replace(f"job:{duplicate.id}:", f"job:{target.id}:")
        existing = session.scalar(select(Notification).where(Notification.identity == identity))
        if existing:
            if event.status in {"delivered", "unknown", "sending", "preview"}:
                existing.status = event.status
            for attempt in session.scalars(
                select(DeliveryAttempt).where(DeliveryAttempt.notification_id == event.id)
            ):
                attempt.notification_id = existing.id
            session.flush()
            session.delete(event)
        else:
            event.job_id, event.identity = target.id, identity
    target.first_seen_at = min(aware(target.first_seen_at), aware(duplicate.first_seen_at))
    target.discovery_event = target.discovery_event or duplicate.discovery_event
    target.feedback = sorted(set(target.feedback + duplicate.feedback))
    if duplicate.candidate_status != "new" and target.candidate_status == "new":
        target.candidate_status = duplicate.candidate_status
    session.flush()
    session.delete(duplicate)


def is_stale(source: Source) -> bool:
    return source.enabled and (
        source.last_success is None
        or aware(source.last_success) < utcnow() - timedelta(minutes=source.interval_minutes * 2)
    )
