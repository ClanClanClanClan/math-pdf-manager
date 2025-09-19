#!/usr/bin/env python3
"""Strategy-based acquisition engine for downloading papers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import httpx

from publishers import DownloadResult
from publishers.unified_downloader import UnifiedDownloader

logger = logging.getLogger(__name__)

UNPAYWALL_API = "https://api.unpaywall.org/v2/"


@dataclass
class AcquisitionConfig:
    download_dir: Path = Path("downloads")
    unpaywall_email: Optional[str] = None
    allow_alternative_sources: bool = False


@dataclass
class AcquisitionResult:
    success: bool
    strategy: str
    file_path: Optional[Path] = None
    message: Optional[str] = None


class BaseStrategy:
    name = "base"

    async def try_acquire(
        self,
        paper: dict,
        *,
        client: httpx.AsyncClient,
        downloader: UnifiedDownloader,
        config: AcquisitionConfig,
    ) -> AcquisitionResult:
        raise NotImplementedError


class OpenAccessStrategy(BaseStrategy):
    name = "open_access"

    async def try_acquire(
        self,
        paper: dict,
        *,
        client: httpx.AsyncClient,
        downloader: UnifiedDownloader,
        config: AcquisitionConfig,
    ) -> AcquisitionResult:
        doi = paper.get("doi")
        if not doi or not config.unpaywall_email:
            return AcquisitionResult(False, self.name, message="No DOI or Unpaywall email configured")

        url = f"{UNPAYWALL_API}{doi}"
        params = {"email": config.unpaywall_email}
        try:
            response = await client.get(url, params=params)
            if response.status_code == httpx.codes.NOT_FOUND:
                return AcquisitionResult(False, self.name, message="No open access record")
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network failure path
            return AcquisitionResult(False, self.name, message=f"Unpaywall error: {exc}")

        data = response.json()
        oa_location = data.get("best_oa_location") or {}
        pdf_url = oa_location.get("url_for_pdf") or oa_location.get("url")
        if not pdf_url:
            return AcquisitionResult(False, self.name, message="Open access PDF unavailable")

        sanitized = (paper.get("doi", "paper").replace("/", "_"))
        download_path = config.download_dir / "open_access" / f"{sanitized}.pdf"
        result = await downloader.download_from_url(pdf_url, download_path)
        if result.success:
            return AcquisitionResult(True, self.name, file_path=result.file_path)
        return AcquisitionResult(False, self.name, message=result.error_message)


class PublisherStrategy(BaseStrategy):
    name = "publisher"

    async def try_acquire(
        self,
        paper: dict,
        *,
        client: httpx.AsyncClient,
        downloader: UnifiedDownloader,
        config: AcquisitionConfig,
    ) -> AcquisitionResult:
        title = paper.get("title")
        doi = paper.get("doi")
        if not (title or doi):
            return AcquisitionResult(False, self.name, message="Insufficient metadata for publisher download")

        download_dir = config.download_dir / "publisher"
        result = await downloader.download_best_match(title or doi, authors=paper.get("authors"), download_dir=download_dir)
        if result.success:
            return AcquisitionResult(True, self.name, file_path=result.file_path)
        return AcquisitionResult(False, self.name, message=result.error_message)


class PreprintStrategy(BaseStrategy):
    name = "preprint"

    async def try_acquire(
        self,
        paper: dict,
        *,
        client: httpx.AsyncClient,
        downloader: UnifiedDownloader,
        config: AcquisitionConfig,
    ) -> AcquisitionResult:
        arxiv_id = paper.get("arxiv_id")
        if not arxiv_id:
            return AcquisitionResult(False, self.name, message="No preprint identifier")

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        download_path = config.download_dir / "preprint" / f"{arxiv_id.replace('/', '_')}.pdf"
        result = await downloader.download_from_url(pdf_url, download_path)
        if result.success:
            return AcquisitionResult(True, self.name, file_path=result.file_path)
        return AcquisitionResult(False, self.name, message=result.error_message)


class AlternativeStrategy(BaseStrategy):
    name = "alternative"

    async def try_acquire(
        self,
        paper: dict,
        *,
        client: httpx.AsyncClient,
        downloader: UnifiedDownloader,
        config: AcquisitionConfig,
    ) -> AcquisitionResult:
        if not config.allow_alternative_sources:
            return AcquisitionResult(False, self.name, message="Alternative sources disabled")
        return AcquisitionResult(False, self.name, message="No alternative strategy implemented")


class AcquisitionEngine:
    """Coordinates strategies to download papers in priority order."""

    def __init__(
        self,
        downloader: Optional[UnifiedDownloader] = None,
        client: Optional[httpx.AsyncClient] = None,
        config: Optional[AcquisitionConfig] = None,
        strategies: Optional[Iterable[BaseStrategy]] = None,
    ):
        self.config = config or AcquisitionConfig()
        self.downloader = downloader or UnifiedDownloader()
        self.client = client or httpx.AsyncClient(timeout=15.0)
        self.strategies: List[BaseStrategy] = list(
            strategies
            or [
                OpenAccessStrategy(),
                PublisherStrategy(),
                PreprintStrategy(),
                AlternativeStrategy(),
            ]
        )

    async def acquire_paper(self, paper: dict) -> AcquisitionResult:
        self.config.download_dir.mkdir(parents=True, exist_ok=True)
        for strategy in self.strategies:
            result = await strategy.try_acquire(
                paper,
                client=self.client,
                downloader=self.downloader,
                config=self.config,
            )
            if result.success:
                logger.info("Acquired paper '%s' via %s", paper.get('title'), strategy.name)
                return result
            logger.debug("Strategy %s failed for '%s': %s", strategy.name, paper.get('title'), result.message)
        return AcquisitionResult(False, "none", message="All acquisition strategies failed")

    async def batch_acquire(self, papers: Iterable[dict]) -> List[AcquisitionResult]:
        results: List[AcquisitionResult] = []
        for paper in papers:
            results.append(await self.acquire_paper(paper))
        return results

    async def close(self) -> None:
        await self.client.aclose()


__all__ = ["AcquisitionEngine", "AcquisitionResult", "AcquisitionConfig"]
