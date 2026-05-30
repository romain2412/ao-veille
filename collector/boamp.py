"""
Connecteur BOAMP — API OpenDataSoft (boamp-datadila.opendatasoft.com)

Documentation API :
  https://boamp-datadila.opendatasoft.com/api/explore/v2.1/console

Champs utilisés :
  idweb, objet, nomacheteur, nature, nature_libelle, type_marche,
  code_departement, dateparution, datelimitereponse, donnees
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import AsyncGenerator
from urllib.parse import urlencode

import json

import httpx

from collector.base import BaseSource
from models.tender import MarketType, NoticeNature, Tender

logger = logging.getLogger(__name__)

API_BASE = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1"
DATASET = "boamp"
PAGE_SIZE = 100

NATURE_MAP: dict[str, NoticeNature] = {
    "APPEL_OFFRE": NoticeNature.APPEL_OFFRE,
    "MARCHE_SIMPLIF": NoticeNature.MARCHE_SIMPLIF,
    "MARCHE_NEGOC": NoticeNature.MARCHE_NEGOC,
    "CONCESSION": NoticeNature.CONCESSION,
}

MARKET_MAP: dict[str, MarketType] = {
    "TRAVAUX": MarketType.TRAVAUX,
    "SERVICES": MarketType.SERVICES,
    "FOURNITURES": MarketType.FOURNITURES,
}

TENDER_URL_TPL = "https://www.boamp.fr/avis/detail/{idweb}"


class BOAMPSource(BaseSource):
    """Collecteur pour le Bulletin Officiel des Annonces des Marchés Publics."""

    name = "boamp"
    description = "BOAMP — API OpenDataSoft officielle"

    _FIELDS = (
        "idweb,id,objet,nomacheteur,nature,nature_libelle,"
        "type_marche,code_departement,dateparution,"
        "datelimitereponse,famille,donnees"
    )

    async def fetch(self, since: datetime) -> AsyncGenerator[Tender, None]:
        """
        Récupère tous les avis publiés depuis `since`.
        Pagine automatiquement jusqu'à épuisement des résultats.
        """
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S")
        where_clause = f"dateparution >= '{since_str}'"

        offset = 0
        total_fetched = 0

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                params = {
                    "select": self._FIELDS,
                    "where": where_clause,
                    "order_by": "dateparution DESC",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                }
                url = (
                    f"{API_BASE}/catalog/datasets/{DATASET}/records"
                    f"?{urlencode(params)}"
                )

                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.error("[boamp] Erreur HTTP: %s", exc)
                    break

                data = response.json()
                records = data.get("results", [])

                if not records:
                    break

                for record in records:
                    tender = self._parse_record(record)
                    if tender:
                        total_fetched += 1
                        yield tender

                offset += PAGE_SIZE
                total_count = data.get("total_count", 0)
                if offset >= total_count:
                    break

        logger.info("[boamp] %d avis récupérés depuis %s", total_fetched, since_str)

    def _parse_record(self, record: dict) -> Tender | None:
        try:
            idweb: str = record.get("idweb", "") or record.get("id", "")
            if not idweb:
                return None

            title: str = record.get("objet") or ""
            buyer: str = record.get("nomacheteur") or ""

            pub_date = self._parse_date(record.get("dateparution"))
            deadline = self._parse_date(record.get("datelimitereponse"))

            nature_raw: str = (record.get("nature") or "").upper()
            notice_nature = NATURE_MAP.get(nature_raw, NoticeNature.OTHER)

            market_type = MarketType.OTHER
            for mt_raw in (record.get("type_marche") or []):
                mt = MARKET_MAP.get((mt_raw or "").upper())
                if mt:
                    market_type = mt
                    break

            departments: list[str] = [
                str(d) for d in (record.get("code_departement") or []) if d
            ]

            donnees_raw = record.get("donnees") or {}
            # L'API peut renvoyer donnees comme string JSON ou comme dict
            if isinstance(donnees_raw, str):
                try:
                    donnees: dict = json.loads(donnees_raw)
                except (json.JSONDecodeError, ValueError):
                    donnees = {}
            else:
                donnees = donnees_raw
            description, cpv_codes, buyer_city, exec_location = (
                self._extract_donnees(donnees)
            )

            if not title and not description:
                return None

            return Tender(
                uid=f"boamp_{idweb.replace('-', '_')}",
                source=self.name,
                source_id=idweb,
                url=TENDER_URL_TPL.format(idweb=idweb),
                title=title,
                buyer_name=buyer or None,
                buyer_city=buyer_city,
                description=description,
                cpv_codes=cpv_codes,
                market_type=market_type,
                notice_nature=notice_nature,
                departments=departments,
                execution_location=exec_location,
                publication_date=pub_date,
                deadline=deadline,
            )

        except Exception as exc:
            logger.warning("[boamp] Impossible de parser: %s", exc)
            return None

    def _extract_donnees(
        self, donnees: dict
    ) -> tuple[str | None, list[str], str | None, str | None]:
        description: str | None = None
        cpv_codes: list[str] = []
        buyer_city: str | None = None
        exec_location: str | None = None

        if not donnees:
            return description, cpv_codes, buyer_city, exec_location

        objet = donnees.get("OBJET") or {}
        description = (
            objet.get("DESCRIPTION")
            or objet.get("TITRE_MARCHE")
            or objet.get("INTITULE")
        )

        cpv_raw = objet.get("CPV") or {}
        if isinstance(cpv_raw, dict):
            code = cpv_raw.get("CPV_PRINCIPAL") or cpv_raw.get("CODE")
            if code:
                cpv_codes.append(str(code))
        elif isinstance(cpv_raw, list):
            cpv_codes = [str(c) for c in cpv_raw if c]

        exec_location = (
            objet.get("LIEU_EXECUTION")
            or objet.get("LIEU_PRINCIPAL_EXECUTION")
        )

        identite = donnees.get("IDENTITE") or {}
        if isinstance(identite, dict):
            buyer_city = identite.get("VILLE") or identite.get("CP_VILLE")

        return description, cpv_codes, buyer_city, exec_location

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value[:19], fmt[:len(value[:19])])
            except ValueError:
                continue
        return None
