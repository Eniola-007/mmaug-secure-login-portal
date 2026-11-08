from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.audit import record_event
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import User
from app.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=UserRead)
def me(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    record_event(
        db,
        action="session.validated",
        actor=user,
        correlation_id=request.headers.get("X-Correlation-ID"),
    )
    return user


@router.get("/recovery")
def recovery() -> dict[str, str]:
    return {
        "provider": "Microsoft Entra ID",
        "url": get_settings().password_reset_url,
        "message": "Password recovery is handled by the identity provider.",
    }
