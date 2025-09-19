"""FastAPI application exposing discovery and acquisition endpoints."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is required for the API server. Install dependencies with `pip install -r requirements.txt`."
    ) from exc

from acquisition.engine import AcquisitionConfig, AcquisitionEngine
from discovery import DiscoveryEngine, PaperCandidate

app = FastAPI(title="Academic Paper Manager API", version="0.1.0")


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


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await app.state.discovery_engine.close()
    await app.state.acquisition_engine.close()


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/discovery/query", response_model=DiscoveryResponse)
async def discovery_query(payload: DiscoveryRequest) -> DiscoveryResponse:
    engine: DiscoveryEngine = app.state.discovery_engine
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
    result = await engine.acquire_paper(payload.paper)
    return AcquisitionResponse(
        success=result.success,
        strategy=result.strategy,
        file_path=str(result.file_path) if result.file_path else None,
        message=result.message,
    )


__all__ = ["app"]
