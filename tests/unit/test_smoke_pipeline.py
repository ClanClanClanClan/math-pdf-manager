import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

from cli.args_parser import create_args_parser
from processing.main_processing import process_files
from publishers.unified_downloader import UnifiedDownloader


def _dummy_config(base_path: Path) -> SimpleNamespace:
    base_path = Path(base_path)
    return SimpleNamespace(
        known_words=set(),
        capitalization_whitelist=set(),
        exceptions=set(),
        config={
            'base_maths_folder': str(base_path),
            'database_path': str(base_path / "papers.db"),
        }
    )


def test_process_files_empty_directory(tmp_path):
    summary = process_files(
        tmp_path,
        _dummy_config(tmp_path),
        logger_service=logging.getLogger("test_process_files_empty"),
    )

    assert summary["total_candidate_files"] == 0
    assert summary["processed"] == 0
    assert summary["failed"] == 0
    assert summary["organization"] == []
    assert summary["duplicates"] == {}


def test_process_files_single_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    summary = process_files(
        tmp_path,
        _dummy_config(tmp_path),
        logger_service=logging.getLogger("test_process_files_pdf"),
    )

    assert summary["total_candidate_files"] == 1
    assert summary["processed"] == 1
    assert summary["failed"] == 0
    assert len(summary["organization"]) == 1


def test_process_files_persists_to_database(tmp_path):
    pdf_path = tmp_path / "stored.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    summary = process_files(
        tmp_path,
        _dummy_config(tmp_path),
        logger_service=logging.getLogger("test_process_files_db"),
        dry_run=False,
    )

    from core.database import AsyncPaperDatabase

    db_path = Path(summary["database_path"])
    db = AsyncPaperDatabase(str(db_path))

    async def fetch():
        return await db.get_paper_by_path(str(pdf_path.resolve()))

    record = asyncio.run(fetch())
    assert record is not None
    assert "stored" in record.title.lower()


def test_create_args_parser_exposes_expected_options():
    parser = create_args_parser()
    opts = {action.dest for action in parser._actions}
    assert "max_files" in opts
    assert "dry_run" in opts


def test_unified_downloader_download_from_url(tmp_path):
    downloader = UnifiedDownloader()

    class DummyResponse:
        status = 200

        async def read(self):
            return b"%PDF-1.4\n"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySession:
        def get(self, url):
            return DummyResponse()

        async def close(self):
            return None

    destination = tmp_path / "downloaded.pdf"
    result = asyncio.run(
        downloader.download_from_url("https://example.com/paper.pdf", destination, session=DummySession())
    )

    assert result.success is True
    assert destination.exists()
