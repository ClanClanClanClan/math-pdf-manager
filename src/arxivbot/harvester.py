"""Simplified asynchronous harvesters for the ArXiv bot test-suite."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .models import Author, CMO


@dataclass
class PersonalizedResearchProfile:
    """Minimal representation of a personalised research focus."""

    name: str
    categories: List[str]
    keywords: List[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class HarvesterConfig:
    """Configuration consumed by :class:`Harvester`."""

    arxiv_enabled: bool = True
    hal_enabled: bool = False
    biorxiv_enabled: bool = False
    days_back: int = 7
    ingest_dir: Path = Path("ingest")
    personalized_profiles: List[PersonalizedResearchProfile] = field(default_factory=list)


class Harvester:
    """Coroutine-friendly harvester returning :class:`CMO` instances."""

    def __init__(self, config: HarvesterConfig):
        self.config = config
        if not isinstance(self.config.ingest_dir, Path):
            self.config.ingest_dir = Path(self.config.ingest_dir)
        self._active = False

    async def __aenter__(self) -> "Harvester":
        self._active = True
        self.config.ingest_dir.mkdir(parents=True, exist_ok=True)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._active = False

    async def harvest_all(self, target_date: Optional[_dt.date] = None) -> Dict[str, List[CMO]]:
        """Harvest from all enabled sources."""

        if not self._active:
            raise RuntimeError("Harvester must be used as an async context manager")

        results: Dict[str, List[CMO]] = {}
        if self.config.arxiv_enabled:
            results["arxiv"] = await self.harvest_arxiv(target_date)
        if self.config.hal_enabled:
            results["hal"] = []
        if self.config.biorxiv_enabled:
            results["biorxiv"] = []
        return results

    async def harvest_arxiv(self, target_date: Optional[_dt.date] = None) -> List[CMO]:
        """Harvest a small deterministic set of CMOs for tests."""

        date = target_date or _dt.date.today()
        authors = [Author(family="Researcher", given="Ada"), Author(family="Collaborator", given="Bob")]
        base = CMO(
            external_id=f"arXiv:{date:%Y%m%d}.00001",
            source="arxiv",
            title="A Sample Study on Graph Algorithms",
            authors=authors,
            published=f"{date.isoformat()}T00:00:00Z",
            abstract="We investigate deterministic constructions of expanders.",
            pdf_url="https://arxiv.org/pdf/0000.00001.pdf",
            categories=["cs.DS"],
        )
        papers = [base]
        for profile in self.config.personalized_profiles:
            for category in profile.categories:
                papers.append(
                    CMO(
                        external_id=f"arXiv:{date:%Y%m%d}.{hash(category) & 0xffff:05d}",
                        source="arxiv",
                        title=f"{profile.name} insights into {category}",
                        authors=authors,
                        published=f"{date.isoformat()}T00:00:00Z",
                        abstract="Profile-generated candidate",
                        categories=[category],
                    )
                )
        return papers

    async def harvest_profiles(self, profiles: Iterable[PersonalizedResearchProfile]) -> Dict[str, List[CMO]]:
        mapping: Dict[str, List[CMO]] = {}
        for profile in profiles:
            mapping[profile.name] = [
                CMO(
                    external_id=f"profile:{profile.name}:{idx}",
                    source="profile",
                    title=f"{profile.name} candidate {idx}",
                    authors=[Author(family="Profile")],
                    published=None,
                    abstract="Generated via personalised profile",
                    categories=profile.categories,
                )
                for idx, _ in enumerate(profile.categories, start=1)
            ]
        return mapping


__all__ = ["Harvester", "HarvesterConfig", "PersonalizedResearchProfile"]
