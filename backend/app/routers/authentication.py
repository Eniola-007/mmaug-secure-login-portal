from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
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
from app.models import LocalCredential, Role, User
from app.schemas import (
    LocalLoginRequest,
    LocalRegistrationRequest,
    RegistrationRead,
    TokenRead,
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
            "Your account request has been received. A school administrator must assign and "
            "activate your database role before you can enter a dashboard."
        ),
    )


@router.post("/register", response_model=RegistrationRead, status_code=status.HTTP_201_CREATED)
def register_local_account(
    registration: LocalRegistrationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegistrationRead:
    email = str(registration.email).lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account already exists for this email")

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
    return _pending_response()


@router.post("/login", response_model=TokenRead)
def login_local_account(
    login: LocalLoginRequest,
    db: Session = Depends(get_db),
) -> TokenRead:
    email = str(login.email).lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    password_hash = user.local_credential.password_hash if user and user.local_credential else None
    if not verify_password(password_hash, login.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
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
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=409,
            detail="This email is already registered. Ask an administrator to link the account.",
        )

    user = User(
        entra_tenant_id=tenant_id,
        entra_object_id=object_id,
        email=email,
        display_name=_normalise_name(str(claims.get("name") or email.split("@", maxsplit=1)[0])),
        role=Role.STUDENT,
        is_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_event(
        db,
        action="user.registration_requested",
        target_type="user",
        target_id=user.id,
        correlation_id=request.headers.get("X-Correlation-ID"),
        details={"provider": "microsoft", "requested_role": "student"},
    )
    return _pending_response()


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
