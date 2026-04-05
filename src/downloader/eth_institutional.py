#!/usr/bin/env python3
"""ETH institutional PDF download via Playwright + Shibboleth.

Downloads paywalled papers using ETH Zurich institutional access.
Works headless. Tested on Springer Nature (April 2026).

The flow:
1. Visit article page
2. Click "log in via an institution"
3. Search "ETH Zurich" on the WAYF page
4. Fill ETH credentials on aai-logon.ethz.ch
5. Download PDF with institutional cookies

Usage::

    from downloader.eth_institutional import download_with_eth_auth

    path = await download_with_eth_auth(
        doi="10.1007/s00245-025-10368-x",
        output_dir=Path("/tmp"),
    )
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def _kill_overlays(page) -> None:
    """Force-remove ALL cookie banners, modals, overlays via JS."""
    await page.evaluate('''() => {
        document.querySelectorAll(
            '[data-cc-banner], .cc-banner, #onetrust-banner-sdk, ' +
            '.cookie-banner, .consent-banner, [class*="cookie"], ' +
            '[class*="consent"], dialog[open]'
        ).forEach(el => el.remove());
        document.querySelectorAll('.overlay, .modal-backdrop').forEach(el => el.remove());
    }''')
    await page.wait_for_timeout(500)


async def _eth_shibboleth_login(page, username: str, password: str) -> bool:
    """Fill and submit the ETH Shibboleth login form.

    Expects the page to be at aai-logon.ethz.ch.
    Returns True if login succeeded (page navigated away from login).
    """
    u_field = await page.query_selector(
        'input#username, input[name="j_username"]'
    )
    if not u_field:
        logger.warning("No username field found at %s", page.url[:60])
        return False

    await u_field.fill(username)

    p_field = await page.query_selector(
        'input#password, input[name="j_password"], input[type="password"]'
    )
    if p_field:
        await p_field.fill(password)

    submit = await page.query_selector(
        'button[type="submit"], input[type="submit"]'
    )
    if submit:
        await submit.click()
        await page.wait_for_timeout(8000)
        if "aai-logon.ethz.ch" not in page.url:
            logger.info("ETH login successful")
            return True
        else:
            logger.warning("Still on login page after submit — credentials may be wrong")
            return False

    logger.warning("No submit button found")
    return False


# ---------------------------------------------------------------------------
# Publisher-specific WAYF flows
# ---------------------------------------------------------------------------

async def _springer_wayf(page, doi: str) -> bool:
    """Navigate Springer Nature's WAYF to ETH login."""
    # Find institutional login link
    inst = await page.query_selector(
        'a:has-text("log in via an institution"), '
        'a:has-text("Log in via an institution")'
    )
    if not inst:
        logger.debug("No institutional login link on Springer page")
        return False

    href = await inst.get_attribute("href")
    if href and href.startswith("//"):
        href = "https:" + href

    await page.goto(href, wait_until="networkidle", timeout=20000)
    await page.wait_for_timeout(2000)
    await _kill_overlays(page)

    # Search for ETH
    search = await page.query_selector("#searchFormTextInput, input[name='search']")
    if not search:
        logger.debug("No WAYF search field found")
        return False

    await search.fill("ETH Zurich")
    await search.press("Enter")
    await page.wait_for_timeout(3000)
    await _kill_overlays(page)

    # Click ETH result
    eth = await page.query_selector(
        'a:has-text("ETH Zurich"), a:has-text("ETH Zürich")'
    )
    if eth:
        await eth.click()
        await page.wait_for_timeout(5000)
        return True

    logger.warning("ETH Zurich not found in WAYF results")
    return False


async def _euclid_wayf(page, doi: str) -> bool:
    """Navigate Project Euclid's institutional login."""
    inst = await page.query_selector(
        'a:has-text("Sign in with your institutional credentials")'
    )
    if not inst:
        return False

    await inst.click()
    await page.wait_for_timeout(5000)
    await _kill_overlays(page)

    # Euclid uses a different WAYF — look for institution search
    search = await page.query_selector(
        'input[type="search"], input[type="text"], #search'
    )
    if search:
        await search.fill("ETH Zurich")
        await page.wait_for_timeout(2000)
        eth = await page.query_selector('text="ETH Zurich"')
        if eth:
            await eth.click()
            await page.wait_for_timeout(5000)
            return True

    return False


async def _generic_wayf(page, doi: str) -> bool:
    """Generic Shibboleth WAYF flow — try common selectors."""
    # Look for any institutional access link
    for sel in [
        'a:has-text("institutional")',
        'a:has-text("Sign in via")',
        'a:has-text("Access through")',
        'a[href*="shibboleth"]',
        'a[href*="wayf"]',
        'a[href*="institutional"]',
    ]:
        try:
            link = await page.wait_for_selector(sel, timeout=2000)
            if link:
                await _kill_overlays(page)
                await link.click()
                await page.wait_for_timeout(5000)
                break
        except Exception:
            continue

    await _kill_overlays(page)

    # Look for institution search
    for sel in [
        '#searchFormTextInput',
        'input[type="search"]',
        'input[placeholder*="institution"]',
        'input[placeholder*="search"]',
        '#inst-search',
        '#search-input',
        'input[type="text"]',
    ]:
        try:
            search = await page.wait_for_selector(sel, timeout=2000)
            if search and await search.is_visible():
                await search.fill("ETH Zurich")
                await page.wait_for_timeout(1000)
                await search.press("Enter")
                await page.wait_for_timeout(3000)
                await _kill_overlays(page)

                eth = await page.query_selector(
                    'a:has-text("ETH Zurich"), a:has-text("ETH Zürich"), '
                    'li:has-text("ETH Zurich")'
                )
                if eth:
                    await eth.click()
                    await page.wait_for_timeout(5000)
                    return True
                break
        except Exception:
            continue

    # Check if we're already at ETH login
    if "aai-logon.ethz.ch" in page.url:
        return True

    return False


# ---------------------------------------------------------------------------
# Publisher PDF URL patterns
# ---------------------------------------------------------------------------

def _get_pdf_url(doi: str, publisher_domain: str) -> Optional[str]:
    """Return the direct PDF URL pattern for a given publisher."""
    patterns = {
        "link.springer.com": f"https://link.springer.com/content/pdf/{doi}.pdf",
        "epubs.siam.org": f"https://epubs.siam.org/doi/pdf/{doi}",
    }
    for domain, url in patterns.items():
        if domain in publisher_domain:
            return url
    return None


# ---------------------------------------------------------------------------
# Main download function
# ---------------------------------------------------------------------------

async def download_with_eth_auth(
    doi: str,
    output_dir: Path,
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
    headless: bool = True,
) -> Optional[Path]:
    """Download a paywalled paper via ETH institutional access.

    Parameters
    ----------
    doi : str
        The DOI of the paper.
    output_dir : Path
        Directory to save the downloaded PDF.
    username, password : str or None
        ETH credentials. If None, read from environment variables
        ETH_USERNAME and ETH_PASSWORD.
    headless : bool
        Run browser in headless mode (default True).

    Returns
    -------
    Path or None
        Path to downloaded PDF, or None if download failed.
    """
    username = username or os.environ.get("ETH_USERNAME", "")
    password = password or os.environ.get("ETH_PASSWORD", "")

    if not username or not password:
        logger.warning("ETH credentials not configured")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_doi = re.sub(r"[/\\:]", "_", doi)
    output_path = output_dir / f"{safe_doi}.pdf"

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed — can't use institutional access")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
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

            # Step 1: Visit article page
            logger.debug("Visiting https://doi.org/%s", doi)
            await page.goto(
                f"https://doi.org/{doi}",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            await page.wait_for_timeout(3000)
            await _kill_overlays(page)

            article_url = page.url
            title = await page.title()

            # Check for Cloudflare
            if "Just a moment" in title:
                logger.warning("Cloudflare challenge — cannot proceed headless")
                await browser.close()
                return None

            # Step 2: Navigate WAYF (publisher-specific)
            wayf_ok = False
            if "springer" in article_url or "nature.com" in article_url:
                wayf_ok = await _springer_wayf(page, doi)
            elif "projecteuclid" in article_url:
                wayf_ok = await _euclid_wayf(page, doi)
            else:
                wayf_ok = await _generic_wayf(page, doi)

            if not wayf_ok and "aai-logon.ethz.ch" not in page.url:
                logger.warning("Could not navigate to ETH login for %s", doi)
                await browser.close()
                return None

            # Step 3: ETH login
            if "aai-logon.ethz.ch" in page.url:
                login_ok = await _eth_shibboleth_login(page, username, password)
                if not login_ok:
                    await browser.close()
                    return None
            else:
                logger.debug("Not at ETH login page: %s", page.url[:60])

            # Step 4: Download PDF
            import requests

            # Try publisher-specific PDF URL
            pdf_url = _get_pdf_url(doi, article_url)
            if not pdf_url:
                # Fallback: look for PDF link on the page
                pdf_link = await page.query_selector(
                    'a.c-pdf-download__link, a:has-text("Download PDF"), '
                    'a[href*=".pdf"], a.btn-DownloadPaper'
                )
                if pdf_link:
                    href = await pdf_link.get_attribute("href")
                    if href:
                        from urllib.parse import urljoin
                        pdf_url = urljoin(page.url, href)

            if pdf_url:
                cookies = {c["name"]: c["value"] for c in await ctx.cookies()}
                resp = requests.get(
                    pdf_url,
                    cookies=cookies,
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if (
                    resp.headers.get("content-type", "").startswith("application/pdf")
                    and len(resp.content) > 1000
                ):
                    output_path.write_bytes(resp.content)
                    logger.info(
                        "ETH auth: downloaded %s (%d KB)",
                        doi,
                        len(resp.content) // 1024,
                    )
                    await browser.close()
                    return output_path

            logger.warning("Could not download PDF for %s after ETH auth", doi)
            await browser.close()
            return None

    except Exception as exc:
        logger.error("ETH download failed for %s: %s", doi, exc)
        return None


def download_sync(doi: str, output_dir: Path, **kwargs) -> Optional[Path]:
    """Synchronous wrapper for download_with_eth_auth."""
    return asyncio.run(download_with_eth_auth(doi, output_dir, **kwargs))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m downloader.eth_institutional <DOI>")
        sys.exit(1)

    doi = sys.argv[1]
    output = Path("/tmp/eth_download")
    result = download_sync(doi, output)
    if result:
        print(f"✅ Downloaded: {result} ({result.stat().st_size // 1024} KB)")
    else:
        print("❌ Failed")
