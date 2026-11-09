import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Role, User

bearer = HTTPBearer(auto_error=False)


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


def _claims_from_token(token: str) -> dict:
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


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_dev_user: str | None = Header(default=None, alias="X-Dev-User"),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    lookup_column = User.entra_object_id
    lookup_value: str | None = None
    tenant_id: str | None = None

    if settings.allow_dev_auth and settings.environment in {"development", "test"} and x_dev_user:
        lookup_column = User.email
        lookup_value = x_dev_user.lower().strip()
    elif credentials and credentials.scheme.lower() == "bearer":
        claims = _claims_from_token(credentials.credentials)
        tenant_id = str(claims["tid"]).lower()
        lookup_value = str(claims["oid"])
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if lookup_column is User.entra_object_id:
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
