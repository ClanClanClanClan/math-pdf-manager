#!/usr/bin/env python3
"""Unified DOI → PDF downloader with layered strategy chain.

Tries multiple sources in order to download a published paper:
1. Unpaywall (open access — free, fastest)
2. Publisher-specific downloader (19 registered publishers)
3. Direct DOI resolution (follow redirects)
4. Sci-Hub (pre-2021 papers, ~80% hit rate)
5. Cloudflare session (SIAM, Elsevier, etc.)
6. Browser session (reuse the user's authenticated Chrome cookies — recent
   paywalled papers across publishers; see downloader.browser_session)
7. Anna's Archive (needs DDoS-Guard cookies)
8. ETH Institutional auth (slowest — opens browser)

Usage::

    from downloader.doi_downloader import DOIDownloader

    dl = DOIDownloader(unpaywall_email="your@email.com")
    path = dl.download("10.1007/s00245-023-10001-5", Path("/tmp"))
    if path:
        print(f"Downloaded: {path}")

    # Or test from CLI:
    python -m downloader.doi_downloader 10.1007/s00245-023-10001-5
"""
from __future__ import annotations


import argparse
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNPAYWALL_EMAIL = os.environ.get("UNPAYWALL_EMAIL", "")

SCIHUB_MIRRORS = [
    "https://sci-hub.st",
    "https://sci-hub.ru",
    # sci-hub.se is dead (DNS resolution fails as of April 2026)
]

ANNAS_ARCHIVE_URL = "https://annas-archive.gl"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}


# ---------------------------------------------------------------------------
# PDF verification
# ---------------------------------------------------------------------------

# Smallest plausible real PDF; below this it's an error page / stub that
# happened to start with "%PDF" or a near-empty file.
_MIN_PDF_BYTES = 1024


def _is_valid_pdf(path: Path) -> bool:
    """Check if a file is a plausibly-complete PDF (magic bytes + size)."""
    try:
        if not path.exists() or path.stat().st_size < _MIN_PDF_BYTES:
            return False
        with open(path, "rb") as f:
            return f.read(4) == b"%PDF"
    except OSError:
        return False


def _download_to_file(url: str, path: Path, *, timeout: int = 30) -> bool:
    """Download a URL to a file. Returns True iff the result is a valid,
    complete-looking PDF.

    Robustness (Phase 1b): rejects a download that stalled mid-transfer —
    a valid ``%PDF`` header with a truncated body would otherwise be
    filed as the paper.  We compare the bytes written against the
    server-declared ``Content-Length`` and drop anything short.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        if resp.status_code != 200:
            return False

        try:
            declared = int(resp.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            declared = 0

        written = 0
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    written += len(chunk)

        if declared and written < declared:
            logger.debug("Truncated download %s (%d/%d bytes)", url, written, declared)
            path.unlink(missing_ok=True)
            return False
        if _is_valid_pdf(path):
            return True

        path.unlink(missing_ok=True)
        return False
    except Exception as exc:
        logger.debug("Download failed for %s: %s", url, exc)
        path.unlink(missing_ok=True)
        return False


# ---------------------------------------------------------------------------
# Strategy 1: Unpaywall (open access)
# ---------------------------------------------------------------------------

def try_unpaywall(doi: str, output_path: Path) -> bool:
    """Try Unpaywall API for open access PDF."""
    if not UNPAYWALL_EMAIL:
        logger.debug("Skipping Unpaywall (no UNPAYWALL_EMAIL set)")
        return False

    try:
        resp = requests.get(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": UNPAYWALL_EMAIL},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return False

        data = resp.json()
        if not data.get("is_oa"):
            return False

        # Find best PDF URL
        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or best.get("url")

        if not pdf_url:
            for loc in data.get("oa_locations", []):
                url = loc.get("url_for_pdf") or loc.get("url")
                if url:
                    pdf_url = url
                    break

        if not pdf_url:
            return False

        if _download_to_file(pdf_url, output_path):
            logger.info("Unpaywall: downloaded %s", doi)
            return True

        return False

    except Exception as exc:
        logger.debug("Unpaywall failed for %s: %s", doi, exc)
        return False


# ---------------------------------------------------------------------------
# Strategy 2: Direct DOI resolution
# ---------------------------------------------------------------------------

def try_direct_doi(doi: str, output_path: Path) -> bool:
    """Try following DOI redirect, requesting PDF content type."""
    try:
        resp = requests.get(
            f"https://doi.org/{doi}",
            headers={**HEADERS, "Accept": "application/pdf"},
            timeout=15,
            allow_redirects=True,
            stream=True,
        )

        if resp.status_code != 200:
            return False
        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower():
            return False

        # Same truncation guard as _download_to_file: a stalled transfer
        # leaves a valid %PDF header with a short body, which would pass the
        # magic-byte check and get filed as the paper.  Compare bytes written
        # against the server-declared Content-Length and drop anything short.
        try:
            declared = int(resp.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            declared = 0

        written = 0
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    written += len(chunk)

        if declared and written < declared:
            logger.debug("Truncated direct-DOI download %s (%d/%d bytes)",
                         doi, written, declared)
            output_path.unlink(missing_ok=True)
            return False

        if _is_valid_pdf(output_path):
            logger.info("Direct DOI: downloaded %s", doi)
            return True

        output_path.unlink(missing_ok=True)
        return False

    except Exception as exc:
        logger.debug("Direct DOI failed for %s: %s", doi, exc)
        output_path.unlink(missing_ok=True)
        return False


# ---------------------------------------------------------------------------
# Strategy 3: Sci-Hub (mirror rotation)
# ---------------------------------------------------------------------------

def try_scihub(doi: str, output_path: Path) -> bool:
    """Try Sci-Hub with mirror rotation."""
    for mirror in SCIHUB_MIRRORS:
        try:
            url = f"{mirror}/{doi}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            # Parse the page to find the PDF iframe/embed
            soup = BeautifulSoup(resp.text, "html.parser")

            pdf_url = None

            # Strategy 1: iframe with PDF src
            iframe = soup.find("iframe", src=True)
            if iframe:
                src = iframe["src"]
                if not src.startswith("http"):
                    src = "https:" + src if src.startswith("//") else mirror + src
                pdf_url = src

            # Strategy 2: embed element
            if not pdf_url:
                embed = soup.find("embed", {"type": "application/pdf"})
                if embed and embed.get("src"):
                    src = embed["src"]
                    if not src.startswith("http"):
                        src = "https:" + src if src.startswith("//") else mirror + src
                    pdf_url = src

            # Strategy 3: direct link with .pdf
            if not pdf_url:
                for a in soup.find_all("a", href=True):
                    if ".pdf" in a["href"].lower():
                        href = a["href"]
                        if not href.startswith("http"):
                            href = "https:" + href if href.startswith("//") else mirror + href
                        pdf_url = href
                        break

            # Strategy 4: button with onclick containing PDF URL
            if not pdf_url:
                for btn in soup.find_all("button", onclick=True):
                    onclick = btn["onclick"]
                    match = re.search(r"location\.href\s*=\s*['\"]([^'\"]*\.pdf[^'\"]*)['\"]", onclick)
                    if match:
                        pdf_url = match.group(1)
                        if not pdf_url.startswith("http"):
                            pdf_url = "https:" + pdf_url if pdf_url.startswith("//") else mirror + pdf_url
                        break

            if pdf_url and _download_to_file(pdf_url, output_path):
                logger.info("Sci-Hub (%s): downloaded %s", mirror, doi)
                return True

        except Exception as exc:
            logger.debug("Sci-Hub %s failed for %s: %s", mirror, doi, exc)
            continue

    return False


# ---------------------------------------------------------------------------
# Main DOI Downloader
# ---------------------------------------------------------------------------

class DOIDownloader:
    """Layered DOI → PDF downloader.

    Tries multiple strategies in order:
    1. Unpaywall (open access — free, fastest)
    2. Publisher-specific downloader (19 registered publishers)
    3. Direct DOI resolution (follow redirects)
    4. Sci-Hub (pre-2021 papers, ~80% hit rate)
    5. Cloudflare session (SIAM, Elsevier, etc. — needs CAPTCHA)
    6. Browser session (reuse the user's authenticated Chrome cookies)
    7. Anna's Archive (needs DDoS-Guard cookies)
    8. ETH Institutional auth (slowest — opens browser)
    """

    def __init__(
        self,
        *,
        unpaywall_email: str = "",
        rate_limit: float = 1.0,
    ):
        global UNPAYWALL_EMAIL
        if unpaywall_email:
            UNPAYWALL_EMAIL = unpaywall_email
        self.rate_limit = rate_limit

    @staticmethod
    def _safe_rename(source: Path, dest: Path) -> bool:
        """Safely rename a file, handling race conditions."""
        if not source or not source.exists():
            return False
        if source == dest:
            return True
        try:
            source.rename(dest)
            return True
        except FileExistsError:
            source.unlink(missing_ok=True)
            return True  # dest already has the file
        except Exception as exc:
            logger.warning("Could not rename %s → %s: %s", source, dest, exc)
            return False

    def _try_publisher(self, doi: str, output_path: Path) -> bool:
        """Try the registered publisher-specific downloader for this DOI.

        This uses the publisher registry (19 publishers) which knows the
        exact PDF URL pattern for each publisher, including fallback to
        Cloudflare cookies and ETH auth as needed.
        """
        try:
            from downloader.publishers import download_by_publisher
            result = download_by_publisher(doi, output_path.parent)
            if result:
                return self._safe_rename(result, output_path)
        except Exception as exc:
            logger.debug("Publisher downloader failed for %s: %s", doi, exc)
        return False

    def _try_cloudflare_session(self, doi: str, output_path: Path) -> bool:
        """Try downloading with saved Cloudflare session cookies."""
        try:
            from downloader.cloudflare_session import PUBLISHERS, download_with_cookies
            for pub_name, pub_info in PUBLISHERS.items():
                if pub_info["doi_prefix"] and doi.startswith(pub_info["doi_prefix"]):
                    result = download_with_cookies(pub_name, doi, output_path.parent)
                    if result:
                        return self._safe_rename(result, output_path)
                    break
        except Exception as exc:
            logger.debug("Cloudflare session failed for %s: %s", doi, exc)
        return False

    def _try_annas_archive_cookies(self, doi: str, output_path: Path) -> bool:
        """Try Anna's Archive with saved DDoS-Guard session cookies."""
        try:
            from downloader.cloudflare_session import download_annas_archive
            result = download_annas_archive(doi, output_path.parent)
            if result:
                return self._safe_rename(result, output_path)
        except Exception as exc:
            logger.debug("Anna's Archive (cookies) failed for %s: %s", doi, exc)
        return False

    def _try_browser_session(self, doi: str, output_path: Path) -> bool:
        """Reuse the user's authenticated browser cookies (publisher-agnostic).

        A fresh institutional SAML login can't entitle several publishers
        (proven against Springer); the entitlement lives in a persistent
        cookie the everyday browser already holds.  We borrow those cookies
        (imported via the cockpit) and download with them.  No-op when the
        user hasn't connected a browser session yet.
        """
        try:
            from downloader import browser_session as bs
            cookies = bs.cookies_for_download(allow_import=False)
            if not cookies:
                return False
            result = bs.download_with_session_cookies(doi, output_path.parent, cookies)
            if result:
                return self._safe_rename(result, output_path)
        except Exception as exc:
            logger.debug("Browser-session download failed for %s: %s", doi, exc)
        return False

    def _try_eth_institutional(self, doi: str, output_path: Path) -> bool:
        """Try ETH institutional download via Playwright.

        This is the SLOWEST strategy (opens a browser) so it's tried last.
        """
        try:
            from downloader.eth_institutional import download_sync
            result = download_sync(doi, output_path.parent)
            if result:
                return self._safe_rename(result, output_path)
        except Exception as exc:
            logger.debug("ETH institutional failed for %s: %s", doi, exc)
        return False

    def download(self, doi: str, output_dir: Path) -> Optional[Path]:
        """Try all strategies to download a PDF by DOI.

        Returns path to downloaded PDF, or None if all fail.
        Strategy order: fast/free first, slow/browser-based last.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        # Whitelist alphanumerics + a small set of safe punctuation.
        # DOIs are user-supplied strings and shouldn't be trusted to
        # only contain `/` `\` `:` -- semicolons, ampersands, pipes,
        # backticks, $() and quoted substrings are all valid Unicode
        # but produce confusing filenames and shell hazards if the
        # path is ever passed unquoted (it isn't today, but
        # defence-in-depth).  Collapses runs of unsafe chars to a
        # single underscore so the result stays readable.
        safe_doi = re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_") or "doi"
        output_path = output_dir / f"{safe_doi}.pdf"

        # Ordered: fast/free → publisher-specific → cached sessions → browser
        strategies = [
            ("Unpaywall", try_unpaywall),
            ("Publisher", self._try_publisher),
            ("Direct DOI", try_direct_doi),
            ("Sci-Hub", try_scihub),
            ("Cloudflare Session", self._try_cloudflare_session),
            ("Browser Session", self._try_browser_session),
            ("Anna's Archive", self._try_annas_archive_cookies),
            ("ETH Institutional", self._try_eth_institutional),
        ]

        attempts: list[str] = []
        for name, strategy_fn in strategies:
            # Jittered politeness delay: a fixed interval makes a batch hit
            # each host in lockstep; +/-30% jitter spreads the load and is
            # gentler on rate-limited mirrors (Sci-Hub etc.).
            time.sleep(self.rate_limit * random.uniform(0.7, 1.3))
            logger.debug("Trying %s for %s...", name, doi)
            try:
                if strategy_fn(doi, output_path):
                    logger.info("Downloaded %s via %s", doi, name)
                    return output_path
                attempts.append(f"{name}: no result")
            except Exception as exc:
                attempts.append(f"{name}: {type(exc).__name__}")
                logger.debug("%s error for %s: %s", name, doi, exc)

        # Structured failure summary instead of a bare "all failed", so a
        # user/log can see which strategy did what (paywall vs error vs
        # missing creds).
        logger.warning("All download strategies failed for %s — %s",
                       doi, "; ".join(attempts))
        return None

    def download_batch(
        self,
        dois: list[str],
        output_dir: Path,
        *,
        verbose: bool = False,
    ) -> dict[str, Optional[Path]]:
        """Download multiple papers. Returns {doi: path_or_None}."""
        results = {}
        for i, doi in enumerate(dois, 1):
            if verbose:
                print(f"  [{i}/{len(dois)}] {doi}...", end=" ", flush=True)
            path = self.download(doi, output_dir)
            results[doi] = path
            if verbose:
                print("OK" if path else "FAILED")
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download a PDF by DOI")
    parser.add_argument("doi", nargs="+", help="DOI(s) to download")
    parser.add_argument("--output", "-o", type=Path, default=Path("/tmp/doi_downloads"))
    parser.add_argument("--email", default=os.environ.get("UNPAYWALL_EMAIL", ""))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    dl = DOIDownloader(unpaywall_email=args.email)

    for doi in args.doi:
        print(f"Downloading {doi}...")
        path = dl.download(doi, args.output)
        if path:
            size_kb = path.stat().st_size // 1024
            print(f"  → {path} ({size_kb} KB)")
        else:
            print("  → FAILED (all strategies exhausted)")


if __name__ == "__main__":
    main()
