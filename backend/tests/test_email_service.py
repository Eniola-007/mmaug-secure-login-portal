from types import SimpleNamespace

from app import email_service


class _Poller:
    def result(self):
        return {"status": "Succeeded"}


class _EmailClient:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.polling_values: list[bool] = []

    def begin_send(self, message: dict) -> _Poller:
        self.messages.append(message)
        return _Poller()


def _settings(*, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        email_delivery_enabled=enabled,
        acs_email_endpoint="https://example.communication.azure.com",
        acs_email_sender="donotreply@example.azurecomm.net",
        azure_client_id="managed-identity-client-id",
        public_frontend_url="https://portal.example",
        email_verification_minutes=60,
        password_reset_minutes=30,
    )


def test_verification_and_reset_messages_use_secure_frontend_links(monkeypatch) -> None:
    client = _EmailClient()
    monkeypatch.setattr(email_service, "get_settings", _settings)
    monkeypatch.setattr(email_service, "_client", lambda: client)

    assert email_service.send_verification_email("learner@example.com", "A <Learner>", "v&x")
    assert email_service.send_password_reset_email("learner@example.com", "A Learner", "r&x")
    assert email_service.send_password_setup_email("learner@example.com", "A Learner", "s&x")
    assert email_service.send_microsoft_registration_email("learner@example.com", "A Learner")
    assert email_service.send_admin_verification_alert(
        "admin@example.com",
        "An Admin",
        "A <Learner>",
        "learner@example.com",
    )
    assert email_service.send_school_invitation_email(
        "teacher@example.com",
        "A Teacher",
        "teacher",
        "i&x",
        "reset_password",
    )

    assert len(client.messages) == 6
    assert "verify_email=v%26x" in client.messages[0]["content"]["html"]
    assert "A &lt;Learner&gt;" in client.messages[0]["content"]["html"]
    assert "reset_password=r%26x" in client.messages[1]["content"]["html"]
    assert client.messages[0]["senderAddress"] == "donotreply@example.azurecomm.net"
    assert "reset_password=s%26x" in client.messages[2]["content"]["html"]
    assert client.messages[2]["content"]["subject"] == "Set up your MMAUG portal password"
    assert client.messages[3]["content"]["subject"] == "Your MMAUG portal request was received"
    assert (
        client.messages[4]["content"]["subject"]
        == "MMAUG account verified and ready for review"
    )
    assert "A &lt;Learner&gt;" in client.messages[4]["content"]["html"]
    assert client.messages[5]["content"]["subject"] == (
        "You're invited to join MMAUG High School"
    )
    assert "reset_password=i%26x" in client.messages[5]["content"]["html"]
    assert "Teacher" in client.messages[5]["content"]["html"]
    assert "continue with Microsoft" in client.messages[5]["content"]["html"]


def test_email_delivery_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "get_settings", lambda: _settings(enabled=False))
    assert not email_service.send_verification_email("learner@example.com", "Learner", "token")

    monkeypatch.setattr(email_service, "get_settings", _settings)

    class BrokenClient:
        def begin_send(self, _message: dict):
            raise RuntimeError("delivery unavailable")

    monkeypatch.setattr(email_service, "_client", BrokenClient)
    assert not email_service.send_password_reset_email(
        "learner@example.com", "Learner", "token"
    )


def test_email_delivery_rejects_unsuccessful_final_status(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "get_settings", _settings)

    class FailedPoller:
        def result(self):
            return {"status": "Failed"}

    class FailedClient:
        def begin_send(self, _message: dict):
            return FailedPoller()

    monkeypatch.setattr(email_service, "_client", FailedClient)
    assert not email_service.send_verification_email(
        "learner@example.com", "Learner", "token"
    )
