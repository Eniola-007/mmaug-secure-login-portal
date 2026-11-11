from types import SimpleNamespace

from app import email_service


class _Poller:
    def result(self):
        return {"status": "Succeeded"}


class _EmailClient:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.polling_values: list[bool] = []

    def begin_send(self, message: dict, *, polling: bool) -> _Poller:
        self.messages.append(message)
        self.polling_values.append(polling)
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

    assert len(client.messages) == 3
    assert "verify_email=v%26x" in client.messages[0]["content"]["html"]
    assert "A &lt;Learner&gt;" in client.messages[0]["content"]["html"]
    assert "reset_password=r%26x" in client.messages[1]["content"]["html"]
    assert client.messages[0]["senderAddress"] == "donotreply@example.azurecomm.net"
    assert client.polling_values == [False, False, False]
    assert "reset_password=s%26x" in client.messages[2]["content"]["html"]
    assert client.messages[2]["content"]["subject"] == "Set up your MMAUG portal password"


def test_email_delivery_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(email_service, "get_settings", lambda: _settings(enabled=False))
    assert not email_service.send_verification_email("learner@example.com", "Learner", "token")

    monkeypatch.setattr(email_service, "get_settings", _settings)

    class BrokenClient:
        def begin_send(self, _message: dict, *, polling: bool):
            assert polling is False
            raise RuntimeError("delivery unavailable")

    monkeypatch.setattr(email_service, "_client", BrokenClient)
    assert not email_service.send_password_reset_email(
        "learner@example.com", "Learner", "token"
    )
