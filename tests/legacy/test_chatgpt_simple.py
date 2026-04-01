#!/usr/bin/env python3
"""
Simple test of ChatGPT Pro Bridge - no async complexity
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

# Create test papers data
papers = [
    {
        "id": "2024.1001",
        "title": "Attention Mechanisms in Graph Neural Networks",
        "authors": ["J. Smith", "J. Doe"],
        "abstract": "Graph Neural Networks (GNNs) have emerged as powerful tools..."
    },
    {
        "id": "2024.1002", 
        "title": "Efficient Fine-Tuning of Large Language Models",
        "authors": ["A. Johnson", "B. Williams"],
        "abstract": "We present LoRA++, an improved low-rank adaptation method..."
    },
    {
        "id": "2024.1003",
        "title": "Quantum Computing for Machine Learning",
        "authors": ["W. Chen", "R. Kumar"],
        "abstract": "This paper explores the intersection of quantum computing..."
    }
]

# Create output directory
output_dir = Path("./daily_batches")
output_dir.mkdir(exist_ok=True)

date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")

# Generate ChatGPT prompt
prompt = """Please analyze these research papers and provide:
1. A brief summary (2-3 sentences)
2. Why it's important for ML researchers
3. A relevance score (0-10)

Format as JSON for easy parsing.

PAPERS:

"""

prompt += json.dumps(papers, indent=2)

prompt += """

Respond with JSON like:
[{"id": "2024.1001", "summary": "...", "importance": "...", "score": 8}]
"""

# Save files
prompt_file = output_dir / f"prompt_{date_str}.txt"
prompt_file.write_text(prompt)

markdown_file = output_dir / f"papers_{date_str}.md"
with open(markdown_file, 'w') as f:
    f.write("# Test Papers for ChatGPT Pro\n\n")
    for p in papers:
        f.write(f"## {p['title']}\n")
        f.write(f"**ID:** {p['id']}\n")
        f.write(f"**Authors:** {', '.join(p['authors'])}\n")
        f.write(f"**Abstract:** {p['abstract'][:200]}...\n\n")

print("📚 ChatGPT Pro Test Batch Generated")
print("="*50)
print(f"✅ Files saved to: {output_dir.absolute()}")
print(f"📄 Prompt file: {prompt_file.name}")
print(f"📄 Markdown file: {markdown_file.name}")

# Try clipboard copy
try:
    subprocess.run("pbcopy", text=True, input=prompt, check=True)
    print("\n✂️  Prompt copied to clipboard!")
    print("\n📋 Instructions:")
    print("1. Open ChatGPT Pro")
    print("2. Paste the prompt (Cmd+V)")
    print("3. Copy the JSON response")
    print("4. Save it and run: python3 process_response.py <file>")
except:
    print(f"\n📋 Open {prompt_file} and copy to ChatGPT")