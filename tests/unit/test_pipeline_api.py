import importlib
import os
from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _reload_app_with_flag(monkeypatch, enabled: bool):
    # Ensure env is set before import
    monkeypatch.setenv("PIPELINE_API_ENABLED", "true" if enabled else "false")
    # Reset Prometheus default registry to avoid duplicate metric registration on reload
    import prometheus_client as pc
    monkeypatch.setattr(pc, "REGISTRY", pc.CollectorRegistry())
    import mathpdf.api.app as api_app
    importlib.reload(api_app)
    return api_app


def test_pipeline_endpoints_disabled_by_default(monkeypatch):
    api_app = _reload_app_with_flag(monkeypatch, enabled=False)
    client = TestClient(api_app.app)
    resp = client.post("/pipeline/run")
    assert resp.status_code == 404
    resp = client.get("/pipeline/last_digest")
    assert resp.status_code == 404


def test_pipeline_run_and_metrics(monkeypatch, tmp_path):
    api_app = _reload_app_with_flag(monkeypatch, enabled=True)

    # Stub config loader to use tmp dir
    cfg = SimpleNamespace(data_dir=str(tmp_path))
    monkeypatch.setattr(api_app, "load_bot_config", lambda: cfg)

    # Stub ArxivBot to avoid network and return a fixed summary
    class DummyBot:
        def __init__(self, _):
            pass

        async def initialize(self):
            return None

        async def run_daily_pipeline(self):
            return {
                'papers_harvested': 7,
                'papers_accepted': 3,
                'papers_downloaded': 2,
                'digest_path': str(tmp_path / 'digests' / 'digest_2099-01-01.md'),
                'elapsed_seconds': 1.23,
                'harvested_per_source': {'arxiv': 7},
                'accepted_per_source': {'arxiv': 3},
                'downloaded_per_source': {'arxiv': 2},
            }

    monkeypatch.setattr(api_app, "ArxivBot", DummyBot)

    client = TestClient(api_app.app)

    # Call pipeline/run (should also persist summary to last_pipeline_summary.json)
    r = client.post("/pipeline/run")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["summary"]["papers_accepted"] == 3

    # Metrics should include last-run gauges
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "pipeline_last_run_accepted" in text
    assert "pipeline_last_run_downloaded" in text
    assert "pipeline_last_run_harvested_per_source" in text
    assert "pipeline_last_run_accepted_per_source" in text
    assert "pipeline_last_run_downloaded_per_source" in text

    # Prepare a digest file to test last_digest
    digests_dir = tmp_path / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    p = digests_dir / "digest_2099-01-01.md"
    p.write_text("# Test Digest\n\nContent")

    # last_digest should return the file content
    r2 = client.get("/pipeline/last_digest")
    assert r2.status_code == 200
    assert "Test Digest" in r2.text

    # last_summary should return persisted summary
    r3 = client.get("/pipeline/last_summary")
    assert r3.status_code == 200
    assert r3.json()["papers_harvested"] == 7
