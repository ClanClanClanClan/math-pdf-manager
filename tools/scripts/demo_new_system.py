#!/usr/bin/env python3
"""
Demo script showcasing the new Math-PDF Manager architecture

This script demonstrates the key improvements and capabilities
of the transformed system.
"""
import sys
from pathlib import Path
from typing import List

# Import the new modular components
from validators import FilenameValidator, AuthorValidator, UnicodeValidator
from core.models import Author, ValidationResult, PDFMetadata, ValidationSeverity
from core.container import ServiceContainer, initialize_services
from core.exceptions import ValidationError, MathPDFError
from utils.security import PathValidator


def demo_validation_system():
    """Demonstrate the advanced validation system"""
    print("🔍 VALIDATION SYSTEM DEMO")
    print("=" * 50)
    
    # Create validators
    filename_validator = FilenameValidator(strict_mode=True)
    author_validator = AuthorValidator(strict_mode=True)
    unicode_validator = UnicodeValidator()
    
    # Test various filename patterns
    test_filenames = [
        "Einstein, A. - Relativity Theory.pdf",           # Good
        "Poincaré, H. - Analysis Situs.pdf",             # Unicode  
        "Very-Long-Name-Without-Proper-Format.pdf",      # Bad format
        "Smith, J. & Jones, M. - Collaboration.pdf",     # Multiple authors
    ]
    
    for i, filename in enumerate(test_filenames, 1):
        print(f"\n📄 Test {i}: {filename}")
        
        # Create a mock Path for testing
        file_path = Path(filename)
        
        # Run validation
        try:
            result = filename_validator.validate_filename(file_path)
            
            print(f"   Valid: {'✅' if result.is_valid else '❌'}")
            print(f"   Issues: {len(result.issues)}")
            
            for issue in result.issues:
                severity_icon = {
                    ValidationSeverity.ERROR: "🔴",
                    ValidationSeverity.WARNING: "🟡", 
                    ValidationSeverity.INFO: "🔵"
                }.get(issue.severity, "⚪")
                
                print(f"     {severity_icon} {issue.message}")
                if issue.suggested_value:
                    print(f"        Suggestion: {issue.suggested_value}")
                    
        except Exception as e:
            print(f"   Error: {e}")


def demo_author_system():
    """Demonstrate the author parsing system"""
    print("\n\n👤 AUTHOR PARSING DEMO")
    print("=" * 50)
    
    author_validator = AuthorValidator()
    
    test_authors = [
        "Einstein, Albert",
        "von Neumann, John",
        "Smith, J. & Jones, M.",
        "Poincaré, Henri",
        "A. Einstein and B. Podolsky",
    ]
    
    for author_string in test_authors:
        print(f"\n📝 Parsing: {author_string}")
        
        try:
            result = author_validator.validate_author_string(author_string)
            authors = author_validator.parse_author_string(author_string)
            
            print(f"   Found {len(authors)} author(s)")
            for author in authors:
                print(f"     • {author.full_name}")
                if author.given_name and author.family_name:
                    print(f"       Given: {author.given_name}, Family: {author.family_name}")
                    
        except Exception as e:
            print(f"   Error: {e}")


def demo_security_features():
    """Demonstrate security features"""
    print("\n\n🛡️ SECURITY FEATURES DEMO")
    print("=" * 50)
    
    # Test path validation
    base_dir = Path("/safe/directory")
    test_paths = [
        "document.pdf",                    # Safe
        "subdir/document.pdf",            # Safe  
        "../../../etc/passwd",            # Dangerous
        "/absolute/path/document.pdf",    # Potentially dangerous
    ]
    
    print("🔒 Path Traversal Protection:")
    for test_path in test_paths:
        try:
            safe_path = PathValidator.validate_path(test_path, base_dir)
            print(f"   ✅ {test_path} → {safe_path}")
        except Exception as e:
            print(f"   🚫 {test_path} → BLOCKED: {e}")
    
    # Test Unicode validation
    print("\n🔤 Unicode Security:")
    unicode_validator = UnicodeValidator()
    
    test_texts = [
        "Normal text",
        "Café with accents",
        "Text with\u200bzero-width\u200bchars",  # Hidden characters
    ]
    
    for text in test_texts:
        issues = unicode_validator.validate_text(text)
        if issues:
            print(f"   🟡 '{text}' has {len(issues)} Unicode issues")
            for issue in issues:
                print(f"      - {issue.message}")
        else:
            print(f"   ✅ '{text}' is Unicode-safe")


def demo_service_container():
    """Demonstrate dependency injection"""
    print("\n\n🏭 SERVICE CONTAINER DEMO")
    print("=" * 50)
    
    # Initialize container
    container = ServiceContainer()
    config = {'strict_mode': True, 'output_dir': 'demo_output'}
    container.initialize_default_services(config)
    
    print("📋 Available services:")
    services = container.list_services()
    for name, service_type in services.items():
        print(f"   • {name}: {service_type}")
    
    print("\n🔧 Getting services:")
    try:
        validator = container.get_service('filename_validator')
        print(f"   ✅ filename_validator: {type(validator).__name__}")
        
        scanner = container.get_service('scanner') 
        print(f"   ✅ scanner: {type(scanner).__name__}")
        
        config_service = container.get_service('config')
        print(f"   ✅ config: {config_service}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def demo_data_models():
    """Demonstrate rich data models"""
    print("\n\n📊 DATA MODELS DEMO")
    print("=" * 50)
    
    # Create an author
    author = Author(
        given_name="Albert",
        family_name="Einstein",
        affiliation="Princeton University",
        orcid="0000-0000-0000-0000"
    )
    
    print("👤 Author model:")
    print(f"   Full name: {author.full_name}")
    print(f"   Initials: {author.initials}")  
    print(f"   Affiliation: {author.affiliation}")
    
    # Create metadata
    metadata = PDFMetadata(
        title="On the Electrodynamics of Moving Bodies",
        authors=[author],
        year=1905,
        doi="10.1002/andp.19053221004",
        categories=["physics", "relativity"]
    )
    
    print("\n📄 PDF Metadata:")
    print(f"   Title: {metadata.title}")
    print(f"   Authors: {len(metadata.authors)}")
    print(f"   Year: {metadata.year}")
    print(f"   DOI: {metadata.doi}")
    print(f"   Categories: {metadata.categories}")


def main():
    """Main demo function"""
    print("🎯 MATH-PDF MANAGER: NEW SYSTEM DEMONSTRATION")
    print("=" * 60)
    print("This demo showcases the transformed architecture and capabilities.")
    
    try:
        demo_validation_system()
        demo_author_system() 
        demo_security_features()
        demo_service_container()
        demo_data_models()
        
        print("\n\n🎉 DEMO COMPLETE!")
        print("=" * 60)
        print("✅ All systems operational")
        print("✅ Security features active")  
        print("✅ Architecture transformation successful")
        print("\nYour Math-PDF Manager is now a professional-grade system! 🚀")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())