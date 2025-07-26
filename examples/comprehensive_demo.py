#!/usr/bin/env python3
"""
Comprehensive Academic Paper Management System Demo
Demonstrates the complete workflow from search to download to analysis.
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from downloader.orchestrator import DownloadOrchestrator
from metadata.enhanced_sources import EnhancedMetadataOrchestrator, EnhancedMetadata
from metadata.quality_scoring import MetadataQualityScorer, SourceRankingSystem
from async_metadata_fetcher import AsyncMetadataFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveAcademicManager:
    """
    Complete academic paper management system integrating all components.
    
    Features:
    - Multi-source metadata search and retrieval
    - Quality scoring and source ranking
    - Intelligent download orchestration
    - Citation network analysis
    - Performance monitoring and analytics
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.download_orchestrator = DownloadOrchestrator(str(self.config_dir))
        self.metadata_orchestrator = EnhancedMetadataOrchestrator()
        self.quality_scorer = MetadataQualityScorer()
        self.source_ranking = SourceRankingSystem()
        
        # Statistics
        self.session_stats = {
            'searches_performed': 0,
            'papers_found': 0,
            'downloads_attempted': 0,
            'downloads_successful': 0,
            'quality_scores': [],
            'sources_used': {},
            'processing_times': []
        }
    
    async def initialize(self, master_password: str, 
                        semantic_scholar_key: str = None,
                        openalex_email: str = None):
        """Initialize all components with credentials"""
        logger.info("Initializing Academic Paper Management System...")
        
        # Initialize download orchestrator
        success = await self.download_orchestrator.initialize(master_password)
        if not success:
            raise RuntimeError("Failed to initialize download orchestrator")
        
        # Configure metadata orchestrator
        if semantic_scholar_key:
            self.metadata_orchestrator.semantic_scholar_key = semantic_scholar_key
        if openalex_email:
            self.metadata_orchestrator.openalex_email = openalex_email
        
        logger.info("System initialized successfully")
        return True
    
    async def comprehensive_search(self, queries: List[str], 
                                 max_results_per_query: int = 20) -> List[EnhancedMetadata]:
        """
        Perform comprehensive search across all metadata sources
        with quality scoring and ranking.
        """
        logger.info(f"Starting comprehensive search for {len(queries)} queries...")
        
        all_results = []
        
        for query in queries:
            self.session_stats['searches_performed'] += 1
            
            logger.info(f"Searching for: '{query}'")
            
            # Search using enhanced metadata orchestrator
            results = await self.metadata_orchestrator.comprehensive_search(
                query, max_results_per_query
            )
            
            # Score each result
            scored_results = []
            for result in results:
                quality_metrics = self.quality_scorer.score_metadata(result)
                result.quality_score = quality_metrics.overall_score
                scored_results.append(result)
                
                # Update session statistics
                self.session_stats['quality_scores'].append(quality_metrics.overall_score)
                source = result.source or 'unknown'
                self.session_stats['sources_used'][source] = \
                    self.session_stats['sources_used'].get(source, 0) + 1
            
            # Sort by quality score
            scored_results.sort(key=lambda x: x.quality_score, reverse=True)
            all_results.extend(scored_results)
            
            logger.info(f"Found {len(results)} papers for query '{query}'")
        
        self.session_stats['papers_found'] += len(all_results)
        
        # Final sort and deduplication
        unique_results = self._deduplicate_results(all_results)
        unique_results.sort(key=lambda x: x.quality_score, reverse=True)
        
        logger.info(f"Total unique papers found: {len(unique_results)}")
        return unique_results
    
    def _deduplicate_results(self, results: List[EnhancedMetadata]) -> List[EnhancedMetadata]:
        """Remove duplicate papers based on DOI and title similarity"""
        seen_dois = set()
        seen_titles = set()
        unique_results = []
        
        for result in results:
            # Check DOI first (most reliable)
            if result.DOI:
                if result.DOI in seen_dois:
                    continue
                seen_dois.add(result.DOI)
            
            # Check title similarity
            title_key = result.title.lower().strip() if result.title else ""
            if title_key and title_key in seen_titles:
                continue
            if title_key:
                seen_titles.add(title_key)
            
            unique_results.append(result)
        
        return unique_results
    
    async def intelligent_download(self, papers: List[EnhancedMetadata],
                                 save_directory: str = "downloads",
                                 max_concurrent: int = 3) -> Dict[str, Any]:
        """
        Intelligently download papers using all available sources
        with fallback strategies and quality tracking.
        """
        logger.info(f"Starting intelligent download of {len(papers)} papers...")
        
        self.session_stats['downloads_attempted'] += len(papers)
        
        # Create download plans
        download_plans = await self.download_orchestrator.create_download_plan(papers)
        
        # Execute batch download
        batch_result = await self.download_orchestrator.download_batch(
            papers, max_concurrent=max_concurrent, save_directory=save_directory
        )
        
        # Update statistics
        self.session_stats['downloads_successful'] += batch_result.successful_downloads
        
        # Analyze download performance by source
        source_performance = {}
        for result in batch_result.results:
            if result.success:
                source = result.source or 'unknown'
                if source not in source_performance:
                    source_performance[source] = {'successful': 0, 'total': 0, 'avg_time': 0.0}
                
                source_performance[source]['successful'] += 1
                source_performance[source]['total'] += 1
                source_performance[source]['avg_time'] += result.download_time
            else:
                # Track failed attempts
                for source_name in self.download_orchestrator.universal_downloader.strategies.keys():
                    if source_name not in source_performance:
                        source_performance[source_name] = {'successful': 0, 'total': 0, 'avg_time': 0.0}
                    source_performance[source_name]['total'] += 1
        
        # Calculate average times
        for source_data in source_performance.values():
            if source_data['successful'] > 0:
                source_data['avg_time'] /= source_data['successful']
        
        # Update source rankings based on performance
        self._update_source_rankings(batch_result.results)
        
        return {
            'batch_result': batch_result,
            'source_performance': source_performance,
            'download_plans': download_plans
        }
    
    def _update_source_rankings(self, download_results: List[Any]):
        """Update source rankings based on download performance"""
        source_data = {}
        
        for result in download_results:
            source = result.source or 'unknown'
            if source not in source_data:
                source_data[source] = {'results': [], 'times': []}
            
            # Create dummy metadata for ranking update
            dummy_metadata = EnhancedMetadata(
                title=f"Downloaded paper",
                source=source,
                quality_score=0.8 if result.success else 0.2
            )
            
            source_data[source]['results'].append(dummy_metadata)
            source_data[source]['times'].append(result.download_time)
        
        # Update rankings
        for source, data in source_data.items():
            self.source_ranking.update_source_ranking(
                source, data['results'], data['times']
            )
    
    async def analyze_citation_network(self, papers: List[EnhancedMetadata],
                                     depth: int = 1) -> Dict[str, Any]:
        """
        Analyze citation networks for a set of papers.
        Find related papers, influential citations, and research trends.
        """
        logger.info(f"Analyzing citation network for {len(papers)} papers...")
        
        citation_network = {
            'nodes': [],  # Papers
            'edges': [],  # Citations
            'clusters': [],  # Research clusters
            'influential_papers': [],
            'trends': {}
        }
        
        # Build network from papers with Semantic Scholar IDs
        papers_with_s2_ids = [p for p in papers if p.s2_paper_id]
        
        if not papers_with_s2_ids:
            logger.warning("No papers with Semantic Scholar IDs found for citation analysis")
            return citation_network
        
        # Use async metadata fetcher for citation data
        async with AsyncMetadataFetcher() as fetcher:
            for paper in papers_with_s2_ids[:5]:  # Limit for demo
                # Add paper as node
                citation_network['nodes'].append({
                    'id': paper.s2_paper_id,
                    'title': paper.title,
                    'authors': paper.authors,
                    'citation_count': paper.citation_count,
                    'year': paper.published[:4] if paper.published else None,
                    'quality_score': paper.quality_score
                })
                
                # Get citations if available (would need Semantic Scholar API integration)
                # For now, just demonstrate the structure
                
                # Analyze trends from fields of study
                for field in paper.fields_of_study or []:
                    citation_network['trends'][field] = \
                        citation_network['trends'].get(field, 0) + 1
        
        # Identify influential papers
        citation_network['influential_papers'] = sorted(
            [p for p in papers if p.citation_count > 50],
            key=lambda x: x.citation_count,
            reverse=True
        )[:10]
        
        logger.info("Citation network analysis completed")
        return citation_network
    
    def generate_comprehensive_report(self, papers: List[EnhancedMetadata],
                                    download_results: Dict[str, Any] = None,
                                    citation_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        
        report = {
            'session_summary': self._generate_session_summary(),
            'paper_analysis': self._analyze_paper_set(papers),
            'quality_analysis': self._analyze_quality_distribution(papers),
            'source_analysis': self._analyze_source_performance(),
            'recommendations': self._generate_recommendations(papers)
        }
        
        if download_results:
            report['download_analysis'] = self._analyze_download_performance(download_results)
        
        if citation_analysis:
            report['citation_analysis'] = citation_analysis
        
        return report
    
    def _generate_session_summary(self) -> Dict[str, Any]:
        """Generate session summary statistics"""
        avg_quality = (sum(self.session_stats['quality_scores']) / 
                      len(self.session_stats['quality_scores'])) \
                      if self.session_stats['quality_scores'] else 0.0
        
        return {
            'searches_performed': self.session_stats['searches_performed'],
            'papers_found': self.session_stats['papers_found'],
            'downloads_attempted': self.session_stats['downloads_attempted'],
            'downloads_successful': self.session_stats['downloads_successful'],
            'download_success_rate': (self.session_stats['downloads_successful'] / 
                                    max(1, self.session_stats['downloads_attempted'])),
            'average_quality_score': avg_quality,
            'sources_used': self.session_stats['sources_used']
        }
    
    def _analyze_paper_set(self, papers: List[EnhancedMetadata]) -> Dict[str, Any]:
        """Analyze the set of papers found"""
        if not papers:
            return {'error': 'No papers to analyze'}
        
        # Year distribution
        years = []
        for paper in papers:
            if paper.published:
                try:
                    year = int(paper.published[:4])
                    years.append(year)
                except (ValueError, IndexError):
                    pass
        
        year_dist = {}
        for year in years:
            year_dist[str(year)] = year_dist.get(str(year), 0) + 1
        
        # Field distribution
        field_dist = {}
        for paper in papers:
            for field in paper.fields_of_study or []:
                field_dist[field] = field_dist.get(field, 0) + 1
        
        # Citation statistics
        citations = [p.citation_count for p in papers if p.citation_count >= 0]
        
        return {
            'total_papers': len(papers),
            'papers_with_abstracts': sum(1 for p in papers if p.abstract),
            'papers_with_dois': sum(1 for p in papers if p.DOI),
            'papers_open_access': sum(1 for p in papers if p.open_access),
            'year_distribution': year_dist,
            'field_distribution': dict(sorted(field_dist.items(), 
                                            key=lambda x: x[1], reverse=True)[:10]),
            'citation_stats': {
                'total_citations': sum(citations) if citations else 0,
                'average_citations': sum(citations) / len(citations) if citations else 0,
                'max_citations': max(citations) if citations else 0,
                'highly_cited_papers': sum(1 for c in citations if c > 100)
            }
        }
    
    def _analyze_quality_distribution(self, papers: List[EnhancedMetadata]) -> Dict[str, Any]:
        """Analyze quality score distribution"""
        scores = [p.quality_score for p in papers if hasattr(p, 'quality_score')]
        
        if not scores:
            return {'error': 'No quality scores available'}
        
        # Quality brackets
        excellent = sum(1 for s in scores if s >= 0.8)
        good = sum(1 for s in scores if 0.6 <= s < 0.8)
        fair = sum(1 for s in scores if 0.4 <= s < 0.6)
        poor = sum(1 for s in scores if s < 0.4)
        
        return {
            'average_quality': sum(scores) / len(scores),
            'quality_distribution': {
                'excellent': excellent,
                'good': good,
                'fair': fair,
                'poor': poor
            },
            'top_quality_papers': sorted(papers, key=lambda x: getattr(x, 'quality_score', 0), 
                                       reverse=True)[:5]
        }
    
    def _analyze_source_performance(self) -> Dict[str, Any]:
        """Analyze performance of different sources"""
        rankings = self.source_ranking.get_ranked_sources()
        
        return {
            'top_sources': [(r.source_name, r.overall_ranking) for r in rankings[:5]],
            'source_details': {r.source_name: self.source_ranking.get_source_analysis(r.source_name) 
                             for r in rankings[:3]}
        }
    
    def _analyze_download_performance(self, download_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze download performance"""
        batch_result = download_results['batch_result']
        
        return {
            'success_rate': batch_result.success_rate,
            'throughput': batch_result.throughput_papers_per_minute,
            'total_size_mb': batch_result.total_size_mb,
            'source_breakdown': batch_result.source_breakdown,
            'error_summary': batch_result.error_summary,
            'performance_by_source': download_results['source_performance']
        }
    
    def _generate_recommendations(self, papers: List[EnhancedMetadata]) -> Dict[str, Any]:
        """Generate recommendations for future searches and downloads"""
        recommendations = {
            'search_recommendations': [],
            'quality_improvements': [],
            'source_recommendations': []
        }
        
        # Analyze current results to make recommendations
        if papers:
            # Field diversity recommendation
            fields = set()
            for paper in papers:
                fields.update(paper.fields_of_study or [])
            
            if len(fields) < 3:
                recommendations['search_recommendations'].append(
                    "Consider broadening search terms to discover papers from related fields"
                )
            
            # Quality recommendations
            avg_quality = sum(getattr(p, 'quality_score', 0) for p in papers) / len(papers)
            if avg_quality < 0.6:
                recommendations['quality_improvements'].append(
                    "Consider using more specific search terms to find higher quality papers"
                )
            
            # Source recommendations
            top_sources = self.source_ranking.recommend_sources('general')
            recommendations['source_recommendations'] = top_sources[:3]
        
        return recommendations
    
    async def cleanup(self):
        """Clean up resources"""
        if hasattr(self.download_orchestrator, 'close'):
            await self.download_orchestrator.close()

async def comprehensive_demo():
    """
    Comprehensive demonstration of the academic paper management system.
    """
    print("🚀 Academic Paper Management System - Comprehensive Demo")
    print("=" * 60)
    
    # Initialize system
    manager = ComprehensiveAcademicManager()
    
    # Note: In real usage, you'd provide actual credentials
    await manager.initialize(
        master_password="demo_password_123",
        semantic_scholar_key=None,  # Add your API key
        openalex_email="demo@example.com"  # Add your email
    )
    
    try:
        # Demo 1: Comprehensive Search
        print("\n📚 Demo 1: Comprehensive Metadata Search")
        print("-" * 40)
        
        search_queries = [
            "transformer neural networks attention mechanism",
            "quantum computing machine learning"
        ]
        
        papers = await manager.comprehensive_search(search_queries, max_results_per_query=5)
        
        print(f"Found {len(papers)} unique papers")
        
        # Show top 3 papers
        for i, paper in enumerate(papers[:3], 1):
            print(f"\n{i}. {paper.title}")
            print(f"   Authors: {', '.join(paper.authors[:2])}{'...' if len(paper.authors) > 2 else ''}")
            print(f"   Quality Score: {getattr(paper, 'quality_score', 0):.3f}")
            print(f"   Citations: {paper.citation_count}")
            print(f"   Source: {paper.source}")
            if paper.venue:
                print(f"   Venue: {paper.venue}")
        
        # Demo 2: Quality Analysis
        print("\n🎯 Demo 2: Quality Analysis")
        print("-" * 40)
        
        quality_scores = [getattr(p, 'quality_score', 0) for p in papers]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            print(f"Average Quality Score: {avg_quality:.3f}")
            
            excellent = sum(1 for s in quality_scores if s >= 0.8)
            good = sum(1 for s in quality_scores if 0.6 <= s < 0.8)
            fair = sum(1 for s in quality_scores if 0.4 <= s < 0.6)
            poor = sum(1 for s in quality_scores if s < 0.4)
            
            print(f"Quality Distribution:")
            print(f"  Excellent (≥0.8): {excellent}")
            print(f"  Good (0.6-0.8): {good}")
            print(f"  Fair (0.4-0.6): {fair}")
            print(f"  Poor (<0.4): {poor}")
        
        # Demo 3: Source Rankings
        print("\n🏆 Demo 3: Source Performance Rankings")
        print("-" * 40)
        
        top_sources = manager.source_ranking.get_ranked_sources()
        for i, source in enumerate(top_sources[:5], 1):
            print(f"{i}. {source.source_name}")
            print(f"   Overall Ranking: {source.overall_ranking:.3f}")
            print(f"   Reliability: {source.reliability_score:.3f}")
            print(f"   Coverage: {source.coverage_score:.3f}")
            if source.strength_areas:
                print(f"   Strengths: {', '.join(source.strength_areas[:2])}")
        
        # Demo 4: Download Simulation (without actual downloads)
        print("\n⬇️ Demo 4: Download Planning")
        print("-" * 40)
        
        if papers:
            # Create download plans without executing
            download_plans = await manager.download_orchestrator.create_download_plan(papers[:3])
            
            for i, plan in enumerate(download_plans, 1):
                print(f"\nPaper {i}: {plan.query[:50]}...")
                print(f"  Primary Sources: {', '.join(plan.primary_sources)}")
                print(f"  Fallback Sources: {', '.join(plan.fallback_sources[:2])}")
                print(f"  Estimated Success Rate: {plan.estimated_success_rate:.1%}")
        
        # Demo 5: Citation Network Analysis
        print("\n🕸️ Demo 5: Citation Network Analysis")
        print("-" * 40)
        
        citation_analysis = await manager.analyze_citation_network(papers[:5])
        
        print(f"Network Nodes: {len(citation_analysis['nodes'])}")
        print(f"Research Trends: {len(citation_analysis['trends'])}")
        
        if citation_analysis['trends']:
            top_trends = sorted(citation_analysis['trends'].items(), 
                              key=lambda x: x[1], reverse=True)[:5]
            print("Top Research Areas:")
            for field, count in top_trends:
                print(f"  {field}: {count} papers")
        
        # Demo 6: Comprehensive Report
        print("\n📊 Demo 6: Comprehensive Analysis Report")
        print("-" * 40)
        
        report = manager.generate_comprehensive_report(papers, None, citation_analysis)
        
        session_summary = report['session_summary']
        print(f"Session Summary:")
        print(f"  Searches: {session_summary['searches_performed']}")
        print(f"  Papers Found: {session_summary['papers_found']}")
        print(f"  Average Quality: {session_summary['average_quality_score']:.3f}")
        
        paper_analysis = report['paper_analysis']
        if 'total_papers' in paper_analysis:
            print(f"\nPaper Analysis:")
            print(f"  Total Papers: {paper_analysis['total_papers']}")
            print(f"  With Abstracts: {paper_analysis['papers_with_abstracts']}")
            print(f"  With DOIs: {paper_analysis['papers_with_dois']}")
            print(f"  Open Access: {paper_analysis['papers_open_access']}")
        
        # Show recommendations
        recommendations = report['recommendations']
        if recommendations['search_recommendations']:
            print(f"\nRecommendations:")
            for rec in recommendations['search_recommendations']:
                print(f"  • {rec}")
        
        # Demo 7: Export Results
        print("\n💾 Demo 7: Export Results")
        print("-" * 40)
        
        # Save comprehensive report
        report_file = Path("demo_results.json")
        with open(report_file, 'w') as f:
            # Convert non-serializable objects for JSON
            serializable_report = manager._make_serializable(report)
            json.dump(serializable_report, f, indent=2)
        
        print(f"Results exported to: {report_file.absolute()}")
        
        # Save paper metadata
        papers_file = Path("demo_papers.json")
        with open(papers_file, 'w') as f:
            papers_data = [p.to_dict() for p in papers]
            json.dump(papers_data, f, indent=2)
        
        print(f"Paper metadata exported to: {papers_file.absolute()}")
        
        print("\n✅ Comprehensive demo completed successfully!")
        print(f"Found {len(papers)} papers with average quality {avg_quality:.3f}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")
    
    finally:
        await manager.cleanup()

# Add helper method to make objects JSON serializable
def _make_serializable(self, obj):
    """Make complex objects JSON serializable"""
    if isinstance(obj, dict):
        return {k: self._make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [self._make_serializable(item) for item in obj]
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):
        return self._make_serializable(obj.__dict__)
    else:
        return str(obj) if not isinstance(obj, (str, int, float, bool, type(None))) else obj

# Add the method to the class
ComprehensiveAcademicManager._make_serializable = _make_serializable

if __name__ == "__main__":
    asyncio.run(comprehensive_demo())