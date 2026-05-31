"""
Collecteur Aquitanis — aquitanis.e-marchespublics.com

Aquitanis est l'Office Public de l'Habitat (OPH) de Bordeaux Métropole.
Il publie ses AO sur une salle des marchés dédiée propulsée par la plateforme
**Dematis e-marchespublics** — la MÊME technologie que www.e-marchespublics.com
(cf. collector/e_marches_publics.py). Le rendu des avis se fait en JavaScript,
on utilise donc Playwright et les mêmes sélecteurs `div.box`.

Différences avec e_marches_publics :
  - Salle des marchés mono-acheteur (Aquitanis) → on liste TOUS les avis de
    marché en cours, sans recherche par mot-clé ; le scorer filtre ensuite.
  - Bailleur social de Bordeaux Métropole → département 33 (Gironde) par défaut
    si non détecté, donc région prioritaire (Nouvelle-Aquitaine).

Structure DOM (Dematis, identique à e-marchespublics.com) :
  - Conteneur AO  : div.box
  - Titre         : div.box-header-title div.texttruncate
  - Acheteur      : div.box-body-top > span (premier)
  - Localisation  : div.col1 p:first-child
  - Type marché   : div.col1 p:nth-child(2)
  - Date limite   : div.col3 span.pink

NB : si la salle des marchés Aquitanis emploie un thème légèrement différent,
seuls les sélecteurs CSS de _parse_box sont à ajuster.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from typing import AsyncGenerator

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender

logger = logging.getLogger(__name__)

BASE_URL = "https://aquitanis.e-marchespublics.com"
HOME_URL = BASE_URL + "/"

MAX_PAGES = 10   # garde-fou (Aquitanis a généralement < 10 avis en cours)

# Aquitanis = OPH de Bordeaux Métropole (Gironde)
DEFAULT_DEPARTMENT = "33"
DEFAULT_BUYER = "Aquitanis"

CATEGORY_MAP = {
    "travaux": MarketType.TRAVAUX,
    "services": MarketType.SERVICES,
    "fournitures": MarketType.FOURNITURES,
}


class AquitanisSource(BaseSource):
    """Collecteur pour la salle des marchés Aquitanis (Dematis) via Playwright."""

    name = "aquitanis"
    description = "Aquitanis — OPH de Bordeaux Métropole (e-marchespublics)"

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("[aquitanis] Playwright non installé.")
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

            try:
                await page.goto(HOME_URL, wait_until="networkidle", timeout=30000)
                await self._dismiss_cookies(page)
            except Exception as exc:
                logger.error("[aquitanis] Erreur d'accès à l'accueil: %s", exc)
                await browser.close()
                return

            # S'assurer d'être sur l'onglet "Avis de marché" si présent
            await self._open_avis_list(page)

            seen_refs: set[str] = set()
            total = 0

            for page_num in range(1, MAX_PAGES + 1):
                if page_num > 1:
                    try:
                        await page.evaluate(f"updateSearch('page', {page_num})")
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        await page.wait_for_timeout(1000)
                    except Exception:
                        break

                try:
                    await page.wait_for_selector("div.box", timeout=8000)
                except Exception:
                    break

                boxes = await page.query_selector_all("div.box")
                if not boxes:
                    break

                logger.info("[aquitanis] %d avis (page %d)", len(boxes), page_num)

                page_new = 0
                for box in boxes:
                    tender = await self._parse_box(box)
                    if tender and tender.source_id not in seen_refs:
                        seen_refs.add(tender.source_id)
                        total += 1
                        page_new += 1
                        yield tender

                # Plus de nouvelle entrée → on a probablement bouclé
                if page_new == 0:
                    break

            await browser.close()
            logger.info("[aquitanis] %d AO collectés au total", total)

    @staticmethod
    async def _dismiss_cookies(page) -> None:
        """Ferme la bannière cookies Didomi si présente."""
        try:
            btn = await page.wait_for_selector(
                "#didomi-notice-agree-button, "
                "button[id*=agree], button[id*=accept], "
                "button:has-text('Accepter'), button:has-text('Continuer')",
                timeout=4000,
            )
            if btn:
                await btn.click()
                await page.wait_for_timeout(800)
        except Exception:
            pass  # pas de bannière

    @staticmethod
    async def _open_avis_list(page) -> None:
        """Clique sur l'onglet 'Avis de marché' / 'Tous' si la liste n'est pas déjà affichée."""
        try:
            if await page.query_selector("div.box"):
                return  # liste déjà visible
            link = await page.query_selector(
                "a:has-text('Avis de marché'), a:has-text('Avis de marchés'), "
                "a:has-text('Consultations'), a:has-text('TOUS')"
            )
            if link:
                await link.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.wait_for_timeout(1500)
        except Exception:
            pass

    async def _parse_box(self, box) -> Tender | None:
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
            buyer = buyer or DEFAULT_BUYER

            # --- Localisation → département ---
            loc_el = await box.query_selector("div.col1 p:first-child")
            loc_text = (await loc_el.inner_text()).strip() if loc_el else ""
            departments = self._extract_dept_from_location(loc_text) or [DEFAULT_DEPARTMENT]

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

            # Filtrer les AO expirés
            now = datetime.utcnow()
            if deadline and deadline < now:
                return None

            # --- ID stable (hash titre + acheteur) ---
            raw = f"{title[:80]}|{buyer}"
            source_id = hashlib.md5(raw.encode()).hexdigest()[:12]

            detail_url = HOME_URL  # pas d'URL individuelle fiable sans interaction

            return Tender(
                uid=f"aquitanis_{source_id}",
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
            logger.debug("[aquitanis] Erreur parse: %s", exc)
            return None

    @staticmethod
    def _extract_dept_from_location(text: str) -> list[str]:
        """Extrait le code département depuis un code postal (ex: '33000' → '33')."""
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
