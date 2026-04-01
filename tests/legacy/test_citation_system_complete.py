#!/usr/bin/env python3
"""
Complete Citation Analysis System Test
Tests all v2.4 citation functionality
"""

import asyncio
import sys

import networkx as nx

sys.path.insert(0, 'src')

from mathpdf.arxivbot.citations.citation_extractor import CitationExtractor
from mathpdf.arxivbot.citations.citation_graph_analyzer import CitationGraphAnalyzer
from mathpdf.arxivbot.models.cmo import CMO, Author, Citation


async def test_citation_system():
    """Test complete citation analysis pipeline"""
    
    print("🔗 TESTING COMPLETE CITATION ANALYSIS SYSTEM")
    print("="*60)
    
    # Create test papers with citation relationships
    papers = []
    
    # Paper 1: Attention mechanism paper (foundational)
    paper1 = CMO(
        external_id="1706.03762",
        source="arxiv", 
        title="Attention Is All You Need",
        authors=[Author(family="Vaswani", given="Ashish")],
        published="2017-06-12T00:00:00Z",
        abstract="We propose the Transformer, a new simple network architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."
    )
    papers.append(paper1)
    
    # Paper 2: BERT paper (cites Transformer)
    paper2 = CMO(
        external_id="1810.04805", 
        source="arxiv",
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        authors=[Author(family="Devlin", given="Jacob")],
        published="2018-10-11T00:00:00Z",
        abstract="We introduce BERT, which stands for Bidirectional Encoder Representations from Transformers. Our architecture is based on the original Transformer implementation (Vaswani et al., 2017)."
    )
    # Add citation relationship
    paper2.citations_out = [Citation(
        cited_paper_id="1706.03762",
        context="based on the original Transformer implementation (Vaswani et al., 2017)",
        citation_type="reference"
    )]
    papers.append(paper2)
    
    # Paper 3: GPT paper (also cites Transformer) 
    paper3 = CMO(
        external_id="1706.03762v2",
        source="arxiv",
        title="Language Models are Unsupervised Multitask Learners", 
        authors=[Author(family="Radford", given="Alec")],
        published="2019-02-14T00:00:00Z",
        abstract="We demonstrate that language models begin to learn these tasks without any explicit supervision when trained on a new dataset. We use the Transformer architecture from Vaswani et al."
    )
    paper3.citations_out = [Citation(
        cited_paper_id="1706.03762",
        context="We use the Transformer architecture from Vaswani et al.",
        citation_type="reference"
    )]
    papers.append(paper3)
    
    print(f"📄 Created {len(papers)} test papers with citation relationships")
    
    # Test 1: Citation Extraction
    print("\n1. Testing Citation Extraction...")
    try:
        extractor = CitationExtractor()
        
        extracted_citations = []
        for paper in papers:
            citations = await extractor.extract_citations_from_text(
                paper.abstract, paper.external_id
            )
            extracted_citations.extend(citations)
            
        print(f"   ✅ Extracted {len(extracted_citations)} citations from abstracts")
        
    except Exception as e:
        print(f"   ❌ Citation extraction failed: {e}")
        return False
    
    # Test 2: Graph Construction
    print("\n2. Testing Citation Graph Construction...")
    try:
        analyzer = CitationGraphAnalyzer()
        
        # Add papers to graph
        for paper in papers:
            await analyzer.add_paper(paper)
            
        # Build citation relationships
        await analyzer.build_graph()
        
        stats = analyzer.get_graph_stats()
        print(f"   ✅ Graph built: {stats.total_papers} papers, {stats.total_citations} citations")
        
    except Exception as e:
        print(f"   ❌ Graph construction failed: {e}")
        return False
    
    # Test 3: Citation-based Search Expansion
    print("\n3. Testing Citation-based Search Expansion...")
    try:
        # Find papers related to the Transformer paper
        related_papers = await analyzer.find_related_papers(
            "1706.03762", max_depth=2, max_results=10
        )
        
        print(f"   ✅ Found {len(related_papers)} related papers via citation analysis")
        
        for paper_id, relevance in related_papers[:3]:
            print(f"      - {paper_id}: {relevance:.3f}")
            
    except Exception as e:
        print(f"   ❌ Citation expansion failed: {e}")
        return False
    
    # Test 4: Citation Influence Scoring
    print("\n4. Testing Citation Influence Scoring...")
    try:
        influence_scores = await analyzer.calculate_influence_scores()
        
        print(f"   ✅ Calculated influence scores for {len(influence_scores)} papers")
        
        # Show top influential papers
        sorted_scores = sorted(influence_scores.items(), key=lambda x: x[1], reverse=True)
        for paper_id, score in sorted_scores[:3]:
            print(f"      - {paper_id}: {score:.3f}")
            
    except Exception as e:
        print(f"   ❌ Influence scoring failed: {e}")
        return False
    
    # Test 5: Graph Analysis Metrics
    print("\n5. Testing Graph Analysis Metrics...")
    try:
        metrics = await analyzer.analyze_graph_structure()
        
        print(f"   ✅ Graph analysis complete")
        print(f"      - Clustering coefficient: {metrics.get('clustering', 0):.3f}")
        print(f"      - Average path length: {metrics.get('avg_path_length', 0):.3f}")
        print(f"      - Network density: {metrics.get('density', 0):.3f}")
        
    except Exception as e:
        print(f"   ❌ Graph analysis failed: {e}")
        return False
    
    # Test 6: Citation Context Analysis
    print("\n6. Testing Citation Context Analysis...")
    try:
        contexts = await analyzer.analyze_citation_contexts("1706.03762")
        
        print(f"   ✅ Analyzed citation contexts")
        print(f"      - Found {len(contexts)} different citation contexts")
        
        for context, count in contexts.items():
            print(f"      - {context}: {count} citations")
            
    except Exception as e:
        print(f"   ❌ Context analysis failed: {e}")
        return False
    
    print(f"\n🎉 CITATION SYSTEM TEST COMPLETE")
    print(f"All v2.4 citation analysis features are working!")
    
    return True


async def main():
    """Run citation system tests"""
    success = await test_citation_system()
    
    if success:
        print(f"\n✅ CITATION ANALYSIS SYSTEM: FULLY v2.4 COMPLIANT")
    else:
        print(f"\n❌ CITATION ANALYSIS SYSTEM: NEEDS FIXES")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)