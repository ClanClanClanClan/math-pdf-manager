#!/usr/bin/env python3
"""Semi-automated Cloudflare bypass for publisher downloads.

For publishers behind Cloudflare Turnstile (SIAM, Elsevier, Wiley,
Taylor & Francis), this tool:

1. Opens the publisher in the user's real Chrome browser
2. User solves the CAPTCHA once (single click)
3. Extracts Cloudflare cookies from Chrome
4. Downloads PDFs batch using those cookies + ETH institutional auth

The cookies typically last 30-60 minutes, enough for hundreds of
downloads from the same publisher.

Usage::

    # Step 1: Start a session for SIAM
    python -m downloader.cloudflare_session start siam

    # Step 2: (User solves CAPTCHA in Chrome)

    # Step 3: Extract cookies and download
    python -m downloader.cloudflare_session download siam 10.1137/23m1622660

    # Or batch download from a report
    python -m downloader.cloudflare_session batch siam report.json --limit 50
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

COOKIE_DIR = Path.home() / ".mathpdf" / "cookies"

# Publisher domains and their institutional login patterns
PUBLISHERS = {
    "siam": {
        "domain": "epubs.siam.org",
        "test_url": "https://epubs.siam.org/",
        "pdf_pattern": "https://epubs.siam.org/doi/pdf/{doi}",
        "doi_prefix": "10.1137",
        "wayf_selector": 'a:has-text("Institutional")',
    },
    "elsevier": {
        "domain": "www.sciencedirect.com",
        "test_url": "https://www.sciencedirect.com/",
        "pdf_pattern": None,  # Elsevier uses PII-based URLs, need to extract from page
        "doi_prefix": "10.1016",
        "wayf_selector": 'a#els-footer-remote-access',
    },
    "wiley": {
        "domain": "onlinelibrary.wiley.com",
        "test_url": "https://onlinelibrary.wiley.com/",
        "pdf_pattern": "https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}",
        "doi_prefix": "10.1111",
        "wayf_selector": 'a:has-text("Institutional")',
    },
    "taylor_francis": {
        "domain": "www.tandfonline.com",
        "test_url": "https://www.tandfonline.com/",
        "pdf_pattern": "https://www.tandfonline.com/doi/pdf/{doi}",
        "doi_prefix": "10.1080",
        "wayf_selector": 'a:has-text("Institutional")',
    },
}


def _is_valid_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 100:
        return False
    with open(path, "rb") as f:
        return f.read(4) == b"%PDF"


# ---------------------------------------------------------------------------
# Cookie management
# ---------------------------------------------------------------------------

def save_cookies(publisher: str, cookies: List[Dict]) -> Path:
    """Save cookies for a publisher."""
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    path = COOKIE_DIR / f"{publisher}.json"
    path.write_text(json.dumps(cookies, indent=2))
    logger.info("Saved %d cookies for %s", len(cookies), publisher)
    return path


def load_cookies(publisher: str) -> Optional[List[Dict]]:
    """Load saved cookies for a publisher."""
    path = COOKIE_DIR / f"{publisher}.json"
    if not path.exists():
        return None

    # Check age — cookies expire after ~1 hour
    age_seconds = time.time() - path.stat().st_mtime
    if age_seconds > 3600:
        logger.warning("Cookies for %s are %d minutes old — may be expired", publisher, age_seconds // 60)

    cookies = json.loads(path.read_text())
    return cookies


def cookies_to_session(cookies: List[Dict]) -> requests.Session:
    """Create a requests Session with cookies."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })
    for c in cookies:
        session.cookies.set(
            c["name"], c["value"],
            domain=c.get("domain", ""),
            path=c.get("path", "/"),
        )
    return session


# ---------------------------------------------------------------------------
# Start session (open Chrome for user to solve CAPTCHA)
# ---------------------------------------------------------------------------

async def start_session(publisher: str) -> None:
    """Open the publisher in the user's Chrome for CAPTCHA solving.

    After the user solves the CAPTCHA, call extract_cookies().
    """
    pub = PUBLISHERS.get(publisher)
    if not pub:
        print(f"Unknown publisher: {publisher}")
        print(f"Available: {', '.join(PUBLISHERS.keys())}")
        return

    from playwright.async_api import async_playwright

    print(f"\nOpening {pub['domain']} in a browser window...")
    print("Please solve the Cloudflare CAPTCHA when it appears.")
    print("Then press Enter here to continue.\n")

    async with async_playwright() as p:
        # Use headed mode so user can interact
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = await ctx.new_page()

        # Remove automation markers
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        await page.goto(pub["test_url"], wait_until="domcontentloaded", timeout=30000)

        # Wait for user to solve CAPTCHA
        input(">>> Press Enter after solving the CAPTCHA... ")

        # Check if we passed Cloudflare
        title = await page.title()
        if "Just a moment" in title:
            print("⚠ Still on Cloudflare page. Try again or wait longer.")
            input(">>> Press Enter to try extracting cookies anyway... ")

        # Extract cookies
        cookies = await ctx.cookies()
        save_cookies(publisher, cookies)

        print(f"\n✅ Saved {len(cookies)} cookies for {publisher}")
        print(f"Cookies valid for ~60 minutes.")
        print(f"\nNow you can run:")
        print(f"  python -m downloader.cloudflare_session download {publisher} <DOI>")
        print(f"  python -m downloader.cloudflare_session batch {publisher} report.json")

        # Now try ETH institutional login while we have the session
        username = os.environ.get("ETH_USERNAME", "")
        password = os.environ.get("ETH_PASSWORD", "")

        if username and password:
            print(f"\nAttempting ETH institutional login...")
            try:
                from downloader.eth_institutional import _kill_overlays, _generic_wayf, _eth_shibboleth_login

                await _kill_overlays(page)

                # Try navigating to a sample article to trigger institutional login
                sample_doi = f"{pub['doi_prefix']}/sample"
                # Just check if we can access the site now
                title = await page.title()
                print(f"  Page title: {title[:50]}")

                # Try WAYF
                wayf_ok = await _generic_wayf(page, "")
                if wayf_ok or "aai-logon.ethz.ch" in page.url:
                    login_ok = await _eth_shibboleth_login(page, username, password)
                    if login_ok:
                        # Re-extract cookies (now with institutional auth)
                        cookies = await ctx.cookies()
                        save_cookies(publisher, cookies)
                        print(f"✅ ETH login successful! Updated cookies.")
                else:
                    print("  Could not find institutional login — using Cloudflare cookies only")
            except Exception as e:
                print(f"  ETH login skipped: {e}")

        await browser.close()


# ---------------------------------------------------------------------------
# Download with saved cookies
# ---------------------------------------------------------------------------

def download_with_cookies(
    publisher: str,
    doi: str,
    output_dir: Path,
) -> Optional[Path]:
    """Download a PDF using saved Cloudflare cookies."""
    pub = PUBLISHERS.get(publisher)
    if not pub:
        logger.warning("Unknown publisher: %s", publisher)
        return None

    cookies = load_cookies(publisher)
    if not cookies:
        logger.warning("No cookies for %s — run 'start' first", publisher)
        return None

    session = cookies_to_session(cookies)

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_doi = re.sub(r"[/\\:]", "_", doi)
    output_path = output_dir / f"{safe_doi}.pdf"

    # Try publisher-specific PDF pattern
    if pub["pdf_pattern"]:
        pdf_url = pub["pdf_pattern"].format(doi=doi)
        logger.debug("Trying %s", pdf_url[:60])

        resp = session.get(pdf_url, timeout=30, allow_redirects=True)
        ct = resp.headers.get("content-type", "")

        if ct.startswith("application/pdf") and len(resp.content) > 1000:
            output_path.write_bytes(resp.content)
            if _is_valid_pdf(output_path):
                logger.info("Downloaded %s (%d KB)", doi, len(resp.content) // 1024)
                return output_path
            output_path.unlink(missing_ok=True)

    # Try DOI redirect
    doi_url = f"https://doi.org/{doi}"
    resp = session.get(doi_url, timeout=30, allow_redirects=True)
    final_url = resp.url

    # Look for PDF link in the HTML
    if "html" in resp.headers.get("content-type", "").lower():
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        for sel in ["a[href*='.pdf']", "a.c-pdf-download__link", "a:contains('PDF')"]:
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                text = a.get_text(strip=True).lower()
                if ".pdf" in href or "pdf" in text:
                    if not href.startswith("http"):
                        from urllib.parse import urljoin
                        href = urljoin(final_url, href)

                    resp2 = session.get(href, timeout=30)
                    if resp2.headers.get("content-type", "").startswith("application/pdf"):
                        output_path.write_bytes(resp2.content)
                        if _is_valid_pdf(output_path):
                            return output_path
                        output_path.unlink(missing_ok=True)
                    break

    return None


def batch_download(
    publisher: str,
    report_path: Path,
    output_dir: Path,
    *,
    limit: Optional[int] = None,
    min_confidence: float = 0.85,
) -> dict:
    """Batch download papers from a publication checker report."""
    pub = PUBLISHERS.get(publisher)
    if not pub:
        print(f"Unknown publisher: {publisher}")
        return {"downloaded": 0, "failed": 0}

    report = json.loads(report_path.read_text())
    candidates = [
        p for p in report.get("published", [])
        if p.get("match", {}).get("doi", "").startswith(pub["doi_prefix"])
        and p.get("match", {}).get("confidence", 0) >= min_confidence
    ]

    if limit:
        candidates = candidates[:limit]

    print(f"\nBatch download: {len(candidates)} {publisher} papers")

    downloaded = 0
    failed = 0

    for i, entry in enumerate(candidates, 1):
        doi = entry["match"]["doi"]
        print(f"  [{i}/{len(candidates)}] {doi[:35]}...", end=" ", flush=True)

        time.sleep(1.0)  # rate limit
        path = download_with_cookies(publisher, doi, output_dir)

        if path:
            print(f"OK ({path.stat().st_size // 1024} KB)")
            downloaded += 1
        else:
            print("FAILED")
            failed += 1

    return {"downloaded": downloaded, "failed": failed, "total": len(candidates)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Semi-automated Cloudflare bypass for publisher downloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Publishers: siam, elsevier, wiley, taylor_francis

Workflow:
  1. Start a session (opens Chrome, you solve the CAPTCHA):
     python -m downloader.cloudflare_session start siam

  2. Download papers using the session cookies:
     python -m downloader.cloudflare_session download siam 10.1137/23m1622660
     python -m downloader.cloudflare_session batch siam report.json --limit 50
""",
    )
    sub = parser.add_subparsers(dest="command")

    # start
    start_p = sub.add_parser("start", help="Open browser for CAPTCHA solving")
    start_p.add_argument("publisher", choices=PUBLISHERS.keys())

    # download
    dl_p = sub.add_parser("download", help="Download a single paper")
    dl_p.add_argument("publisher", choices=PUBLISHERS.keys())
    dl_p.add_argument("doi", help="DOI to download")
    dl_p.add_argument("--output", "-o", type=Path, default=Path("/tmp/cf_downloads"))

    # batch
    batch_p = sub.add_parser("batch", help="Batch download from report")
    batch_p.add_argument("publisher", choices=PUBLISHERS.keys())
    batch_p.add_argument("report", type=Path, help="JSON report from publication_checker")
    batch_p.add_argument("--output", "-o", type=Path, default=Path("/tmp/cf_downloads"))
    batch_p.add_argument("--limit", type=int)
    batch_p.add_argument("--min-confidence", type=float, default=0.85)

    # status
    sub.add_parser("status", help="Check cookie status for all publishers")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.command == "start":
        asyncio.run(start_session(args.publisher))

    elif args.command == "download":
        path = download_with_cookies(args.publisher, args.doi, args.output)
        if path:
            print(f"✅ Downloaded: {path} ({path.stat().st_size // 1024} KB)")
        else:
            print("❌ Download failed")

    elif args.command == "batch":
        result = batch_download(
            args.publisher, args.report, args.output,
            limit=args.limit,
            min_confidence=args.min_confidence,
        )
        print(f"\nResults: {result['downloaded']} downloaded, {result['failed']} failed")

    elif args.command == "status":
        print("Cookie status:")
        for name in PUBLISHERS:
            cookie_path = COOKIE_DIR / f"{name}.json"
            if cookie_path.exists():
                age = (time.time() - cookie_path.stat().st_mtime) / 60
                cookies = json.loads(cookie_path.read_text())
                status = "⚠ expired" if age > 60 else "✅ fresh"
                print(f"  {name:15s} {status} ({len(cookies)} cookies, {age:.0f} min old)")
            else:
                print(f"  {name:15s} ❌ no cookies")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
