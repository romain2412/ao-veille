"""Table app_state : magasin clé/valeur pour l'état applicatif partagé.

Utilisé notamment pour exposer la date du prochain run planifié (écrite par
le collecteur, lue par l'API).

Revision ID: 0004_app_state
Revises: 0003_collection_runs
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_app_state"
down_revision: Union[str, None] = "0003_collection_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_state",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_state")
