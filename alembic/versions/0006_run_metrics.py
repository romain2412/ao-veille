"""Ajoute des métriques de run : score_validated_count et updated_count.

Revision ID: 0006_run_metrics
Revises: 0005_collection_requests
Create Date: 2026-06-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_run_metrics"
down_revision: Union[str, None] = "0005_collection_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "collection_runs",
        sa.Column("score_validated_count", sa.Integer(), nullable=False,
                  server_default="0"),
    )
    op.add_column(
        "collection_runs",
        sa.Column("updated_count", sa.Integer(), nullable=False,
                  server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("collection_runs", "updated_count")
    op.drop_column("collection_runs", "score_validated_count")
