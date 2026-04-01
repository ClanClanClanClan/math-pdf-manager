#!/usr/bin/env python3
"""
Test: Base model vs Custom trained model performance
Let's see if training is actually worth it
"""

import asyncio
import json

import aiohttp


async def test_base_model():
    """Test base Llama 3.2 1B on research papers"""
    
    test_paper = {
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "abstract": "An important paradigm of natural language processing consists of large-scale pre-training on general domain data and adaptation to particular tasks or domains. As we pre-train larger models, full fine-tuning, which retrains all model parameters, becomes less feasible. Using GPT-3 175B as an example, deploying independent instances of fine-tuned models, each with 175B parameters, is prohibitively expensive."
    }
    
    # Test with different prompt complexities
    prompts = [
        {
            "name": "Simple Summary",
            "prompt": f"Summarize this paper: {test_paper['title']}. {test_paper['abstract']}"
        },
        {
            "name": "Research Analysis", 
            "prompt": f"""Analyze this research paper and provide structured insights:

Title: {test_paper['title']}
Abstract: {test_paper['abstract']}

Provide:
1. A 2-sentence summary
2. Why this is relevant for ML researchers 
3. A relevance score (0-10)
4. Key technical insights
5. Potential applications

Format as JSON."""
        },
        {
            "name": "Domain-Specific",
            "prompt": f"""As an expert in parameter-efficient fine-tuning for large language models, analyze this paper:

Title: {test_paper['title']}
Abstract: {test_paper['abstract']}

Assess:
- Technical novelty in parameter efficiency
- Impact on deployment costs
- Comparison to other PEFT methods
- Practical implementation considerations

Respond with detailed JSON analysis."""
        }
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for prompt_test in prompts:
            print(f"🧪 Testing: {prompt_test['name']}")
            
            payload = {
                "model": "llama3.2:1b",
                "prompt": prompt_test['prompt'],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 300}
            }
            
            try:
                async with session.post("http://localhost:11434/api/generate", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response = data.get('response', '')
                        
                        results.append({
                            "test": prompt_test['name'],
                            "response": response,
                            "quality": assess_quality(response, prompt_test['name'])
                        })
                        
                        print(f"   Response length: {len(response)} chars")
                        print(f"   Quality: {results[-1]['quality']}/10")
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    return results


def assess_quality(response: str, test_type: str) -> float:
    """Assess response quality (simple heuristic)"""
    
    quality_score = 5.0  # Base score
    
    # Check for JSON formatting (if requested)
    if "JSON" in test_type:
        if "{" in response and "}" in response:
            quality_score += 2.0
        else:
            quality_score -= 2.0
    
    # Check for key terms
    key_terms = ["parameter", "efficient", "fine-tuning", "model", "adaptation"]
    found_terms = sum(1 for term in key_terms if term.lower() in response.lower())
    quality_score += (found_terms / len(key_terms)) * 2
    
    # Check length (not too short, not too long)
    if 100 < len(response) < 500:
        quality_score += 1.0
    elif len(response) < 50:
        quality_score -= 2.0
    
    return min(10.0, max(0.0, quality_score))


def training_recommendation(results):
    """Should you train based on test results?"""
    
    avg_quality = sum(r['quality'] for r in results) / len(results)
    
    print(f"\n🎯 TRAINING RECOMMENDATION")
    print("="*40)
    print(f"Average Quality: {avg_quality:.1f}/10")
    
    if avg_quality >= 7.5:
        print("✅ BASE MODEL IS GOOD ENOUGH")
        print("Recommendation: Skip training, use base model")
        print("Reasoning: Base model handles your tasks well")
        
    elif avg_quality >= 6.0:
        print("🤔 TRAINING MIGHT HELP")
        print("Recommendation: Try base model first, train if needed")
        print("Reasoning: Base model is decent but has room for improvement")
        
    else:
        print("🎓 DEFINITELY TRAIN")
        print("Recommendation: Custom training recommended")
        print("Reasoning: Base model struggles with your requirements")
    
    print(f"\n💡 Cost-Benefit Analysis:")
    print(f"Training Time: 30-60 minutes")
    print(f"Training Cost: $0 (Colab Pro+)")
    print(f"Quality Improvement: ~{min(3.0, 10-avg_quality):.1f} points")
    
    return avg_quality >= 7.5


async def main():
    """Run the training necessity test"""
    
    print("🔬 TESTING: Do You Need Custom Training?")
    print("="*50)
    
    print("Testing base Llama 3.2 1B model on research analysis...")
    results = await test_base_model()
    
    print(f"\n📊 DETAILED RESULTS:")
    print("="*30)
    
    for result in results:
        print(f"\n🧪 {result['test']}")
        print(f"Quality: {result['quality']:.1f}/10")
        print(f"Response: {result['response'][:150]}...")
        print("-" * 40)
    
    skip_training = training_recommendation(results)
    
    print(f"\n🚀 NEXT STEPS:")
    if skip_training:
        print("1. Use the base model as-is")
        print("2. Run your daily ArXiv processing")
        print("3. Evaluate results after a few days")
        print("4. Only train if you're unsatisfied")
    else:
        print("1. Prepare your domain-specific training data")
        print("2. Run the Colab training notebook")
        print("3. Deploy your custom model")
        print("4. Enjoy better research insights")


if __name__ == "__main__":
    asyncio.run(main())