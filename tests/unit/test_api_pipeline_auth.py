import importlib
from types import SimpleNamespace

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


def _load_app(monkeypatch, token: str | None = None, rate_limit_seconds: int = 3600):
    monkeypatch.setenv("PIPELINE_API_ENABLED", "true")
    if token is not None:
        monkeypatch.setenv("API_TOKEN", token)
    monkeypatch.setenv("PIPELINE_RATE_LIMIT_SECONDS", str(rate_limit_seconds))
    import mathpdf.api.app as api_app
    importlib.reload(api_app)
    return api_app


def test_pipeline_auth_and_rate_limit(monkeypatch, tmp_path):
    api_app = _load_app(monkeypatch, token="secret", rate_limit_seconds=3600)

    # Stub config loader and ArxivBot
    api_app.load_bot_config = lambda: SimpleNamespace(data_dir=str(tmp_path))

    class DummyBot:
        def __init__(self, cfg):
            self.cfg = cfg

        async def initialize(self):
            return None

        async def run_daily_pipeline(self):
            return {
                'papers_harvested': 1,
                'papers_accepted': 1,
                'papers_downloaded': 1,
                'digest_path': str(tmp_path / 'digests' / 'digest.md'),
                'elapsed_seconds': 0.1,
                'harvested_per_source': {'arxiv': 1},
                'accepted_per_source': {'arxiv': 1},
                'downloaded_per_source': {'arxiv': 1},
            }

    api_app.ArxivBot = DummyBot
    client = TestClient(api_app.app)

    # No token -> 401
    r = client.post("/pipeline/run")
    assert r.status_code == 401

    # Wrong token -> 401
    r = client.post("/pipeline/run", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401

    # Correct token -> 200
    r = client.post("/pipeline/run", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200

    # Second call triggers rate limiting -> 429
    r = client.post("/pipeline/run", headers={"X-API-Token": "secret"})
    assert r.status_code == 429
