#!/usr/bin/env python3
"""
V2.4 Integration Test - Tests actual component integration
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, 'src')

# Suppress verbose logging for cleaner output
import logging

logging.basicConfig(level=logging.WARNING)

async def main():
    print("=" * 60)
    print("ArXiv Bot v2.4 Integration Test")
    print("=" * 60)
    
    results = {
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    # Test 1: CMO and Embeddings Integration
    print("\n📋 Test 1: CMO + Embeddings")
    try:
        from mathpdf.arxivbot.embeddings.specter2_service import (
            EmbeddingConfig,
            SPECTER2EmbeddingService,
        )
        from mathpdf.arxivbot.models.cmo import CMO, Author

        # Create test papers
        papers = []
        for i in range(3):
            paper = CMO(
                external_id=f"test-{i:03d}",
                source="arxiv",
                title=f"Paper {i}: {'Machine Learning' if i==0 else 'Deep Learning' if i==1 else 'Neural Networks'}",
                authors=[Author(family=f"Author{i}", given="Test")],
                published="2024-01-01T00:00:00Z",
                abstract=f"Abstract about {'transformers and attention' if i==0 else 'convolutional networks' if i==1 else 'recurrent models'}.",
                citation_count=i * 5
            )
            papers.append(paper)
        
        # Initialize embedding service
        config = EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            enable_cache=True,
            cache_dir="./.test_cache"
        )
        embedding_service = SPECTER2EmbeddingService(config)
        await embedding_service.initialize()
        
        # Generate embeddings
        start = time.time()
        embeddings = await embedding_service.embed_papers_batch(papers)
        embed_time = (time.time() - start) * 1000
        
        print(f"  ✓ Generated {len(embeddings)} embeddings in {embed_time:.1f}ms")
        print(f"  ✓ Embedding shape: {embeddings[0].shape if embeddings[0] is not None else 'None'}")
        results['passed'] += 1
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        results['failed'] += 1
        results['errors'].append(str(e))
    
    # Test 2: Vector Store + Search
    print("\n🔍 Test 2: Vector Store + Search")
    try:
        from mathpdf.arxivbot.vector_store.faiss_backend import FAISSVectorStore

        # Initialize store
        store = FAISSVectorStore("./.test_vector_store", dimension=384, use_gpu=False)
        
        # Add papers
        for paper in papers:
            await store.add_paper(paper)
        
        # Search
        query = "attention mechanisms in transformers"
        query_embedding = await embedding_service.embed_text(query)
        
        start = time.time()
        search_results = await store.search(query_embedding, k=2)
        search_time = (time.time() - start) * 1000
        
        print(f"  ✓ Added {len(papers)} papers to store")
        print(f"  ✓ Search returned {len(search_results)} results in {search_time:.1f}ms")
        if search_results:
            print(f"  ✓ Top result: {search_results[0][0]} (score: {search_results[0][1]:.3f})")
        results['passed'] += 1
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        results['failed'] += 1
        results['errors'].append(str(e))
    
    # Test 3: Advanced Scoring
    print("\n⭐ Test 3: Advanced Scoring")
    try:
        from mathpdf.arxivbot.scoring.advanced_scorer import (
            AdvancedPaperScorer,
            ScoringConfig,
            ScoringMode,
        )
        
        scoring_config = ScoringConfig(
            mode=ScoringMode.FAST,  # Fast mode for testing
            enable_cross_encoder=False,
            target_ms_per_paper=15.0
        )
        
        scorer = AdvancedPaperScorer(scoring_config, embedding_service)
        await scorer.initialize()
        
        # Score papers
        query = "deep learning transformers"
        start = time.time()
        scores = await scorer.score_papers_batch(query, papers)
        scoring_time = (time.time() - start) * 1000
        
        print(f"  ✓ Scored {len(scores)} papers in {scoring_time:.1f}ms")
        print(f"  ✓ Scores: {[f'{s:.3f}' for s in scores]}")
        print(f"  ✓ Avg time per paper: {scoring_time/len(papers):.1f}ms")
        results['passed'] += 1
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        results['failed'] += 1
        results['errors'].append(str(e))
    
    # Test 4: Citation Graph
    print("\n🕸️ Test 4: Citation Graph")
    try:
        from mathpdf.arxivbot.citations.graph_analyzer import (
            CitationGraphBuilder,
            CitationPropagator,
        )
        
        builder = CitationGraphBuilder()
        
        # Add papers to graph
        for paper in papers:
            await builder.add_paper(paper, extract_citations=False)
        
        # Add some manual citations for testing
        builder.add_citation(papers[0].external_id, papers[1].external_id, "cites for methodology")
        builder.add_citation(papers[1].external_id, papers[2].external_id, "extends this work")
        
        stats = builder.get_graph_statistics()
        
        print(f"  ✓ Graph contains {stats.total_papers} papers")
        print(f"  ✓ Graph contains {stats.total_citations} citations")
        
        # Test propagation
        propagator = CitationPropagator(builder)
        initial = [papers[0].external_id]
        result = await propagator.propagate_results(initial, depth=2)
        
        print(f"  ✓ Propagation expanded {len(initial)} → {len(result.expanded_papers)} papers")
        results['passed'] += 1
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        results['failed'] += 1
        results['errors'].append(str(e))
    
    # Test 5: Feedback System
    print("\n💬 Test 5: Feedback System")
    try:
        from datetime import datetime

        from mathpdf.arxivbot.feedback.feedback_processor import (
            FeedbackConfig,
            FeedbackProcessor,
            FeedbackType,
            UserInteraction,
        )
        
        feedback_config = FeedbackConfig(
            enable_lora_finetuning=False,  # Skip LoRA for testing
            min_interactions_for_profile=2
        )
        
        processor = FeedbackProcessor(feedback_config, embedding_service)
        
        # Record some feedback
        interactions = [
            UserInteraction(
                user_id="test_user",
                paper_id=papers[0].external_id,
                interaction_type=FeedbackType.EXPLICIT_RATING,
                timestamp=datetime.now(),
                value=5.0
            ),
            UserInteraction(
                user_id="test_user",
                paper_id=papers[1].external_id,
                interaction_type=FeedbackType.SAVE,
                timestamp=datetime.now()
            )
        ]
        
        for interaction in interactions:
            success = await processor.record_feedback(interaction)
        
        # Get user profile
        profile = await processor.get_user_profile("test_user")
        
        print(f"  ✓ Recorded {len(interactions)} interactions")
        print(f"  ✓ User profile created: {profile is not None}")
        if profile:
            print(f"  ✓ Total interactions: {profile.total_interactions}")
        results['passed'] += 1
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        results['failed'] += 1
        results['errors'].append(str(e))
    
    # Test 6: Performance Check
    print("\n⚡ Test 6: Performance Validation")
    performance_ok = True
    
    # Check embedding performance
    if embed_time / len(papers) > 100:
        print(f"  ⚠️ Embedding too slow: {embed_time/len(papers):.1f}ms per paper (target: 100ms)")
        performance_ok = False
    else:
        print(f"  ✓ Embedding performance OK: {embed_time/len(papers):.1f}ms per paper")
    
    # Check search performance
    if search_time > 100:
        print(f"  ⚠️ Search too slow: {search_time:.1f}ms (target: 100ms)")
        performance_ok = False
    else:
        print(f"  ✓ Search performance OK: {search_time:.1f}ms")
    
    # Check scoring performance
    if scoring_time / len(papers) > 15:
        print(f"  ⚠️ Scoring too slow: {scoring_time/len(papers):.1f}ms per paper (target: 15ms)")
        performance_ok = False
    else:
        print(f"  ✓ Scoring performance OK: {scoring_time/len(papers):.1f}ms per paper")
    
    if performance_ok:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {results['passed']}/6")
    print(f"❌ Failed: {results['failed']}/6")
    
    if results['errors']:
        print("\n⚠️ Errors encountered:")
        for error in results['errors']:
            print(f"  • {error[:100]}...")
    
    compliance_score = (results['passed'] / 6) * 100
    print(f"\n🎯 v2.4 Compliance Score: {compliance_score:.0f}%")
    
    if compliance_score >= 80:
        print("✅ System is ready for production!")
    elif compliance_score >= 60:
        print("⚠️ System needs some fixes before production")
    else:
        print("❌ System requires significant work")
    
    return results['failed'] == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)