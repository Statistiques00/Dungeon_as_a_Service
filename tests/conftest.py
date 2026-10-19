import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.mkdtemp()) / 'lifespan.db'}")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.services import hero_service

GUERRIER = {"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2}


@pytest.fixture
def engine():
    moteur = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(moteur)
    yield moteur
    moteur.dispose()


@pytest.fixture
def client(engine, monkeypatch):
    def session_de_test():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(hero_service, "DUREE_REPOS", 0)
    app.dependency_overrides[get_session] = session_de_test
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


def entete(client: TestClient, username: str, password: str = "motdepasse") -> dict[str, str]:
    client.post("/auth/register", json={"username": username, "password": password})
    token = client.post("/auth/login", data={"username": username, "password": password}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


@pytest.fixture
def alice(client):
    return entete(client, "alice")


@pytest.fixture
def heros(client, alice):
    return client.post("/heroes", json=GUERRIER, headers=alice).json()
