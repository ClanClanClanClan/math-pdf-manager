#!/usr/bin/env python3
"""
Production Monitoring Test - Start metrics server and process real papers
"""

import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mathpdf.arxivbot.models.cmo import CMO
from mathpdf.arxivbot.monitoring.metrics import ArxivBotMetrics
from mathpdf.arxivbot.monitoring.service import (
    MonitoringService,
    MonitoringServiceConfig,
    initialize_monitoring_service,
)
from mathpdf.arxivbot.scorer import ArxivBotScorer, ScorerConfig
from mathpdf.arxivbot.testing.mock_database import create_mock_database

logger = logging.getLogger(__name__)

# Global monitoring service for cleanup
monitoring_service = None

async def load_real_arxiv_papers() -> List[CMO]:
    """Load real arxiv papers from the daily ingest file"""
    papers = []
    
    try:
        ingest_file = Path("ingest/2025-08-08_arxiv.ndjson")
        if not ingest_file.exists():
            logger.warning(f"Ingest file {ingest_file} not found, creating mock papers")
            return create_mock_papers()
            
        logger.info(f"Loading papers from {ingest_file}")
        with open(ingest_file) as f:
            for i, line in enumerate(f):
                if i >= 50:  # Limit to first 50 papers for testing
                    break
                    
                data = json.loads(line.strip())
                if not data:
                    continue
                    
                try:
                    # Convert JSON to CMO object
                    authors = []
                    for author_data in data.get('authors', []):
                        from mathpdf.arxivbot.models.cmo import Author
                        authors.append(Author(
                            family=author_data.get('family', ''),
                            given=author_data.get('given', '')
                        ))
                    
                    paper = CMO(
                        external_id=data['external_id'],
                        source=data['source'],
                        title=data['title'],
                        authors=authors,
                        published=data['published'],
                        abstract=data['abstract'],
                        pdf_url=data['pdf_url'],
                        categories=data.get('categories', []),
                        doi=data.get('doi')
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse paper {i}: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Failed to load ingest file: {e}")
        return create_mock_papers()
    
    logger.info(f"Loaded {len(papers)} real arxiv papers")
    return papers

def create_mock_papers() -> List[CMO]:
    """Create mock papers if real ones aren't available"""
    from mathpdf.arxivbot.models.cmo import Author
    
    papers = []
    topics = [
        "Stochastic Optimal Control",
        "Machine Learning Theory", 
        "Probability Theory",
        "Numerical Analysis",
        "Optimization Methods"
    ]
    
    for i in range(20):
        paper = CMO(
            external_id=f"mock:2025.{i:04d}",
            source="test", 
            title=f"Research on {topics[i % len(topics)]} - Paper {i}",
            authors=[Author(family=f"Author{i}", given="Test")],
            published="2025-08-09T10:00:00Z",
            abstract="This paper investigates advanced mathematical techniques " * 15,
            pdf_url=f"https://example.com/{i}.pdf",
            categories=["math.OC", "stat.ML"],
            doi=f"10.1000/mock.{i}"
        )
        papers.append(paper)
    
    return papers

async def run_monitoring_test():
    """Run production monitoring test with real papers"""
    global monitoring_service
    
    logger.info("🚀 STARTING PRODUCTION MONITORING TEST")
    logger.info("=" * 60)
    
    # Initialize monitoring service
    logger.info("📊 Starting monitoring service...")
    monitoring_config = MonitoringServiceConfig(
        prometheus_enabled=True,
        prometheus_port=9090,  # Standard port for arxiv-bot metrics
        auto_start_server=True
    )
    monitoring_service = await initialize_monitoring_service(monitoring_config)
    
    # Setup database and scorer  
    database = await create_mock_database(seed_data=True, num_papers=100)
    scorer_config = ScorerConfig(default_tau=0.3, k_neighbours=8, personal_corpus_path="nonexistent.pkl")
    scorer = ArxivBotScorer(scorer_config, database)
    
    # Load papers
    papers = await load_real_arxiv_papers()
    logger.info(f"📋 Processing {len(papers)} papers...")
    
    # Process papers with monitoring
    start_time = time.time()
    
    try:
        # Batch process with metrics
        batch_size = 10
        total_scored = 0
        
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} papers)")
            
            batch_start = time.time()
            results = await scorer.batch_score(batch)
            batch_time = time.time() - batch_start
            
            # Update metrics (with proper labels)
            monitoring_service.metrics.papers_scored_total.inc(len(results))
            monitoring_service.metrics.harvest_duration_seconds.labels(source='arxiv').observe(batch_time)
            
            for result in results:
                monitoring_service.metrics.papers_saved_total.inc()
                if hasattr(result, 'score'):
                    monitoring_service.metrics.tau_value.set(result.score)
            
            total_scored += len(results)
            logger.info(f"  ✅ Scored {len(results)} papers in {batch_time:.2f}s ({batch_time/len(results)*1000:.1f}ms per paper)")
            
            # Small delay between batches
            await asyncio.sleep(0.5)
    
    except Exception as e:
        logger.error(f"❌ Error during processing: {e}")
        raise
    
    total_time = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info("📊 PRODUCTION TEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"Papers processed: {total_scored}")
    logger.info(f"Total time: {total_time:.2f}s")
    logger.info(f"Average per paper: {total_time/total_scored*1000:.1f}ms")
    logger.info(f"Throughput: {total_scored/total_time:.2f} papers/sec")
    
    # Show metrics endpoint
    logger.info("📈 Metrics now available at:")
    logger.info("  • http://localhost:9090/metrics")
    logger.info("  • http://localhost:3001 (Grafana)")
    logger.info("  • http://localhost:9091 (Prometheus)")
    
    # Keep server running for a bit to allow metrics scraping
    logger.info("\n⏳ Keeping metrics server running for 60 seconds...")
    logger.info("   Check metrics at http://localhost:9090/metrics")
    logger.info("   Press Ctrl+C to stop")
    
    try:
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("\n👋 Interrupted by user")
    
    # Cleanup
    await database.close()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"\n🛑 Received signal {signum}, shutting down...")
    if monitoring_service:
        asyncio.create_task(monitoring_service.stop())
    sys.exit(0)

async def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s'
    )
    
    # Suppress noisy loggers
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await run_monitoring_test()
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)
    finally:
        if monitoring_service:
            await monitoring_service.shutdown()
            logger.info("✅ Monitoring service stopped")

if __name__ == "__main__":
    asyncio.run(main())