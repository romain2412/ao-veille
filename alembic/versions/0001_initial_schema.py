"""Schéma initial : tables tenders et users (avec multi-source).

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("sources", postgresql.ARRAY(sa.String()), nullable=False,
                  server_default="{}"),
        sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True, server_default="{}"),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("buyer_name", sa.Text(), nullable=True),
        sa.Column("buyer_city", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cpv_codes", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("market_type", sa.String(length=32), nullable=True),
        sa.Column("notice_nature", sa.String(length=32), nullable=True),
        sa.Column("departments", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("execution_location", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.DateTime(), nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("collected_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("matched_keywords", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("is_priority_region", sa.Boolean(), nullable=True),
        sa.Column("is_relevant", sa.Boolean(), nullable=True),
        sa.Column("is_new", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenders_uid", "tenders", ["uid"], unique=True)
    op.create_index("ix_tenders_source", "tenders", ["source"])
    op.create_index("ix_tenders_fingerprint", "tenders", ["fingerprint"])
    op.create_index("ix_tenders_publication_date", "tenders", ["publication_date"])
    op.create_index("ix_tenders_score", "tenders", ["score"])
    op.create_index("ix_tenders_is_priority_region", "tenders", ["is_priority_region"])
    op.create_index("ix_tenders_is_relevant", "tenders", ["is_relevant"])
    op.create_index("ix_tenders_is_new", "tenders", ["is_new"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("tenders")
