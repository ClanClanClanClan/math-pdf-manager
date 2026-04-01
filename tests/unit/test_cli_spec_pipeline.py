import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def test_cli_spec_pipeline_persists_summary_and_json(tmp_path, monkeypatch, capsys):
    # Create dummy mathpdf.arxivbot.config and mathpdf.arxivbot.main modules
    cfg_module = ModuleType("mathpdf.arxivbot.config")

    def load_or_create_config(_path=None):
        return SimpleNamespace(data_dir=str(tmp_path))

    cfg_module.load_or_create_config = load_or_create_config

    bot_module = ModuleType("mathpdf.arxivbot.main")

    class DummyBot:
        def __init__(self, cfg):
            self.cfg = cfg

        async def initialize(self):
            return None

        async def run_daily_pipeline(self):
            return {
                'papers_harvested': 5,
                'papers_accepted': 2,
                'papers_downloaded': 1,
                'digest_path': str(tmp_path / 'digests' / 'digest_2099-01-01.md'),
                'elapsed_seconds': 0.42,
                'harvested_per_source': {'arxiv': 5},
                'accepted_per_source': {'arxiv': 2},
                'downloaded_per_source': {'arxiv': 1},
            }

    bot_module.ArxivBot = DummyBot

    monkeypatch.setitem(sys.modules, 'mathpdf.arxivbot.config', cfg_module)
    monkeypatch.setitem(sys.modules, 'mathpdf.arxivbot.main', bot_module)

    # Import and run CLI main with --discover --use-spec-pipeline
    import importlib
    app_main = importlib.import_module('mathpdf.main')

    output_json = tmp_path / "out.json"
    argv = [
        "--discover",
        "--use-spec-pipeline",
        "--json",
        "--output",
        str(output_json),
    ]

    # Run CLI
    app_main.main(argv)

    # Summary JSON persisted
    persisted = tmp_path / "last_pipeline_summary.json"
    assert persisted.exists()
    assert 'papers_harvested' in persisted.read_text(encoding='utf-8')

    # JSON output written to requested path
    assert output_json.exists()
    txt = output_json.read_text(encoding='utf-8')
    assert 'papers_downloaded' in txt
