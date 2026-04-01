#!/usr/bin/env python3
import asyncio
import sys

sys.path.insert(0, 'src')

async def test():
    try:
        # Test CMO
        from mathpdf.arxivbot.models.cmo import CMO, Author
        paper = CMO(
            external_id="test-001",
            source="arxiv",
            title="Test Paper",
            authors=[Author(family="Smith", given="John")],
            published="2024-01-01T00:00:00Z",
            abstract="Test abstract."
        )
        print("✓ CMO works")
        
        # Test embedding service
        from mathpdf.arxivbot.embeddings.specter2_service import (
            EmbeddingConfig,
            SPECTER2EmbeddingService,
        )
        config = EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            enable_cache=False
        )
        service = SPECTER2EmbeddingService(config)
        await service.initialize()
        embedding = await service.embed_paper(paper)
        print(f"✓ Embedding works: {embedding.shape if embedding is not None else 'None'}")
        
        # Test vector store
        from mathpdf.arxivbot.vector_store.faiss_backend import FAISSVectorStore
        store = FAISSVectorStore("./.test_store", 384, False)
        await store.add_paper(paper)
        results = await store.search(embedding, k=1)
        print(f"✓ Vector store works: {len(results)} results")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test())