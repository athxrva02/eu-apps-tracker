import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + str(
    Path(tempfile.mkdtemp(prefix="eu-agent-tests-")) / "test.sqlite"
)
os.environ["DEMO_MODE"] = "true"
os.environ["ADMIN_TOKEN"] = ""

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def seeded():
    from app.demo import seed

    return seed()
