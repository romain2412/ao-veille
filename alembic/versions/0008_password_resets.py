"""Table password_resets : réinitialisation de mot de passe par lien email.

Revision ID: 0008_password_resets
Revises: 0007_invitations
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008_password_resets"
down_revision: Union[str, None] = "0007_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_resets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_resets_token", "password_resets",
                    ["token"], unique=True)
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")
    op.drop_index("ix_password_resets_token", table_name="password_resets")
    op.drop_table("password_resets")
