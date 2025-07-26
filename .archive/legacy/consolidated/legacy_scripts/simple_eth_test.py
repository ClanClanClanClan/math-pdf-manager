#!/usr/bin/env python3
"""
Simple ETH Authentication Test
==============================

Simple, focused test of ETH authentication without complex browser automation.
Tests each component separately to identify specific issues.
"""

import os
import tempfile
import logging
from pathlib import Path

from auth_manager import get_auth_manager
from secure_credential_manager import get_credential_manager
from scripts.downloader import InstitutionalStrategy, DownloadResult

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("simple_eth_test")

def test_credentials():
    """Test ETH credential availability."""
    logger.info("🔐 Testing ETH Credentials")
    logger.info("=" * 40)
    
    manager = get_credential_manager()
    username, password = manager.get_eth_credentials()
    
    logger.info(f"  Username: {username}")
    logger.info(f"  Password: {'***' if password else 'NOT SET'}")
    
    available = manager.list_available_credentials()
    logger.info("  Available credentials:")
    for cred, source in available.items():
        logger.info(f"    {cred}: {source}")
    
    has_creds = username and password
    logger.info(f"  Status: {'✅ Available' if has_creds else '❌ Missing'}")
    return has_creds

def test_auth_configs():
    """Test authentication configurations."""
    logger.info("\n⚙️  Testing Authentication Configs")
    logger.info("=" * 40)
    
    auth_manager = get_auth_manager()
    eth_services = [name for name in auth_manager.configs.keys() if name.startswith('eth_')]
    
    logger.info(f"  Found {len(eth_services)} ETH services:")
    
    results = {}
    for service in eth_services:
        config = auth_manager.configs[service]
        publisher = service.replace('eth_', '')
        
        # Check config completeness
        issues = []
        if not config.username:
            issues.append("Missing username")
        if not config.base_url and not config.shibboleth_idp:
            issues.append("Missing URLs")
        if config.auth_method.value != "shibboleth":
            issues.append(f"Wrong auth method: {config.auth_method.value}")
        
        status = "✅ Valid" if not issues else f"❌ Issues: {', '.join(issues)}"
        logger.info(f"    {publisher}: {status}")
        results[publisher] = len(issues) == 0
    
    return results

def test_institutional_strategy():
    """Test institutional download strategy without browser automation."""
    logger.info("\n📥 Testing Institutional Download Strategy")
    logger.info("=" * 40)
    
    # Test with mock metadata that would trigger institutional access
    test_metadata = {
        'title': 'Test Paper',
        'DOI': '10.1109/TEST.2023.1234567',
        'is_open_access': False,
        'best_oa_location': None,
        'oa_locations': []
    }
    
    results = {}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test each ETH service
        auth_manager = get_auth_manager()
        eth_services = [name for name in auth_manager.configs.keys() if name.startswith('eth_')]
        
        for service in eth_services:
            publisher = service.replace('eth_', '')
            logger.info(f"  Testing {publisher}...")
            
            try:
                # Create institutional strategy with auth service
                strategy = InstitutionalStrategy(auth_service=service)
                
                # Test if it can handle the metadata
                can_handle = strategy.can_handle(test_metadata)
                logger.info(f"    Can handle metadata: {'✅' if can_handle else '❌'}")
                
                if can_handle:
                    # Test URL generation
                    urls = strategy.get_download_urls(test_metadata)
                    logger.info(f"    Generated URLs: {len(urls)}")
                    for url in urls:
                        logger.info(f"      - {url}")
                    
                    # Test auth service determination (without actual download)
                    if hasattr(strategy, '_determine_auth_service'):
                        for url in urls:
                            auth_service = strategy._determine_auth_service(url)
                            logger.info(f"    Auth service for {url}: {auth_service or 'None'}")
                
                results[publisher] = True
                logger.info(f"    Status: ✅ Strategy working")
                
            except Exception as e:
                logger.error(f"    Status: ❌ Error: {e}")
                results[publisher] = False
    
    return results

def test_session_creation_simple():
    """Test session creation without browser automation."""
    logger.info("\n🔗 Testing Session Creation (Non-Browser)")
    logger.info("=" * 40)
    
    auth_manager = get_auth_manager()
    eth_services = [name for name in auth_manager.configs.keys() if name.startswith('eth_')]
    
    results = {}
    
    for service in eth_services:
        publisher = service.replace('eth_', '')
        logger.info(f"  Testing {publisher}...")
        
        try:
            config = auth_manager.configs[service]
            
            # Check if credentials are available
            username = config.username
            password = auth_manager.get_credential(service, username)
            
            logger.info(f"    Username: {username}")
            logger.info(f"    Password: {'Available' if password else 'Missing'}")
            
            if password:
                logger.info(f"    Status: ✅ Credentials available")
                results[publisher] = True
            else:
                logger.info(f"    Status: ❌ No password found")
                results[publisher] = False
                
        except Exception as e:
            logger.error(f"    Status: ❌ Error: {e}")
            results[publisher] = False
    
    return results

def test_doi_url_generation():
    """Test DOI URL generation for each publisher."""
    logger.info("\n🔗 Testing DOI URL Generation")
    logger.info("=" * 40)
    
    test_dois = {
        'ieee': '10.1109/ACCESS.2023.1234567',
        'acm': '10.1145/1234567.7654321', 
        'springer': '10.1007/s10994-023-06123-4',
        'elsevier': '10.1016/j.neunet.2023.01.012',
        'wiley': '10.1002/widm.1234'
    }
    
    auth_manager = get_auth_manager()
    eth_services = [name for name in auth_manager.configs.keys() if name.startswith('eth_')]
    
    for service in eth_services:
        publisher = service.replace('eth_', '')
        if publisher in test_dois:
            doi = test_dois[publisher]
            
            logger.info(f"  {publisher.upper()}:")
            logger.info(f"    DOI: {doi}")
            logger.info(f"    DOI URL: https://doi.org/{doi}")
            
            # Check if this would be recognized by institutional strategy
            strategy = InstitutionalStrategy(auth_service=service)
            metadata = {'DOI': doi}
            
            urls = strategy.get_download_urls(metadata)
            for url in urls:
                logger.info(f"    Generated: {url}")

def run_comprehensive_test():
    """Run all simple tests."""
    logger.info("🧪 Simple ETH Authentication Test Suite")
    logger.info("=" * 60)
    
    # Test 1: Credentials
    creds_ok = test_credentials()
    
    # Test 2: Auth configs
    config_results = test_auth_configs()
    
    # Test 3: Session creation (simple)
    session_results = test_session_creation_simple()
    
    # Test 4: Institutional strategy
    strategy_results = test_institutional_strategy()
    
    # Test 5: DOI URL generation
    test_doi_url_generation()
    
    # Summary
    logger.info("\n📊 Test Summary")
    logger.info("=" * 40)
    
    logger.info(f"Credentials: {'✅ Available' if creds_ok else '❌ Missing'}")
    
    config_passed = sum(config_results.values())
    config_total = len(config_results)
    logger.info(f"Auth Configs: {config_passed}/{config_total} valid")
    
    session_passed = sum(session_results.values())
    session_total = len(session_results)
    logger.info(f"Session Creds: {session_passed}/{session_total} available")
    
    strategy_passed = sum(strategy_results.values())
    strategy_total = len(strategy_results)
    logger.info(f"Strategy Tests: {strategy_passed}/{strategy_total} working")
    
    # Detailed results
    logger.info("\n📋 Publisher Status:")
    publishers = set(config_results.keys()) | set(session_results.keys()) | set(strategy_results.keys())
    
    for publisher in sorted(publishers):
        config_ok = config_results.get(publisher, False)
        session_ok = session_results.get(publisher, False)
        strategy_ok = strategy_results.get(publisher, False)
        
        status = "✅" if all([config_ok, session_ok, strategy_ok]) else "⚠️"
        logger.info(f"  {status} {publisher}: Config={config_ok}, Creds={session_ok}, Strategy={strategy_ok}")
    
    # Overall status
    all_systems = creds_ok and config_passed == config_total
    logger.info(f"\n🏁 Overall Status: {'✅ Ready for testing' if all_systems else '⚠️ Issues detected'}")
    
    if not all_systems:
        logger.info("\n🔧 Next Steps:")
        if not creds_ok:
            logger.info("  1. Set up ETH credentials: export ETH_USERNAME='...' ETH_password = os.environ.get("PASSWORD", "...")  # TODO: Remove default value")
        if config_passed < config_total:
            logger.info("  2. Re-run automated setup: python automated_eth_setup.py")
        logger.info("  3. Check specific publisher configurations above")

if __name__ == "__main__":
    run_comprehensive_test()