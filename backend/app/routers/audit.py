from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import AuditEvent, Role, User
from app.schemas import AuditEventRead

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditEvent]:
    query = select(AuditEvent)
    if current.role != Role.ADMIN:
        query = query.where(
            or_(
                AuditEvent.actor_id == current.id,
                AuditEvent.target_id == str(current.id),
            )
        )
    query = query.order_by(desc(AuditEvent.occurred_at)).limit(limit)
    return list(db.scalars(query))
