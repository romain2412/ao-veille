"""
Collecteur e-marchespublics.com

Structure DOM (inspectée le 2026-05-31) :
  - Conteneur AO  : div.box
  - Titre         : div.box-header-title div.texttruncate
  - Acheteur      : div.box-body-top > span (premier)
  - Localisation  : div.col1 p:first-child (icône fa-map-marker)
  - Type marché   : div.col1 p:nth-child(2) (icône fa-file-alt)
  - Date limite   : div.col3 span.pink
  - Pagination    : JS updateSearch('page', N) — 10 résultats/page

Recherche : POST /appel-offre avec _token + what + category
URL détail : https://www.e-marchespublics.com/appel-offre/<slug>
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import AsyncGenerator

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender

logger = logging.getLogger(__name__)

BASE_URL = "https://www.e-marchespublics.com"
SEARCH_URL = BASE_URL + "/appel-offre"

SEARCH_KEYWORDS = ["VRD", "voirie", "assainissement", "paysage", "espaces verts"]
MAX_PAGES = 10   # 10 pages max par mot-clé (100 résultats)

CATEGORY_MAP = {
    "travaux": MarketType.TRAVAUX,
    "services": MarketType.SERVICES,
    "fournitures": MarketType.FOURNITURES,
}


class EMarchesPublicsSource(BaseSource):
    """Collecteur pour e-marchespublics.com via Playwright."""

    name = "e_marches_publics"
    description = "e-marchespublics.com — scraping Playwright"

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("[e_marches_publics] Playwright non installé.")
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
                logger.info("[e_marches_publics] Recherche : %s", keyword)

                # Aller sur l'accueil et soumettre la recherche
                try:
                    await page.goto(BASE_URL + "/", wait_until="networkidle", timeout=30000)
                    await page.fill("input#what", keyword)
                    await page.get_by_text("Lancer la recherche").first.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await page.wait_for_timeout(3000)
                    # Pas de wait_for_selector bloquant — on essaie directement
                except Exception as exc:
                    logger.debug("[e_marches_publics] Erreur navigation '%s': %s", keyword, exc)
                    continue

                # Attendre un peu plus pour le rendu JS
                await page.wait_for_timeout(2000)

                # Nombre total de pages
                total_pages = await self._get_total_pages(page)
                pages_to_fetch = min(total_pages, MAX_PAGES)
                logger.info(
                    "[e_marches_publics] %d pages disponibles, on en lit %d pour '%s'",
                    total_pages, pages_to_fetch, keyword
                )

                for page_num in range(1, pages_to_fetch + 1):
                    if page_num > 1:
                        try:
                            # Navigation via JS
                            await page.evaluate(f"updateSearch('page', {page_num})")
                            await page.wait_for_load_state("networkidle", timeout=15000)
                            await page.wait_for_timeout(1000)
                        except Exception:
                            break

                    boxes = await page.query_selector_all("div.box")
                    if not boxes:
                        break

                    for box in boxes:
                        tender = await self._parse_box(box, since)
                        if tender and tender.source_id not in seen_refs:
                            seen_refs.add(tender.source_id)
                            total += 1
                            yield tender

            await browser.close()
            logger.info("[e_marches_publics] %d AO collectés au total", total)

    async def _get_total_pages(self, page) -> int:
        """Récupère le nombre total de pages depuis l'interface."""
        try:
            html = await page.inner_text("body")
            match = re.search(r'(\d+)\s*/\s*(\d+)', html)
            if match:
                return int(match.group(2))
        except Exception:
            pass
        return 1

    async def _parse_box(self, box, since: datetime) -> Tender | None:
        try:
            # --- Titre ---
            title_el = await box.query_selector("div.box-header-title div.texttruncate")
            if not title_el:
                return None
            title = (await title_el.inner_text()).strip()
            title = re.sub(r'\s+', ' ', title)
            if not title:
                return None

            # --- Acheteur ---
            buyer_el = await box.query_selector("div.box-body-top > span")
            buyer = (await buyer_el.inner_text()).strip() if buyer_el else None

            # --- Localisation (ex: "91910 Saint Sulpice de Favières") ---
            loc_el = await box.query_selector("div.col1 p:first-child")
            loc_text = (await loc_el.inner_text()).strip() if loc_el else ""
            departments = self._extract_dept_from_location(loc_text)

            # --- Type de marché ---
            type_el = await box.query_selector("div.col1 p:nth-child(2)")
            type_text = (await type_el.inner_text()).strip().lower() if type_el else ""
            market_type = MarketType.OTHER
            for key, val in CATEGORY_MAP.items():
                if key in type_text:
                    market_type = val
                    break

            # --- Date limite ---
            deadline_el = await box.query_selector("div.col3 span.pink, .col3 .pink")
            deadline = None
            if deadline_el:
                deadline_text = (await deadline_el.inner_text()).strip()
                deadline = self._parse_date(deadline_text)

            # Filtrer AO expirés
            now = datetime.utcnow()
            if deadline and deadline < now:
                return None

            # --- ID unique (hash du titre + acheteur) ---
            import hashlib
            raw = f"{title[:80]}|{buyer or ''}"
            source_id = hashlib.md5(raw.encode()).hexdigest()[:12]

            # URL de la page courante
            detail_url = SEARCH_URL  # pas d'URL individuelle sans interaction

            return Tender(
                uid=f"e_marches_publics_{source_id}",
                source=self.name,
                source_id=source_id,
                sources=[self.name],
                source_urls={self.name: detail_url},
                url=detail_url,
                title=title,
                buyer_name=buyer,
                departments=departments,
                market_type=market_type,
                notice_nature=NoticeNature.APPEL_OFFRE,
                deadline=deadline,
                publication_date=None,
            )

        except Exception as exc:
            logger.debug("[e_marches_publics] Erreur parse: %s", exc)
            return None

    @staticmethod
    def _extract_dept_from_location(text: str) -> list[str]:
        """Extrait le code département depuis un code postal (ex: '91910' → '91')."""
        match = re.search(r'\b(\d{5})\b', text)
        if match:
            cp = match.group(1)
            dept = cp[:2] if cp[:2] != "97" else cp[:3]
            return [dept]
        return []

    @staticmethod
    def _parse_date(text: str) -> datetime | None:
        """Parse une date du type '19/06/2026 à 12h00'."""
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
        if match:
            try:
                return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                pass
        return None
