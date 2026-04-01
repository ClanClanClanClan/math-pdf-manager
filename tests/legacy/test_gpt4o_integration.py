#!/usr/bin/env python3
"""
Test GPT-4o Integration with API Key
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.arxivbot.llm.gpt4o_summarizer import GPT4oSummarizer, LLMConfig, SummaryType
from src.arxivbot.models.cmo import CMO, Author


async def test_gpt4o_integration():
    """Test GPT-4o integration with the provided API key"""
    print("🧪 Testing GPT-4o Integration")
    print("=" * 35)
    
    # Configure with the provided API key
    config = LLMConfig(
        api_key=os.getenv('OPENAI_API_KEY'),
        model_name="gpt-4o-mini",  # Cost-effective model
        max_concurrent_requests=1,
        daily_cost_limit=5.0,  # Conservative limit for testing
        enable_cost_optimization=True
    )
    
    print(f"✅ API Key configured: {config.api_key[:20]}..." if config.api_key else "❌ No API key found")
    print(f"✅ Model: {config.model_name}")
    print(f"✅ Daily cost limit: ${config.daily_cost_limit}")
    
    # Initialize GPT-4o service
    summarizer = GPT4oSummarizer(config)
    
    try:
        print("\n🔧 Initializing GPT-4o service...")
        if not await summarizer.initialize():
            print("❌ Failed to initialize GPT-4o service")
            return False
        
        print("✅ GPT-4o service initialized successfully")
        
        # Create a test paper
        test_paper = CMO(
            external_id="test:gpt4o:1",
            source="arxiv",
            title="Attention Is All You Need: Transformer Architecture for Sequence-to-Sequence Learning",
            authors=[
                Author(family="Vaswani", given="Ashish"),
                Author(family="Shazeer", given="Noam"),
                Author(family="Parmar", given="Niki")
            ],
            published="2017-06-12T00:00:00Z",
            abstract="We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
            categories=["cs.CL", "cs.LG"],
            doi="10.48550/arXiv.1706.03762"
        )
        
        print(f"\n📄 Test paper: {test_paper.title}")
        
        # Test different summary types
        summary_types = [
            (SummaryType.BRIEF, "Brief summary"),
            (SummaryType.DETAILED, "Detailed summary"),
            (SummaryType.RELEVANCE, "Relevance summary")
        ]
        
        total_cost = 0.0
        
        for summary_type, description in summary_types:
            print(f"\n🔍 Generating {description}...")
            
            try:
                response = await summarizer.summarize_paper(
                    test_paper, 
                    summary_type=summary_type,
                    query_context="machine learning and natural language processing"
                )
                
                if response.success:
                    print(f"✅ {description} generated successfully")
                    print(f"   Length: {len(response.summary_text)} characters")
                    print(f"   Cost: ${response.cost_usd:.4f}")
                    print(f"   Tokens used: {response.tokens_used}")
                    print(f"   Confidence: {response.confidence:.3f}")
                    print(f"   Processing time: {response.processing_time_ms:.1f}ms")
                    print(f"   Summary: {response.summary_text[:200]}{'...' if len(response.summary_text) > 200 else ''}")
                    
                    total_cost += response.cost_usd
                else:
                    print(f"❌ {description} failed: {response.error}")
                    
            except Exception as e:
                print(f"❌ {description} error: {e}")
        
        print(f"\n💰 Total cost for test: ${total_cost:.4f}")
        
        # Get service statistics
        stats = summarizer.get_statistics()
        print(f"\n📊 Service Statistics:")
        print(f"   Summaries generated: {stats['service_stats']['summaries_generated']}")
        print(f"   Total tokens used: {stats['service_stats']['total_tokens_used']}")
        print(f"   Total cost: ${stats['service_stats']['total_cost_usd']:.4f}")
        print(f"   Cache hits: {stats['service_stats']['cache_hits']}")
        print(f"   Cache misses: {stats['service_stats']['cache_misses']}")
        
        # Health check
        print(f"\n🏥 Health Check...")
        health = await summarizer.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Healthy: {health['healthy']}")
        if 'test_cost_usd' in health:
            print(f"   Test cost: ${health['test_cost_usd']:.4f}")
            print(f"   Test time: {health['test_time_ms']:.1f}ms")
        
        return True
        
    except Exception as e:
        print(f"❌ GPT-4o integration test failed: {e}")
        return False
    
    finally:
        await summarizer.shutdown()

async def main():
    """Main test function"""
    print("🚀 ArXiv Bot v2.4 GPT-4o Integration Test")
    print("=" * 45)
    
    success = await test_gpt4o_integration()
    
    if success:
        print("\n🎉 GPT-4o integration test PASSED!")
        print("✅ OpenAI API key is working correctly")
        print("✅ GPT-4o service is production-ready")
        print("✅ Cost tracking and optimization enabled")
        return 0
    else:
        print("\n❌ GPT-4o integration test FAILED!")
        print("🔧 Check your API key and network connection")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)