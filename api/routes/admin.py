"""
Routes d'administration / monitoring (réservées aux administrateurs).

GET /admin/monitoring → état du DERNIER run par source/collecteur :
  - status / error      : issue du dernier run
  - collected_count     : AO récupérés du site avant scoring
  - inserted_count      : AO ayant passé le score et insérés en base
  - started_at / finished_at / duration_seconds : horodatage et durée du run
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_admin_user, get_db
from storage.database import (
    AppStateORM, CollectionRequestORM, CollectionRunORM, UserORM,
)
from timeutils import as_utc, now_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/collect/{source}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_collection(
    source: str,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Demande une collecte manuelle d'une source.

    L'API n'exécute pas la collecte elle-même (elle n'a pas Playwright) : elle
    enregistre une demande (status=pending) que le collecteur traitera en
    arrière-plan. N'affecte pas le planning du scheduler ni next_collect_run.
    """
    from collector.registry import registry

    if source not in registry.all_names():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source inconnue : {source}",
        )

    # Évite d'empiler les demandes : réutilise celle en cours s'il y en a une
    existing = (await db.execute(
        select(CollectionRequestORM).where(
            CollectionRequestORM.source == source,
            CollectionRequestORM.status.in_(["pending", "processing"]),
        ).order_by(CollectionRequestORM.requested_at.desc()).limit(1)
    )).scalar_one_or_none()

    if existing is not None:
        return {"status": "requested", "source": source, "request_id": existing.id}

    req = CollectionRequestORM(source=source, status="pending")
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return {"status": "requested", "source": source, "request_id": req.id}


@router.post("/collect-all", status_code=status.HTTP_202_ACCEPTED)
async def trigger_collection_all(
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Demande une collecte manuelle de TOUTES les sources enregistrées.

    Crée une demande par source (en réutilisant celle déjà en cours s'il y en a),
    que le collecteur traitera en arrière-plan. Renvoie la liste des request_id.
    """
    from collector.registry import registry

    results = []
    for source in sorted(registry.all_names()):
        existing = (await db.execute(
            select(CollectionRequestORM).where(
                CollectionRequestORM.source == source,
                CollectionRequestORM.status.in_(["pending", "processing"]),
            ).order_by(CollectionRequestORM.requested_at.desc()).limit(1)
        )).scalar_one_or_none()

        if existing is not None:
            results.append({"source": source, "request_id": existing.id})
            continue

        req = CollectionRequestORM(source=source, status="pending")
        db.add(req)
        await db.flush()
        results.append({"source": source, "request_id": req.id})

    await db.commit()
    return {"status": "requested", "requests": results}


@router.get("/collect-status/{request_id}")
async def collection_status(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    """Statut d'une demande de collecte (pour le suivi côté admin)."""
    req = (await db.execute(
        select(CollectionRequestORM).where(CollectionRequestORM.id == request_id)
    )).scalar_one_or_none()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable"
        )
    return {
        "id": req.id,
        "source": req.source,
        "status": req.status,   # pending | processing | done | error
        "requested_at": as_utc(req.requested_at),
        "processed_at": as_utc(req.processed_at),
    }


@router.get("/monitoring")
async def monitoring(
    db: AsyncSession = Depends(get_db),
    _: UserORM = Depends(get_admin_user),
):
    from collector.registry import registry

    now = now_utc()
    sources = sorted(registry.all_names())
    result = []

    for src in sources:
        # Dernier run de cette source
        last_run = (await db.execute(
            select(CollectionRunORM)
            .where(CollectionRunORM.source == src)
            .order_by(CollectionRunORM.started_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        if last_run is None:
            result.append({"source": src, "last_run": None})
            continue

        # Durée du run en secondes (si terminé)
        duration = None
        if last_run.finished_at and last_run.started_at:
            duration = (last_run.finished_at - last_run.started_at).total_seconds()

        result.append({
            "source": src,
            "last_run": {
                "status": last_run.status,
                "error": last_run.error,
                "collected_count": last_run.collected_count,
                "inserted_count": last_run.inserted_count,
                # marquées UTC (suffixe de fuseau explicite dans le JSON)
                "started_at": as_utc(last_run.started_at),
                "finished_at": as_utc(last_run.finished_at),
                "duration_seconds": duration,
            },
        })

    # Date du prochain run planifié (écrite par le collecteur dans app_state)
    next_run_raw = (await db.execute(
        select(AppStateORM.value).where(AppStateORM.key == "next_collect_run")
    )).scalar_one_or_none()

    return {
        "sources": result,
        "generated_at": as_utc(now),
        "next_collect_run": next_run_raw,
    }
