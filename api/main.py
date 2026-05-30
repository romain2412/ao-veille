"""
Application FastAPI — portail de veille AO FB VRD.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, tenders
from storage.database import init_db

app = FastAPI(
    title="Veille AO — FB VRD",
    description="API de consultation des appels d'offres VRD et Paysage",
    version="1.0.0",
)

# CORS — autorise le frontend (à restreindre en production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(tenders.router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
