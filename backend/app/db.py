from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import REPO, settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    options = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=options, pool_pre_ping=True)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure_sqlite(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

    return engine


(REPO / ".data").mkdir(exist_ok=True)
engine = make_engine(settings.database_url)
Session = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope():
    with Session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
