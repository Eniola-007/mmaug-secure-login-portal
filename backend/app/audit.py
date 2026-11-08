import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, User


def record_event(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    outcome: str = "success",
    correlation_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor.id if actor else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        outcome=outcome,
        correlation_id=correlation_id,
        details_json=json.dumps(details or {}, separators=(",", ":"), sort_keys=True),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
