#!/usr/bin/env python3
"""
Main Processing Module
======================

Core processing functions for the Academic Paper Management System.
"""

import os
import hashlib
import json
import re
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

from organization.system import OrganizationSystem
from core.database import AsyncPaperDatabase, PaperRecord
from metadata.enrichment import enrich_metadata

logger = logging.getLogger(__name__)


def _extract_pdf_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from a PDF file using the enhanced extraction pipeline.

    Tries the full ``EnhancedPDFParser`` pipeline (ArXiv API, Crossref,
    GROBID, heuristics, LLM) via the facade.  Falls back to PyMuPDF
    embedded-metadata / filename heuristics when the facade is not available
    or the file is too small.
    """
    # Try the enhanced extraction facade first
    try:
        from pdf_processing.extract_metadata_facade import extract_pdf_metadata_enhanced

        # Skip enhanced extraction for very small files (test stubs, etc.)
        if file_path.stat().st_size >= 512:
            meta = extract_pdf_metadata_enhanced(file_path)
            if meta.get("confidence", 0) >= 0.3:
                return {
                    'title': meta.get('title', file_path.stem),
                    'authors': meta.get('authors', []),
                    'year': meta.get('year'),
                    'abstract': meta.get('abstract', ''),
                    'doi': meta.get('doi'),
                    'arxiv_id': meta.get('arxiv_id'),
                    'source_method': meta.get('source_method', 'enhanced'),
                    'confidence': meta.get('confidence', 0),
                }
    except ImportError:
        logger.debug("Enhanced extraction facade not available, using PyMuPDF fallback")
    except Exception as e:
        logger.warning(f"Enhanced extraction failed for {file_path}: {e}")

    # Fallback: PyMuPDF embedded metadata + filename heuristics
    return _extract_pdf_metadata_fallback(file_path)


def _extract_pdf_metadata_fallback(file_path: Path) -> Dict[str, Any]:
    """Fallback metadata extraction using PyMuPDF embedded metadata.

    Used when the enhanced pipeline is unavailable or fails.
    """
    metadata: Dict[str, Any] = {
        'title': '',
        'authors': [],
        'year': None,
        'abstract': '',
    }

    try:
        import fitz  # PyMuPDF

        # Guard: skip PyMuPDF for files too small to be valid PDFs (avoids
        # crashes on malformed test stubs).  The smallest valid PDF with any
        # content is ~500 bytes; academic papers are orders of magnitude larger.
        if file_path.stat().st_size < 512:
            raise ValueError("File too small for reliable PDF parsing")

        doc = fitz.open(str(file_path))
        try:
            info = doc.metadata or {}

            raw_title = (info.get('title') or '').strip()
            metadata['title'] = raw_title if raw_title else file_path.stem

            raw_author = (info.get('author') or '').strip()
            if raw_author:
                # Authors may be separated by commas, semicolons, or " and "
                parts = [a.strip() for a in raw_author.replace(' and ', ';').replace(',', ';').split(';') if a.strip()]
                metadata['authors'] = parts if parts else [raw_author]
            else:
                metadata['authors'] = []

            # Try to extract year from creationDate (format: D:YYYYMMDDHHmmSS...)
            creation_date = (info.get('creationDate') or '').strip()
            if creation_date:
                m = re.search(r'D:(\d{4})', creation_date)
                if m:
                    metadata['year'] = int(m.group(1))

            # Extract first-page text for abstract heuristic
            if doc.page_count > 0:
                first_page_text = doc[0].get_text()
                # Look for an abstract section
                abstract_match = re.search(
                    r'(?i)\babstract\b[:\s.\-]*\n?(.*?)(?:\n\s*\n|\b(?:introduction|keywords|1[\.\s])\b)',
                    first_page_text,
                    re.DOTALL,
                )
                if abstract_match:
                    abstract_text = re.sub(r'\s+', ' ', abstract_match.group(1)).strip()
                    if len(abstract_text) > 20:
                        metadata['abstract'] = abstract_text
        finally:
            doc.close()

    except Exception:
        # Fallback: derive title from filename stem
        metadata['title'] = file_path.stem

    # Ensure title is never empty
    if not metadata['title']:
        metadata['title'] = file_path.stem

    return metadata


def process_file(file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process a single academic paper file.
    
    Args:
        file_path: Path to the file to process
        config: Processing configuration
        
    Returns:
        Dictionary with processing results
    """
    if config is None:
        config = {}
    
    file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        return {
            'success': False,
            'error': f'File not found: {file_path}',
            'file_path': str(file_path)
        }
    
    # Check if it's a PDF
    if file_path.suffix.lower() != '.pdf':
        return {
            'success': False,
            'error': 'Not a PDF file',
            'file_path': str(file_path)
        }
    
    # Process the file (mock processing)
    try:
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Get file stats
        stats = file_path.stat()
        
        # Extract metadata from PDF using PyMuPDF
        metadata = _extract_pdf_metadata(file_path)
        
        return {
            'success': True,
            'file_path': str(file_path),
            'file_hash': file_hash,
            'file_size': stats.st_size,
            'metadata': metadata,
            'processed_with': config.get('processor', 'default')
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'file_path': str(file_path)
        }


def verify_output(output: Dict[str, Any], expected_format: Dict[str, Any] = None) -> bool:
    """
    Verify that processing output matches expected format.
    
    Args:
        output: Output from process_file
        expected_format: Expected format specification
        
    Returns:
        True if output is valid, False otherwise
    """
    if expected_format is None:
        expected_format = {
            'required_fields': ['success', 'file_path'],
            'optional_fields': ['error', 'metadata', 'file_hash', 'file_size']
        }
    
    # Check required fields
    required = expected_format.get('required_fields', ['success', 'file_path'])
    for field in required:
        if field not in output:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Check success/error logic
    if output.get('success'):
        # Successful processing should have metadata
        if 'metadata' not in output and 'file_hash' not in output:
            logger.warning("Successful processing but no metadata or hash")
            return False
    else:
        # Failed processing should have error
        if 'error' not in output:
            logger.error("Failed processing but no error message")
            return False
    
    return True


def process_batch(file_paths: List[str], config: Dict[str, Any] = None, 
                  parallel: bool = False) -> List[Dict[str, Any]]:
    """
    Process multiple files.
    
    Args:
        file_paths: List of file paths to process
        config: Processing configuration
        parallel: Whether to process in parallel
        
    Returns:
        List of processing results
    """
    results = []
    
    if parallel:
        # Mock parallel processing
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_file, path, config) for path in file_paths]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    else:
        # Sequential processing
        for file_path in file_paths:
            result = process_file(file_path, config)
            results.append(result)
    
    return results


def cleanup_processed_files(results: List[Dict[str, Any]], move_to: str = None) -> Dict[str, Any]:
    """
    Clean up or organize processed files.
    
    Args:
        results: Processing results from process_batch
        move_to: Optional directory to move processed files to
        
    Returns:
        Cleanup summary
    """
    summary = {
        'files_processed': 0,
        'files_moved': 0,
        'files_failed': 0,
        'errors': []
    }
    
    for result in results:
        if result.get('success'):
            summary['files_processed'] += 1
            
            if move_to:
                try:
                    source = Path(result['file_path'])
                    dest_dir = Path(move_to)
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    dest = dest_dir / source.name
                    source.rename(dest)
                    summary['files_moved'] += 1
                    
                except Exception as e:
                    summary['errors'].append(str(e))
        else:
            summary['files_failed'] += 1
            if 'error' in result:
                summary['errors'].append(result['error'])
    
    return summary


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate processing configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if config is valid
    """
    # Check for required config keys
    required_keys = []  # No required keys for basic processing
    
    for key in required_keys:
        if key not in config:
            logger.error(f"Missing required config key: {key}")
            return False
    
    # Validate specific config values
    if 'max_file_size' in config:
        if not isinstance(config['max_file_size'], (int, float)) or config['max_file_size'] <= 0:
            logger.error("Invalid max_file_size in config")
            return False
    
    if 'output_format' in config:
        valid_formats = ['json', 'csv', 'xml']
        if config['output_format'] not in valid_formats:
            logger.error(f"Invalid output_format: {config['output_format']}")
            return False
    
    return True


def verify_configuration(config_data: Any) -> List[str]:
    """Run high-level checks against the loaded configuration object.

    The configuration loader used by the CLI has historically returned a
    variety of lightweight data containers.  Rather than enforcing a concrete
    type hierarchy here we rely on duck typing and report non-critical issues
    as warnings so the caller can decide how to proceed.
    """

    warnings: List[str] = []

    # The config migration layer populates these collections.  When they are
    # empty it usually signals that the underlying resource files failed to
    # load (missing data, wrong path, etc.).
    collection_checks: List[Tuple[str, str]] = [
        ("known_words", "Known words list is empty"),
        ("capitalization_whitelist", "Capitalization whitelist is empty"),
        ("exceptions", "Exceptions list is empty"),
    ]

    for attribute, warning_message in collection_checks:
        values = getattr(config_data, attribute, None)
        if isinstance(values, (list, set, tuple)):
            if not values:
                warnings.append(warning_message)
        elif values is None:
            warnings.append(f"Configuration missing '{attribute}' data")

    # Ensure the configured maths folder exists when specified.
    base_folder = None
    if hasattr(config_data, "config") and isinstance(config_data.config, dict):
        base_folder = config_data.config.get("base_maths_folder")

    if base_folder:
        base_path = Path(base_folder).expanduser()
        if not base_path.exists():
            warnings.append(f"Base maths folder does not exist: {base_folder}")

    return warnings


def _collect_pdf_files(root: Path, max_files: Optional[int] = None) -> List[Path]:
    """Return deterministically ordered PDF files under ``root``."""

    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Root directory not found: {root}")

    pdf_files = sorted(path for path in root.rglob("*.pdf") if path.is_file())

    if max_files is not None and max_files >= 0:
        pdf_files = pdf_files[:max_files]

    return pdf_files


def process_files(
    root_directory: Path,
    config_data: Any,
    *,
    max_files: Optional[int] = None,
    parallel_workers: int = 1,
    dry_run: bool = False,
    logger_service: Optional[Any] = None,
    metrics_service: Optional[Any] = None,
) -> Dict[str, Any]:
    """Process PDF files within ``root_directory``.

    Args:
        root_directory: Directory containing candidate PDF files.
        config_data: Loaded configuration object (kept for future use).
        max_files: Optional hard limit on the number of files to process.
        parallel_workers: Desired parallelism level (>1 triggers thread pool).
        dry_run: When ``True`` the pipeline still performs analysis but callers
            can use the flag to skip write actions.
        logger_service: Optional logging facade implementing ``info``/``debug``.
        metrics_service: Optional metrics sink with ``increment_counter`` and
            ``record_timing`` methods.

    Returns:
        Dictionary containing a processing summary and individual file results.
    """

    log = logger_service or logger

    root_directory = Path(root_directory).expanduser().resolve()
    log.debug(f"Collecting PDF files in {root_directory}")

    pdf_files = _collect_pdf_files(root_directory, max_files=max_files)
    base_folder = Path(config_data.config.get('base_maths_folder', root_directory)).expanduser()
    db_path = Path(config_data.config.get('database_path', base_folder / "papers.db")).expanduser()
    database = AsyncPaperDatabase(str(db_path))

    if not pdf_files:
        log.info("No PDF files found – nothing to do")
        return {
            "root": str(root_directory),
            "total_candidate_files": 0,
            "processed": 0,
            "failed": 0,
            "duration_seconds": 0.0,
            "results": [],
            "dry_run": dry_run,
            "parallel_workers": parallel_workers,
            "organization": [],
            "duplicates": {},
            "database_path": str(db_path),
        }

    config = get_default_config()
    config['processor'] = 'cli'
    config['parallel_processing'] = parallel_workers > 1

    if parallel_workers > 1:
        config['max_workers'] = parallel_workers

    start_time = time.time()
    log.info(f"Processing {len(pdf_files)} PDF file(s)")

    results = process_batch(
        [str(path) for path in pdf_files],
        config=config,
        parallel=config['parallel_processing']
    )

    duration = time.time() - start_time
    successes = [result for result in results if result.get('success')]
    failures = [result for result in results if not result.get('success')]

    if metrics_service:
        metrics_service.increment_counter("processed_files_total", len(results))
        metrics_service.increment_counter("processed_files_success", len(successes))
        metrics_service.increment_counter("processed_files_failed", len(failures))
        metrics_service.record_timing("processing_duration_ms", duration * 1000)

    organization_system = OrganizationSystem(base_folder, dry_run=dry_run)
    organization_reports = []

    upsert_tasks: List[Dict[str, Any]] = []

    for result in successes:
        metadata = result.get('metadata', {}).copy()
        metadata.setdefault('title', metadata.get('title') or Path(result['file_path']).stem)
        metadata.setdefault('authors', metadata.get('authors', []))
        metadata.setdefault('doi', metadata.get('doi'))
        metadata.setdefault('arxiv_id', metadata.get('arxiv_id'))
        enrichment = enrich_metadata(metadata)
        metadata['topics'] = enrichment.topics
        metadata['subject_area'] = enrichment.subject_area
        metadata['journal_quality'] = enrichment.journal_quality
        metadata['mathematical_concepts'] = enrichment.math_concepts
        report = organization_system.organize(Path(result['file_path']), metadata)
        organization_reports.append(report)

        upsert_tasks.append({
            'result': result,
            'metadata': metadata,
            'report': report,
        })

    async def _run_upserts(db: AsyncPaperDatabase, tasks: List[Dict[str, Any]]) -> None:
        for task in tasks:
            result_item = task['result']
            meta = task['metadata']
            rpt = task['report']

            resolved = str(Path(result_item['file_path']).resolve())
            existing = await db.get_paper_by_path(resolved)

            authors = meta.get('authors', [])
            if isinstance(authors, list):
                normalized_authors = [a.get('name') if isinstance(a, dict) else str(a) for a in authors]
            else:
                normalized_authors = [str(authors)]

            keywords = meta.get('topics', [])
            research_areas = meta.get('mathematical_concepts', [])

            publication_date = None
            if meta.get('published_year'):
                publication_date = str(meta['published_year'])

            record = PaperRecord(
                file_path=resolved,
                title=meta['title'],
                authors=json.dumps(normalized_authors),
                publication_date=publication_date,
                arxiv_id=meta.get('arxiv_id'),
                doi=meta.get('doi'),
                journal=meta.get('journal'),
                abstract=meta.get('abstract', ''),
                keywords=json.dumps(keywords),
                research_areas=json.dumps(research_areas),
                paper_type=rpt.publication_status,
                source=meta.get('source', 'local'),
                confidence=float(result_item.get('confidence', 1.0)),
                file_size=Path(resolved).stat().st_size if Path(resolved).exists() else 0,
            )

            if existing:
                record.id = existing.id
                record.created_at = existing.created_at
                await db.update_paper(record)
            else:
                await db.add_paper(record)

    if upsert_tasks:
        asyncio.run(_run_upserts(database, upsert_tasks))

    duplicate_map = organization_system.find_duplicates(Path(res['file_path']) for res in successes)

    if failures:
        log.warning(f"{len(failures)} file(s) failed to process")
    else:
        log.info("All files processed successfully")

    summary = {
        "root": str(root_directory),
        "total_candidate_files": len(pdf_files),
        "processed": len(successes),
        "failed": len(failures),
        "duration_seconds": round(duration, 4),
        "results": results,
        "dry_run": dry_run,
        "parallel_workers": parallel_workers,
        "organization": [
            {
                'file': str(report.file_path),
                'destination': str(report.destination),
                'actions': report.actions,
                'subjects': report.subjects,
                'status': report.publication_status,
            }
            for report in organization_reports
        ],
        "duplicates": {digest: [str(path) for path in paths] for digest, paths in duplicate_map.items()},
        "database_path": str(db_path),
    }

    return summary


def get_default_config() -> Dict[str, Any]:
    """
    Get default processing configuration.
    
    Returns:
        Default configuration dictionary
    """
    return {
        'processor': 'default',
        'max_file_size': 100 * 1024 * 1024,  # 100MB
        'output_format': 'json',
        'extract_metadata': True,
        'verify_output': True,
        'parallel_processing': False,
        'timeout': 300  # 5 minutes
    }


# Compatibility function for tests
def verify_processing_output(output: Dict[str, Any]) -> bool:
    """Compatibility wrapper for verify_output."""
    return verify_output(output)
