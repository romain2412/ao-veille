"""Harmonise les colonnes tableau de `tenders` en text[].

Selon l'historique de la base, certaines colonnes tableau pouvaient être en
varchar[] (local) ou text[] (prod). Cette migration force toutes les colonnes
array de `tenders` en text[] pour avoir un schéma identique partout et éviter
les erreurs PostgreSQL "varchar[] @> text[]" lors du filtre par source.

Revision ID: 0002_arrays_text
Revises: 0001_initial
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_arrays_text"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ARRAY_COLUMNS = ("sources", "cpv_codes", "departments", "matched_keywords")


def upgrade() -> None:
    # Convertit chaque colonne en text[] (idempotent : si déjà text[], no-op réel).
    for col in ARRAY_COLUMNS:
        op.execute(
            f"ALTER TABLE tenders "
            f"ALTER COLUMN {col} TYPE text[] USING {col}::text[]"
        )


def downgrade() -> None:
    # Retour en varchar[] (type historique d'origine).
    for col in ARRAY_COLUMNS:
        op.execute(
            f"ALTER TABLE tenders "
            f"ALTER COLUMN {col} TYPE varchar[] USING {col}::varchar[]"
        )
