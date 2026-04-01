#!/usr/bin/env python3
"""
Test OpenTelemetry tracing integration with Jaeger
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up OpenTelemetry tracing
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

async def setup_tracing():
    """Initialize OpenTelemetry tracing"""
    # Create resource
    resource = Resource.create({
        "service.name": "arxiv-bot-tracer-test",
        "service.version": "2.0.0",
        "service.instance.id": "test-instance"
    })
    
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()
    
    # Create OTLP HTTP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4318/v1/traces",
        headers={}
    )
    
    # Add batch span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    logger.info("✅ OpenTelemetry tracing initialized")
    return trace.get_tracer(__name__)

async def simulate_arxiv_operations(tracer):
    """Simulate arxiv-bot operations with tracing"""
    logger.info("🔍 Simulating traced operations...")
    
    # Main harvest operation
    with tracer.start_as_current_span("Harvest/arxiv") as harvest_span:
        harvest_span.set_attribute("source", "arxiv")
        harvest_span.set_attribute("papers.fetched", 25)
        
        # Simulate fetching papers
        await asyncio.sleep(0.5)
        
        papers = [
            {"id": "2508.05564", "title": "Numerical analysis of stochastic Navier-Stokes"},
            {"id": "2508.04993", "title": "Turnpike Property of Linear-Quadratic Control"},
            {"id": "2508.05541", "title": "Disappointment Aversion and Expectiles"}
        ]
        
        for i, paper in enumerate(papers):
            # Score operation trace
            with tracer.start_as_current_span(f"Score/{paper['id']}") as score_span:
                score_span.set_attribute("paper.id", paper['id'])
                score_span.set_attribute("paper.title", paper['title'])
                score_span.set_attribute("operation", "scoring")
                
                # Simulate scoring time
                scoring_time = 0.1 + (i * 0.05)  # 100-200ms
                await asyncio.sleep(scoring_time)
                
                score = 0.3 + (i * 0.1)
                score_span.set_attribute("score.value", score)
                score_span.set_attribute("score.above_threshold", score > 0.25)
                
                if score > 0.25:
                    # Download operation trace
                    with tracer.start_as_current_span(f"Download/{paper['id']}") as download_span:
                        download_span.set_attribute("paper.id", paper['id'])
                        download_span.set_attribute("url", f"https://arxiv.org/pdf/{paper['id']}.pdf")
                        download_span.set_attribute("operation", "download")
                        
                        await asyncio.sleep(0.2)  # Simulate download
                        download_span.set_attribute("download.success", True)
                        download_span.set_attribute("download.bytes", 2048576)
                    
                    # LLM summarization trace
                    with tracer.start_as_current_span(f"LLM/{paper['id']}") as llm_span:
                        llm_span.set_attribute("paper.id", paper['id'])
                        llm_span.set_attribute("model", "gpt-4o")
                        llm_span.set_attribute("operation", "summarization")
                        
                        await asyncio.sleep(0.3)  # Simulate LLM call
                        
                        tokens_input = 1500 + (i * 200)
                        tokens_output = 300 + (i * 50)
                        
                        llm_span.set_attribute("tokens.input", tokens_input)
                        llm_span.set_attribute("tokens.output", tokens_output)
                        llm_span.set_attribute("tokens.total", tokens_input + tokens_output)
                        llm_span.set_attribute("summary.generated", True)
        
        harvest_span.set_attribute("papers.scored", len(papers))
        harvest_span.set_attribute("papers.saved", sum(1 for p in papers if 0.3 + papers.index(p) * 0.1 > 0.25))
        harvest_span.set_attribute("duration_ms", 2500)

async def verify_traces_in_jaeger():
    """Check if traces appear in Jaeger"""
    import aiohttp
    
    await asyncio.sleep(5)  # Wait for traces to be exported
    
    logger.info("🔍 Checking traces in Jaeger...")
    
    async with aiohttp.ClientSession() as session:
        # Get services
        async with session.get("http://localhost:16686/api/services") as resp:
            if resp.status == 200:
                services = await resp.json()
                service_names = [s for s in services.get('data', [])]
                logger.info(f"📋 Services in Jaeger: {service_names}")
                
                if 'arxiv-bot-tracer-test' in service_names:
                    logger.info("✅ Our service found in Jaeger!")
                    
                    # Get traces for our service
                    params = {
                        'service': 'arxiv-bot-tracer-test',
                        'limit': 20
                    }
                    
                    async with session.get("http://localhost:16686/api/traces", params=params) as trace_resp:
                        if trace_resp.status == 200:
                            traces = await trace_resp.json()
                            trace_count = len(traces.get('data', []))
                            logger.info(f"📊 Found {trace_count} traces")
                            
                            if trace_count > 0:
                                # Show details of first trace
                                first_trace = traces['data'][0]
                                spans = first_trace.get('spans', [])
                                logger.info(f"📋 First trace has {len(spans)} spans:")
                                
                                for span in spans[:5]:  # Show first 5 spans
                                    operation = span.get('operationName', 'unknown')
                                    duration = span.get('duration', 0) / 1000  # Convert to ms
                                    logger.info(f"  • {operation}: {duration:.1f}ms")
                                
                                return True
                            else:
                                logger.warning("⚠️ No traces found for our service")
                        else:
                            logger.error(f"❌ Failed to get traces: {trace_resp.status}")
                else:
                    logger.error("❌ Our service not found in Jaeger services")
            else:
                logger.error(f"❌ Failed to get Jaeger services: {resp.status}")
    
    return False

async def main():
    """Main test function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s'
    )
    
    logger.info("🚀 TESTING OPENTELEMETRY TRACING → JAEGER")
    logger.info("=" * 60)
    
    try:
        # Setup tracing
        tracer = await setup_tracing()
        
        # Send some traces
        await simulate_arxiv_operations(tracer)
        
        # Force export of spans
        tracer_provider = trace.get_tracer_provider()
        for processor in tracer_provider._active_span_processor._span_processors:
            if hasattr(processor, 'force_flush'):
                processor.force_flush(30000)  # 30 second timeout
        
        logger.info("📤 Traces exported to OTLP collector")
        
        # Verify traces appear in Jaeger
        traces_found = await verify_traces_in_jaeger()
        
        if traces_found:
            logger.info("=" * 60)
            logger.info("🎉 TRACING VALIDATION SUCCESSFUL!")
            logger.info("✅ Traces sent to OTLP collector")
            logger.info("✅ Traces forwarded to Jaeger")
            logger.info("✅ Traces visible in Jaeger UI")
            logger.info("🌐 View traces: http://localhost:16686")
            logger.info("=" * 60)
        else:
            logger.error("❌ Tracing validation failed - no traces in Jaeger")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Tracing test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())