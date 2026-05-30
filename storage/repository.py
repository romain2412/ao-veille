"""
Repository — CRUD pour les appels d'offres.
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

    async def upsert(self, tender: Tender) -> tuple[TenderORM, bool]:
        """Insère ou met à jour. Retourne (orm, is_new)."""
        existing = await self._get_by_uid(tender.uid)

        if existing:
            await self.session.execute(
                update(TenderORM)
                .where(TenderORM.uid == tender.uid)
                .values(
                    score=tender.score,
                    matched_keywords=tender.matched_keywords,
                    is_relevant=tender.is_relevant,
                    is_priority_region=tender.is_priority_region,
                    deadline=tender.deadline,
                )
            )
            await self.session.commit()
            return existing, False

        orm = self._to_orm(tender)
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return orm, True

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
        """AO pertinents, triés par région prioritaire puis score."""
        stmt = (
            select(TenderORM)
            .where(TenderORM.is_relevant == True)   # noqa: E712
            .where(TenderORM.score >= min_score)
        )
        if only_new:
            stmt = stmt.where(TenderORM.is_new == True)  # noqa: E712
        stmt = stmt.order_by(
            TenderORM.is_priority_region.desc(),
            TenderORM.score.desc(),
            TenderORM.publication_date.desc(),
        ).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_new_since(self, since: datetime) -> list[TenderORM]:
        """AO pertinents collectés depuis `since` (pour rapports mail)."""
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

    async def _get_by_uid(self, uid: str) -> TenderORM | None:
        result = await self.session.execute(
            select(TenderORM).where(TenderORM.uid == uid)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _to_orm(t: Tender) -> TenderORM:
        return TenderORM(
            uid=t.uid,
            source=t.source,
            source_id=t.source_id,
            url=t.url,
            title=t.title,
            buyer_name=t.buyer_name,
            buyer_city=t.buyer_city,
            description=t.description,
            cpv_codes=t.cpv_codes,
            market_type=t.market_type,
            notice_nature=t.notice_nature,
            departments=t.departments,
            execution_location=t.execution_location,
            publication_date=t.publication_date,
            deadline=t.deadline,
            collected_at=t.collected_at,
            score=t.score,
            matched_keywords=t.matched_keywords,
            is_priority_region=t.is_priority_region,
            is_relevant=t.is_relevant,
            is_new=t.is_new,
        )
