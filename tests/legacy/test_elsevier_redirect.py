#!/usr/bin/env python3
"""
Test Elsevier Redirect Handling

The DOI redirects to linkinghub.elsevier.com instead of sciencedirect.com.
This test will follow the redirect chain and implement proper handling.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright


async def analyze_elsevier_redirect():
    """Analyze the Elsevier redirect chain and authentication."""
    
    working_doi = '10.1016/j.jmb.2021.166861'
    
    print(f"\n{'='*70}")
    print(f"🔍 ANALYZING ELSEVIER REDIRECT CHAIN")
    print(f"{'='*70}")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"🌐 Step 1: Navigate to DOI")
            url = f"https://doi.org/{working_doi}"
            
            # Track all navigations
            navigations = []
            
            def track_navigation(request):
                navigations.append({
                    'url': request.url,
                    'method': request.method
                })
            
            page.on('request', track_navigation)
            
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            print(f"   Final URL: {page.url}")
            print(f"   Title: {await page.title()}")
            print(f"   Status: {response.status}")
            
            print(f"\n🔗 Redirect chain:")
            for i, nav in enumerate(navigations[:10]):
                print(f"   {i+1}. {nav['method']} {nav['url']}")
            
            print(f"\n🔍 Analyzing current page...")
            
            # Check if we're at linkinghub
            current_url = page.url
            if 'linkinghub.elsevier.com' in current_url:
                print(f"   📍 At Elsevier Link Hub")
                
                # Wait for any automatic redirects
                await asyncio.sleep(5)
                
                # Check if redirected to ScienceDirect
                new_url = page.url
                if new_url != current_url:
                    print(f"   🔄 Auto-redirected to: {new_url}")
                    current_url = new_url
                
                # Look for ScienceDirect access
                if 'sciencedirect.com' in current_url:
                    print(f"   ✅ Now at ScienceDirect!")
                else:
                    print(f"   🔍 Still at Link Hub, looking for ScienceDirect access...")
                    
                    # Look for buttons/links to access full article
                    all_links = await page.query_selector_all('a, button')
                    access_options = []
                    
                    for link in all_links[:20]:
                        try:
                            text = await link.inner_text()
                            href = await link.get_attribute('href')
                            
                            if text and any(term in text.lower() for term in 
                                          ['full text', 'article', 'access', 'read', 'view', 'download', 'sciencedirect']):
                                access_options.append({
                                    'text': text.strip()[:50],
                                    'href': href[:80] if href else None
                                })
                        except:
                            continue
                    
                    if access_options:
                        print(f"   🔗 Found {len(access_options)} access options:")
                        for opt in access_options[:5]:
                            print(f"      • '{opt['text']}' → {opt['href']}")
                        
                        # Try clicking the first promising option
                        for link in all_links[:20]:
                            try:
                                text = await link.inner_text()
                                if text and 'full text' in text.lower():
                                    print(f"\n   🔗 Clicking 'Full text' link...")
                                    await link.click()
                                    await page.wait_for_load_state('domcontentloaded', timeout=10000)
                                    
                                    final_url = page.url
                                    print(f"   📍 After click: {final_url}")
                                    
                                    if 'sciencedirect.com' in final_url:
                                        print(f"   ✅ Successfully reached ScienceDirect!")
                                        break
                                    
                            except Exception as e:
                                print(f"   ⚠️  Click failed: {e}")
                                continue
                    else:
                        print(f"   ❌ No obvious access options found")
            
            # Now analyze institutional access options
            print(f"\n🔐 Analyzing institutional access options...")
            
            page_content = await page.content()
            
            # Look for institutional access indicators
            institutional_terms = ['sign in', 'login', 'institutional', 'organization', 'access through', 'shibboleth']
            found_terms = []
            
            for term in institutional_terms:
                if term in page_content.lower():
                    found_terms.append(term)
            
            if found_terms:
                print(f"   ✅ Found institutional indicators: {found_terms[:3]}")
            else:
                print(f"   ⚠️  No clear institutional access indicators")
            
            # Look for specific sign-in elements
            signin_elements = []
            all_elements = await page.query_selector_all('a, button')
            
            for element in all_elements:
                try:
                    text = await element.inner_text()
                    href = await element.get_attribute('href')
                    
                    if text and any(term in text.lower() for term in 
                                  ['sign in', 'log in', 'institutional', 'organization', 'access through']):
                        signin_elements.append({
                            'text': text.strip()[:50],
                            'href': href[:80] if href else None,
                            'tag': await element.evaluate('el => el.tagName')
                        })
                except:
                    continue
            
            if signin_elements:
                print(f"\n   🔗 Found {len(signin_elements)} sign-in elements:")
                for elem in signin_elements[:5]:
                    print(f"      • {elem['tag']}: '{elem['text']}' → {elem['href']}")
            else:
                print(f"\n   ❌ No sign-in elements found")
            
            print(f"\n⏸️  Page analysis complete. Browser kept open for manual inspection...")
            print(f"Press Enter to close...")
            input()
            
        except Exception as e:
            print(f"❌ Analysis error: {e}")
        
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_elsevier_redirect())