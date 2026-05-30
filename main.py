"""
Point d'entrée — collecteur de veille AO.

Usage :
  python main.py          # démarre en mode démon (scheduler continu)
  python main.py --once   # une seule collecte puis quitte
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
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


async def run_once(settings: dict) -> None:
    from scheduler.jobs import collect_and_score
    from storage.database import init_db
    await init_db()
    await collect_and_score(settings, sources_config={})


async def run_daemon(settings: dict) -> None:
    from scheduler.jobs import build_scheduler, collect_and_score
    from storage.database import init_db

    await init_db()
    logger.info("Base de données prête.")

    logger.info("Collecte initiale au démarrage…")
    await collect_and_score(settings, sources_config={})

    scheduler = build_scheduler(settings)
    scheduler.start()
    logger.info("Scheduler démarré. Ctrl+C pour arrêter.")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Arrêt propre.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Veille AO — FB VRD")
    parser.add_argument("--once", action="store_true", help="Collecte unique")
    args = parser.parse_args()

    settings = load_settings()

    if args.once:
        asyncio.run(run_once(settings))
    else:
        asyncio.run(run_daemon(settings))


if __name__ == "__main__":
    main()
