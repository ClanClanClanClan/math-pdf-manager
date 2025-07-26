#!/usr/bin/env python3
"""
Dependency Impact Analysis for Project Reorganization
Analyzes what will break when reorganizing the project structure.
"""

import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set

class DependencyAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.python_files = list(self.project_root.rglob("*.py"))
        self.imports = defaultdict(list)
        self.relative_imports = defaultdict(list)
        self.hardcoded_paths = defaultdict(list)
        
    def analyze_imports(self):
        """Analyze all import statements in Python files"""
        print(f"🔍 Analyzing {len(self.python_files)} Python files for dependencies...")
        
        import_patterns = [
            r'from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import',  # from X import Y
            r'import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)',          # import X
            r'from\s+\.([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import', # from .X import Y
            r'from\s+\.+\s+import',                          # from .. import Y
        ]
        
        path_patterns = [
            r'["\']([^"\']*[/\\][^"\']*)["\']',              # Quoted paths with slashes
            r'Path\(["\']([^"\']*)["\']',                    # Path() constructors
            r'open\(["\']([^"\']*)["\']',                    # File opens
        ]
        
        for py_file in self.python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find imports
                for pattern in import_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        if '.' in match:  # relative import
                            self.relative_imports[str(py_file)].append(match)
                        else:
                            self.imports[str(py_file)].append(match)
                
                # Find hardcoded paths
                for pattern in path_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        if any(suspicious in match.lower() for suspicious in ['test', 'debug', 'archive', 'config', 'data']):
                            self.hardcoded_paths[str(py_file)].append(match)
                            
            except Exception as e:
                print(f"⚠️  Error reading {py_file}: {e}")
    
    def find_broken_imports(self):
        """Identify imports that will break after reorganization"""
        broken_imports = defaultdict(list)
        
        # Common directories that will be moved
        moved_modules = {
            'core', 'api', 'cli', 'publishers', 'parsers', 'validators', 
            'extractors', 'filename_checker', 'gmnap', 'utils', 'tools',
            'scripts', 'config', 'data'
        }
        
        for file_path, imports_list in self.imports.items():
            for imp in imports_list:
                # Check if import refers to a module that will be moved
                imp_parts = imp.split('.')
                if imp_parts[0] in moved_modules:
                    broken_imports[file_path].append(imp)
        
        return broken_imports
    
    def analyze_configuration_files(self):
        """Find configuration files that might have hardcoded paths"""
        config_files = []
        config_patterns = ['*.yaml', '*.yml', '*.json', '*.toml', '*.ini', '*.cfg']
        
        for pattern in config_patterns:
            config_files.extend(self.project_root.rglob(pattern))
        
        path_references = defaultdict(list)
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for path-like strings
                path_patterns = [
                    r'["\']([^"\']*[/\\][^"\']*)["\']',
                    r':\s*([^"\s]+/[^"\s]+)',
                    r'=\s*([^"\s]+/[^"\s]+)',
                ]
                
                for pattern in path_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if any(dir_name in match for dir_name in ['core', 'api', 'tests', 'config', 'data', 'tools']):
                            path_references[str(config_file)].append(match)
                            
            except Exception as e:
                print(f"⚠️  Error reading config {config_file}: {e}")
        
        return path_references
    
    def generate_impact_report(self):
        """Generate comprehensive impact analysis report"""
        
        self.analyze_imports()
        broken_imports = self.find_broken_imports()
        config_paths = self.analyze_configuration_files()
        
        # Count current structure
        root_dirs = [d for d in self.project_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
        root_files = [f for f in self.project_root.iterdir() if f.is_file()]
        
        report = f"""
# DEPENDENCY IMPACT ANALYSIS REPORT

## CURRENT STRUCTURE METRICS
- **Root Directories**: {len(root_dirs)}
- **Root Files**: {len(root_files)}
- **Total Python Files**: {len(self.python_files)}
- **Files with Imports**: {len(self.imports)}
- **Files with Relative Imports**: {len(self.relative_imports)}

## REORGANIZATION IMPACT ASSESSMENT

### 🚨 HIGH RISK: Import Dependencies
**{len(broken_imports)} files** have imports that will break:

"""
        
        # Add broken imports details
        for file_path, imports_list in broken_imports.items():
            rel_path = Path(file_path).relative_to(self.project_root)
            report += f"**{rel_path}**:\n"
            for imp in set(imports_list):  # Remove duplicates
                report += f"  - `{imp}`\n"
            report += "\n"
        
        report += f"""
### ⚠️  MEDIUM RISK: Configuration Files
**{len(config_paths)} configuration files** may need path updates:

"""
        
        for config_file, paths in config_paths.items():
            rel_path = Path(config_file).relative_to(self.project_root)
            report += f"**{rel_path}**:\n"
            for path in set(paths):
                report += f"  - `{path}`\n"
            report += "\n"
        
        # Import frequency analysis
        all_imports = []
        for imports_list in self.imports.values():
            all_imports.extend(imports_list)
        
        import_frequency = Counter(all_imports)
        top_imports = import_frequency.most_common(10)
        
        report += f"""
### 📊 IMPORT FREQUENCY ANALYSIS
Most frequently imported modules that will be affected:

"""
        for module, count in top_imports:
            if any(moved in module for moved in ['core', 'api', 'utils', 'config', 'tools']):
                report += f"- `{module}`: {count} references\n"
        
        report += f"""

## REMEDIATION PLAN

### 1. **Import Path Updates Required**
All Python files importing from moved modules will need import statements updated:

```python
# BEFORE (broken after reorganization)
from core.models import Document
from utils.text import normalize
from config import settings

# AFTER (fixed for new structure)  
from src.core.models import Document
from src.utils.text import normalize
from config.environments import settings
```

### 2. **Configuration File Updates**
Update hardcoded paths in configuration files:
- Docker files: Update COPY and WORKDIR paths
- CI/CD pipelines: Update test and build paths  
- Configuration files: Update data and log file paths

### 3. **Test Path Updates**
All test files will need updated import paths and test data paths.

### 4. **Documentation Updates**
Update any documentation referencing file paths or module imports.

## AUTOMATED FIXES

### Import Statement Replacements
```bash
# Core module imports
find src/ -name "*.py" -exec sed -i 's/from core\\./from src.core./g' {{}} \\;
find src/ -name "*.py" -exec sed -i 's/import core\\./import src.core./g' {{}} \\;

# Utils imports  
find src/ -name "*.py" -exec sed -i 's/from utils\\./from src.utils./g' {{}} \\;
find src/ -name "*.py" -exec sed -i 's/import utils\\./import src.utils./g' {{}} \\;

# API imports
find src/ -name "*.py" -exec sed -i 's/from api\\./from src.api./g' {{}} \\;
find src/ -name "*.py" -exec sed -i 's/import api\\./import src.api./g' {{}} \\;
```

## TESTING STRATEGY

1. **Pre-reorganization**: Run full test suite to establish baseline
2. **Post-reorganization**: Fix imports systematically
3. **Incremental testing**: Test each module as imports are fixed
4. **Full regression**: Run complete test suite after all fixes

## RISK MITIGATION

- **Full backup**: Complete project backup before starting
- **Incremental approach**: Fix one module at a time
- **Automated testing**: Run tests after each fix
- **Rollback plan**: Keep backup accessible for quick rollback

## ESTIMATED EFFORT

- **Import fixes**: {len(broken_imports)} files × 5 minutes = {len(broken_imports) * 5} minutes
- **Config updates**: {len(config_paths)} files × 10 minutes = {len(config_paths) * 10} minutes  
- **Testing**: 2 hours comprehensive testing
- **Total**: ~{(len(broken_imports) * 5 + len(config_paths) * 10) // 60 + 2} hours

## RECOMMENDATION

✅ **PROCEED WITH REORGANIZATION**

The benefits of a clean, professional structure far outweigh the temporary import fix effort. 
Most issues are automatically fixable with find/replace operations.

"""
        
        return report

def main():
    """Main analysis execution"""
    project_root = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/Scripts"
    
    analyzer = DependencyAnalyzer(project_root)
    report = analyzer.generate_impact_report()
    
    # Save report
    report_file = Path(project_root) / "DEPENDENCY_IMPACT_ANALYSIS.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"📄 Impact analysis complete!")
    print(f"📁 Report saved to: {report_file}")
    print("\n" + "="*60)
    print(report[:1000] + "..." if len(report) > 1000 else report)

if __name__ == "__main__":
    main()