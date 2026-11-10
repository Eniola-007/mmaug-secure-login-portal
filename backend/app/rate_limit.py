import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuthRateLimit


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _client_address(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",", maxsplit=1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def enforce_rate_limit(
    db: Session,
    request: Request,
    *,
    scope: str,
    subject: str = "",
    limit: int,
    window_seconds: int,
) -> None:
    secret = get_settings().local_auth_jwt_secret.get_secret_value().encode()
    raw_key = f"{scope}|{_client_address(request)}|{subject.casefold()}".encode()
    key_hash = hmac.new(secret, raw_key, hashlib.sha256).hexdigest()
    now = datetime.now(UTC)
    window = timedelta(seconds=window_seconds)
    db.execute(delete(AuthRateLimit).where(AuthRateLimit.updated_at < now - timedelta(days=2)))
    row = db.scalar(
        select(AuthRateLimit).where(AuthRateLimit.key_hash == key_hash).with_for_update()
    )

    if row is None:
        db.add(AuthRateLimit(key_hash=key_hash, window_started_at=now, attempts=1))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            enforce_rate_limit(
                db,
                request,
                scope=scope,
                subject=subject,
                limit=limit,
                window_seconds=window_seconds,
            )
        return

    started = _utc(row.window_started_at)
    blocked_until = _utc(row.blocked_until) if row.blocked_until else None
    if blocked_until and blocked_until > now:
        retry_after = max(1, int((blocked_until - now).total_seconds()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    if now - started >= window:
        row.window_started_at = now
        row.attempts = 1
        row.blocked_until = None
    else:
        row.attempts += 1
        if row.attempts > limit:
            row.blocked_until = started + window
            db.add(row)
            db.commit()
            retry_after = max(1, int((row.blocked_until - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )
    db.add(row)
    db.commit()
