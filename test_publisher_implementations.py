#!/usr/bin/env python3
"""
Test script to verify publisher implementations
"""

import asyncio
import logging
from src.downloader.universal_downloader import UniversalDownloader
from src.downloader.publisher_downloaders import (
    WileyDownloader, TaylorFrancisDownloader, 
    SageDownloader, CambridgeDownloader
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_individual_publisher(downloader, test_query):
    """Test individual publisher downloader"""
    logger.info(f"\nTesting {downloader.name} with query: {test_query}")
    
    try:
        # Test search
        results = await downloader.search(test_query)
        logger.info(f"Found {len(results)} results")
        
        if results:
            # Show first result
            first = results[0]
            logger.info(f"First result: {first.title}")
            logger.info(f"Authors: {', '.join(first.authors) if first.authors else 'N/A'}")
            logger.info(f"DOI: {first.doi or 'N/A'}")
            logger.info(f"URL: {first.url or 'N/A'}")
            
            # Test download (dry run - don't actually download)
            logger.info(f"Download capability: {downloader.can_handle(test_query)}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error testing {downloader.name}: {e}")
        return False

async def test_universal_downloader():
    """Test the universal downloader"""
    config = {
        'credentials': {
            # Add empty credentials for testing
            'wiley': {},
            'taylor_francis': {},
            'sage': {},
            'cambridge': {}
        }
    }
    
    downloader = UniversalDownloader(config)
    
    # Test search
    test_query = "machine learning"
    logger.info(f"\nTesting UniversalDownloader with query: {test_query}")
    
    try:
        results = await downloader.search_all(test_query, max_results=10)
        logger.info(f"Found {len(results)} total results across all sources")
        
        # Show results by source
        sources = {}
        for result in results:
            source = result.source
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
        
        logger.info("Results by source:")
        for source, count in sources.items():
            logger.info(f"  {source}: {count}")
            
    except Exception as e:
        logger.error(f"Error testing UniversalDownloader: {e}")
    
    finally:
        await downloader.close()

async def main():
    """Run all tests"""
    logger.info("Testing Publisher Implementations")
    logger.info("=" * 50)
    
    # Test individual publishers
    test_credentials = {}
    
    publishers = [
        (WileyDownloader(test_credentials), "neural networks"),
        (TaylorFrancisDownloader(test_credentials), "machine learning"),
        (SageDownloader(test_credentials), "data science"),
        (CambridgeDownloader(test_credentials), "artificial intelligence")
    ]
    
    for downloader, query in publishers:
        await test_individual_publisher(downloader, query)
        # Clean up session
        if hasattr(downloader, 'session') and downloader.session:
            await downloader.session.close()
    
    # Test universal downloader
    await test_universal_downloader()
    
    logger.info("\nTest complete!")

if __name__ == "__main__":
    asyncio.run(main())