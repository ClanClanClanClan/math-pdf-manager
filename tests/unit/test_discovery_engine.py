from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from discovery.engine import DiscoveryEngine, PaperCandidate


ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1234.5678v1</id>
    <title> Sample ArXiv Paper </title>
    <author><name>Alice Example</name></author>
    <author><name>Bob Example</name></author>
    <arxiv:doi>10.1234/example.doi</arxiv:doi>
    <link rel="alternate" type="text/html" href="http://arxiv.org/abs/1234.5678"/>
    <published>2024-01-01T00:00:00Z</published>
  </entry>
</feed>
"""

CROSSREF_RESPONSE = {
    "status": "ok",
    "message-type": "work-list",
    "message": {
        "items": [
            {
                "title": ["Crossref Sample"],
                "author": [{"given": "Carol", "family": "Researcher"}],
                "DOI": "10.5555/sample",
                "URL": "https://doi.org/10.5555/sample",
                "published-print": {"date-parts": [[2023, 7, 1]]},
            }
        ]
    },
}


@pytest_asyncio.fixture
async def discovery_engine():
    async def handler(request: httpx.Request) -> httpx.Response:
        if "export.arxiv.org" in request.url.host:
            return httpx.Response(200, text=ARXIV_FEED)
        if "api.crossref.org" in request.url.host and request.method == "GET":
            if request.url.path.startswith("/works/"):
                return httpx.Response(200, json={"message": CROSSREF_RESPONSE["message"]["items"][0]})
            return httpx.Response(200, json=CROSSREF_RESPONSE)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    engine = DiscoveryEngine(client=client)
    yield engine
    await engine.close()


@pytest.mark.asyncio
async def test_search_by_query_aggregates_sources(discovery_engine):
    results = await discovery_engine.search_by_query("quantum", max_results=5)
    titles = {candidate.title for candidate in results}
    assert "Sample ArXiv Paper" in titles
    assert "Crossref Sample" in titles


@pytest.mark.asyncio
async def test_search_by_doi_returns_candidate(discovery_engine):
    candidate = await discovery_engine.search_by_doi("10.5555/sample")
    assert isinstance(candidate, PaperCandidate)
    assert candidate.doi == "10.5555/sample"
    assert candidate.title == "Crossref Sample"


@pytest.mark.asyncio
async def test_import_from_bibliography(tmp_path):
    bib = tmp_path / "papers.bib"
    bib.write_text("""@article{sample,
      title={A BibTeX Paper},
      author={Doe, Jane and Smith, John},
      year={2022},
      doi={10.1111/bibtex}
    }
    """, encoding="utf-8")
    engine = DiscoveryEngine()
    candidates = engine.import_from_bibliography(bib)
    await engine.close()
    assert candidates[0].title == "A BibTeX Paper"
    concatenated = " ".join(candidates[0].authors)
    assert "Doe" in concatenated
    assert "Jane" in concatenated
