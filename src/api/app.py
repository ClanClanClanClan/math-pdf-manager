"""FastAPI application exposing discovery and acquisition endpoints."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import Response
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is required for the API server. Install dependencies with `pip install -r requirements.txt`."
    ) from exc

from acquisition.engine import AcquisitionConfig, AcquisitionEngine
from discovery import DiscoveryEngine, PaperCandidate
from maintenance.system import MaintenanceSystem
from core.database import AsyncPaperDatabase
from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest

app = FastAPI(title="Academic Paper Manager API", version="0.1.0")

DISCOVERY_COUNTER = Counter("discovery_requests_total", "Total discovery requests")
ACQUISITION_COUNTER = Counter("acquisition_requests_total", "Total acquisition requests")
MAINTENANCE_COUNTER = Counter("maintenance_runs_total", "Total maintenance runs")


class DiscoveryRequest(BaseModel):
    query: str = Field(..., description="Search query (e.g., 'quantum computing')")
    max_results: int = Field(10, ge=1, le=50)


class DiscoveryResponse(BaseModel):
    results: List[Dict[str, Any]]


class AcquisitionRequest(BaseModel):
    paper: Dict[str, Any]


class AcquisitionResponse(BaseModel):
    success: bool
    strategy: str
    file_path: Optional[str]
    message: Optional[str]


@app.on_event("startup")
async def startup_event() -> None:
    app.state.discovery_engine = DiscoveryEngine()
    app.state.acquisition_engine = AcquisitionEngine(config=AcquisitionConfig())
    app.state.database = AsyncPaperDatabase(str(Path("papers.db")))
    app.state.maintenance_system = MaintenanceSystem()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await app.state.discovery_engine.close()
    await app.state.acquisition_engine.close()
    # AsyncPaperDatabase uses on-demand connections; nothing to close.


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/discovery/query", response_model=DiscoveryResponse)
async def discovery_query(payload: DiscoveryRequest) -> DiscoveryResponse:
    engine: DiscoveryEngine = app.state.discovery_engine
    DISCOVERY_COUNTER.inc()
    candidates = await engine.search_by_query(payload.query, max_results=payload.max_results)
    result_payload = [
        {
            "title": candidate.title,
            "authors": candidate.authors,
            "doi": candidate.doi,
            "arxiv_id": candidate.arxiv_id,
            "source": candidate.source,
            "url": candidate.url,
            "published_year": candidate.published_year,
        }
        for candidate in candidates
    ]
    return DiscoveryResponse(results=result_payload)


@app.post("/acquisition/acquire", response_model=AcquisitionResponse)
async def acquisition_acquire(payload: AcquisitionRequest) -> AcquisitionResponse:
    engine: AcquisitionEngine = app.state.acquisition_engine
    ACQUISITION_COUNTER.inc()
    result = await engine.acquire_paper(payload.paper)
    return AcquisitionResponse(
        success=result.success,
        strategy=result.strategy,
        file_path=str(result.file_path) if result.file_path else None,
        message=result.message,
    )


@app.post("/maintenance/run")
async def maintenance_run() -> Dict[str, Any]:
    db: AsyncPaperDatabase = app.state.database
    maintenance: MaintenanceSystem = app.state.maintenance_system

    MAINTENANCE_COUNTER.inc()

    papers = await db.list_papers()
    metadata_list = []
    file_paths = []
    for record in papers:
        metadata_list.append({
            'doi': record.doi,
            'arxiv_id': record.arxiv_id,
            'added_at': record.created_at,
        })
        file_paths.append(Path(record.file_path))

    duplicate_map = {}
    duplicates = await db.find_duplicates(similarity_threshold=0.8)
    for paper1, paper2, score in duplicates:
        key = f"{paper1.id}-{paper2.id}"
        duplicate_map[key] = [Path(paper1.file_path), Path(paper2.file_path)]

    summary = await maintenance.run_maintenance(metadata_list, file_paths, duplicate_map)
    return {
        'update_report': asdict(summary.update_report),
        'quality_report': asdict(summary.quality_report),
    }


@app.get("/organization/duplicates")
async def organization_duplicates() -> Dict[str, Any]:
    db: AsyncPaperDatabase = app.state.database
    duplicates = await db.find_duplicates(similarity_threshold=0.8)
    payload = [
        {
            'paper1': paper1.to_dict() if hasattr(paper1, 'to_dict') else paper1.__dict__,
            'paper2': paper2.to_dict() if hasattr(paper2, 'to_dict') else paper2.__dict__,
            'similarity': score,
        }
        for paper1, paper2, score in duplicates
    ]
    return {'duplicates': payload}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


__all__ = ["app"]
