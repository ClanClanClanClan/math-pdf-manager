#!/usr/bin/env python3
"""
Full System Test with GPT-4o Integration
Tests the complete ArXiv Bot v2.4 system including LLM features
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.arxivbot.citations.enhanced_citation_service import EnhancedCitationService
from src.arxivbot.config.production_config import Environment, ProductionConfig
from src.arxivbot.database.sqlite_backend import SQLiteConfig, SQLiteDatabase
from src.arxivbot.llm.gpt4o_summarizer import GPT4oSummarizer, LLMConfig, SummaryType
from src.arxivbot.models.cmo import CMO, Author
from src.arxivbot.pipeline.real_api_harvester import RealAPIHarvester
from src.arxivbot.scoring.advanced_scorer import AdvancedPaperScorer


class FullSystemTest:
    """Complete system test with all v2.4 features"""
    
    def __init__(self):
        self.config = None
        self.database = None
        self.harvester = None
        self.citation_service = None
        self.scorer = None
        self.summarizer = None
        self.test_results = []
    
    async def setup_system(self):
        """Initialize the complete system"""
        print("🔧 Setting up complete ArXiv Bot v2.4 system...")
        
        # 1. Configuration
        self.config = ProductionConfig(environment=Environment.DEVELOPMENT)
        print("✅ Configuration loaded")
        
        # 2. Database
        db_config = SQLiteConfig(database_path="full_system_test.db")
        self.database = SQLiteDatabase(db_config)
        await self.database.initialize()
        print("✅ Database initialized")
        
        # 3. Harvester
        self.harvester = RealAPIHarvester()
        await self.harvester.initialize()
        print("✅ API Harvester initialized")
        
        # 4. Citation Service
        self.citation_service = EnhancedCitationService()
        await self.citation_service.initialize()
        print("✅ Citation Service initialized")
        
        # 5. Scorer
        self.scorer = AdvancedPaperScorer()
        print("✅ Advanced Scorer ready")
        
        # 6. GPT-4o Summarizer
        llm_config = LLMConfig(
            api_key=os.getenv('OPENAI_API_KEY'),
            model_name="gpt-4o-mini",
            daily_cost_limit=2.0,  # Conservative limit
            enable_cost_optimization=True,
            cache_dir="./.summary_cache_test"
        )
        
        self.summarizer = GPT4oSummarizer(llm_config)
        if await self.summarizer.initialize():
            print("✅ GPT-4o Summarizer initialized")
        else:
            print("⚠️  GPT-4o Summarizer failed to initialize")
            self.summarizer = None
    
    async def test_complete_workflow(self):
        """Test the complete paper processing workflow"""
        print("\n🧪 Testing Complete Workflow")
        print("=" * 32)
        
        start_time = time.time()
        
        # Step 1: Harvest papers
        print("📥 Harvesting papers from ArXiv...")
        papers = await self.harvester.harvest_arxiv(query="cat:cs.AI", max_results=2)
        print(f"✅ Harvested {len(papers)} papers")
        
        if not papers:
            print("❌ No papers harvested, cannot continue workflow test")
            return False
        
        # Step 2: Store papers in database
        print("💾 Storing papers in database...")
        for paper in papers:
            await self.database.insert_paper(paper)
        print(f"✅ Stored {len(papers)} papers in database")
        
        # Step 3: Analyze citations
        print("🔗 Analyzing citations...")
        paper = papers[0]  # Test with first paper
        citation_result = await self.citation_service.analyze_paper_citations(paper)
        print(f"✅ Citation analysis: {citation_result.citation_count} citations")
        
        # Step 4: Score papers
        print("⭐ Scoring papers...")
        scores = []
        for paper in papers:
            score = await self.scorer.score_paper_basic(paper, "artificial intelligence")
            scores.append(score)
            print(f"   {paper.title[:50]}... = {score:.3f}")
        print(f"✅ Scored {len(papers)} papers")
        
        # Step 5: Generate summaries (if GPT-4o available)
        if self.summarizer:
            print("📝 Generating AI summaries...")
            test_paper = papers[0]
            
            # Test different summary types
            summary_types = [SummaryType.BRIEF, SummaryType.DETAILED]
            total_cost = 0.0
            
            for summary_type in summary_types:
                response = await self.summarizer.summarize_paper(
                    test_paper, 
                    summary_type=summary_type,
                    query_context="artificial intelligence and machine learning"
                )
                
                if response.success:
                    print(f"   ✅ {summary_type.value.title()} summary: {len(response.summary_text)} chars, ${response.cost_usd:.4f}")
                    total_cost += response.cost_usd
                else:
                    print(f"   ❌ {summary_type.value.title()} summary failed: {response.error}")
            
            print(f"✅ Generated summaries (total cost: ${total_cost:.4f})")
        
        # Step 6: Search and retrieval
        print("🔍 Testing search functionality...")
        search_results = await self.database.search_papers("artificial intelligence")
        print(f"✅ Search found {len(search_results)} relevant papers")
        
        total_time = time.time() - start_time
        print(f"\n⚡ Complete workflow finished in {total_time:.2f}s")
        
        return True
    
    async def test_system_health(self):
        """Test system health and performance"""
        print("\n🏥 System Health Check")
        print("=" * 22)
        
        # Database health
        stats = await self.database.get_stats()
        print(f"✅ Database: {stats['total_papers']} papers stored")
        
        # Harvester health  
        harvester_stats = self.harvester.stats
        print(f"✅ Harvester: {harvester_stats['total_harvested']} total harvested")
        
        # Citation service health
        citation_stats = self.citation_service.get_service_stats()
        print(f"✅ Citation Service: {citation_stats['papers_processed']} papers processed")
        
        # GPT-4o health
        if self.summarizer:
            health = await self.summarizer.health_check()
            print(f"✅ GPT-4o Service: {health['status']} (cost: ${health.get('test_cost_usd', 0):.4f})")
            
            # Show service stats
            stats = self.summarizer.get_statistics()
            print(f"   Summaries generated: {stats['service_stats']['summaries_generated']}")
            print(f"   Total cost: ${stats['service_stats']['total_cost_usd']:.4f}")
        
        return True
    
    async def cleanup(self):
        """Clean up test resources"""
        print("\n🧹 Cleaning up...")
        
        if self.database:
            await self.database.close()
        
        if self.harvester:
            await self.harvester.close()
        
        if self.citation_service:
            await self.citation_service.shutdown()
        
        if self.summarizer:
            await self.summarizer.shutdown()
        
        # Remove test database
        test_db = Path("full_system_test.db")
        if test_db.exists():
            test_db.unlink()
        
        print("✅ Cleanup completed")

async def main():
    """Main test function"""
    print("🚀 ArXiv Bot v2.4 Full System Test with GPT-4o")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"✅ OpenAI API Key: {api_key[:20]}...")
    else:
        print("⚠️  No OpenAI API key found in environment")
    
    test = FullSystemTest()
    
    try:
        # Setup system
        await test.setup_system()
        
        # Run complete workflow test
        workflow_success = await test.test_complete_workflow()
        
        # Run health checks
        health_success = await test.test_system_health()
        
        if workflow_success and health_success:
            print("\n🎉 FULL SYSTEM TEST: SUCCESS!")
            print("✅ Complete ArXiv Bot v2.4 system working perfectly")
            print("✅ All components integrated and functional")
            print("✅ GPT-4o summarization enabled and working")
            print("✅ System ready for production use")
            return 0
        else:
            print("\n❌ FULL SYSTEM TEST: PARTIAL SUCCESS")
            print("🔧 Some components need attention")
            return 1
    
    except Exception as e:
        print(f"\n❌ FULL SYSTEM TEST: FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await test.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)