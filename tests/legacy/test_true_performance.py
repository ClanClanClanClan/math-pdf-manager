#!/usr/bin/env python3
"""
Test TRUE performance without caching effects
Forces fresh computation every time
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mathpdf.arxivbot.monitoring.service import (
    MonitoringService,
    MonitoringServiceConfig,
    initialize_monitoring_service,
)
from mathpdf.arxivbot.pipeline import (
    OptimizedHarvesterConfig,
    PerformanceMode,
    create_production_harvester,
)


async def test_true_performance():
    """Test real performance without caching"""
    
    print("=" * 80)
    print("🔬 TRUE PERFORMANCE TEST - NO CACHING")
    print("=" * 80)
    print()
    
    # Initialize monitoring
    monitoring_config = MonitoringServiceConfig(
        prometheus_enabled=True,
        prometheus_port=9098,
        auto_start_server=True
    )
    
    monitoring_service = await initialize_monitoring_service(monitoring_config)
    
    # Test configurations with CACHE DISABLED
    test_configs = [
        {'cache': False, 'name': 'No Cache (Cold)'},
        {'cache': True, 'name': 'With Cache (First Run)'},
        {'cache': True, 'name': 'With Cache (Warm)'}
    ]
    
    all_results = []
    
    for config in test_configs:
        print(f"\n📊 TEST: {config['name']}")
        print("-" * 40)
        
        # Create fresh harvester for each test
        harvester_config = OptimizedHarvesterConfig(
            performance_mode=PerformanceMode.FAST,
            max_papers_per_batch=50,
            score_threshold=0.25,
            enable_monitoring=True,
            cache_embeddings=config['cache']  # Control caching
        )
        
        harvester = await create_production_harvester(
            monitoring_service=monitoring_service,
            **harvester_config.__dict__
        )
        
        async with harvester:
            # Test with fresh data
            category = 'cs.LG'
            
            # Run twice if caching to show warm cache effect
            runs = 2 if config['cache'] and 'Warm' in config['name'] else 1
            
            for run in range(runs):
                if run > 0:
                    print(f"  (Run {run + 1} - Cache should be warm)")
                
                start = time.time()
                results = await harvester.process_category(
                    category=category,
                    max_papers=50
                )
                elapsed = time.time() - start
                
                if 'error' not in results:
                    papers = results['papers_scored']
                    ms_per_paper = results['critical_path_ms_per_paper']
                    
                    print(f"  • Papers: {papers}")
                    print(f"  • Performance: {ms_per_paper:.2f}ms per paper")
                    print(f"  • Total time: {elapsed:.2f}s")
                    print(f"  • Cache enabled: {config['cache']}")
                    
                    if run == runs - 1:  # Only save last run
                        all_results.append({
                            'config': config['name'],
                            'ms_per_paper': ms_per_paper,
                            'papers': papers,
                            'cache': config['cache']
                        })
                else:
                    print(f"  ❌ Error: {results.get('error')}")
    
    # Analysis
    print("\n" + "=" * 80)
    print("📈 PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    if all_results:
        no_cache = [r for r in all_results if 'No Cache' in r['config']]
        with_cache_first = [r for r in all_results if 'First Run' in r['config']]
        with_cache_warm = [r for r in all_results if 'Warm' in r['config']]
        
        if no_cache:
            print(f"No Cache (TRUE PERFORMANCE):     {no_cache[0]['ms_per_paper']:.2f}ms per paper")
        if with_cache_first:
            print(f"With Cache (First Run):          {with_cache_first[0]['ms_per_paper']:.2f}ms per paper")
        if with_cache_warm:
            print(f"With Cache (Warm):               {with_cache_warm[0]['ms_per_paper']:.2f}ms per paper")
        
        print()
        print("📊 CACHING IMPACT:")
        if no_cache and with_cache_warm:
            speedup = no_cache[0]['ms_per_paper'] / with_cache_warm[0]['ms_per_paper']
            print(f"  • Cache speedup: {speedup:.1f}x faster")
            print(f"  • Time saved: {no_cache[0]['ms_per_paper'] - with_cache_warm[0]['ms_per_paper']:.2f}ms per paper")
        
        print()
        print("🎯 TRUE SPECIFICATION COMPLIANCE:")
        true_perf = no_cache[0]['ms_per_paper'] if no_cache else 0
        print(f"  • Spec requirement: ≤15ms per paper")
        print(f"  • True performance: {true_perf:.2f}ms per paper")
        print(f"  • Meets spec: {'✅ YES' if true_perf <= 15 else '❌ NO'}")
        if true_perf <= 15:
            print(f"  • Margin: {15 - true_perf:.2f}ms under target")
    
    await monitoring_service.shutdown()
    
    print("\n" + "=" * 80)
    print("🏁 TRUE PERFORMANCE TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_true_performance())