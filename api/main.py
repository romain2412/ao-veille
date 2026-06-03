"""
Application FastAPI — portail de veille AO FB VRD.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.rate_limit import limiter
from api.routes import admin, auth, invite, tenders

app = FastAPI(
    title="Veille AO — FB VRD",
    description="API de consultation des appels d'offres VRD et Paysage",
    version="1.0.0",
)

# Branche le limiter sur l'app + réponse 429 propre quand la limite est dépassée
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — origines autorisées explicitement via CORS_ORIGINS (séparées par virgule)
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(tenders.router)
app.include_router(admin.router)
app.include_router(invite.router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
