import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from mathpdf.acquisition.engine import AcquisitionConfig, AcquisitionEngine
from mathpdf.publishers import DownloadResult


class DummyClient:
    class Resp:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception("error")

        def json(self):
            return self._json

    async def get(self, url, params=None, headers=None):
        # Simulate Unpaywall
        if "api.unpaywall.org" in url:
            return DummyClient.Resp(200, {"best_oa_location": {"url_for_pdf": "http://example.com/file.pdf"}})
        return DummyClient.Resp(404, {})

    async def aclose(self):
        return None


class DummyDownloader:
    async def download_from_url(self, url, download_path, **kwargs):
        download_path.parent.mkdir(parents=True, exist_ok=True)
        download_path.write_bytes(b"%PDF-1.4\n")
        return DownloadResult(True, file_path=download_path)

    async def download_best_match(self, title, authors=None, download_dir=None):
        # Simulate failure to force next strategy
        return DownloadResult(False, error_message="not found")


@pytest.mark.asyncio
async def test_open_access_strategy_success(tmp_path):
    engine = AcquisitionEngine(
        downloader=DummyDownloader(),
        client=DummyClient(),
        config=AcquisitionConfig(download_dir=tmp_path, unpaywall_email="user@example.com"),
    )
    result = await engine.acquire_paper({"title": "Something", "doi": "10.1/test-doi"})
    assert result.success is True
    assert Path(result.file_path).exists()


@pytest.mark.asyncio
async def test_preprint_strategy_fallback(tmp_path):
    # Force OA to fail by removing email; publisher fails by DummyDownloader; use preprint
    engine = AcquisitionEngine(
        downloader=DummyDownloader(),
        client=DummyClient(),
        config=AcquisitionConfig(download_dir=tmp_path, unpaywall_email=None),
    )
    result = await engine.acquire_paper({"title": "Paper", "arxiv_id": "1234.5678"})
    # DummyDownloader download_best_match not used; but download_from_url in PreprintStrategy uses it
    # We need to let DummyDownloader cover preprint download
    assert result.success is True

