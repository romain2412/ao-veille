"""
Collecteur demat-ampa.fr (Portail marchés publics AMPA)

Approche : navigation directe via URL de recherche (découverte le 2026-05-31)
  URL résultats : https://demat-ampa.fr/?page=Entreprise.EntrepriseAdvancedSearch
                  &searchAnnCons&keyWord=VRD&categorie=0&localisations=

Structure DOM inspectée :
  - Conteneur AO  : div.item_consultation (ou div[id^=row-consultation])
  - Référence     : input[name*="refCons"] → value
  - Titre         : div.small.pull-left.truncate span[data-original-title]
  - Catégorie     : div.cons_categorie span
  - Organisme     : div.cons_organisme ou texte "Organisme : ..."
  - Date limite   : div.date  (2ème occurrence = deadline)
  - Département   : "(33) Gironde" dans le texte
  - Pagination    : paramètre &page=2
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import AsyncGenerator

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender
from timeutils import now_utc

logger = logging.getLogger(__name__)

HOME_URL = "https://demat-ampa.fr/entreprise/"
RESULTS_URL = (
    "https://demat-ampa.fr/"
    "?page=Entreprise.EntrepriseAdvancedSearch"
    "&searchAnnCons&keyWord={keyword}&categorie=0&localisations="
)
RESULTS_URL_PAGE = RESULTS_URL + "&debut={offset}"
DETAIL_URL = (
    "https://demat-ampa.fr/"
    "?page=Entreprise.EntrepriseDetailConsultation&refCons={ref}"
)

SEARCH_KEYWORDS = ["VRD", "voirie", "assainissement", "paysage", "espaces+verts"]
PAGE_SIZE = 10    # résultats par page sur demat-ampa
MAX_PAGES = 15    # max 15 pages par mot-clé (150 résultats)

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

            # Démarrer par la page d'accueil pour initialiser la session/cookies
            await page.goto(HOME_URL, wait_until="networkidle", timeout=30000)

            seen_refs: set[str] = set()
            total = 0

            for keyword in SEARCH_KEYWORDS:
                logger.info("[demat_ampa] Recherche : %s", keyword)
                offset = 0
                page_num = 0

                while page_num < MAX_PAGES:
                    url = (
                        RESULTS_URL_PAGE.format(keyword=keyword, offset=offset)
                        if offset > 0
                        else RESULTS_URL.format(keyword=keyword)
                    )

                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        await page.wait_for_selector(
                            "div.item_consultation", timeout=10000
                        )
                    except Exception:
                        break

                    rows = await page.query_selector_all("div.item_consultation")
                    if not rows:
                        break

                    logger.info(
                        "[demat_ampa] %d résultats (offset=%d) pour '%s'",
                        len(rows), offset, keyword
                    )

                    page_new = 0
                    for row in rows:
                        tender = await self._parse_row(row, since)
                        if tender and tender.source_id not in seen_refs:
                            seen_refs.add(tender.source_id)
                            total += 1
                            page_new += 1
                            yield tender

                    logger.debug(
                        "[demat_ampa] %d nouveaux AO sur cette page pour '%s'",
                        page_new, keyword
                    )

                    if len(rows) < PAGE_SIZE:
                        break

                    offset += PAGE_SIZE
                    page_num += 1

            await browser.close()
            logger.info("[demat_ampa] %d AO collectés au total", total)

    async def _parse_row(self, row, since: datetime) -> Tender | None:
        try:
            # --- Référence ---
            ref_input = await row.query_selector("input[name*='refCons']")
            if not ref_input:
                return None
            ref = (await ref_input.get_attribute("value") or "").strip()
            if not ref:
                return None

            # --- Titre ---
            title_el = await row.query_selector(
                "div.small.pull-left.truncate span[data-original-title]"
            )
            if not title_el:
                title_el = await row.query_selector("div.small.pull-left.truncate span")
            if not title_el:
                return None
            title = (
                await title_el.get_attribute("data-original-title")
                or await title_el.inner_text()
            )
            title = (title or "").strip().strip('"')
            if not title:
                return None

            # --- Catégorie ---
            cat_el = await row.query_selector("div.cons_categorie span")
            cat_text = (await cat_el.inner_text()).strip().lower() if cat_el else ""
            market_type = CATEGORY_MAP.get(cat_text, MarketType.OTHER)

            # --- Texte complet pour extraire organisme + département ---
            full_text = await row.inner_text()

            # Organisme
            buyer = self._extract_organisme(full_text)

            # Département
            departments = self._extract_departments(full_text)

            # --- Dates (2 dates dans la page : publication + deadline) ---
            dates = await self._parse_all_dates(row)
            pub_date = dates[0] if len(dates) > 0 else None
            deadline = dates[1] if len(dates) > 1 else dates[0] if dates else None

            # Pour demat-ampa : on ne filtre PAS par date de publication
            # (la recherche retourne déjà les AO en cours)
            # On filtre uniquement les AO dont la deadline est dépassée
            now = now_utc()
            if deadline and deadline < now:
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
                buyer_name=buyer,
                departments=departments,
                market_type=market_type,
                notice_nature=NoticeNature.APPEL_OFFRE,
                publication_date=pub_date,
                deadline=deadline,
            )

        except Exception as exc:
            logger.debug("[demat_ampa] Erreur parse: %s", exc)
            return None

    @staticmethod
    def _extract_organisme(text: str) -> str | None:
        """Extrait le nom de l'organisme depuis le texte."""
        match = re.search(r'Organisme\s*:\s*([^\n]+)', text)
        if match:
            # Retirer le code postal entre parenthèses
            org = re.sub(r'\s*\(\d{5}[^)]*\)', '', match.group(1)).strip()
            return org or None
        return None

    @staticmethod
    def _extract_departments(text: str) -> list[str]:
        """Extrait les codes département depuis le texte '(33) Gironde'."""
        return re.findall(r'\((\d{2,3})\)\s+\w+', text)

    @staticmethod
    async def _parse_all_dates(row) -> list[datetime]:
        """Extrait toutes les dates du bloc (publication + deadline)."""
        dates = []
        date_divs = await row.query_selector_all("div.date")
        for date_div in date_divs:
            try:
                day_el = await date_div.query_selector("div.day span")
                month_el = await date_div.query_selector("div.month span")
                year_el = await date_div.query_selector("div.year")

                if not (day_el and month_el):
                    continue

                day = int((await day_el.inner_text()).strip())
                month_str = (await month_el.inner_text()).strip().lower()
                month = MONTH_MAP.get(month_str, 0)
                if month == 0:
                    continue

                year = now_utc().year
                if year_el:
                    year_text = (await year_el.inner_text()).strip()
                    digits = re.search(r'\d{4}', year_text)
                    if digits:
                        year = int(digits.group())

                dates.append(datetime(year, month, day))
            except Exception:
                continue
        return dates
