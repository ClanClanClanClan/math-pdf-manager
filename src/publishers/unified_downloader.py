#!/usr/bin/env python3
"""Unified downloader facade for publisher adapters."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

import aiohttp

from . import AuthenticationConfig, DownloadResult, publisher_registry

logger = logging.getLogger(__name__)


class UnifiedDownloader:
    """Orchestrate searches and downloads across publisher implementations."""

    def __init__(self) -> None:
        self.publishers: dict[str, Any] = {}
        self.auth_configs: dict[str, AuthenticationConfig] = {}

    def configure_publisher(self, publisher_name: str, auth_config: AuthenticationConfig) -> None:
        """Configure authentication for *publisher_name*."""

        self.auth_configs[publisher_name] = auth_config
        logger.info("Configured authentication for %s", publisher_name)

    def get_publisher(self, publisher_name: str):
        """Return (and cache) a publisher instance."""

        if publisher_name not in self.publishers:
            auth_config = self.auth_configs.get(publisher_name, AuthenticationConfig())
            self.publishers[publisher_name] = publisher_registry.get_publisher(publisher_name, auth_config)
        return self.publishers[publisher_name]

    async def search_all_publishers(self, title: str, authors: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
        """Search all registered publishers for ``title``."""

        results: dict[str, list[dict[str, Any]]] = {}

        for publisher_name in publisher_registry.list_publishers():
            try:
                publisher = self.get_publisher(publisher_name)
                search_results = await publisher.search_paper(title, authors)
                results[publisher_name] = search_results or []
                logger.debug("Found %d candidate(s) at %s", len(results[publisher_name]), publisher_name)
            except Exception as exc:  # pragma: no cover - depends on implementations
                logger.error("Search failed for %s: %s", publisher_name, exc)
                results[publisher_name] = []

        return results

    async def download_from_publisher(self, publisher_name: str, paper_id: str, download_path: Path) -> DownloadResult:
        """Download ``paper_id`` from ``publisher_name`` into ``download_path``."""

        try:
            publisher = self.get_publisher(publisher_name)
            download_path.parent.mkdir(parents=True, exist_ok=True)
            return await publisher.download_paper(paper_id, download_path)
        except Exception as exc:  # pragma: no cover - depends on implementations
            error_msg = f"Download failed from {publisher_name}: {exc}"
            logger.error(error_msg)
            return DownloadResult(False, error_message=error_msg)

    async def download_best_match(
        self,
        title: str,
        authors: list[str] | None = None,
        download_dir: Path | None = None,
    ) -> DownloadResult:
        """Search every publisher and download the first positive match."""

        search_results = await self.search_all_publishers(title, authors)

        for publisher_name, results in search_results.items():
            if not results:
                continue

            best_match = results[0]
            paper_id = best_match.get('id') or best_match.get('arnumber') or best_match.get('doi')
            if not paper_id:
                continue

            target_dir = download_dir or Path.cwd()
            filename = f"{title[:50]}.pdf"
            download_path = target_dir / filename
            return await self.download_from_publisher(publisher_name, paper_id, download_path)

        return DownloadResult(False, error_message="No suitable paper found")

    async def download_from_url(self, url: str, download_path: Path, *, session: aiohttp.ClientSession | None = None) -> DownloadResult:
        """Download a PDF directly from ``url`` without using a publisher adapter."""

        own_session = False
        if session is None:
            session = aiohttp.ClientSession()
            own_session = True

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    error_msg = f"HTTP {response.status} while downloading {url}"
                    logger.error(error_msg)
                    return DownloadResult(False, error_message=error_msg)

                content = await response.read()
                download_path.parent.mkdir(parents=True, exist_ok=True)
                download_path.write_bytes(content)

            return DownloadResult(True, file_path=download_path, metadata={'source_url': url})

        except Exception as exc:  # pragma: no cover - network interactions
            error_msg = f"Direct download failed: {exc}"
            logger.error(error_msg)
            return DownloadResult(False, error_message=error_msg)

        finally:
            if own_session:
                await session.close()

    def get_publisher_status(self) -> dict[str, bool]:
        """Return authentication status for cached publishers."""

        status: dict[str, bool] = {}
        for publisher_name in publisher_registry.list_publishers():
            try:
                publisher = self.get_publisher(publisher_name)
                status[publisher_name] = publisher.is_authenticated()
            except Exception as exc:  # pragma: no cover - depends on implementations
                logger.error("Failed to check status for %s: %s", publisher_name, exc)
                status[publisher_name] = False
        return status

    async def authenticate_all(self) -> dict[str, bool]:
        """Authenticate with every registered publisher."""

        results: dict[str, bool] = {}
        for publisher_name in publisher_registry.list_publishers():
            try:
                publisher = self.get_publisher(publisher_name)
                results[publisher_name] = await publisher.authenticate()
            except Exception as exc:  # pragma: no cover - depends on implementations
                logger.error("Authentication failed for %s: %s", publisher_name, exc)
                results[publisher_name] = False
        return results

    async def logout_all(self) -> None:
        """Logout from all cached publisher sessions."""

        tasks: List[asyncio.Task] = []
        loop = asyncio.get_running_loop()

        for publisher_name, publisher in list(self.publishers.items()):
            try:
                tasks.append(loop.create_task(publisher.logout()))
            except Exception as exc:  # pragma: no cover - depends on implementations
                logger.error("Logout failed for %s: %s", publisher_name, exc)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.publishers.clear()


__all__ = ["UnifiedDownloader"]
