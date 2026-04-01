#!/usr/bin/env python3
"""Check progress of ultimate 100% test"""

from pathlib import Path

output_dir = Path("ULTIMATE_100_FINAL")

if output_dir.exists():
    pdfs = list(output_dir.glob("*.pdf"))

    arxiv_count = len([p for p in pdfs if p.name.startswith("arxiv_")])
    scihub_count = len([p for p in pdfs if p.name.startswith("scihub_")])
    ieee_count = len([p for p in pdfs if p.name.startswith("ieee_")])
    siam_count = len([p for p in pdfs if p.name.startswith("siam_")])

    total = len(pdfs)

    print("🎯 ULTIMATE 100% TEST PROGRESS")
    print("=" * 50)
    print(f"ArXiv:   {arxiv_count} PDFs")
    print(f"Sci-Hub: {scihub_count} PDFs")
    print(f"IEEE:    {ieee_count} PDFs")
    print(f"SIAM:    {siam_count} PDFs")
    print(f"─────────────────")
    print(f"TOTAL:   {total} PDFs")

    if total > 0:
        print(f"\n✅ Test is running successfully!")
        print(f"Progress: {total}/400 ({total/4:.1f}%)")
else:
    print("❌ Test directory not found")
