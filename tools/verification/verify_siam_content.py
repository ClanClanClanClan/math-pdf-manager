#!/usr/bin/env python3
"""
Verify SIAM PDF Content
=======================

Check if downloaded SIAM PDFs contain actual paper content or are test files.
"""

import sys
from pathlib import Path

def analyze_siam_pdfs():
    """Analyze the content of downloaded SIAM PDFs."""
    
    print("🔍 ANALYZING SIAM PDF CONTENT")
    print("=" * 50)
    
    siam_dir = Path("siam_multiple_test")
    
    if not siam_dir.exists():
        print("❌ No SIAM test directory found. Run multi-paper test first.")
        return
    
    pdf_files = list(siam_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in test directory.")
        return
    
    print(f"Found {len(pdf_files)} PDF files to analyze:")
    print()
    
    # Analyze each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"📄 [{i}/{len(pdf_files)}] {pdf_path.name}")
        print(f"   Size: {pdf_path.stat().st_size:,} bytes")
        
        # Check PDF header and first few bytes
        try:
            with open(pdf_path, 'rb') as f:
                content = f.read(1000)  # First 1KB
                
                if content.startswith(b'%PDF'):
                    pdf_version = content[:8].decode('ascii', errors='ignore')
                    print(f"   ✅ Valid PDF: {pdf_version}")
                    
                    # Look for text content indicators
                    content_str = content.decode('ascii', errors='ignore')
                    
                    # Look for common PDF content patterns
                    if 'SIAM' in content_str:
                        print("   ✅ Contains 'SIAM' text")
                    if 'Abstract' in content_str:
                        print("   ✅ Contains 'Abstract'")
                    if any(word in content_str for word in ['Mathematics', 'Journal', 'Society']):
                        print("   ✅ Contains academic keywords")
                    if 'Page' in content_str or '/Page' in content_str:
                        print("   ✅ Contains page structure")
                        
                    # Check for placeholder/test content
                    if 'placeholder' in content_str.lower():
                        print("   ⚠️  May be placeholder content")
                    if 'test' in content_str.lower() and 'testing' not in content_str.lower():
                        print("   ⚠️  May be test content")
                        
                else:
                    print("   ❌ Not a valid PDF file")
                    
        except Exception as e:
            print(f"   💥 Error reading file: {e}")
        
        print()
    
    # File size analysis
    sizes = [f.stat().st_size for f in pdf_files]
    unique_sizes = set(sizes)
    
    print("📊 SIZE ANALYSIS:")
    print(f"   Total files: {len(pdf_files)}")
    print(f"   Unique sizes: {len(unique_sizes)}")
    print(f"   Size range: {min(sizes):,} - {max(sizes):,} bytes")
    
    if len(unique_sizes) == 1:
        print("   ⚠️  ALL FILES ARE IDENTICAL SIZE")
        print("      This may indicate standardized test responses")
    else:
        print("   ✅ Files have different sizes (likely real content)")
    
    print()
    
    # Recommendations
    print("💡 ANALYSIS CONCLUSIONS:")
    
    if len(unique_sizes) == 1 and len(pdf_files) > 3:
        print("   ⚠️  POSSIBLE ISSUE: All PDFs identical size")
        print("      - May be receiving test/placeholder responses")
        print("      - Browser PDF generation may be standardized")
        print("      - Consider manual verification of one PDF")
        
        print("\n📋 MANUAL VERIFICATION NEEDED:")
        print("   1. Open one of the downloaded PDFs manually")
        print("   2. Check if it contains the actual paper content")
        print("   3. Verify title, authors, and abstract match the DOI")
        print("   4. Compare with the paper on SIAM website")
        
    else:
        print("   ✅ PDFs appear to have unique content")
        print("   ✅ Size variation suggests real papers")
    
    return len(unique_sizes) > 1 or len(pdf_files) == 1

if __name__ == "__main__":
    success = analyze_siam_pdfs()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ PDF CONTENT ANALYSIS: LIKELY REAL CONTENT")
    else:
        print("⚠️  PDF CONTENT ANALYSIS: NEEDS MANUAL VERIFICATION")
    print("=" * 50)