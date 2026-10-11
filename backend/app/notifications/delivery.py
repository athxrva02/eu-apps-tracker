import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import settings
from app.db import Session
from app.models import DeliveryAttempt, Job, Notification, ScanRun, Source
from app.services.jobs import approved_profile, latest_match
from app.services.leases import Guard
from app.services.settings import get_settings
from app.timeutils import quiet_until, utcnow


def render_payload(payload: dict) -> str:
    if "items" in payload:
        parts = ["European executive job digest", ""]
        parts.extend(render_payload(item) for item in payload["items"])
        if payload.get("provisional"):
            parts.append("Limited evidence — review manually")
            parts.extend(render_payload(item) for item in payload["provisional"])
        if payload.get("failures"):
            parts.append("Sources needing attention: " + ", ".join(payload["failures"]))
        return "\n\n".join(parts)
    return "\n".join(
        [
            f"{payload['title']} — {payload['company']}",
            f"Locations: {', '.join(payload.get('locations', [])) or 'unknown'}",
            f"Score: {payload.get('score', 'provisional')} • {payload.get('freshness', 'availability unverified')}",
            *["• " + reason for reason in payload.get("reasons", [])[:3]],
            "Gaps: " + ("; ".join(payload.get("gaps", [])) or "Review original requirements"),
            "Unknowns: " + "; ".join(payload.get("unknowns", [])),
            "Source: " + payload.get("source", "import"),
            payload["url"],
        ]
    )


def smtp_send(recipient: str, subject: str, body: str, message_id: str) -> tuple[str, str | None]:
    """Return accepted, failed-before-acceptance, or ambiguous. Never retry ambiguity."""
    if not settings.smtp_host or not settings.smtp_from:
        return "failed", "SMTP host and sender are not configured"
    message = EmailMessage()
    message["From"], message["To"], message["Subject"], message["Message-ID"] = (
        settings.smtp_from,
        recipient,
        subject,
        message_id,
    )
    message.set_content(body)
    server = None
    try:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
        if settings.smtp_starttls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
    except (OSError, smtplib.SMTPException):
        if server:
            server.close()
        return "failed", "SMTP connection or authentication failed before sending"
    try:
        server.send_message(message)
        return "delivered", None
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
        return "failed", "SMTP explicitly rejected the message"
    except (OSError, smtplib.SMTPException):
        return "unknown", "SMTP acknowledgement is ambiguous; no automatic resend"
    finally:
        server.close()


def deliver_due(sender=None):
    sender = sender or smtp_send
    with Guard("notification-delivery", seconds=120):
        with Session.begin() as session:
            config = get_settings(session)
            # A previous worker could have stopped after provider acceptance.
            for stale in session.scalars(
                select(Notification).where(Notification.status == "sending")
            ):
                stale.status = "unknown"
                session.add(
                    DeliveryAttempt(
                        notification_id=stale.id,
                        status="unknown",
                        error="Worker stopped during delivery; no blind resend",
                    )
                )
            due = list(
                session.scalars(
                    select(Notification)
                    .where(Notification.status == "queued", Notification.due_at <= utcnow())
                    .order_by(Notification.id)
                )
            )
            groups = {}
            for event in due:
                if event.event_type == "digest-member":
                    continue
                if event.batch_key and event.batch_key.startswith("scan:"):
                    run = session.get(ScanRun, int(event.batch_key.split(":", 1)[1]))
                    if run and (run.status == "running" or run.stats.get("matching_pending")):
                        continue
                groups.setdefault(event.batch_key or event.identity, []).append(event.id)
        for ids in groups.values():
            with Session.begin() as session:
                config = get_settings(session)
                events = [session.get(Notification, identity) for identity in ids]
                if not settings.demo_mode:
                    if not config["notifications_enabled"] or not config["recipient"]:
                        continue
                    due_at = quiet_until(
                        utcnow(), config["timezone"], config["quiet_start"], config["quiet_end"]
                    )
                    if due_at > utcnow():
                        for event in events:
                            event.due_at = due_at
                        continue
                for event in events:
                    event.status, event.attempts = "sending", event.attempts + 1
                body = "\n\n".join(render_payload(event.payload) for event in events)
                subject = (
                    "European job digest"
                    if events[0].event_type == "digest"
                    else f"{len(events)} new executive job match(es)"
                )
                message_id = f"<eu-agent-{events[0].id}@job-agent.local>"
            if settings.demo_mode:
                state, error = "preview", None
            else:
                try:
                    state, error = sender(config["recipient"], subject, body, message_id)
                except Exception:
                    state, error = "unknown", "Delivery adapter stopped without acknowledgement"
            with Session.begin() as session:
                for identity in ids:
                    event = session.get(Notification, identity)
                    event.status = "queued" if state == "failed" and event.attempts < 3 else state
                    if event.status == "queued":
                        event.due_at = utcnow() + timedelta(minutes=2**event.attempts)
                    session.add(
                        DeliveryAttempt(
                            notification_id=event.id,
                            status=state,
                            provider_id=message_id if state in {"delivered", "preview"} else None,
                            error=error,
                        )
                    )
        return len(groups)


def schedule_digest(now=None):
    now = now or utcnow()
    with Guard("digest-scheduling", wait=5):
        with Session.begin() as session:
            config = get_settings(session)
            if not settings.demo_mode and not config["notifications_enabled"]:
                return None
            local = now.astimezone(ZoneInfo(config["timezone"]))
            if local.hour < config["digest_hour"]:
                return None
            identity = f"candidate:1:digest:{local.date()}:email"
            if session.scalar(select(Notification.id).where(Notification.identity == identity)):
                return None
            profile = approved_profile(session)
            if not profile:
                return None
            items, provisional = [], []
            members = []
            for job in session.scalars(
                select(Job).where(Job.discovery_event.is_(True), Job.availability != "closed")
            ):
                match = latest_match(session, job.id, profile.id)
                if (
                    not match
                    or match.score < config["review_threshold"]
                    or match.result["hard_filters"]
                ):
                    continue
                item = {
                    "title": job.title,
                    "company": job.company,
                    "score": match.score,
                    "locations": job.data.get("locations", []),
                    "url": job.url,
                    "freshness": "newly discovered",
                    "reasons": [r["reason"] for r in match.result["reasons"][:3]],
                    "gaps": match.result["gaps"],
                    "unknowns": match.result["unknowns"],
                }
                if match.result["provisional"]:
                    provisional.append(item)
                else:
                    membership = f"candidate:1:job:{job.id}:digest-member:email"
                    if not session.scalar(
                        select(Notification.id).where(Notification.identity == membership)
                    ):
                        items.append(item)
                        members.append((job.id, membership))
            failures = [
                source.name
                for source in session.scalars(
                    select(Source).where(Source.enabled.is_(True), Source.last_error.is_not(None))
                )
            ]
            notification = Notification(
                identity=identity,
                event_type="digest",
                due_at=quiet_until(
                    now, config["timezone"], config["quiet_start"], config["quiet_end"]
                ),
                payload={
                    "items": items,
                    "provisional": provisional,
                    "failures": failures,
                    "date": str(local.date()),
                },
            )
            session.add(notification)
            session.flush()
            for job_id, membership in members:
                session.add(
                    Notification(
                        identity=membership,
                        job_id=job_id,
                        event_type="digest-member",
                        status="included",
                        payload={"digest_id": notification.id},
                    )
                )
            return notification.id
