import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_discovery_query_returns_payload(client, monkeypatch):
    from discovery.engine import PaperCandidate

    class DummyDiscovery:
        async def search_by_query(self, query: str, max_results: int = 10):
            return [PaperCandidate(title="Test Paper", authors=["Jane Doe"], doi="10.1/test", source="mock")]

        async def close(self):
            return None

    monkeypatch.setattr(app.state, "discovery_engine", DummyDiscovery())
    response = client.post("/discovery/query", json={"query": "test"})
    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "Test Paper"


def test_acquisition_endpoint(client, monkeypatch):
    from acquisition.engine import AcquisitionResult

    class DummyAcquisition:
        async def acquire_paper(self, paper):
            return AcquisitionResult(True, "open_access", file_path=None, message=None)

        async def close(self):
            return None

    monkeypatch.setattr(app.state, "acquisition_engine", DummyAcquisition())
    response = client.post("/acquisition/acquire", json={"paper": {"doi": "10.1/test"}})
    assert response.status_code == 200
    assert response.json()["success"] is True
