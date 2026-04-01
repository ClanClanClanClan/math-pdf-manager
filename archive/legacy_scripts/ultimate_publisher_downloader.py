#!/usr/bin/env python3
"""
ULTIMATE PUBLISHER DOWNLOADER - ULTRATHINK IMPLEMENTATION
The definitive solution for downloading from ALL academic publishers

Core Strategies:
1. Advanced anti-bot detection evasion
2. Persistent browser sessions with cookie management
3. Direct Shibboleth federation URLs (bypass publisher detection)
4. Fallback authentication methods
5. Smart retry logic with different approaches
"""

import asyncio
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth import stealth_async

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

# ETH Shibboleth IdP endpoint - CRITICAL for direct authentication
ETH_IDP = "https://aai-logon.ethz.ch/idp/shibboleth"
ETH_LOGIN_URL = "https://aai-logon.ethz.ch/idp/profile/SAML2/Redirect/SSO"


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
    """Paper metadata"""

    url: str
    publisher: str
    doi: str = ""
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    journal: str = ""
    year: str = ""
    pdf_url: str = ""
    pdf_path: Optional[Path] = None
    success: bool = False
    error: str = ""

    def generate_correct_filename(self) -> str:
        if self.authors:
            author_strs = [author.to_filename_format() for author in self.authors]
            authors_part = ", ".join(author_strs)
        else:
            authors_part = "Unknown"

        title_part = self.title
        if SENTENCE_CASE_AVAILABLE and title_part:
            title_part, _ = to_sentence_case_academic(title_part)
        elif title_part:
            title_part = title_part[0].upper() + title_part[1:].lower() if title_part else ""

        forbidden = '<>:"/\\|?*'
        for char in forbidden:
            title_part = title_part.replace(char, "_")
            authors_part = authors_part.replace(char, "_")

        filename = f"{authors_part} - {title_part}.pdf"

        if len(filename) > 250:
            max_title_len = 250 - len(authors_part) - len(" - .pdf")
            if max_title_len > 20:
                title_part = title_part[: max_title_len - 3] + "..."
                filename = f"{authors_part} - {title_part}.pdf"

        return filename


class UltimatePublisherDownloader:
    """The ultimate solution for academic paper downloads"""

    # Publisher-specific configurations
    PUBLISHER_CONFIG = {
        "springer": {
            "domain": "link.springer.com",
            "name": "Springer",
            "wayf_url": "https://wayf.springernature.com/?redirect_uri=https://link.springer.com",
            "direct_shibboleth": f"https://link.springer.com/Shibboleth.sso/Login?entityID={ETH_IDP}",
            "search_selector": "#searchFormTextInput",
            "pdf_selectors": [
                'a[href*=".pdf"]',
                'a:has-text("Download PDF")',
                'button:has-text("PDF")',
            ],
            "title_selectors": [
                'meta[name="citation_title"]',
                'h1[data-test="article-title"]',
                "h1",
            ],
            "author_selector": 'meta[name="citation_author"]',
        },
        "nature": {
            "domain": "nature.com",
            "name": "Nature",
            "wayf_url": "https://wayf.springernature.com/?redirect_uri=https://www.nature.com",
            "direct_shibboleth": f"https://www.nature.com/Shibboleth.sso/Login?entityID={ETH_IDP}",
            "search_selector": "#searchFormTextInput",
            "pdf_selectors": [".c-pdf-download__link", 'a:has-text("Download PDF")'],
            "title_selectors": ['meta[name="citation_title"]', ".c-article-title", "h1"],
            "author_selector": 'meta[name="citation_author"]',
        },
        "ieee": {
            "domain": "ieeexplore.ieee.org",
            "name": "IEEE",
            # IEEE direct Shibboleth URL with ETH IdP
            "direct_shibboleth": f"https://ieeexplore.ieee.org/Shibboleth.sso/Login?entityID={ETH_IDP}&target=https://ieeexplore.ieee.org/",
            "alternate_url": "https://www.ieee.org/profile/eduinstitution/getPref.html",
            "pdf_selectors": [
                'a[href*=".pdf"]',
                ".stats-document-lh-action-downloadPdf",
                'a:has-text("PDF")',
            ],
            "title_selectors": ['meta[property="og:title"]', ".document-title h1", "h1"],
            "author_selector": ".authors-info .author",
        },
        "acm": {
            "domain": "dl.acm.org",
            "name": "ACM",
            # ACM direct Shibboleth with ETH
            "direct_shibboleth": f"https://dl.acm.org/action/ssostart?idp={ETH_IDP}&redirectUri=%2F",
            "pdf_selectors": [".btn--red", 'a[href*=".pdf"]', 'a:has-text("PDF")'],
            "title_selectors": ['meta[name="citation_title"]', "h1.citation__title", "h1"],
            "author_selector": ".loa__author-name",
        },
        "elsevier": {
            "domain": "sciencedirect.com",
            "name": "Elsevier",
            # Elsevier federation URL
            "direct_shibboleth": f"https://www.sciencedirect.com/science/login/shibboleth?idp={ETH_IDP}",
            "inst_login_url": "https://www.sciencedirect.com/user/login?targetUrl=%2F",
            "pdf_selectors": ['a[aria-label*="Download PDF"]', ".PdfEmbed a"],
            "title_selectors": ['meta[name="citation_title"]', ".title-text", "h1"],
            "author_selector": 'meta[name="citation_author"]',
        },
        "wiley": {
            "domain": "onlinelibrary.wiley.com",
            "name": "Wiley",
            # Wiley Shibboleth
            "direct_shibboleth": f"https://onlinelibrary.wiley.com/action/ssostart?idp={ETH_IDP}",
            "pdf_selectors": [".coolBar__ctrl--pdf", 'a:has-text("PDF")'],
            "title_selectors": ['meta[name="citation_title"]', "h1"],
            "author_selector": 'meta[name="citation_author"]',
        },
    }

    def __init__(self, base_dir: str = "data/ultimate"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.browser = None
        self.context = None
        self.authenticated_publishers = set()

    async def setup_browser(self) -> Browser:
        """Setup browser with advanced anti-detection"""
        playwright = await async_playwright().start()

        # Use Chrome instead of Chromium for better compatibility
        browser = await playwright.chromium.launch(
            headless=False,  # Run with GUI for better success rate
            channel="chrome",  # Use actual Chrome if available
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--start-maximized",
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
        )

        return browser

    async def setup_context(self, browser: Browser) -> BrowserContext:
        """Setup browser context with stealth and cookies"""
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="Europe/Zurich",
            permissions=["geolocation"],
            geolocation={"latitude": 47.3769, "longitude": 8.5417},  # ETH Zurich coordinates
            ignore_https_errors=True,
            java_script_enabled=True,
        )

        # Advanced stealth setup
        await context.add_init_script(
            """
            // Override webdriver detection
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"}},
                    {1: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"}}
                ]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'de-CH', 'de'] });
            
            // Mock vendor
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
            
            // Mock platform
            Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
            
            // Chrome specific
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // WebGL vendor
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
            
            // Canvas fingerprint protection
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' && this.width === 280 && this.height === 60) {
                    return 'data:image/png;base64,';  // Return empty for fingerprinting canvases
                }
                return originalToDataURL.apply(this, arguments);
            };
        """
        )

        # Load cookies if they exist
        cookies_file = self.base_dir / "cookies.json"
        if cookies_file.exists():
            with open(cookies_file, "r") as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                print("📂 Loaded saved cookies")

        return context

    async def save_cookies(self):
        """Save cookies for session persistence"""
        if self.context:
            cookies = await self.context.cookies()
            cookies_file = self.base_dir / "cookies.json"
            with open(cookies_file, "w") as f:
                json.dump(cookies, f)
            print("💾 Saved cookies")

    async def authenticate_eth(self, page: Page) -> bool:
        """Authenticate with ETH credentials"""
        print("🔐 Authenticating with ETH...")

        # Check if we're on ETH login page
        if "ethz.ch" not in page.url:
            return False

        try:
            # Wait for login form
            await page.wait_for_selector(
                'input[name="j_username"], input[name="username"]', timeout=10000
            )

            # Fill credentials
            username_field = page.locator('input[name="j_username"], input[name="username"]').first
            password_field = page.locator('input[type="password"]').first

            await username_field.fill(ETH_USERNAME)
            await password_field.fill(ETH_PASSWORD)

            # Submit
            submit_button = page.locator('button[type="submit"], input[type="submit"]').first
            await submit_button.click()

            # Wait for redirect
            await page.wait_for_timeout(5000)

            # Check if authentication successful
            if "ethz.ch" not in page.url:
                print("   ✅ ETH authentication successful")
                return True
            else:
                print("   ❌ ETH authentication failed")
                return False

        except Exception as e:
            print(f"   ❌ ETH auth error: {str(e)}")
            return False

    async def authenticate_publisher(self, page: Page, publisher: str) -> bool:
        """Authenticate with a specific publisher"""

        if publisher in self.authenticated_publishers:
            print(f"   ✅ Already authenticated with {publisher}")
            return True

        config = self.PUBLISHER_CONFIG.get(publisher)
        if not config:
            return False

        print(f"🔐 Authenticating with {config['name']}...")

        # Method 1: Try direct Shibboleth URL
        if "direct_shibboleth" in config:
            print(f"   Trying direct Shibboleth...")
            try:
                await page.goto(
                    config["direct_shibboleth"], wait_until="domcontentloaded", timeout=20000
                )
                await page.wait_for_timeout(3000)

                # Check if redirected to ETH
                if "ethz.ch" in page.url:
                    auth_success = await self.authenticate_eth(page)
                    if auth_success:
                        self.authenticated_publishers.add(publisher)
                        await self.save_cookies()
                        return True
            except:
                pass

        # Method 2: Try WAYF URL
        if "wayf_url" in config:
            print(f"   Trying WAYF service...")
            try:
                await page.goto(config["wayf_url"], wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)
                await CookieBannerHandler.dismiss_cookie_banner(page)

                # Search for ETH
                if "search_selector" in config:
                    search = page.locator(config["search_selector"]).first
                    if await search.count() > 0:
                        await search.type("ETH Zurich", delay=100)
                        await page.wait_for_timeout(2000)

                        # Click ETH option
                        eth_option = page.locator('text="ETH Zurich"').first
                        if await eth_option.count() > 0:
                            await eth_option.click()
                            await page.wait_for_timeout(5000)

                            if "ethz.ch" in page.url:
                                auth_success = await self.authenticate_eth(page)
                                if auth_success:
                                    self.authenticated_publishers.add(publisher)
                                    await self.save_cookies()
                                    return True
            except:
                pass

        # Method 3: Try institutional login URL
        if "inst_login_url" in config:
            print(f"   Trying institutional login...")
            try:
                await page.goto(
                    config["inst_login_url"], wait_until="domcontentloaded", timeout=20000
                )
                await page.wait_for_timeout(3000)

                # Look for institutional button
                inst_button = page.locator(
                    'button:has-text("institution"), a:has-text("institution")'
                ).first
                if await inst_button.count() > 0:
                    await inst_button.click()
                    await page.wait_for_timeout(3000)

                    # Search for ETH
                    search = page.locator(
                        'input[type="search"], input[placeholder*="institution"]'
                    ).first
                    if await search.count() > 0:
                        await search.type("ETH", delay=100)
                        await page.wait_for_timeout(2000)

                        eth_option = page.locator('text="ETH"').first
                        if await eth_option.count() > 0:
                            await eth_option.click()
                            await page.wait_for_timeout(5000)

                            if "ethz.ch" in page.url:
                                auth_success = await self.authenticate_eth(page)
                                if auth_success:
                                    self.authenticated_publishers.add(publisher)
                                    await self.save_cookies()
                                    return True
            except:
                pass

        print(f"   ⚠️ Could not authenticate with {publisher}")
        return False

    def identify_publisher(self, url: str) -> Optional[str]:
        """Identify publisher from URL"""
        for publisher, config in self.PUBLISHER_CONFIG.items():
            if config["domain"] in url:
                return publisher
        return None

    async def extract_metadata(self, page: Page, publisher: str) -> Paper:
        """Extract paper metadata"""
        config = self.PUBLISHER_CONFIG[publisher]
        paper = Paper(url=page.url, publisher=config["name"])

        # Extract title
        for selector in config.get("title_selectors", []):
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    if selector.startswith("meta"):
                        paper.title = await elem.get_attribute("content")
                    else:
                        paper.title = await elem.text_content()

                    if paper.title:
                        paper.title = re.sub(r"\s+", " ", paper.title.strip())
                        # Clean publisher-specific patterns
                        paper.title = re.sub(
                            r"\s*[-|]\s*(IEEE|ACM|Springer|Nature|Wiley).*$", "", paper.title
                        )
                        break
            except:
                continue

        # Extract authors
        author_selector = config.get("author_selector")
        if author_selector:
            try:
                elems = await page.locator(author_selector).all()
                for elem in elems:
                    if author_selector.startswith("meta"):
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
            except:
                pass

        # Extract DOI
        doi_patterns = [
            r"/doi/(10\.\d+/[^/?]+)",
            r"/article/(10\.\d+/[^/?]+)",
            r"/document/(\d+)",
            r"/pii/([^/?]+)",
        ]

        for pattern in doi_patterns:
            match = re.search(pattern, page.url)
            if match:
                paper.doi = match.group(1)
                break

        return paper

    async def download_pdf(self, page: Page, paper: Paper, publisher: str) -> bool:
        """Download PDF with smart retry logic"""
        config = self.PUBLISHER_CONFIG[publisher]

        # Create publisher directory
        pub_dir = self.base_dir / publisher
        pub_dir.mkdir(exist_ok=True)

        # Try each PDF selector
        for selector in config.get("pdf_selectors", []):
            try:
                pdf_link = page.locator(selector).first
                if await pdf_link.count() > 0 and await pdf_link.is_visible():
                    filename = paper.generate_correct_filename()
                    pdf_path = pub_dir / filename

                    print(f"   📄 Downloading: {filename[:80]}...")

                    # Set up download
                    async with page.expect_download(timeout=30000) as download_info:
                        await pdf_link.click()

                    download = await download_info.value
                    await download.save_as(pdf_path)

                    if pdf_path.exists() and pdf_path.stat().st_size > 1000:  # At least 1KB
                        paper.pdf_path = pdf_path
                        paper.success = True
                        print(f"   ✅ Downloaded: {pdf_path.stat().st_size:,} bytes")
                        return True
            except Exception as e:
                continue

        print(f"   ❌ Could not download PDF")
        paper.error = "PDF download failed"
        return False

    async def process_paper(self, url: str) -> Paper:
        """Process a single paper with all retry logic"""

        publisher = self.identify_publisher(url)
        if not publisher:
            return Paper(url=url, publisher="Unknown", error="Unsupported publisher")

        print(f"\n📚 Processing {publisher.upper()} paper:")
        print(f"   {url}")

        page = await self.context.new_page()

        try:
            # Apply stealth to page
            await stealth_async(page)

            # Random delay to appear human
            await asyncio.sleep(random.uniform(1, 3))

            # Navigate to paper
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if response.status != 200:
                # Try authentication first
                auth_success = await self.authenticate_publisher(page, publisher)
                if auth_success:
                    # Retry navigation
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            await page.wait_for_timeout(3000)
            await CookieBannerHandler.dismiss_cookie_banner(page)

            # Extract metadata
            paper = await self.extract_metadata(page, publisher)

            # Check if we need to authenticate
            login_indicators = ['text="Sign In"', 'text="Log in"', 'text="Subscribe"']
            needs_auth = False
            for indicator in login_indicators:
                if await page.locator(indicator).count() > 0:
                    needs_auth = True
                    break

            if needs_auth and publisher not in self.authenticated_publishers:
                auth_success = await self.authenticate_publisher(page, publisher)
                if auth_success:
                    # Reload page after authentication
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)

            # Try to download PDF
            success = await self.download_pdf(page, paper, publisher)

            if not success and publisher not in self.authenticated_publishers:
                # Last attempt: authenticate and retry
                auth_success = await self.authenticate_publisher(page, publisher)
                if auth_success:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)
                    success = await self.download_pdf(page, paper, publisher)

            return paper

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return Paper(url=url, publisher=publisher, error=str(e))
        finally:
            await page.close()

    async def download_batch(self, urls: List[str]) -> List[Paper]:
        """Download multiple papers"""

        print("🚀 ULTIMATE PUBLISHER DOWNLOADER")
        print("=" * 70)
        print(f"Papers to process: {len(urls)}")
        print(f"Sentence case: {'✅ Enabled' if SENTENCE_CASE_AVAILABLE else '❌ Disabled'}")
        print()

        # Setup browser
        self.browser = await self.setup_browser()
        self.context = await self.setup_context(self.browser)

        results = []
        successful = 0

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}]")
            paper = await self.process_paper(url)
            results.append(paper)

            if paper.success:
                successful += 1
                print(f"   🎉 SUCCESS ({successful}/{i})")

            # Save cookies after each successful download
            if paper.success:
                await self.save_cookies()

            # Random delay between papers
            await asyncio.sleep(random.uniform(3, 6))

        # Cleanup
        await self.context.close()
        await self.browser.close()

        # Summary
        print(f"\n{'=' * 70}")
        print("📊 DOWNLOAD SUMMARY")
        print("=" * 70)
        print(f"✅ Success: {successful}/{len(urls)}")

        # Group by publisher
        by_publisher = {}
        for paper in results:
            by_publisher.setdefault(paper.publisher, []).append(paper)

        for publisher, papers in by_publisher.items():
            success_count = len([p for p in papers if p.success])
            print(f"\n📚 {publisher}: {success_count}/{len(papers)}")

            for paper in papers[:2]:
                if paper.success and paper.pdf_path:
                    print(f"   📄 {paper.pdf_path.name[:80]}...")

        # Save results
        results_data = []
        for paper in results:
            results_data.append(
                {
                    "url": paper.url,
                    "publisher": paper.publisher,
                    "title": paper.title,
                    "authors": [f"{a.family}, {a.given or ''}" for a in paper.authors],
                    "doi": paper.doi,
                    "success": paper.success,
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
    """Test the ultimate downloader"""

    # Test papers from multiple publishers
    test_papers = [
        # Springer (known working)
        "https://link.springer.com/article/10.1007/s11263-025-02548-7",
        "https://link.springer.com/article/10.1007/s42979-025-04237-1",
        # Nature
        "https://www.nature.com/articles/s41586-024-07871-w",
        # IEEE
        "https://ieeexplore.ieee.org/document/10280029",
        "https://ieeexplore.ieee.org/document/9134692",
        # ACM
        "https://dl.acm.org/doi/10.1145/3613904.3642596",
        # Elsevier
        "https://www.sciencedirect.com/science/article/pii/S0167739X23004113",
        # Wiley
        "https://onlinelibrary.wiley.com/doi/10.1002/anie.202318946",
    ]

    downloader = UltimatePublisherDownloader()
    results = await downloader.download_batch(test_papers)

    success_count = len([r for r in results if r.success])
    print(f"\n🎯 FINAL RESULT: {success_count}/{len(test_papers)} papers downloaded successfully")


if __name__ == "__main__":
    # Install playwright-stealth if needed
    try:
        from playwright_stealth import stealth_async
    except ImportError:
        print("Installing playwright-stealth...")
        os.system("pip install playwright-stealth")
        from playwright_stealth import stealth_async

    asyncio.run(main())
