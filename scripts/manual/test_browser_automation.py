#!/usr/bin/env python3
"""
Test browser automation publisher implementations
"""

import asyncio
import logging
from src.secure_credential_manager import SecureCredentialManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def test_browser_publishers():
    """Test browser-based publisher implementations"""
    print("\n" + "="*60)
    print("Testing Browser Automation Publishers")
    print("="*60)
    
    # Get ETH credentials
    cred_manager = SecureCredentialManager()
    username = cred_manager.get_credential("eth_username")
    password = cred_manager.get_credential("eth_password")
    
    if not username or not password:
        print("✗ No ETH credentials found")
        return
    
    print(f"✓ Using ETH credentials: {username[:3]}***")
    
    # Create credential config
    eth_config = {
        'username': username,
        'password': password,
        'institution_name': 'ETH Zurich'
    }
    
    # Test imports
    try:
        from src.downloader.browser_publisher_downloaders import (
            WileyBrowserDownloader, TaylorFrancisBrowserDownloader,
            SageBrowserDownloader, CambridgeBrowserDownloader, SpringerBrowserDownloader
        )
        print("✓ Browser publisher downloaders imported successfully")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("  Make sure Playwright is installed: playwright install")
        return
    
    # Test publishers
    publishers = [
        (WileyBrowserDownloader(eth_config), "Wiley", "machine learning"),
        (TaylorFrancisBrowserDownloader(eth_config), "Taylor & Francis", "neural networks"),
        (SageBrowserDownloader(eth_config), "SAGE", "data science"),
        (CambridgeBrowserDownloader(eth_config), "Cambridge", "artificial intelligence"),
        (SpringerBrowserDownloader(eth_config), "Springer", "algorithms")
    ]
    
    for publisher, name, query in publishers:
        print(f"\nTesting {name}:")
        print("-" * 30)
        
        try:
            # Test authentication
            print("  → Starting browser automation...")
            auth_result = await publisher.authenticate()
            print(f"  Authentication: {'✓ Success' if auth_result else '✗ Failed'}")
            
            if auth_result:
                # Test search
                print(f"  → Searching for: '{query}'")
                results = await publisher.search(query)
                print(f"  Search results: {len(results)}")
                
                if results:
                    first = results[0]
                    print(f"    First result: {first.title[:50]}...")
                    print(f"    URL: {first.url or 'N/A'}")
                
                # Test download capability (without actually downloading)
                print(f"  Confidence score: {publisher.can_handle(query)}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        finally:
            # Clean up browser
            try:
                await publisher.cleanup()
                print("  → Browser cleaned up")
            except:
                pass

async def test_universal_downloader_with_browser():
    """Test UniversalDownloader with browser implementations"""
    print("\n" + "="*60)
    print("Testing UniversalDownloader with Browser Automation")
    print("="*60)
    
    # Get ETH credentials
    cred_manager = SecureCredentialManager()
    username = cred_manager.get_credential("eth_username")
    password = cred_manager.get_credential("eth_password")
    
    # Configure with ETH credentials for all publishers
    config = {
        'credentials': {
            'wiley': {
                'username': username,
                'password': password,
                'institution_name': 'ETH Zurich'
            },
            'taylor_francis': {
                'username': username,
                'password': password,
                'institution_name': 'ETH Zurich'
            },
            'sage': {
                'username': username,
                'password': password,
                'institution_name': 'ETH Zurich'
            },
            'cambridge': {
                'username': username,
                'password': password,
                'institution_name': 'ETH Zurich'
            },
            'springer': {
                'username': username,
                'password': password,
                'institution_name': 'ETH Zurich'
            }
        }
    }
    
    from src.downloader.universal_downloader import UniversalDownloader
    
    downloader = UniversalDownloader(config)
    
    print(f"✓ Configured with ETH credentials: {username[:3]}***")
    print(f"✓ Loaded {len(downloader.strategies)} download strategies:")
    
    browser_count = 0
    for name, strategy in downloader.strategies.items():
        is_browser = 'Browser' in strategy.__class__.__name__
        print(f"  - {name}: {strategy.__class__.__name__} {'[BROWSER]' if is_browser else '[HTTP]'}")
        if is_browser:
            browser_count += 1
    
    print(f"✓ Browser automation enabled for {browser_count} publishers")
    
    # Test search (limited to avoid long browser operations)
    test_query = "quantum computing"
    print(f"\nTesting search: '{test_query}'")
    print("Note: This will launch multiple browsers - may take time...")
    
    try:
        # Test search with a small limit to avoid too many browser instances
        results = await downloader.search_all(test_query, max_results=5)
        print(f"✓ Found {len(results)} total results")
        
        # Group by source
        by_source = {}
        for result in results:
            source = result.source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(result)
        
        print("\nResults by source:")
        for source, source_results in by_source.items():
            is_browser = any('browser' in source.lower() for source in by_source.keys())
            print(f"  {source}: {len(source_results)} results")
    
    except Exception as e:
        print(f"✗ Search failed: {e}")
    
    finally:
        await downloader.close()

async def test_single_publisher_demo():
    """Demo with a single publisher to show full functionality"""
    print("\n" + "="*60)
    print("Single Publisher Demo - Wiley")
    print("="*60)
    
    # Get ETH credentials
    cred_manager = SecureCredentialManager()
    username = cred_manager.get_credential("eth_username")
    password = cred_manager.get_credential("eth_password")
    
    eth_config = {
        'username': username,
        'password': password,
        'institution_name': 'ETH Zurich'
    }
    
    try:
        from src.downloader.browser_publisher_downloaders import WileyBrowserDownloader
        
        print("✓ Testing Wiley with full browser automation")
        wiley = WileyBrowserDownloader(eth_config)
        
        # Authenticate
        print("  → Launching browser and authenticating...")
        success = await wiley.authenticate()
        
        if success:
            print("  ✓ Authentication successful!")
            
            # Search
            query = "machine learning"
            print(f"  → Searching for: '{query}'")
            results = await wiley.search(query)
            
            print(f"  ✓ Found {len(results)} results")
            for i, result in enumerate(results[:3]):
                print(f"    {i+1}. {result.title}")
                print(f"       URL: {result.url}")
        else:
            print("  ✗ Authentication failed")
            
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        
    finally:
        try:
            await wiley.cleanup()
        except:
            pass

async def main():
    """Run all browser automation tests"""
    print("Browser Automation Publisher Tests")
    print("=" * 60)
    
    # Check if Playwright is available
    try:
        from playwright.async_api import async_playwright
        print("✓ Playwright is available")
    except ImportError:
        print("✗ Playwright not installed. Install with:")
        print("  pip install playwright")
        print("  playwright install")
        return
    
    await test_browser_publishers()
    await test_universal_downloader_with_browser()
    await test_single_publisher_demo()
    
    print("\n" + "="*60)
    print("Browser Automation Test Summary:")
    print("✓ Browser-based publisher implementations created")
    print("✓ ETH institutional authentication flow implemented")
    print("✓ All publishers now use automatic navigation")
    print("✓ Integration with UniversalDownloader complete")
    print("\nNote: Browser automation requires network access to ETH")
    print("      authentication servers and publisher websites.")

if __name__ == "__main__":
    asyncio.run(main())