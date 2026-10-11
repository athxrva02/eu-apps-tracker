"""Container init: migrate, then seed only a fresh demo workspace."""

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.config import REPO, settings
from app.db import Session
from app.models import Source


def main():
    command.upgrade(Config(str(REPO / "alembic.ini")), "head")
    from app.demo import seed_targets

    seed_targets()
    if settings.demo_mode:
        with Session() as session:
            existing = session.scalar(select(Source.id).where(Source.kind == "demo"))
        if existing is None:
            from app.demo import seed

            seed()


if __name__ == "__main__":
    main()
