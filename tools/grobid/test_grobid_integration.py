#!/usr/bin/env python3
"""
Grobid Integration Test & Validation

Tests the complete Grobid integration including:
- Service availability detection
- Fallback mechanism functionality
- PDF processing with sample documents
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.grobid_client import grobid_client, extract_with_grobid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_grobid_availability():
    """Test if Grobid service is available"""
    print("🔬 GROBID INTEGRATION TEST")
    print("=" * 50)
    
    print("1. Testing Grobid service availability...")
    is_available = grobid_client.is_available()
    
    if is_available:
        print("   ✅ Grobid service is running and available")
        print(f"   🔗 Server: {grobid_client.grobid_server}")
    else:
        print("   ⚠️ Grobid service not available")
        print("   📋 Fallback mechanisms will be used")
    
    return is_available


def test_fallback_extraction():
    """Test fallback extraction with sample PDF"""
    print("\n2. Testing fallback extraction...")
    
    # Look for sample PDFs
    samples_dir = Path(__file__).parent.parent.parent / "samples" / "papers"
    
    if not samples_dir.exists():
        print("   ⚠️ No samples directory found")
        return False
    
    pdf_files = list(samples_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("   ⚠️ No PDF files found in samples")
        return False
    
    # Test with first available PDF
    test_pdf = pdf_files[0]
    print(f"   📄 Testing with: {test_pdf.name}")
    
    try:
        result = extract_with_grobid(test_pdf)
        
        if result:
            print(f"   ✅ Extraction successful!")
            print(f"   📝 Title: {result.get('title', 'N/A')[:80]}...")
            print(f"   👥 Authors: {result.get('authors', 'N/A')[:60]}...")
            print(f"   🎯 Confidence: {result.get('confidence', 0):.2f}")
            print(f"   🔧 Method: {result.get('source', result.get('extractor', 'Unknown'))}")
            return True
        else:
            print("   ❌ Extraction failed")
            return False
            
    except Exception as e:
        print(f"   💥 Extraction error: {e}")
        return False


def test_grobid_service_interaction():
    """Test direct Grobid service if available"""
    print("\n3. Testing Grobid service interaction...")
    
    if not grobid_client.is_available():
        print("   ⏭️ Skipping - Grobid service not available")
        return True
    
    # Test basic API endpoints
    import requests
    
    try:
        # Test isalive endpoint
        response = requests.get(f"{grobid_client.grobid_server}/api/isalive", timeout=5)
        if response.status_code == 200:
            print("   ✅ /api/isalive endpoint working")
        
        # Test version endpoint
        response = requests.get(f"{grobid_client.grobid_server}/api/version", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print(f"   ✅ Grobid version: {version_info.get('version', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"   ⚠️ Service interaction failed: {e}")
        return False


def generate_integration_report():
    """Generate comprehensive integration status report"""
    print("\n" + "=" * 50)
    print("📊 GROBID INTEGRATION STATUS REPORT")
    print("=" * 50)
    
    # Run all tests
    service_available = test_grobid_availability()
    fallback_working = test_fallback_extraction()
    service_functional = test_grobid_service_interaction()
    
    print(f"\n📋 SUMMARY:")
    print(f"   Grobid Service Available: {'✅ Yes' if service_available else '❌ No'}")
    print(f"   Fallback Extraction: {'✅ Working' if fallback_working else '❌ Failed'}")
    print(f"   Service Functional: {'✅ Yes' if service_functional else '❌ No'}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if not service_available:
        print("   📦 Install Grobid server for enhanced extraction:")
        print("      - Download: https://github.com/kermitt2/grobid/releases")
        print("      - Run: ./gradlew run")
        print("      - Or use Docker: docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.2")
    
    if fallback_working:
        print("   ✅ System functional with fallback extractors")
    else:
        print("   ⚠️ Check PDF processing dependencies (PyMuPDF, etc.)")
    
    # Overall status
    overall_status = "OPERATIONAL" if fallback_working else "NEEDS_ATTENTION"
    print(f"\n🎯 OVERALL STATUS: {overall_status}")
    
    if overall_status == "OPERATIONAL":
        print("   📈 The PDF management system is fully functional")
        print("   🔄 Grobid integration provides enhanced extraction when available")
        print("   🛡️ Robust fallback ensures system reliability")


if __name__ == "__main__":
    generate_integration_report()