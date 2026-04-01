import asyncio
from pathlib import Path

import pytest
import respx
from httpx import Response

from mathpdf.acquisition.engine import AcquisitionConfig, AcquisitionEngine
from mathpdf.publishers import DownloadResult


@pytest.mark.asyncio
@respx.mock
async def test_open_access_strategy_downloads(tmp_path: Path):
    # Mock Unpaywall response
    doi = "10.1000/test-doi"
    unpaywall_url = f"https://api.unpaywall.org/v2/{doi}"
    respx.get(unpaywall_url).mock(
        return_value=Response(200, json={
            "best_oa_location": {"url_for_pdf": "https://example.org/paper.pdf"}
        })
    )

    # Mock direct PDF download
    respx.get("https://example.org/paper.pdf").mock(
        return_value=Response(200, content=b"%PDF-1.4 test")
    )

    cfg = AcquisitionConfig(download_dir=tmp_path, unpaywall_email="user@example.org")
    engine = AcquisitionEngine(config=cfg)

    async def fake_download(url, download_path, **_):
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.write_bytes(b"%PDF-1.4 stub")
        return DownloadResult(True, file_path=download_path)

    engine.downloader.download_from_url = fake_download  # type: ignore[assignment]
    result = await engine.acquire_paper({"doi": doi, "title": "X"})
    assert result.success
    assert result.file_path
    assert Path(result.file_path).exists()
