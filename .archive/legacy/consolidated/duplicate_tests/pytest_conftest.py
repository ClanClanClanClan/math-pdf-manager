"""
conftest.py - pytest configuration and shared fixtures
"""

import pytest
import logging
import sys

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

# Add project root to Python path
sys.path.insert(0, '.')

# pytest options
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "stress: mark test as a stress test" 
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )