import uuid

import jwt
import pytest
from sqlalchemy.orm import Session

from app.auth import _issuer_for_tenant, _tenant_id_from_claims
from app.enroll_users import enroll_users
from app.models import Role, User


def test_multitenant_issuer_is_bound_to_token_tenant() -> None:
    tenant_id = str(uuid.uuid4())
    assert _tenant_id_from_claims({"tid": tenant_id}) == tenant_id
    assert _issuer_for_tenant(tenant_id) == (f"https://login.microsoftonline.com/{tenant_id}/v2.0")


def test_non_guid_tenant_is_rejected() -> None:
    with pytest.raises(jwt.InvalidTokenError):
        _tenant_id_from_claims({"tid": "common"})


def test_enrollment_replaces_local_placeholder_by_email(db_session: Session) -> None:
    tenant_id = str(uuid.uuid4())
    object_id = str(uuid.uuid4())
    records = [
        {
            "entra_tenant_id": tenant_id,
            "entra_object_id": object_id,
            "email": "student1@mmaug.example",
            "display_name": "Amina Student",
            "role": Role.STUDENT,
            "is_active": True,
        }
    ]

    assert enroll_users(db_session, records) == 1
    user = db_session.query(User).filter_by(email="student1@mmaug.example").one()
    assert user.entra_tenant_id == tenant_id
    assert user.entra_object_id == object_id
