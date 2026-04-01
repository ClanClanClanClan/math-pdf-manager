#!/usr/bin/env python3
"""
Working Sci-Hub downloader based on the successful tests
"""

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


class WorkingSciHubDownloader:
    """Actually working Sci-Hub downloader"""

    SCIHUB_MIRRORS = [
        "https://sci-hub.se",
        "https://sci-hub.st",
        "https://sci-hub.ru",
        "https://sci-hub.ee",
    ]

    def __init__(self, base_dir: str = "data/scihub"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )

    def extract_doi_from_url(self, url: str) -> str:
        """Extract DOI from various academic URLs"""

        # DOI patterns in URLs
        patterns = [
            r"doi\.org/(10\.\d+/[^\s?]+)",
            r"/doi/(10\.\d+/[^\s?]+)",
            r"doi:(10\.\d+/[^\s?]+)",
            r"(10\.\d+/[^\s?]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1) if "/" in pattern else match.group(0)

        return None

    def download_from_scihub(self, doi: str, filename: str = None) -> bool:
        """Download paper from Sci-Hub using DOI"""

        if not filename:
            # Create safe filename from DOI
            safe_doi = doi.replace("/", "_").replace(":", "_")
            filename = f"scihub_{safe_doi}.pdf"

        pdf_path = self.base_dir / filename

        print(f"🏴‍☠️ Downloading from Sci-Hub: {doi}")

        for mirror in self.SCIHUB_MIRRORS:
            try:
                print(f"   Trying {mirror}...")

                # Get Sci-Hub page
                scihub_url = f"{mirror}/{doi}"
                response = self.session.get(scihub_url, timeout=15)

                if response.status_code != 200:
                    print(f"      ❌ HTTP {response.status_code}")
                    continue

                print(f"      ✅ Page loaded")

                # Extract PDF URL from page
                pdf_url = self._extract_pdf_url(response.text, mirror)

                if not pdf_url:
                    print(f"      ❌ No PDF URL found")
                    continue

                print(f"      📥 PDF URL found: {pdf_url[:50]}...")

                # Download the PDF
                pdf_response = self.session.get(pdf_url, timeout=30)

                if pdf_response.status_code != 200:
                    print(f"      ❌ PDF download failed: HTTP {pdf_response.status_code}")
                    continue

                # Verify it's a PDF
                if not pdf_response.content.startswith(b"%PDF"):
                    print(f"      ❌ Not a valid PDF file")
                    continue

                # Save PDF
                with open(pdf_path, "wb") as f:
                    f.write(pdf_response.content)

                if pdf_path.exists() and pdf_path.stat().st_size > 1000:
                    print(f"      ✅ Downloaded: {pdf_path.stat().st_size:,} bytes")
                    print(f"      📄 Saved as: {filename}")
                    return True

            except Exception as e:
                print(f"      ❌ Error: {str(e)[:50]}")
                continue

        print(f"   ❌ All mirrors failed")
        return False

    def _extract_pdf_url(self, html: str, mirror: str) -> str:
        """Extract PDF URL from Sci-Hub HTML"""

        # Patterns to find PDF URLs in Sci-Hub pages
        patterns = [
            r'<iframe[^>]+src="([^"]*\.pdf[^"]*)"',
            r'<embed[^>]+src="([^"]*\.pdf[^"]*)"',
            r'<object[^>]+data="([^"]*\.pdf[^"]*)"',
            r'href="([^"]*\.pdf[^"]*)"',
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

                # Clean up URL
                pdf_url = pdf_url.split("#")[0]  # Remove fragment

                if ".pdf" in pdf_url:
                    return pdf_url

        return None

    def test_known_papers(self):
        """Test with papers known to be on Sci-Hub"""

        test_cases = [
            {"doi": "10.1038/nature12373", "title": "Nature paper (should work)"},
            {"doi": "10.1126/science.1259855", "title": "Science paper (should work)"},
            {"doi": "10.1109/TPAMI.2020.3019330", "title": "IEEE Computer Vision paper"},
        ]

        print("🧪 TESTING WORKING SCI-HUB DOWNLOADER")
        print("=" * 60)

        successful = 0

        for i, test in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] {test['title']}")

            if self.download_from_scihub(test["doi"]):
                successful += 1
                print(f"   🎉 SUCCESS")
            else:
                print(f"   ❌ FAILED")

        print(f"\n📊 RESULTS: {successful}/{len(test_cases)} papers downloaded")
        return successful == len(test_cases)


if __name__ == "__main__":
    downloader = WorkingSciHubDownloader()
    success = downloader.test_known_papers()

    if success:
        print("\n✅ Sci-Hub downloader is working perfectly!")
        print("   Ready to integrate into ultimate downloader")
    else:
        print("\n❌ Some issues remain to debug")
