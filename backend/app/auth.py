import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Role, User

bearer = HTTPBearer(auto_error=False)
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
LOCAL_ISSUER = "mmaug-local"
LOCAL_AUDIENCE = "mmaug-api"
_DUMMY_PASSWORD_HASH = password_hasher.hash("mmaug-login-timing-sentinel")


def _tenant_id_from_claims(claims: dict) -> str:
    tenant_id = str(claims.get("tid", "")).lower()
    try:
        parsed = uuid.UUID(tenant_id)
    except ValueError as exc:
        raise jwt.InvalidTokenError("Token tenant ID is not a GUID") from exc
    if str(parsed) != tenant_id:
        raise jwt.InvalidTokenError("Token tenant ID is not canonical")
    return tenant_id


def _issuer_for_tenant(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}/v2.0"


def _validate_signing_key_issuer(signing_key: object, tenant_id: str) -> None:
    key_data = getattr(signing_key, "_jwk_data", {})
    key_issuer = key_data.get("issuer") if isinstance(key_data, dict) else None
    if not key_issuer:
        return
    expected = _issuer_for_tenant(tenant_id)
    if str(key_issuer).replace("{tenantid}", tenant_id) != expected:
        raise jwt.InvalidIssuerError("Signing key issuer does not match token tenant")


def claims_from_entra_token(token: str) -> dict:
    settings = get_settings()
    if not settings.entra_api_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft Entra authentication is not configured",
        )
    try:
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
        tenant_id = _tenant_id_from_claims(unverified_claims)
        expected_issuer = _issuer_for_tenant(tenant_id)
        signing_key = PyJWKClient(settings.jwks_url, cache_jwk_set=True).get_signing_key_from_jwt(
            token
        )
        _validate_signing_key_issuer(signing_key, tenant_id)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_api_client_id,
            issuer=expected_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "oid", "tid"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    scopes = set(str(claims.get("scp", "")).split())
    if settings.entra_required_scope and settings.entra_required_scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Required API scope is missing",
        )
    return claims


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    candidate = password_hash or _DUMMY_PASSWORD_HASH
    try:
        valid = password_hasher.verify(candidate, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    return bool(valid and password_hash)


def create_local_access_token(user: User) -> tuple[str, int]:
    settings = get_settings()
    secret = settings.local_auth_jwt_secret.get_secret_value()
    if len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local account sign-in is not configured",
        )
    now = datetime.now(UTC)
    expires_in = settings.local_auth_token_minutes * 60
    token = jwt.encode(
        {
            "sub": str(user.id),
            "iss": LOCAL_ISSUER,
            "aud": LOCAL_AUDIENCE,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "token_kind": "local_access",
            "auth_version": user.auth_version,
        },
        secret,
        algorithm="HS256",
    )
    return token, expires_in


def _local_token_identity(token: str) -> tuple[uuid.UUID, int]:
    secret = get_settings().local_auth_jwt_secret.get_secret_value()
    if len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local account sign-in is not configured",
        )
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=LOCAL_AUDIENCE,
            issuer=LOCAL_ISSUER,
            options={"require": ["sub", "exp", "iat", "iss", "aud", "token_kind"]},
        )
        if claims["token_kind"] != "local_access":  # noqa: S105 - JWT type, not a secret
            raise jwt.InvalidTokenError("Unexpected token kind")
        return uuid.UUID(str(claims["sub"])), int(claims.get("auth_version", -1))
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _is_local_token(token: str) -> bool:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return False
    return claims.get("iss") == LOCAL_ISSUER


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_dev_user: str | None = Header(default=None, alias="X-Dev-User"),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    lookup_column = User.entra_object_id
    lookup_value: str | None = None
    tenant_id: str | None = None
    local_user_id: uuid.UUID | None = None
    local_auth_version: int | None = None

    if settings.allow_dev_auth and settings.environment in {"development", "test"} and x_dev_user:
        lookup_column = User.email
        lookup_value = x_dev_user.lower().strip()
    elif credentials and credentials.scheme.lower() == "bearer":
        if _is_local_token(credentials.credentials):
            local_user_id, local_auth_version = _local_token_identity(credentials.credentials)
        else:
            claims = claims_from_entra_token(credentials.credentials)
            tenant_id = str(claims["tid"]).lower()
            lookup_value = str(claims["oid"])
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if local_user_id is not None:
        user = db.get(User, local_user_id)
    elif lookup_column is User.entra_object_id:
        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token tenant is missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db.scalar(
            select(User).where(
                User.entra_tenant_id == tenant_id,
                User.entra_object_id == lookup_value,
            )
        )
    else:
        user = db.scalar(select(User).where(lookup_column == lookup_value))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "account_not_enrolled",
                "message": (
                    "Microsoft sign-in succeeded, but this account is not enrolled in the "
                    "MMAUG portal. Give the enrollment reference below to a portal administrator."
                ),
                "tenant_id": tenant_id,
                "object_id": lookup_value,
            },
        )
    if local_user_id is not None and user.auth_version != local_auth_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This session is no longer valid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal access is inactive",
        )
    return user


def require_roles(*allowed: Role) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not permitted to access this resource",
            )
        return user

    return dependency
