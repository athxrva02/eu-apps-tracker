import random
from datetime import timedelta

from sqlalchemy import select

from app.connectors import fetch_source
from app.db import Session
from app.matching.provider import optional_model
from app.matching.scoring import cache_key, deterministic
from app.models import Config, Job, Match, ScanRun, Source
from app.services.jobs import approved_profile, enqueue_discovery, ingest, save_match, substantive
from app.services.leases import Guard, host_lease
from app.services.settings import get_settings
from app.timeutils import utcnow


def score_job(job_id: int, notify: bool = False, batch_key: str = "manual"):
    with Guard(f"score:{job_id}", seconds=120, wait=30):
        return _score_job(job_id, notify, batch_key)


def _score_job(job_id: int, notify: bool, batch_key: str):
    with Session() as session:
        job = session.get(Job, job_id)
        profile = approved_profile(session)
        if not job:
            return True
        if not profile:
            return False
        config = get_settings(session)
        key = cache_key(substantive(job.data), profile.id, config)
        existing = session.scalar(
            select(Match).where(
                Match.job_id == job.id, Match.profile_id == profile.id, Match.cache_key == key
            )
        )
        data, profile_data, profile_id = dict(job.data), dict(profile.data), profile.id
        result = existing.result if existing else None
    if result is None:
        result = optional_model(
            data, profile_data, config, deterministic(data, profile_data, config)
        )
    with Guard("ingest", wait=30):
        with Session.begin() as session:
            job = session.get(Job, job_id)
            profile = approved_profile(session)
            # Results generated against obsolete content/profile/settings are discarded.
            if (
                not job
                or not profile
                or profile.id != profile_id
                or cache_key(substantive(job.data), profile_id, get_settings(session)) != key
            ):
                return False
            match = save_match(session, job, profile, config, result)
            if notify:
                enqueue_discovery(session, job, match, config, batch_key)
    return True


def rescore_all():
    with Session() as session:
        ids = list(session.scalars(select(Job.id)))
        queued = session.get(Config, "rescore")
        token = queued.value.get("token") if queued else None
    for identity in ids:
        score_job(identity)
    with Session.begin() as session:
        queued = session.get(Config, "rescore")
        if queued and queued.value.get("token") == token:
            session.delete(queued)
    return len(ids)


def queue_matching(
    session, source_id: int, new_ids: list[int], changed_ids: list[int], count: int, notify=True
):
    pending = list(dict.fromkeys(changed_ids + new_ids))
    run = ScanRun(
        source_id=source_id,
        status="imported",
        complete=True,
        count=count,
        new_count=len(new_ids),
        ended_at=utcnow(),
        stats={
            "score_job_ids": pending,
            "new_job_ids": new_ids if notify else [],
            "matching_pending": bool(pending),
        },
    )
    session.add(run)
    session.flush()
    return run.id


def finish_matching(run_id: int):
    """Resume the durable matching queue after a crash, without duplicate alerts."""
    with Guard(f"matching:{run_id}", seconds=120):
        with Session() as session:
            run = session.get(ScanRun, run_id)
            if not run or not run.stats.get("matching_pending"):
                return
            pending = list(run.stats.get("score_job_ids", []))
            discoveries = set(run.stats.get("new_job_ids", []))
        for job_id in pending:
            if not score_job(job_id, job_id in discoveries, f"scan:{run_id}"):
                continue
            with Session.begin() as session:
                run = session.get(ScanRun, run_id)
                remaining = [
                    identity for identity in run.stats["score_job_ids"] if identity != job_id
                ]
                run.stats = run.stats | {
                    "score_job_ids": remaining,
                    "matching_pending": bool(remaining),
                }


def recover_matching():
    from app.services.leases import Busy

    with Session() as session:
        ids = [
            run.id for run in session.scalars(select(ScanRun)) if run.stats.get("matching_pending")
        ]
    for identity in ids:
        try:
            finish_matching(identity)
        except Busy:
            continue
    with Session() as session:
        pending_rescore = session.get(Config, "rescore") is not None
    if pending_rescore:
        with Guard("rescore", seconds=120):
            rescore_all()


def run_scan(source_id: int, client=None) -> int:
    with Guard(f"source:{source_id}", seconds=120) as guard:
        with Session.begin() as session:
            source = session.get(Source, source_id)
            if not source:
                raise ValueError("Source not found")
            # Recover old runs from crashed processes only after obtaining the lease.
            for old in session.scalars(
                select(ScanRun).where(ScanRun.source_id == source_id, ScanRun.status == "running")
            ):
                old.status, old.complete, old.ended_at, old.error = (
                    "interrupted",
                    False,
                    utcnow(),
                    "Worker stopped before scan completion",
                )
            run = ScanRun(source_id=source_id)
            session.add(run)
            session.flush()
            run_id = run.id
        try:
            result = fetch_source(source, client, host_lease=host_lease)
            with Guard("ingest", wait=30):
                with Session.begin() as session:
                    guard.verify(session)
                    source = session.get(Source, source_id)
                    new_ids, changed_ids = ingest(session, source, result.jobs, result.complete)
                    run = session.get(ScanRun, run_id)
                    run.status = "success" if result.complete else "incomplete"
                    run.complete, run.count, run.new_count = (
                        result.complete,
                        len(result.jobs),
                        len(new_ids),
                    )
                    pending = list(dict.fromkeys(changed_ids + new_ids))
                    run.stats, run.ended_at = (
                        result.stats
                        | {
                            "warnings": result.warnings,
                            "score_job_ids": pending,
                            "new_job_ids": new_ids,
                            "matching_pending": bool(pending),
                        },
                        utcnow(),
                    )
                    if result.complete:
                        source.last_success, source.last_error = utcnow(), None
                    else:
                        source.last_error = "; ".join(result.warnings)
                    source.next_run = utcnow() + timedelta(
                        minutes=source.interval_minutes, seconds=random.randint(0, 30)
                    )
        except Exception as exc:
            with Session.begin() as session:
                run = session.get(ScanRun, run_id)
                run.status, run.complete, run.ended_at = "failed", False, utcnow()
                # Store operational errors, never raw documents or provider payloads.
                message = (
                    str(exc)
                    if isinstance(exc, ValueError)
                    else f"{type(exc).__name__}: scan failed"
                )
                run.error = message[:500]
                source = session.get(Source, source_id)
                source.last_error, source.next_run = (
                    run.error,
                    utcnow() + timedelta(minutes=source.interval_minutes),
                )
        # The queue is committed with ingestion. A matching failure leaves it retryable.
        finish_matching(run_id)
        return run_id
