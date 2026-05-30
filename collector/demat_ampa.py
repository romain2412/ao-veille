"""
Collecteur demat-ampa.fr (Portail marchés publics AMPA)

demat-ampa est un portail JavaScript dynamique → on utilise Playwright
(navigateur headless) pour charger et scraper les pages de résultats.

URL de recherche :
  https://demat-ampa.fr/entreprise/?page=Entreprise.EntrepriseAdvancedSearch&AllCons
  Paramètres : categorieCode (TRAVAUX/SERVICES/...), motCle, lieuExecution
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import AsyncGenerator

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender

logger = logging.getLogger(__name__)

BASE_URL = "https://demat-ampa.fr/entreprise/"
SEARCH_URL = (
    BASE_URL
    + "?page=Entreprise.EntrepriseAdvancedSearch&AllCons"
)

# Mots-clés métier pour le filtre initial (côté site)
SEARCH_KEYWORDS = ["VRD", "voirie", "assainissement", "paysage", "espaces verts"]


class DematAmpaSource(BaseSource):
    """Collecteur pour le portail demat-ampa.fr via Playwright."""

    name = "demat_ampa"
    description = "Portail demat-ampa.fr (AMPA) — scraping Playwright"

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        """
        Collecte les AO depuis demat-ampa.fr publiés depuis `since`.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error(
                "[demat_ampa] Playwright non installé. "
                "Ajouter 'playwright' aux requirements."
            )
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

            total = 0
            # Lancer une recherche par mot-clé pour chaque terme métier
            seen_refs = set()

            for keyword in SEARCH_KEYWORDS:
                url = f"{SEARCH_URL}&categorieCode=&motCle={keyword}"
                logger.info("[demat_ampa] Recherche : %s", keyword)

                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    # Attendre que les résultats soient chargés
                    await page.wait_for_timeout(2000)

                    tenders = await self._extract_tenders(page, since, seen_refs)
                    for tender in tenders:
                        total += 1
                        seen_refs.add(tender.source_id)
                        yield tender

                except Exception as exc:
                    logger.warning("[demat_ampa] Erreur sur keyword '%s': %s", keyword, exc)
                    continue

            await browser.close()
            logger.info("[demat_ampa] %d AO collectés", total)

    async def _extract_tenders(
        self,
        page,
        since: datetime,
        seen_refs: set,
    ) -> list[Tender]:
        """Extrait les AO de la page courante."""
        tenders = []

        try:
            # Attendre les résultats — s'adapter selon la structure réelle du DOM
            # Ces sélecteurs seront à affiner après inspection en live
            rows = await page.query_selector_all(
                "table tr.consultation-row, "
                ".consultation-item, "
                "tr[data-ref], "
                ".result-item"
            )

            if not rows:
                # Fallback : essayer de parser tout le contenu textuel
                logger.debug("[demat_ampa] Aucune ligne trouvée avec les sélecteurs standards")
                return tenders

            for row in rows:
                tender = await self._parse_row(row, page)
                if tender and tender.source_id not in seen_refs:
                    # Filtrer par date
                    if tender.publication_date and tender.publication_date < since:
                        continue
                    tenders.append(tender)

        except Exception as exc:
            logger.warning("[demat_ampa] Erreur extraction: %s", exc)

        return tenders

    async def _parse_row(self, row, page) -> Tender | None:
        """Parse une ligne de résultat en Tender."""
        try:
            text = await row.inner_text()
            if not text.strip():
                return None

            # Extraire le lien de détail
            link_el = await row.query_selector("a[href]")
            detail_url = None
            source_id = None

            if link_el:
                href = await link_el.get_attribute("href")
                if href:
                    detail_url = href if href.startswith("http") else BASE_URL + href.lstrip("/")
                    # Extraire la référence depuis l'URL ou le texte
                    ref_match = re.search(r'[Cc]ons[_=](\d+)', href)
                    if ref_match:
                        source_id = ref_match.group(1)

            if not source_id:
                # Fallback : utiliser un hash du texte
                source_id = str(abs(hash(text[:100])))

            # Titre
            title_el = await row.query_selector(".consultation-titre, .titre, td:first-child, h3, h4")
            title = (await title_el.inner_text()).strip() if title_el else text.split("\n")[0][:200]

            if not title:
                return None

            # Acheteur
            buyer_el = await row.query_selector(".acheteur, .organisme, td:nth-child(2)")
            buyer = (await buyer_el.inner_text()).strip() if buyer_el else None

            # Date limite
            deadline = self._extract_date(text)

            # Date de publication
            pub_date = self._extract_pub_date(text)

            # Type de marché
            market_type = MarketType.OTHER
            text_lower = text.lower()
            if "travaux" in text_lower:
                market_type = MarketType.TRAVAUX
            elif "service" in text_lower:
                market_type = MarketType.SERVICES
            elif "fourniture" in text_lower:
                market_type = MarketType.FOURNITURES

            return Tender(
                uid=f"demat_ampa_{source_id}",
                source=self.name,
                source_id=source_id,
                sources=[self.name],
                source_urls={self.name: detail_url} if detail_url else {},
                url=detail_url,
                title=title,
                buyer_name=buyer,
                market_type=market_type,
                notice_nature=NoticeNature.APPEL_OFFRE,
                deadline=deadline,
                publication_date=pub_date,
            )

        except Exception as exc:
            logger.debug("[demat_ampa] Erreur parse row: %s", exc)
            return None

    @staticmethod
    def _extract_date(text: str) -> datetime | None:
        """Extrait une date limite du texte (format DD/MM/YYYY)."""
        match = re.search(r'(\d{2})[/\-](\d{2})[/\-](\d{4})', text)
        if match:
            try:
                return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                pass
        return None

    @staticmethod
    def _extract_pub_date(text: str) -> datetime | None:
        """Extrait la date de publication si présente."""
        matches = re.findall(r'(\d{2})[/\-](\d{2})[/\-](\d{4})', text)
        if len(matches) >= 2:
            try:
                m = matches[1]  # La 2ème date est souvent la publication
                return datetime(int(m[2]), int(m[1]), int(m[0]))
            except ValueError:
                pass
        return None
