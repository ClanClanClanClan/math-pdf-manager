#!/usr/bin/env python3
"""
Test IEEE Metadata Extraction
Quick test to see what we can extract from IEEE papers without authentication
"""

import asyncio
import json
import re

from playwright.async_api import async_playwright

from cookie_banner_handler import CookieBannerHandler

# Test with just a few IEEE papers
TEST_PAPERS = [
    "https://ieeexplore.ieee.org/document/10280029",
    "https://ieeexplore.ieee.org/document/9134692", 
    "https://ieeexplore.ieee.org/document/8186812"
]

async def test_ieee_metadata():
    """Test metadata extraction from IEEE papers"""
    
    print("🔍 TESTING IEEE METADATA EXTRACTION")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # Add stealth
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        results = []
        
        for i, url in enumerate(TEST_PAPERS, 1):
            print(f"\n[{i}] Testing: {url}")
            print("-" * 50)
            
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                print(f"   Status: {response.status}")
                
                if response.status != 200:
                    results.append({'url': url, 'status': response.status, 'accessible': False})
                    continue
                
                await page.wait_for_timeout(3000)
                await CookieBannerHandler.dismiss_cookie_banner(page)
                
                # Extract basic info
                paper_info = {'url': url, 'status': response.status, 'accessible': True}
                
                # Document ID
                doc_match = re.search(r'/document/(\d+)', url)
                if doc_match:
                    paper_info['doc_id'] = doc_match.group(1)
                    print(f"   📋 Doc ID: {paper_info['doc_id']}")
                
                # Title
                title_selectors = [
                    'meta[property="og:title"]',
                    'meta[name="citation_title"]',
                    '.document-title h1',
                    'h1.document-title',
                    '.article-title',
                    'h1'
                ]
                
                for selector in title_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0:
                            if selector.startswith('meta'):
                                title = await element.get_attribute('content')
                            else:
                                title = await element.text_content()
                            
                            if title and title.strip():
                                clean_title = title.strip()
                                clean_title = re.sub(r'\s*-\s*IEEE.*$', '', clean_title)
                                clean_title = re.sub(r'\s*\|\s*IEEE.*$', '', clean_title)
                                paper_info['title'] = clean_title
                                print(f"   📰 Title: {clean_title[:60]}...")
                                break
                    except:
                        continue
                
                # Authors
                author_selectors = [
                    'meta[name="citation_author"]',
                    '.authors-info .author',
                    '.author-list a',
                    '.document-authors a',
                    '.authors a'
                ]
                
                authors = []
                for selector in author_selectors:
                    try:
                        elements = await page.locator(selector).all()
                        if elements:
                            for elem in elements[:5]:  # Limit for testing
                                if selector.startswith('meta'):
                                    name = await elem.get_attribute('content')
                                else:
                                    name = await elem.text_content()
                                
                                if name and name.strip():
                                    clean_name = name.strip()
                                    clean_name = re.sub(r'\s*\([^)]*\)\s*', '', clean_name)
                                    authors.append(clean_name)
                            
                            if authors:
                                paper_info['authors'] = authors
                                print(f"   👥 Authors: {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}")
                                break
                    except:
                        continue
                
                # Journal/Conference
                venue_selectors = [
                    'meta[name="citation_journal_title"]',
                    'meta[name="citation_conference_title"]',
                    '.stats-document-abstract-publishedIn a',
                    '.document-banner-content .doc-abstract-pubinfo',
                    '.publication-title'
                ]
                
                for selector in venue_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0:
                            if selector.startswith('meta'):
                                venue = await element.get_attribute('content')
                            else:
                                venue = await element.text_content()
                            
                            if venue and venue.strip():
                                paper_info['venue'] = venue.strip()
                                print(f"   📚 Venue: {venue.strip()}")
                                break
                    except:
                        continue
                
                # DOI
                doi_selectors = [
                    'meta[name="citation_doi"]',
                    'a[href*="doi.org"]'
                ]
                
                for selector in doi_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0:
                            if selector.startswith('meta'):
                                doi = await element.get_attribute('content')
                            else:
                                href = await element.get_attribute('href')
                                doi_match = re.search(r'doi\.org/(.+)', href) if href else None
                                doi = doi_match.group(1) if doi_match else None
                            
                            if doi and doi.strip():
                                paper_info['doi'] = doi.strip()
                                print(f"   🔗 DOI: {doi.strip()}")
                                break
                    except:
                        continue
                
                # Look for PDF availability
                pdf_selectors = [
                    'a[href*=".pdf"]',
                    'a:has-text("Download PDF")',
                    'a:has-text("PDF")',
                    '.stats-document-lh-action-downloadPdf',
                    '.pdf-btn'
                ]
                
                pdf_found = False
                for selector in pdf_selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0 and await element.is_visible():
                            pdf_found = True
                            print(f"   📄 PDF available: {selector}")
                            break
                    except:
                        continue
                
                paper_info['pdf_available'] = pdf_found
                if not pdf_found:
                    print("   ❌ No PDF found")
                
                # Look for institutional access indicators
                access_indicators = [
                    'text="Sign In"',
                    'text="Subscribe"',
                    'text="Purchase"',
                    'text="Institutional Access"'
                ]
                
                for indicator in access_indicators:
                    try:
                        if await page.locator(indicator).count() > 0:
                            print(f"   🏛️ Access indicator: {indicator}")
                            paper_info.setdefault('access_indicators', []).append(indicator)
                    except:
                        continue
                
                results.append(paper_info)
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                results.append({'url': url, 'error': str(e), 'accessible': False})
            
            await page.wait_for_timeout(2000)
        
        await browser.close()
    
    # Summary
    print(f"\n{'=' * 60}")
    print("📊 IEEE METADATA TEST RESULTS")
    print("=" * 60)
    
    accessible = [r for r in results if r.get('accessible')]
    with_title = [r for r in accessible if 'title' in r]
    with_authors = [r for r in accessible if 'authors' in r]
    with_pdf = [r for r in accessible if r.get('pdf_available')]
    
    print(f"✅ Accessible: {len(accessible)}/{len(results)}")
    print(f"📰 With title: {len(with_title)}/{len(accessible)}")
    print(f"👥 With authors: {len(with_authors)}/{len(accessible)}")
    print(f"📄 With PDF: {len(with_pdf)}/{len(accessible)}")
    
    if accessible:
        print(f"\n🎯 SAMPLE EXTRACTIONS:")
        for result in accessible[:2]:
            print(f"   📄 {result.get('title', 'No title')[:50]}...")
            if 'authors' in result:
                print(f"      Authors: {', '.join(result['authors'][:2])}...")
            if 'venue' in result:
                print(f"      Venue: {result['venue']}")
            print()
    
    # Save results
    with open('ieee_metadata_test.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Results saved to: ieee_metadata_test.json")
    return results


async def main():
    results = await test_ieee_metadata()
    
    accessible_count = len([r for r in results if r.get('accessible')])
    if accessible_count > 0:
        print(f"\n🚀 NEXT STEP:")
        print(f"   IEEE papers are accessible ({accessible_count}/{len(results)})")
        print(f"   Can proceed with full downloader implementation")
    else:
        print(f"\n❌ ISSUE:")
        print(f"   No IEEE papers accessible - need different approach")


if __name__ == "__main__":
    asyncio.run(main())