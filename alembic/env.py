"""Environnement Alembic — migrations synchrones (psycopg2-style via asyncpg→sync).

On réutilise les métadonnées des modèles SQLAlchemy (storage.database.Base)
pour l'autogénération, et l'URL est lue depuis DATABASE_URL.

Note : l'application utilise asyncpg (driver async). Alembic, lui, tourne en
mode synchrone ; on convertit donc l'URL `postgresql+asyncpg://` en
`postgresql://` (psycopg2) le temps des migrations.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Rendre le package applicatif importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from storage.database import Base  # noqa: E402
import models.tender  # noqa: F401,E402  (enregistre les modèles sur Base)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://ao_user:ao_password@localhost:5432/ao_veille",
    )
    # Alembic tourne en synchrone : on retire le driver async.
    return url.replace("+asyncpg", "").replace("+psycopg2", "")


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
