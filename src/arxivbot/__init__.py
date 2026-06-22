"""Canonical metadata model.

The old arxivbot harvester/scorer/integration framework was retired in
the Phase-2 cleanup.  What remains live is the data model in
``arxivbot.models`` (``CMO``/``Author``) — the canonical-filename core
used by ``processing.ingest``.  Import it directly:
``from arxivbot.models.cmo import CMO, Author``.
"""
