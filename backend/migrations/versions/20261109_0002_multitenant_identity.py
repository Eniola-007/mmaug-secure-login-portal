"""Use tenant and object ID as the Entra identity key.

Revision ID: 20261109_0002
Revises: 20261108_0001
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_0002"
down_revision: str | None = "20261108_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HOME_TENANT_ID = "71beefd7-29f4-4b9e-9cb2-e78b5dc851ad"


def upgrade() -> None:
    op.add_column("users", sa.Column("entra_tenant_id", sa.String(length=36), nullable=True))
    op.execute(
        sa.text(
            "UPDATE users SET entra_tenant_id = :tenant_id WHERE entra_tenant_id IS NULL"
        ).bindparams(tenant_id=HOME_TENANT_ID)
    )
    op.alter_column("users", "entra_tenant_id", nullable=False)
    op.drop_index(op.f("ix_users_entra_object_id"), table_name="users")
    op.create_index(op.f("ix_users_entra_object_id"), "users", ["entra_object_id"], unique=False)
    op.create_index(op.f("ix_users_entra_tenant_id"), "users", ["entra_tenant_id"], unique=False)
    op.create_unique_constraint(
        "uq_users_entra_identity",
        "users",
        ["entra_tenant_id", "entra_object_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_entra_identity", "users", type_="unique")
    op.drop_index(op.f("ix_users_entra_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_users_entra_object_id"), table_name="users")
    op.create_index(op.f("ix_users_entra_object_id"), "users", ["entra_object_id"], unique=True)
    op.drop_column("users", "entra_tenant_id")
