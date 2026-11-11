import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.audit import record_event
from app.auth import (
    bearer,
    claims_from_entra_token,
    create_local_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.db import get_db
from app.email_service import (
    send_admin_verification_alert,
    send_microsoft_registration_email,
    send_password_reset_email,
    send_password_setup_email,
    send_school_invitation_email,
    send_verification_email,
)
from app.models import (
    EmailVerificationToken,
    LocalCredential,
    PasswordResetToken,
    Role,
    User,
)
from app.rate_limit import enforce_rate_limit
from app.schemas import (
    EmailRequest,
    LocalLoginRequest,
    LocalRegistrationRequest,
    PasswordResetRequest,
    RegistrationRead,
    TokenRead,
    TokenRequest,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
email_adapter = TypeAdapter(EmailStr)


def _normalise_name(value: str) -> str:
    return " ".join(value.strip().split())


def _validate_new_password(password: str, email: str) -> None:
    common_passwords = {
        "password1234",
        "password123!",
        "letmein12345",
        "qwerty123456",
        "welcome12345",
    }
    lowered = password.casefold()
    if lowered in common_passwords or email.split("@", maxsplit=1)[0].casefold() in lowered:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a stronger password that does not contain your email name",
        )


def _pending_response() -> RegistrationRead:
    return RegistrationRead(
        status="pending_approval",
        message=(
            "Your account request has been received. Check your email to verify ownership. "
            "A school administrator must then assign and activate your database role."
        ),
    )


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _issue_verification(db: Session, user: User) -> bool:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_digest=_token_digest(raw_token),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=get_settings().email_verification_minutes),
        )
    )
    db.commit()
    return send_verification_email(user.email, user.display_name, raw_token)


def _issue_password_reset(db: Session, user: User) -> bool:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_digest=_token_digest(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=get_settings().password_reset_minutes),
        )
    )
    db.commit()
    return send_password_reset_email(user.email, user.display_name, raw_token)


def _issue_password_setup(db: Session, user: User) -> bool:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_digest=_token_digest(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=get_settings().password_reset_minutes),
        )
    )
    db.commit()
    return send_password_setup_email(user.email, user.display_name, raw_token)


def issue_school_invitation(db: Session, user: User) -> bool:
    """Send a role-specific invite and rotate any outstanding one-time token."""
    now = datetime.now(UTC)
    if user.entra_object_id or user.email_verified_at:
        return send_school_invitation_email(
            user.email,
            user.display_name,
            user.role.value,
        )

    raw_token = secrets.token_urlsafe(32)
    if user.local_credential:
        db.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        db.add(
            EmailVerificationToken(
                user_id=user.id,
                token_digest=_token_digest(raw_token),
                expires_at=now + timedelta(minutes=get_settings().email_verification_minutes),
            )
        )
        query_parameter = "verify_email"
    else:
        db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_digest=_token_digest(raw_token),
                expires_at=now + timedelta(minutes=get_settings().password_reset_minutes),
            )
        )
        query_parameter = "reset_password"
    db.commit()
    return send_school_invitation_email(
        user.email,
        user.display_name,
        user.role.value,
        raw_token,
        query_parameter,
    )


def _queue_admin_verification_alerts(
    db: Session,
    background_tasks: BackgroundTasks,
    verified_user: User,
) -> None:
    administrators = db.scalars(
        select(User).where(
            User.role == Role.ADMIN,
            User.is_active.is_(True),
            User.id != verified_user.id,
            or_(User.email_verified_at.is_not(None), User.entra_object_id.is_not(None)),
        )
    ).all()
    for administrator in administrators:
        background_tasks.add_task(
            send_admin_verification_alert,
            administrator.email,
            administrator.display_name,
            verified_user.display_name,
            verified_user.email,
        )


@router.post("/register", response_model=RegistrationRead, status_code=status.HTTP_201_CREATED)
def register_local_account(
    registration: LocalRegistrationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegistrationRead:
    email = str(registration.email).lower().strip()
    enforce_rate_limit(db, request, scope="register", subject=email, limit=5, window_seconds=3600)
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        if not existing.local_credential:
            delivered = _issue_password_setup(db, existing)
            if not delivered:
                record_event(
                    db,
                    action="email.password_setup_delivery_failed",
                    target_type="user",
                    target_id=existing.id,
                    outcome="failure",
                    correlation_id=request.headers.get("X-Correlation-ID"),
                )
        elif not existing.email_verified_at:
            _issue_verification(db, existing)
        return _pending_response()

    user = User(
        entra_tenant_id=None,
        entra_object_id=None,
        email=email,
        display_name=_normalise_name(registration.display_name),
        role=Role.STUDENT,
        is_active=False,
    )
    _validate_new_password(registration.password, email)
    user.local_credential = LocalCredential(password_hash=hash_password(registration.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    record_event(
        db,
        action="user.registration_requested",
        target_type="user",
        target_id=user.id,
        correlation_id=request.headers.get("X-Correlation-ID"),
        details={"provider": "local", "requested_role": "student"},
    )
    delivered = _issue_verification(db, user)
    if not delivered:
        record_event(
            db,
            action="email.verification_delivery_failed",
            target_type="user",
            target_id=user.id,
            outcome="failure",
            correlation_id=request.headers.get("X-Correlation-ID"),
        )
    return _pending_response()


@router.post("/login", response_model=TokenRead)
def login_local_account(
    login: LocalLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenRead:
    email = str(login.email).lower().strip()
    enforce_rate_limit(db, request, scope="login", subject=email, limit=30, window_seconds=900)
    user = db.scalar(select(User).where(User.email == email))
    password_hash = user.local_credential.password_hash if user and user.local_credential else None
    if not verify_password(password_hash, login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.email_verified_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before signing in",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is waiting for school administrator approval",
        )
    token, expires_in = create_local_access_token(user)
    return TokenRead(access_token=token, expires_in=expires_in)


@router.post(
    "/register-microsoft",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
def register_microsoft_account(
    request: Request,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> RegistrationRead:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Microsoft authentication is required")
    claims = claims_from_entra_token(credentials.credentials)
    tenant_id = str(claims["tid"]).lower()
    object_id = str(claims["oid"])
    existing = db.scalar(
        select(User).where(
            User.entra_tenant_id == tenant_id,
            User.entra_object_id == object_id,
        )
    )
    if existing:
        return _pending_response()

    raw_email = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
    try:
        email = str(email_adapter.validate_python(raw_email)).lower().strip()
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Microsoft did not provide a usable email address for registration",
        ) from exc
    user = db.scalar(select(User).where(User.email == email))
    invitation_accepted = bool(
        user and not user.entra_object_id and not user.local_credential and not user.is_active
    )
    if user and not invitation_accepted:
        raise HTTPException(
            status_code=409,
            detail="This email is already registered. Ask an administrator to link the account.",
        )
    if user:
        user.entra_tenant_id = tenant_id
        user.entra_object_id = object_id
        user.email_verified_at = datetime.now(UTC)
        db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.consumed_at.is_(None),
            )
            .values(consumed_at=datetime.now(UTC))
        )
    else:
        user = User(
            entra_tenant_id=tenant_id,
            entra_object_id=object_id,
            email=email,
            display_name=_normalise_name(
                str(claims.get("name") or email.split("@", maxsplit=1)[0])
            ),
            role=Role.STUDENT,
            is_active=False,
            email_verified_at=datetime.now(UTC),
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    record_event(
        db,
        action=(
            "user.invitation_accepted"
            if invitation_accepted
            else "user.registration_requested"
        ),
        target_type="user",
        target_id=user.id,
        correlation_id=request.headers.get("X-Correlation-ID"),
        details={"provider": "microsoft", "requested_role": user.role.value},
    )
    delivered = send_microsoft_registration_email(user.email, user.display_name)
    if not delivered:
        record_event(
            db,
            action="email.microsoft_registration_delivery_failed",
            target_type="user",
            target_id=user.id,
            outcome="failure",
            correlation_id=request.headers.get("X-Correlation-ID"),
        )
    _queue_admin_verification_alerts(db, background_tasks, user)
    return RegistrationRead(
        status="verified_pending_approval",
        message=(
            "Your Microsoft identity is verified. Check your email for confirmation; "
            "a school administrator must now assign and activate your database role."
        ),
    )


@router.post("/verify-email", response_model=RegistrationRead)
def verify_email(
    payload: TokenRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RegistrationRead:
    enforce_rate_limit(db, request, scope="verify-email", limit=10, window_seconds=3600)
    token = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_digest == _token_digest(payload.token)
        )
    )
    now = datetime.now(UTC)
    if not token or token.consumed_at or _utc(token.expires_at) <= now:
        raise HTTPException(status_code=400, detail="This verification link is invalid or expired")
    user = token.user
    user.email_verified_at = now
    db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    db.add(user)
    db.commit()
    record_event(
        db,
        action="user.email_verified",
        target_type="user",
        target_id=user.id,
        correlation_id=request.headers.get("X-Correlation-ID"),
    )
    _queue_admin_verification_alerts(db, background_tasks, user)
    return RegistrationRead(
        status="verified_pending_approval",
        message="Email verified. A school administrator must now approve your portal role.",
    )


@router.post("/resend-verification", response_model=RegistrationRead)
def resend_verification(
    payload: EmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegistrationRead:
    email = str(payload.email).lower().strip()
    enforce_rate_limit(
        db, request, scope="resend-verification", subject=email, limit=5, window_seconds=3600
    )
    user = db.scalar(select(User).where(User.email == email))
    if user and not user.local_credential:
        _issue_password_setup(db, user)
    elif user and not user.email_verified_at:
        _issue_verification(db, user)
    return RegistrationRead(
        status="accepted",
        message="If the account is eligible, a verification email is on its way.",
    )


@router.post("/forgot-password", response_model=RegistrationRead)
def forgot_password(
    payload: EmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegistrationRead:
    email = str(payload.email).lower().strip()
    enforce_rate_limit(
        db, request, scope="forgot-password", subject=email, limit=5, window_seconds=3600
    )
    user = db.scalar(select(User).where(User.email == email))
    if user and not user.local_credential:
        _issue_password_setup(db, user)
    elif user and user.email_verified_at:
        _issue_password_reset(db, user)
    if user:
        record_event(
            db,
            action="user.password_reset_requested",
            target_type="user",
            target_id=user.id,
            correlation_id=request.headers.get("X-Correlation-ID"),
        )
    return RegistrationRead(
        status="accepted",
        message="If a verified local account exists, a password-reset email is on its way.",
    )


@router.post("/reset-password", response_model=RegistrationRead)
def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RegistrationRead:
    enforce_rate_limit(db, request, scope="reset-password", limit=10, window_seconds=3600)
    token = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_digest == _token_digest(payload.token)
        )
    )
    now = datetime.now(UTC)
    if not token or token.consumed_at or _utc(token.expires_at) <= now:
        raise HTTPException(
            status_code=400, detail="This password-reset link is invalid or expired"
        )
    user = token.user
    is_setup = not user.local_credential
    _validate_new_password(payload.password, user.email)
    if is_setup:
        user.local_credential = LocalCredential(password_hash=hash_password(payload.password))
        user.email_verified_at = now
    else:
        user.local_credential.password_hash = hash_password(payload.password)
    user.auth_version += 1
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    db.add(user)
    db.commit()
    record_event(
        db,
        action="user.password_setup_completed" if is_setup else "user.password_reset_completed",
        target_type="user",
        target_id=user.id,
        correlation_id=request.headers.get("X-Correlation-ID"),
    )
    if is_setup:
        _queue_admin_verification_alerts(db, background_tasks, user)
    return RegistrationRead(
        status="password_setup" if is_setup else "password_reset",
        message=(
            "Your email is verified and your password is ready. You can now sign in."
            if is_setup
            else "Your password has been reset. You can now sign in."
        ),
    )


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
        "provider": "Microsoft Entra ID or MMAUG local account",
        "url": get_settings().password_reset_url,
        "message": (
            "Use Microsoft recovery for Microsoft accounts or Forgot password for "
            "local accounts."
        ),
    }
