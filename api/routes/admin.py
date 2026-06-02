"""
Routes d'administration / monitoring (réservées aux administrateurs).

GET /admin/monitoring → état du DERNIER run par source/collecteur :
  - status / error      : issue du dernier run
  - collected_count     : AO récupérés du site avant scoring
  - inserted_count      : AO ayant passé le score et insérés en base
  - started_at / finished_at / duration_seconds : horodatage et durée du run
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_admin_user, get_db
from storage.database import CollectionRunORM, UserORM
from timeutils import as_utc, now_utc

router = APIRouter(prefix="/admin", tags=["admin"])


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

    return {"sources": result, "generated_at": as_utc(now)}
