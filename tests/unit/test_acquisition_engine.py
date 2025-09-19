import asyncio
from pathlib import Path

import httpx
import pytest

from acquisition.engine import (
    AcquisitionConfig,
    AcquisitionEngine,
    AcquisitionResult,
    InstitutionalCredentials,
    InstitutionalStrategy,
)
from publishers import DownloadResult


class StubDownloader:
    def __init__(self, *, url_success=True, publisher_success=True):
        self.url_success = url_success
        self.publisher_success = publisher_success
        self.downloaded = []

    async def download_from_url(self, url, download_path, **_):
        self.downloaded.append(("url", url, download_path))
        if self.url_success:
            download_path.parent.mkdir(parents=True, exist_ok=True)
            download_path.write_bytes(b"PDF")
            return DownloadResult(True, file_path=download_path)
        return DownloadResult(False, error_message="url failed")

    async def download_best_match(self, title, authors=None, download_dir=None):
        self.downloaded.append(("publisher", title, download_dir))
        if self.publisher_success:
            download_dir.mkdir(parents=True, exist_ok=True)
            path = download_dir / "publisher.pdf"
            path.write_bytes(b"PDF")
            return DownloadResult(True, file_path=path)
        return DownloadResult(False, error_message="publisher failed")


@pytest.mark.asyncio
async def test_open_access_strategy_success(tmp_path):
    paper = {"title": "OA Paper", "doi": "10.1234/oa"}

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"best_oa_location": {"url_for_pdf": "https://example.com/oa.pdf"}})

    engine = AcquisitionEngine(
        downloader=StubDownloader(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        config=AcquisitionConfig(download_dir=tmp_path, unpaywall_email="test@example.com"),
    )

    try:
        result = await engine.acquire_paper(paper)
    finally:
        await engine.close()

    assert result.success is True
    assert result.strategy == "open_access"
    assert result.file_path and result.file_path.exists()


@pytest.mark.asyncio
async def test_publisher_strategy_used_when_open_access_unavailable(tmp_path):
    paper = {"title": "Publisher Paper"}

    engine = AcquisitionEngine(
        downloader=StubDownloader(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))),
        config=AcquisitionConfig(download_dir=tmp_path, unpaywall_email=None),
    )

    try:
        result = await engine.acquire_paper(paper)
    finally:
        await engine.close()

    assert result.success is True
    assert result.strategy == "publisher"


@pytest.mark.asyncio
async def test_preprint_strategy_handles_arxiv(tmp_path):
    paper = {"title": "ArXiv Paper", "arxiv_id": "1234.5678"}

    downloader = StubDownloader(url_success=True, publisher_success=False)

    engine = AcquisitionEngine(
        downloader=downloader,
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))),
        config=AcquisitionConfig(download_dir=tmp_path, unpaywall_email=None),
    )

    try:
        result = await engine.acquire_paper(paper)
    finally:
        await engine.close()

    assert result.success is True
    assert result.strategy == "preprint"
    assert any(kind == "url" and "arxiv.org" in url for kind, url, _ in downloader.downloaded)


@pytest.mark.asyncio
async def test_all_strategies_fail(tmp_path):
    paper = {"title": "Missing Data"}

    downloader = StubDownloader(url_success=False, publisher_success=False)

    engine = AcquisitionEngine(
        downloader=downloader,
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))),
        config=AcquisitionConfig(download_dir=tmp_path, unpaywall_email=None),
    )

    try:
        result = await engine.acquire_paper(paper)
    finally:
        await engine.close()

    assert result.success is False
    assert result.strategy == "none"
    assert "failed" in (result.message or "")


@pytest.mark.asyncio
async def test_institutional_strategy_uses_custom_downloader(tmp_path):
    paper = {"title": "Institutional", "doi": "10.1234/institutional", "publisher": "Elsevier"}

    async def fake_download_with_institutional_access(**kwargs):
        output_dir = kwargs.get('output_dir')
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "institutional.pdf"
        path.write_bytes(b"%PDF")
        return path, {}

    creds = InstitutionalCredentials(username="user", password="pass")

    engine = AcquisitionEngine(
        downloader=StubDownloader(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(404))),
        config=AcquisitionConfig(download_dir=tmp_path, institutional_credentials=creds),
        strategies=[InstitutionalStrategy(creds, downloader_fn=fake_download_with_institutional_access)],
    )

    try:
        result = await engine.acquire_paper(paper)
    finally:
        await engine.close()

    assert result.success is True
    assert result.strategy == "institutional"
