"""
Phase 7: API Endpoint Audit

Comprehensive audit of src/api/app.py -- the FastAPI application that exposes
discovery, acquisition, maintenance, organization, and metrics endpoints.

AUDIT FINDINGS SUMMARY
======================
CRITICAL:
  1. /maintenance/run calls ``db.list_papers()`` but AsyncPaperDatabase has NO
     ``list_papers()`` method.  The endpoint WILL crash with ``AttributeError``
     at runtime.
  2. /organization/duplicates falls back to ``paper.__dict__`` when
     ``to_dict()`` is absent.  For dataclass ``PaperRecord`` this exposes
     internal state (timestamps, hashes, raw SQL row data) to the API consumer.

SECURITY:
  3. CORS ``allow_origins=["*"]`` permits any origin -- no access control.
  4. Zero authentication or authorization middleware.

DEPRECATION:
  5. ``@app.on_event("startup")`` / ``@app.on_event("shutdown")`` are
     deprecated since FastAPI 0.93; the replacement is ``lifespan`` context
     manager.

DESIGN:
  6. ``PaperRecord`` lacks a ``to_dict()`` method, so the /organization
     endpoint's primary serialisation path is dead code.
"""
from __future__ import annotations

import asyncio
import sys
import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Guard: skip entire module when FastAPI / httpx are absent
# ---------------------------------------------------------------------------
fastapi = pytest.importorskip("fastapi")
httpx_mod = pytest.importorskip("httpx")

# ---------------------------------------------------------------------------
# Mock heavy/optional third-party modules that the API file imports at the
# module level BEFORE we import the app itself.
# ---------------------------------------------------------------------------
_MODULES_TO_MOCK = [
    "publishers",
    "publishers.unified_downloader",
]

# Only mock aiosqlite if it's not already importable (avoid breaking
# database audit tests that run in the same process).
try:
    import aiosqlite as _aio_check  # noqa: F401
except ImportError:
    _MODULES_TO_MOCK.append("aiosqlite")

for _mod_name in _MODULES_TO_MOCK:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

# Mock ``publishers.DownloadResult`` so AcquisitionEngine can reference it.
_mock_publishers = sys.modules["publishers"]
_mock_publishers.DownloadResult = MagicMock()

# Mock prometheus_client with just enough surface area for the app
if "prometheus_client" not in sys.modules:
    sys.modules["prometheus_client"] = MagicMock()

_mock_prom = sys.modules["prometheus_client"]
_mock_prom.Counter = MagicMock(return_value=MagicMock())
_mock_prom.CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
_mock_prom.generate_latest = MagicMock(return_value=b"# HELP fake_metric\n")

# ---------------------------------------------------------------------------
# Fix: api/__init__.py imports ArxivAPIClient → xml_parser.py which uses
# defusedxml.ElementTree.Element as a type annotation.  defusedxml's ET
# wrapper does NOT expose Element.  Patch it before importing anything
# from the api package.
# ---------------------------------------------------------------------------
try:
    import defusedxml.ElementTree as _det
    if not hasattr(_det, "Element"):
        import xml.etree.ElementTree as _real_et
        _det.Element = _real_et.Element
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Now it is safe to import the app module and its Pydantic models.
# ---------------------------------------------------------------------------
from api.app import (  # noqa: E402
    app,
    AcquisitionRequest,
    AcquisitionResponse,
    CollectionSummaryResponse,
    DiscoveryRequest,
    DiscoveryResponse,
)
from fastapi.testclient import TestClient  # noqa: E402


# ============================================================================
# Helpers
# ============================================================================

@dataclass
class _FakePaperRecord:
    """Lightweight stand-in for ``core.database.PaperRecord``."""
    id: int = 1
    file_path: str = "/papers/test.pdf"
    title: str = "Test Paper"
    authors: str = '["Author A"]'
    publication_date: Optional[str] = "2024-01-01"
    arxiv_id: Optional[str] = "2401.00001"
    doi: Optional[str] = "10.1234/test"
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    abstract: str = ""
    keywords: str = "[]"
    research_areas: str = "[]"
    paper_type: str = "published"
    source: str = "crossref"
    confidence: float = 0.95
    file_size: int = 12345
    file_hash: str = "abc123"
    created_at: str = "2024-01-01T00:00:00"
    updated_at: str = "2024-06-01T00:00:00"


@dataclass
class _FakeAcquisitionResult:
    """Mirrors ``acquisition.engine.AcquisitionResult``."""
    success: bool = True
    strategy: str = "open_access"
    file_path: Optional[Path] = None
    message: Optional[str] = None


@pytest.fixture()
def client():
    """Create a ``TestClient`` with mocked ``app.state`` dependencies."""
    # Populate app.state so endpoints don't rely on the startup event
    app.state.discovery_engine = MagicMock()
    app.state.acquisition_engine = MagicMock()
    app.state.database = MagicMock()
    app.state.maintenance_system = MagicMock()

    # TestClient triggers startup/shutdown events itself; suppress them here
    # by overriding to no-ops so mocked engines are not replaced.
    with (
        patch.object(app, "router", wraps=app.router),
    ):
        # Use raise_server_exceptions=False for tests that expect 500s
        yield TestClient(app, raise_server_exceptions=False)


# ============================================================================
# Section 7A: Health endpoint
# ============================================================================

class TestHealthEndpoint:
    """GET /health -- the only dependency-free endpoint."""

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_body(self, client: TestClient):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}


# ============================================================================
# Section 7B: Pydantic request/response model validation
# ============================================================================

class TestPydanticModels:
    """Verify the Pydantic models defined in app.py parse and serialise."""

    # -- DiscoveryRequest ---------------------------------------------------

    def test_discovery_request_valid(self):
        req = DiscoveryRequest(query="stochastic calculus")
        assert req.query == "stochastic calculus"
        assert req.max_results == 10  # default

    def test_discovery_request_max_results_bounds(self):
        req = DiscoveryRequest(query="test", max_results=50)
        assert req.max_results == 50

    def test_discovery_request_max_results_below_minimum(self):
        with pytest.raises(Exception):
            DiscoveryRequest(query="test", max_results=0)

    def test_discovery_request_max_results_above_maximum(self):
        with pytest.raises(Exception):
            DiscoveryRequest(query="test", max_results=51)

    def test_discovery_request_missing_query(self):
        """query is required (Field(...))."""
        with pytest.raises(Exception):
            DiscoveryRequest()  # type: ignore[call-arg]

    # -- DiscoveryResponse --------------------------------------------------

    def test_discovery_response_valid(self):
        resp = DiscoveryResponse(results=[{"title": "Paper A"}])
        assert len(resp.results) == 1

    def test_discovery_response_empty_results(self):
        resp = DiscoveryResponse(results=[])
        assert resp.results == []

    # -- AcquisitionRequest -------------------------------------------------

    def test_acquisition_request_valid(self):
        req = AcquisitionRequest(paper={"doi": "10.1234/test"})
        assert req.paper["doi"] == "10.1234/test"

    def test_acquisition_request_empty_paper_dict(self):
        req = AcquisitionRequest(paper={})
        assert req.paper == {}

    # -- AcquisitionResponse ------------------------------------------------

    def test_acquisition_response_success(self):
        resp = AcquisitionResponse(
            success=True,
            strategy="open_access",
            file_path="/tmp/paper.pdf",
            message=None,
        )
        assert resp.success is True
        assert resp.file_path == "/tmp/paper.pdf"

    def test_acquisition_response_failure(self):
        resp = AcquisitionResponse(
            success=False,
            strategy="none",
            file_path=None,
            message="All strategies failed",
        )
        assert resp.success is False
        assert resp.message == "All strategies failed"

    # -- CollectionSummaryResponse ------------------------------------------

    def test_collection_summary_valid(self):
        resp = CollectionSummaryResponse(
            total_papers=42,
            by_type={"published": 30, "working_paper": 12},
            recent_additions=5,
            total_duplicates=2,
        )
        assert resp.total_papers == 42
        assert resp.by_type["published"] == 30


# ============================================================================
# Section 7C: Discovery endpoint
# ============================================================================

class TestDiscoveryEndpoint:
    """POST /discovery/query"""

    def test_discovery_success(self, client: TestClient):
        mock_engine = app.state.discovery_engine
        mock_candidate = MagicMock(
            title="Test Paper",
            authors=["Author A"],
            doi="10.1234/test",
            arxiv_id="2401.00001",
            source="arxiv",
            url="https://arxiv.org/abs/2401.00001",
            published_year=2024,
        )
        mock_engine.search_by_query = AsyncMock(return_value=[mock_candidate])

        response = client.post(
            "/discovery/query",
            json={"query": "stochastic processes", "max_results": 5},
        )
        assert response.status_code == 200
        body = response.json()
        assert "results" in body
        assert len(body["results"]) == 1
        assert body["results"][0]["title"] == "Test Paper"
        assert body["results"][0]["doi"] == "10.1234/test"

    def test_discovery_empty_results(self, client: TestClient):
        app.state.discovery_engine.search_by_query = AsyncMock(return_value=[])

        response = client.post(
            "/discovery/query",
            json={"query": "nonexistent topic"},
        )
        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_discovery_invalid_body_missing_query(self, client: TestClient):
        """Request validation: query is mandatory."""
        response = client.post("/discovery/query", json={})
        assert response.status_code == 422

    def test_discovery_invalid_body_max_results_zero(self, client: TestClient):
        response = client.post(
            "/discovery/query",
            json={"query": "test", "max_results": 0},
        )
        assert response.status_code == 422

    def test_discovery_invalid_body_max_results_too_high(self, client: TestClient):
        response = client.post(
            "/discovery/query",
            json={"query": "test", "max_results": 100},
        )
        assert response.status_code == 422

    def test_discovery_engine_exception_propagates(self, client: TestClient):
        """If the engine raises, FastAPI returns 500."""
        app.state.discovery_engine.search_by_query = AsyncMock(
            side_effect=RuntimeError("upstream failure"),
        )
        response = client.post(
            "/discovery/query",
            json={"query": "boom"},
        )
        assert response.status_code == 500


# ============================================================================
# Section 7D: Acquisition endpoint
# ============================================================================

class TestAcquisitionEndpoint:
    """POST /acquisition/acquire"""

    def test_acquire_success(self, client: TestClient):
        fake_result = _FakeAcquisitionResult(
            success=True,
            strategy="open_access",
            file_path=Path("/downloads/paper.pdf"),
            message=None,
        )
        app.state.acquisition_engine.acquire_paper = AsyncMock(
            return_value=fake_result,
        )

        response = client.post(
            "/acquisition/acquire",
            json={"paper": {"doi": "10.1234/test", "title": "Test Paper"}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["strategy"] == "open_access"
        assert body["file_path"] == "/downloads/paper.pdf"

    def test_acquire_failure(self, client: TestClient):
        fake_result = _FakeAcquisitionResult(
            success=False,
            strategy="none",
            file_path=None,
            message="All acquisition strategies failed",
        )
        app.state.acquisition_engine.acquire_paper = AsyncMock(
            return_value=fake_result,
        )

        response = client.post(
            "/acquisition/acquire",
            json={"paper": {"doi": "10.0000/missing"}},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "All acquisition strategies failed"

    def test_acquire_missing_paper_field(self, client: TestClient):
        """``paper`` is required in AcquisitionRequest."""
        response = client.post("/acquisition/acquire", json={})
        assert response.status_code == 422

    def test_acquire_engine_exception(self, client: TestClient):
        app.state.acquisition_engine.acquire_paper = AsyncMock(
            side_effect=Exception("download blew up"),
        )
        response = client.post(
            "/acquisition/acquire",
            json={"paper": {"title": "Kaboom"}},
        )
        assert response.status_code == 500


# ============================================================================
# Section 7E: Maintenance endpoint -- CRITICAL BUG
# ============================================================================

class TestMaintenanceEndpoint:
    """POST /maintenance/run

    CRITICAL AUDIT FINDING
    ----------------------
    The endpoint calls ``await db.list_papers()`` on line 125 of app.py.
    ``AsyncPaperDatabase`` does NOT define ``list_papers()``.  The available
    methods are:
        add_paper, get_paper, get_paper_by_path, search_papers,
        find_duplicates, get_papers_by_type, update_paper, get_statistics.

    At runtime this endpoint WILL raise ``AttributeError: 'AsyncPaperDatabase'
    object has no attribute 'list_papers'``.

    RECOMMENDED FIX: Either add a ``list_papers()`` method to
    ``AsyncPaperDatabase`` or replace the call with ``search_papers('')`` or a
    new paginated query.
    """

    def test_list_papers_method_exists_on_real_database(self):
        """FIXED: AsyncPaperDatabase now has list_papers() method."""
        from core.database import AsyncPaperDatabase

        db = AsyncPaperDatabase.__new__(AsyncPaperDatabase)
        assert hasattr(db, "list_papers"), (
            "list_papers() should exist on AsyncPaperDatabase"
        )
        assert asyncio.iscoroutinefunction(db.list_papers), (
            "list_papers() should be an async method"
        )

    def test_list_papers_method_is_public(self):
        """Verify list_papers is a public async method on AsyncPaperDatabase."""
        from core.database import AsyncPaperDatabase

        public_methods = [
            m for m in dir(AsyncPaperDatabase)
            if not m.startswith("_") and callable(getattr(AsyncPaperDatabase, m))
        ]
        assert "list_papers" in public_methods, (
            "list_papers() should be a public method on AsyncPaperDatabase"
        )

    def test_maintenance_run_with_fully_mocked_dependencies(self, client: TestClient):
        """When list_papers is mocked away, the rest of the flow is testable."""
        fake_paper = _FakePaperRecord()

        mock_db = app.state.database
        mock_db.list_papers = AsyncMock(return_value=[fake_paper])
        mock_db.find_duplicates = AsyncMock(return_value=[])

        @dataclass
        class _FakeUpdateReport:
            checked_papers: int = 0
            publication_updates: list = field(default_factory=list)
            missing_files: list = field(default_factory=list)

        @dataclass
        class _FakeQualityReport:
            total_files: int = 0
            invalid_files: list = field(default_factory=list)
            duplicate_groups: list = field(default_factory=list)

        @dataclass
        class _FakeSummary:
            update_report: _FakeUpdateReport = field(default_factory=_FakeUpdateReport)
            quality_report: _FakeQualityReport = field(default_factory=_FakeQualityReport)

        app.state.maintenance_system.run_maintenance = AsyncMock(
            return_value=_FakeSummary(),
        )

        response = client.post("/maintenance/run")
        assert response.status_code == 200
        body = response.json()
        assert "update_report" in body
        assert "quality_report" in body


# ============================================================================
# Section 7F: Organization / duplicates endpoint -- AUDIT FINDING
# ============================================================================

class TestOrganizationDuplicatesEndpoint:
    """GET /organization/duplicates

    AUDIT FINDING
    -------------
    ``PaperRecord`` is a dataclass and has no ``to_dict()`` method.  The
    endpoint code (line 155) is:

        paper1.to_dict() if hasattr(paper1, 'to_dict') else paper1.__dict__

    The ``hasattr`` guard means it always falls through to ``__dict__``.  While
    ``__dict__`` works for dataclasses, it exposes ALL internal state including
    timestamps, file hashes, and confidence scores -- none of which should be
    part of a public API response.

    RECOMMENDED FIX: Add an explicit serialisation method (e.g. ``to_dict()``)
    to ``PaperRecord`` that returns only the intended public fields, or use
    ``dataclasses.asdict()`` with field filtering.
    """

    def test_paper_record_lacks_to_dict(self):
        """Confirm PaperRecord has no to_dict(), so the fallback is always used."""
        from core.database import PaperRecord

        record = PaperRecord(
            file_path="/test.pdf",
            title="Test",
            authors="[]",
        )
        assert not hasattr(record, "to_dict"), (
            "If to_dict() has been added, revisit this audit finding."
        )

    def test_dict_fallback_leaks_internal_fields(self):
        """__dict__ exposes fields that should not be public API data."""
        from core.database import PaperRecord

        record = PaperRecord(
            id=1,
            file_path="/test.pdf",
            title="Test",
            authors="[]",
        )
        raw = record.__dict__
        # These internal-ish fields leak through __dict__
        leaked_fields = {"file_hash", "confidence", "created_at", "updated_at"}
        assert leaked_fields.issubset(raw.keys()), (
            f"Expected internal fields to leak via __dict__; got keys {raw.keys()}"
        )

    def test_duplicates_returns_list(self, client: TestClient):
        paper1 = _FakePaperRecord(id=1, title="Paper A")
        paper2 = _FakePaperRecord(id=2, title="Paper B")

        app.state.database.find_duplicates = AsyncMock(
            return_value=[(paper1, paper2, 0.92)],
        )

        response = client.get("/organization/duplicates")
        assert response.status_code == 200
        body = response.json()
        assert "duplicates" in body
        assert len(body["duplicates"]) == 1
        dup = body["duplicates"][0]
        assert dup["similarity"] == 0.92
        assert "paper1" in dup
        assert "paper2" in dup

    def test_duplicates_empty(self, client: TestClient):
        app.state.database.find_duplicates = AsyncMock(return_value=[])

        response = client.get("/organization/duplicates")
        assert response.status_code == 200
        assert response.json()["duplicates"] == []

    def test_duplicates_fallback_uses_dunder_dict(self, client: TestClient):
        """Verify the __dict__ fallback is what actually runs."""
        paper1 = _FakePaperRecord(id=10, title="Alpha")
        paper2 = _FakePaperRecord(id=20, title="Beta")

        # Ensure there is no to_dict
        assert not hasattr(paper1, "to_dict")

        app.state.database.find_duplicates = AsyncMock(
            return_value=[(paper1, paper2, 0.85)],
        )

        response = client.get("/organization/duplicates")
        assert response.status_code == 200
        dup = response.json()["duplicates"][0]

        # __dict__ serialisation means ALL dataclass fields appear
        assert "file_hash" in dup["paper1"], (
            "AUDIT: __dict__ fallback leaks file_hash to API consumers."
        )
        assert "confidence" in dup["paper1"], (
            "AUDIT: __dict__ fallback leaks confidence to API consumers."
        )


# ============================================================================
# Section 7G: Collection summary endpoint
# ============================================================================

class TestCollectionSummaryEndpoint:
    """GET /collection/summary"""

    def test_summary_success(self, client: TestClient):
        app.state.database.get_statistics = AsyncMock(
            return_value={
                "total_papers": 100,
                "by_type": {"published": 80, "working_paper": 20},
                "recent_additions": 7,
                "total_duplicates": 3,
            },
        )

        response = client.get("/collection/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["total_papers"] == 100
        assert body["by_type"]["published"] == 80
        assert body["recent_additions"] == 7
        assert body["total_duplicates"] == 3

    def test_summary_defaults_for_missing_keys(self, client: TestClient):
        """get_statistics() might return partial data; the endpoint uses .get()."""
        app.state.database.get_statistics = AsyncMock(return_value={})

        response = client.get("/collection/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["total_papers"] == 0
        assert body["by_type"] == {}
        assert body["recent_additions"] == 0
        assert body["total_duplicates"] == 0

    def test_summary_matches_response_model(self, client: TestClient):
        """Ensure the response validates against CollectionSummaryResponse."""
        app.state.database.get_statistics = AsyncMock(
            return_value={
                "total_papers": 5,
                "by_type": {},
                "recent_additions": 1,
                "total_duplicates": 0,
            },
        )
        response = client.get("/collection/summary")
        body = response.json()
        # Should parse without error
        model = CollectionSummaryResponse(**body)
        assert model.total_papers == 5


# ============================================================================
# Section 7H: Metrics endpoint
# ============================================================================

class TestMetricsEndpoint:
    """GET /metrics -- returns Prometheus exposition format."""

    def test_metrics_returns_200(self, client: TestClient):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client: TestClient):
        response = client.get("/metrics")
        # Content-Type should be the Prometheus text format
        ct = response.headers.get("content-type", "")
        assert "text/plain" in ct

    def test_metrics_body_not_empty(self, client: TestClient):
        response = client.get("/metrics")
        assert len(response.content) > 0


# ============================================================================
# Section 7I: CORS policy audit
# ============================================================================

class TestCORSPolicy:
    """RESOLVED: CORS now restricts origins to configured list (default: localhost:3000)."""

    def test_cors_rejects_arbitrary_origin(self, client: TestClient):
        """Preflight from an unknown origin should NOT return access-control-allow-origin: *."""
        response = client.options(
            "/health",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        acl = response.headers.get("access-control-allow-origin", "")
        assert acl != "*", "CORS should no longer use wildcard origins"

    def test_cors_no_wildcard_in_middleware(self):
        """Verify the middleware does NOT include '*'."""
        from starlette.middleware.cors import CORSMiddleware as _CLS

        found_cors = False
        for mw in app.user_middleware:
            if mw.cls is _CLS:
                found_cors = True
                assert "*" not in mw.kwargs.get("allow_origins", []), (
                    "CORS should not use wildcard origins."
                )
        assert found_cors, "CORSMiddleware not found in middleware stack."


# ============================================================================
# Section 7J: Authentication audit
# ============================================================================

class TestAuthenticationAudit:
    """AUDIT FINDING: No authentication or authorization middleware.

    All endpoints are publicly accessible.  There is no API key, JWT, OAuth,
    or session-based auth.  Any client that can reach the server can trigger
    discovery, acquisition, and maintenance operations.
    """

    def test_no_auth_dependency_on_routes(self):
        """None of the routes declare a Depends() for auth."""
        from fastapi.routing import APIRoute

        for route in app.routes:
            if not isinstance(route, APIRoute):
                continue
            deps = route.dependant.dependencies
            # A real auth system would inject at least one dependency
            auth_deps = [
                d for d in deps
                if "auth" in str(d.call).lower()
                or "token" in str(d.call).lower()
                or "apikey" in str(d.call).lower()
                or "api_key" in str(d.call).lower()
            ]
            assert len(auth_deps) == 0, (
                f"Unexpected auth dependency found on {route.path} -- "
                "update this audit test if auth has been added."
            )

    def test_no_auth_middleware(self):
        """No middleware class name hints at authentication."""
        for mw in app.user_middleware:
            cls_name = mw.cls.__name__.lower()
            assert "auth" not in cls_name, (
                f"Auth middleware found ({mw.cls.__name__}); update audit."
            )

    def test_health_accessible_without_credentials(self, client: TestClient):
        """Demonstrate: no headers needed to hit any endpoint."""
        response = client.get("/health")
        assert response.status_code == 200


# ============================================================================
# Section 7K: Deprecated lifecycle events
# ============================================================================

class TestLifespanPattern:
    """RESOLVED: App now uses the modern ``lifespan`` async context manager."""

    def test_app_does_not_use_on_event(self):
        """Deprecated @app.on_event patterns should be gone."""
        import inspect
        from api import app as app_module

        source = inspect.getsource(app_module)
        assert '@app.on_event("startup")' not in source, (
            "Deprecated @app.on_event('startup') should be removed."
        )
        assert '@app.on_event("shutdown")' not in source, (
            "Deprecated @app.on_event('shutdown') should be removed."
        )

    def test_app_uses_lifespan(self):
        """The modern lifespan pattern should be present."""
        import inspect
        from api import app as app_module

        source = inspect.getsource(app_module)
        assert "lifespan" in source, (
            "Expected lifespan context manager in app.py."
        )


# ============================================================================
# Section 7L: Request validation edge cases
# ============================================================================

class TestRequestValidation:
    """Verify FastAPI returns proper 422 responses for malformed payloads."""

    def test_discovery_no_json_body(self, client: TestClient):
        response = client.post("/discovery/query")
        assert response.status_code == 422

    def test_discovery_wrong_content_type(self, client: TestClient):
        response = client.post(
            "/discovery/query",
            content=b"query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 422

    def test_acquisition_no_json_body(self, client: TestClient):
        response = client.post("/acquisition/acquire")
        assert response.status_code == 422

    def test_acquisition_wrong_type_for_paper(self, client: TestClient):
        """paper must be a dict, not a string."""
        response = client.post(
            "/acquisition/acquire",
            json={"paper": "not a dict"},
        )
        assert response.status_code == 422

    def test_unknown_route_returns_404(self, client: TestClient):
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_wrong_method_on_health(self, client: TestClient):
        response = client.post("/health")
        assert response.status_code == 405

    def test_wrong_method_on_discovery(self, client: TestClient):
        response = client.get("/discovery/query")
        assert response.status_code == 405

    def test_discovery_extra_fields_ignored(self, client: TestClient):
        """Pydantic by default ignores extra fields."""
        app.state.discovery_engine.search_by_query = AsyncMock(return_value=[])
        response = client.post(
            "/discovery/query",
            json={"query": "test", "max_results": 5, "unknown_field": "ignored"},
        )
        assert response.status_code == 200


# ============================================================================
# Section 7M: OpenAPI schema verification
# ============================================================================

class TestOpenAPISchema:
    """Verify the auto-generated OpenAPI spec is consistent.

    NOTE: Uses app.openapi() directly instead of TestClient because the
    client fixture's router wrapping empties the paths dict in OpenAPI output.
    """

    def test_openapi_json_loads(self):
        schema = app.openapi()
        assert schema["info"]["title"] == "Academic Paper Manager API"
        assert schema["info"]["version"] == "0.1.0"

    def test_openapi_contains_all_paths(self):
        schema = app.openapi()
        paths = set(schema.get("paths", {}).keys())
        expected = {
            "/health",
            "/discovery/query",
            "/acquisition/acquire",
            "/maintenance/run",
            "/organization/duplicates",
            "/collection/summary",
            "/metrics",
        }
        assert expected.issubset(paths), (
            f"Missing paths in OpenAPI: {expected - paths}"
        )

    def test_openapi_discovery_has_post_method(self):
        schema = app.openapi()
        methods = set(schema["paths"]["/discovery/query"].keys())
        assert "post" in methods

    def test_openapi_health_has_get_method(self):
        schema = app.openapi()
        methods = set(schema["paths"]["/health"].keys())
        assert "get" in methods


# ============================================================================
# Section 7N: Endpoint-database contract mismatches (integration audit)
# ============================================================================

class TestDatabaseContractMismatches:
    """Cross-check what the endpoints call vs. what AsyncPaperDatabase provides.

    This section documents the exact contract violations between the API
    endpoints and the database class.
    """

    def test_maintenance_calls_list_papers_which_now_exists(self):
        """FIXED: /maintenance/run relies on db.list_papers() which now exists."""
        from core.database import AsyncPaperDatabase
        import inspect
        from api.app import maintenance_run

        endpoint_source = inspect.getsource(maintenance_run)
        assert "list_papers" in endpoint_source, (
            "The endpoint source should reference list_papers."
        )
        assert hasattr(AsyncPaperDatabase, "list_papers"), (
            "list_papers() should exist on AsyncPaperDatabase"
        )

    def test_find_duplicates_exists(self):
        """find_duplicates IS a real method -- used by both maintenance and org."""
        from core.database import AsyncPaperDatabase

        assert hasattr(AsyncPaperDatabase, "find_duplicates")

    def test_get_statistics_exists(self):
        """get_statistics IS a real method -- used by /collection/summary."""
        from core.database import AsyncPaperDatabase

        assert hasattr(AsyncPaperDatabase, "get_statistics")

    def test_maintenance_endpoint_references_record_dot_created_at(self):
        """The endpoint accesses record.created_at which IS on PaperRecord."""
        from core.database import PaperRecord
        import inspect
        from api.app import maintenance_run

        source = inspect.getsource(maintenance_run)
        assert "record.created_at" in source

        record = PaperRecord(file_path="/test.pdf", title="T", authors="[]")
        assert hasattr(record, "created_at"), "PaperRecord should have created_at."


# ============================================================================
# Section 7O: Prometheus counter behaviour
# ============================================================================

class TestPrometheusCounters:
    """Verify that Prometheus counters are incremented on endpoint calls."""

    def test_discovery_counter_incremented(self, client: TestClient):
        app.state.discovery_engine.search_by_query = AsyncMock(return_value=[])

        from api.app import DISCOVERY_COUNTER

        DISCOVERY_COUNTER.inc.reset_mock()
        client.post("/discovery/query", json={"query": "test"})
        DISCOVERY_COUNTER.inc.assert_called()

    def test_acquisition_counter_incremented(self, client: TestClient):
        fake = _FakeAcquisitionResult()
        app.state.acquisition_engine.acquire_paper = AsyncMock(return_value=fake)

        from api.app import ACQUISITION_COUNTER

        ACQUISITION_COUNTER.inc.reset_mock()
        client.post("/acquisition/acquire", json={"paper": {"doi": "10.1/x"}})
        ACQUISITION_COUNTER.inc.assert_called()

    def test_maintenance_counter_incremented(self, client: TestClient):
        fake_paper = _FakePaperRecord()
        app.state.database.list_papers = AsyncMock(return_value=[fake_paper])
        app.state.database.find_duplicates = AsyncMock(return_value=[])

        @dataclass
        class _UR:
            checked_papers: int = 0
            publication_updates: list = field(default_factory=list)
            missing_files: list = field(default_factory=list)

        @dataclass
        class _QR:
            total_files: int = 0
            invalid_files: list = field(default_factory=list)
            duplicate_groups: list = field(default_factory=list)

        @dataclass
        class _S:
            update_report: _UR = field(default_factory=_UR)
            quality_report: _QR = field(default_factory=_QR)

        app.state.maintenance_system.run_maintenance = AsyncMock(return_value=_S())

        from api.app import MAINTENANCE_COUNTER

        MAINTENANCE_COUNTER.inc.reset_mock()
        client.post("/maintenance/run")
        MAINTENANCE_COUNTER.inc.assert_called()
