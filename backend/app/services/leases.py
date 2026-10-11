import threading
import time
import uuid
from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db import Session
from app.models import Lease
from app.timeutils import utcnow


class Busy(ValueError):
    pass


def acquire(session, key: str, owner: str, seconds: int = 120) -> bool:
    now = utcnow()
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(Lease).values(key=key, owner=owner, expires=now + timedelta(seconds=seconds))
    statement = statement.on_conflict_do_update(
        index_elements=[Lease.key],
        set_={"owner": owner, "expires": now + timedelta(seconds=seconds)},
        where=Lease.expires < now,
    )
    return session.execute(statement).rowcount == 1


class Guard:
    def __init__(self, key: str, seconds: int = 120, wait: float = 0, factory=None):
        self.key, self.seconds, self.wait = key, seconds, wait
        self.factory = factory or Session
        self.owner = uuid.uuid4().hex
        self.stop = threading.Event()
        self.lost = False

    def __enter__(self):
        deadline = time.monotonic() + self.wait
        while True:
            with self.factory.begin() as session:
                ok = acquire(session, self.key, self.owner, self.seconds)
            if ok:
                break
            if time.monotonic() >= deadline:
                raise Busy(f"{self.key.split(':')[0]} is already running")
            time.sleep(0.1)
        self.thread = threading.Thread(target=self._heartbeat, daemon=True)
        self.thread.start()
        return self

    def _heartbeat(self):
        while not self.stop.wait(max(1, self.seconds / 3)):
            try:
                with self.factory.begin() as session:
                    result = session.execute(
                        update(Lease)
                        .where(
                            Lease.key == self.key,
                            Lease.owner == self.owner,
                            Lease.expires > utcnow(),
                        )
                        .values(expires=utcnow() + timedelta(seconds=self.seconds))
                    )
                    if result.rowcount != 1:
                        self.lost = True
                        return
            except Exception:
                self.lost = True
                return

    def verify(self, session):
        lease = session.get(Lease, self.key, populate_existing=True)
        from app.timeutils import aware

        if self.lost or not lease or lease.owner != self.owner or aware(lease.expires) <= utcnow():
            raise Busy("Worker lease expired; results cannot be committed")

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=5)
        with self.factory.begin() as session:
            session.execute(delete(Lease).where(Lease.key == self.key, Lease.owner == self.owner))


@contextmanager
def host_lease(host: str):
    with Guard("host:" + host, seconds=60, wait=30):
        yield
