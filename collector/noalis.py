"""
Collecteur Noalis — marches-publics.info (IDS=3414)

Noalis (Entreprise Sociale pour l'Habitat, Nouvelle-Aquitaine) publie ses AO
via un iframe hébergé sur marches-publics.info.

URL directe : https://www.marches-publics.info/avis/index.cfm?IDS=3414

Structure HTML (HTML statique, pas de JS) :
  - Tableau de 10 lignes pour 3 AO
  - Pattern : toutes les 3 lignes à partir de la ligne 1
  - Ligne principale : dates | acheteur | [réf. XXX] | titre
  - Liens : [0] = page détail (refPub=...)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import AsyncGenerator

import httpx

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender
from timeutils import now_utc

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.marches-publics.info/avis/index.cfm?IDS=3414"
BASE_URL   = "https://www.marches-publics.info/avis/"
NOALIS_URL = "https://noalis.fr/fournisseurs/"


class NoalisSource(BaseSource):
    """Collecteur pour les AO de Noalis (via marches-publics.info)."""

    name = "noalis"
    description = "Noalis — marchés publics ESH Nouvelle-Aquitaine"

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        """
        Récupère les AO de Noalis depuis marches-publics.info.
        Page HTML statique — httpx suffit, pas de Playwright.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("[noalis] BeautifulSoup non installé (pip install beautifulsoup4)")
            return

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(SOURCE_URL)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("[noalis] Erreur HTTP: %s", exc)
                return

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all("tr")

        total = 0
        # Les AO sont sur les lignes 1, 4, 7, 10... (toutes les 3 lignes, depuis index 1)
        for i, row in enumerate(rows):
            tds = row.find_all("td")
            if not tds:
                continue

            text = row.get_text(separator="|", strip=True)

            # Identifier les lignes AO : commencent par une date dd/mm/yy
            if not re.match(r'\d{2}/\d{2}/\d{2}', text):
                continue

            tender = self._parse_row(row, tds, text, since)
            if tender:
                total += 1
                yield tender

        logger.info("[noalis] %d AO collectés", total)

    def _parse_row(self, row, tds, text: str, since: datetime) -> Tender | None:
        try:
            parts = [p.strip() for p in text.split("|") if p.strip()]

            # --- Dates ---
            pub_date  = self._parse_date_yy(parts[0]) if parts else None
            deadline  = self._parse_deadline(parts[1] + " " + parts[2]) if len(parts) > 2 else None

            # Filtrer AO expirés
            now = now_utc()
            if deadline and deadline < now:
                return None

            # --- Acheteur (ex: "NOALIS (87000)") ---
            buyer = None
            ref   = None
            title = None
            departments: list[str] = []

            for part in parts:
                if re.match(r'.+\s*\(\d{5}\)', part) and not buyer:
                    buyer = re.sub(r'\s*\(\d{5}\)', '', part).strip()
                    cp_match = re.search(r'\((\d{5})\)', part)
                    if cp_match:
                        cp = cp_match.group(1)
                        departments = [cp[:2] if cp[:2] != "97" else cp[:3]]
                elif re.match(r'\[réf\. .+\]', part):
                    ref = part.strip("[]").replace("réf. ", "").strip()
                elif part not in ("Avis", "RC", "DCE", "Déposer un pli") and not re.match(r'\d{2}/\d{2}', part):
                    if len(part) > 10 and not title:
                        title = part

            if not title or not ref:
                return None

            # --- URL de détail ---
            link = row.find("a", href=re.compile(r"affPublication"))
            detail_url = BASE_URL + link["href"] if link else SOURCE_URL

            source_id = ref.replace(" ", "_").replace("/", "_")

            return Tender(
                uid=f"noalis_{source_id}",
                source=self.name,
                source_id=source_id,
                sources=[self.name],
                source_urls={self.name: detail_url},
                url=detail_url,
                title=title,
                buyer_name=buyer or "NOALIS",
                departments=departments,
                market_type=MarketType.TRAVAUX,
                notice_nature=NoticeNature.APPEL_OFFRE,
                publication_date=pub_date,
                deadline=deadline,
            )

        except Exception as exc:
            logger.debug("[noalis] Erreur parse: %s", exc)
            return None

    @staticmethod
    def _parse_date_yy(text: str) -> datetime | None:
        """Parse dd/mm/yy → datetime."""
        match = re.search(r'(\d{2})/(\d{2})/(\d{2})', text)
        if match:
            try:
                year = 2000 + int(match.group(3))
                return datetime(year, int(match.group(2)), int(match.group(1)))
            except ValueError:
                pass
        return None

    @staticmethod
    def _parse_deadline(text: str) -> datetime | None:
        """Parse 'dd/mm/yy à HHhMM' → datetime."""
        match = re.search(r'(\d{2})/(\d{2})/(\d{2})', text)
        if match:
            try:
                year = 2000 + int(match.group(3))
                return datetime(year, int(match.group(2)), int(match.group(1)))
            except ValueError:
                pass
        return None
