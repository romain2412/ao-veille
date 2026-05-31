"""
Point d'entrée — collecteur de veille AO.

Usage :
  python main.py                              # toutes les sources au démarrage + scheduler
  python main.py --once                       # collecte unique toutes sources
  python main.py --start-sources boamp        # seulement BOAMP au démarrage (scheduler = toutes)
  python main.py --start-sources boamp,noalis # BOAMP + Noalis au démarrage
  python main.py --once --start-sources noalis # collecte unique uniquement Noalis
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config" / "settings.yml"


def load_settings() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


async def run_once(settings: dict, start_sources: list[str] | None = None) -> None:
    from scheduler.jobs import collect_and_score
    from storage.database import init_db
    await init_db()
    await collect_and_score(settings, sources_config={}, only_sources=start_sources)


async def run_daemon(settings: dict, start_sources: list[str] | None = None) -> None:
    from scheduler.jobs import build_scheduler, collect_and_score
    from storage.database import init_db

    await init_db()
    logger.info("Base de données prête.")

    if start_sources:
        logger.info("Collecte initiale limitée aux sources : %s", ", ".join(start_sources))
    else:
        logger.info("Collecte initiale sur toutes les sources...")

    await collect_and_score(settings, sources_config={}, only_sources=start_sources)

    # Le scheduler tourne toujours sur TOUTES les sources
    scheduler = build_scheduler(settings)
    scheduler.start()
    logger.info("Scheduler démarré (toutes les sources). Ctrl+C pour arrêter.")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Arrêt propre.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Veille AO — FB VRD")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Lance une collecte unique puis quitte",
    )
    parser.add_argument(
        "--start-sources",
        type=str,
        default=None,
        help=(
            "Sources à collecter au démarrage uniquement (séparées par des virgules). "
            "Ex : boamp,noalis — Le scheduler collecte toujours toutes les sources. "
            "Si omis : toutes les sources sont collectées au démarrage."
        ),
    )
    args = parser.parse_args()

    # Parser la liste des sources
    start_sources: list[str] | None = None
    if args.start_sources:
        start_sources = [s.strip() for s in args.start_sources.split(",") if s.strip()]

    settings = load_settings()

    if args.once:
        asyncio.run(run_once(settings, start_sources=start_sources))
    else:
        asyncio.run(run_daemon(settings, start_sources=start_sources))


if __name__ == "__main__":
    main()
