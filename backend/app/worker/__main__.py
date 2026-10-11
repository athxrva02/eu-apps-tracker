import logging
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from sqlalchemy import delete, select

from app.db import Session
from app.models import Config, ImportedMessage, ScanRun
from app.notifications.delivery import deliver_due, schedule_digest
from app.services.leases import Busy
from app.services.scans import recover_matching, run_scan
from app.services.settings import get_settings
from app.timeutils import iso, utcnow

stop = threading.Event()
log = logging.getLogger("jobagent.worker")


def heartbeat():
    with Session.begin() as session:
        heartbeat = session.get(Config, "worker") or Config(key="worker")
        heartbeat.value = {"last_tick": iso(utcnow())}
        session.add(heartbeat)


def maintain_heartbeat():
    while not stop.wait(15):
        try:
            heartbeat()
        except Exception:
            log.error("Worker heartbeat unavailable")


def run_once():
    from app.models import Source

    heartbeat()
    with Session.begin() as session:
        due = list(
            session.scalars(
                select(Source.id).where(
                    Source.enabled.is_(True),
                    Source.next_run <= utcnow(),
                    Source.kind.in_(["demo", "greenhouse", "lever", "html"]),
                )
            )
        )
        config = get_settings(session)
        session.execute(
            delete(ImportedMessage).where(
                ImportedMessage.created_at
                < utcnow() - timedelta(days=config["email_retention_days"])
            )
        )
        for run in session.scalars(
            select(ScanRun).where(
                ScanRun.ended_at < utcnow() - timedelta(days=config["log_retention_days"])
            )
        ):
            if not run.stats.get("matching_pending"):
                session.delete(run)

    def safe_scan(source_id):
        try:
            run_scan(source_id)
        except Busy:
            pass
        except Exception:
            log.error("Source %s scan failed before a run could be created", source_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(safe_scan, due))
    for operation in (recover_matching, schedule_digest, deliver_due):
        try:
            operation()
        except Busy:
            pass


def main():
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    threading.Thread(target=maintain_heartbeat, daemon=True).start()
    while not stop.is_set():
        try:
            run_once()
        except Exception:
            log.error("Worker tick failed; retrying in 10 seconds")
        stop.wait(10)


if __name__ == "__main__":
    main()
