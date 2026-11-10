import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ALLOW_DEV_AUTH"] = "true"
os.environ["LOCAL_AUTH_JWT_SECRET"] = "test-only-secret-that-is-longer-than-32-characters"

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.seed import SEED_USERS  # noqa: E402


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    with TestingSession() as session:
        for tenant_id, object_id, email, name, role in SEED_USERS:
            session.add(
                User(
                    entra_tenant_id=tenant_id,
                    entra_object_id=object_id,
                    email=email,
                    display_name=name,
                    role=role,
                )
            )
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth(email: str) -> dict[str, str]:
    return {"X-Dev-User": email}


STUDENT = auth("student1@mmaug.example")
TEACHER = auth("teacher1@mmaug.example")
ADMIN = auth("admin@mmaug.example")
