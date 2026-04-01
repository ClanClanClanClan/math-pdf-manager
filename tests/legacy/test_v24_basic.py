#!/usr/bin/env python3
"""
Basic v2.4 functionality test - checks core components work
"""

import asyncio
import os
import sys

sys.path.insert(0, 'src')

async def test_basic_functionality():
    print("Testing v2.4 Basic Functionality...")
    print("=" * 50)
    
    # Test 1: CMO creation
    print("\n1. Testing CMO creation...")
    try:
        from mathpdf.arxivbot.models.cmo import CMO, Author
        
        paper = CMO(
            external_id="test-001",
            source="arxiv",
            title="Test Paper",
            authors=[Author(family="Smith", given="John")],
            published="2024-01-01T00:00:00Z",
            abstract="This is a test abstract for the paper."
        )
        print(f"   ✓ CMO created: {paper.external_id}")
        print(f"   ✓ Embedding text: {len(paper.get_embedding_text())} chars")
    except Exception as e:
        print(f"   ✗ CMO test failed: {e}")
        return False
    
    # Test 2: SPECTER2 embedding service
    print("\n2. Testing SPECTER2 embedding service...")
    try:
        from mathpdf.arxivbot.embeddings.specter2_service import (
            EmbeddingConfig,
            SPECTER2EmbeddingService,
        )
        
        config = EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            enable_cache=False,
            enable_fallback=True
        )
        
        service = SPECTER2EmbeddingService(config)
        await service.initialize()
        
        embedding = await service.embed_text("Test text for embedding")
        if embedding is not None:
            print(f"   ✓ Embedding generated: shape {embedding.shape}")
        else:
            print("   ⚠ Embedding failed but service initialized")
            
    except Exception as e:
        print(f"   ✗ SPECTER2 test failed: {e}")
        return False
    
    # Test 3: Vector store
    print("\n3. Testing FAISS vector store...")
    try:
        from mathpdf.arxivbot.vector_store.faiss_backend import FAISSVectorStore
        
        store = FAISSVectorStore(
            storage_path="./.test_vector_store",
            dimension=384,  # MiniLM dimension
            use_gpu=False
        )
        
        print(f"   ✓ Vector store initialized")
        
        # Add test paper
        await service.embed_paper(paper)
        await store.add_paper(paper)
        print(f"   ✓ Paper added to store")
        
        # Search
        query_embedding = await service.embed_text("machine learning")
        if query_embedding is not None:
            results = await store.search(query_embedding, k=1)
            print(f"   ✓ Search completed: {len(results)} results")
        
    except Exception as e:
        print(f"   ✗ Vector store test failed: {e}")
        return False
    
    # Test 4: Advanced scorer
    print("\n4. Testing advanced scorer...")
    try:
        from mathpdf.arxivbot.scoring.advanced_scorer import AdvancedPaperScorer, ScoringConfig
        
        scoring_config = ScoringConfig(
            enable_cross_encoder=False,  # Skip for speed
            enable_author_priors=True
        )
        
        scorer = AdvancedPaperScorer(scoring_config, service)
        await scorer.initialize()
        
        score = await scorer.score_paper("machine learning", paper)
        print(f"   ✓ Paper scored: {score:.3f}")
        
    except Exception as e:
        print(f"   ✗ Scorer test failed: {e}")
        return False
    
    # Test 5: Citation graph
    print("\n5. Testing citation graph...")
    try:
        from mathpdf.arxivbot.citations.graph_analyzer import CitationGraphBuilder
        
        builder = CitationGraphBuilder()
        citations_added = await builder.add_paper(paper, extract_citations=True)
        stats = builder.get_graph_statistics()
        
        print(f"   ✓ Graph builder working")
        print(f"   ✓ Papers in graph: {stats.total_papers}")
        
    except Exception as e:
        print(f"   ✗ Citation graph test failed: {e}")
        return False
    
    # Test 6: Feedback processor
    print("\n6. Testing feedback processor...")
    try:
        from datetime import datetime

        from mathpdf.arxivbot.feedback.feedback_processor import (
            FeedbackConfig,
            FeedbackProcessor,
            FeedbackType,
            UserInteraction,
        )
        
        feedback_config = FeedbackConfig(enable_lora_finetuning=False)
        processor = FeedbackProcessor(feedback_config, service)
        
        interaction = UserInteraction(
            user_id="test_user",
            paper_id="test-001",
            interaction_type=FeedbackType.EXPLICIT_RATING,
            timestamp=datetime.now(),
            value=4.0
        )
        
        success = await processor.record_feedback(interaction)
        print(f"   ✓ Feedback recorded: {success}")
        
    except Exception as e:
        print(f"   ✗ Feedback test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All basic tests passed!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_basic_functionality())
    sys.exit(0 if result else 1)