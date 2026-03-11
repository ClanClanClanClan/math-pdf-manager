#!/usr/bin/env python3
"""Discovery engine providing multi-source paper search capabilities."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional
import defusedxml.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperCandidate:
    """Represents a paper discovered from an external source."""

    title: str
    authors: List[str]
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    source: str = ""
    url: Optional[str] = None
    published_year: Optional[int] = None
    metadata: dict = field(default_factory=dict)


class DiscoveryEngine:
    """Aggregates results from multiple discovery sources."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client or httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def search_by_query(self, query: str, *, max_results: int = 10) -> List[PaperCandidate]:
        tasks = [
            self._search_arxiv(query, max_results=max_results),
            self._search_crossref(query, max_results=max_results),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: List[PaperCandidate] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Discovery query failed: %s", result)
                continue
            merged.extend(result)
        return merged

    async def search_by_doi(self, doi: str) -> Optional[PaperCandidate]:
        try:
            record = await self._fetch_crossref_record(doi)
        except Exception as exc:  # pragma: no cover - network failure path
            logger.error("Crossref lookup failed for DOI %s: %s", doi, exc)
            return None
        if not record:
            return None
        return self._build_candidate_from_crossref(record)

    async def search_by_arxiv_id(self, arxiv_id: str) -> Optional[PaperCandidate]:
        results = await self._search_arxiv(f"id:{arxiv_id}", max_results=1)
        return results[0] if results else None

    async def search_by_authors(self, authors: List[str], year_range: Optional[tuple[int, int]] = None,
                                *, max_results: int = 10) -> List[PaperCandidate]:
        author_query = " ".join(authors)
        tasks = [
            self._search_arxiv(f"au:{author_query}", max_results=max_results),
            self._search_crossref(author_query, max_results=max_results, filter_year_range=year_range),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: List[PaperCandidate] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Author discovery failed: %s", result)
                continue
            merged.extend(result)
        return merged

    def import_from_bibliography(self, bib_file: Path, fmt: str = "bibtex") -> List[PaperCandidate]:
        parser = {
            "bibtex": self._parse_bibtex,
        }.get(fmt.lower())
        if not parser:
            raise ValueError(f"Unsupported bibliography format: {fmt}")
        return parser(bib_file)

    async def scan_conference_proceedings(self, source: str, *, max_results: int = 20) -> List[PaperCandidate]:
        if Path(source).exists():
            text = Path(source).read_text(encoding="utf-8")
        else:
            response = await self._client.get(source)
            response.raise_for_status()
            text = response.text
        doi_pattern = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
        dois = list(dict.fromkeys(doi_pattern.findall(text)))[:max_results]
        candidates = []
        for doi in dois:
            candidate = await self.search_by_doi(doi)
            if candidate:
                candidates.append(candidate)
        return candidates

    async def _search_arxiv(self, query: str, *, max_results: int) -> List[PaperCandidate]:
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
        }
        response = await self._client.get(ARXIV_API, params=params)
        response.raise_for_status()
        return list(self._parse_arxiv_feed(response.text))

    async def _search_crossref(self, query: str, *, max_results: int,
                               filter_year_range: Optional[tuple[int, int]] = None) -> List[PaperCandidate]:
        params = {
            "query": query,
            "rows": max_results,
        }
        if filter_year_range:
            start, end = filter_year_range
            params["filter"] = f"from-pub-date:{start}-01-01,until-pub-date:{end}-12-31"
        response = await self._client.get(CROSSREF_API, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        payload = response.json()
        items = payload.get("message", {}).get("items", [])
        return [self._build_candidate_from_crossref(item) for item in items if item]

    async def _fetch_crossref_record(self, doi: str) -> Optional[dict]:
        safe_doi = doi.strip()
        url = f"{CROSSREF_API}/{safe_doi}"
        response = await self._client.get(url, headers={"Accept": "application/json"})
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        response.raise_for_status()
        return response.json().get("message")

    def _build_candidate_from_crossref(self, record: dict) -> PaperCandidate:
        title = self._extract_first(record.get("title")) or "Unknown title"
        authors = [self._format_crossref_author(a) for a in record.get("author", []) if a]
        doi = record.get("DOI")
        url = self._extract_first(record.get("URL"))
        published = record.get("published-print") or record.get("published-online") or {}
        year = self._extract_year(published)
        return PaperCandidate(
            title=title,
            authors=authors or ["Unknown"],
            doi=doi,
            source="crossref",
            url=url,
            published_year=year,
            metadata=record,
        )

    def _parse_bibtex(self, bib_file: Path) -> List[PaperCandidate]:
        content = bib_file.read_text(encoding="utf-8")
        entries = re.split(r"@\w+\s*{", content)[1:]
        candidates: List[PaperCandidate] = []
        for entry in entries:
            fields = self._extract_bibtex_fields(entry)
            title = fields.get("title")
            if not title:
                continue
            authors = [a.strip() for a in fields.get("author", "").split(" and ") if a.strip()]
            doi = fields.get("doi")
            url = fields.get("url")
            year = None
            try:
                year = int(fields.get("year", "").strip()) if fields.get("year") else None
            except ValueError:
                year = None
            candidates.append(
                PaperCandidate(
                    title=self._clean_field(title),
                    authors=[self._clean_field(a) for a in authors] or ["Unknown"],
                    doi=self._clean_field(doi) if doi else None,
                    source="bibliography",
                    url=self._clean_field(url) if url else None,
                    published_year=year,
                    metadata=fields,
                )
            )
        return candidates

    def _extract_bibtex_fields(self, entry: str) -> dict:
        fields = {}
        for line in entry.splitlines():
            if line.strip().startswith("}"):
                break
            match = re.match(r"\s*(\w+)\s*=\s*[{\"](.+)[}\"],?", line)
            if match:
                key, value = match.groups()
                fields[key.lower()] = value.strip()
        return fields

    def _clean_field(self, value: str) -> str:
        return re.sub(r"[{}]", "", value).strip()

    def _parse_arxiv_feed(self, xml_data: str) -> Iterable[PaperCandidate]:
        # Namespace map for Atom + arXiv extensions
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        root = ET.fromstring(xml_data)
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            title = re.sub(r"\s+", " ", (title_el.text or "").strip()) if title_el is not None else "Unknown title"

            authors = [
                name_el.text
                for author_el in entry.findall("atom:author", ns)
                if (name_el := author_el.find("atom:name", ns)) is not None and name_el.text
            ] or ["Unknown"]

            doi_el = entry.find("arxiv:doi", ns)
            doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

            id_el = entry.find("atom:id", ns)
            arxiv_id = None
            if id_el is not None and id_el.text:
                id_text = id_el.text.strip()
                if "/abs/" in id_text:
                    arxiv_id = id_text.split("/abs/")[-1]

            url = None
            for link in entry.findall("atom:link", ns):
                if link.get("rel") == "alternate" and link.get("type") == "text/html":
                    url = link.get("href")
                    break

            published_el = entry.find("atom:published", ns)
            published_year = None
            if published_el is not None and published_el.text:
                # ISO 8601: "2024-01-15T00:00:00Z" — extract year
                year_match = re.match(r"(\d{4})", published_el.text.strip())
                if year_match:
                    published_year = int(year_match.group(1))

            yield PaperCandidate(
                title=title,
                authors=authors,
                doi=doi,
                arxiv_id=arxiv_id,
                source="arxiv",
                url=url,
                published_year=published_year,
                metadata={"raw": ET.tostring(entry, encoding="unicode")},
            )

    def _extract_first(self, value) -> Optional[str]:
        if isinstance(value, list) and value:
            return value[0]
        if isinstance(value, str):
            return value
        return None

    def _format_crossref_author(self, author: dict) -> str:
        given = author.get("given", "").strip()
        family = author.get("family", "").strip()
        if given and family:
            return f"{given} {family}"
        return family or given or "Unknown"

    def _extract_year(self, published: dict) -> Optional[int]:
        date_parts = published.get("date-parts")
        if not date_parts:
            return None
        try:
            return int(date_parts[0][0])
        except (ValueError, TypeError, IndexError):
            return None


__all__ = ["DiscoveryEngine", "PaperCandidate"]
