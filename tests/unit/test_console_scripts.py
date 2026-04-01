import importlib


def test_mathpdf_cli_imports():
    mod = importlib.import_module('mathpdf.main')
    assert hasattr(mod, 'main')


def test_mathpdf_harvest_cli_imports():
    mod = importlib.import_module('mathpdf.arxivbot.main')
    assert hasattr(mod, 'cli_main')

