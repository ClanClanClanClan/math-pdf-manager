#!/usr/bin/env python3
"""
Comprehensive analysis of the Dependency Injection framework.
This analyzes the code structure and identifies issues without running it.
"""

import sys
import os
from pathlib import Path
import importlib.util

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_file_structure():
    """Analyze the DI framework file structure."""
    print("DI FRAMEWORK STRUCTURE ANALYSIS")
    print("=" * 60)
    
    base_path = Path(__file__).parent
    di_path = base_path / "core" / "dependency_injection"
    
    expected_files = [
        "__init__.py",
        "container.py", 
        "interfaces.py",
        "implementations.py"
    ]
    
    print("Checking file structure...")
    for file in expected_files:
        file_path = di_path / file
        if file_path.exists():
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
    
    print()

def analyze_imports():
    """Analyze import statements and dependencies."""
    print("IMPORT ANALYSIS")
    print("=" * 60)
    
    # Check __init__.py imports
    init_file = Path(__file__).parent / "core" / "dependency_injection" / "__init__.py"
    if init_file.exists():
        with open(init_file, 'r') as f:
            content = f.read()
            
        print("__init__.py imports:")
        imports = [line.strip() for line in content.split('\n') if line.strip().startswith('from')]
        for imp in imports:
            print(f"  {imp}")
    
    # Check container.py imports
    container_file = Path(__file__).parent / "core" / "dependency_injection" / "container.py"
    if container_file.exists():
        with open(container_file, 'r') as f:
            content = f.read()
            
        print("\ncontainer.py imports:")
        imports = [line.strip() for line in content.split('\n') if line.strip().startswith('from') or line.strip().startswith('import')]
        for imp in imports:
            print(f"  {imp}")
    
    print()

def analyze_secureconfig_issue():
    """Analyze the SecureConfig import issue."""
    print("SECURECONFIG ISSUE ANALYSIS")
    print("=" * 60)
    
    # Check what's in the container.py
    container_file = Path(__file__).parent / "core" / "dependency_injection" / "container.py"
    if container_file.exists():
        with open(container_file, 'r') as f:
            content = f.read()
        
        # Look for SecureConfig import
        if "from core.config.secure_config import SecureConfig" in content:
            print("✗ Found problematic import: from core.config.secure_config import SecureConfig")
        
        # Check what's actually in secure_config.py
        secure_config_file = Path(__file__).parent / "core" / "config" / "secure_config.py"
        if secure_config_file.exists():
            with open(secure_config_file, 'r') as f:
                secure_content = f.read()
            
            if "class SecureConfig" in secure_content:
                print("✓ SecureConfig class found in secure_config.py")
            elif "class SecureConfigManager" in secure_content:
                print("✗ Only SecureConfigManager found, not SecureConfig")
                print("  This is the root cause of the import issue!")
            else:
                print("✗ No SecureConfig or SecureConfigManager found")
    
    print()

def analyze_service_registrations():
    """Analyze how services are registered."""
    print("SERVICE REGISTRATION ANALYSIS")
    print("=" * 60)
    
    implementations_file = Path(__file__).parent / "core" / "dependency_injection" / "implementations.py"
    if implementations_file.exists():
        with open(implementations_file, 'r') as f:
            content = f.read()
        
        # Look for @service decorators
        service_decorators = [line.strip() for line in content.split('\n') if '@service' in line]
        print("Found service registrations:")
        for decorator in service_decorators:
            print(f"  {decorator}")
    
    print()

def analyze_dependency_chains():
    """Analyze dependency chains between services."""
    print("DEPENDENCY CHAIN ANALYSIS")
    print("=" * 60)
    
    implementations_file = Path(__file__).parent / "core" / "dependency_injection" / "implementations.py"
    if implementations_file.exists():
        with open(implementations_file, 'r') as f:
            content = f.read()
        
        # Look for constructor dependencies
        lines = content.split('\n')
        current_class = None
        
        for line in lines:
            if line.strip().startswith('class '):
                current_class = line.strip().split('class ')[1].split('(')[0]
            elif line.strip().startswith('def __init__(self') and current_class:
                # Extract constructor parameters
                if ':' in line:
                    params = line.split('def __init__(self')[1].split('):')[0]
                    if params.strip() and params.strip() != '':
                        print(f"{current_class} depends on: {params.strip()}")
                    else:
                        print(f"{current_class} has no dependencies")
    
    print()

def analyze_interfaces():
    """Analyze the service interfaces."""
    print("INTERFACE ANALYSIS")
    print("=" * 60)
    
    interfaces_file = Path(__file__).parent / "core" / "dependency_injection" / "interfaces.py"
    if interfaces_file.exists():
        with open(interfaces_file, 'r') as f:
            content = f.read()
        
        # Look for interface classes
        interface_classes = [line.strip() for line in content.split('\n') if line.strip().startswith('class I')]
        print("Found interfaces:")
        for interface in interface_classes:
            interface_name = interface.split('class ')[1].split('(')[0]
            print(f"  {interface_name}")
    
    print()

def analyze_container_functionality():
    """Analyze the DI container functionality."""
    print("CONTAINER FUNCTIONALITY ANALYSIS")
    print("=" * 60)
    
    container_file = Path(__file__).parent / "core" / "dependency_injection" / "container.py"
    if container_file.exists():
        with open(container_file, 'r') as f:
            content = f.read()
        
        # Look for key methods
        key_methods = [
            'register_singleton',
            'register_transient', 
            'register_factory',
            'resolve',
            '_create_instance'
        ]
        
        print("Container methods:")
        for method in key_methods:
            if f"def {method}(" in content:
                print(f"✓ {method} implemented")
            else:
                print(f"✗ {method} missing")
    
    print()

def identify_issues():
    """Identify specific issues with the DI framework."""
    print("IDENTIFIED ISSUES")
    print("=" * 60)
    
    issues = []
    
    # Issue 1: SecureConfig import
    container_file = Path(__file__).parent / "core" / "dependency_injection" / "container.py"
    if container_file.exists():
        with open(container_file, 'r') as f:
            content = f.read()
        
        if "from core.config.secure_config import SecureConfig" in content:
            secure_config_file = Path(__file__).parent / "core" / "config" / "secure_config.py"
            if secure_config_file.exists():
                with open(secure_config_file, 'r') as f:
                    secure_content = f.read()
                
                if "class SecureConfig" not in secure_content:
                    issues.append("Import mismatch: container.py imports SecureConfig but only SecureConfigManager exists")
    
    # Issue 2: Check if all imports are available
    try:
        import yaml
        print("✓ PyYAML available")
    except ImportError:
        issues.append("PyYAML not installed (required for config files)")
    
    # Issue 3: Check if config files exist
    config_file = Path(__file__).parent / "config.yaml"
    if not config_file.exists():
        issues.append("config.yaml file missing")
    
    config_defs = Path(__file__).parent / "core" / "config" / "config_definitions.yaml"
    if not config_defs.exists():
        issues.append("config_definitions.yaml file missing")
    
    if issues:
        print("Found issues:")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    else:
        print("No major issues found in static analysis")
    
    print()

def provide_recommendations():
    """Provide recommendations for fixing the DI framework."""
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    recommendations = [
        "Fix SecureConfig import issue by either:",
        "  - Renaming SecureConfigManager to SecureConfig, or",
        "  - Updating container.py to import SecureConfigManager and alias it",
        "",
        "Ensure all required dependencies are installed:",
        "  - PyYAML for configuration files",
        "  - Any other dependencies used by services",
        "",
        "Create missing configuration files:",
        "  - config.yaml in the root directory",
        "  - config_definitions.yaml in core/config/",
        "",
        "Add proper error handling for missing dependencies",
        "",
        "Consider adding unit tests for the DI framework",
        "",
        "Document the DI framework usage and patterns"
    ]
    
    for rec in recommendations:
        print(rec)
    
    print()

def main():
    """Run the complete analysis."""
    print("DEPENDENCY INJECTION FRAMEWORK ANALYSIS")
    print("=" * 60)
    print("This analysis examines the DI framework code structure and identifies issues.")
    print()
    
    analyze_file_structure()
    analyze_imports()
    analyze_secureconfig_issue()
    analyze_service_registrations()
    analyze_dependency_chains()
    analyze_interfaces()
    analyze_container_functionality()
    identify_issues()
    provide_recommendations()
    
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print("The DI framework appears to be mostly implemented but has import issues.")
    print("The main blocker is the SecureConfig import mismatch.")

if __name__ == "__main__":
    main()