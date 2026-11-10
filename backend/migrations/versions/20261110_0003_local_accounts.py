"""Add approved local account credentials.

Revision ID: 20261110_0003
Revises: 20261109_0002
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261110_0003"
down_revision: str | None = "20261109_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "entra_tenant_id", existing_type=sa.String(length=36), nullable=True)
    op.alter_column("users", "entra_object_id", existing_type=sa.String(length=64), nullable=True)
    op.create_table(
        "local_credentials",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("local_credentials")
    op.execute(
        sa.text("DELETE FROM users WHERE entra_tenant_id IS NULL OR entra_object_id IS NULL")
    )
    op.alter_column("users", "entra_object_id", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("users", "entra_tenant_id", existing_type=sa.String(length=36), nullable=False)
