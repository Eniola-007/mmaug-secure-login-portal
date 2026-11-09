"""Idempotently enroll Microsoft identities in the portal database."""

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Role, User

email_adapter = TypeAdapter(EmailStr)


def _guid(value: object, field_name: str) -> str:
    candidate = str(value).lower()
    try:
        parsed = uuid.UUID(candidate)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a GUID") from exc
    if str(parsed) != candidate:
        raise ValueError(f"{field_name} must use canonical GUID format")
    return candidate


def _record(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Each enrollment entry must be a JSON object")
    required = {"tenant_id", "object_id", "email", "display_name", "role"}
    missing = required.difference(raw)
    if missing:
        raise ValueError(f"Enrollment entry is missing: {', '.join(sorted(missing))}")
    return {
        "entra_tenant_id": _guid(raw["tenant_id"], "tenant_id"),
        "entra_object_id": _guid(raw["object_id"], "object_id"),
        "email": str(email_adapter.validate_python(raw["email"])).lower(),
        "display_name": str(raw["display_name"]).strip(),
        "role": Role(str(raw["role"]).lower()),
        "is_active": bool(raw.get("is_active", True)),
    }


def load_enrollments(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Enrollment file must contain a non-empty JSON array")
    return [_record(item) for item in payload]


def enroll_users(db: Session, records: list[dict[str, Any]]) -> int:
    changed = 0
    for record in records:
        by_identity = db.scalar(
            select(User).where(
                User.entra_tenant_id == record["entra_tenant_id"],
                User.entra_object_id == record["entra_object_id"],
            )
        )
        by_email = db.scalar(select(User).where(User.email == record["email"]))
        if by_identity and by_email and by_identity.id != by_email.id:
            raise ValueError(f"Identity and email resolve to different users: {record['email']}")

        user = by_identity or by_email
        if user is None:
            user = User(**record)
            db.add(user)
        else:
            for field, value in record.items():
                setattr(user, field, value)
        db.flush()
        changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enroll Microsoft work, school, guest, or personal accounts."
    )
    parser.add_argument("--file", required=True, type=Path, help="Path to enrollment JSON")
    parser.add_argument("--dry-run", action="store_true", help="Validate and roll back changes")
    args = parser.parse_args()

    records = load_enrollments(args.file)
    with SessionLocal() as db:
        changed = enroll_users(db, records)
        if args.dry_run:
            db.rollback()
            print(f"Validated {changed} enrollment records; no changes committed.")
        else:
            db.commit()
            print(f"Enrolled or updated {changed} portal users.")


if __name__ == "__main__":
    main()
