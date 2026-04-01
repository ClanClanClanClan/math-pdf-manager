import asyncio
from types import SimpleNamespace

import pytest

from mathpdf.discovery.integration import DiscoveryIntegration


class DummyCMO:
    def __init__(self, title, authors, categories, doi=None, pdf_url=None, source="arxiv"):
        self.title = title
        self.authors = [SimpleNamespace(given=a.split(" ")[0], family=a.split(" ")[-1]) for a in authors]
        self.categories = categories
        self.doi = doi
        self.pdf_url = pdf_url
        self.published = "2025-01-01"
        self.external_id = f"{source}:id"
        self.source = source


class DummyHarvester:
    def __init__(self, cmos):
        self._cmos = cmos

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def harvest_all(self, _date):
        return {"arxiv": self._cmos}


class DummyDiscovery:
    def __init__(self, results=None):
        self._results = results or []

    async def search_by_query(self, query, *, max_results=10):
        return list(self._results)

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_cmo_to_candidate_and_strict_filter(monkeypatch):
    cmo_ok = DummyCMO("A paper", ["Ada Lovelace"], ["cs.LG", "cs.AI"], doi="10.1/test", pdf_url="http://x")
    cmo_other = DummyCMO("Other paper", ["Alan Turing"], ["math.PR"], doi=None, pdf_url=None)
    di = DiscoveryIntegration()
    di.discovery_engine = DummyDiscovery()
    di.harvester = SimpleNamespace(config=SimpleNamespace(score_threshold=0.0))
    di.cmo_harvester = DummyHarvester([cmo_ok, cmo_other])

    di._cmo_to_candidate = lambda cmo: SimpleNamespace(  # type: ignore[attr-defined]
        title=getattr(cmo, "title", ""),
        metadata={"categories": getattr(cmo, "categories", [])},
    )

    # Strict filter on: only cs.* matches when categories=['cs.']
    results = await di.discover_papers(categories=["cs."], max_papers_per_category=10, relevance_threshold=0.0, strict_category_filter=True)
    assert any(r.title == "A paper" for r in results)
    assert not any(r.title == "Other paper" for r in results)

    # Strict filter off: include all
    results2 = await di.discover_papers(categories=["cs."], max_papers_per_category=10, relevance_threshold=0.0, strict_category_filter=False)
    titles = [r.title for r in results2]
    assert "A paper" in titles and "Other paper" in titles
