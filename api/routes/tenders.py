"""
Routes appels d'offres.

GET   /tenders              → liste paginée des AO pertinents
GET   /tenders/{id}         → détail d'un AO
PATCH /tenders/{id}/seen    → marquer comme vu
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.schemas import TenderListResponse, TenderResponse
from storage.database import TenderORM, UserORM

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=TenderListResponse)
async def list_tenders(
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Résultats par page"),
    only_new: bool = Query(False, description="Uniquement les non vus"),
    only_priority: bool = Query(False, description="Uniquement Nouvelle-Aquitaine"),
    min_score: int = Query(0, ge=0, description="Score minimum"),
    search: str | None = Query(None, description="Recherche dans le titre"),
    sources: str | None = Query(None, description="Sources séparées par virgule (ex: boamp,demat_ampa)"),
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_current_user),
):
    stmt = (
        select(TenderORM)
        .where(TenderORM.is_relevant == True)   # noqa: E712
        .where(TenderORM.score >= min_score)
    )

    if only_new:
        stmt = stmt.where(TenderORM.is_new == True)   # noqa: E712
    if only_priority:
        stmt = stmt.where(TenderORM.is_priority_region == True)   # noqa: E712
    if search:
        stmt = stmt.where(TenderORM.title.ilike(f"%{search}%"))
    if sources:
        # Filtre : l'AO doit contenir AU MOINS une des sources sélectionnées.
        # La colonne `sources` est de type varchar[] : on caste en ARRAY(String)
        # pour éviter l'erreur PostgreSQL "varchar[] @> text[]".
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
        if source_list:
            from sqlalchemy import String, cast, or_
            from sqlalchemy.dialects.postgresql import ARRAY
            stmt = stmt.where(
                or_(*[
                    TenderORM.sources.contains(cast([src], ARRAY(String)))
                    for src in source_list
                ])
            )

    # Compte total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Pagination + tri
    stmt = (
        stmt
        .order_by(
            TenderORM.is_priority_region.desc(),
            TenderORM.score.desc(),
            TenderORM.publication_date.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    results = (await db.execute(stmt)).scalars().all()

    return TenderListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=list(results),
    )


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_current_user),
):
    result = await db.execute(
        select(TenderORM).where(TenderORM.id == tender_id)
    )
    tender = result.scalar_one_or_none()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appel d'offres introuvable",
        )
    return tender


@router.patch("/{tender_id}/seen", response_model=TenderResponse)
async def mark_seen(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_current_user),
):
    """Marque un AO comme vu (is_new = False)."""
    result = await db.execute(
        select(TenderORM).where(TenderORM.id == tender_id)
    )
    tender = result.scalar_one_or_none()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appel d'offres introuvable",
        )

    await db.execute(
        update(TenderORM)
        .where(TenderORM.id == tender_id)
        .values(is_new=False)
    )
    await db.commit()
    await db.refresh(tender)
    return tender
