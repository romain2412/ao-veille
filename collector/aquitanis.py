"""
Collecteur Aquitanis — aquitanis.e-marchespublics.com

Aquitanis est l'Office Public de l'Habitat (OPH) de Bordeaux Métropole.
Sa salle des marchés tourne sur la plateforme **Dematis e-marchespublics**.

Parcours public (sans authentification) découvert le 2026-05-31 :
  La page d'accueil contient un moteur de recherche. Le bouton « Tout afficher »
  mène à une page de résultats HTML statique à URL propre :

    /pack/recherche_d_appels_d_offres_marches_publics_<p>_aapc_________<p>.html

  où `aapc` = « avis de marché » (appels publics à concurrence) et <p> = page.
  Cette page est servie en HTML pur → httpx + BeautifulSoup suffisent
  (pas besoin de Playwright), ce qui est bien plus robuste.

Structure DOM d'un avis (vérifiée le 2026-05-31) :
  div.list-organisme
    div.orga                              ← un avis
      div.resultatOrganismeHaut          "AQUITANIS - OPH … Réf. : 20260030"
      div.resultatOrganismeMilieu        titre de la consultation
      div.resultatOrganismeBas
        div.resultatOrganismeBasTab1      type de procédure (Proc.Adapt./Proc.Négo.)
        div.resultatOrganismeBasTab2      liens (Avis / RC / Dossier / Questions / Dépôt)
        div.resultatOrganismeBasTab4      date(s) — la dernière = date limite
      a[href*="annonce_marche_public_222_<id>.html"]   ← lien "Avis" = détail

Aquitanis = acheteur unique en Gironde → buyer « Aquitanis », département 33
(région prioritaire Nouvelle-Aquitaine).
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

BASE_URL = "https://aquitanis.e-marchespublics.com"
# <p> apparaît deux fois dans l'URL (numéro de page en début et en fin)
RESULTS_URL_TPL = (
    BASE_URL
    + "/pack/recherche_d_appels_d_offres_marches_publics_{p}_aapc_________{p}.html"
)
MAX_PAGES = 10  # garde-fou (Aquitanis a en général < 10 avis en cours)

DEFAULT_DEPARTMENT = "33"   # Gironde
DEFAULT_BUYER = "Aquitanis"

# id de consultation dans les liens "annonce_marche_public_222_<id>.html"
AVIS_ID_RE = re.compile(r"annonce_marche_public_\d+_(\d+)")
REF_RE = re.compile(r"R[ée]f\.?\s*:?\s*(\S+)")
DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


class AquitanisSource(BaseSource):
    """Collecteur pour la salle des marchés Aquitanis (Dematis), HTML statique."""

    name = "aquitanis"
    description = "Aquitanis — OPH de Bordeaux Métropole (e-marchespublics)"

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error("[aquitanis] BeautifulSoup non installé")
            return

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        seen: set[str] = set()
        total = 0

        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True, headers=headers
        ) as client:
            for page in range(1, MAX_PAGES + 1):
                url = RESULTS_URL_TPL.format(p=page)
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.error("[aquitanis] Erreur HTTP page %d: %s", page, exc)
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                blocks = soup.select("div.orga")
                if not blocks:
                    break

                page_new = 0
                for block in blocks:
                    tender = self._parse_block(block)
                    if tender and tender.source_id not in seen:
                        seen.add(tender.source_id)
                        total += 1
                        page_new += 1
                        yield tender

                # Dernière page atteinte (aucun nouvel avis) → on arrête
                if page_new == 0:
                    break

        logger.info("[aquitanis] %d AO collectés au total", total)

    def _parse_block(self, block) -> Tender | None:
        try:
            # --- Lien "Avis" → URL détail + id de consultation ---
            avis = block.find("a", href=AVIS_ID_RE)
            href = avis.get("href", "") if avis else ""
            detail_url = (BASE_URL + href) if href.startswith("/") else (href or BASE_URL)
            m_id = AVIS_ID_RE.search(href)
            cons_id = m_id.group(1) if m_id else ""

            # --- Acheteur + référence (resultatOrganismeHaut) ---
            haut_el = block.select_one("div.resultatOrganismeHaut")
            haut = self._clean(haut_el.get_text(" ")) if haut_el else ""
            m_ref = REF_RE.search(haut)
            ref = m_ref.group(1).strip() if m_ref else ""

            # On dédoublonne par RÉFÉRENCE (ex: 20260011) : un marché et ses
            # rectificatifs partagent la même réf mais ont des id de consultation
            # différents — on ne veut qu'une seule entrée par référence.
            source_id = ref or cons_id
            if not source_id:
                return None

            # --- Titre (resultatOrganismeMilieu) ---
            title_el = block.select_one("div.resultatOrganismeMilieu")
            title = self._clean(title_el.get_text(" ")) if title_el else ""
            if not title:
                title = ref or "Consultation Aquitanis"

            # --- Type de procédure (resultatOrganismeBasTab1) ---
            proc_el = block.select_one("div.resultatOrganismeBasTab1")
            proc = self._clean(proc_el.get_text(" ")).lower() if proc_el else ""
            if "nego" in proc or "négo" in proc:
                notice_nature = NoticeNature.MARCHE_NEGOC
            elif "adapt" in proc:
                notice_nature = NoticeNature.MARCHE_SIMPLIF
            else:
                notice_nature = NoticeNature.APPEL_OFFRE

            # --- Type de marché : déduit du titre (best effort) ---
            market_type = self._infer_market_type(title)

            # --- Date limite (resultatOrganismeBasTab4) : dernière date affichée ---
            tab4_el = block.select_one("div.resultatOrganismeBasTab4")
            date_src = (
                self._clean(tab4_el.get_text(" "))
                if tab4_el
                else self._clean(block.get_text(" "))
            )
            deadline = self._last_date(date_src)

            # Filtrer les avis dont la date limite est dépassée
            if deadline and deadline < datetime.utcnow():
                return None

            return Tender(
                uid=f"aquitanis_{source_id}",
                source=self.name,
                source_id=source_id,
                sources=[self.name],
                source_urls={self.name: detail_url},
                url=detail_url,
                title=title,
                buyer_name=DEFAULT_BUYER,
                departments=[DEFAULT_DEPARTMENT],
                market_type=market_type,
                notice_nature=notice_nature,
                publication_date=None,
                deadline=deadline,
            )

        except Exception as exc:
            logger.debug("[aquitanis] Erreur parse: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "")).strip()

    @staticmethod
    def _infer_market_type(title: str) -> MarketType:
        t = title.lower()
        if t.startswith("travaux") or "travaux" in t[:40]:
            return MarketType.TRAVAUX
        if "fourniture" in t:
            return MarketType.FOURNITURES
        if any(k in t for k in ("maîtrise d'œuvre", "maitrise d'oeuvre", "moe",
                                 "mission", "étude", "etude", "service",
                                 "entretien", "accord cadre", "accord-cadre")):
            return MarketType.SERVICES
        return MarketType.OTHER

    @staticmethod
    def _last_date(text: str) -> datetime | None:
        """Retourne la dernière date dd/mm/yyyy du texte (= date limite)."""
        matches = DATE_RE.findall(text or "")
        if not matches:
            return None
        d, mth, y = matches[-1]
        try:
            return datetime(int(y), int(mth), int(d))
        except ValueError:
            return None
