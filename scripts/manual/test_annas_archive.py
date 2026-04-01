#!/usr/bin/env python3
"""
Test Anna's Archive Integration
===============================

Test Anna's Archive as additional backup source for papers.
"""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def test_annas_archive():
    """Test Anna's Archive functionality"""
    
    print("🔍 Testing Anna's Archive Integration")
    print("=" * 50)
    
    try:
        from src.downloader.universal_downloader import AnnaArchiveDownloader
        
        anna = AnnaArchiveDownloader()
        
        # Test different types of queries
        test_queries = [
            "10.1016/j.jcp.2019.07.031",  # Elsevier DOI
            "computational physics",      # General search
            "machine learning",          # Popular topic
            "neural networks"            # Technical term
        ]
        
        for query in test_queries:
            print(f"\n🔍 Searching for: {query}")
            
            try:
                results = await anna.search(query)
                print(f"   Found {len(results)} results")
                
                if results:
                    # Show first few results
                    for i, result in enumerate(results[:3]):
                        print(f"   {i+1}. {result.title[:60]}...")
                        if result.confidence:
                            print(f"      Confidence: {result.confidence:.2f}")
                    
                    # Try downloading the first result
                    first_result = results[0]
                    print(f"\n📥 Attempting download of: {first_result.title[:40]}...")
                    
                    download_result = await anna.download(first_result)
                    
                    if download_result.success:
                        print("   ✅ Download successful!")
                        print(f"   Size: {download_result.file_size / 1024:.1f} KB")
                        
                        # Save test file
                        output_dir = Path("anna_test")
                        output_dir.mkdir(exist_ok=True)
                        
                        filename = f"anna_test_{query.replace(' ', '_').replace('.', '_')}.pdf"
                        output_path = output_dir / filename
                        
                        with open(output_path, 'wb') as f:
                            f.write(download_result.pdf_data)
                        
                        print(f"   Saved to: {output_path}")
                        
                        # Verify it's a valid PDF
                        with open(output_path, 'rb') as f:
                            header = f.read(8)
                            if header.startswith(b'%PDF'):
                                print("   ✅ Valid PDF confirmed")
                                return True
                            else:
                                print("   ❌ Not a valid PDF")
                    else:
                        print(f"   ❌ Download failed: {download_result.error}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
    except ImportError as e:
        print(f"❌ Cannot import Anna's Archive: {e}")
        return False
    
    return False

async def test_comprehensive_fallback():
    """Test comprehensive fallback strategy with Anna's Archive"""
    
    print("\n🎯 Testing Comprehensive Fallback Strategy")
    print("=" * 50)
    
    # Test DOI that might be on multiple sources
    test_doi = "10.1016/j.jcp.2019.07.031"  # Elsevier paper
    
    print(f"Testing comprehensive access for: {test_doi}")
    
    sources_tested = []
    
    # 1. Try Sci-Hub first
    try:
        from src.downloader.universal_downloader import SciHubDownloader
        
        print("\n1️⃣ Trying Sci-Hub...")
        sci_hub = SciHubDownloader()
        result = await sci_hub.download(test_doi)
        
        if result.success:
            print("   ✅ Sci-Hub found the paper!")
            sources_tested.append(("Sci-Hub", True))
        else:
            print(f"   ❌ Sci-Hub failed: {result.error}")
            sources_tested.append(("Sci-Hub", False))
    except Exception as e:
        print(f"   ❌ Sci-Hub error: {e}")
        sources_tested.append(("Sci-Hub", False))
    
    # 2. Try Anna's Archive as backup
    try:
        from src.downloader.universal_downloader import AnnaArchiveDownloader
        
        print("\n2️⃣ Trying Anna's Archive as backup...")
        anna = AnnaArchiveDownloader()
        
        # Search for the DOI or paper title
        results = await anna.search(test_doi)
        
        if results:
            print(f"   Found {len(results)} potential matches")
            result = await anna.download(results[0])
            
            if result.success:
                print("   ✅ Anna's Archive found the paper!")
                sources_tested.append(("Anna's Archive", True))
            else:
                print(f"   ❌ Anna's Archive download failed: {result.error}")
                sources_tested.append(("Anna's Archive", False))
        else:
            print("   ❌ No results found in Anna's Archive")
            sources_tested.append(("Anna's Archive", False))
            
    except Exception as e:
        print(f"   ❌ Anna's Archive error: {e}")
        sources_tested.append(("Anna's Archive", False))
    
    # 3. Show final strategy
    print("\n📊 Comprehensive Fallback Results:")
    for source, success in sources_tested:
        status = "✅" if success else "❌"
        print(f"   {status} {source}")
    
    # Check if we have any working sources
    working_sources = [s for s, success in sources_tested if success]
    
    if working_sources:
        print(f"\n🎉 Success! Paper available via: {', '.join(working_sources)}")
        return True
    else:
        print("\n⚠️ Paper not found in any automatic source")
        print("   Would fall back to manual Elsevier approaches")
        return False

async def main():
    # Test Anna's Archive directly
    anna_works = await test_annas_archive()
    
    # Test comprehensive fallback strategy
    fallback_works = await test_comprehensive_fallback()
    
    print("\n" + "=" * 60)
    print("🎯 ANNA'S ARCHIVE INTEGRATION RESULTS")
    print("=" * 60)
    
    if anna_works:
        print("✅ Anna's Archive is working and downloading PDFs")
    else:
        print("⚠️ Anna's Archive needs investigation")
    
    print("\n💡 Recommended Enhanced Strategy:")
    print("1. 🔄 Sci-Hub (primary - covers most papers)")
    print("2. 📚 Anna's Archive (backup - books + some papers)")
    print("3. 🏛️ Publisher direct (IEEE, SIAM - institutional)")
    print("4. 🍪 Manual Elsevier (cookie approach for recent papers)")
    
    if anna_works or fallback_works:
        print("\n🚀 Enhanced system provides even better coverage!")
    
    return anna_works

if __name__ == "__main__":
    asyncio.run(main())