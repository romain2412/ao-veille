"""
Rate-limiter partagé de l'application.

Placé dans son propre module pour être importable à la fois par `api.main`
(qui le branche sur l'app) et par les routes (qui posent les limites), sans
créer d'import circulaire.

Identification du client par IP RÉELLE : l'app tourne derrière des reverse-proxies
(Caddy → nginx), donc l'IP de connexion vue par l'API est celle du proxy. On lit
donc l'en-tête `X-Forwarded-For` (1ʳᵉ valeur = client d'origine), avec repli sur
l'IP directe si l'en-tête est absent (cas dev/local).

Sécurité : se fier à `X-Forwarded-For` n'est sûr QUE parce que l'API n'est jamais
exposée directement (réseau Docker interne ; seul Caddy a un port public). Un
client externe ne peut donc pas forger cet en-tête.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """IP réelle du client : 1ʳᵉ entrée de X-Forwarded-For, sinon IP directe."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Format : "client, proxy1, proxy2" → on prend le client d'origine.
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)
