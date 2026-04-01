#!/usr/bin/env python3
"""
Quick Validation Test - Prove what ACTUALLY works
No claims, just facts
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

logger = logging.getLogger(__name__)

async def test_metrics_endpoint():
    """Test if metrics endpoint actually works"""
    import aiohttp
    
    urls = [
        "http://localhost:9090/metrics",  # arxiv-bot
        "http://localhost:9091/metrics",  # Prometheus
        "http://localhost:9098/metrics",  # Test port
        "http://localhost:9099/metrics",  # Load test port
    ]
    
    logger.info("🌐 Testing metrics endpoints...")
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        if "papers_scored_total" in text:
                            logger.info(f"✅ {url} - WORKING (found metrics)")
                        else:
                            logger.info(f"⚠️ {url} - UP but no arxiv-bot metrics")
                    else:
                        logger.info(f"❌ {url} - Status {resp.status}")
            except Exception as e:
                logger.info(f"❌ {url} - NOT ACCESSIBLE ({type(e).__name__})")

async def test_otlp_collector():
    """Test if OTLP collector is running"""
    import aiohttp
    
    urls = [
        "http://localhost:4317",  # gRPC (won't work with HTTP)
        "http://localhost:4318",  # HTTP
        "http://localhost:13133",  # Health check
    ]
    
    logger.info("\n🔍 Testing OTLP collector...")
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    logger.info(f"✅ {url} - Status {resp.status}")
            except Exception as e:
                logger.info(f"❌ {url} - NOT RUNNING ({type(e).__name__})")

async def test_docker():
    """Test if Docker is available"""
    import subprocess
    
    logger.info("\n🐳 Testing Docker...")
    
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            logger.info(f"✅ Docker installed: {result.stdout.strip()}")
            
            # Check if daemon is running
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                logger.info("✅ Docker daemon running")
            else:
                logger.error("❌ Docker daemon not running")
        else:
            logger.error("❌ Docker command failed")
    except FileNotFoundError:
        logger.error("❌ Docker not installed")
    except Exception as e:
        logger.error(f"❌ Docker check failed: {e}")

async def test_monitoring_config():
    """Test if monitoring configs are valid"""
    import json

    import yaml
    
    logger.info("\n📄 Testing configuration files...")
    
    configs = [
        ("infrastructure/docker-compose.monitoring.yml", "yaml"),
        ("infrastructure/otel-collector.yml", "yaml"),
        ("infrastructure/prometheus.yml", "yaml"),
        ("infrastructure/alert.rules.yml", "yaml"),
        ("infrastructure/alertmanager.yml", "yaml"),
        ("infrastructure/grafana/dashboards/arxivbot-overview.json", "json"),
    ]
    
    for filepath, format in configs:
        try:
            path = Path(filepath)
            if path.exists():
                with open(path) as f:
                    if format == "yaml":
                        yaml.safe_load(f)
                        logger.info(f"✅ {filepath} - Valid YAML")
                    else:
                        json.load(f)
                        logger.info(f"✅ {filepath} - Valid JSON")
            else:
                logger.error(f"❌ {filepath} - FILE NOT FOUND")
        except Exception as e:
            logger.error(f"❌ {filepath} - INVALID: {e}")

async def test_actual_performance():
    """Test actual scoring performance with real timing"""
    from mathpdf.arxivbot.models.cmo import CMO, Author
    from mathpdf.arxivbot.scorer import ArxivBotScorer, ScorerConfig
    from mathpdf.arxivbot.testing.mock_database import create_mock_database
    
    logger.info("\n⚡ Testing ACTUAL scoring performance...")
    
    # Create test papers
    papers = []
    for i in range(10):
        paper = CMO(
            external_id=f"perf:{i:03d}",
            source="test",
            title=f"Performance Test Paper {i}",
            authors=[Author(family=f"Test{i}", given="Author")],
            published="2024-01-01",
            abstract="Test abstract for performance measurement. " * 20,
            pdf_url=f"https://test.com/{i}.pdf",
            categories=["math.OC"],
            doi=None
        )
        papers.append(paper)
    
    # Setup
    database = await create_mock_database(seed_data=True, num_papers=50)
    config = ScorerConfig(default_tau=0.3, k_neighbours=8, personal_corpus_path="nonexistent.pkl")
    scorer = ArxivBotScorer(config, database)
    
    # Time the scoring
    start = time.time()
    results = await scorer.batch_score(papers)
    elapsed = time.time() - start
    
    per_paper_ms = (elapsed / len(papers)) * 1000
    
    logger.info(f"📊 REAL Performance Results:")
    logger.info(f"  Papers scored: {len(results)}")
    logger.info(f"  Total time: {elapsed:.2f}s")
    logger.info(f"  Per paper: {per_paper_ms:.1f}ms")
    
    if per_paper_ms < 100:
        logger.info(f"✅ MEETS <100ms target")
    else:
        logger.error(f"❌ FAILS <100ms target ({per_paper_ms:.1f}ms > 100ms)")
    
    await database.close()

async def main():
    """Run all validation tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Suppress noisy loggers
    logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
    logging.getLogger('transformers').setLevel(logging.ERROR)
    logging.getLogger('arxivbot').setLevel(logging.WARNING)
    
    logger.info("=" * 60)
    logger.info("🔬 VALIDATION TEST - What ACTUALLY Works")
    logger.info("=" * 60)
    
    await test_metrics_endpoint()
    await test_otlp_collector()
    await test_docker()
    await test_monitoring_config()
    await test_actual_performance()
    
    logger.info("\n" + "=" * 60)
    logger.info("📋 VALIDATION COMPLETE - These are FACTS, not claims")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())