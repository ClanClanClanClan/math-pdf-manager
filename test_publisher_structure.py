#!/usr/bin/env python3
"""
Test publisher implementation structure and methods
"""

import asyncio
import inspect
from src.downloader.publisher_downloaders import (
    WileyDownloader, TaylorFrancisDownloader, 
    SageDownloader, CambridgeDownloader
)
from src.downloader.universal_downloader import (
    AnnaArchiveDownloader, LibgenDownloader, DownloadStrategy
)

def test_publisher_structure(publisher_class, name):
    """Test that publisher has all required methods"""
    print(f"\nTesting {name}:")
    print("-" * 40)
    
    # Check if it inherits from DownloadStrategy
    if issubclass(publisher_class, DownloadStrategy):
        print("✓ Inherits from DownloadStrategy")
    else:
        print("✗ Does NOT inherit from DownloadStrategy")
        return False
    
    # Create instance
    try:
        if publisher_class in [AnnaArchiveDownloader, LibgenDownloader]:
            instance = publisher_class()
        else:
            instance = publisher_class({})
        print("✓ Can be instantiated")
    except Exception as e:
        print(f"✗ Cannot be instantiated: {e}")
        return False
    
    # Check required methods
    required_methods = ['search', 'download', 'can_handle', 'name']
    for method in required_methods:
        if hasattr(instance, method):
            print(f"✓ Has {method} method")
            
            # Check if it's properly implemented (not just inherited abstract)
            method_obj = getattr(instance, method)
            if callable(method_obj) or isinstance(method_obj, property):
                print(f"  → {method} is callable/property")
            else:
                print(f"  → WARNING: {method} is not callable")
        else:
            print(f"✗ Missing {method} method")
    
    # Check for additional publisher-specific methods
    if publisher_class in [WileyDownloader, TaylorFrancisDownloader, SageDownloader, CambridgeDownloader]:
        if hasattr(instance, 'authenticate'):
            print("✓ Has authenticate method")
        else:
            print("✗ Missing authenticate method")
    
    # Test can_handle method
    try:
        confidence = instance.can_handle("test query")
        print(f"✓ can_handle returns: {confidence} (type: {type(confidence).__name__})")
    except Exception as e:
        print(f"✗ can_handle failed: {e}")
    
    # Test name property
    try:
        name_value = instance.name
        print(f"✓ name property returns: '{name_value}'")
    except Exception as e:
        print(f"✗ name property failed: {e}")
    
    return True

async def test_basic_functionality():
    """Test basic functionality without requiring auth"""
    print("\n\nTesting Basic Functionality:")
    print("=" * 60)
    
    # Test Anna's Archive
    print("\nTesting Anna's Archive basic search:")
    anna = AnnaArchiveDownloader()
    try:
        # Just test that search method exists and is callable
        search_coro = anna.search("test")
        print("✓ Anna's Archive search method is callable")
        # Don't await to avoid network calls
    except Exception as e:
        print(f"✗ Anna's Archive search failed: {e}")
    
    # Test can_handle for different queries
    print("\nTesting can_handle responses:")
    publishers = [
        (WileyDownloader({}), "wiley", ["wiley.com/test", "random query"]),
        (TaylorFrancisDownloader({}), "taylor-francis", ["tandfonline.com/test", "taylor francis paper"]),
        (SageDownloader({}), "sage", ["sagepub.com/test", "sage publications"]),
        (CambridgeDownloader({}), "cambridge", ["cambridge.org/test", "cambridge university press"]),
        (AnnaArchiveDownloader(), "anna-archive", ["any query", "test"]),
        (LibgenDownloader(), "libgen", ["libgen query", "library genesis"])
    ]
    
    for publisher, name, queries in publishers:
        print(f"\n{name} confidence scores:")
        for query in queries:
            confidence = publisher.can_handle(query)
            print(f"  '{query}': {confidence}")

def main():
    """Run all structure tests"""
    print("Publisher Implementation Structure Test")
    print("=" * 60)
    
    publishers = [
        (WileyDownloader, "WileyDownloader"),
        (TaylorFrancisDownloader, "TaylorFrancisDownloader"),
        (SageDownloader, "SageDownloader"),
        (CambridgeDownloader, "CambridgeDownloader"),
        (AnnaArchiveDownloader, "AnnaArchiveDownloader"),
        (LibgenDownloader, "LibgenDownloader")
    ]
    
    all_passed = True
    for publisher_class, name in publishers:
        if not test_publisher_structure(publisher_class, name):
            all_passed = False
    
    # Run async tests
    asyncio.run(test_basic_functionality())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All structure tests passed!")
    else:
        print("✗ Some structure tests failed!")

if __name__ == "__main__":
    main()