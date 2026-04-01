"""Lightweight ArXiv bot framework used by the discovery pipeline tests."""
from __future__ import annotations

from .config import ArxivBotConfig, load_or_create_config
from .harvester import Harvester, HarvesterConfig, PersonalizedResearchProfile
from .integration import ArxivBotIntegration, SimpleVectorStore
from .main import ArxivBot
from .scorer import Scorer, ScorerConfig, SemanticFilter

__all__ = [
    "ArxivBot",
    "ArxivBotConfig",
    "ArxivBotIntegration",
    "Harvester",
    "HarvesterConfig",
    "PersonalizedResearchProfile",
    "Scorer",
    "ScorerConfig",
    "SemanticFilter",
    "SimpleVectorStore",
    "load_or_create_config",
]
