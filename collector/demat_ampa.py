"""
Collecteur demat-ampa.fr (Portail marchés publics AMPA)

Le site requiert une interaction formulaire (pas de navigation directe par URL).
On remplit le champ "Mots clés" et on soumet la recherche rapide.

Structure DOM inspectée le 2026-05-31 :
  - Conteneur AO  : div.item_consultation  (ou div[id^=row-consultation])
  - Référence     : input[name*="refCons"] → value
  - Titre         : div.small.pull-left.truncate span[data-original-title]
  - Catégorie     : div.cons_categorie span
  - Date limite   : div.date.date-min (day / month / year)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import AsyncGenerator

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender

logger = logging.getLogger(__name__)

BASE_URL = "https://demat-ampa.fr/entreprise/"
DETAIL_URL = BASE_URL + "?page=Entreprise.EntrepriseDetailConsultation&refCons={ref}"

# Mots-clés à rechercher un par un via le formulaire
SEARCH_KEYWORDS = ["VRD", "voirie", "assainissement", "paysage", "espaces verts"]

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

            seen_refs: set[str] = set()
            total = 0

            for keyword in SEARCH_KEYWORDS:
                logger.info("[demat_ampa] Recherche : %s", keyword)

                try:
                    # 1. Aller sur la page d'accueil
                    await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

                    # 2. Remplir le champ mots-clés
                    kw_input = await page.wait_for_selector(
                        "input[name*='motCle'], input[placeholder*='lot'], input[id*='motCle']",
                        timeout=10000,
                    )
                    if not kw_input:
                        logger.warning("[demat_ampa] Champ mots-clés introuvable")
                        continue

                    await kw_input.fill(keyword)

                    # 3. Soumettre le formulaire (bouton "Lancer la recherche")
                    submit = await page.query_selector(
                        "button[type='submit'], input[type='submit'], "
                        "button:has-text('Lancer'), button:has-text('Rechercher')"
                    )
                    if submit:
                        await submit.click()
                    else:
                        await kw_input.press("Enter")

                    # 4. Attendre les résultats
                    await page.wait_for_selector(
                        "div.item_consultation, div[id^=row-consultation], "
                        "div.table-results",
                        timeout=20000,
                    )
                    await page.wait_for_timeout(1000)

                except Exception as exc:
                    logger.debug("[demat_ampa] Pas de résultats pour '%s': %s", keyword, exc)
                    continue

                # 5. Extraire les AO
                rows = await page.query_selector_all(
                    "div.item_consultation, div[id^=row-consultation]"
                )
                logger.info(
                    "[demat_ampa] %d consultations pour '%s'", len(rows), keyword
                )

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
            # Référence
            ref_input = await row.query_selector("input[name*='refCons']")
            if not ref_input:
                return None
            ref = (await ref_input.get_attribute("value") or "").strip()
            if not ref:
                return None

            # Titre
            title_el = await row.query_selector(
                "div.small.pull-left.truncate span[data-original-title], "
                "div.small.pull-left.truncate span, "
                "span[data-original-title]"
            )
            if not title_el:
                return None
            title = (
                await title_el.get_attribute("data-original-title")
                or await title_el.inner_text()
            )
            title = (title or "").strip().strip('"')
            if not title:
                return None

            # Catégorie
            cat_el = await row.query_selector("div.cons_categorie span")
            cat_text = (await cat_el.inner_text()).strip().lower() if cat_el else ""
            market_type = CATEGORY_MAP.get(cat_text, MarketType.OTHER)

            # Date limite
            deadline = await self._parse_date(row)
            if deadline and deadline < since:
                return None

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
        try:
            day_el = await row.query_selector("div.date.date-min div.day span")
            month_el = await row.query_selector("div.date.date-min div.month span")
            year_el = await row.query_selector("div.date.date-min div.year")

            if not (day_el and month_el):
                return None

            day = int((await day_el.inner_text()).strip())
            month_str = (await month_el.inner_text()).strip().lower()
            month = MONTH_MAP.get(month_str, 0)
            if month == 0:
                return None

            year = datetime.utcnow().year
            if year_el:
                year_text = (await year_el.inner_text()).strip()
                if year_text.isdigit():
                    year = int(year_text)

            return datetime(year, month, day)
        except Exception:
            return None
