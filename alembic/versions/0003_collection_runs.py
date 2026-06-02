"""Table collection_runs : trace des exécutions de collecte (monitoring).

Une ligne par run et par source : statut, erreur éventuelle, volumes traités.

Revision ID: 0003_collection_runs
Revises: 0002_arrays_text
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_collection_runs"
down_revision: Union[str, None] = "0002_arrays_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default="success"),
        sa.Column("error", sa.Text(), nullable=True),
        # COLLECTÉ : AO récupérés du site avant scoring
        sa.Column("collected_count", sa.Integer(), nullable=False,
                  server_default="0"),
        # RÉCUPÉRÉ : AO ayant passé le score et insérés comme nouvelle entrée
        sa.Column("inserted_count", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_runs_source", "collection_runs", ["source"])


def downgrade() -> None:
    op.drop_index("ix_collection_runs_source", table_name="collection_runs")
    op.drop_table("collection_runs")
