"""
Collecteur demat-ampa.fr (Portail marchés publics AMPA)

Structure DOM inspectée le 2026-05-31 :
  - Conteneur AO  : div.item_consultation
  - Référence     : input[name*="refCons"] → value
  - Titre         : div.small.pull-left.truncate span[data-original-title]
  - Catégorie     : div.cons_categorie span
  - Date limite   : div.date.date-min (day / month / year)
  - URL détail    : /?page=Entreprise.EntrepriseDetailConsultation&refCons=<ref>
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import AsyncGenerator

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender

logger = logging.getLogger(__name__)

BASE_URL = "https://demat-ampa.fr/entreprise/"
SEARCH_URL = BASE_URL + "?page=Entreprise.EntrepriseAdvancedSearch&AllCons"
DETAIL_URL = BASE_URL + "?page=Entreprise.EntrepriseDetailConsultation&refCons={ref}"

SEARCH_KEYWORDS = ["VRD", "voirie", "assainissement", "paysage", "espaces+verts"]

MONTH_MAP = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}

CATEGORY_MAP = {
    "travaux": MarketType.TRAVAUX,
    "services": MarketType.SERVICES,
    "fournitures": MarketType.FOURNITURES,
}


class DematAmpaSource(BaseSource):
    """Collecteur pour le portail demat-ampa.fr via Playwright."""

    name = "demat_ampa"
    description = "Portail demat-ampa.fr (AMPA) — scraping Playwright"

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("[demat_ampa] Playwright non installé.")
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            seen_refs = set()
            total = 0

            for keyword in SEARCH_KEYWORDS:
                url = f"{SEARCH_URL}&motCle={keyword}"
                logger.info("[demat_ampa] Recherche : %s", keyword)

                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    # Attendre que les résultats soient chargés
                    await page.wait_for_selector(
                        "div.item_consultation", timeout=15000
                    )
                except Exception:
                    logger.debug("[demat_ampa] Timeout ou pas de résultats pour '%s'", keyword)
                    continue

                rows = await page.query_selector_all("div.item_consultation")
                logger.info("[demat_ampa] %d consultations trouvées pour '%s'", len(rows), keyword)

                for row in rows:
                    tender = await self._parse_row(row, since)
                    if tender and tender.source_id not in seen_refs:
                        seen_refs.add(tender.source_id)
                        total += 1
                        yield tender

            await browser.close()
            logger.info("[demat_ampa] %d AO collectés au total", total)

    async def _parse_row(self, row, since: datetime) -> Tender | None:
        try:
            # --- Référence ---
            ref_input = await row.query_selector("input[name*='refCons']")
            if not ref_input:
                return None
            ref = await ref_input.get_attribute("value")
            if not ref or not ref.strip():
                return None
            ref = ref.strip()

            # --- Titre ---
            title_el = await row.query_selector(
                "div.small.pull-left.truncate span[data-original-title]"
            )
            if not title_el:
                title_el = await row.query_selector("div.small.pull-left.truncate span")
            if not title_el:
                return None

            title = await title_el.get_attribute("data-original-title") or await title_el.inner_text()
            title = title.strip().strip('"')
            if not title:
                return None

            # --- Catégorie → type de marché ---
            cat_el = await row.query_selector("div.cons_categorie span")
            cat_text = (await cat_el.inner_text()).strip().lower() if cat_el else ""
            market_type = CATEGORY_MAP.get(cat_text, MarketType.OTHER)

            # --- Date limite ---
            deadline = await self._parse_date(row)

            # Filtrer par date
            if deadline and deadline < since:
                return None

            # --- URL détail ---
            detail_url = DETAIL_URL.format(ref=ref)

            return Tender(
                uid=f"demat_ampa_{ref}",
                source=self.name,
                source_id=ref,
                sources=[self.name],
                source_urls={self.name: detail_url},
                url=detail_url,
                title=title,
                market_type=market_type,
                notice_nature=NoticeNature.APPEL_OFFRE,
                deadline=deadline,
                publication_date=None,
            )

        except Exception as exc:
            logger.debug("[demat_ampa] Erreur parse: %s", exc)
            return None

    @staticmethod
    async def _parse_date(row) -> datetime | None:
        """Parse la date depuis div.date.date-min → jour / mois / année."""
        try:
            day_el = await row.query_selector("div.date.date-min div.day span")
            month_el = await row.query_selector("div.date.date-min div.month span")
            year_el = await row.query_selector("div.date.date-min div.year")

            if not (day_el and month_el):
                return None

            day = int((await day_el.inner_text()).strip())
            month_str = (await month_el.inner_text()).strip().lower()
            month = MONTH_MAP.get(month_str, 0)

            year = datetime.utcnow().year
            if year_el:
                year_text = (await year_el.inner_text()).strip()
                if year_text.isdigit():
                    year = int(year_text)

            if month == 0:
                return None

            return datetime(year, month, day)
        except Exception:
            return None
