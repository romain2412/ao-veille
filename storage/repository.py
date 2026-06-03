"""
Repository — CRUD pour les appels d'offres avec gestion multi-source.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.tender import Tender
from storage.database import TenderORM

logger = logging.getLogger(__name__)


class TenderRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, tender: Tender) -> tuple[TenderORM, str]:
        """
        Insère ou met à jour un Tender avec gestion multi-source.

        Logique :
        1. Cherche par uid (même source, même id) → update si changé
        2. Sinon cherche par fingerprint (même AO, source différente)
           → fusionne la source dans l'enregistrement existant si changé
        3. Sinon → insert nouvelle entrée

        Retourne (orm, status) où status ∈ {"inserted", "updated", "unchanged"}.
        """
        # Calcul du fingerprint
        fingerprint = tender.compute_fingerprint()

        # --- Cas 1 : même uid (même source) ---
        existing = await self._get_by_uid(tender.uid)
        if existing:
            changed = await self._update_score(existing, tender)
            return existing, ("updated" if changed else "unchanged")

        # --- Cas 2 : même fingerprint (AO vu dans une autre source) ---
        if fingerprint:
            duplicate = await self._get_by_fingerprint(fingerprint)
            if duplicate:
                changed = await self._merge_source(duplicate, tender)
                if changed:
                    logger.info(
                        "[repo] AO fusionné : fingerprint=%s sources=%s+%s",
                        fingerprint, duplicate.source, tender.source,
                    )
                return duplicate, ("updated" if changed else "unchanged")

        # --- Cas 3 : nouvel AO ---
        sources = [tender.source]
        source_urls = {}
        if tender.url:
            source_urls[tender.source] = tender.url

        orm = TenderORM(
            uid=tender.uid,
            source=tender.source,
            source_id=tender.source_id,
            sources=sources,
            source_urls=source_urls,
            fingerprint=fingerprint,
            url=tender.url,
            title=tender.title,
            buyer_name=tender.buyer_name,
            buyer_city=tender.buyer_city,
            description=tender.description,
            cpv_codes=tender.cpv_codes,
            market_type=tender.market_type,
            notice_nature=tender.notice_nature,
            departments=tender.departments,
            execution_location=tender.execution_location,
            publication_date=tender.publication_date,
            deadline=tender.deadline,
            collected_at=tender.collected_at,
            score=tender.score,
            matched_keywords=tender.matched_keywords,
            is_priority_region=tender.is_priority_region,
            is_relevant=tender.is_relevant,
            is_new=tender.is_new,
        )
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return orm, "inserted"

    async def mark_seen(self, uid: str) -> None:
        await self.session.execute(
            update(TenderORM).where(TenderORM.uid == uid).values(is_new=False)
        )
        await self.session.commit()

    async def get_relevant(
        self,
        min_score: int = 0,
        only_new: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> list[TenderORM]:
        stmt = (
            select(TenderORM)
            .where(TenderORM.is_relevant == True)   # noqa: E712
            .where(TenderORM.score >= min_score)
        )
        if only_new:
            stmt = stmt.where(TenderORM.is_new == True)   # noqa: E712
        stmt = stmt.order_by(
            TenderORM.is_priority_region.desc(),
            TenderORM.score.desc(),
            TenderORM.publication_date.desc(),
        ).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_new_since(self, since: datetime) -> list[TenderORM]:
        stmt = (
            select(TenderORM)
            .where(TenderORM.is_relevant == True)   # noqa: E712
            .where(TenderORM.collected_at >= since)
            .order_by(TenderORM.score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def exists(self, uid: str) -> bool:
        result = await self.session.execute(
            select(TenderORM.uid).where(TenderORM.uid == uid)
        )
        return result.scalar() is not None

    # ------------------------------------------------------------------
    # Privé
    # ------------------------------------------------------------------

    async def _get_by_uid(self, uid: str) -> TenderORM | None:
        result = await self.session.execute(
            select(TenderORM).where(TenderORM.uid == uid)
        )
        return result.scalar_one_or_none()

    async def _get_by_fingerprint(self, fingerprint: str) -> TenderORM | None:
        result = await self.session.execute(
            select(TenderORM).where(TenderORM.fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()

    async def _update_score(self, orm: TenderORM, tender: Tender) -> bool:
        """Met à jour un AO existant si des champs ont changé.

        Retourne True si au moins un champ a réellement changé (update effectué),
        False si l'AO est identique (aucune écriture).
        """
        changed = (
            orm.score != tender.score
            or list(orm.matched_keywords or []) != list(tender.matched_keywords or [])
            or orm.is_relevant != tender.is_relevant
            or orm.is_priority_region != tender.is_priority_region
            or orm.deadline != tender.deadline
        )
        if not changed:
            return False

        await self.session.execute(
            update(TenderORM)
            .where(TenderORM.uid == orm.uid)
            .values(
                score=tender.score,
                matched_keywords=tender.matched_keywords,
                is_relevant=tender.is_relevant,
                is_priority_region=tender.is_priority_region,
                deadline=tender.deadline,
            )
        )
        await self.session.commit()
        return True

    async def _merge_source(self, orm: TenderORM, tender: Tender) -> bool:
        """Fusionne une nouvelle source dans un AO existant.

        Retourne True si la fusion modifie réellement l'enregistrement,
        False si rien ne change (source déjà présente, score/mots-clés identiques).
        """
        current_sources = list(orm.sources or [])
        current_urls = dict(orm.source_urls or {})

        new_sources = list(current_sources)
        if tender.source not in new_sources:
            new_sources.append(tender.source)
        new_urls = dict(current_urls)
        if tender.url:
            new_urls[tender.source] = tender.url

        new_score = max(orm.score, tender.score)
        new_keywords = list(set((orm.matched_keywords or []) + tender.matched_keywords))
        new_relevant = orm.is_relevant or tender.is_relevant

        changed = (
            new_sources != current_sources
            or new_urls != current_urls
            or new_score != orm.score
            or set(new_keywords) != set(orm.matched_keywords or [])
            or new_relevant != orm.is_relevant
        )
        if not changed:
            return False

        await self.session.execute(
            update(TenderORM)
            .where(TenderORM.id == orm.id)
            .values(
                sources=new_sources,
                source_urls=new_urls,
                score=new_score,
                matched_keywords=new_keywords,
                is_relevant=new_relevant,
            )
        )
        await self.session.commit()
        return True
