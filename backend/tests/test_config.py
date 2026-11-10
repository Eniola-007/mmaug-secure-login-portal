from app.config import Settings
from app.runtime_migrations import MigrationStatus, migration_status, start_runtime_migration


def test_cors_origins_accepts_json_environment_format(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["https://portal.example"]')

    settings = Settings()

    assert settings.cors_origins == ["https://portal.example"]


def test_alembic_url_escapes_percent_encoded_password() -> None:
    settings = Settings(database_url="postgresql+psycopg://user:p%25word@database.example/db")

    assert settings.alembic_database_url == (
        "postgresql+psycopg://user:p%%25word@database.example/db"
    )


def test_runtime_migration_is_non_blocking_in_tests() -> None:
    start_runtime_migration("test")

    assert migration_status() == MigrationStatus.SUCCEEDED
