#!/usr/bin/env python3
"""
Test the complete local LLM ArXiv Bot system
"""

import asyncio
import sys

sys.path.insert(0, 'src')

from arxiv_local_complete import ArXivLocalBot


async def test_complete_system():
    """Test the full system without user interaction"""
    
    print("🧪 TESTING COMPLETE LOCAL LLM ARXIV SYSTEM")
    print("="*50)
    
    # Initialize bot
    bot = ArXivLocalBot()
    
    # Test with a specific research query
    query = "machine learning transformers attention mechanisms"
    
    print(f"🔍 Query: {query}")
    
    try:
        # Run the complete pipeline
        result = await bot.process_daily_papers(query)
        
        print("\n🎉 SYSTEM TEST RESULTS:")
        print("="*30)
        print(f"✅ Papers processed: {result['stats']['processed']}")
        print(f"📊 Average local score: {result['stats']['avg_score']:.1%}")
        print(f"🤖 Average LLM score: {result['stats']['avg_llm_score']:.1f}/10")
        
        # Show sample results
        if result['results']:
            print(f"\n📝 SAMPLE ANALYSIS:")
            sample = result['results'][0]
            print(f"Paper: {sample['paper'].title[:50]}...")
            print(f"Local Score: {sample['local_score']:.1%}")
            print(f"LLM Summary: {sample['llm_analysis'].get('summary', 'N/A')[:100]}...")
            print(f"Relevance Score: {sample['llm_analysis'].get('score', 'N/A')}/10")
        
        await bot.close()
        
        print(f"\n✅ COMPLETE SYSTEM WORKING!")
        print(f"📁 Results saved to: ./daily_batches/local_llm/")
        print(f"📄 Digest saved to: ./daily_batches/digests/")
        
        return True
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        import traceback
        traceback.print_exc()
        await bot.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_complete_system())
    exit(0 if success else 1)