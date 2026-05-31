"""
Collecteur Vilogia — groupevilogia.achatpublic.com

Vilogia (ESH Nord/Nouvelle-Aquitaine) publie ses AO sur sa propre salle des marchés.

URL liste : https://groupevilogia.achatpublic.com/sdm/ent/gen/ent_recherche.do
URL détail : https://groupevilogia.achatpublic.com/sdm/ent2/gen/ficheCsl.action?PCSLID=...

Structure HTML (statique) :
  - Chaque AO démarre par un <li> contenant un lien vers ficheCsl.action
  - Titre dans le texte du li (format "REF : Titre\n\nDate limite...")
  - Les li suivants contiennent : Organisme, Référence, Nature, Type, Lieu
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import AsyncGenerator

import httpx

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender

logger = logging.getLogger(__name__)

LIST_URL   = "https://groupevilogia.achatpublic.com/sdm/ent/gen/ent_recherche.do"
BASE_URL   = "https://groupevilogia.achatpublic.com"

CATEGORY_MAP = {
    "travaux": MarketType.TRAVAUX,
    "services": MarketType.SERVICES,
    "fournitures": MarketType.FOURNITURES,
}


class VilogiaSource(BaseSource):
    """Collecteur pour les AO de Vilogia (achatpublic.com)."""

    name = "vilogia"
    description = "Vilogia — ESH Nord / Nouvelle-Aquitaine"

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("[vilogia] BeautifulSoup non installé")
            return

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                resp = await client.get(LIST_URL)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("[vilogia] Erreur HTTP: %s", exc)
                return

        soup = BeautifulSoup(resp.text, "html.parser")

        # Trouver tous les li qui contiennent un lien vers ficheCsl (= titre d'un AO)
        all_lis = soup.find_all("li")
        ao_lis = [
            li for li in all_lis
            if li.find("a", href=re.compile(r"ficheCsl"))
        ]

        total = 0
        for ao_li in ao_lis:
            tender = self._parse_ao(ao_li, soup, all_lis, since)
            if tender:
                total += 1
                yield tender

        logger.info("[vilogia] %d AO collectés", total)

    def _parse_ao(self, ao_li, soup, all_lis, since: datetime) -> Tender | None:
        try:
            # --- URL détail + source_id ---
            link = ao_li.find("a", href=re.compile(r"ficheCsl"))
            if not link:
                return None
            href = link.get("href", "")
            detail_url = BASE_URL + href if href.startswith("/") else href
            pcslid_match = re.search(r"PCSLID=([^&]+)", href)
            source_id = pcslid_match.group(1) if pcslid_match else href[-20:]

            # --- Titre ---
            full_text = ao_li.get_text(separator="\n", strip=True)
            # Le titre est avant "Date limite" ou à la première ligne
            title_raw = full_text.split("\n")[0].strip()
            # Retirer la référence préfixe "AO XXX : " si présente
            title = re.sub(r'^[A-Z]{2,5}[\s_\d]+\d+\s*:\s*', '', title_raw).strip()
            if not title:
                title = title_raw
            if not title:
                return None

            # --- Date limite ---
            deadline = self._extract_date(full_text)

            # Filtrer AO expirés
            if deadline and deadline < datetime.utcnow():
                return None

            # --- Les li suivants contiennent les métadonnées ---
            idx = all_lis.index(ao_li)
            meta = {}
            for li in all_lis[idx + 1: idx + 10]:
                # Arrêter si on rencontre le prochain AO
                if li.find("a", href=re.compile(r"ficheCsl")):
                    break
                text = li.get_text(strip=True)
                for key in ("Organisme", "Référence", "Nature des prestations",
                            "Lieu d'exécution", "Type de procédure"):
                    if text.startswith(key + " :") or text.startswith(key + "\xa0:"):
                        val = re.sub(r'^[^:]+:\s*', '', text).strip()
                        meta[key] = val
                        break

            buyer   = meta.get("Organisme")
            ref     = meta.get("Référence")
            nature  = meta.get("Nature des prestations", "").lower()
            lieu    = meta.get("Lieu d'exécution")

            market_type = CATEGORY_MAP.get(nature, MarketType.OTHER)

            # Département depuis le lieu ("Nord", "Val-de-Marne", code postal...)
            departments = self._extract_dept(lieu or "")

            return Tender(
                uid=f"vilogia_{source_id}",
                source=self.name,
                source_id=source_id,
                sources=[self.name],
                source_urls={self.name: detail_url},
                url=detail_url,
                title=title,
                buyer_name=buyer,
                departments=departments,
                execution_location=lieu,
                market_type=market_type,
                notice_nature=NoticeNature.APPEL_OFFRE,
                deadline=deadline,
                publication_date=None,
            )

        except Exception as exc:
            logger.debug("[vilogia] Erreur parse: %s", exc)
            return None

    @staticmethod
    def _extract_date(text: str) -> datetime | None:
        """Extrait la date limite depuis le texte (dd/mm/yyyy ou dd/mm/yy)."""
        match = re.search(r'(\d{2})/(\d{2})/(\d{2,4})', text)
        if match:
            try:
                year = int(match.group(3))
                if year < 100:
                    year += 2000
                return datetime(year, int(match.group(2)), int(match.group(1)))
            except ValueError:
                pass
        return None

    @staticmethod
    def _extract_dept(lieu: str) -> list[str]:
        """Extrait un code département depuis un lieu."""
        # Code postal entre parenthèses : "(94 350)" -> 94
        cp = re.search(r'\((\d{2})\s*\d{3}\)', lieu)
        if cp:
            return [cp.group(1)]
        # Département nommé
        DEPTS = {
            "nord": "59", "pas-de-calais": "62", "somme": "80",
            "gironde": "33", "landes": "40", "pyrénées-atlantiques": "64",
            "val-de-marne": "94", "val-d'oise": "95", "seine-et-marne": "77",
            "hauts-de-seine": "92", "seine-saint-denis": "93",
            "essonne": "91", "yvelines": "78",
        }
        lieu_lower = lieu.lower()
        for name, code in DEPTS.items():
            if name in lieu_lower:
                return [code]
        return []
