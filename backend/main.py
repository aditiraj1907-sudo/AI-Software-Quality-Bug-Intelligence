"""FastAPI application.

Run from the project root:

    uvicorn backend.main:app --reload

then open http://127.0.0.1:8000. The same server serves the API under /api
and the web pages from the frontend/ folder.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import db
from ml.model import get_model

from . import service
from .analyzer import RULES
from .schemas import AddFileRequest, AnalyzeRequest, PredictRequest

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    get_model()  # loads the saved models, or trains them on first run
    service.ensure_seeded()
    yield


app = FastAPI(title="Quality & Bug Intelligence", version="1.0.0", lifespan=lifespan)

# Only needed if the frontend is hosted somewhere else (for example GitHub Pages).
# Set QBI_CORS to a comma-separated list of allowed origins.
_origins = [o.strip() for o in os.environ.get("QBI_CORS", "").split(",") if o.strip()]
if _origins:
    app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "rules": len(RULES), "modelSamples": get_model().metrics["samples"]}


@app.get("/api/samples")
def samples():
    return service.load_samples()


@app.post("/api/analyze")
def analyze_code(req: AnalyzeRequest):
    """Analyze code without saving it."""
    return service.analyze_code(req.code, req.language, req.filename)


@app.get("/api/project")
def project():
    return service.project_state()


@app.post("/api/project/files", status_code=201)
def add_file(req: AddFileRequest):
    """Analyze code and add it to the project (saved in the database)."""
    return service.add_file(req.code, req.language, req.filename)


@app.delete("/api/project/files/{file_id}")
def remove_file(file_id: int):
    if not service.remove_file(file_id):
        raise HTTPException(status_code=404, detail="That file is not in the project.")
    return {"deleted": file_id}


@app.post("/api/project/reset")
def reset_project():
    service.reset_to_samples()
    return service.project_state()


@app.get("/api/findings")
def findings(severity: Optional[str] = Query(None, pattern="^(critical|high|medium|low)$"),
             category: Optional[str] = None, file: Optional[str] = None):
    return service.findings(severity, category, file)


@app.get("/api/report")
def report():
    return service.build_report()


@app.post("/api/predict")
def predict(req: PredictRequest):
    """Predict severity and category of a bug described in plain words."""
    return get_model().predict(req.text)


@app.get("/api/rules")
def rules():
    return service.rules_overview()


@app.get("/api/model")
def model_info():
    return get_model().metrics


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
