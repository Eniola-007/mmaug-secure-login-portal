from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.db import get_db
from app.models import AuditEvent, Role, User
from app.schemas import AuditEventRead

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> list[AuditEvent]:
    query = select(AuditEvent).order_by(desc(AuditEvent.occurred_at)).limit(limit)
    return list(db.scalars(query))
