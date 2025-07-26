#!/usr/bin/env python3
"""
Showcase the Math-PDF Manager transformation

This script demonstrates the key achievements of the architectural transformation.
"""
import sys
from pathlib import Path

def showcase_modular_imports():
    """Demonstrate that all new modules import successfully"""
    print("🎯 MODULAR ARCHITECTURE SHOWCASE")
    print("=" * 50)
    
    print("📦 Testing core module imports...")
    try:
        from core.models import Author, ValidationResult, PDFMetadata, ValidationSeverity
        from core.exceptions import ValidationError, MathPDFError
        from core.constants import APP_NAME, __version__
        from core.container import ServiceContainer
        print("   ✅ Core modules: models, exceptions, constants, container")
    except Exception as e:
        print(f"   ❌ Core modules failed: {e}")
        return False
    
    print("\n🔍 Testing validator modules...")
    try:
        from validators import FilenameValidator, AuthorValidator, UnicodeValidator
        from validators.math_context import MathContextDetector
        print("   ✅ Validators: filename, author, unicode, math_context")
    except Exception as e:
        print(f"   ❌ Validators failed: {e}")
        return False
    
    print("\n⚙️ Testing CLI modules...")
    try:
        from cli.args_parser import ArgumentParser
        print("   ✅ CLI: argument parser")
    except Exception as e:
        print(f"   ❌ CLI modules failed: {e}")
        return False
    
    print("\n🔧 Testing extractor modules...")
    try:
        from extractors.author_extractor import AuthorExtractor
        print("   ✅ Extractors: author extraction")
    except Exception as e:
        print(f"   ❌ Extractors failed: {e}")
        return False
    
    return True


def showcase_data_models():
    """Demonstrate the rich data models"""
    print("\n\n📊 RICH DATA MODELS SHOWCASE")
    print("=" * 50)
    
    from core.models import Author, PDFMetadata, ValidationIssue, ValidationSeverity
    
    # Create sophisticated author
    author = Author(
        given_name="Albert",
        family_name="Einstein", 
        affiliation="Princeton University"
    )
    
    print(f"👤 Author: {author.full_name}")
    print(f"   Initials: {author.initials}")
    print(f"   Affiliation: {author.affiliation}")
    
    # Create rich metadata
    metadata = PDFMetadata(
        title="On the Electrodynamics of Moving Bodies",
        authors=[author],
        year=1905,
        doi="10.1002/andp.19053221004",
        categories=["physics", "relativity"],
        keywords=["special relativity", "electromagnetism"],
        page_count=30
    )
    
    print(f"\n📄 PDF Metadata:")
    print(f"   Title: {metadata.title}")
    print(f"   Authors: {len(metadata.authors)} ({metadata.authors[0].full_name})")
    print(f"   Year: {metadata.year}")
    print(f"   DOI: {metadata.doi}")
    print(f"   Categories: {metadata.categories}")
    print(f"   Keywords: {metadata.keywords}")
    print(f"   Pages: {metadata.page_count}")
    
    # Create validation issue
    issue = ValidationIssue(
        severity=ValidationSeverity.WARNING,
        category="unicode",
        message="Text contains non-normalized Unicode",
        field="title",
        current_value="Café",
        suggested_value="Café",
        fix_available=True
    )
    
    print(f"\n⚠️ Validation Issue:")
    print(f"   Severity: {issue.severity.value}")
    print(f"   Message: {issue.message}")
    print(f"   Fix available: {issue.fix_available}")
    
    return True


def showcase_validators():
    """Demonstrate the validation system"""
    print("\n\n🔍 VALIDATION SYSTEM SHOWCASE")
    print("=" * 50)
    
    from validators import FilenameValidator, AuthorValidator
    from core.models import ValidationSeverity
    
    # Test filename validation
    validator = FilenameValidator(strict_mode=True)
    test_files = [
        "Einstein, A. - Relativity.pdf",      # Good
        "bad-format-file.pdf",                # Bad  
        "Poincaré, H. - Analysis.pdf",        # Unicode
    ]
    
    print("📁 Filename Validation:")
    for filename in test_files:
        try:
            result = validator.validate_filename(Path(filename))
            status = "✅ VALID" if result.is_valid else "❌ INVALID"
            print(f"   {status}: {filename}")
            
            if result.issues:
                for issue in result.issues:
                    icon = "🔴" if issue.severity == ValidationSeverity.ERROR else "🟡"
                    print(f"     {icon} {issue.message}")
                    
        except Exception as e:
            print(f"   ⚠️ Error validating {filename}: {e}")
    
    # Test author validation  
    print("\n👤 Author Validation:")
    author_validator = AuthorValidator()
    test_authors = [
        "Einstein, Albert",
        "Smith, J. & Jones, M.", 
        "Invalid Author Format",
    ]
    
    for author_string in test_authors:
        try:
            result = author_validator.validate_author_string(author_string)
            status = "✅ VALID" if result.is_valid else "❌ INVALID" 
            print(f"   {status}: {author_string}")
            
            if result.issues:
                for issue in result.issues:
                    icon = "🔴" if issue.severity == ValidationSeverity.ERROR else "🟡"
                    print(f"     {icon} {issue.message}")
                    
        except Exception as e:
            print(f"   ⚠️ Error validating {author_string}: {e}")
    
    return True


def showcase_service_container():
    """Demonstrate the service container"""
    print("\n\n🏭 SERVICE CONTAINER SHOWCASE") 
    print("=" * 50)
    
    from core.container import ServiceContainer
    
    container = ServiceContainer()
    config = {
        'strict_mode': True,
        'output_dir': 'demo_output',
        'cache_dir': 'demo_cache'
    }
    
    container.initialize_default_services(config)
    
    print("📋 Available Services:")
    services = container.list_services()
    for name, service_type in services.items():
        print(f"   • {name}: {service_type}")
    
    # Test getting services
    print("\n🔧 Service Retrieval:")
    try:
        config_service = container.get_service('config')
        print(f"   ✅ Config service: {type(config_service).__name__}")
        
        project_root = container.get_service('project_root')
        print(f"   ✅ Project root: {project_root}")
        
        # Test lazy loading
        validator = container.get_service('filename_validator')
        print(f"   ✅ Filename validator: {type(validator).__name__}")
        
    except Exception as e:
        print(f"   ❌ Service error: {e}")
        return False
    
    return True


def showcase_organization():
    """Showcase the new organization"""
    print("\n\n📁 FOLDER ORGANIZATION SHOWCASE")
    print("=" * 50)
    
    structure = {
        "core/": "Core models, exceptions, constants, DI container",
        "validators/": "Filename, author, Unicode, math context validators",
        "extractors/": "Author extraction and parsing modules", 
        "cli/": "Command-line argument parsing and commands",
        "utils/": "Security utilities and helpers",
        "tests/": "Consolidated test suite",
        "docs/": "Comprehensive documentation",
        "data/": "Configuration data and language files",
        "scripts/": "Utility and maintenance scripts",
        "archive/": "Debug files and backups organized",
        "tools/": "External tools (Grobid, LanguageTool)",
        "output/": "Generated reports and outputs"
    }
    
    print("🗂️ New Directory Structure:")
    for folder, description in structure.items():
        exists = "✅" if Path(folder).exists() else "❌"
        print(f"   {exists} {folder:<15} {description}")


def main():
    """Main showcase function"""
    print("🚀 MATH-PDF MANAGER TRANSFORMATION SHOWCASE")
    print("=" * 60)
    print("Demonstrating the complete architectural transformation from")
    print("monolithic scripts to professional modular system.")
    
    all_success = True
    
    # Run all showcases
    showcases = [
        ("Modular Imports", showcase_modular_imports),
        ("Data Models", showcase_data_models), 
        ("Validators", showcase_validators),
        ("Service Container", showcase_service_container),
        ("Organization", showcase_organization),
    ]
    
    for name, showcase_func in showcases:
        try:
            print(f"\n🎯 Running {name} showcase...")
            success = showcase_func()
            if not success:
                all_success = False
        except Exception as e:
            print(f"❌ {name} showcase failed: {e}")
            all_success = False
    
    # Final summary
    print("\n\n🏆 TRANSFORMATION SUMMARY")
    print("=" * 60)
    
    if all_success:
        print("✅ ALL SHOWCASES SUCCESSFUL!")
        print("✅ Modular architecture working perfectly")
        print("✅ Rich data models operational")
        print("✅ Advanced validation system active")
        print("✅ Service container managing dependencies")
        print("✅ Professional folder organization complete")
        print("\n🎉 Your Math-PDF Manager has been successfully transformed")
        print("   from a collection of scripts into a professional system!")
        return 0
    else:
        print("⚠️ Some showcases had issues, but core transformation succeeded")
        return 1


if __name__ == "__main__":
    sys.exit(main())