from types import SimpleNamespace

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


def test_admin_can_delete_another_user_but_not_self(client: TestClient) -> None:
    users = client.get("/api/users", headers=ADMIN).json()
    target = next(item for item in users if item["email"] == "student2@mmaug.example")
    deleted = client.delete(f"/api/users/{target['id']}", headers=ADMIN)
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted", "user_id": target["id"]}
    assert client.get(f"/api/users/{target['id']}", headers=ADMIN).status_code == 404
    events = client.get("/api/audit-events", headers=ADMIN).json()
    assert events[0]["action"] == "user.deleted"
    assert events[0]["target_id"] == target["id"]

    me = client.get("/api/auth/me", headers=ADMIN).json()
    assert client.delete(f"/api/users/{me['id']}", headers=ADMIN).status_code == 409
    assert client.delete(f"/api/users/{target['id']}", headers=STUDENT).status_code == 403


def test_non_admins_only_see_their_own_activity(client: TestClient) -> None:
    student = client.get("/api/auth/me", headers=STUDENT).json()
    teacher = client.get("/api/auth/me", headers=TEACHER).json()
    student_events = client.get("/api/audit-events", headers=STUDENT).json()
    assert student_events
    assert all(
        event["actor_id"] == student["id"] or event["target_id"] == student["id"]
        for event in student_events
    )
    assert all(event["actor_id"] != teacher["id"] for event in student_events)


def test_admin_can_invite_and_reinvite_a_role_scoped_user(
    client: TestClient, monkeypatch
) -> None:
    invitation_tokens: list[tuple[str | None, str | None]] = []
    monkeypatch.setattr(
        "app.routers.authentication.send_school_invitation_email",
        lambda _email, _name, _role, token=None, query_parameter=None: (
            invitation_tokens.append((token, query_parameter)) or True
        ),
    )
    invited = client.post(
        "/api/users/invitations",
        headers=ADMIN,
        json={
            "display_name": "Invited Teacher",
            "email": "invited.teacher@example.com",
            "role": "teacher",
        },
    )
    assert invited.status_code == 201
    invitation = invited.json()
    assert invitation["status"] == "sent"
    assert invitation["user"]["role"] == "teacher"
    assert invitation["user"]["is_active"] is False
    assert invitation["user"]["identity_provider"] == "local"
    assert invitation_tokens[0][1] == "reset_password"

    reinvited = client.post(
        f"/api/users/{invitation['user']['id']}/reinvite",
        headers=ADMIN,
    )
    assert reinvited.status_code == 200
    assert len(invitation_tokens) == 2
    assert invitation_tokens[1][0] != invitation_tokens[0][0]

    password = "A-secure-invited-teacher-passphrase-2026"
    expired = client.post(
        "/api/auth/reset-password",
        json={"token": invitation_tokens[0][0], "password": password},
    )
    assert expired.status_code == 400
    accepted = client.post(
        "/api/auth/reset-password",
        json={"token": invitation_tokens[1][0], "password": password},
    )
    assert accepted.status_code == 200

    pending = client.post(
        "/api/auth/login",
        json={"email": "invited.teacher@example.com", "password": password},
    )
    assert pending.status_code == 403
    assert "administrator approval" in pending.json()["detail"]

    approved = client.patch(
        f"/api/users/{invitation['user']['id']}",
        headers=ADMIN,
        json={"is_active": True},
    )
    assert approved.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"email": "invited.teacher@example.com", "password": password},
    )
    assert login.status_code == 200

    duplicate = client.post(
        "/api/users/invitations",
        headers=ADMIN,
        json={
            "display_name": "Duplicate Teacher",
            "email": "invited.teacher@example.com",
            "role": "student",
        },
    )
    assert duplicate.status_code == 409
    assert client.post(
        "/api/users/invitations",
        headers=STUDENT,
        json={
            "display_name": "Unauthorized Invite",
            "email": "blocked@example.com",
            "role": "admin",
        },
    ).status_code == 403


def test_invited_user_can_accept_with_same_email_microsoft_identity(
    client: TestClient, monkeypatch
) -> None:
    invitation: dict[str, str] = {}
    monkeypatch.setattr(
        "app.routers.authentication.send_school_invitation_email",
        lambda _email, _name, _role, token=None, query_parameter=None: (
            invitation.update(token=token or "", parameter=query_parameter or "") or True
        ),
    )
    created = client.post(
        "/api/users/invitations",
        headers=ADMIN,
        json={
            "display_name": "Microsoft Teacher",
            "email": "microsoft.teacher@example.com",
            "role": "teacher",
        },
    )
    assert created.status_code == 201
    assert invitation["parameter"] == "reset_password"

    monkeypatch.setattr(
        "app.routers.authentication.claims_from_entra_token",
        lambda _token: {
            "tid": "71beefd7-29f4-4b9e-9cb2-e78b5dc851ad",
            "oid": "2c79f45c-16bf-4e52-a593-43d5de2b57b7",
            "preferred_username": "microsoft.teacher@example.com",
            "name": "Microsoft Teacher",
        },
    )
    monkeypatch.setattr(
        "app.routers.authentication.send_microsoft_registration_email",
        lambda _email, _name: True,
    )
    monkeypatch.setattr(
        "app.routers.authentication.send_admin_verification_alert",
        lambda _recipient, _admin, _name, _email: True,
    )
    accepted = client.post(
        "/api/auth/register-microsoft",
        headers={"Authorization": "Bearer validated-test-token"},
    )
    assert accepted.status_code == 201
    assert accepted.json()["status"] == "verified_pending_approval"

    users = client.get("/api/users", headers=ADMIN).json()
    linked = next(
        user for user in users if user["email"] == "microsoft.teacher@example.com"
    )
    assert linked["role"] == "teacher"
    assert linked["is_active"] is False
    assert linked["identity_provider"] == "microsoft"
    assert linked["email_verified_at"] is not None
    assert client.post(
        "/api/auth/reset-password",
        json={
            "token": invitation["token"],
            "password": "This-token-was-rotated-by-Microsoft-2026",
        },
    ).status_code == 400


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


def test_authenticated_agent_uses_foundry_with_database_role(
    client: TestClient, monkeypatch
) -> None:
    foundry_calls: list[tuple[str, str, str]] = []

    def fake_ask_foundry(audience: str, agent_name: str, prompt: str) -> str:
        foundry_calls.append((audience, agent_name, prompt))
        return "Foundry grounded answer."

    monkeypatch.setattr(
        "app.routers.agents.get_settings",
        lambda: SimpleNamespace(
            azure_ai_project_endpoint="https://foundry.example/project",
            azure_ai_student_agent_id="mmaug-student",
            azure_ai_teacher_agent_id="mmaug-teacher",
            azure_ai_admin_agent_id="mmaug-admin",
        ),
    )
    monkeypatch.setattr("app.routers.agents._ask_foundry", fake_ask_foundry)

    response = client.post(
        "/api/agent/message",
        headers=STUDENT,
        json={"message": "Where can I find approved study resources?"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "foundry"
    assert response.json()["role"] == "student"
    assert response.json()["response"] == "Foundry grounded answer."
    assert len(foundry_calls) == 1
    audience, agent_name, prompt = foundry_calls[0]
    assert audience == "student"
    assert agent_name == "mmaug-student"
    assert "Authenticated PostgreSQL portal role: student." in prompt
    assert "Where can I find approved study resources?" in prompt


def test_foundry_request_targets_agent_and_deletes_one_turn_conversation(monkeypatch) -> None:
    from types import SimpleNamespace

    from pydantic import SecretStr

    calls: dict[str, object] = {}

    class FakeOpenAI:
        class conversations:
            @staticmethod
            def create(**kwargs):
                calls["conversation_create"] = kwargs
                return SimpleNamespace(id="conversation-123")

            @staticmethod
            def delete(conversation_id: str, **kwargs) -> None:
                calls["deleted_conversation"] = conversation_id
                calls["conversation_delete"] = kwargs

        class responses:
            @staticmethod
            def create(**kwargs):
                calls["response_request"] = kwargs
                return SimpleNamespace(output_text="Grounded Foundry answer.")

    class FakeProject:
        def __init__(self, *, endpoint: str, credential) -> None:
            calls["endpoint"] = endpoint
            calls["credential"] = credential

        @staticmethod
        def get_openai_client():
            return FakeOpenAI()

    monkeypatch.setattr("azure.ai.projects.AIProjectClient", FakeProject)
    monkeypatch.setattr(
        "azure.identity.DefaultAzureCredential",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        "app.routers.agents.get_settings",
        lambda: SimpleNamespace(
            azure_ad_client_secret=SecretStr(""),
            azure_client_id="managed-identity-client-id",
            azure_ai_project_endpoint="https://foundry.example/project",
        ),
    )

    from app.routers.agents import _ask_foundry

    result = _ask_foundry("student", "mmaug-student", "Where are study resources?")

    assert result == "Grounded Foundry answer."
    assert calls["endpoint"] == "https://foundry.example/project"
    assert calls["deleted_conversation"] == "conversation-123"
    assert calls["conversation_create"] == {"timeout": 15.0}
    assert calls["conversation_delete"] == {"timeout": 10.0}
    request = calls["response_request"]
    assert request["conversation"] == "conversation-123"
    assert request["input"] == "Where are study resources?"
    assert request["timeout"] == 45.0
    assert request["extra_body"]["agent_reference"] == {
        "name": "mmaug-student",
        "type": "agent_reference",
    }


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
