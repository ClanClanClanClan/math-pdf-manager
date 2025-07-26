#!/usr/bin/env python3
"""
Test Publishers Directly
=========================

Test the publisher implementations directly to see exactly what's happening
with institutional authentication.
"""

import asyncio
import sys
sys.path.append('src')

from pathlib import Path


def test_ieee_publisher_direct():
    """Test IEEE publisher directly."""
    print("🔍 TESTING IEEE PUBLISHER DIRECTLY")
    print("=" * 50)
    
    try:
        from publishers.ieee_publisher import IEEEPublisher
        from publishers import AuthenticationConfig
        import os
        
        # Create auth config
        auth_config = AuthenticationConfig(
            username=os.environ.get('ETH_USERNAME', ''),
            password=os.environ.get('ETH_PASSWORD', ''),
            institutional_login='eth'
        )
        
        # Create publisher instance
        ieee = IEEEPublisher(auth_config)
        
        print(f"✅ IEEE publisher created successfully")
        print(f"   Base URL: {ieee.base_url}")
        print(f"   Publisher: {ieee.publisher_name}")
        
        # Test authentication
        print(f"\n🔐 Testing IEEE authentication...")
        auth_result = ieee.authenticate()
        
        if auth_result:
            print(f"   ✅ Authentication successful!")
        else:
            print(f"   ❌ Authentication failed")
        
        # Test download
        test_paper_id = "7780459"  # ResNet paper
        download_path = Path("test_publishers_direct") / f"ieee_{test_paper_id}.pdf"
        
        print(f"\n📄 Testing IEEE download...")
        print(f"   Paper ID: {test_paper_id}")
        print(f"   Target: {download_path}")
        
        result = ieee.download_paper(test_paper_id, download_path)
        
        if result.success:
            print(f"   ✅ Download successful!")
            print(f"      File: {result.file_path}")
            if download_path.exists():
                print(f"      Size: {download_path.stat().st_size:,} bytes")
        else:
            print(f"   ❌ Download failed: {result.error_message}")
        
    except Exception as e:
        print(f"   💥 IEEE publisher test failed: {e}")


def test_siam_publisher_direct():
    """Test SIAM publisher directly."""
    print("\n\n🔍 TESTING SIAM PUBLISHER DIRECTLY")
    print("=" * 50)
    
    try:
        from publishers.siam_publisher import SIAMPublisher
        from publishers import AuthenticationConfig
        import os
        
        # Create auth config
        auth_config = AuthenticationConfig(
            username=os.environ.get('ETH_USERNAME', ''),
            password=os.environ.get('ETH_PASSWORD', ''),
            institutional_login='eth'
        )
        
        # Create publisher instance
        siam = SIAMPublisher(auth_config)
        
        print(f"✅ SIAM publisher created successfully")
        print(f"   Base URL: {siam.base_url}")
        print(f"   Publisher: {siam.publisher_name}")
        
        # Test authentication
        print(f"\n🔐 Testing SIAM authentication...")
        auth_result = siam.authenticate()
        
        if auth_result:
            print(f"   ✅ Authentication successful!")
        else:
            print(f"   ❌ Authentication failed")
        
        # Test download
        test_paper_doi = "10.1137/S0097539795293172"
        download_path = Path("test_publishers_direct") / f"siam_paper.pdf"
        
        print(f"\n📄 Testing SIAM download...")
        print(f"   Paper DOI: {test_paper_doi}")
        print(f"   Target: {download_path}")
        
        result = siam.download_paper(test_paper_doi, download_path)
        
        if result.success:
            print(f"   ✅ Download successful!")
            print(f"      File: {result.file_path}")
            if download_path.exists():
                print(f"      Size: {download_path.stat().st_size:,} bytes")
        else:
            print(f"   ❌ Download failed: {result.error_message}")
        
    except Exception as e:
        print(f"   💥 SIAM publisher test failed: {e}")


def test_springer_publisher_direct():
    """Test Springer publisher directly."""
    print("\n\n🔍 TESTING SPRINGER PUBLISHER DIRECTLY")
    print("=" * 50)
    
    try:
        from publishers.springer_publisher import SpringerPublisher
        from publishers import AuthenticationConfig
        import os
        
        # Create auth config
        auth_config = AuthenticationConfig(
            username=os.environ.get('ETH_USERNAME', ''),
            password=os.environ.get('ETH_PASSWORD', ''),
            institutional_login='eth'
        )
        
        # Create publisher instance
        springer = SpringerPublisher(auth_config)
        
        print(f"✅ Springer publisher created successfully")
        print(f"   Base URL: {springer.base_url}")
        print(f"   Publisher: {springer.publisher_name}")
        
        # Test authentication
        print(f"\n🔐 Testing Springer authentication...")
        auth_result = springer.authenticate()
        
        if auth_result:
            print(f"   ✅ Authentication successful!")
        else:
            print(f"   ❌ Authentication failed")
        
        # Test download
        test_paper_doi = "10.1007/978-3-319-07443-6_15"
        download_path = Path("test_publishers_direct") / f"springer_paper.pdf"
        
        print(f"\n📄 Testing Springer download...")
        print(f"   Paper DOI: {test_paper_doi}")
        print(f"   Target: {download_path}")
        
        result = springer.download_paper(test_paper_doi, download_path)
        
        if result.success:
            print(f"   ✅ Download successful!")
            print(f"      File: {result.file_path}")
            if download_path.exists():
                print(f"      Size: {download_path.stat().st_size:,} bytes")
        else:
            print(f"   ❌ Download failed: {result.error_message}")
        
    except Exception as e:
        print(f"   💥 Springer publisher test failed: {e}")


def test_publisher_registry():
    """Test the publisher registry system."""
    print("\n\n🔍 TESTING PUBLISHER REGISTRY")
    print("=" * 50)
    
    try:
        from publishers import publisher_registry
        
        print(f"✅ Publisher registry imported successfully")
        
        # Check registered publishers
        registered = publisher_registry.get_all_publishers()
        print(f"📊 Registered publishers: {len(registered)}")
        
        for name, publisher_class in registered.items():
            print(f"   • {name}: {publisher_class.__name__}")
        
        # Test publisher creation
        for name in ['ieee', 'siam', 'springer']:
            try:
                publisher = publisher_registry.get_publisher(name)
                if publisher:
                    print(f"   ✅ {name} publisher factory works")
                else:
                    print(f"   ❌ {name} publisher factory failed")
            except Exception as e:
                print(f"   💥 {name} publisher factory error: {e}")
        
    except Exception as e:
        print(f"   💥 Publisher registry test failed: {e}")


def test_authentication_config():
    """Test authentication configuration."""
    print("\n\n🔍 TESTING AUTHENTICATION CONFIG")
    print("=" * 50)
    
    try:
        from publishers import AuthenticationConfig
        import os
        
        # Test config creation
        auth_config = AuthenticationConfig(
            username=os.environ.get('ETH_USERNAME', 'test_user'),
            password=os.environ.get('ETH_PASSWORD', 'test_pass'),
            institutional_login='eth'
        )
        
        print(f"✅ AuthenticationConfig created successfully")
        print(f"   Username: {auth_config.username[:3]}***" if auth_config.username else "   Username: None")
        print(f"   Password: {'*' * len(auth_config.password)}" if auth_config.password else "   Password: None")
        print(f"   Institution: {auth_config.institutional_login}")
        
        # Check credential manager integration
        try:
            from secure_credential_manager import get_credential_manager
            cm = get_credential_manager()
            eth_username, eth_password = cm.get_eth_credentials()
            
            print(f"\n🔐 Credential Manager Integration:")
            print(f"   ✅ Credential manager available")
            print(f"   Username from CM: {eth_username[:3]}***" if eth_username else "   Username from CM: None")
            print(f"   Password from CM: {'*' * len(eth_password)}" if eth_password else "   Password from CM: None")
            
        except Exception as e:
            print(f"   💥 Credential manager error: {e}")
        
    except Exception as e:
        print(f"   💥 Authentication config test failed: {e}")


def main():
    """Run all publisher tests."""
    print("🧪 COMPREHENSIVE PUBLISHER TESTING")
    print("=" * 80)
    print("Testing publisher implementations directly to diagnose issues.\n")
    
    # Create output directory
    Path("test_publishers_direct").mkdir(exist_ok=True)
    
    # Test authentication and registry first
    test_authentication_config()
    test_publisher_registry()
    
    # Test each publisher
    test_ieee_publisher_direct()
    test_siam_publisher_direct() 
    test_springer_publisher_direct()
    
    print("\n" + "=" * 80)
    print("🏁 PUBLISHER TEST SUMMARY")
    print("=" * 80)
    print("This test shows:")
    print("1. 🏗️  Publisher classes instantiate correctly")
    print("2. 🔐 Authentication methods are called properly")
    print("3. 📄 Download methods attempt to fetch papers")
    print("4. 🔧 Any errors in the authentication flow")
    print("\nIf authentication fails but classes work, the issue is:")
    print("- Browser automation timing/selectors need adjustment")
    print("- Network access requirements for institutional login")
    print("- Publisher website UI changes")


if __name__ == "__main__":
    main()