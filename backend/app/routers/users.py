import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.auth import require_roles
from app.db import get_db
from app.models import Role, User
from app.rate_limit import enforce_rate_limit
from app.routers.authentication import issue_school_invitation
from app.schemas import (
    UserInvitationCreate,
    UserInvitationRead,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(
    _: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db)
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.role, User.display_name)))


@router.post(
    "/invitations",
    response_model=UserInvitationRead,
    status_code=status.HTTP_201_CREATED,
)
def invite_user(
    invitation: UserInvitationCreate,
    request: Request,
    admin: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> UserInvitationRead:
    email = str(invitation.email).lower().strip()
    enforce_rate_limit(
        db,
        request,
        scope="admin-invite",
        subject=email,
        limit=5,
        window_seconds=3600,
    )
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email already has a portal record. Use Re-send invite instead.",
        )
    display_name = " ".join(invitation.display_name.strip().split())
    user = User(
        email=email,
        display_name=display_name,
        role=invitation.role,
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    delivered = issue_school_invitation(db, user)
    record_event(
        db,
        action="user.invited",
        actor=admin,
        target_type="user",
        target_id=user.id,
        outcome="success" if delivered else "failure",
        correlation_id=request.headers.get("X-Correlation-ID"),
        details={"role": user.role.value, "email_delivery": delivered},
    )
    return UserInvitationRead(
        status="sent" if delivered else "delivery_failed",
        message=(
            f"Invitation sent to {user.email}."
            if delivered
            else "The account was created, but email delivery failed. Use Re-send invite."
        ),
        user=UserRead.model_validate(user),
    )


@router.post("/{user_id}/reinvite", response_model=UserInvitationRead)
def reinvite_user(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> UserInvitationRead:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    enforce_rate_limit(
        db,
        request,
        scope="admin-reinvite",
        subject=target.email,
        limit=5,
        window_seconds=3600,
    )
    delivered = issue_school_invitation(db, target)
    record_event(
        db,
        action="user.reinvited",
        actor=admin,
        target_type="user",
        target_id=target.id,
        outcome="success" if delivered else "failure",
        correlation_id=request.headers.get("X-Correlation-ID"),
        details={"role": target.role.value, "email_delivery": delivered},
    )
    return UserInvitationRead(
        status="sent" if delivered else "delivery_failed",
        message=(
            f"Invitation sent again to {target.email}."
            if delivered
            else "The invitation email could not be delivered. Try again later."
        ),
        user=UserRead.model_validate(target),
    )


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
    if (
        (update.is_active is True or update.role is not None)
        and target.local_credential is not None
        and target.email_verified_at is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This local account must verify its email before role assignment or activation",
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
