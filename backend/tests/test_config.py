from app.config import Settings


def test_cors_origins_accepts_json_environment_format(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["https://portal.example"]')

    settings = Settings()

    assert settings.cors_origins == ["https://portal.example"]
