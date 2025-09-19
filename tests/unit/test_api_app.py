import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.app import app  # noqa: E402
from maintenance.system import MaintenanceSummary, UpdateReport, QualityReport


class DummyDatabase:
    def __init__(self, papers=None, duplicates=None):
        self._papers = papers or []
        self._duplicates = duplicates or []

    async def list_papers(self, limit=None):
        return self._papers

    async def find_duplicates(self, similarity_threshold=0.8):
        return self._duplicates


class DummyMaintenance:
    def __init__(self, summary: MaintenanceSummary):
        self._summary = summary

    async def run_maintenance(self, metadata_list, files, duplicate_map):
        return self._summary


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        # Replace database and maintenance system with controllable stubs for tests.
        app.state.database = DummyDatabase()
        summary = MaintenanceSummary(
            update_report=UpdateReport(checked_papers=0),
            quality_report=QualityReport(total_files=0, invalid_files=[], duplicate_groups=[])
        )
        app.state.maintenance_system = DummyMaintenance(summary)
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


def test_maintenance_run_endpoint(client, monkeypatch, tmp_path):
    class Paper:
        def __init__(self, doi, arxiv_id, created_at, file_path):
            self.doi = doi
            self.arxiv_id = arxiv_id
            self.created_at = created_at
            self.file_path = file_path

    paper_file = tmp_path / "paper.pdf"
    paper_file.write_bytes(b"%PDF")
    papers = [
        Paper("10.1/test", "1234.5678", "2022-01-01T00:00:00", str(paper_file)),
    ]
    duplicates = []
    app.state.database = DummyDatabase(papers=papers, duplicates=duplicates)
    summary = MaintenanceSummary(
        update_report=UpdateReport(checked_papers=1, publication_updates=["1234.5678"], missing_files=[]),
        quality_report=QualityReport(total_files=1, invalid_files=[], duplicate_groups=[]),
    )
    app.state.maintenance_system = DummyMaintenance(summary)

    response = client.post("/maintenance/run")
    assert response.status_code == 200
    payload = response.json()
    assert payload['update_report']['checked_papers'] == 1
    assert payload['quality_report']['total_files'] == 1


def test_organization_duplicates_endpoint(client, monkeypatch):
    class Paper:
        def __init__(self, file_path):
            self.file_path = file_path
            self.id = 1
            self.title = "Title"
            self.authors = "[]"
            self.publication_date = None
            self.arxiv_id = None
            self.doi = "10.1/test"
            self.journal = None
            self.volume = None
            self.pages = None
            self.abstract = ""
            self.keywords = "[]"
            self.research_areas = "[]"
            self.paper_type = "published"
            self.source = "test"
            self.confidence = 1.0
            self.file_size = 0
            self.file_hash = "hash"
            self.created_at = "2023-01-01T00:00:00"
            self.updated_at = "2023-01-01T00:00:00"

        def to_dict(self):
            return {
                'file_path': self.file_path,
                'title': self.title,
                'authors': self.authors,
                'doi': self.doi,
            }

    paper1 = Paper("/tmp/a.pdf")
    paper2 = Paper("/tmp/b.pdf")
    app.state.database = DummyDatabase(papers=[], duplicates=[(paper1, paper2, 0.95)])
    response = client.get("/organization/duplicates")
    assert response.status_code == 200
    assert response.json()['duplicates'][0]['similarity'] == 0.95


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'process_start_time_seconds' in response.text or response.content


def test_collection_summary_endpoint(client, monkeypatch):
    class DummyDB(DummyDatabase):
        async def get_statistics(self):
            return {
                'total_papers': 5,
                'by_type': {'published': 3},
                'recent_additions': 2,
                'total_duplicates': 1,
            }

    app.state.database = DummyDB()
    response = client.get("/collection/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload['total_papers'] == 5
    assert payload['total_duplicates'] == 1
