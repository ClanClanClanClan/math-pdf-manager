#!/usr/bin/env python3
"""
Start monitoring service persistently for production validation
"""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent / "src"))

from arxivbot.monitoring.service import (
    MonitoringService,
    MonitoringServiceConfig,
    initialize_monitoring_service,
)

logger = logging.getLogger(__name__)

# Global service for cleanup
monitoring_service: Optional[MonitoringService] = None
should_stop = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global should_stop
    logger.info(f"\n🛑 Received signal {signum}, shutting down...")
    should_stop = True


async def generate_metrics_continuously():
    """Generate realistic metrics continuously"""
    global monitoring_service

    if not monitoring_service or not monitoring_service.metrics:
        return

    # Simulate realistic arxiv-bot operations
    sources = ["arxiv", "ieee", "springer"]
    models = ["gpt-4o", "claude-3-haiku", "gpt-3.5-turbo"]

    batch_num = 1
    while not should_stop:
        try:
            # Simulate a harvest batch
            source = sources[batch_num % len(sources)]
            papers_in_batch = 10 + (batch_num % 20)  # 10-30 papers per batch
            harvest_time = 2.0 + (batch_num % 10) * 0.5  # 2-7 seconds

            # Record harvest metrics
            monitoring_service.metrics.harvest_duration_seconds.labels(source=source).observe(
                harvest_time
            )
            monitoring_service.metrics.papers_scored_total.inc(papers_in_batch)
            monitoring_service.metrics.papers_saved_total.inc(papers_in_batch // 3)  # ~33% saved

            # Simulate LLM summary generation
            model = models[batch_num % len(models)]
            tokens = 800 + (batch_num % 400)  # 800-1200 tokens
            monitoring_service.metrics.summary_tokens_total.labels(model=model).inc(tokens)

            # Update tau value (varies between 0.2-0.5)
            tau = 0.2 + (batch_num % 30) * 0.01
            monitoring_service.metrics.tau_value.set(tau)

            # Simulate vector queries
            query_time = 0.05 + (batch_num % 10) * 0.02  # 50-250ms
            monitoring_service.metrics.vector_query_seconds.observe(query_time)

            logger.info(
                f"📊 Batch {batch_num}: {papers_in_batch} papers, {harvest_time:.1f}s harvest, τ={tau:.3f}"
            )
            batch_num += 1

            # Wait 30 seconds between batches
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            await asyncio.sleep(5)


async def main():
    """Main function"""
    global monitoring_service, should_stop

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s")

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("🚀 STARTING PERSISTENT MONITORING SERVICE")
    logger.info("=" * 60)

    try:
        # Initialize monitoring service
        config = MonitoringServiceConfig(
            prometheus_enabled=True, prometheus_port=9090, auto_start_server=True
        )

        monitoring_service = await initialize_monitoring_service(config)
        logger.info("✅ Monitoring service started successfully")
        logger.info("📈 Metrics available at: http://localhost:9090/metrics")

        # Start continuous metrics generation
        logger.info("🔄 Starting continuous metrics generation...")
        metrics_task = asyncio.create_task(generate_metrics_continuously())

        # Keep running until interrupted
        logger.info("⏳ Service running... Press Ctrl+C to stop")

        while not should_stop:
            await asyncio.sleep(1)

        logger.info("🛑 Stopping metrics generation...")
        metrics_task.cancel()
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass

    except Exception as e:
        logger.error(f"❌ Service failed: {e}")
        sys.exit(1)
    finally:
        if monitoring_service:
            logger.info("🔄 Shutting down monitoring service...")
            await monitoring_service.shutdown()
            logger.info("✅ Monitoring service stopped")


if __name__ == "__main__":
    asyncio.run(main())
