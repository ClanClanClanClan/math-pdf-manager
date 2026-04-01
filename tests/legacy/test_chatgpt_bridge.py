#!/usr/bin/env python3
"""
Test the ChatGPT Pro Bridge implementation
Non-interactive version for testing
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, 'src')

from mathpdf.arxivbot.embeddings.specter2_service import EmbeddingConfig, SPECTER2EmbeddingService
from mathpdf.arxivbot.models.cmo import CMO, Author
from mathpdf.arxivbot.scoring.advanced_scorer import AdvancedPaperScorer, ScoringConfig
from mathpdf.arxivbot.vector_store.faiss_backend import FAISSVectorStore


async def test_batch_generation():
    """Test generating a batch for ChatGPT Pro"""
    
    print("\n📚 Testing ArXiv Bot ChatGPT Pro Integration")
    print("="*60)
    
    # Initialize services
    print("Initializing local services...")
    
    # Embeddings
    embedding_config = EmbeddingConfig(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        enable_cache=True
    )
    embedding_service = SPECTER2EmbeddingService(embedding_config)
    await embedding_service.initialize()
    
    # Vector store
    vector_store = FAISSVectorStore("./data/vector_store", 384, False)
    
    # Scorer
    scoring_config = ScoringConfig(enable_cross_encoder=False)
    scorer = AdvancedPaperScorer(scoring_config, embedding_service)
    await scorer.initialize()
    
    # Create test papers
    papers = [
        CMO(
            external_id="2024.1001",
            source="arxiv",
            title="Attention Mechanisms in Graph Neural Networks: A Comprehensive Survey",
            authors=[Author(family="Smith", given="John"), Author(family="Doe", given="Jane")],
            published=datetime.now().isoformat(),
            abstract="Graph Neural Networks (GNNs) have emerged as powerful tools for learning on graph-structured data. This survey provides a comprehensive overview of attention mechanisms in GNNs, categorizing existing approaches and analyzing their theoretical foundations. We examine how attention improves message passing, enables adaptive aggregation, and handles heterogeneous graphs. Our analysis includes performance comparisons on benchmark datasets and identifies key research directions."
        ),
        CMO(
            external_id="2024.1002",
            source="arxiv",
            title="Efficient Fine-Tuning of Large Language Models via Low-Rank Adaptation",
            authors=[Author(family="Johnson", given="Alice"), Author(family="Williams", given="Bob")],
            published=datetime.now().isoformat(),
            abstract="We present LoRA++, an improved low-rank adaptation method for efficient fine-tuning of large language models. Our approach reduces the number of trainable parameters by 99% while maintaining comparable performance to full fine-tuning. We introduce dynamic rank allocation and adaptive learning rates for different LoRA modules. Experiments on various NLP tasks demonstrate that LoRA++ achieves state-of-the-art results with significantly reduced computational requirements."
        ),
        CMO(
            external_id="2024.1003",
            source="arxiv",
            title="Quantum Computing for Machine Learning: Current State and Future Directions",
            authors=[Author(family="Chen", given="Wei"), Author(family="Kumar", given="Raj")],
            published=datetime.now().isoformat(),
            abstract="This paper explores the intersection of quantum computing and machine learning, examining both quantum-enhanced classical algorithms and genuinely quantum machine learning approaches. We provide a critical analysis of claimed quantum advantages, separating hype from realistic near-term applications. Our experiments on NISQ devices reveal practical limitations and opportunities. We propose a hybrid quantum-classical framework that leverages the strengths of both paradigms."
        ),
        CMO(
            external_id="2024.1004",
            source="arxiv",
            title="Diffusion Models for Scientific Data Generation and Analysis",
            authors=[Author(family="Martinez", given="Carlos"), Author(family="Lee", given="Sarah")],
            published=datetime.now().isoformat(),
            abstract="Diffusion models have shown remarkable success in image generation, but their application to scientific data remains underexplored. We present SciDiff, a framework for applying diffusion models to various scientific domains including molecular design, climate modeling, and astronomical data synthesis. Our approach handles irregular grids, physical constraints, and multi-modal data. We demonstrate applications in drug discovery, weather prediction, and cosmological simulations."
        ),
        CMO(
            external_id="2024.1005",
            source="arxiv",
            title="Causal Representation Learning: Theory and Applications",
            authors=[Author(family="Brown", given="David"), Author(family="Wilson", given="Emma")],
            published=datetime.now().isoformat(),
            abstract="Understanding causal relationships from observational data is fundamental to scientific discovery. This paper presents a unified framework for causal representation learning that combines ideas from causal inference, deep learning, and information theory. We prove identifiability results under various assumptions and develop practical algorithms for learning causal representations. Applications to healthcare, economics, and climate science demonstrate the value of our approach for discovering interpretable causal structures."
        )
    ]
    
    # Score papers
    print(f"\nScoring {len(papers)} test papers...")
    query = "machine learning artificial intelligence deep learning neural networks"
    scores = await scorer.score_papers_batch(query, papers)
    
    # Sort by score
    scored_papers = list(zip(papers, scores))
    scored_papers.sort(key=lambda x: x[1], reverse=True)
    
    # Generate output files
    print("\n📋 Generating ChatGPT batch files...")
    
    output_dir = Path("./daily_batches")
    output_dir.mkdir(exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    # 1. Markdown file (human-readable)
    markdown_file = output_dir / f"test_batch_{date_str}.md"
    with open(markdown_file, 'w') as f:
        f.write(f"# Test ArXiv Papers Batch\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Query:** {query}\n\n")
        f.write("---\n\n")
        
        for i, (paper, score) in enumerate(scored_papers, 1):
            f.write(f"## Paper {i} (Relevance: {score:.1%})\n\n")
            f.write(f"**Title:** {paper.title}\n\n")
            f.write(f"**Authors:** {', '.join(str(a) for a in paper.authors)}\n\n")
            f.write(f"**ID:** {paper.external_id}\n\n")
            f.write(f"**Abstract:** {paper.abstract[:300]}...\n\n")
            f.write("---\n\n")
    
    # 2. ChatGPT prompt file
    prompt_file = output_dir / f"chatgpt_prompt_{date_str}.txt"
    prompt_text = """You are an expert AI research assistant. Please analyze these papers and provide structured summaries.

For each paper, provide:
1. A 2-3 sentence summary of the key contribution
2. Why it's important/novel in the field
3. Potential applications or impact
4. A relevance score (0-10) for ML researchers
5. Any notable connections to other recent work

Please format your response as JSON for easy parsing.

PAPERS TO ANALYZE:

"""
    
    papers_data = []
    for i, (paper, score) in enumerate(scored_papers, 1):
        paper_dict = {
            "index": i,
            "id": paper.external_id,
            "title": paper.title,
            "authors": [str(a) for a in paper.authors],
            "abstract": paper.abstract[:400],
            "local_relevance_score": round(score, 3)
        }
        papers_data.append(paper_dict)
    
    prompt_text += json.dumps(papers_data, indent=2)
    prompt_text += """

Please provide your analysis in this JSON format:
[
    {
        "id": "paper_id",
        "summary": "2-3 sentence summary",
        "importance": "Why this matters",
        "applications": "Potential uses",
        "relevance_score": 8,
        "connections": "Related work"
    }
]"""
    
    with open(prompt_file, 'w') as f:
        f.write(prompt_text)
    
    # 3. Response template
    response_template = output_dir / f"response_template_{date_str}.json"
    template = []
    for paper, score in scored_papers:
        template.append({
            "id": paper.external_id,
            "title": paper.title[:50] + "...",
            "summary": "",
            "importance": "",
            "applications": "",
            "relevance_score": 0,
            "connections": "",
            "local_score": round(score, 3)
        })
    
    with open(response_template, 'w') as f:
        json.dump(template, f, indent=2)
    
    print("\n✅ Test batch generated successfully!")
    print(f"\n📁 Output directory: {output_dir.absolute()}")
    print(f"\n📄 Files created:")
    print(f"  1. {markdown_file.name} - Human-readable paper list")
    print(f"  2. {prompt_file.name} - Copy this to ChatGPT")
    print(f"  3. {response_template.name} - Template for responses")
    
    # Try to copy to clipboard
    try:
        import subprocess
        subprocess.run("pbcopy", text=True, input=prompt_text, check=True)
        print("\n✂️  Prompt copied to clipboard!")
        print("   Paste it into ChatGPT Pro to test the integration")
    except:
        print("\n📋 Could not copy to clipboard automatically")
        print(f"   Please open: {prompt_file}")
    
    print("\n🔄 Next Steps:")
    print("  1. Open ChatGPT Pro in your browser")
    print("  2. Paste the prompt (it's in your clipboard)")
    print("  3. Copy ChatGPT's JSON response")
    print("  4. Run: python3 test_chatgpt_response.py")
    
    return scored_papers


async def main():
    """Main test function"""
    await test_batch_generation()


if __name__ == "__main__":
    asyncio.run(main())