"""PDF metadata extraction.

The legacy multi-engine parser stack (models/constants/parsers/extractors/
enhanced_parser/facade) was retired in the Phase-2 cleanup — the live
pipeline extracts metadata in ``processing.ingest`` and falls back to the
local-LLM extractor here.  Only ``llm_extractor`` remains.
"""
