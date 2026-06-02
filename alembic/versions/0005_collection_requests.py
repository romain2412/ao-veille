"""Table collection_requests : file de demandes de collecte manuelle.

L'API (page admin) insère une demande (pending) ; le collecteur la traite.

Revision ID: 0005_collection_requests
Revises: 0004_app_state
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_collection_requests"
down_revision: Union[str, None] = "0004_app_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collection_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default="pending"),
        sa.Column("requested_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_requests_source", "collection_requests", ["source"])
    op.create_index("ix_collection_requests_status", "collection_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_collection_requests_status", table_name="collection_requests")
    op.drop_index("ix_collection_requests_source", table_name="collection_requests")
    op.drop_table("collection_requests")
