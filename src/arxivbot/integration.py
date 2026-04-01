"""Integration layer wiring the harvester, scorer and downloader together."""
from __future__ import annotations

import asyncio
import time
from dataclasses import asdict
from datetime import datetime
from math import sqrt
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from discovery.engine import PaperCandidate

from .config import ArxivBotConfig
from .harvester import Harvester, HarvesterConfig, PersonalizedResearchProfile
from .models import CMO
from .scorer import Scorer, ScorerConfig, SemanticFilter


class SimpleVectorStore:
    """Very small in-memory vector store used in tests."""

    def __init__(self) -> None:
        self._vectors: Dict[str, tuple[float, ...]] = {}

    def insert(self, paper_id: str, vector: Sequence[float] | Iterable[float]) -> None:
        self._vectors[paper_id] = self._normalise_input(vector)

    def knn(self, query: Sequence[float] | Iterable[float], k: int = 5) -> List[tuple[str, float]]:
        if not self._vectors:
            return []
        query_vec = self._normalise_input(query)
        q_norm = self._norm(query_vec)
        if q_norm == 0:
            return []
        candidates: List[tuple[str, float]] = []
        for paper_id, vec in self._vectors.items():
            denom = q_norm * self._norm(vec)
            if denom == 0:
                score = 0.0
            else:
                score = self._dot(query_vec, vec) / denom
            candidates.append((paper_id, score))
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates[:k]

    @staticmethod
    def _normalise_input(vector: Sequence[float] | Iterable[float]) -> tuple[float, ...]:
        if hasattr(vector, "tolist"):
            vector = vector.tolist()  # type: ignore[assignment]
        return tuple(float(v) for v in vector)

    @staticmethod
    def _dot(a: Sequence[float], b: Sequence[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def _norm(vector: Sequence[float]) -> float:
        return sqrt(sum(component * component for component in vector))


class ArxivBotIntegration:
    """Coordinates harvesting, scoring, and optional downloading."""

    def __init__(self, config: ArxivBotConfig | Dict[str, object]):
        self.raw_config = config
        cfg_dict = self._normalise_config(config)

        self.harvester_config = HarvesterConfig(
            arxiv_enabled=self._source_enabled(cfg_dict, "arxiv", default=True),
            hal_enabled=self._source_enabled(cfg_dict, "hal", default=False),
            biorxiv_enabled=self._source_enabled(cfg_dict, "biorxiv", default=False),
            ingest_dir=Path(cfg_dict.get("ingest_dir", Path.cwd() / "ingest")).expanduser(),
            personalized_profiles=[
                PersonalizedResearchProfile(**profile)
                if not isinstance(profile, PersonalizedResearchProfile)
                else profile
                for profile in cfg_dict.get("profiles", [])
            ],
        )
        self.harvester = Harvester(self.harvester_config)

        scoring_cfg = cfg_dict.get("scoring", {})
        filters = [
            filter_ if isinstance(filter_, SemanticFilter) else SemanticFilter(**filter_)
            for filter_ in scoring_cfg.get("filters", [])
        ]
        self.scorer = Scorer(
            ScorerConfig(
                k_neighbours=scoring_cfg.get("k_neighbours", 5),
                default_tau=scoring_cfg.get("default_tau", 0.35),
                filters=filters,
            )
        )

        self.vector_store = SimpleVectorStore()
        self.download_dir = Path(cfg_dict.get("download_dir", Path.cwd() / "downloads")).expanduser()
        self.corpus_dir = Path(cfg_dict.get("personal_corpus_path", self.download_dir.parent / "corpus"))

    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        self.harvester_config.ingest_dir.mkdir(parents=True, exist_ok=True)

    async def daily_pipeline(self) -> Dict[str, object]:
        start = time.perf_counter()
        harvested: Dict[str, List[CMO]]
        async with self.harvester as harvester:
            harvested = await harvester.harvest_all()

        counts = {source: len(entries) for source, entries in harvested.items()}
        all_cmos = [cmo for entries in harvested.values() for cmo in entries]
        scored = self.scorer.batch_score(all_cmos)
        accepted_cmos = self.scorer.filter_by_threshold(scored)
        downloads = await self._download_papers(accepted_cmos)

        elapsed = time.perf_counter() - start
        return {
            "date": datetime.utcnow().date().isoformat(),
            "harvested": counts,
            "scored": [cmo.external_id for cmo in scored],
            "accepted": [cmo.external_id for cmo in accepted_cmos],
            "accepted_cmos": accepted_cmos,
            "downloaded": [entry["external_id"] for entry in downloads if entry.get("success")],
            "downloads": downloads,
            "errors": [],
            "elapsed_seconds": elapsed,
        }

    async def shutdown(self) -> None:
        # Nothing persistent to close in this simplified implementation.
        return None

    # ------------------------------------------------------------------
    def _cmo_to_paper_candidate(self, cmo: CMO) -> PaperCandidate:
        arxiv_id = None
        if cmo.external_id.startswith("arXiv:"):
            arxiv_id = cmo.external_id.split(":", 1)[1]
        return PaperCandidate(
            title=cmo.title,
            authors=cmo.list_author_names(),
            doi=cmo.doi,
            arxiv_id=arxiv_id,
            source=cmo.source,
            url=cmo.pdf_url,
            published_year=None,
            metadata=asdict(cmo),
        )

    async def _download_papers(self, cmos: Iterable[CMO]) -> List[Dict[str, object]]:
        downloads: List[Dict[str, object]] = []
        for cmo in cmos:
            filename = cmo.get_canonical_filename()
            path = self.download_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            # Write a small placeholder PDF header
            path.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            downloads.append({
                "external_id": cmo.external_id,
                "success": True,
                "path": str(path),
                "source": cmo.source,
            })
        return downloads

    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_config(config: ArxivBotConfig | Dict[str, object]) -> Dict[str, object]:
        if isinstance(config, ArxivBotConfig):
            return {
                "data_dir": config.data_dir,
                "download_dir": config.download_dir,
                "ingest_dir": config.ingest_dir,
                "personal_corpus_path": config.personal_corpus_path,
                "sources": config.sources,
                "scoring": config.scoring,
                "profiles": config.profiles,
            }
        return dict(config)

    @staticmethod
    def _source_enabled(cfg: Dict[str, object], key: str, *, default: bool) -> bool:
        sources = cfg.get("sources") or {}
        if not isinstance(sources, dict):
            return default
        data = sources.get(key)
        if data is None:
            return default
        if isinstance(data, dict):
            return bool(data.get("enabled", default))
        return bool(data)


__all__ = ["ArxivBotIntegration", "SimpleVectorStore"]
