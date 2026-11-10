from datetime import UTC, datetime

from conftest import ADMIN
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def test_local_registration_is_pending_and_cannot_choose_role(client: TestClient) -> None:
    rejected = client.post(
        "/api/auth/register",
        json={
            "display_name": "New Learner",
            "email": "new.learner@example.com",
            "password": "A-safe-learning-passphrase-2026",
            "role": "admin",
        },
    )
    assert rejected.status_code == 422

    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "New Learner",
            "email": "new.learner@example.com",
            "password": "A-safe-learning-passphrase-2026",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_approval"
    users = client.get("/api/users", headers=ADMIN).json()
    created = next(user for user in users if user["email"] == "new.learner@example.com")
    assert created["role"] == "student"
    assert created["is_active"] is False


def test_approved_local_user_receives_database_role(client: TestClient, monkeypatch) -> None:
    password = "A-safe-teacher-passphrase-2026"
    verification: dict[str, str] = {}
    monkeypatch.setattr(
        "app.routers.authentication.send_verification_email",
        lambda _email, _name, token: verification.update(token=token) or True,
    )
    client.post(
        "/api/auth/register",
        json={
            "display_name": "New Teacher",
            "email": "new.teacher@example.com",
            "password": password,
        },
    )
    users = client.get("/api/users", headers=ADMIN).json()
    created = next(user for user in users if user["email"] == "new.teacher@example.com")

    pending = client.post(
        "/api/auth/login",
        json={"email": created["email"], "password": password},
    )
    assert pending.status_code == 403
    assert "Verify your email" in pending.json()["detail"]

    rejected = client.patch(
        f"/api/users/{created['id']}",
        headers=ADMIN,
        json={"role": "teacher", "is_active": True},
    )
    assert rejected.status_code == 409

    verified = client.post(
        "/api/auth/verify-email",
        json={"token": verification["token"]},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "verified_pending_approval"

    approved = client.patch(
        f"/api/users/{created['id']}",
        headers=ADMIN,
        json={"role": "teacher", "is_active": True},
    )
    assert approved.status_code == 200

    login = client.post(
        "/api/auth/login",
        json={"email": created["email"], "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    dashboard = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dashboard.status_code == 200
    assert dashboard.json()["role"] == "teacher"


def test_local_login_rejects_wrong_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "student1@mmaug.example", "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_password_reset_is_generic_and_revokes_old_sessions(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    password = "A-safe-student-passphrase-2026"
    reset: dict[str, str] = {}
    monkeypatch.setattr(
        "app.routers.authentication.send_verification_email",
        lambda _email, _name, _token: True,
    )
    client.post(
        "/api/auth/register",
        json={
            "display_name": "Reset Student",
            "email": "reset.student@example.com",
            "password": password,
        },
    )
    users = client.get("/api/users", headers=ADMIN).json()
    created = next(user for user in users if user["email"] == "reset.student@example.com")

    # Tests can mark email ownership verified without sending a real message.
    user = db_session.scalar(select(User).where(User.email == created["email"]))
    assert user is not None
    user.email_verified_at = datetime.now(UTC)
    db_session.commit()
    client.patch(
        f"/api/users/{created['id']}",
        headers=ADMIN,
        json={"is_active": True},
    )
    old_token = client.post(
        "/api/auth/login", json={"email": created["email"], "password": password}
    ).json()["access_token"]

    monkeypatch.setattr(
        "app.routers.authentication.send_password_reset_email",
        lambda _email, _name, token: reset.update(token=token) or True,
    )
    requested = client.post("/api/auth/forgot-password", json={"email": created["email"]})
    assert requested.status_code == 200
    unknown = client.post("/api/auth/forgot-password", json={"email": "unknown@example.com"})
    assert unknown.status_code == 200
    assert unknown.json()["message"] == requested.json()["message"]

    new_password = "A-new-safe-student-passphrase-2026"
    changed = client.post(
        "/api/auth/reset-password",
        json={"token": reset["token"], "password": new_password},
    )
    assert changed.status_code == 200
    assert (
        client.get("/api/dashboard", headers={"Authorization": f"Bearer {old_token}"}).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": created["email"], "password": new_password},
        ).status_code
        == 200
    )


def test_recovery_requests_are_persistently_rate_limited(client: TestClient) -> None:
    for _ in range(5):
        assert (
            client.post(
                "/api/auth/forgot-password", json={"email": "limited@example.com"}
            ).status_code
            == 200
        )
    limited = client.post("/api/auth/forgot-password", json={"email": "limited@example.com"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    assert client.post(
        "/api/auth/forgot-password", json={"email": "limited@example.com"}
    ).status_code == 429


def test_resend_verification_is_generic(client: TestClient, monkeypatch) -> None:
    delivered: list[str] = []
    monkeypatch.setattr(
        "app.routers.authentication.send_verification_email",
        lambda _email, _name, token: delivered.append(token) or True,
    )
    client.post(
        "/api/auth/register",
        json={
            "display_name": "Pending Learner",
            "email": "pending@example.com",
            "password": "A-safe-learning-passphrase-2026",
        },
    )
    known = client.post(
        "/api/auth/resend-verification", json={"email": "pending@example.com"}
    )
    unknown = client.post(
        "/api/auth/resend-verification", json={"email": "nobody@example.com"}
    )
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(delivered) == 2


def test_invalid_one_time_tokens_are_rejected(client: TestClient) -> None:
    invalid = "invalid-token-value-that-is-long-enough"
    assert client.post(
        "/api/auth/verify-email", json={"token": invalid}
    ).status_code == 400
    assert client.post(
        "/api/auth/reset-password",
        json={"token": invalid, "password": "A-safe-new-passphrase-2026"},
    ).status_code == 400
