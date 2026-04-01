#!/usr/bin/env python3
"""
ULTRATHINK: Comprehensive Publisher Download Solution
Deep analysis and implementation for ALL major publishers

Key Insights:
1. Most publishers use Shibboleth/SAML for institutional authentication
2. Each has specific WAYF (Where Are You From) endpoints
3. Bot detection is blocking direct access - need proper browser automation
4. Cookie handling is critical for maintaining sessions
5. Each publisher has unique metadata and PDF access patterns

Strategy:
- Use proper institutional discovery services
- Maintain persistent sessions with cookies
- Handle JavaScript-heavy authentication flows
- Implement publisher-specific access patterns
"""

import asyncio
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import BrowserContext, Page, async_playwright

from cookie_banner_handler import CookieBannerHandler

# Import your sentence case converter
sys.path.insert(0, str(Path(__file__).parent / "src"))
try:
    from core.sentence_case import to_sentence_case_academic

    SENTENCE_CASE_AVAILABLE = True
except ImportError:
    SENTENCE_CASE_AVAILABLE = False

# ETH credentials (no hardcoded defaults)
ETH_USERNAME = os.getenv("ETH_USERNAME")
ETH_PASSWORD = os.getenv("ETH_PASSWORD")

# Fallback to SecureCredentialManager if env not set
if not (ETH_USERNAME and ETH_PASSWORD):
    try:
        from mathpdf.secure_credential_manager import get_credential_manager
    except Exception:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        try:
            from mathpdf.secure_credential_manager import get_credential_manager
        except Exception:
            get_credential_manager = None

    if get_credential_manager:
        cm = get_credential_manager()
        u, p = cm.get_eth_credentials()
        ETH_USERNAME = ETH_USERNAME or u
        ETH_PASSWORD = ETH_PASSWORD or p

if not ETH_USERNAME or not ETH_PASSWORD:
    raise RuntimeError(
        "Missing ETH credentials. Set ETH_USERNAME/ETH_PASSWORD or use secure_credential_manager."
    )


@dataclass
class Author:
    """Universal author representation"""

    family: str
    given: Optional[str] = None

    def to_filename_format(self) -> str:
        """Your format: 'Last, F.'"""
        if self.given:
            initial = self.given[0].upper() + "."
            return f"{self.family}, {initial}"
        return self.family


@dataclass
class Paper:
    """Universal paper representation"""

    url: str
    publisher: str
    doi: str = ""
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    journal: str = ""
    year: str = ""
    pdf_url: str = ""
    pdf_size: Optional[int] = None
    downloaded_at: Optional[datetime] = None

    def generate_correct_filename(self) -> str:
        """Generate filename in YOUR format"""
        # Format ALL authors (no et al.)
        if self.authors:
            author_strs = [author.to_filename_format() for author in self.authors]
            authors_part = ", ".join(author_strs)
        else:
            authors_part = "Unknown"

        # Convert title to sentence case
        title_part = self.title
        if SENTENCE_CASE_AVAILABLE and title_part:
            title_part, _ = to_sentence_case_academic(title_part)
        elif title_part:
            title_part = title_part[0].upper() + title_part[1:].lower() if title_part else ""

        # Remove problematic characters
        forbidden = '<>:"/\\|?*'
        for char in forbidden:
            title_part = title_part.replace(char, "_")
            authors_part = authors_part.replace(char, "_")

        # Construct filename
        filename = f"{authors_part} - {title_part}.pdf"

        # Ensure reasonable length
        if len(filename) > 250:
            max_title_len = 250 - len(authors_part) - len(" - .pdf")
            if max_title_len > 20:
                title_part = title_part[: max_title_len - 3] + "..."
                filename = f"{authors_part} - {title_part}.pdf"

        return filename


class PublisherDownloader(ABC):
    """Abstract base class for publisher-specific downloaders"""

    def __init__(self, name: str, domain: str, base_dir: Path):
        self.name = name
        self.domain = domain
        self.base_dir = base_dir / name.lower().replace(" ", "_")
        self.pdfs_dir = self.base_dir / "pdfs"
        self.metadata_dir = self.base_dir / "metadata"

        for dir_path in [self.pdfs_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    async def authenticate(self, page: Page) -> bool:
        """Publisher-specific authentication"""
        pass

    @abstractmethod
    async def extract_metadata(self, page: Page, url: str) -> Paper:
        """Publisher-specific metadata extraction"""
        pass

    @abstractmethod
    async def download_pdf(self, page: Page, paper: Paper) -> bool:
        """Publisher-specific PDF download"""
        pass

    async def process_paper(self, page: Page, url: str) -> Tuple[bool, Paper]:
        """Process a single paper"""
        try:
            paper = await self.extract_metadata(page, url)
            success = await self.download_pdf(page, paper)
            return success, paper
        except Exception as e:
            print(f"   ❌ Error processing {url}: {str(e)}")
            return False, Paper(url=url, publisher=self.name)


class SpringerDownloader(PublisherDownloader):
    """Springer/Nature downloader - WORKING"""

    def __init__(self, base_dir: Path):
        super().__init__("Springer", "link.springer.com", base_dir)
        self.wayf_url = "https://wayf.springernature.com/?redirect_uri=https://link.springer.com"

    async def authenticate(self, page: Page) -> bool:
        """Authenticate via Springer WAYF"""
        print(f"🔐 Authenticating {self.name} with ETH...")

        await page.goto(self.wayf_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await CookieBannerHandler.dismiss_cookie_banner(page)

        # Search for ETH
        search_input = page.locator('#searchFormTextInput, input[name="search"]').first
        if await search_input.count() > 0:
            await search_input.type("ETH Zurich", delay=100)
            await page.wait_for_timeout(2000)

            # Select ETH from dropdown
            eth_option = page.locator('[role="listbox"] *:has-text("ETH Zurich")').first
            if await eth_option.count() > 0:
                await eth_option.click()
                await page.wait_for_timeout(5000)

                # ETH login
                if "ethz.ch" in page.url:
                    await page.locator('input[name="j_username"]').fill(ETH_USERNAME)
                    await page.locator('input[type="password"]').fill(ETH_PASSWORD)
                    await page.locator('button[type="submit"]').click()
                    await page.wait_for_timeout(8000)

                    if "springer.com" in page.url:
                        print("   ✅ Authentication successful")
                        return True

        return False

    async def extract_metadata(self, page: Page, url: str) -> Paper:
        """Extract Springer metadata"""
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        paper = Paper(url=url, publisher=self.name)

        # DOI
        doi_match = re.search(r"/article/([^/?]+)", url)
        if doi_match:
            paper.doi = doi_match.group(1)

        # Title
        for selector in ['meta[name="citation_title"]', 'h1[data-test="article-title"]', "h1"]:
            elem = page.locator(selector).first
            if await elem.count() > 0:
                if selector.startswith("meta"):
                    paper.title = await elem.get_attribute("content")
                else:
                    paper.title = await elem.text_content()
                paper.title = re.sub(r"\s+", " ", paper.title.strip())
                break

        # Authors
        author_elems = await page.locator('meta[name="citation_author"]').all()
        for elem in author_elems:
            name = await elem.get_attribute("content")
            if name:
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
                        paper.authors.append(Author(family=parts[-1], given=" ".join(parts[:-1])))
                    else:
                        paper.authors.append(Author(family=name))

        return paper

    async def download_pdf(self, page: Page, paper: Paper) -> bool:
        """Download Springer PDF"""
        pdf_link = page.locator('a[href*=".pdf"], a:has-text("Download PDF")').first
        if await pdf_link.count() > 0:
            correct_filename = paper.generate_correct_filename()
            pdf_path = self.pdfs_dir / correct_filename

            try:
                async with page.expect_download() as download_info:
                    await pdf_link.click()
                download = await download_info.value
                await download.save_as(pdf_path)

                if pdf_path.exists() and pdf_path.stat().st_size > 0:
                    paper.pdf_size = pdf_path.stat().st_size
                    paper.downloaded_at = datetime.now()
                    print(f"   ✅ Downloaded: {correct_filename}")
                    return True
            except:
                pass

        return False


class IEEEDownloader(PublisherDownloader):
    """IEEE Xplore downloader with proper authentication"""

    def __init__(self, base_dir: Path):
        super().__init__("IEEE", "ieeexplore.ieee.org", base_dir)
        # IEEE uses OpenAthens for many institutions
        self.openathens_url = "https://ieeexplore.ieee.org/servlet/wayf.jsp"

    async def authenticate(self, page: Page) -> bool:
        """Authenticate via IEEE OpenAthens/Shibboleth"""
        print(f"🔐 Authenticating {self.name} with ETH...")

        # Method 1: Try OpenAthens
        await page.goto(self.openathens_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Look for institution search
        search_selectors = [
            'input[placeholder*="institution"]',
            'input[name="searchInstitution"]',
            "#institutionSearch",
        ]

        for selector in search_selectors:
            search_input = page.locator(selector).first
            if await search_input.count() > 0:
                await search_input.type("ETH", delay=100)
                await page.wait_for_timeout(2000)

                # Look for ETH in results
                eth_option = page.locator('text="ETH Zurich"').first
                if await eth_option.count() > 0:
                    await eth_option.click()
                    await page.wait_for_timeout(5000)

                    # Handle ETH login if redirected
                    if "ethz.ch" in page.url:
                        await self._eth_login(page)

                        if "ieee.org" in page.url:
                            print("   ✅ Authenticated via OpenAthens")
                            return True
                break

        # Method 2: Direct institutional sign-in
        await page.goto("https://ieeexplore.ieee.org/Xplore/home.jsp")
        await page.wait_for_timeout(3000)

        # Click institutional sign-in
        inst_signin = page.locator('a:has-text("Institutional Sign In")').first
        if await inst_signin.count() > 0:
            await inst_signin.click()
            await page.wait_for_timeout(3000)

            # Search for ETH
            search_input = page.locator('input[type="search"]').first
            if await search_input.count() > 0:
                await search_input.type("ETH Zurich", delay=100)
                await page.wait_for_timeout(2000)

                eth_link = page.locator('a:has-text("ETH")').first
                if await eth_link.count() > 0:
                    await eth_link.click()
                    await page.wait_for_timeout(5000)

                    if "ethz.ch" in page.url:
                        await self._eth_login(page)

                        if "ieee.org" in page.url:
                            print("   ✅ Authenticated via institutional sign-in")
                            return True

        print("   ⚠️ Authentication unclear")
        return True  # Proceed anyway

    async def _eth_login(self, page: Page):
        """Handle ETH login page"""
        username_field = page.locator('input[name="j_username"], input[name="username"]').first
        if await username_field.count() > 0:
            await username_field.fill(ETH_USERNAME)
            await page.locator('input[type="password"]').fill(ETH_PASSWORD)
            await page.locator('button[type="submit"]').click()
            await page.wait_for_timeout(8000)

    async def extract_metadata(self, page: Page, url: str) -> Paper:
        """Extract IEEE metadata"""
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        paper = Paper(url=url, publisher=self.name)

        # Document ID
        doc_match = re.search(r"/document/(\d+)", url)
        if doc_match:
            paper.doi = f"IEEE_{doc_match.group(1)}"

        # Title - IEEE specific
        for selector in ['meta[property="og:title"]', ".document-title h1", "h1"]:
            elem = page.locator(selector).first
            if await elem.count() > 0:
                if selector.startswith("meta"):
                    paper.title = await elem.get_attribute("content")
                else:
                    paper.title = await elem.text_content()
                paper.title = re.sub(r"\s*-\s*IEEE.*$", "", paper.title)
                paper.title = re.sub(r"\s+", " ", paper.title.strip())
                break

        # Authors - IEEE specific patterns
        author_selectors = [
            'meta[name="citation_author"]',
            ".authors-info .author",
            ".document-authors a",
        ]

        for selector in author_selectors:
            elems = await page.locator(selector).all()
            if elems:
                for elem in elems:
                    if selector.startswith("meta"):
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
                            else:
                                paper.authors.append(Author(family=name))
                break

        return paper

    async def download_pdf(self, page: Page, paper: Paper) -> bool:
        """Download IEEE PDF"""
        pdf_selectors = [
            'a[href*=".pdf"]',
            'a:has-text("PDF")',
            ".stats-document-lh-action-downloadPdf",
        ]

        for selector in pdf_selectors:
            pdf_link = page.locator(selector).first
            if await pdf_link.count() > 0 and await pdf_link.is_visible():
                correct_filename = paper.generate_correct_filename()
                pdf_path = self.pdfs_dir / correct_filename

                try:
                    async with page.expect_download() as download_info:
                        await pdf_link.click()
                    download = await download_info.value
                    await download.save_as(pdf_path)

                    if pdf_path.exists() and pdf_path.stat().st_size > 0:
                        paper.pdf_size = pdf_path.stat().st_size
                        paper.downloaded_at = datetime.now()
                        print(f"   ✅ Downloaded: {correct_filename}")
                        return True
                except:
                    pass

        return False


class ElsevierDownloader(PublisherDownloader):
    """Elsevier/ScienceDirect downloader"""

    def __init__(self, base_dir: Path):
        super().__init__("Elsevier", "sciencedirect.com", base_dir)
        # Elsevier institutional access
        self.inst_url = "https://www.sciencedirect.com/user/login?targetUrl=%2F"

    async def authenticate(self, page: Page) -> bool:
        """Authenticate via Elsevier institutional access"""
        print(f"🔐 Authenticating {self.name} with ETH...")

        await page.goto(self.inst_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Click on institutional login
        inst_button = page.locator('button:has-text("Sign in via your institution")').first
        if await inst_button.count() > 0:
            await inst_button.click()
            await page.wait_for_timeout(3000)

            # Search for ETH
            search_input = page.locator(
                'input[type="search"], input[placeholder*="institution"]'
            ).first
            if await search_input.count() > 0:
                await search_input.type("ETH Zurich", delay=100)
                await page.wait_for_timeout(2000)

                # Select ETH
                eth_option = page.locator('text="ETH Zurich"').first
                if await eth_option.count() > 0:
                    await eth_option.click()
                    await page.wait_for_timeout(5000)

                    # Handle ETH login
                    if "ethz.ch" in page.url:
                        await self._eth_login(page)

                        if "sciencedirect.com" in page.url:
                            print("   ✅ Authenticated")
                            return True

        return False

    async def _eth_login(self, page: Page):
        """Handle ETH login"""
        username_field = page.locator('input[name="j_username"], input[name="username"]').first
        if await username_field.count() > 0:
            await username_field.fill(ETH_USERNAME)
            await page.locator('input[type="password"]').fill(ETH_PASSWORD)
            await page.locator('button[type="submit"]').click()
            await page.wait_for_timeout(8000)

    async def extract_metadata(self, page: Page, url: str) -> Paper:
        """Extract Elsevier metadata"""
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        paper = Paper(url=url, publisher=self.name)

        # Extract PII/DOI
        pii_match = re.search(r"/pii/([^/?]+)", url)
        if pii_match:
            paper.doi = pii_match.group(1)

        # Title
        for selector in ['meta[name="citation_title"]', ".title-text", "h1"]:
            elem = page.locator(selector).first
            if await elem.count() > 0:
                if selector.startswith("meta"):
                    paper.title = await elem.get_attribute("content")
                else:
                    paper.title = await elem.text_content()
                paper.title = re.sub(r"\s+", " ", paper.title.strip())
                break

        # Authors
        author_elems = await page.locator('meta[name="citation_author"]').all()
        for elem in author_elems:
            name = await elem.get_attribute("content")
            if name:
                # Parse Elsevier author format
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
                        paper.authors.append(Author(family=parts[-1], given=" ".join(parts[:-1])))
                    else:
                        paper.authors.append(Author(family=name))

        return paper

    async def download_pdf(self, page: Page, paper: Paper) -> bool:
        """Download Elsevier PDF"""
        pdf_selectors = [
            'a[aria-label*="Download PDF"]',
            'a:has-text("Download PDF")',
            ".PdfEmbed a",
        ]

        for selector in pdf_selectors:
            pdf_link = page.locator(selector).first
            if await pdf_link.count() > 0:
                correct_filename = paper.generate_correct_filename()
                pdf_path = self.pdfs_dir / correct_filename

                try:
                    async with page.expect_download() as download_info:
                        await pdf_link.click()
                    download = await download_info.value
                    await download.save_as(pdf_path)

                    if pdf_path.exists() and pdf_path.stat().st_size > 0:
                        paper.pdf_size = pdf_path.stat().st_size
                        paper.downloaded_at = datetime.now()
                        print(f"   ✅ Downloaded: {correct_filename}")
                        return True
                except:
                    pass

        return False


class UnifiedPublisherDownloader:
    """Unified interface for all publishers"""

    def __init__(self, base_dir: str = "data/publishers"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Initialize all publisher downloaders
        self.downloaders = {
            "springer": SpringerDownloader(self.base_dir),
            "ieee": IEEEDownloader(self.base_dir),
            "elsevier": ElsevierDownloader(self.base_dir),
        }

        # URL patterns to identify publishers
        self.url_patterns = {
            "springer": r"link\.springer\.com|nature\.com",
            "ieee": r"ieeexplore\.ieee\.org",
            "elsevier": r"sciencedirect\.com",
        }

    def identify_publisher(self, url: str) -> Optional[str]:
        """Identify publisher from URL"""
        for publisher, pattern in self.url_patterns.items():
            if re.search(pattern, url):
                return publisher
        return None

    async def download_paper(self, url: str, context: BrowserContext) -> Tuple[bool, Paper]:
        """Download a paper from any supported publisher"""
        publisher = self.identify_publisher(url)
        if not publisher:
            print(f"❌ Unsupported publisher for URL: {url}")
            return False, Paper(url=url, publisher="Unknown")

        print(f"\n📚 Processing {publisher.upper()} paper:")
        print(f"   {url}")

        downloader = self.downloaders[publisher]
        page = await context.new_page()

        try:
            # Authenticate if needed
            if not hasattr(downloader, "_authenticated"):
                auth_success = await downloader.authenticate(page)
                if auth_success:
                    downloader._authenticated = True
                else:
                    print(f"   ❌ Authentication failed for {publisher}")
                    return False, Paper(url=url, publisher=publisher)

            # Process paper
            success, paper = await downloader.process_paper(page, url)
            return success, paper

        finally:
            await page.close()

    async def download_batch(self, urls: List[str]):
        """Download multiple papers from various publishers"""
        print("🚀 UNIFIED PUBLISHER DOWNLOADER")
        print("=" * 70)
        print(f"Papers to process: {len(urls)}")
        print()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
            )

            # Add stealth scripts
            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' })
                    })
                });
            """
            )

            results = []
            successful = 0

            for i, url in enumerate(urls, 1):
                print(f"\n[{i}/{len(urls)}] Processing:")
                success, paper = await self.download_paper(url, context)

                if success:
                    successful += 1
                    results.append(
                        {
                            "url": url,
                            "publisher": paper.publisher,
                            "title": paper.title,
                            "authors": [f"{a.family}, {a.given or 'X'}" for a in paper.authors],
                            "filename": paper.generate_correct_filename(),
                            "success": True,
                        }
                    )
                    print(f"   🎉 SUCCESS ({successful}/{len(urls)})")
                else:
                    results.append({"url": url, "publisher": paper.publisher, "success": False})

                await asyncio.sleep(3)  # Be polite between downloads

            await browser.close()

        # Summary
        print(f"\n{'=' * 70}")
        print(f"📊 DOWNLOAD SUMMARY")
        print(f"{'=' * 70}")
        print(f"✅ Success: {successful}/{len(urls)}")

        # Group by publisher
        by_publisher = {}
        for result in results:
            pub = result.get("publisher", "Unknown")
            by_publisher.setdefault(pub, []).append(result)

        for publisher, pub_results in by_publisher.items():
            success_count = len([r for r in pub_results if r["success"]])
            print(f"\n📚 {publisher.upper()}: {success_count}/{len(pub_results)}")

            for result in pub_results[:2]:  # Show first 2
                if result["success"]:
                    print(f"   📄 {result['filename'][:80]}...")

        return results


async def main():
    """Test the unified downloader with papers from multiple publishers"""

    # Test papers from different publishers
    test_papers = [
        # Springer (known to work)
        "https://link.springer.com/article/10.1007/s11263-025-02548-7",
        "https://link.springer.com/article/10.1007/s42979-025-04237-1",
        # IEEE
        "https://ieeexplore.ieee.org/document/10280029",
        "https://ieeexplore.ieee.org/document/9134692",
        # Elsevier (if accessible)
        "https://www.sciencedirect.com/science/article/pii/S0167739X23004113",
    ]

    downloader = UnifiedPublisherDownloader()
    results = await downloader.download_batch(test_papers)

    # Save results
    with open("unified_download_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: unified_download_results.json")


if __name__ == "__main__":
    asyncio.run(main())
