#!/usr/bin/env python3
"""
Code Analyzer - Analyzes Python code for dead code, unused imports, and quality issues
"""

import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CodeAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = Path(file_path).name
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            self.tree = ast.parse(self.content)
        except Exception as e:
            print(f"❌ Error parsing {file_path}: {e}")
            self.content = ""
            self.tree = None
    
    def find_dead_functions(self) -> List[Dict]:
        """Find functions that are defined but never called within the file"""
        if not self.tree:
            return []
        
        defined_functions = set()
        called_functions = set()
        
        # Find all function definitions
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                defined_functions.add(node.name)
        
        # Find all function calls
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_functions.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_functions.add(node.func.attr)
        
        # Find potentially dead functions
        potentially_dead = defined_functions - called_functions
        
        # Filter out special methods and common patterns
        dead_functions = []
        for func_name in potentially_dead:
            if not func_name.startswith('_') and func_name not in ['main', 'setup', 'teardown']:
                dead_functions.append({
                    'name': func_name,
                    'type': 'function',
                    'reason': 'Never called within file'
                })
        
        return dead_functions
    
    def find_unused_imports(self) -> List[Dict]:
        """Find imports that are never used"""
        if not self.tree:
            return []
        
        imported_names = set()
        used_names = set()
        import_details = {}
        
        # Find all imports
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imported_names.add(name)
                    import_details[name] = f"import {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imported_names.add(name)
                    import_details[name] = f"from {node.module} import {alias.name}"
        
        # Find all name usages
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # Handle module.function usage
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)
        
        # Find unused imports
        unused_imports = []
        for name in imported_names:
            if name not in used_names:
                unused_imports.append({
                    'name': name,
                    'type': 'import',
                    'statement': import_details[name],
                    'reason': 'Imported but never used'
                })
        
        return unused_imports
    
    def find_duplicate_code(self) -> List[Dict]:
        """Find potential duplicate code blocks"""
        if not self.tree:
            return []
        
        # Look for functions with very similar names
        function_groups = defaultdict(list)
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                # Group by base name (removing version suffixes)
                base_name = re.sub(r'_v\d+$|_old$|_new$|_backup$', '', node.name)
                function_groups[base_name].append(node.name)
        
        duplicates = []
        for base_name, functions in function_groups.items():
            if len(functions) > 1:
                duplicates.append({
                    'type': 'duplicate_functions',
                    'base_name': base_name,
                    'functions': functions,
                    'reason': f'Multiple versions of {base_name}'
                })
        
        return duplicates
    
    def find_code_smells(self) -> List[Dict]:
        """Find code smells and quality issues"""
        if not self.tree:
            return []
        
        smells = []
        
        # Long functions
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno'):
                    func_lines = node.end_lineno - node.lineno + 1
                    if func_lines > 50:
                        smells.append({
                            'type': 'long_function',
                            'name': node.name,
                            'lines': func_lines,
                            'reason': f'Function is {func_lines} lines long (>50)'
                        })
        
        # Too many imports
        import_count = 0
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_count += 1
        
        if import_count > 30:
            smells.append({
                'type': 'too_many_imports',
                'count': import_count,
                'reason': f'File has {import_count} imports (>30)'
            })
        
        # Global variables
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.isupper() and len(target.id) > 3:
                            smells.append({
                                'type': 'global_variable',
                                'name': target.id,
                                'reason': 'Global variable detected'
                            })
        
        return smells
    
    def find_todo_comments(self) -> List[Dict]:
        """Find TODO, FIXME, HACK comments"""
        todos = []
        
        lines = self.content.split('\n')
        for i, line in enumerate(lines, 1):
            # Look for TODO, FIXME, HACK comments
            todo_match = re.search(r'#\s*(TODO|FIXME|HACK|XXX):?\s*(.+)', line, re.IGNORECASE)
            if todo_match:
                comment_type = todo_match.group(1).upper()
                comment_text = todo_match.group(2).strip()
                
                # Check if comment is old (contains dates from previous years)
                is_old = bool(re.search(r'202[0-3]', comment_text))
                
                todos.append({
                    'type': 'todo_comment',
                    'comment_type': comment_type,
                    'line': i,
                    'text': comment_text,
                    'is_old': is_old,
                    'reason': f'{comment_type} comment found'
                })
        
        return todos
    
    def analyze_all(self) -> Dict:
        """Run all analyses and return results"""
        print(f"🔍 Analyzing {self.file_name}...")
        
        results = {
            'file': self.file_name,
            'dead_functions': self.find_dead_functions(),
            'unused_imports': self.find_unused_imports(),
            'duplicate_code': self.find_duplicate_code(),
            'code_smells': self.find_code_smells(),
            'todo_comments': self.find_todo_comments()
        }
        
        # Summary statistics
        total_issues = (
            len(results['dead_functions']) +
            len(results['unused_imports']) +
            len(results['duplicate_code']) +
            len(results['code_smells']) +
            len(results['todo_comments'])
        )
        
        results['summary'] = {
            'total_issues': total_issues,
            'dead_functions_count': len(results['dead_functions']),
            'unused_imports_count': len(results['unused_imports']),
            'duplicate_code_count': len(results['duplicate_code']),
            'code_smells_count': len(results['code_smells']),
            'todo_comments_count': len(results['todo_comments'])
        }
        
        return results


def print_analysis_results(results: Dict):
    """Print analysis results in a formatted way"""
    print(f"\n📊 Analysis Results for {results['file']}")
    print("=" * 50)
    
    summary = results['summary']
    if summary['total_issues'] == 0:
        print("✅ No issues found!")
        return
    
    print(f"📈 Total Issues: {summary['total_issues']}")
    print()
    
    # Dead functions
    if results['dead_functions']:
        print(f"🔴 Dead Functions ({len(results['dead_functions'])}):")
        for func in results['dead_functions']:
            print(f"  • {func['name']} - {func['reason']}")
        print()
    
    # Unused imports
    if results['unused_imports']:
        print(f"🟡 Unused Imports ({len(results['unused_imports'])}):")
        for imp in results['unused_imports']:
            print(f"  • {imp['statement']} - {imp['reason']}")
        print()
    
    # Duplicate code
    if results['duplicate_code']:
        print(f"🟠 Duplicate Code ({len(results['duplicate_code'])}):")
        for dup in results['duplicate_code']:
            print(f"  • {dup['base_name']}: {', '.join(dup['functions'])}")
        print()
    
    # Code smells
    if results['code_smells']:
        print(f"🔵 Code Smells ({len(results['code_smells'])}):")
        for smell in results['code_smells']:
            if smell['type'] == 'long_function':
                print(f"  • {smell['name']}() - {smell['lines']} lines")
            elif smell['type'] == 'too_many_imports':
                print(f"  • Too many imports - {smell['count']} imports")
            elif smell['type'] == 'global_variable':
                print(f"  • Global variable - {smell['name']}")
        print()
    
    # TODO comments
    if results['todo_comments']:
        print(f"📝 TODO Comments ({len(results['todo_comments'])}):")
        old_todos = [t for t in results['todo_comments'] if t['is_old']]
        if old_todos:
            print(f"  ❌ Old TODOs ({len(old_todos)}):")
            for todo in old_todos:
                print(f"    Line {todo['line']}: {todo['comment_type']} - {todo['text']}")
        
        new_todos = [t for t in results['todo_comments'] if not t['is_old']]
        if new_todos:
            print(f"  📋 Current TODOs ({len(new_todos)}):")
            for todo in new_todos:
                print(f"    Line {todo['line']}: {todo['comment_type']} - {todo['text']}")
        print()


def main():
    """Main function to analyze files"""
    if len(sys.argv) < 2:
        print("Usage: python code_analyzer.py <file1.py> [file2.py] ...")
        sys.exit(1)
    
    all_results = []
    
    for file_path in sys.argv[1:]:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            continue
        
        analyzer = CodeAnalyzer(file_path)
        results = analyzer.analyze_all()
        all_results.append(results)
        print_analysis_results(results)
    
    # Summary across all files
    if len(all_results) > 1:
        print("\n🌟 OVERALL SUMMARY")
        print("=" * 50)
        
        total_issues = sum(r['summary']['total_issues'] for r in all_results)
        total_dead_functions = sum(r['summary']['dead_functions_count'] for r in all_results)
        total_unused_imports = sum(r['summary']['unused_imports_count'] for r in all_results)
        total_duplicates = sum(r['summary']['duplicate_code_count'] for r in all_results)
        total_smells = sum(r['summary']['code_smells_count'] for r in all_results)
        total_todos = sum(r['summary']['todo_comments_count'] for r in all_results)
        
        print(f"📊 Files analyzed: {len(all_results)}")
        print(f"📈 Total issues: {total_issues}")
        print(f"🔴 Dead functions: {total_dead_functions}")
        print(f"🟡 Unused imports: {total_unused_imports}")
        print(f"🟠 Duplicate code: {total_duplicates}")
        print(f"🔵 Code smells: {total_smells}")
        print(f"📝 TODO comments: {total_todos}")


if __name__ == "__main__":
    main()