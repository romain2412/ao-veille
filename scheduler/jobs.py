"""
Tâches planifiées — APScheduler (AsyncIOScheduler).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


async def collect_and_score(settings: dict, sources_config: dict) -> None:
    """Pipeline : collecte → scoring → persistance."""
    from collector.registry import registry
    from processor.scorer import TenderScorer
    from storage.database import AsyncSessionLocal
    from storage.repository import TenderRepository

    lookback_days = settings.get("collection", {}).get("lookback_days", 3)
    since = datetime.utcnow() - timedelta(days=lookback_days)

    scorer = TenderScorer(settings)
    sources = registry.build_all(sources_config)

    new_count = 0
    total_count = 0

    async with AsyncSessionLocal() as session:
        repo = TenderRepository(session)
        for source in sources:
            logger.info("[job] Collecte %s depuis %s…", source.name, since.date())
            try:
                async for tender in source.fetch(since):
                    total_count += 1
                    scored = scorer.score(tender)
                    if scored.is_relevant:
                        _, is_new = await repo.upsert(scored)
                        if is_new:
                            new_count += 1
            except Exception as exc:
                logger.exception("[job] Erreur source %s: %s", source.name, exc)

    logger.info(
        "[job] Terminé : %d AO traités, %d nouveaux pertinents",
        total_count, new_count,
    )


async def send_report(settings: dict) -> None:
    """Rapport mail des nouveaux AO (si notifications activées)."""
    if not settings.get("notifications", {}).get("enabled", False):
        return

    frequency_h = settings.get("notifications", {}).get("frequency_hours", 24)
    since = datetime.utcnow() - timedelta(hours=frequency_h)

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

    logger.info("Scheduler: collecte /%dh, rapport /%dh", collect_hours, notify_hours)
    return scheduler
