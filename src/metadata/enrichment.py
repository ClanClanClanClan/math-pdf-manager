#!/usr/bin/env python3
"""Metadata enrichment utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

try:  # Optional heavy dependency for richer enrichment
    import spacy
    _NLP = spacy.load("en_core_web_sm")
except Exception:  # pragma: no cover - spaCy or model may be unavailable
    _NLP = None


TOPIC_KEYWORDS = {
    "probability": {"probability", "stochastic", "random"},
    "optimization": {"optimization", "optimal", "gradient"},
    "machine learning": {"learning", "neural", "deep", "reinforcement"},
    "analysis": {"analysis", "harmonic", "functional"},
    "algebra": {"algebra", "group", "ring", "module"},
}

JOURNAL_QUALITY = {
    "annals of mathematics": {"tier": "A+"},
    "communications on pure and applied mathematics": {"tier": "A"},
}


@dataclass
class EnrichmentResult:
    topics: List[str]
    subject_area: Optional[str]
    journal_quality: Optional[Dict[str, str]]
    math_concepts: List[str]


def enrich_metadata(metadata: Dict[str, any]) -> EnrichmentResult:
    title = metadata.get('title', '')
    abstract = metadata.get('abstract', '')
    journal = metadata.get('journal', '')

    text = f"{title} {abstract}".lower()
    topics = _detect_topics(text)
    subject = _classify_subject_area(metadata)
    journal_quality = _assess_journal_quality(journal)
    math_concepts = _extract_mathematical_concepts(text)
    if _NLP is not None:
        try:
            doc = _NLP(text)
            topics.extend(_extract_topics_spacy(doc))
            math_concepts.extend(_extract_spacy_entities(doc))
        except Exception:
            pass

    topics = sorted(set(topics))
    math_concepts = sorted(set(math_concepts))

    metadata.setdefault('topics', topics)
    metadata.setdefault('subject_area', subject)
    metadata.setdefault('journal_quality', journal_quality)
    metadata.setdefault('mathematical_concepts', math_concepts)

    return EnrichmentResult(
        topics=topics,
        subject_area=subject,
        journal_quality=journal_quality,
        math_concepts=math_concepts,
    )


def _detect_topics(text: str) -> List[str]:
    detected = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            detected.append(topic)
    return detected or ["unspecified"]


def _classify_subject_area(metadata: Dict[str, any]) -> Optional[str]:
    if metadata.get('arxiv_id'):
        prefix = metadata['arxiv_id'].split('.', 1)[0]
        category = prefix.split(':')[0] if ':' in prefix else prefix
        mapping = {
            'math': 'Mathematics',
            'cs': 'Computer Science',
            'physics': 'Physics',
        }
        return mapping.get(category)
    if metadata.get('doi'):
        return 'Published Work'
    return None


def _assess_journal_quality(journal: str) -> Optional[Dict[str, str]]:
    key = journal.lower().strip()
    return JOURNAL_QUALITY.get(key)


def _extract_mathematical_concepts(text: str) -> List[str]:
    patterns = {
        'laplacian': r'laplacian',
        'fourier transform': r'fourier',
        'markov chain': r'markov',
    }
    return [name for name, pattern in patterns.items() if re.search(pattern, text)]


def _extract_topics_spacy(doc) -> List[str]:
    ranked = {token.lemma_.lower() for token in doc if token.pos_ in {"NOUN", "PROPN"} and len(token) > 3}
    return sorted(ranked)


def _extract_spacy_entities(doc) -> List[str]:
    labels = {"ORG", "LAW", "NORP", "FAC"}
    return [ent.text for ent in doc.ents if ent.label_ in labels]


__all__ = ["enrich_metadata", "EnrichmentResult"]
