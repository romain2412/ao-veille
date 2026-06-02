"""
Routes appels d'offres.

GET   /tenders              → liste paginée des AO pertinents
GET   /tenders/{id}         → détail d'un AO
PATCH /tenders/{id}/seen    → marquer comme vu
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Text, cast, func, or_, select, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.schemas import TenderListResponse, TenderResponse
from storage.database import TenderORM, UserORM
from timeutils import now_utc

router = APIRouter(prefix="/tenders", tags=["tenders"])


def _source_in(source: str):
    """Filtre : AO où `source` figure dans la colonne multi-source `sources`.

    Caste les deux côtés en text[] pour être robuste au type réel de la colonne
    (varchar[] ou text[] selon l'historique de la base).
    """
    return cast(TenderORM.sources, ARRAY(Text)).contains(cast([source], ARRAY(Text)))


def _not_expired():
    """AO non expiré : deadline absente ou dans le futur."""
    return or_(TenderORM.deadline.is_(None), TenderORM.deadline >= now_utc())


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
        .where(_not_expired())   # on n'affiche que les AO non expirés
    )

    if only_new:
        stmt = stmt.where(TenderORM.is_new == True)   # noqa: E712
    if only_priority:
        stmt = stmt.where(TenderORM.is_priority_region == True)   # noqa: E712
    if search:
        stmt = stmt.where(TenderORM.title.ilike(f"%{search}%"))
    if sources:
        # L'AO doit contenir AU MOINS une des sources sélectionnées.
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
        if source_list:
            stmt = stmt.where(or_(*[_source_in(src) for src in source_list]))

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


@router.get("/stats")
async def tenders_stats(
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_current_user),
):
    """Stats par source pour le bandeau de la page appli (AO non expirés) :
      - seen_count   : déjà vus (is_new = False)
      - unseen_count : pas encore vus (is_new = True)
    """
    from collector.registry import registry

    not_expired = _not_expired()
    sources = sorted(registry.all_names())
    result = []
    total_seen = 0
    total_unseen = 0

    for src in sources:
        in_src = _source_in(src)
        seen = (await db.execute(
            select(func.count()).select_from(TenderORM).where(
                in_src, not_expired, TenderORM.is_new == False  # noqa: E712
            )
        )).scalar_one()
        unseen = (await db.execute(
            select(func.count()).select_from(TenderORM).where(
                in_src, not_expired, TenderORM.is_new == True  # noqa: E712
            )
        )).scalar_one()
        result.append({"source": src, "seen_count": seen, "unseen_count": unseen})
        total_seen += seen
        total_unseen += unseen

    return {
        "sources": result,
        "total_seen": total_seen,
        "total_unseen": total_unseen,
    }


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
