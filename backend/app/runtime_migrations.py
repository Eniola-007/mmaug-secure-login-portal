import logging
import threading
import time
from enum import StrEnum
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


class MigrationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


_status = MigrationStatus.PENDING
_lock = threading.Lock()
_worker: threading.Thread | None = None


def migration_status() -> MigrationStatus:
    with _lock:
        return _status


def _set_status(status: MigrationStatus) -> None:
    global _status
    with _lock:
        _status = status


def _upgrade_database() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    configuration = Config(str(backend_root / "alembic.ini"))
    configuration.set_main_option("script_location", str(backend_root / "migrations"))

    for attempt in range(1, 6):
        try:
            command.upgrade(configuration, "head")
            _set_status(MigrationStatus.SUCCEEDED)
            logger.info("Database migration completed successfully")
            return
        except Exception as exc:  # pragma: no cover - exercised against Azure PostgreSQL
            logger.warning(
                "Database migration attempt %s failed (%s)", attempt, type(exc).__name__
            )
            if attempt < 5:
                time.sleep(min(10 * (2 ** (attempt - 1)), 60))

    _set_status(MigrationStatus.FAILED)
    logger.error("Database migration did not complete after five attempts")


def start_runtime_migration(environment: str) -> None:
    """Start the idempotent migration without blocking App Service warm-up probes."""
    global _status, _worker

    if environment == "test":
        _set_status(MigrationStatus.SUCCEEDED)
        return

    with _lock:
        if _status in {MigrationStatus.RUNNING, MigrationStatus.SUCCEEDED}:
            return
        _status = MigrationStatus.RUNNING
        _worker = threading.Thread(
            target=_upgrade_database,
            name="database-migration",
            daemon=True,
        )
        _worker.start()
