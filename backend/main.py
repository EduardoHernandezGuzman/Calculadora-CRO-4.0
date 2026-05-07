from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as api_router

app = FastAPI(title="Calculadora CRO API", version="4.0")

app.include_router(api_router, prefix="/api")

_HERE = Path(__file__).resolve().parent
FRONTEND_DIR = _HERE.parent / "frontend"

if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
