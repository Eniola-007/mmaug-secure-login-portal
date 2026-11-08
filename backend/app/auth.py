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


def _claims_from_token(token: str) -> dict:
    settings = get_settings()
    if not settings.entra_api_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft Entra authentication is not configured",
        )
    try:
        signing_key = PyJWKClient(settings.jwks_url, cache_jwk_set=True).get_signing_key_from_jwt(
            token
        )
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_api_client_id,
            issuer=settings.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "oid"]},
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

    if settings.allow_dev_auth and settings.environment in {"development", "test"} and x_dev_user:
        lookup_column = User.email
        lookup_value = x_dev_user.lower().strip()
    elif credentials and credentials.scheme.lower() == "bearer":
        claims = _claims_from_token(credentials.credentials)
        lookup_value = str(claims["oid"])
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(User).where(lookup_column == lookup_value))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not enrolled in this portal",
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
