import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.auth import require_roles
from app.db import get_db
from app.models import Role, User
from app.schemas import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    _: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db)
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.role, User.display_name)))


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    current: User = Depends(require_roles(Role.STUDENT, Role.TEACHER, Role.ADMIN)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if current.role != Role.ADMIN and current.id != target.id:
        raise HTTPException(status_code=403, detail="You may only view your own profile")
    return target


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    update: UserUpdate,
    request: Request,
    admin: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and update.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Administrators cannot deactivate their own portal access",
        )
    before = {"role": target.role.value, "is_active": target.is_active}
    if update.role is not None:
        target.role = update.role
    if update.is_active is not None:
        target.is_active = update.is_active
    db.add(target)
    db.commit()
    db.refresh(target)
    record_event(
        db,
        action="user.access_updated",
        actor=admin,
        target_type="user",
        target_id=target.id,
        correlation_id=request.headers.get("X-Correlation-ID"),
        details={
            "before": before,
            "after": {"role": target.role.value, "is_active": target.is_active},
        },
    )
    return target
