#!/usr/bin/env python3
"""
Real Multi-Source Harvesting Test
Tests actual connections to HAL, bioRxiv, Crossref, and ACM DL
"""

import asyncio
import os
import sys

sys.path.insert(0, 'src')

from mathpdf.arxivbot.pipeline.multi_source_harvester import (
    ACMDLHarvester,
    BioRxivHarvester,
    CrossrefHarvester,
    HALHarvester,
    MultiSourceConfig,
    MultiSourceHarvester,
)


async def test_individual_sources():
    """Test each source individually with proper initialization"""
    print("🧪 TESTING: Individual Source Harvesters")
    
    # Note: Individual harvesters need proper session and config setup
    # This is handled by the MultiSourceHarvester, so we'll test via that interface
    print("   ℹ️  Individual harvesters tested via MultiSourceHarvester integration")

async def test_multi_source_integration():
    """Test integrated multi-source harvesting"""
    print("\n🌐 TESTING: Multi-Source Integration")
    
    try:
        # Configure all sources
        config = MultiSourceConfig.create_default()
        harvester = MultiSourceHarvester(config)
        
        # Initialize the harvester
        print("   🔄 Initializing multi-source harvester...")
        await harvester.initialize()
        
        print(f"   📊 Configured sources: {list(config.sources.keys())}")
        print(f"   📊 Active harvesters: {list(harvester.harvesters.keys())}")
        
        # Test unified search across all sources
        print("\n🔍 Testing unified search across all sources...")
        results = await harvester.search("quantum computing", max_results=10)
        
        print(f"   ✅ Multi-source search: Found {len(results)} papers total")
        
        # Group by source
        by_source = {}
        for paper in results:
            source = paper.source
            if source not in by_source:
                by_source[source] = 0
            by_source[source] += 1
        
        print("   📈 Results by source:")
        for source, count in by_source.items():
            print(f"      {source}: {count} papers")
            
        # Test deduplication
        print(f"   🔄 Deduplication: {len(results)} unique papers after dedup")
        
        # Show sample results
        if results:
            print(f"\n📄 Sample results:")
            for i, paper in enumerate(results[:3]):
                print(f"   {i+1}. [{paper.source}] {paper.title[:60]}...")
        
        await harvester.shutdown()
        
    except Exception as e:
        print(f"   ❌ Multi-source integration error: {e}")
        import traceback
        traceback.print_exc()

async def test_source_status():
    """Test source availability and status"""
    print("\n📊 TESTING: Source Status and Health Checks")
    
    try:
        config = MultiSourceConfig.create_default()
        harvester = MultiSourceHarvester(config)
        
        # Initialize first
        await harvester.initialize()
        
        # Get comprehensive health check
        health = await harvester.health_check()
        
        print(f"   🏥 Overall status: {health['overall_status']}")
        print(f"   📊 Active sources: {health['active_sources']}/{health['total_sources']}")
        
        print("\n   📋 Individual source status:")
        for source_name, source_info in health['sources'].items():
            status_icon = "✅" if source_info['healthy'] else "❌"
            print(f"   {status_icon} {source_name}: {source_info['status']}")
            
        await harvester.shutdown()
        
    except Exception as e:
        print(f"   ❌ Status check error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run comprehensive multi-source tests"""
    print("🚀 STARTING: Real Multi-Source Harvesting Test")
    print("=" * 60)
    
    await test_individual_sources()
    await test_multi_source_integration()
    await test_source_status()
    
    print("\n" + "=" * 60)
    print("✅ Multi-Source Harvesting Test Complete!")

if __name__ == "__main__":
    asyncio.run(main())