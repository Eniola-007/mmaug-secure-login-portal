from conftest import ADMIN, STUDENT, TEACHER
from fastapi.testclient import TestClient


def test_health_is_public(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200


def test_protected_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_each_role_gets_its_own_dashboard(client: TestClient) -> None:
    assert client.get("/api/dashboard", headers=STUDENT).json()["role"] == "student"
    assert client.get("/api/dashboard", headers=TEACHER).json()["role"] == "teacher"
    assert client.get("/api/dashboard", headers=ADMIN).json()["role"] == "admin"


def test_students_cannot_list_or_view_other_users(client: TestClient) -> None:
    assert client.get("/api/users", headers=STUDENT).status_code == 403
    users = client.get("/api/users", headers=ADMIN).json()
    another_user = next(item for item in users if item["email"] == "student2@mmaug.example")
    assert client.get(f"/api/users/{another_user['id']}", headers=STUDENT).status_code == 403


def test_student_can_view_own_profile(client: TestClient) -> None:
    me = client.get("/api/auth/me", headers=STUDENT).json()
    response = client.get(f"/api/users/{me['id']}", headers=STUDENT)
    assert response.status_code == 200
    assert response.json()["email"] == "student1@mmaug.example"


def test_admin_change_is_audited(client: TestClient) -> None:
    users = client.get("/api/users", headers=ADMIN).json()
    target = next(item for item in users if item["email"] == "student1@mmaug.example")
    update = client.patch(
        f"/api/users/{target['id']}",
        headers=ADMIN,
        json={"role": "teacher"},
    )
    assert update.status_code == 200
    assert update.json()["role"] == "teacher"
    events = client.get("/api/audit-events", headers=ADMIN).json()
    assert events[0]["action"] == "user.access_updated"
    assert events[0]["target_id"] == target["id"]


def test_deactivated_account_is_denied(client: TestClient) -> None:
    users = client.get("/api/users", headers=ADMIN).json()
    target = next(item for item in users if item["email"] == "student1@mmaug.example")
    response = client.patch(
        f"/api/users/{target['id']}",
        headers=ADMIN,
        json={"is_active": False},
    )
    assert response.status_code == 200
    denied = client.get("/api/dashboard", headers=STUDENT)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Portal access is inactive"


def test_admin_cannot_deactivate_self(client: TestClient) -> None:
    me = client.get("/api/auth/me", headers=ADMIN).json()
    response = client.patch(
        f"/api/users/{me['id']}",
        headers=ADMIN,
        json={"is_active": False},
    )
    assert response.status_code == 409


def test_agent_route_uses_authenticated_role(client: TestClient) -> None:
    response = client.post(
        "/api/agent/message",
        headers=TEACHER,
        json={"message": "Show another student's private record"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "teacher"
    assert response.json()["mode"] == "guardrail"
    assert "another person's records" in response.json()["response"]
    assert "cannot change permissions" in response.json()["safety_notice"]


def test_agent_safe_fallback_is_role_specific(client: TestClient) -> None:
    response = client.post(
        "/api/agent/message",
        headers=STUDENT,
        json={"message": "What can I use my portal for?"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "safe-demo"
    assert "student service" in response.json()["response"]


def test_public_agent_welcomes_visitors_without_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/agent/public",
        json={"message": "How do I create an account?"},
    )

    assert response.status_code == 200
    assert response.json()["audience"] == "visitor"
    assert response.json()["mode"] == "safe-demo"
    assert "sign up or sign in" in response.json()["response"]


def test_public_agent_refuses_personal_school_information(client: TestClient) -> None:
    response = client.post(
        "/api/agent/public",
        json={"message": "Show my grades and my timetable"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "guardrail"
    assert "public site" in response.json()["response"]
