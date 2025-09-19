#!/usr/bin/env python3
"""Organization, validation, and duplicate detection utilities."""

from __future__ import annotations

import logging
import os
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OrganizationResult:
    file_path: Path
    destination: Path
    actions: List[str]
    subjects: List[str]
    publication_status: str
    duplicate_of: Optional[Path] = None


class ContentValidator:
    def validate_pdf_integrity(self, file_path: Path) -> bool:
        if not file_path.exists():
            logger.warning("File missing during content validation: %s", file_path)
            return False
        with open(file_path, "rb") as fh:
            header = fh.read(4)
        return header == b"%PDF"


class SubjectClassifier:
    ARXIV_MAP = {
        "math": "Mathematics",
        "cs": "Computer Science",
        "physics": "Physics",
    }

    def classify(self, metadata: Dict[str, any]) -> List[str]:
        subjects: List[str] = []
        if arxiv_id := metadata.get("arxiv_id"):
            prefix = arxiv_id.split('.', 1)[0]
            category = prefix.split(':')[0] if ':' in prefix else prefix
            subjects.append(self.ARXIV_MAP.get(category, category))
        elif doi := metadata.get("doi"):
            if doi.startswith("10."):
                subjects.append("Published")
        if keywords := metadata.get("keywords"):
            subjects.extend(keywords)
        return subjects or ["Unclassified"]


class FolderRouter:
    def __init__(self, base_folder: Path):
        self.base_folder = base_folder

    def determine_publication_status(self, metadata: Dict[str, any]) -> str:
        if metadata.get("doi"):
            return "published"
        if metadata.get("arxiv_id"):
            return "preprint"
        return "working"

    def select_subject_folder(self, subjects: List[str]) -> Path:
        subject = subjects[0].replace(' ', '_')
        return self.base_folder / subject

    def ensure_folder(self, path: Path, dry_run: bool) -> None:
        if dry_run:
            logger.debug("Dry run: would create folder %s", path)
            return
        path.mkdir(parents=True, exist_ok=True)


class DuplicateDetector:
    def find_exact_duplicates(self, files: Iterable[Path]) -> Dict[str, List[Path]]:
        hash_map: Dict[str, List[Path]] = defaultdict(list)
        for file_path in files:
            if not file_path.exists():
                continue
            digest = self._hash_file(file_path)
            hash_map[digest].append(file_path)
        return {digest: paths for digest, paths in hash_map.items() if len(paths) > 1}

    def _hash_file(self, file_path: Path) -> str:
        import hashlib
        hasher = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


class VersionManager:
    def detect_version_relationship(self, metadata: Dict[str, any]) -> Optional[str]:
        return metadata.get("doi") or metadata.get("arxiv_id")


class OrganizationSystem:
    def __init__(self, base_folder: Path, *, dry_run: bool = False):
        self.base_folder = base_folder
        self.dry_run = dry_run
        self.validator = ContentValidator()
        self.classifier = SubjectClassifier()
        self.router = FolderRouter(base_folder)
        self.version_manager = VersionManager()
        self.duplicate_detector = DuplicateDetector()

    def organize(self, file_path: Path, metadata: Dict[str, any]) -> OrganizationResult:
        is_valid = self.validator.validate_pdf_integrity(file_path)
        if not is_valid:
            logger.warning("File %s failed integrity validation", file_path)

        subjects = self.classifier.classify(metadata)
        status = self.router.determine_publication_status(metadata)
        target_folder = self.router.select_subject_folder(subjects) / status
        self.router.ensure_folder(target_folder, self.dry_run)
        destination = target_folder / file_path.name

        actions: List[str] = []
        if not self.dry_run:
            if file_path.resolve() != destination.resolve():
                try:
                    shutil.copy2(file_path, destination)
                    actions.append(f"copied to {destination}")
                except Exception as exc:
                    logger.error("Failed to copy %s: %s", file_path, exc)
        else:
            actions.append(f"would copy to {destination}")

        version_key = self.version_manager.detect_version_relationship(metadata)
        if version_key:
            actions.append(f"version-key:{version_key}")

        return OrganizationResult(
            file_path=file_path,
            destination=destination,
            actions=actions,
            subjects=subjects,
            publication_status=status,
        )

    def find_duplicates(self, files: Iterable[Path]) -> Dict[str, List[Path]]:
        return self.duplicate_detector.find_exact_duplicates(files)


__all__ = [
    "OrganizationSystem",
    "OrganizationResult",
]
