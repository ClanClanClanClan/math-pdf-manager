#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive tests for core.models module
"""

import pytest
from datetime import datetime
from pathlib import Path
from core.models import (
    # Enums
    MetadataSource,
    DocumentType,
    ValidationSeverity,
    # Data classes
    Author,
    PDFMetadata,
    ValidationIssue,
    ValidationResult,
    ScanResult,
    DuplicateGroup,
    ProcessingStats
)


class TestMetadataSource:
    """Test MetadataSource enum"""
    
    def test_all_values(self):
        """Test all metadata source values"""
        expected_values = {
            "unknown", "filename", "pdf_text", "pdf_metadata",
            "arxiv_api", "crossref_api", "scholar_api", "grobid", "ocr", "manual"
        }
        actual_values = {source.value for source in MetadataSource}
        assert actual_values == expected_values
    
    def test_enum_access(self):
        """Test enum member access"""
        assert MetadataSource.UNKNOWN.value == "unknown"
        assert MetadataSource.ARXIV_API.value == "arxiv_api"
        assert MetadataSource.MANUAL.value == "manual"


class TestDocumentType:
    """Test DocumentType enum"""
    
    def test_all_values(self):
        """Test all document type values"""
        expected_values = {
            "unknown", "journal_article", "conference_paper", "arxiv_preprint",
            "book", "book_chapter", "thesis", "technical_report", "working_paper"
        }
        actual_values = {doc_type.value for doc_type in DocumentType}
        assert actual_values == expected_values
    
    def test_enum_access(self):
        """Test enum member access"""
        assert DocumentType.JOURNAL_ARTICLE.value == "journal_article"
        assert DocumentType.ARXIV_PREPRINT.value == "arxiv_preprint"
        assert DocumentType.UNKNOWN.value == "unknown"


class TestValidationSeverity:
    """Test ValidationSeverity enum"""
    
    def test_all_values(self):
        """Test all validation severity values"""
        expected_values = {"info", "warning", "error", "critical"}
        actual_values = {severity.value for severity in ValidationSeverity}
        assert actual_values == expected_values
    
    def test_enum_access(self):
        """Test enum member access"""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.CRITICAL.value == "critical"


class TestAuthor:
    """Test Author dataclass"""
    
    def test_default_creation(self):
        """Test default author creation"""
        author = Author()
        assert author.given_name == ""
        assert author.family_name == ""
        assert author.full_name == ""
        assert author.initials == ""
        assert author.suffix is None
        assert author.affiliation is None
        assert author.orcid is None
        assert author.email is None
    
    def test_basic_author(self):
        """Test basic author with given and family names"""
        author = Author(given_name="John", family_name="Doe")
        assert author.given_name == "John"
        assert author.family_name == "Doe"
        assert author.full_name == "John Doe"  # Computed in __post_init__
        assert author.initials == "J."  # Computed in __post_init__
    
    def test_full_name_override(self):
        """Test that explicit full_name is preserved"""
        author = Author(
            given_name="John",
            family_name="Doe",
            full_name="Dr. John A. Doe"
        )
        assert author.full_name == "Dr. John A. Doe"  # Should not be overwritten
    
    def test_initials_override(self):
        """Test that explicit initials are preserved"""
        author = Author(
            given_name="John Andrew",
            family_name="Doe",
            initials="J.A.D."
        )
        assert author.initials == "J.A.D."  # Should not be overwritten
    
    def test_multiple_given_names(self):
        """Test author with multiple given names"""
        author = Author(given_name="John Andrew Michael")
        assert author.initials == "J.A.M."
    
    def test_complete_author(self):
        """Test author with all fields"""
        author = Author(
            given_name="Marie",
            family_name="Curie",
            suffix="Ph.D.",
            affiliation="University of Paris",
            orcid="0000-0000-0000-0000",
            email="marie@curie.fr"
        )
        
        assert author.full_name == "Marie Curie"
        assert author.initials == "M."
        assert author.suffix == "Ph.D."
        assert author.affiliation == "University of Paris"
        assert author.orcid == "0000-0000-0000-0000"
        assert author.email == "marie@curie.fr"
    
    def test_edge_cases(self):
        """Test edge cases for name processing"""
        # Empty given name
        author1 = Author(given_name="", family_name="Doe")
        assert author1.full_name == ""  # No full name computed
        assert author1.initials == ""
        
        # Single letter given name
        author2 = Author(given_name="J", family_name="Doe")
        assert author2.full_name == "J Doe"
        assert author2.initials == "J."


class TestPDFMetadata:
    """Test PDFMetadata dataclass"""
    
    def test_default_creation(self):
        """Test default metadata creation"""
        metadata = PDFMetadata()
        
        # Basic metadata defaults
        assert metadata.title == "Unknown Title"
        assert metadata.authors == []
        assert metadata.authors_string == "Unknown"
        assert metadata.year is None
        
        # Source information defaults
        assert metadata.source == MetadataSource.UNKNOWN
        assert metadata.confidence == 0.0
        assert metadata.filename == ""
        assert metadata.path == Path()
        
        # Document classification defaults
        assert metadata.document_type == DocumentType.UNKNOWN
        assert metadata.repository_type is None
        assert metadata.language == "en"
        assert metadata.is_published is False
        
        # Content metadata defaults
        assert metadata.keywords == []
        assert metadata.categories == []
        assert metadata.page_count == 0
    
    def test_complete_metadata(self):
        """Test metadata with all fields populated"""
        authors = [Author(given_name="John", family_name="Doe")]
        path = Path("/test/paper.pdf")
        creation_date = datetime(2023, 1, 1)
        
        metadata = PDFMetadata(
            title="Test Paper",
            authors=authors,
            authors_string="John Doe",
            year=2023,
            source=MetadataSource.ARXIV_API,
            confidence=0.95,
            filename="paper.pdf",
            path=path,
            document_type=DocumentType.ARXIV_PREPRINT,
            language="en",
            is_published=True,
            doi="10.1000/test",
            arxiv_id="2301.12345",
            abstract="This is a test paper",
            keywords=["machine learning", "mathematics"],
            categories=["cs.LG", "math.ST"],
            page_count=10,
            text_quality=0.98,
            extraction_method="grobid",
            file_size=1024000,
            creation_date=creation_date,
            processing_time=2.5,
            warnings=["Minor OCR issue"],
            extraction_details={"method": "grobid", "version": "0.7.0"}
        )
        
        assert metadata.title == "Test Paper"
        assert len(metadata.authors) == 1
        assert metadata.authors[0].full_name == "John Doe"
        assert metadata.year == 2023
        assert metadata.source == MetadataSource.ARXIV_API
        assert metadata.confidence == 0.95
        assert metadata.document_type == DocumentType.ARXIV_PREPRINT
        assert metadata.doi == "10.1000/test"
        assert metadata.keywords == ["machine learning", "mathematics"]
        assert metadata.page_count == 10
        assert metadata.processing_time == 2.5
    
    def test_identifier_fields(self):
        """Test all identifier fields"""
        metadata = PDFMetadata(
            doi="10.1000/test",
            arxiv_id="2301.12345",
            isbn="978-3-16-148410-0",
            issn="1234-5678",
            pmid="12345678"
        )
        
        assert metadata.doi == "10.1000/test"
        assert metadata.arxiv_id == "2301.12345"
        assert metadata.isbn == "978-3-16-148410-0"
        assert metadata.issn == "1234-5678"
        assert metadata.pmid == "12345678"


class TestValidationIssue:
    """Test ValidationIssue dataclass"""
    
    def test_basic_issue(self):
        """Test basic validation issue"""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category="title",
            message="Title may need capitalization fixes"
        )
        
        assert issue.severity == ValidationSeverity.WARNING
        assert issue.category == "title"
        assert issue.message == "Title may need capitalization fixes"
        assert issue.field is None
        assert issue.fix_available is False
    
    def test_complete_issue(self):
        """Test validation issue with all fields"""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category="author",
            message="Invalid author format",
            field="authors",
            current_value="john doe",
            suggested_value="John Doe",
            line_number=5,
            position=12,
            context="author: john doe",
            fix_available=True
        )
        
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.field == "authors"
        assert issue.current_value == "john doe"
        assert issue.suggested_value == "John Doe"
        assert issue.line_number == 5
        assert issue.position == 12
        assert issue.context == "author: john doe"
        assert issue.fix_available is True
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        issue = ValidationIssue(
            severity=ValidationSeverity.WARNING,
            category="filename",
            message="Filename contains special characters",
            field="filename",
            current_value="file@name.pdf",
            suggested_value="file_name.pdf",
            fix_available=True
        )
        
        expected_dict = {
            'severity': 'warning',
            'category': 'filename',
            'message': 'Filename contains special characters',
            'field': 'filename',
            'current_value': 'file@name.pdf',
            'suggested_value': 'file_name.pdf',
            'line_number': None,
            'position': None,
            'context': None,
            'fix_available': True
        }
        
        assert issue.to_dict() == expected_dict


class TestValidationResult:
    """Test ValidationResult dataclass"""
    
    def test_valid_result(self):
        """Test valid validation result"""
        result = ValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert result.issues == []
        assert result.metadata is None
        assert result.suggested_filename is None
        assert result.validation_time == 0.0
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.has_auto_fixable_issues is False
    
    def test_result_with_issues(self):
        """Test validation result with various issues"""
        issues = [
            ValidationIssue(ValidationSeverity.WARNING, "title", "Warning message"),
            ValidationIssue(ValidationSeverity.ERROR, "author", "Error message"),
            ValidationIssue(ValidationSeverity.ERROR, "filename", "Another error"),
            ValidationIssue(ValidationSeverity.INFO, "metadata", "Info message", fix_available=True)
        ]
        
        result = ValidationResult(
            is_valid=False,
            issues=issues,
            suggested_filename="corrected_filename.pdf",
            validation_time=1.5
        )
        
        assert result.is_valid is False
        assert len(result.issues) == 4
        assert result.error_count == 2
        assert result.warning_count == 1
        assert result.has_auto_fixable_issues is True
        assert result.suggested_filename == "corrected_filename.pdf"
        assert result.validation_time == 1.5
    
    def test_get_issues_by_severity(self):
        """Test filtering issues by severity"""
        issues = [
            ValidationIssue(ValidationSeverity.WARNING, "cat1", "Warning 1"),
            ValidationIssue(ValidationSeverity.ERROR, "cat2", "Error 1"),
            ValidationIssue(ValidationSeverity.WARNING, "cat3", "Warning 2"),
            ValidationIssue(ValidationSeverity.CRITICAL, "cat4", "Critical 1")
        ]
        
        result = ValidationResult(is_valid=False, issues=issues)
        
        warnings = result.get_issues_by_severity(ValidationSeverity.WARNING)
        errors = result.get_issues_by_severity(ValidationSeverity.ERROR)
        critical = result.get_issues_by_severity(ValidationSeverity.CRITICAL)
        info = result.get_issues_by_severity(ValidationSeverity.INFO)
        
        assert len(warnings) == 2
        assert len(errors) == 1
        assert len(critical) == 1
        assert len(info) == 0
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        issues = [
            ValidationIssue(ValidationSeverity.WARNING, "test", "Warning", fix_available=True),
            ValidationIssue(ValidationSeverity.ERROR, "test", "Error")
        ]
        
        result = ValidationResult(
            is_valid=False,
            issues=issues,
            suggested_filename="test.pdf",
            validation_time=2.0
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['is_valid'] is False
        assert len(result_dict['issues']) == 2
        assert result_dict['suggested_filename'] == "test.pdf"
        assert result_dict['validation_time'] == 2.0
        assert result_dict['error_count'] == 1
        assert result_dict['warning_count'] == 1
        assert result_dict['has_auto_fixable_issues'] is True


class TestScanResult:
    """Test ScanResult dataclass"""
    
    def test_default_scan_result(self):
        """Test default scan result"""
        result = ScanResult()
        
        assert result.total_files == 0
        assert result.pdf_files == 0
        assert result.skipped_files == 0
        assert result.error_files == 0
        assert result.scan_time == 0.0
        assert result.files == []
        assert result.errors == {}
        assert result.statistics == {}
    
    def test_complete_scan_result(self):
        """Test scan result with data"""
        files = [Path("/test/file1.pdf"), Path("/test/file2.pdf")]
        errors = {Path("/test/bad.pdf"): "Permission denied"}
        stats = {"directories_scanned": 5, "largest_file": "big.pdf"}
        
        result = ScanResult(
            total_files=10,
            pdf_files=8,
            skipped_files=1,
            error_files=1,
            scan_time=5.2,
            files=files,
            errors=errors,
            statistics=stats
        )
        
        assert result.total_files == 10
        assert result.pdf_files == 8
        assert result.skipped_files == 1
        assert result.error_files == 1
        assert result.scan_time == 5.2
        assert len(result.files) == 2
        assert len(result.errors) == 1
        assert result.statistics["directories_scanned"] == 5


class TestDuplicateGroup:
    """Test DuplicateGroup dataclass"""
    
    def test_basic_duplicate_group(self):
        """Test basic duplicate group"""
        master = Path("/test/original.pdf")
        duplicates = [Path("/test/copy1.pdf"), Path("/test/copy2.pdf")]
        similarities = {
            Path("/test/copy1.pdf"): 0.95,
            Path("/test/copy2.pdf"): 0.88
        }
        metadata = {
            master: PDFMetadata(title="Original"),
            Path("/test/copy1.pdf"): PDFMetadata(title="Copy 1"),
            Path("/test/copy2.pdf"): PDFMetadata(title="Copy 2")
        }
        
        group = DuplicateGroup(
            master_file=master,
            duplicates=duplicates,
            similarity_scores=similarities,
            metadata=metadata
        )
        
        assert group.master_file == master
        assert len(group.duplicates) == 2
        assert group.similarity_scores[Path("/test/copy1.pdf")] == 0.95
        assert group.suggested_action == "review"  # default
        assert group.size == 3  # master + 2 duplicates
    
    def test_size_property(self):
        """Test size property calculation"""
        master = Path("/test/master.pdf")
        duplicates = [Path("/test/dup1.pdf")]
        
        group = DuplicateGroup(
            master_file=master,
            duplicates=duplicates,
            similarity_scores={Path("/test/dup1.pdf"): 0.9},
            metadata={}
        )
        
        assert group.size == 2  # 1 master + 1 duplicate
        
        # Test with more duplicates
        group.duplicates.extend([Path("/test/dup2.pdf"), Path("/test/dup3.pdf")])
        assert group.size == 4  # 1 master + 3 duplicates
    
    def test_total_size_bytes_nonexistent_files(self):
        """Test total_size_bytes with nonexistent files"""
        master = Path("/nonexistent/master.pdf")
        duplicates = [Path("/nonexistent/dup.pdf")]
        
        group = DuplicateGroup(
            master_file=master,
            duplicates=duplicates,
            similarity_scores={Path("/nonexistent/dup.pdf"): 0.9},
            metadata={}
        )
        
        # Should not crash with nonexistent files
        assert group.total_size_bytes == 0


class TestProcessingStats:
    """Test ProcessingStats dataclass"""
    
    def test_default_stats(self):
        """Test default processing stats"""
        stats = ProcessingStats()
        
        assert isinstance(stats.start_time, datetime)
        assert stats.end_time is None
        assert stats.files_processed == 0
        assert stats.files_succeeded == 0
        assert stats.files_failed == 0
        assert stats.files_skipped == 0
        assert stats.total_processing_time == 0.0
        assert stats.average_processing_time == 0.0
        assert stats.peak_memory_usage == 0
        assert stats.api_calls_made == {}
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
    
    def test_stats_with_data(self):
        """Test processing stats with data"""
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        api_calls = {"arxiv": 5, "crossref": 3}
        
        stats = ProcessingStats(
            start_time=start_time,
            files_processed=10,
            files_succeeded=8,
            files_failed=1,
            files_skipped=1,
            peak_memory_usage=512000000,
            api_calls_made=api_calls,
            cache_hits=15,
            cache_misses=5
        )
        
        assert stats.start_time == start_time
        assert stats.files_processed == 10
        assert stats.files_succeeded == 8
        assert stats.files_failed == 1
        assert stats.files_skipped == 1
        assert stats.api_calls_made["arxiv"] == 5
        assert stats.cache_hits == 15
    
    def test_complete_method(self):
        """Test complete method calculations"""
        start_time = datetime(2023, 1, 1, 10, 0, 0)
        stats = ProcessingStats(
            start_time=start_time,
            files_processed=5
        )
        
        # Test the complete method - since we can't easily mock datetime.now(),
        # we'll just verify that it sets end_time and calculates times
        stats.complete()
        
        assert stats.end_time is not None
        assert stats.total_processing_time > 0
        assert stats.average_processing_time > 0
        # Verify calculation logic
        expected_avg = stats.total_processing_time / stats.files_processed
        assert abs(stats.average_processing_time - expected_avg) < 0.001
    
    def test_complete_method_zero_files(self):
        """Test complete method with zero files processed"""
        stats = ProcessingStats(files_processed=0)
        stats.complete()
        
        # Should not divide by zero
        assert stats.average_processing_time == 0.0


class TestDataClassInteroperability:
    """Test how data classes work together"""
    
    def test_metadata_with_authors(self):
        """Test metadata containing authors"""
        authors = [
            Author(given_name="Alice", family_name="Smith"),
            Author(given_name="Bob", family_name="Jones", orcid="0000-0000-0000-0001")
        ]
        
        metadata = PDFMetadata(
            title="Collaborative Research",
            authors=authors,
            year=2023
        )
        
        assert len(metadata.authors) == 2
        assert metadata.authors[0].full_name == "Alice Smith"
        assert metadata.authors[1].orcid == "0000-0000-0000-0001"
    
    def test_validation_result_with_metadata(self):
        """Test validation result containing metadata"""
        metadata = PDFMetadata(title="Test Paper", year=2023)
        issues = [
            ValidationIssue(ValidationSeverity.WARNING, "title", "Check capitalization")
        ]
        
        result = ValidationResult(
            is_valid=True,  # Can be valid with warnings
            issues=issues,
            metadata=metadata
        )
        
        assert result.metadata.title == "Test Paper"
        assert result.warning_count == 1
        assert result.error_count == 0
    
    def test_duplicate_group_with_metadata(self):
        """Test duplicate group with full metadata"""
        metadata1 = PDFMetadata(
            title="Original Paper",
            authors=[Author(given_name="John", family_name="Doe")]
        )
        metadata2 = PDFMetadata(
            title="Original Paper", 
            authors=[Author(given_name="J.", family_name="Doe")]
        )
        
        group = DuplicateGroup(
            master_file=Path("/test/original.pdf"),
            duplicates=[Path("/test/copy.pdf")],
            similarity_scores={Path("/test/copy.pdf"): 0.92},
            metadata={
                Path("/test/original.pdf"): metadata1,
                Path("/test/copy.pdf"): metadata2
            }
        )
        
        master_metadata = group.metadata[group.master_file]
        assert master_metadata.title == "Original Paper"
        assert master_metadata.authors[0].full_name == "John Doe"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_collections(self):
        """Test data classes with empty collections"""
        metadata = PDFMetadata(
            authors=[],
            keywords=[],
            categories=[],
            warnings=[]
        )
        
        assert len(metadata.authors) == 0
        assert len(metadata.keywords) == 0
        assert len(metadata.categories) == 0
        assert len(metadata.warnings) == 0
    
    def test_none_values(self):
        """Test handling of None values"""
        author = Author(
            given_name="John",
            family_name="Doe",
            suffix=None,
            affiliation=None,
            orcid=None,
            email=None
        )
        
        # Should not crash with None values
        assert author.suffix is None
        assert author.affiliation is None
    
    def test_unicode_handling(self):
        """Test Unicode character handling"""
        author = Author(
            given_name="François",
            family_name="Müller",
            affiliation="Université de Strasbourg"
        )
        
        metadata = PDFMetadata(
            title="Étude mathématique: αβγ analysis",
            authors=[author],
            abstract="This paper studies αβγ transformations in François Müller's framework"
        )
        
        assert "François" in author.given_name
        assert "Müller" in author.family_name
        assert "αβγ" in metadata.title
        assert "Université" in author.affiliation
    
    def test_large_numbers(self):
        """Test handling of large numbers"""
        metadata = PDFMetadata(
            file_size=5000000000,  # 5GB file
            page_count=10000,      # Very long document
            references_count=50000  # Huge bibliography
        )
        
        assert metadata.file_size == 5000000000
        assert metadata.page_count == 10000
        assert metadata.references_count == 50000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])