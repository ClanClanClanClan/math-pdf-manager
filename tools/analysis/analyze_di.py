#!/usr/bin/env python3
"""Analyze dependency injection implementation in main.py"""

import ast
import re
from pathlib import Path

def analyze_main_function():
    """Analyze the main() function for dependency injection usage."""
    
    main_file = Path('main.py')
    if not main_file.exists():
        print("❌ main.py not found")
        return
    
    content = main_file.read_text()
    
    # Count @inject decorators
    inject_decorators = re.findall(r'@inject\(([^)]+)\)', content)
    print(f"✅ Found {len(inject_decorators)} @inject decorators:")
    for decorator in inject_decorators:
        print(f"   - {decorator}")
    
    # Check main function signature
    main_function_match = re.search(
        r'def main\([^)]*\) -> None:',
        content,
        re.MULTILINE | re.DOTALL
    )
    
    if main_function_match:
        print(f"✅ Found main function signature")
        
        # Extract parameter section
        params_section = re.search(
            r'def main\(([^)]*)\) -> None:',
            content,
            re.MULTILINE | re.DOTALL
        )
        
        if params_section:
            params_text = params_section.group(1)
            # Count service parameters
            service_params = re.findall(r'(\w+_service):', params_text)
            print(f"✅ Found {len(service_params)} service parameters:")
            for param in service_params:
                print(f"   - {param}")
    else:
        print("❌ main function not found")
    
    # Check actual usage of services
    service_usage = {}
    services = ['config_service', 'logging_service', 'file_service', 
                'validation_service', 'metrics_service', 'notification_service',
                'cache_service', 'security_service']
    
    for service in services:
        pattern = f"{service}\\."
        matches = re.findall(pattern, content)
        service_usage[service] = len(matches)
        
    print(f"\n📊 Service Usage Analysis:")
    total_usage = 0
    for service, count in service_usage.items():
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {service}: {count} usages")
        if count > 0:
            total_usage += 1
    
    print(f"\n📈 Summary:")
    print(f"   - Total @inject decorators: {len(inject_decorators)}")
    print(f"   - Services actually used: {total_usage}/{len(services)}")
    
    # Check for hardcoded dependencies (potential issues)
    print(f"\n🔍 Hardcoded Dependencies Check:")
    hardcoded_patterns = [
        (r'logging\.getLogger', 'Direct logging.getLogger usage'),
        (r'yaml\.safe_load', 'Direct yaml.safe_load usage'),
        (r'open\s*\(', 'Direct file open() usage'),
        (r'Path\s*\(', 'Direct Path() instantiation'),
        (r'print\s*\(', 'Direct print() usage')
    ]
    
    for pattern, description in hardcoded_patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"   ⚠️  {description}: {len(matches)} instances")
        else:
            print(f"   ✅ {description}: None found")

if __name__ == "__main__":
    analyze_main_function()