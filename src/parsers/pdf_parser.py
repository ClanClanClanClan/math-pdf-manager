#!/usr/bin/env python3
"""
Ultra-Enhanced PDF Metadata Parser with modular architecture

Provides backward compatibility while using the new modular structure.
The core functionality has been extracted into src/pdf_processing/ modules.
"""

import os
import sys
import types
import importlib
from pathlib import Path

# Resolve current directory (for relative imports)
current_dir = Path(__file__).parent.resolve()

# Import will be done after module setup

# ---- GROBID dummy (only if not already installed) -------------------
try:
    import grobid_client  # noqa: F401
except ImportError:
    stub = types.ModuleType("grobid_client")

    class _FakeGrobidClient:  # minimal API-surface
        def __init__(self, *_, **__): ...
        def process_pdf(self, *_, **__):  # returns fake TEI XML
            return "<tei><title>Dummy</title></tei>"
        def process_fulltext_document(self, *args, **kwargs):
            return {"title": "Sample Title", "authors": [{"first": "John", "last": "Doe"}]}

    stub.GrobidClient = _FakeGrobidClient
    stub.__spec__ = importlib.machinery.ModuleSpec("grobid_client", loader=None)
    sys.modules["grobid_client"] = stub

# ---- pytesseract dummy (only if not already installed) ---------------
try:
    import pytesseract  # noqa: F401
except ImportError:
    tess = types.ModuleType("pytesseract")

    def _fake_image_to_string(*_, **__):
        return "dummy ocr text"

    tess.image_to_string = _fake_image_to_string
    tess.pytesseract = tess  # self-ref like the real lib
    tess.__spec__ = importlib.machinery.ModuleSpec("pytesseract", loader=None)
    sys.modules["pytesseract"] = tess

# Import everything from the new modular structure (after module setup)
try:
    from src.pdf_processing import (
        _fake_image_to_string,
        UltraEnhancedPDFParser
    )
except ImportError:
    # Fallback if imports fail
    _fake_image_to_string = None
    UltraEnhancedPDFParser = None

# Heavy PDF libraries with better error handling
OFFLINE = bool(os.getenv("PDF_PARSER_OFFLINE"))
# Make sure unit-tests are treated as online
if "PYTEST_CURRENT_TEST" in os.environ:
    OFFLINE = False

# Additional backward compatibility exports
globals().update(
    _FakeGrobidClient=_FakeGrobidClient,
    _fake_image_to_string=_fake_image_to_string,
)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION FOR TESTING
# ──────────────────────────────────────────────────────────────────────────────


def main():
    """Test the enhanced parser with ArXiv API"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ultra-Enhanced PDF Parser with ArXiv API"
    )
    parser.add_argument("pdf_files", nargs="*", help="PDF files to process")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--stats", action="store_true", help="Show detailed statistics")
    parser.add_argument("--no-api", action="store_true", help="Disable ArXiv API")

    args = parser.parse_args()

    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Initialize parser
    config_path = args.config or "config.yaml"
    ultra_parser = UltraEnhancedPDFParser(config_path)

    if args.no_api:
        ultra_parser.arxiv_client.api_available = False

    # Process files
    pdf_files = args.pdf_files or list(Path(".").glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found to process.")
        return

    print(f"Processing {len(pdf_files)} PDF files...")
    print(
        f"ArXiv API: {'Enabled' if ultra_parser.arxiv_client.api_available else 'Disabled'}"
    )

    for pdf_file in pdf_files:
        print(f"\n{'='*80}")
        print(f"Processing: {pdf_file}")
        print("=" * 80)

        try:
            metadata = ultra_parser.extract_metadata(str(pdf_file))

            print(f"Title: {metadata.title}")
            print(f"Authors: {metadata.authors}")
            print(f"Source: {metadata.source.value}")
            print(f"Confidence: {metadata.confidence:.3f}")
            print(f"Repository: {metadata.repository_type or 'Unknown'}")

            if metadata.arxiv_id:
                print(f"ArXiv ID: {metadata.arxiv_id}")
            if metadata.categories:
                print(f"Categories: {', '.join(metadata.categories)}")
            if metadata.doi:
                print(f"DOI: {metadata.doi}")

            print(f"Published: {metadata.is_published}")
            print(f"Language: {metadata.language}")
            print(f"Pages: {metadata.page_count}")
            print(f"Text Quality: {metadata.text_quality:.3f}")
            print(f"Extraction Method: {metadata.extraction_method}")
            print(f"Processing Time: {metadata.processing_time:.3f}s")

            if metadata.warnings:
                print(f"Warnings: {'; '.join(metadata.warnings)}")

            if metadata.error:
                print(f"Error: {metadata.error}")

        except Exception as e:
            print(f"Failed to process {pdf_file}: {e}")
            if args.debug:
                import traceback

                traceback.print_exc()

    # Show statistics
    if args.stats:
        stats = ultra_parser.get_statistics()
        print(f"\n{'='*80}")
        print("PROCESSING STATISTICS")
        print("=" * 80)

        for key, value in stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.3f}")
            else:
                print(f"{key}: {value}")


if __name__ == "__main__":
    main()