#!/usr/bin/env python3
"""
Test package for Enhanced Acquisition Engine

Comprehensive test suite for the academic paper acquisition system including:
- Unit tests for all components
- Integration tests for workflows
- Mock tests for external services
- Configuration testing
- Performance and stress testing
"""

# Test configuration
TEST_CONFIG = {
    "enable_network_tests": False,  # Set to True to enable real network tests
    "test_timeout": 30,  # Timeout for individual tests
    "temp_dir_prefix": "apm_test_",
    "mock_responses": True,  # Use mock responses by default
}

# Test data
SAMPLE_PAPERS = [
    {
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        "doi": "10.1109/ICCV.2017.97",
        "arxiv_id": "1706.03762",
        "url": "https://arxiv.org/abs/1706.03762",
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "authors": ["Jacob Devlin", "Ming-Wei Chang"],
        "arxiv_id": "1810.04805",
        "url": "https://arxiv.org/abs/1810.04805",
    },
    {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": ["Kaiming He", "Xiangyu Zhang"],
        "doi": "10.1109/CVPR.2016.90",
        "arxiv_id": "1512.03385",
    },
]

# Mock data for testing
MOCK_UNPAYWALL_RESPONSES = {
    "10.1371/journal.pone.0000308": {
        "doi": "10.1371/journal.pone.0000308",
        "is_oa": True,
        "best_oa_location": {
            "url_for_pdf": "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000308&type=printable"
        },
        "oa_locations": [
            {
                "url": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0000308",
                "url_for_pdf": "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000308&type=printable",
            }
        ],
        "journal_is_oa": True,
        "has_repository_copy": False,
    },
    "10.1234/closed-access": {
        "doi": "10.1234/closed-access",
        "is_oa": False,
        "best_oa_location": None,
        "oa_locations": [],
        "journal_is_oa": False,
        "has_repository_copy": False,
    },
}

__all__ = ["TEST_CONFIG", "SAMPLE_PAPERS", "MOCK_UNPAYWALL_RESPONSES"]
