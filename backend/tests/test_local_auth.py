from conftest import ADMIN
from fastapi.testclient import TestClient


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


def test_approved_local_user_receives_database_role(client: TestClient) -> None:
    password = "A-safe-teacher-passphrase-2026"
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
