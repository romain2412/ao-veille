"""
Couche base de données — SQLAlchemy async + PostgreSQL.
"""
from __future__ import annotations

import os

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://ao_user:ao_password@localhost:5432/ao_veille",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


class TenderORM(Base):
    """Table principale des appels d'offres."""

    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, autoincrement=True)

    uid = Column(String(128), unique=True, nullable=False, index=True)

    # --- Multi-source ---
    # source = source principale (première qui a trouvé l'AO)
    source = Column(String(64), nullable=False, index=True)
    source_id = Column(String(128), nullable=False)
    # sources = toutes les sources où cet AO a été trouvé
    sources = Column(ARRAY(String), nullable=False, default=[])
    # source_urls = {"boamp": "https://...", "demat_ampa": "https://..."}
    source_urls = Column(JSONB, nullable=True, default={})
    # fingerprint = hash pour détecter les doublons inter-sources
    fingerprint = Column(String(64), nullable=True, index=True)

    url = Column(Text, nullable=True)  # URL principale (source primaire)

    title = Column(Text, nullable=False)
    buyer_name = Column(Text, nullable=True)
    buyer_city = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    cpv_codes = Column(ARRAY(String), nullable=True, default=[])

    market_type = Column(String(32), nullable=True)
    notice_nature = Column(String(32), nullable=True)

    departments = Column(ARRAY(String), nullable=True, default=[])
    execution_location = Column(Text, nullable=True)

    publication_date = Column(DateTime, nullable=True, index=True)
    deadline = Column(DateTime, nullable=True)
    collected_at = Column(DateTime, server_default=func.now(), nullable=False)

    score = Column(Integer, default=0, index=True)
    matched_keywords = Column(ARRAY(String), nullable=True, default=[])
    is_priority_region = Column(Boolean, default=False, index=True)
    is_relevant = Column(Boolean, default=False, index=True)
    is_new = Column(Boolean, default=True, index=True)

    def __repr__(self) -> str:
        return f"<TenderORM uid={self.uid!r} score={self.score}>"


class UserORM(Base):
    """Table des utilisateurs (accès portail)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


async def init_db() -> None:
    """Crée les tables si elles n'existent pas."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """Dependency injection FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
