import asyncio
from typing import Any

import pytest
import respx
from httpx import Response

from mathpdf.discovery.engine import CROSSREF_API, DiscoveryEngine


@pytest.mark.asyncio
@respx.mock
async def test_discovery_crossref_basic():
    # Mock Crossref search
    mock_items = {
        "message": {
            "items": [
                {
                    "DOI": "10.1000/test-doi",
                    "title": ["A Test Paper"],
                    "author": [{"family": "Doe", "given": "Jane"}],
                    "URL": "http://dx.doi.org/10.1000/test-doi",
                    "subject": ["Mathematics"],
                    "type": "journal-article",
                }
            ]
        }
    }
    respx.get(CROSSREF_API).mock(return_value=Response(200, json=mock_items))

    engine = DiscoveryEngine()
    results = await engine.search_by_query("graph theory", max_results=1)
    assert results
    first = results[0]
    assert first.doi == "10.1000/test-doi"
    assert first.title == "A Test Paper"
    assert first.source == "crossref"

