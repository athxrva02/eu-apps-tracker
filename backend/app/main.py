import secrets
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import BackgroundTasks, Body, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text

from app.config import REPO, settings
from app.connectors import NormalizedJob, fetch_source
from app.db import Session
from app.models import (
    Config,
    DeliveryAttempt,
    ImportedMessage,
    Job,
    Notification,
    ProfileVersion,
    ScanRun,
    Source,
    Usage,
)
from app.notifications.delivery import deliver_due, render_payload
from app.security import validated_url
from app.services.imports import import_source, parse_email, register_email
from app.services.jobs import (
    approved_profile,
    ingest,
    is_stale,
    merge_jobs,
    serialization_context,
    serialize_job,
)
from app.services.leases import Busy, Guard
from app.services.profiles import MAX_UPLOAD, draft_profile, extract_document, validate_profile
from app.services.scans import finish_matching, queue_matching, rescore_all, run_scan, score_job
from app.services.settings import get_settings, save_settings
from app.timeutils import aware, iso, recently_published, utcnow


@asynccontextmanager
async def lifespan(_):
    # Startup fails clearly if documented migrations have not been applied.
    with Session() as session:
        session.execute(select(Config).limit(1))
    yield


app = FastAPI(title="European Executive Job Agent", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def protect(request: Request, call_next):
    if request.url.path.startswith("/api"):
        if settings.admin_token:
            supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
            if not secrets.compare_digest(supplied, settings.admin_token):
                return JSONResponse({"detail": "Enter the configured admin token"}, status_code=401)
        elif request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}:
            return JSONResponse(
                {"detail": "Remote access requires ADMIN_TOKEN and HTTPS"}, status_code=403
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin:
                from urllib.parse import urlsplit

                if urlsplit(origin).netloc != request.headers.get("host"):
                    return JSONResponse(
                        {"detail": "Cross-origin writes are blocked"}, status_code=403
                    )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(ValueError)
async def invalid(_, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409 if isinstance(exc, Busy) else 422)


def required(session, model, identity):
    row = session.get(model, identity)
    if row is None:
        raise HTTPException(404, "Not found")
    return row


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        with Session() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(503, "Database unavailable") from None


@app.get("/api/v1/overview")
def overview():
    with Session() as session:
        profile = approved_profile(session)
        jobs = list(session.scalars(select(Job)))
        sources = list(session.scalars(select(Source)))
        worker = session.get(Config, "worker")
        usage = session.scalars(
            select(Usage).where(
                Usage.created_at
                >= utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            )
        ).all()
        config = get_settings(session)
        context = serialization_context(session, profile.id if profile else None)
        matches = [match.result for match in context[0].values()]
        return {
            "demo": settings.demo_mode,
            "total_jobs": len(jobs),
            "high_matches": sum(
                bool(m and m["score"] >= config["high_threshold"] and not m["provisional"])
                for m in matches
            ),
            "saved": sum(j.candidate_status == "saved" for j in jobs),
            "enabled_sources": sum(s.enabled for s in sources),
            "total_sources": len(sources),
            "stale_sources": sum(is_stale(s) for s in sources),
            "profile_approved": bool(profile),
            "worker": worker.value if worker else None,
            "model_cost_usd": sum(
                u.actual_usd if u.actual_usd is not None else u.reserved_usd for u in usage
            ),
            "budget_usd": config["monthly_budget_usd"],
            "timezone": config["timezone"],
        }


@app.get("/api/v1/settings")
def read_settings():
    with Session() as session:
        return get_settings(session) | {
            "demo_mode": settings.demo_mode,
            "smtp_configured": bool(settings.smtp_host and settings.smtp_from),
            "model_configured": settings.model_configured,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
        }


@app.patch("/api/v1/settings")
def update_settings(tasks: BackgroundTasks, changes: dict = Body(...)):
    requires_rescore = any(
        k in changes
        for k in [
            "weights",
            "countries",
            "exclusions",
            "high_threshold",
            "review_threshold",
            "llm_enabled",
            "external_model_consent",
        ]
    )
    with Session.begin() as session:
        result = save_settings(session, changes)
        if requires_rescore:
            row = session.get(Config, "rescore") or Config(key="rescore")
            row.value = {"token": secrets.token_hex(16)}
            session.add(row)
    if requires_rescore:
        tasks.add_task(rescore_all)
    return result


@app.get("/api/v1/profiles")
def profiles():
    with Session() as session:
        return [
            {"id": p.id, "approved": p.approved, "created_at": iso(p.created_at), "data": p.data}
            for p in session.scalars(select(ProfileVersion).order_by(ProfileVersion.id.desc()))
        ]


class TextProfile(BaseModel):
    text: str = Field(min_length=10, max_length=250000)


@app.post("/api/v1/profiles/paste")
def paste_profile(body: TextProfile):
    with Session.begin() as session:
        profile = ProfileVersion(data=draft_profile(body.text))
        session.add(profile)
        session.flush()
        return {"id": profile.id, "approved": False, "data": profile.data}


@app.post("/api/v1/profiles/upload")
async def upload_profile(file: UploadFile = File(...)):
    content = await file.read(MAX_UPLOAD + 1)
    # Upload bytes are processed in memory and never retained on disk.
    data = draft_profile(
        extract_document(file.filename or "", file.content_type or "", content), "uploaded résumé"
    )
    with Session.begin() as session:
        profile = ProfileVersion(data=data)
        session.add(profile)
        session.flush()
        return {"id": profile.id, "approved": False, "data": profile.data}


@app.put("/api/v1/profiles/{identity}")
def edit_profile(identity: int, data: dict = Body(...)):
    with Session.begin() as session:
        original = required(session, ProfileVersion, identity)
        validate_profile(data)
        if original.approved:
            original = ProfileVersion(data=data)
            session.add(original)
            session.flush()
        else:
            original.data = data
        return {"id": original.id, "approved": original.approved, "data": original.data}


@app.post("/api/v1/profiles/{identity}/approve")
def approve_profile(identity: int, tasks: BackgroundTasks):
    with Session.begin() as session:
        profile = required(session, ProfileVersion, identity)
        validate_profile(profile.data)
        profile.approved = True
        row = session.get(Config, "rescore") or Config(key="rescore")
        row.value = {"token": secrets.token_hex(16)}
        session.add(row)
    tasks.add_task(rescore_all)
    return {"id": identity, "approved": True}


@app.delete("/api/v1/profiles")
def delete_profile_data():
    with Guard("ingest", wait=30):
        with Session.begin() as session:
            session.execute(delete(Notification))
            session.execute(delete(ProfileVersion))
            session.execute(delete(ImportedMessage))
    return {
        "deleted": "Profile versions, matches, email metadata and notifications; database backups expire separately"
    }


@app.get("/api/v1/jobs")
def list_jobs(
    q: str = "",
    freshness: str = "all",
    hours: int = Query(24, ge=1, le=168),
    min_score: int = Query(0, ge=0, le=100),
    country: str = "",
    company: str = "",
    status: str = "",
    work_mode: str = "",
    source: int | None = None,
    function: str = "",
):
    with Session() as session:
        profile = approved_profile(session)
        result = []
        now = utcnow()
        context = serialization_context(session, profile.id if profile else None)
        for job in session.scalars(select(Job)):
            row = serialize_job(session, job, profile.id if profile else None, context)
            match = row["match"]
            if (
                q.lower() not in (job.title + " " + job.company).lower()
                or company.lower() not in job.company.lower()
            ):
                continue
            if function.lower() not in (job.title + " " + job.data.get("description", "")).lower():
                continue
            if min_score and (not match or match["score"] < min_score):
                continue
            if country and country not in job.data.get("countries", []):
                continue
            if status and job.candidate_status != status:
                continue
            if work_mode and work_mode != job.data.get("work_mode"):
                continue
            if source and not any(s["id"] == source for s in row["sources"]):
                continue
            if freshness == "published" and not recently_published(
                job.data.get("publication", {}), hours, now
            ):
                continue
            if freshness == "discovered" and aware(job.first_seen_at) < now - timedelta(
                hours=hours
            ):
                continue
            result.append(row)
        return sorted(
            result,
            key=lambda r: ((r["match"] or {}).get("score", -1), r["first_seen_at"]),
            reverse=True,
        )


@app.get("/api/v1/jobs/{identity}")
def job_detail(identity: int):
    with Session() as session:
        profile = approved_profile(session)
        return serialize_job(
            session, required(session, Job, identity), profile.id if profile else None
        )


@app.patch("/api/v1/jobs/{identity}")
def update_job(identity: int, changes: dict = Body(...)):
    with Session.begin() as session:
        job = required(session, Job, identity)
        if "status" in changes:
            if changes["status"] not in {
                "new",
                "saved",
                "dismissed",
                "applied",
                "interview",
                "offer",
                "archived",
            }:
                raise ValueError("Invalid candidate status")
            job.candidate_status = changes["status"]
        if "feedback" in changes:
            if changes["feedback"] not in {"too junior", "wrong sector", "good match"}:
                raise ValueError("Invalid feedback")
            job.feedback = sorted(set(job.feedback + [changes["feedback"]]))
        if "availability" in changes:
            if changes["availability"] not in {"open", "closed", "unverified"}:
                raise ValueError("Invalid availability")
            job.availability = changes["availability"]
        return {"id": job.id, "status": job.candidate_status, "feedback": job.feedback}


@app.post("/api/v1/jobs/{identity}/merge/{duplicate_id}")
def merge(identity: int, duplicate_id: int):
    with Guard("ingest", wait=30):
        with Session.begin() as session:
            merge_jobs(
                session, required(session, Job, identity), required(session, Job, duplicate_id)
            )
    score_job(identity)
    return {"id": identity, "merged": duplicate_id}


def source_dict(source: Source) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "company": source.company,
        "kind": source.kind,
        "url": source.url,
        "config": source.config,
        "enabled": source.enabled,
        "interval_minutes": source.interval_minutes,
        "next_run": iso(source.next_run),
        "last_success": iso(source.last_success),
        "last_error": source.last_error,
        "baseline_complete": source.baseline_complete,
        "stale": is_stale(source),
        "capability": source.capability,
    }


@app.get("/api/v1/sources")
def sources():
    with Session() as session:
        return [source_dict(s) for s in session.scalars(select(Source).order_by(Source.id))]


class SourceInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    kind: str
    url: str = ""
    config: dict = Field(default_factory=dict)
    interval_minutes: int = Field(default=60, ge=15, le=10080)


@app.post("/api/v1/sources")
def create_source(body: SourceInput):
    if body.kind not in {"greenhouse", "lever", "html", "unsupported"}:
        raise ValueError("Choose Greenhouse, Lever, configured HTML, or unsupported")
    if body.url:
        validated_url(body.url)
    with Session.begin() as session:
        if session.scalar(select(Source.id).where(Source.name == body.name)):
            raise ValueError("A source with this name already exists")
        source = Source(**body.model_dump(), enabled=False)
        session.add(source)
        session.flush()
        return source_dict(source)


@app.patch("/api/v1/sources/{identity}")
def edit_source(identity: int, changes: dict = Body(...)):
    with Session.begin() as session:
        source = required(session, Source, identity)
        if "enabled" in changes:
            if not isinstance(changes["enabled"], bool):
                raise ValueError("enabled must be a boolean")
            if changes["enabled"] and not source.capability.get("supported"):
                raise ValueError("Pass a connection test before enabling this source")
            source.enabled = changes["enabled"]
            if source.enabled:
                source.next_run = utcnow()
        if any(key in changes for key in ("config", "url", "kind", "company")):
            candidate = SourceInput.model_validate(
                {
                    "name": source.name,
                    "company": source.company,
                    "kind": source.kind,
                    "url": source.url,
                    "config": source.config,
                    "interval_minutes": source.interval_minutes,
                }
                | {key: value for key, value in changes.items() if key != "enabled"}
            )
            if candidate.kind not in {"greenhouse", "lever", "html", "unsupported"}:
                raise ValueError("Unsupported connector kind")
            source.kind, source.company = candidate.kind, candidate.company
            if "url" in changes:
                if changes["url"]:
                    validated_url(changes["url"])
                source.url = changes["url"]
            if "config" in changes:
                source.config = changes["config"]
            source.capability, source.enabled = {}, False
        if "name" in changes:
            if not isinstance(changes["name"], str) or not changes["name"].strip():
                raise ValueError("Source name is required")
            if session.scalar(
                select(Source.id).where(Source.name == changes["name"], Source.id != identity)
            ):
                raise ValueError("A source with this name already exists")
            source.name = changes["name"]
        if "interval_minutes" in changes:
            if (
                not isinstance(changes["interval_minutes"], int)
                or not 15 <= changes["interval_minutes"] <= 10080
            ):
                raise ValueError("Interval must be 15–10080 minutes")
            source.interval_minutes = changes["interval_minutes"]
        return source_dict(source)


@app.delete("/api/v1/sources/{identity}")
def remove_source(identity: int):
    # Preserve source observations and audit history; deletion archives the source.
    with Session.begin() as session:
        source = required(session, Source, identity)
        source.enabled = False
        source.capability = source.capability | {"archived": True}
    return {"archived": identity}


@app.post("/api/v1/sources/{identity}/test")
def test_source(identity: int):
    with Guard(f"source:{identity}"):
        with Session() as session:
            source = required(session, Source, identity)
        try:
            result = fetch_source(source)
            capability = {
                "supported": result.complete,
                "count": len(result.jobs),
                "complete": result.complete,
                "warnings": result.warnings,
                "tested_at": iso(utcnow()),
                "publication": "source evidence only; may be unavailable",
                "pagination": "complete" if result.complete else "capped",
            }
        except ValueError as exc:
            capability = {"supported": False, "error": str(exc), "tested_at": iso(utcnow())}
        with Session.begin() as session:
            required(session, Source, identity).capability = capability
        return capability


@app.post("/api/v1/sources/{identity}/scan")
def scan_source(identity: int, tasks: BackgroundTasks):
    with Session() as session:
        source = required(session, Source, identity)
        if source.kind in {"unsupported", "email", "manual"}:
            raise ValueError("This source cannot be scanned automatically")
    tasks.add_task(run_scan, identity)
    return {"queued": identity}


@app.post("/api/v1/imports/jobs")
def import_jobs(records: list[NormalizedJob], tasks: BackgroundTasks):
    if not 1 <= len(records) <= 500:
        raise ValueError("Import 1–500 jobs at a time")
    with Guard("ingest", wait=30):
        with Session.begin() as session:
            source = import_source(session, "manual")
            new, changed = ingest(session, source, records, True)
            run_id = queue_matching(session, source.id, new, changed, len(records))
    tasks.add_task(finish_matching, run_id)
    return {"imported": len(records), "new": len(new)}


@app.post("/api/v1/imports/email")
async def import_email(tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".eml"):
        raise ValueError("Upload an .eml job-alert email")
    metadata, records = parse_email(await file.read(MAX_UPLOAD + 1))
    with Guard("ingest", wait=30):
        with Session.begin() as session:
            if not register_email(session, metadata):
                return {"duplicate": True, "imported": 0}
            source = import_source(session, "email")
            new, changed = ingest(session, source, records, True)
            run_id = queue_matching(session, source.id, new, changed, len(records), notify=False)
    tasks.add_task(finish_matching, run_id)
    return {"duplicate": False, "imported": len(records), "limited_evidence": True}


@app.get("/api/v1/activity")
def activity():
    with Session() as session:
        runs = [
            {
                "id": r.id,
                "source_id": r.source_id,
                "started_at": iso(r.started_at),
                "ended_at": iso(r.ended_at),
                "status": r.status,
                "complete": r.complete,
                "count": r.count,
                "new_count": r.new_count,
                "error": r.error,
                "stats": r.stats,
            }
            for r in session.scalars(select(ScanRun).order_by(ScanRun.id.desc()).limit(100))
        ]
        notifications = [
            {
                "id": n.id,
                "type": n.event_type,
                "status": n.status,
                "due_at": iso(n.due_at),
                "created_at": iso(n.created_at),
                "attempts": n.attempts,
                "payload": n.payload,
                "body": render_payload(n.payload),
            }
            for n in session.scalars(
                select(Notification)
                .where(Notification.event_type != "digest-member")
                .order_by(Notification.id.desc())
                .limit(100)
            )
        ]
        attempts = [
            {
                "notification_id": d.notification_id,
                "status": d.status,
                "provider_id": d.provider_id,
                "error": d.error,
                "created_at": iso(d.created_at),
            }
            for d in session.scalars(
                select(DeliveryAttempt).order_by(DeliveryAttempt.id.desc()).limit(100)
            )
        ]
        usage = [
            {
                "id": u.id,
                "status": u.status,
                "reserved_usd": u.reserved_usd,
                "actual_usd": u.actual_usd,
                "tokens": u.tokens,
                "created_at": iso(u.created_at),
            }
            for u in session.scalars(select(Usage).order_by(Usage.id.desc()).limit(100))
        ]
        return {
            "runs": runs,
            "notifications": notifications,
            "delivery_attempts": attempts,
            "model_usage": usage,
        }


@app.post("/api/v1/notifications/test")
def test_notification():
    with Session.begin() as session:
        config = get_settings(session)
        if not settings.demo_mode and not (config["notifications_enabled"] and config["recipient"]):
            raise ValueError("Configure recipient and explicitly enable notifications first")
        event = Notification(
            identity="test:" + secrets.token_hex(10),
            event_type="test",
            payload={
                "title": "Notification connection test",
                "company": "European Job Agent",
                "url": "http://localhost:8000",
                "score": 0,
            },
        )
        session.add(event)
    deliver_due()
    return {"mode": "preview" if settings.demo_mode else "configured recipient only"}


@app.get("/api/v1/export")
def export_data():
    with Session() as session:
        profile = approved_profile(session)
        return {
            "exported_at": iso(utcnow()),
            "profile": profile.data if profile else None,
            "jobs": [
                serialize_job(session, j, profile.id if profile else None)
                for j in session.scalars(select(Job))
            ],
            "sources": [source_dict(s) for s in session.scalars(select(Source))],
        }


@app.post("/api/v1/demo/advance")
def advance_demo(tasks: BackgroundTasks):
    if not settings.demo_mode:
        raise HTTPException(404)
    with Session.begin() as session:
        source = session.scalar(select(Source).where(Source.kind == "demo"))
        if not source:
            raise ValueError("Seed demo data first")
        source.config = source.config | {"stage": 1}
        identity = source.id
    tasks.add_task(run_scan, identity)
    return {"queued": identity, "message": "A subsequent scan will discover one synthetic vacancy"}


static = REPO / "frontend" / "dist"
if static.exists():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")


@app.get("/")
def index():
    if not (static / "index.html").exists():
        return JSONResponse(
            {"message": "Build frontend with npm --prefix frontend run build; API docs at /docs"}
        )
    return FileResponse(static / "index.html")
