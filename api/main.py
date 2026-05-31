"""
Application FastAPI — portail de veille AO FB VRD.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, tenders

app = FastAPI(
    title="Veille AO — FB VRD",
    description="API de consultation des appels d'offres VRD et Paysage",
    version="1.0.0",
)

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


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
