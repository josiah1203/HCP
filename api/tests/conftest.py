from __future__ import annotations
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("HCP_PROVIDER", "onprem-compose")
os.environ.setdefault("NEO4J_URI", "")
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("MINIO_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "hcp")
os.environ.setdefault("MINIO_SECRET_KEY", "hcpsecret")
os.environ.setdefault("MINIO_BUCKET", "hcp-local")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.auth.dependencies import hash_password  # noqa: E402
from app.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.db import Base, Org, Project, User  # noqa: E402


def _sqlite_compat_metadata() -> None:
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, postgresql.JSONB):
                col.type = sa.JSON()
            if isinstance(col.type, postgresql.ARRAY):
                col.type = sa.JSON()
            # SQLite only autoincrements INTEGER PRIMARY KEY, not BIGINT.
            if table.name == "event_log" and col.name == "seq":
                col.type = sa.Integer()


@pytest.fixture(scope="session")
def engine():
    url = os.environ["DATABASE_URL"]
    if url.startswith("sqlite"):
        _sqlite_compat_metadata()
        eng = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        eng = create_engine(url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    org = Org(name="Test Org", slug=f"test-{uuid.uuid4().hex[:8]}", plan="free")
    db_session.add(org)
    db_session.flush()

    user = User(
        org_id=org.id,
        email=f"test-{uuid.uuid4().hex[:8]}@hcp.test",
        name="Test User",
        password_hash=hash_password("testpass"),
        role="admin",
    )
    db_session.add(user)
    db_session.flush()

    project = Project(org_id=org.id, name="Test Project", created_by=user.id)
    db_session.add(project)
    db_session.commit()

    with TestClient(app) as test_client:
        test_client.test_org = org
        test_client.test_user = user
        test_client.test_project = project
        yield test_client

    app.dependency_overrides.clear()
