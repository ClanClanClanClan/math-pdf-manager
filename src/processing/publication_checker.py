#!/usr/bin/env python3
"""Check if unpublished/working papers have been published.

Scans a directory of PDFs, parses filenames to extract titles and authors,
queries Crossref for DOI matches, and reports papers that appear to have
been published.

Usage::

    # Check unpublished papers
    python -m processing.publication_checker "02 - Unpublished papers/"

    # Check working papers
    python -m processing.publication_checker "03 - Working papers/"

    # Check the "not fully published" holding area
    python -m processing.publication_checker "04 - Papers to be downloaded/Not fully published version/"

    # Output JSON report
    python -m processing.publication_checker "02 - Unpublished papers/" --json --output report.json

    # Limit to 50 papers (for testing)
    python -m processing.publication_checker "02 - Unpublished papers/" --limit 50
"""
from __future__ import annotations
from processing.identity import iter_pdfs


import argparse
import hashlib
import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure src/ is on the path
# ---------------------------------------------------------------------------
# Filename parsing (reuse from extract_text if available, else inline)
# ---------------------------------------------------------------------------
def parse_paper_filename(pdf: Path) -> tuple[Optional[str], list[str]]:
    """Parse ``Author1, I. - Title.pdf`` → (title, [author_lastnames]).

    Returns ``(None, [])`` if the filename doesn't match the convention.
    """
    stem = unicodedata.normalize("NFC", pdf.stem)

    # Strip leading article numbers (Séminaire papers)
    stem = re.sub(r"^\d+\s*[-–]\s*", "", stem)

    if " - " not in stem:
        return None, []

    authors_part, title = stem.split(" - ", 1)
    title = title.strip()
    if not title or len(title) < 3:
        return None, []

    # Extract author lastnames from "Lastname, I., Lastname2, I." format
    # Split on commas, then group lastname + initials pairs
    parts = [p.strip() for p in authors_part.split(",") if p.strip()]
    lastnames = []
    for part in parts:
        # Skip initials (short parts with dots)
        if re.fullmatch(r"[A-ZÀ-ÖØ-Þ\u0100-\u024EŁ]{1,2}\.(?:[A-Z]\.)*", part):
            continue
        if re.fullmatch(r"[A-ZÀ-ÖØ-Þ\u0100-\u024EŁ]\.?\s*-\s*[A-Z]\.", part):
            continue
        if re.fullmatch(r"(?:Jr|Sr|II|III|IV)\.?", part, re.IGNORECASE):
            continue
        if len(part) <= 3 and "." in part:
            continue
        lastnames.append(part)

    return title, lastnames


# ---------------------------------------------------------------------------
# Crossref querying
# ---------------------------------------------------------------------------
class CrossrefChecker:
    """Query Crossref to check if a paper has been published."""

    API_URL = "https://api.crossref.org/works"
    RATE_LIMIT_SECS = 1.0  # Polite rate limit
    # Bump when the match dict schema changes so old entries get
    # re-queried instead of silently feeding auto-apply with stale
    # data.  v2 added ``author_count`` (Phase 3 auto-apply gate); any
    # cached entry without ``author_count`` is v1 and dropped on load.
    CACHE_VERSION = 2

    def __init__(self, *, cache_path: Optional[Path] = None):
        import requests

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "MathPDFManager/1.0 (mailto:admin@example.com)"}
        )
        self._last_request_time = 0.0
        self._cache: dict = {}
        self._cache_path = cache_path
        if cache_path and cache_path.exists():
            try:
                raw = json.loads(cache_path.read_text())
            except Exception:
                raw = {}
            # Schema v2 wraps the entries in
            # ``{"_version": 2, "entries": {...}}``.  v1 was a flat
            # ``{cache_key: result}`` mapping.  We accept both on load
            # but always WRITE v2; v1 entries that lack the auto-apply
            # gate (``match.author_count``) are dropped so the cache
            # doesn't poison the safety check.
            if isinstance(raw, dict) and raw.get("_version") == self.CACHE_VERSION:
                # Live-trial finding: a v2 cache can still contain
                # entries that pre-date later validation rules
                # (repository filter, author_count gate).  Re-validate
                # on every load so a cache written months ago doesn't
                # poison today's pipeline.
                raw_entries = raw.get("entries", {}) or {}
                kept = dropped = 0
                for k, v in raw_entries.items():
                    if v and "author_count" not in v:
                        dropped += 1
                        continue
                    if v and _is_repository_match(v):
                        # Convert repository hits to negative cache
                        # entries so we don't re-query Crossref for
                        # them every time -- they're known not to be
                        # real publications.
                        self._cache[k] = None
                        kept += 1
                        continue
                    self._cache[k] = v
                    kept += 1
                if dropped:
                    logger.info(
                        "Dropped %d stale v2 cache entries missing author_count "
                        "during load.", dropped,
                    )
            else:
                # v1 migration.  Cache stores match dicts directly
                # (NOT nested under a "match" key -- earlier
                # migration code wrongly assumed otherwise and
                # silently kept all entries).  Live-trial finding.
                migrated = 0
                dropped = 0
                for k, v in (raw or {}).items():
                    if k.startswith("_"):
                        continue
                    # v is either None (negative) or the match dict.
                    if v and "author_count" not in v:
                        dropped += 1
                        continue
                    if v and _is_repository_match(v):
                        # Repository hit -- neutralise so the next
                        # scan_directory doesn't surface it.
                        self._cache[k] = None
                        migrated += 1
                        continue
                    self._cache[k] = v
                    migrated += 1
                if dropped:
                    logger.info(
                        "Dropped %d cached results without author_count; "
                        "they will be re-queried.",
                        dropped,
                    )
                if migrated:
                    logger.info("Migrated %d cache entries to v%d", migrated, self.CACHE_VERSION)
            logger.info("Loaded %d cached results", len(self._cache))

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_SECS:
            time.sleep(self.RATE_LIMIT_SECS - elapsed)
        self._last_request_time = time.time()

    def _cache_key(self, title: str) -> str:
        normalized = re.sub(r"\s+", " ", title.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()

    def check_title(
        self, title: str, author_lastnames: list[str]
    ) -> Optional[dict]:
        """Query Crossref for a title match.

        Returns a dict with DOI, journal, year, matched_title, confidence
        if a match is found, or None otherwise.
        """
        cache_key = self._cache_key(title)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Live-trial finding: the repository filter only runs on
            # FRESH Crossref queries.  A cached SSRN / arXiv / HAL
            # match (e.g. from a session before the filter existed,
            # or one with stale schema) bypassed it forever.  Validate
            # cache hits on the way out so the filter is enforced
            # universally.  ``cached`` is either None (negative miss
            # we already chose to cache) or a match dict; only the
            # latter needs re-validation.
            if cached and _is_repository_match(cached):
                self._cache[cache_key] = None
                self._save_cache()
                return None
            # Audit-3's safe-upgrade gate needs ``author_count``.  An
            # old cached match that pre-dates that field would
            # silently fall back to author_count=1 and could trigger
            # a wrong auto-upgrade.  Invalidate and re-query.
            if cached and "author_count" not in cached:
                del self._cache[cache_key]
                self._save_cache()
                # Fall through to re-query Crossref below
            else:
                return cached

        self._rate_limit()

        # Clean title for query
        query_title = re.sub(r"[^\w\s]", " ", title)
        query_title = re.sub(r"\s+", " ", query_title).strip()

        # Audit-7 #2/#4: retriable errors (429 rate-limited, 5xx
        # server errors, timeouts) must NOT be cached as negative
        # results.  The earlier code returned None and then cached
        # ``self._cache[cache_key] = None`` below; if Crossref had a
        # bad five minutes during the weekly run, every paper queried
        # in that window got permanently marked "not published".
        # Now we differentiate: real "no items" (HTTP 200, empty
        # results) caches; transient errors propagate as None
        # WITHOUT touching the cache so the next run retries.
        retriable = False
        try:
            resp = self.session.get(
                self.API_URL,
                params={
                    "query.title": query_title,
                    "rows": 5,
                    "select": "DOI,title,author,container-title,published-print,published-online,type",
                },
                timeout=15,
            )
            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                wait_s = float(retry_after) if retry_after else 5.0
                logger.warning(
                    "Crossref returned %d for '%s'; backing off %.1fs and treating as retriable",
                    resp.status_code, title[:50], wait_s,
                )
                time.sleep(min(wait_s, 60.0))  # cap at 60s
                retriable = True
                return None
            resp.raise_for_status()
        except requests.exceptions.Timeout as exc:
            logger.warning("Crossref query timed out for '%s': %s", title[:50], exc)
            retriable = True
            return None
        except requests.exceptions.RequestException as exc:
            logger.warning("Crossref API request failed for '%s': %s", title[:50], exc)
            retriable = True
            return None
        except Exception as exc:
            logger.warning("Crossref query failed for '%s': %s", title[:50], exc)
            retriable = True
            return None
        finally:
            if retriable:
                # Make sure we DON'T poison the cache with a None for
                # this title -- the next scan should retry.
                self._cache.pop(cache_key, None)

        items = resp.json().get("message", {}).get("items", [])
        if not items:
            self._cache[cache_key] = None
            return None

        # Score each result
        best_match = None
        best_score = 0.0

        for item in items:
            cr_titles = item.get("title", [])
            if not cr_titles:
                continue
            cr_title = cr_titles[0]

            # Title similarity
            title_score = self._title_similarity(title, cr_title)

            # Author overlap
            cr_authors = item.get("author", [])
            cr_lastnames = [a.get("family", "") for a in cr_authors if a.get("family")]
            author_score = self._author_overlap(author_lastnames, cr_lastnames)

            # Combined score (title weighted more heavily)
            combined = 0.7 * title_score + 0.3 * author_score

            if combined > best_score:
                best_score = combined
                pub_date = item.get("published-print") or item.get("published-online")
                year = None
                if pub_date and pub_date.get("date-parts"):
                    parts = pub_date["date-parts"][0]
                    if parts:
                        year = parts[0]

                best_match = {
                    "doi": item.get("DOI"),
                    "matched_title": cr_title,
                    "journal": (item.get("container-title") or [""])[0],
                    "year": year,
                    "type": item.get("type", ""),
                    "title_score": round(title_score, 3),
                    "author_score": round(author_score, 3),
                    "confidence": round(combined, 3),
                    # Phase 3 auto-apply needs to know how many authors
                    # Crossref says the paper has, not just how many
                    # the filename happens to mention.  Saving the
                    # count keeps the safe-upgrade selector honest.
                    "author_count": len(cr_lastnames),
                }

        # Only accept high-confidence matches from real journals
        # (not repositories like SSRN, arXiv, HAL, NBER, etc.)
        if best_match and best_match["confidence"] >= 0.75:
            if _is_repository_match(best_match):
                logger.debug(
                    "Skipping repository match for '%s': %s (%s)",
                    title[:40], best_match.get("journal"), best_match.get("doi"),
                )
                self._cache[cache_key] = None
                self._save_cache()
                return None
            self._cache[cache_key] = best_match
            self._save_cache()
            return best_match

        self._cache[cache_key] = None
        self._save_cache()
        return None

    def _title_similarity(self, a: str, b: str) -> float:
        """Compute normalized title similarity (0-1)."""
        from rapidfuzz import fuzz

        # Normalize both titles
        a_norm = self._normalize_title(a)
        b_norm = self._normalize_title(b)
        return fuzz.ratio(a_norm, b_norm) / 100.0

    def _normalize_title(self, title: str) -> str:
        """Normalize a title for comparison."""
        t = unicodedata.normalize("NFC", title.lower())
        t = re.sub(r"[^\w\s]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _author_overlap(self, ours: list[str], theirs: list[str]) -> float:
        """Compute Jaccard similarity of author lastname sets."""
        if not ours or not theirs:
            return 0.5  # neutral when we can't compare

        ours_norm = {self._normalize_title(n) for n in ours}
        theirs_norm = {self._normalize_title(n) for n in theirs}

        intersection = len(ours_norm & theirs_norm)
        union = len(ours_norm | theirs_norm)
        return intersection / union if union > 0 else 0.0

    def _save_cache(self) -> None:
        if self._cache_path:
            try:
                self._cache_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "_version": self.CACHE_VERSION,
                    "entries": self._cache,
                }
                self._cache_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False)
                )
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Batch scanning
# ---------------------------------------------------------------------------
def scan_directory(
    directory: Path,
    *,
    checker: Optional[CrossrefChecker] = None,
    limit: Optional[int] = None,
    verbose: bool = False,
) -> list[dict]:
    """Scan a directory of PDFs and check which ones have been published.

    Returns a list of results, one per checked PDF.
    """
    if checker is None:
        cache_path = directory / ".publication_check_cache.json"
        checker = CrossrefChecker(cache_path=cache_path)

    pdfs = sorted(iter_pdfs(directory))
    if limit:
        pdfs = pdfs[:limit]

    results = []
    published_count = 0
    checked_count = 0

    for i, pdf in enumerate(pdfs):
        title, lastnames = parse_paper_filename(pdf)
        if not title:
            if verbose:
                print(f"  [{i + 1}/{len(pdfs)}] SKIP (can't parse): {pdf.name[:60]}")
            continue

        checked_count += 1
        match = checker.check_title(title, lastnames)

        entry = {
            "file": str(pdf),
            "filename": pdf.name,
            "parsed_title": title,
            "parsed_authors": lastnames,
        }

        if match:
            entry["published"] = True
            entry["match"] = match
            published_count += 1
            if verbose:
                conf = match["confidence"]
                journal = match.get("journal", "?")[:30]
                print(
                    f"  [{i + 1}/{len(pdfs)}] PUBLISHED ({conf:.0%}) "
                    f"→ {journal}: {pdf.name[:50]}"
                )
        else:
            entry["published"] = False
            if verbose and (i + 1) % 20 == 0:
                print(f"  [{i + 1}/{len(pdfs)}] checked {checked_count}, found {published_count} published...")

        results.append(entry)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check if unpublished/working papers have been published",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "02 - Unpublished papers/"
  %(prog)s "03 - Working papers/" --limit 50 -v
  %(prog)s "04 - Papers to be downloaded/Not fully published version/" --json
""",
    )
    parser.add_argument("directory", type=Path, help="Directory to scan")
    parser.add_argument("--limit", type=int, help="Max papers to check")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--output", type=Path, help="Write report to file")
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.75,
        help="Minimum confidence threshold (default: 0.75)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = build_parser()
    args = parser.parse_args(argv)

    directory = args.directory.resolve()
    if not directory.exists():
        print(f"Error: directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {directory}...")
    results = scan_directory(
        directory,
        limit=args.limit,
        verbose=args.verbose,
    )

    # Audit-7 #3: tell CI / scripts about empty scans rather than
    # silently exiting 0.  An empty results list could mean
    # "nothing to check" (legitimate, exit 0) or "scan failed
    # internally" (worth surfacing).  We distinguish by checking
    # whether the directory contains any PDFs at all.
    if not results:
        # Any PDFs in here?  If yes, the scanner skipped them all,
        # which is interesting; if no, an empty directory is fine.
        has_pdfs = next(iter_pdfs(directory), None) is not None
        if has_pdfs:
            print(
                "Warning: directory contains PDFs but scan returned 0 "
                "results.  Check that filenames match "
                "'Author, I. - Title.pdf' format.",
                file=sys.stderr,
            )
            sys.exit(2)

    published = [r for r in results if r.get("published")]
    not_published = [r for r in results if not r.get("published")]

    # Print summary
    if not args.json:
        print(f"\n{'=' * 60}")
        print(f"Checked: {len(results)} papers")
        print(f"Published: {len(published)}")
        print(f"Not published: {len(not_published)}")

        if published:
            print("\n--- Papers that appear to be published ---")
            for r in sorted(published, key=lambda x: -x["match"]["confidence"]):
                m = r["match"]
                print(f"\n  {r['filename'][:70]}")
                print(f"    DOI: {m.get('doi', '?')}")
                print(f"    Journal: {m.get('journal', '?')}")
                print(f"    Year: {m.get('year', '?')}")
                print(f"    Confidence: {m['confidence']:.0%}")
                if m.get("matched_title") != r["parsed_title"]:
                    print(f"    Crossref title: {m['matched_title'][:70]}")

    # JSON output
    report = {
        "directory": str(directory),
        "total_checked": len(results),
        "published_count": len(published),
        "not_published_count": len(not_published),
        "published": published,
    }

    if args.json:
        output = json.dumps(report, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(output)
            print(f"Report written to {args.output}")
        else:
            print(output)
    elif args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\nFull report written to {args.output}")


# ---------------------------------------------------------------------------
# ArXiv version checker
# ---------------------------------------------------------------------------
def check_arxiv_versions(
    directory: Path,
    *,
    limit: Optional[int] = None,
    verbose: bool = False,
) -> list[dict]:
    """Check for outdated ArXiv paper versions in the library.

    Scans filenames for arXiv IDs (e.g., ``2401.07160v1``), queries the
    ArXiv API for the latest version, and reports papers where the library
    has an older version.
    """
    import xml.etree.ElementTree as ET

    import requests

    results = []
    pdfs = sorted(iter_pdfs(directory))
    if limit:
        pdfs = pdfs[:limit]

    arxiv_pattern = re.compile(r"(\d{4}\.\d{4,5})(v(\d+))?")

    for pdf in pdfs:
        stem = unicodedata.normalize("NFC", pdf.stem)
        match = arxiv_pattern.search(stem)
        if not match:
            continue

        arxiv_id = match.group(1)
        local_version = int(match.group(3)) if match.group(3) else None

        # Query ArXiv API
        try:
            time.sleep(1.0)  # rate limit
            resp = requests.get(
                f"https://export.arxiv.org/api/query?id_list={arxiv_id}",
                timeout=10,
            )
            if resp.status_code != 200:
                continue

            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(resp.content)
            entry = root.find("atom:entry", ns)
            if entry is None:
                continue

            # Find latest version from the entry ID
            entry_id = entry.find("atom:id", ns)
            if entry_id is None:
                continue
            id_match = arxiv_pattern.search(entry_id.text or "")
            if not id_match:
                continue
            latest_version = int(id_match.group(3)) if id_match.group(3) else 1

            if local_version and latest_version > local_version:
                title_el = entry.find("atom:title", ns)
                title = (title_el.text or "").strip() if title_el else ""

                results.append({
                    "file": str(pdf),
                    "filename": pdf.name,
                    "arxiv_id": arxiv_id,
                    "local_version": local_version,
                    "latest_version": latest_version,
                    "title": re.sub(r"\s+", " ", title),
                })
                if verbose:
                    print(f"  OUTDATED: {arxiv_id} v{local_version} → v{latest_version}: {title[:50]}")

        except Exception as exc:
            logger.debug("ArXiv check failed for %s: %s", arxiv_id, exc)

    return results


# ---------------------------------------------------------------------------
# Repository detection — matches from these are NOT publications
# ---------------------------------------------------------------------------

_REPOSITORY_DOI_PREFIXES = (
    "10.2139/ssrn",       # SSRN
    "10.48550/arxiv",     # arXiv
    "10.5281/zenodo",     # Zenodo
    "10.3386/",           # NBER
    "10.1101/",           # bioRxiv / medRxiv
    "10.21203/",          # Research Square (preprints)
    "10.22541/",          # Authorea (preprints)
    "10.20944/",          # Preprints.org
)

_REPOSITORY_JOURNALS = (
    "ssrn electronic journal",
    "ssrn",
    "arxiv",
    "nber working paper",
    "zenodo",
    "biorxiv",
    "medrxiv",
    "hal",
    "working paper",
    "discussion paper",
    "preprint",
    "research square",
    "authorea",
)


def _is_repository_match(match: dict) -> bool:
    """Check if a Crossref match is from a repository, not a journal."""
    doi = (match.get("doi") or "").lower()
    journal = (match.get("journal") or "").lower()

    if any(doi.startswith(prefix) for prefix in _REPOSITORY_DOI_PREFIXES):
        return True
    if any(repo in journal for repo in _REPOSITORY_JOURNALS):
        return True
    return False


if __name__ == "__main__":
    main()
