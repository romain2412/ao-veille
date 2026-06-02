"""
Tâches planifiées — APScheduler (AsyncIOScheduler).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from timeutils import now_utc

logger = logging.getLogger(__name__)


async def collect_and_score(
    settings: dict,
    sources_config: dict,
    only_sources: list[str] | None = None,
) -> None:
    """
    Pipeline : collecte → scoring → persistance.

    Parameters
    ----------
    only_sources:
        Si fourni, seules les sources listées sont collectées.
        Si None (défaut), toutes les sources enregistrées sont collectées.
    """
    from collector.registry import registry
    from processor.scorer import TenderScorer
    from storage.database import AsyncSessionLocal, CollectionRunORM
    from storage.repository import TenderRepository

    lookback_days = settings.get("collection", {}).get("lookback_days", 3)
    since = now_utc() - timedelta(days=lookback_days)

    scorer = TenderScorer(settings)
    all_sources = registry.build_all(sources_config)

    # Filtrer les sources si demandé
    if only_sources:
        sources = [s for s in all_sources if s.name in only_sources]
        skipped = [s.name for s in all_sources if s.name not in only_sources]
        if skipped:
            logger.info("[job] Sources ignorées au démarrage : %s", ", ".join(skipped))
    else:
        sources = all_sources

    grand_total = 0
    grand_new = 0

    async with AsyncSessionLocal() as session:
        repo = TenderRepository(session)
        for source in sources:
            logger.info("[job] Collecte %s depuis %s…", source.name, since.date())
            # Un run de monitoring par source
            run = CollectionRunORM(source=source.name, started_at=now_utc())
            src_total = 0
            src_new = 0
            try:
                async for tender in source.fetch(since):
                    src_total += 1
                    scored = scorer.score(tender)
                    if scored.is_relevant:
                        _, is_new = await repo.upsert(scored)
                        if is_new:
                            src_new += 1
                run.status = "success"
                run.error = None
            except Exception as exc:
                logger.exception("[job] Erreur source %s: %s", source.name, exc)
                run.status = "error"
                run.error = str(exc)[:2000]
            finally:
                run.collected_count = src_total
                run.inserted_count = src_new
                run.finished_at = now_utc()
                session.add(run)
                await session.commit()
                grand_total += src_total
                grand_new += src_new

    logger.info(
        "[job] Terminé : %d AO traités, %d nouveaux pertinents",
        grand_total, grand_new,
    )


async def send_report(settings: dict) -> None:
    """Rapport mail des nouveaux AO (si notifications activées)."""
    if not settings.get("notifications", {}).get("enabled", False):
        return

    frequency_h = settings.get("notifications", {}).get("frequency_hours", 24)
    since = now_utc() - timedelta(hours=frequency_h)

    from storage.database import AsyncSessionLocal
    from storage.repository import TenderRepository

    async with AsyncSessionLocal() as session:
        repo = TenderRepository(session)
        new_tenders = await repo.get_new_since(since)

    if not new_tenders:
        logger.info("[job] Aucun nouvel AO à signaler.")
        return

    logger.info("[job] %d AO à envoyer par mail.", len(new_tenders))
    # TODO: appeler notifier/mailer.py


async def _set_app_state(key: str, value: str) -> None:
    """Écrit une valeur dans le magasin clé/valeur app_state (upsert)."""
    from sqlalchemy.dialects.postgresql import insert
    from storage.database import AppStateORM, AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        stmt = insert(AppStateORM).values(
            key=key, value=value, updated_at=now_utc()
        ).on_conflict_do_update(
            index_elements=["key"],
            set_={"value": value, "updated_at": now_utc()},
        )
        await session.execute(stmt)
        await session.commit()


async def save_next_collect_run(scheduler: AsyncIOScheduler) -> None:
    """Persiste la date du prochain run planifié de la collecte (clé app_state).

    Lu par l'API pour l'afficher dans la page admin.
    """
    job = scheduler.get_job("collect_and_score")
    nrt = getattr(job, "next_run_time", None) if job else None
    if nrt is not None:
        # Stocké en ISO 8601 avec fuseau (next_run_time est aware)
        await _set_app_state("next_collect_run", nrt.isoformat())


def build_scheduler(settings: dict, sources_config: dict | None = None) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    collect_hours = settings.get("collection", {}).get("frequency_hours", 12)
    scheduler.add_job(
        collect_and_score,
        trigger=IntervalTrigger(hours=collect_hours),
        kwargs={"settings": settings, "sources_config": sources_config or {}},
        id="collect_and_score",
        name="Collecte & scoring des AO",
        replace_existing=True,
        max_instances=1,
    )

    notify_hours = settings.get("notifications", {}).get("frequency_hours", 24)
    scheduler.add_job(
        send_report,
        trigger=IntervalTrigger(hours=notify_hours),
        kwargs={"settings": settings},
        id="send_report",
        name="Rapport mail AO",
        replace_existing=True,
    )

    # Rafraîchit la date du prochain run en base après chaque exécution du job.
    from apscheduler.events import EVENT_JOB_EXECUTED

    def _on_job_executed(event):
        if event.job_id == "collect_and_score":
            import asyncio
            asyncio.create_task(save_next_collect_run(scheduler))

    scheduler.add_listener(_on_job_executed, EVENT_JOB_EXECUTED)

    logger.info("Scheduler: collecte /%dh, rapport /%dh", collect_hours, notify_hours)
    return scheduler
