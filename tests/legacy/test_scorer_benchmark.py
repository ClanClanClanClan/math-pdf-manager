#!/usr/bin/env python3
"""
Benchmark Test: Original Scorer vs Optimized Scorer
Shows ACTUAL performance, not theoretical claims
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List

import psutil

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mathpdf.arxivbot.models.cmo import CMO, Author
from mathpdf.arxivbot.scorer import ArxivBotScorer, ScorerConfig
from mathpdf.arxivbot.scorer_optimized import OptimizedScorer, OptimizedScorerConfig
from mathpdf.arxivbot.testing.mock_database import create_mock_database

logger = logging.getLogger(__name__)

async def create_test_papers(count: int) -> List[CMO]:
    """Create test papers for benchmarking"""
    papers = []
    for i in range(count):
        paper = CMO(
            external_id=f"test:{i:04d}",
            source="test",
            title=f"Test Paper {i}: Stochastic Analysis and Optimal Control",
            authors=[Author(family=f"Test{i}", given="Author")],
            published="2024-01-01T00:00:00Z",
            abstract="This paper studies convergence properties of stochastic differential equations with applications to optimal control theory. " * 20,  # Realistic length
            pdf_url=f"https://example.com/{i}.pdf",
            categories=["math.OC", "math.PR"],
            doi=f"10.1000/test.{i}"
        )
        papers.append(paper)
    return papers

async def benchmark_original_scorer(papers: List[CMO], database):
    """Benchmark the original scorer"""
    logger.info("=" * 60)
    logger.info("📊 BENCHMARKING ORIGINAL SCORER")
    logger.info("=" * 60)
    
    config = ScorerConfig(
        default_tau=0.3,
        k_neighbours=8,
        personal_corpus_path="nonexistent.pkl"
    )
    
    scorer = ArxivBotScorer(config, database)
    
    # Warmup
    logger.info("Warming up...")
    await scorer.batch_score(papers[:2])
    
    # Actual benchmark
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    results = await scorer.batch_score(papers)
    
    elapsed = time.time() - start_time
    end_memory = psutil.Process().memory_info().rss / 1024 / 1024
    memory_used = end_memory - start_memory
    
    per_paper_ms = (elapsed / len(papers)) * 1000
    
    logger.info(f"✅ Original Scorer Results:")
    logger.info(f"  Papers scored:     {len(results)}")
    logger.info(f"  Total time:        {elapsed:.2f}s")
    logger.info(f"  Per paper:         {per_paper_ms:.1f}ms")
    logger.info(f"  Throughput:        {len(papers)/elapsed:.1f} papers/sec")
    logger.info(f"  Memory used:       {memory_used:.1f} MB")
    
    return {
        'total_time': elapsed,
        'per_paper_ms': per_paper_ms,
        'throughput': len(papers)/elapsed,
        'memory_mb': memory_used
    }

async def benchmark_optimized_scorer(papers: List[CMO], database):
    """Benchmark the optimized scorer"""
    logger.info("=" * 60)
    logger.info("⚡ BENCHMARKING OPTIMIZED SCORER")
    logger.info("=" * 60)
    
    config = OptimizedScorerConfig(
        batch_size=32,
        use_gpu=False,  # CPU only for fair comparison
        fp16=False,  # No half precision on CPU
        cache_embeddings=True,
        max_workers=4
    )
    
    try:
        scorer = OptimizedScorer(config, database)
        
        # Warmup
        logger.info("Warming up...")
        await scorer.batch_score(papers[:2])
        
        # Actual benchmark
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        results = await scorer.batch_score(papers)
        
        elapsed = time.time() - start_time
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_used = end_memory - start_memory
        
        per_paper_ms = (elapsed / len(papers)) * 1000
        
        logger.info(f"✅ Optimized Scorer Results:")
        logger.info(f"  Papers scored:     {len(results)}")
        logger.info(f"  Total time:        {elapsed:.2f}s")
        logger.info(f"  Per paper:         {per_paper_ms:.1f}ms")
        logger.info(f"  Throughput:        {len(papers)/elapsed:.1f} papers/sec")
        logger.info(f"  Memory used:       {memory_used:.1f} MB")
        
        return {
            'total_time': elapsed,
            'per_paper_ms': per_paper_ms,
            'throughput': len(papers)/elapsed,
            'memory_mb': memory_used
        }
        
    except Exception as e:
        logger.error(f"❌ Optimized scorer failed: {e}")
        return None

async def main():
    """Run comparative benchmark"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s'
    )
    
    # Suppress noisy loggers
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    
    logger.info("🔬 SCORER PERFORMANCE BENCHMARK - ACTUAL RESULTS")
    logger.info("=" * 60)
    
    # Create test data
    paper_counts = [10, 50, 100]
    
    # Setup mock database
    database = await create_mock_database(seed_data=True, num_papers=200)
    
    for count in paper_counts:
        logger.info(f"\n📋 Testing with {count} papers")
        logger.info("-" * 60)
        
        papers = await create_test_papers(count)
        
        # Test original
        original_results = await benchmark_original_scorer(papers, database)
        
        # Test optimized
        optimized_results = await benchmark_optimized_scorer(papers, database)
        
        # Compare results
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 COMPARISON RESULTS ({count} papers)")
        logger.info("=" * 60)
        
        if optimized_results:
            speedup = original_results['total_time'] / optimized_results['total_time']
            memory_diff = optimized_results['memory_mb'] - original_results['memory_mb']
            
            logger.info(f"Original:  {original_results['per_paper_ms']:.1f}ms per paper")
            logger.info(f"Optimized: {optimized_results['per_paper_ms']:.1f}ms per paper")
            logger.info(f"Speedup:   {speedup:.2f}x faster")
            logger.info(f"Memory:    {'+' if memory_diff > 0 else ''}{memory_diff:.1f} MB difference")
            
            if optimized_results['per_paper_ms'] < 100:
                logger.info("✅ TARGET MET: <100ms per paper")
            else:
                logger.error(f"❌ TARGET MISSED: {optimized_results['per_paper_ms']:.1f}ms > 100ms")
        else:
            logger.error("❌ Optimized scorer failed to run")
    
    # Cleanup
    await database.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("🏁 BENCHMARK COMPLETE - These are REAL results, not claims")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())