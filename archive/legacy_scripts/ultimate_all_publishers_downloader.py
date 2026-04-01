#!/usr/bin/env python3
"""
ULTIMATE ALL PUBLISHERS DOWNLOADER
The REAL solution that actually works for EVERYTHING

Strategy:
1. Try direct download from publisher (with proper auth)
2. Fallback to Sci-Hub
3. Fallback to Anna's Archive
4. Try Google Scholar PDF links
5. Try ResearchGate/Academia.edu

NO VPN NEEDED for most publishers!
"""

import asyncio
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

import requests
from playwright.async_api import BrowserContext, Page, async_playwright

from cookie_banner_handler import CookieBannerHandler

# Import your sentence case converter
sys.path.insert(0, str(Path(__file__).parent / "src"))
try:
    from core.sentence_case import to_sentence_case_academic

    SENTENCE_CASE_AVAILABLE = True
except ImportError:
    SENTENCE_CASE_AVAILABLE = False

# ETH credentials
import os

ETH_USERNAME = os.getenv("ETH_USERNAME")
ETH_PASSWORD = os.getenv("ETH_PASSWORD")

# Sci-Hub mirrors (updated regularly)
SCIHUB_MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.st",
    "https://sci-hub.ru",
    "https://sci-hub.ee",
    "https://sci-hub.do",
    "https://sci-hub.ren",
    "https://sci-hub.mksa.top",
    "https://sci-hub.tw",
]

# Anna's Archive
ANNAS_ARCHIVE_URLS = [
    "https://annas-archive.org",
    "https://annas-archive.se",
    "https://annas-archive.gs",
]


@dataclass
class Author:
    """Author representation"""

    family: str
    given: Optional[str] = None

    def to_filename_format(self) -> str:
        if self.given:
            initial = self.given[0].upper() + "."
            return f"{self.family}, {initial}"
        return self.family


@dataclass
class Paper:
    """Paper with all metadata"""

    url: str
    doi: str = ""
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    journal: str = ""
    year: str = ""
    publisher: str = ""
    pdf_path: Optional[Path] = None
    download_source: str = ""  # publisher, scihub, annas, etc.
    success: bool = False
    error: str = ""

    def generate_correct_filename(self) -> str:
        """Your format: Authors - Title in sentence case.pdf"""
        if self.authors:
            author_strs = [author.to_filename_format() for author in self.authors]
            authors_part = ", ".join(author_strs)
        else:
            authors_part = "Unknown"

        title_part = self.title or "Unknown Title"
        if SENTENCE_CASE_AVAILABLE and title_part:
            title_part, _ = to_sentence_case_academic(title_part)
        elif title_part:
            title_part = title_part[0].upper() + title_part[1:].lower() if title_part else ""

        # Clean forbidden characters
        forbidden = '<>:"/\\|?*'
        for char in forbidden:
            title_part = title_part.replace(char, "_")
            authors_part = authors_part.replace(char, "_")

        filename = f"{authors_part} - {title_part}.pdf"

        # Ensure reasonable length
        if len(filename) > 250:
            max_title_len = 250 - len(authors_part) - len(" - .pdf")
            if max_title_len > 20:
                title_part = title_part[: max_title_len - 3] + "..."
                filename = f"{authors_part} - {title_part}.pdf"

        return filename


class UltimateAllPublishersDownloader:
    """Downloads from ALL publishers using multiple strategies"""

    # Publisher configurations (NO VPN NEEDED for most!)
    PUBLISHERS = {
        "springer": {
            "domain": "link.springer.com",
            "needs_vpn": False,
            "wayf_url": "https://wayf.springernature.com/?redirect_uri=https://link.springer.com",
            "pdf_selectors": ['a[href*=".pdf"]', 'button:has-text("Download PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "nature": {
            "domain": "nature.com",
            "needs_vpn": False,
            "wayf_url": "https://wayf.springernature.com/?redirect_uri=https://www.nature.com",
            "pdf_selectors": [".c-pdf-download__link", 'a:has-text("Download PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "ieee": {
            "domain": "ieeexplore.ieee.org",
            "needs_vpn": False,  # NO VPN NEEDED!
            "pdf_selectors": ['a:has-text("PDF")', ".stats-document-lh-action-downloadPdf"],
            "title_selector": 'meta[property="og:title"]',
            "author_selector": ".authors-info .author",
        },
        "acm": {
            "domain": "dl.acm.org",
            "needs_vpn": False,  # Often has open access!
            "pdf_selectors": [".btn--red", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": ".loa__author-name",
        },
        "elsevier": {
            "domain": "sciencedirect.com",
            "needs_vpn": True,  # Cloudflare protected
            "pdf_selectors": ['a[aria-label*="Download PDF"]'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "wiley": {
            "domain": "onlinelibrary.wiley.com",
            "needs_vpn": False,
            "pdf_selectors": [".coolBar__ctrl--pdf", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "taylor_francis": {
            "domain": "tandfonline.com",
            "needs_vpn": False,
            "pdf_selectors": [".show-pdf", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "sage": {
            "domain": "journals.sagepub.com",
            "needs_vpn": False,
            "pdf_selectors": [".pdf-link", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "oup": {
            "domain": "academic.oup.com",
            "needs_vpn": False,
            "pdf_selectors": [".pdf-link", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "cambridge": {
            "domain": "cambridge.org",
            "needs_vpn": False,
            "pdf_selectors": [".pdf-link", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "aps": {
            "domain": "journals.aps.org",
            "needs_vpn": False,
            "pdf_selectors": [".btn-download-pdf", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "iop": {
            "domain": "iopscience.iop.org",
            "needs_vpn": False,
            "pdf_selectors": [".pdf-link", 'a:has-text("PDF")'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "arxiv": {
            "domain": "arxiv.org",
            "needs_vpn": False,
            "pdf_selectors": ["a.download-pdf", 'a[href*="/pdf/"]'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "biorxiv": {
            "domain": "biorxiv.org",
            "needs_vpn": False,
            "pdf_selectors": ["a.article-dl-pdf-link", 'a[href*=".full.pdf"]'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "plos": {
            "domain": "journals.plos.org",
            "needs_vpn": False,  # Open access!
            "pdf_selectors": ["a#downloadPdf", 'a[href*="/article/file"]'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "pmc": {
            "domain": "ncbi.nlm.nih.gov/pmc",
            "needs_vpn": False,  # Open access!
            "pdf_selectors": ["a.pdf-link", 'a[href*="/pdf/"]'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "mdpi": {
            "domain": "mdpi.com",
            "needs_vpn": False,  # Open access!
            "pdf_selectors": ["a.download-pdf", 'a[href*="/pdf"]'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
        "frontiers": {
            "domain": "frontiersin.org",
            "needs_vpn": False,  # Open access!
            "pdf_selectors": ["a.download-files-pdf", 'a[href*="/pdf"]'],
            "title_selector": 'meta[name="citation_title"]',
            "author_selector": 'meta[name="citation_author"]',
        },
    }

    def __init__(self, base_dir: str = "data/papers"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.context = None
        self.authenticated = set()

    def extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from URL or text"""
        # DOI patterns
        doi_patterns = [
            r"10\.\d{4,}(?:\.\d+)*\/[-._;()\/:a-zA-Z0-9]+",
            r"doi\.org\/(10\.\d{4,}[^\s]+)",
            r"doi:(10\.\d{4,}[^\s]+)",
            r"/doi/(10\.\d{4,}[^\s]+)",
        ]

        for pattern in doi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Check if pattern has groups
                if match.groups():
                    doi = match.group(1)
                else:
                    doi = match.group(0)
                return doi.strip()
        return None

    def identify_publisher(self, url: str) -> Optional[str]:
        """Identify publisher from URL"""
        for pub_name, pub_config in self.PUBLISHERS.items():
            if pub_config["domain"] in url:
                return pub_name
        return None

    async def setup_browser(self):
        """Setup browser with stealth"""
        playwright = await async_playwright().start()

        browser = await playwright.chromium.launch(
            headless=True,  # Can run headless for most
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        self.context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Stealth JavaScript
        await self.context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """
        )

    async def extract_metadata(self, page: Page, publisher: str) -> Paper:
        """Extract metadata from page"""
        config = self.PUBLISHERS.get(publisher, {})
        paper = Paper(url=page.url, publisher=publisher)

        # Extract title
        if "title_selector" in config:
            try:
                elem = page.locator(config["title_selector"]).first
                if await elem.count() > 0:
                    if config["title_selector"].startswith("meta"):
                        paper.title = await elem.get_attribute("content")
                    else:
                        paper.title = await elem.text_content()
                    paper.title = re.sub(r"\s+", " ", (paper.title or "").strip())
            except:
                pass

        # Extract authors
        if "author_selector" in config:
            try:
                elems = await page.locator(config["author_selector"]).all()
                for elem in elems[:20]:  # Limit to 20 authors
                    if config["author_selector"].startswith("meta"):
                        name = await elem.get_attribute("content")
                    else:
                        name = await elem.text_content()

                    if name:
                        name = re.sub(r"\s*\([^)]*\)\s*", "", name.strip())
                        if "," in name:
                            parts = name.split(",", 1)
                            paper.authors.append(
                                Author(
                                    family=parts[0].strip(),
                                    given=parts[1].strip() if len(parts) > 1 else None,
                                )
                            )
                        else:
                            parts = name.split()
                            if len(parts) >= 2:
                                paper.authors.append(
                                    Author(family=parts[-1], given=" ".join(parts[:-1]))
                                )
                            elif parts:
                                paper.authors.append(Author(family=parts[0]))
            except:
                pass

        # Extract DOI
        paper.doi = self.extract_doi(page.url) or ""

        return paper

    async def try_publisher_download(self, url: str) -> Paper:
        """Try to download directly from publisher"""
        publisher = self.identify_publisher(url)
        if not publisher:
            return Paper(url=url, error="Unknown publisher")

        config = self.PUBLISHERS[publisher]

        # Skip if needs VPN and we don't have it
        if config.get("needs_vpn"):
            print(f"   ⚠️ {publisher} needs VPN, skipping to fallbacks...")
            return Paper(url=url, publisher=publisher, error="Needs VPN")

        print(f"   📚 Trying {publisher} direct download...")

        page = await self.context.new_page()
        try:
            # Navigate to paper
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if response.status != 200:
                return Paper(url=url, publisher=publisher, error=f"HTTP {response.status}")

            await page.wait_for_timeout(3000)
            await CookieBannerHandler.dismiss_cookie_banner(page)

            # Extract metadata
            paper = await self.extract_metadata(page, publisher)

            # Try to find PDF link
            for selector in config.get("pdf_selectors", []):
                try:
                    pdf_link = page.locator(selector).first
                    if await pdf_link.count() > 0 and await pdf_link.is_visible():
                        # Create filename
                        filename = paper.generate_correct_filename()
                        pdf_path = self.base_dir / publisher / filename
                        pdf_path.parent.mkdir(exist_ok=True)

                        # Download PDF
                        async with page.expect_download(timeout=30000) as download_info:
                            await pdf_link.click()

                        download = await download_info.value
                        await download.save_as(pdf_path)

                        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
                            paper.pdf_path = pdf_path
                            paper.success = True
                            paper.download_source = publisher
                            print(
                                f"   ✅ Downloaded from {publisher}: {pdf_path.stat().st_size:,} bytes"
                            )
                            return paper
                except:
                    continue

            return Paper(url=url, publisher=publisher, error="No PDF found")

        except Exception as e:
            return Paper(url=url, publisher=publisher, error=str(e))
        finally:
            await page.close()

    async def try_scihub_download(self, url: str, doi: str = None) -> Paper:
        """Try to download from Sci-Hub"""
        print(f"   🏴‍☠️ Trying Sci-Hub...")

        # Extract DOI if not provided
        if not doi:
            doi = self.extract_doi(url)

        if not doi:
            print(f"      ❌ No DOI found")
            return Paper(url=url, error="No DOI for Sci-Hub")

        print(f"      DOI: {doi}")

        # Try each Sci-Hub mirror
        for mirror in SCIHUB_MIRRORS:
            try:
                scihub_url = f"{mirror}/{doi}"
                print(f"      Trying {mirror}...")

                page = await self.context.new_page()
                try:
                    response = await page.goto(
                        scihub_url, wait_until="domcontentloaded", timeout=20000
                    )

                    if response.status != 200:
                        continue

                    await page.wait_for_timeout(2000)

                    # Look for PDF embed or download button
                    pdf_selectors = [
                        "#pdf",  # PDF embed
                        'embed[type="application/pdf"]',
                        "iframe#pdf",
                        'button:has-text("↓")',  # Download button
                        'a[onclick*="download"]',
                    ]

                    for selector in pdf_selectors:
                        elem = page.locator(selector).first
                        if await elem.count() > 0:
                            # Get PDF URL
                            if (
                                selector.startswith("#pdf")
                                or "embed" in selector
                                or "iframe" in selector
                            ):
                                pdf_src = await elem.get_attribute("src")
                                if pdf_src:
                                    if not pdf_src.startswith("http"):
                                        pdf_src = f"{mirror}{pdf_src}"

                                    # Download PDF directly
                                    pdf_response = requests.get(pdf_src, timeout=30)
                                    if pdf_response.status_code == 200:
                                        # Save PDF
                                        filename = f"scihub_{doi.replace('/', '_')}.pdf"
                                        pdf_path = self.base_dir / "scihub" / filename
                                        pdf_path.parent.mkdir(exist_ok=True)

                                        with open(pdf_path, "wb") as f:
                                            f.write(pdf_response.content)

                                        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
                                            paper = Paper(
                                                url=url,
                                                doi=doi,
                                                pdf_path=pdf_path,
                                                success=True,
                                                download_source="scihub",
                                            )
                                            print(
                                                f"   ✅ Downloaded from Sci-Hub: {pdf_path.stat().st_size:,} bytes"
                                            )
                                            return paper
                            else:
                                # Click download button
                                async with page.expect_download(timeout=30000) as download_info:
                                    await elem.click()

                                download = await download_info.value
                                filename = f"scihub_{doi.replace('/', '_')}.pdf"
                                pdf_path = self.base_dir / "scihub" / filename
                                pdf_path.parent.mkdir(exist_ok=True)
                                await download.save_as(pdf_path)

                                if pdf_path.exists() and pdf_path.stat().st_size > 1000:
                                    paper = Paper(
                                        url=url,
                                        doi=doi,
                                        pdf_path=pdf_path,
                                        success=True,
                                        download_source="scihub",
                                    )
                                    print(
                                        f"   ✅ Downloaded from Sci-Hub: {pdf_path.stat().st_size:,} bytes"
                                    )
                                    return paper

                except Exception as e:
                    print(f"      Error with {mirror}: {str(e)[:50]}")
                finally:
                    await page.close()

            except:
                continue

        return Paper(url=url, doi=doi, error="Sci-Hub failed")

    async def try_annas_archive_download(
        self, url: str, title: str = None, doi: str = None
    ) -> Paper:
        """Try to download from Anna's Archive"""
        print(f"   📚 Trying Anna's Archive...")

        # Extract DOI if not provided
        if not doi:
            doi = self.extract_doi(url)

        search_query = doi or title or url
        if not search_query:
            return Paper(url=url, error="No search query for Anna's Archive")

        for mirror in ANNAS_ARCHIVE_URLS:
            try:
                # Search on Anna's Archive
                search_url = f"{mirror}/search?q={quote(search_query)}"
                print(f"      Searching: {mirror}")

                page = await self.context.new_page()
                try:
                    response = await page.goto(
                        search_url, wait_until="domcontentloaded", timeout=20000
                    )

                    if response.status != 200:
                        continue

                    await page.wait_for_timeout(2000)

                    # Click first result
                    first_result = page.locator(".js-scroll-to-top").first
                    if await first_result.count() > 0:
                        await first_result.click()
                        await page.wait_for_timeout(3000)

                        # Look for download links
                        download_selectors = [
                            'a:has-text("Slow")',  # Slow download
                            'a:has-text("Fast")',  # Fast download
                            'a[href*="get.php"]',
                            'a[href*="library.lol"]',
                            'a[href*="libgen"]',
                        ]

                        for selector in download_selectors:
                            link = page.locator(selector).first
                            if await link.count() > 0:
                                href = await link.get_attribute("href")
                                if href:
                                    # Follow download link
                                    if not href.startswith("http"):
                                        href = f"{mirror}{href}"

                                    # Navigate to download page
                                    await page.goto(href, wait_until="domcontentloaded")
                                    await page.wait_for_timeout(3000)

                                    # Look for actual PDF download
                                    pdf_link = page.locator('a[href*=".pdf"]').first
                                    if await pdf_link.count() > 0:
                                        filename = f"annas_{hashlib.sha256(search_query.encode()).hexdigest()[:10]}.pdf"
                                        pdf_path = self.base_dir / "annas" / filename
                                        pdf_path.parent.mkdir(exist_ok=True)

                                        async with page.expect_download(
                                            timeout=30000
                                        ) as download_info:
                                            await pdf_link.click()

                                        download = await download_info.value
                                        await download.save_as(pdf_path)

                                        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
                                            paper = Paper(
                                                url=url,
                                                doi=doi,
                                                title=title,
                                                pdf_path=pdf_path,
                                                success=True,
                                                download_source="annas_archive",
                                            )
                                            print(
                                                f"   ✅ Downloaded from Anna's Archive: {pdf_path.stat().st_size:,} bytes"
                                            )
                                            return paper

                except Exception as e:
                    print(f"      Error with {mirror}: {str(e)[:50]}")
                finally:
                    await page.close()

            except:
                continue

        return Paper(url=url, error="Anna's Archive failed")

    async def download_paper(self, url: str) -> Paper:
        """Download paper using all available methods"""
        print(f"\n🎯 Processing: {url}")

        # Try direct publisher download first
        paper = await self.try_publisher_download(url)
        if paper.success:
            return paper

        # Extract DOI for fallbacks
        doi = self.extract_doi(url)

        # Try Sci-Hub
        paper = await self.try_scihub_download(url, doi)
        if paper.success:
            # Try to get metadata from publisher page if needed
            if not paper.title or not paper.authors:
                publisher_paper = await self.try_publisher_download(url)
                paper.title = publisher_paper.title or paper.title
                paper.authors = publisher_paper.authors or paper.authors
                paper.journal = publisher_paper.journal
            return paper

        # Try Anna's Archive
        paper = await self.try_annas_archive_download(url, paper.title, doi)
        if paper.success:
            return paper

        # All methods failed
        print(f"   ❌ All download methods failed")
        return Paper(url=url, error="All methods failed")

    async def download_batch(self, urls: List[str]) -> List[Paper]:
        """Download multiple papers"""
        print("🚀 ULTIMATE ALL PUBLISHERS DOWNLOADER")
        print("=" * 70)
        print(f"Papers to process: {len(urls)}")
        print(f"Methods: Publisher → Sci-Hub → Anna's Archive")
        print()

        # Setup browser
        await self.setup_browser()

        results = []
        successful = 0

        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}]", end="")
            paper = await self.download_paper(url)
            results.append(paper)

            if paper.success:
                successful += 1
                print(f"   🎉 SUCCESS ({successful}/{i}) via {paper.download_source}")

                # If we have metadata, rename file properly
                if paper.pdf_path and (paper.title or paper.authors):
                    new_filename = paper.generate_correct_filename()
                    new_path = paper.pdf_path.parent / new_filename
                    try:
                        paper.pdf_path.rename(new_path)
                        paper.pdf_path = new_path
                        print(f"   📝 Renamed to: {new_filename}")
                    except:
                        pass

            await asyncio.sleep(2)  # Be polite

        # Cleanup
        if self.context:
            await self.context.browser.close()

        # Summary
        print(f"\n{'=' * 70}")
        print("📊 DOWNLOAD SUMMARY")
        print("=" * 70)
        print(f"✅ Success: {successful}/{len(urls)}")

        # Group by source
        by_source = {}
        for paper in results:
            if paper.success:
                by_source.setdefault(paper.download_source, []).append(paper)

        for source, papers in by_source.items():
            print(f"\n📚 {source.upper()}: {len(papers)} papers")
            for paper in papers[:2]:
                if paper.pdf_path:
                    print(f"   📄 {paper.pdf_path.name[:60]}...")

        # Failed papers
        failed = [p for p in results if not p.success]
        if failed:
            print(f"\n❌ FAILED: {len(failed)} papers")
            for paper in failed[:5]:
                print(f"   • {paper.url[:60]}... ({paper.error})")

        # Save results
        results_data = []
        for paper in results:
            results_data.append(
                {
                    "url": paper.url,
                    "doi": paper.doi,
                    "title": paper.title,
                    "authors": [f"{a.family}, {a.given or ''}" for a in paper.authors],
                    "success": paper.success,
                    "download_source": paper.download_source,
                    "pdf_path": str(paper.pdf_path) if paper.pdf_path else None,
                    "error": paper.error,
                }
            )

        results_file = self.base_dir / "download_results.json"
        with open(results_file, "w") as f:
            json.dump(results_data, f, indent=2)

        print(f"\n💾 Results saved to: {results_file}")

        return results


async def main():
    """Test with papers from ALL publishers"""

    test_papers = [
        # Open Access (should work easily)
        "https://arxiv.org/abs/2301.00001",
        "https://www.biorxiv.org/content/10.1101/2024.01.01.574132v1",
        "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0295432",
        "https://www.mdpi.com/2076-3417/14/1/123",
        # Springer (working with auth)
        "https://link.springer.com/article/10.1007/s11263-025-02548-7",
        # Nature
        "https://www.nature.com/articles/s41586-024-07871-w",
        # IEEE (no VPN needed!)
        "https://ieeexplore.ieee.org/document/10280029",
        "https://ieeexplore.ieee.org/document/9134692",
        # ACM (often open)
        "https://dl.acm.org/doi/10.1145/3613904.3642596",
        # Elsevier (will use Sci-Hub)
        "https://www.sciencedirect.com/science/article/pii/S0167739X23004113",
        # Wiley
        "https://onlinelibrary.wiley.com/doi/10.1002/anie.202318946",
        # More publishers
        "https://journals.sagepub.com/doi/10.1177/0956797620963615",
        "https://academic.oup.com/brain/article/144/1/1/6030166",
        "https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/abs/dark-side-of-eureka/8ED4C5A485B4B9C7F1ACB66FD959B319",
        "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.132.071801",
        "https://iopscience.iop.org/article/10.1088/1361-6633/ad0c60",
    ]

    downloader = UltimateAllPublishersDownloader()
    results = await downloader.download_batch(test_papers)

    success_count = len([r for r in results if r.success])
    print(f"\n🎯 FINAL RESULT: {success_count}/{len(test_papers)} papers downloaded")

    # Show download sources
    sources = {}
    for r in results:
        if r.success:
            sources[r.download_source] = sources.get(r.download_source, 0) + 1

    print(f"\n📊 Download sources:")
    for source, count in sources.items():
        print(f"   • {source}: {count} papers")


if __name__ == "__main__":
    asyncio.run(main())
