#!/usr/bin/env python3
"""
ULTIMATE DOWNLOADER V2
Fixed version with working Sci-Hub integration and proper DOI handling
"""

import asyncio
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests
from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler

# Import your sentence case converter
sys.path.insert(0, str(Path(__file__).parent / "src"))
try:
    from core.sentence_case import to_sentence_case_academic

    SENTENCE_CASE_AVAILABLE = True
except ImportError:
    SENTENCE_CASE_AVAILABLE = False


@dataclass
class Author:
    family: str
    given: Optional[str] = None

    def to_filename_format(self) -> str:
        if self.given:
            initial = self.given[0].upper() + "."
            return f"{self.family}, {initial}"
        return self.family


@dataclass
class Paper:
    url: str
    doi: str = ""
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    publisher: str = ""
    pdf_path: Optional[Path] = None
    download_source: str = ""
    success: bool = False
    error: str = ""

    def generate_correct_filename(self) -> str:
        """Generate filename in your format: Authors - Title in sentence case.pdf"""
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
        if len(filename) > 200:
            max_title_len = 200 - len(authors_part) - len(" - .pdf")
            if max_title_len > 20:
                title_part = title_part[: max_title_len - 3] + "..."
                filename = f"{authors_part} - {title_part}.pdf"

        return filename


class UltimateDownloaderV2:
    """Fixed version with working Sci-Hub and proper DOI extraction"""

    SCIHUB_MIRRORS = [
        "https://sci-hub.se",
        "https://sci-hub.st",
        "https://sci-hub.ru",
        "https://sci-hub.ee",
    ]

    # Publisher configs for DOI extraction
    PUBLISHERS = {
        "nature": {"domain": "nature.com"},
        "springer": {"domain": "link.springer.com"},
        "ieee": {"domain": "ieeexplore.ieee.org"},
        "acm": {"domain": "dl.acm.org"},
        "elsevier": {"domain": "sciencedirect.com"},
        "wiley": {"domain": "onlinelibrary.wiley.com"},
        "aps": {"domain": "journals.aps.org"},
        "arxiv": {"domain": "arxiv.org"},
    }

    def __init__(self, base_dir: str = "data/papers_v2"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # HTTP session for Sci-Hub
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )

    def identify_publisher(self, url: str) -> Optional[str]:
        """Identify publisher from URL"""
        for pub_name, config in self.PUBLISHERS.items():
            if config["domain"] in url:
                return pub_name
        return None

    def extract_doi_from_url(self, url: str) -> Optional[str]:
        """Extract DOI from URL patterns"""
        patterns = [
            r"doi\.org/(10\.\d+/[^\s?#]+)",
            r"/doi/(10\.\d+/[^\s?#]+)",
            r"/abs/(10\.\d+/[^\s?#]+)",
            r"doi:(10\.\d+/[^\s?#]+)",
            r"(10\.\d+/[^\s?#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                groups = match.groups()
                if groups:
                    return groups[0]
                else:
                    return match.group(0)
        return None

    async def extract_metadata_from_page(self, url: str) -> Paper:
        """Extract metadata from publisher page"""
        print(f"   📄 Extracting metadata from page...")

        paper = Paper(url=url)
        paper.publisher = self.identify_publisher(url) or "unknown"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # Navigate to page
                response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                if response.status != 200:
                    paper.error = f"HTTP {response.status}"
                    return paper

                await page.wait_for_timeout(3000)
                await CookieBannerHandler.dismiss_cookie_banner(page)

                # Extract DOI from meta tags
                doi_selectors = [
                    'meta[name="citation_doi"]',
                    'meta[name="doi"]',
                    'meta[property="citation_doi"]',
                ]

                for selector in doi_selectors:
                    try:
                        elem = page.locator(selector).first
                        if await elem.count() > 0:
                            doi_content = await elem.get_attribute("content")
                            if doi_content and "10." in doi_content:
                                paper.doi = doi_content.strip()
                                print(f"      Found DOI: {paper.doi}")
                                break
                    except:
                        continue

                # Extract title
                title_selectors = [
                    'meta[name="citation_title"]',
                    'meta[property="og:title"]',
                    "h1",
                    "title",
                ]

                for selector in title_selectors:
                    try:
                        elem = page.locator(selector).first
                        if await elem.count() > 0:
                            if selector.startswith("meta"):
                                title_content = await elem.get_attribute("content")
                            else:
                                title_content = await elem.text_content()

                            if title_content:
                                paper.title = re.sub(r"\\s+", " ", title_content.strip())
                                print(f"      Found title: {paper.title[:50]}...")
                                break
                    except:
                        continue

                # Extract authors
                author_selectors = [
                    'meta[name="citation_author"]',
                    'meta[name="author"]',
                    ".authors .author",
                    ".author-list .author",
                ]

                for selector in author_selectors:
                    try:
                        if selector.startswith("meta"):
                            elems = await page.locator(selector).all()
                            for elem in elems[:10]:  # Limit authors
                                name = await elem.get_attribute("content")
                                if name:
                                    paper.authors.append(self._parse_author_name(name))
                        else:
                            elems = await page.locator(selector).all()
                            for elem in elems[:10]:
                                name = await elem.text_content()
                                if name:
                                    paper.authors.append(self._parse_author_name(name))

                        if paper.authors:
                            print(f"      Found {len(paper.authors)} authors")
                            break
                    except:
                        continue

                await browser.close()

        except Exception as e:
            paper.error = f"Metadata extraction failed: {str(e)}"

        # Try URL-based DOI extraction if no DOI found
        if not paper.doi:
            paper.doi = self.extract_doi_from_url(url) or ""

        return paper

    def _parse_author_name(self, name: str) -> Author:
        """Parse author name into Author object"""
        name = re.sub(r"\\s*\\([^)]*\\)\\s*", "", name.strip())

        if "," in name:
            parts = name.split(",", 1)
            return Author(
                family=parts[0].strip(), given=parts[1].strip() if len(parts) > 1 else None
            )
        else:
            parts = name.split()
            if len(parts) >= 2:
                return Author(family=parts[-1], given=" ".join(parts[:-1]))
            else:
                return Author(family=name)

    def download_from_scihub(self, paper: Paper) -> bool:
        """Download from Sci-Hub using the working method"""
        if not paper.doi:
            print("   ❌ No DOI available for Sci-Hub")
            return False

        print(f"   🏴‍☠️ Trying Sci-Hub with DOI: {paper.doi}")

        for mirror in self.SCIHUB_MIRRORS:
            try:
                print(f"      Trying {mirror}...")

                # Get Sci-Hub page
                scihub_url = f"{mirror}/{paper.doi}"
                response = self.session.get(scihub_url, timeout=15)

                if response.status_code != 200:
                    continue

                # Extract PDF URL
                pdf_url = self._extract_pdf_url_from_html(response.text, mirror)
                if not pdf_url:
                    continue

                print(f"      📥 Found PDF: {pdf_url[:50]}...")

                # Download PDF
                pdf_response = self.session.get(pdf_url, timeout=30)
                if pdf_response.status_code != 200:
                    continue

                # Verify PDF
                if not pdf_response.content.startswith(b"%PDF"):
                    continue

                # Save PDF
                filename = (
                    paper.generate_correct_filename()
                    if (paper.title or paper.authors)
                    else f"scihub_{paper.doi.replace('/', '_')}.pdf"
                )
                pdf_path = self.base_dir / "scihub" / filename
                pdf_path.parent.mkdir(exist_ok=True)

                with open(pdf_path, "wb") as f:
                    f.write(pdf_response.content)

                if pdf_path.exists() and pdf_path.stat().st_size > 1000:
                    paper.pdf_path = pdf_path
                    paper.success = True
                    paper.download_source = "scihub"
                    print(f"      ✅ Downloaded: {pdf_path.stat().st_size:,} bytes")
                    return True

            except Exception as e:
                print(f"      Error with {mirror}: {str(e)[:30]}...")
                continue

        return False

    def _extract_pdf_url_from_html(self, html: str, mirror: str) -> Optional[str]:
        """Extract PDF URL from Sci-Hub HTML"""
        patterns = [
            r'<iframe[^>]+src="([^"]*\.pdf[^"]*)"',
            r'<embed[^>]+src="([^"]*\.pdf[^"]*)"',
            r'<object[^>]+data="([^"]*\.pdf[^"]*)"',
            r'src="([^"]*\.pdf[^"]*)"',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                pdf_url = match

                # Handle relative URLs
                if pdf_url.startswith("//"):
                    pdf_url = f"https:{pdf_url}"
                elif pdf_url.startswith("/"):
                    pdf_url = f"{mirror}{pdf_url}"
                elif not pdf_url.startswith("http"):
                    pdf_url = f"{mirror}/{pdf_url}"

                pdf_url = pdf_url.split("#")[0]  # Remove fragment

                if ".pdf" in pdf_url:
                    return pdf_url

        return None

    async def download_paper(self, url: str) -> Paper:
        """Download paper using all methods"""
        print(f"\\n🎯 Processing: {url}")

        # Step 1: Extract metadata (including DOI)
        paper = await self.extract_metadata_from_page(url)

        if paper.error:
            print(f"   ❌ Metadata extraction failed: {paper.error}")
            return paper

        print(f"   📊 Publisher: {paper.publisher}")
        if paper.doi:
            print(f"   🔗 DOI: {paper.doi}")
        if paper.title:
            print(f"   📄 Title: {paper.title[:60]}...")
        if paper.authors:
            print(f"   👥 Authors: {len(paper.authors)} found")

        # Step 2: Try Sci-Hub (since most publishers are paywalled)
        if paper.doi:
            if self.download_from_scihub(paper):
                return paper
        else:
            print("   ⚠️ No DOI found, cannot use Sci-Hub")

        # Step 3: All methods failed
        paper.error = "All download methods failed"
        return paper


async def test_ultimate_v2():
    """Test the improved ultimate downloader"""

    test_papers = [
        # Papers with known DOIs that should work on Sci-Hub
        "https://www.nature.com/articles/nature12373",  # Nature paper (DOI: 10.1038/nature12373)
        "https://science.sciencemag.org/content/345/6200/1255855",  # Science paper
        # IEEE paper (may or may not be on Sci-Hub)
        "https://ieeexplore.ieee.org/document/9134692",  # Computer Vision survey
        # Elsevier paper (should definitely need Sci-Hub)
        "https://www.sciencedirect.com/science/article/pii/S0167739X23004113",
    ]

    print("🚀 ULTIMATE DOWNLOADER V2 - TESTING")
    print("=" * 70)
    print("Focus: Proper DOI extraction + Working Sci-Hub integration")
    print()

    downloader = UltimateDownloaderV2()
    results = []
    successful = 0

    for i, url in enumerate(test_papers, 1):
        print(f"[{i}/{len(test_papers)}]")
        paper = await downloader.download_paper(url)
        results.append(paper)

        if paper.success:
            successful += 1
            print(f"   🎉 SUCCESS via {paper.download_source}")
        else:
            print(f"   ❌ FAILED: {paper.error}")

    print(f"\\n📊 FINAL RESULTS: {successful}/{len(test_papers)} papers downloaded")

    # Show successful downloads
    for paper in results:
        if paper.success:
            print(f"✅ {paper.pdf_path.name}")


if __name__ == "__main__":
    asyncio.run(test_ultimate_v2())
