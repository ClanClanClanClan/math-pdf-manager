#!/usr/bin/env python3
"""
Automated Improvement Tooling Strategy
Strategy for building tools that can automatically detect, prevent, and fix architectural anti-patterns.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class ArchitecturalViolation:
    """Represents a violation of architectural rules."""
    rule_id: str
    file_path: str
    line_number: int
    description: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    auto_fixable: bool = False
    suggested_fix: Optional[str] = None

@dataclass
class ModuleMetrics:
    """Metrics for a Python module."""
    path: str
    line_count: int
    function_count: int
    class_count: int
    import_count: int
    complexity_score: float
    responsibilities: List[str]
    dependencies: Set[str]
    dependents: Set[str]

class ArchitecturalLinter:
    """
    Automated architectural linting and enforcement.
    
    Detects violations of architectural rules and suggests fixes.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.violations: List[ArchitecturalViolation] = []
        self.module_metrics: Dict[str, ModuleMetrics] = {}
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load architectural linting configuration."""
        default_config = {
            'max_lines_per_file': 500,
            'max_functions_per_file': 20,
            'max_classes_per_file': 5,
            'max_imports_per_file': 20,
            'forbidden_patterns': [
                r'os\.environ\.get\([^,]+,\s*["\'][^"\']*["\']',  # Hardcoded env defaults
                r'print\s*\(',  # Print statements in production
                r'except\s*Exception\s*:',  # Bare exception handling
                r'import\s+\*',  # Star imports
            ],
            'required_patterns': [
                r'from\s+core\.config\.secure_config\s+import',  # Use secure config
                r'logger\s*=\s*logging\.getLogger',  # Proper logging
            ],
            'dependency_rules': {
                'core/': ['typing', 'dataclasses', 'abc'],  # Core can only depend on stdlib
                'utils/': ['core/'],  # Utils can depend on core
                'services/': ['core/', 'utils/'],  # Services can depend on core and utils
            }
        }
        
        if config_path and Path(config_path).exists():
            # Load custom config (implementation would parse YAML/JSON)
            pass
        
        return default_config
    
    def analyze_codebase(self, root_path: str) -> Dict[str, Any]:
        """Analyze entire codebase for architectural violations."""
        results = {
            'violations': [],
            'metrics': {},
            'suggestions': [],
            'architectural_health_score': 0.0
        }
        
        # Find all Python files
        python_files = list(Path(root_path).rglob('*.py'))
        
        for file_path in python_files:
            if self._should_analyze_file(file_path):
                try:
                    metrics = self._analyze_file(file_path)
                    self.module_metrics[str(file_path)] = metrics
                    
                    # Check for violations
                    violations = self._check_violations(file_path, metrics)
                    self.violations.extend(violations)
                    
                except Exception as e:
                    logger.error(f"Error analyzing {file_path}: {e}")
        
        # Analyze cross-module dependencies
        dependency_violations = self._check_dependency_violations()
        self.violations.extend(dependency_violations)
        
        # Calculate architectural health score
        health_score = self._calculate_health_score()
        
        # Calculate violation summary
        violation_summary = {}
        for violation in self.violations:
            violation_summary[violation.rule_id] = violation_summary.get(violation.rule_id, 0) + 1
        
        results.update({
            'violations': self.violations,
            'metrics': self.module_metrics,
            'suggestions': self._generate_suggestions(),
            'architectural_health_score': health_score,
            'total_violations': len(self.violations),
            'violation_summary': violation_summary
        })
        
        return results
    
    def _should_analyze_file(self, file_path: Path) -> bool:
        """Determine if a file should be analyzed."""
        # Skip test files, generated files, archives, etc.
        skip_patterns = [
            '/_archive/',
            '/tools/',
            '/test_',
            '/.venv/',
            '__pycache__',
            '.backup',
            '.temp',
            '/site-packages/',
            '/lib/python',
            '_generated.py',
            'mupdf.py',
            '/scipy/',
            '/torch/',
            '/lib/',
            '/bin/',
            '/include/',
            '/share/',
            '/modules/unicode_utils 2/',  # This seems to be a duplicate/backup
        ]
        
        file_str = str(file_path)
        if any(pattern in file_str for pattern in skip_patterns):
            return False
        
        # Only analyze files in the main project directory
        # Focus on the core academic papers system
        main_project_patterns = [
            'main.py',
            'pdf_parser.py',
            'filename_checker.py',
            'utils.py',
            'my_spellchecker.py',
            'auth_manager.py',
            'scanner.py',
            'reporter.py',
            'metadata_fetcher.py',
            'duplicate_detector.py',
            'core/',
            'validators/',
            'scripts/',
            'tests/',
        ]
        
        # If it's a direct file in the root, analyze it
        if file_path.parent.name == Path('.').resolve().name:
            return True
        
        # Otherwise, check if it's in allowed directories
        return any(pattern in file_str for pattern in main_project_patterns)
    
    def _analyze_file(self, file_path: Path) -> ModuleMetrics:
        """Analyze a single Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Return minimal metrics for files with syntax errors
            return ModuleMetrics(
                path=str(file_path),
                line_count=len(content.splitlines()),
                function_count=0,
                class_count=0,
                import_count=0,
                complexity_score=0.0,
                responsibilities=[],
                dependencies=set(),
                dependents=set()
            )
        
        # Count elements
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        imports = [node for node in ast.walk(tree) 
                  if isinstance(node, (ast.Import, ast.ImportFrom))]
        
        # Identify responsibilities (heuristic)
        responsibilities = self._identify_responsibilities(content, functions, classes)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(imports)
        
        # Calculate complexity score
        complexity = self._calculate_complexity(tree)
        
        return ModuleMetrics(
            path=str(file_path),
            line_count=len(content.splitlines()),
            function_count=len(functions),
            class_count=len(classes),
            import_count=len(imports),
            complexity_score=complexity,
            responsibilities=responsibilities,
            dependencies=dependencies,
            dependents=set()  # Will be populated later
        )
    
    def _identify_responsibilities(self, content: str, functions: List[ast.FunctionDef], 
                                classes: List[ast.ClassDef]) -> List[str]:
        """Identify the responsibilities of a module."""
        responsibilities = []
        
        # Heuristics for identifying responsibilities
        patterns = {
            'configuration': [r'config', r'settings', r'Config', r'Settings'],
            'authentication': [r'auth', r'login', r'credential', r'Auth', r'Login'],
            'file_processing': [r'file', r'path', r'read', r'write', r'File', r'Path'],
            'networking': [r'http', r'request', r'api', r'Http', r'Request', r'API'],
            'data_parsing': [r'parse', r'extract', r'Parse', r'Extract'],
            'validation': [r'valid', r'check', r'Valid', r'Check'],
            'logging': [r'log', r'debug', r'Log', r'Debug'],
            'error_handling': [r'error', r'exception', r'Error', r'Exception'],
            'testing': [r'test', r'mock', r'Test', r'Mock'],
            'ui': [r'ui', r'interface', r'UI', r'Interface'],
        }
        
        for responsibility, keywords in patterns.items():
            if any(re.search(pattern, content) for pattern in keywords):
                responsibilities.append(responsibility)
        
        return responsibilities
    
    def _extract_dependencies(self, imports: List[ast.stmt]) -> Set[str]:
        """Extract module dependencies from import statements."""
        dependencies = set()
        
        for import_node in imports:
            if isinstance(import_node, ast.Import):
                for alias in import_node.names:
                    dependencies.add(alias.name.split('.')[0])
            elif isinstance(import_node, ast.ImportFrom):
                if import_node.module:
                    dependencies.add(import_node.module.split('.')[0])
        
        return dependencies
    
    def _calculate_complexity(self, tree: ast.AST) -> float:
        """Calculate complexity score for a module."""
        # Simplified complexity calculation
        complexity = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(node, ast.FunctionDef):
                complexity += 0.5
            elif isinstance(node, ast.ClassDef):
                complexity += 0.3
        
        return complexity
    
    def _check_violations(self, file_path: Path, metrics: ModuleMetrics) -> List[ArchitecturalViolation]:
        """Check for architectural violations in a file."""
        violations = []
        
        # Check file size
        if metrics.line_count > self.config['max_lines_per_file']:
            violations.append(ArchitecturalViolation(
                rule_id='FILE_TOO_LARGE',
                file_path=str(file_path),
                line_number=metrics.line_count,
                description=f'File has {metrics.line_count} lines (max: {self.config["max_lines_per_file"]})',
                severity='high',
                auto_fixable=False,
                suggested_fix='Consider splitting into smaller modules'
            ))
        
        # Check function count
        if metrics.function_count > self.config['max_functions_per_file']:
            violations.append(ArchitecturalViolation(
                rule_id='TOO_MANY_FUNCTIONS',
                file_path=str(file_path),
                line_number=1,
                description=f'File has {metrics.function_count} functions (max: {self.config["max_functions_per_file"]})',
                severity='medium',
                auto_fixable=False,
                suggested_fix='Consider grouping related functions into classes'
            ))
        
        # Check multiple responsibilities
        if len(metrics.responsibilities) > 3:
            violations.append(ArchitecturalViolation(
                rule_id='MULTIPLE_RESPONSIBILITIES',
                file_path=str(file_path),
                line_number=1,
                description=f'File has {len(metrics.responsibilities)} responsibilities: {", ".join(metrics.responsibilities)}',
                severity='high',
                auto_fixable=False,
                suggested_fix='Split into separate modules for each responsibility'
            ))
        
        # Check forbidden patterns
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        for pattern in self.config['forbidden_patterns']:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_number = content[:match.start()].count('\n') + 1
                violations.append(ArchitecturalViolation(
                    rule_id='FORBIDDEN_PATTERN',
                    file_path=str(file_path),
                    line_number=line_number,
                    description=f'Forbidden pattern found: {match.group()}',
                    severity='high',
                    auto_fixable=True,
                    suggested_fix='Use secure configuration or proper logging'
                ))
        
        return violations
    
    def _check_dependency_violations(self) -> List[ArchitecturalViolation]:
        """Check for dependency rule violations."""
        violations = []
        
        # Build dependency graph
        for module_path, metrics in self.module_metrics.items():
            for dependency in metrics.dependencies:
                # Check if dependency is allowed
                module_layer = self._get_module_layer(module_path)
                if module_layer in self.config['dependency_rules']:
                    allowed_deps = self.config['dependency_rules'][module_layer]
                    if not any(dependency.startswith(allowed) for allowed in allowed_deps):
                        violations.append(ArchitecturalViolation(
                            rule_id='DEPENDENCY_VIOLATION',
                            file_path=module_path,
                            line_number=1,
                            description=f'Module in {module_layer} cannot depend on {dependency}',
                            severity='high',
                            auto_fixable=False,
                            suggested_fix='Refactor to follow dependency rules'
                        ))
        
        return violations
    
    def _get_module_layer(self, module_path: str) -> str:
        """Determine which architectural layer a module belongs to."""
        if 'core/' in module_path:
            return 'core/'
        elif 'utils/' in module_path:
            return 'utils/'
        elif 'services/' in module_path:
            return 'services/'
        else:
            return 'application/'
    
    def _calculate_health_score(self) -> float:
        """Calculate overall architectural health score."""
        if not self.module_metrics:
            return 0.0
        
        # Score based on violations
        critical_violations = sum(1 for v in self.violations if v.severity == 'critical')
        high_violations = sum(1 for v in self.violations if v.severity == 'high')
        medium_violations = sum(1 for v in self.violations if v.severity == 'medium')
        
        # Penalty for violations
        violation_penalty = (critical_violations * 10 + high_violations * 5 + medium_violations * 2)
        
        # Score based on module metrics
        total_files = len(self.module_metrics)
        large_files = sum(1 for m in self.module_metrics.values() if m.line_count > 500)
        complex_files = sum(1 for m in self.module_metrics.values() if m.complexity_score > 20)
        
        # Base score
        base_score = 100
        
        # Apply penalties
        size_penalty = (large_files / total_files) * 30
        complexity_penalty = (complex_files / total_files) * 20
        
        final_score = max(0, base_score - violation_penalty - size_penalty - complexity_penalty)
        
        return final_score
    
    def _generate_suggestions(self) -> List[str]:
        """Generate improvement suggestions based on analysis."""
        suggestions = []
        
        # File size suggestions
        large_files = [m for m in self.module_metrics.values() if m.line_count > 1000]
        if large_files:
            suggestions.append(f"Split {len(large_files)} large files (>1000 lines) into smaller modules")
        
        # Responsibility suggestions
        multi_responsibility_files = [m for m in self.module_metrics.values() if len(m.responsibilities) > 3]
        if multi_responsibility_files:
            suggestions.append(f"Extract responsibilities from {len(multi_responsibility_files)} files with multiple concerns")
        
        # Violation suggestions
        critical_violations = [v for v in self.violations if v.severity == 'critical']
        if critical_violations:
            suggestions.append(f"Address {len(critical_violations)} critical architectural violations")
        
        auto_fixable = [v for v in self.violations if v.auto_fixable]
        if auto_fixable:
            suggestions.append(f"Auto-fix {len(auto_fixable)} violations using automated refactoring")
        
        return suggestions
    
    def generate_report(self) -> str:
        """Generate a detailed architectural analysis report."""
        report = []
        report.append("# Architectural Analysis Report")
        report.append("=" * 50)
        
        # Summary
        report.append(f"\n## Summary")
        report.append(f"- **Files analyzed**: {len(self.module_metrics)}")
        report.append(f"- **Violations found**: {len(self.violations)}")
        report.append(f"- **Health score**: {self._calculate_health_score():.1f}/100")
        
        # Top violations
        report.append(f"\n## Top Violations")
        violation_counts = defaultdict(int)
        for v in self.violations:
            violation_counts[v.rule_id] += 1
        
        for rule_id, count in sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            report.append(f"- **{rule_id}**: {count} occurrences")
        
        # Largest files
        report.append(f"\n## Largest Files")
        largest_files = sorted(self.module_metrics.values(), key=lambda m: m.line_count, reverse=True)[:10]
        for metrics in largest_files:
            report.append(f"- **{Path(metrics.path).name}**: {metrics.line_count} lines, {len(metrics.responsibilities)} responsibilities")
        
        # Suggestions
        report.append(f"\n## Improvement Suggestions")
        for suggestion in self._generate_suggestions():
            report.append(f"- {suggestion}")
        
        return "\n".join(report)

def main():
    """Main function to run architectural analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Architectural Analysis Tool - Detect and prevent architectural violations'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to analyze (default: current directory)'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check mode - return non-zero exit code if violations found'
    )
    parser.add_argument(
        '--fail-on-violations',
        action='store_true',
        help='Fail if any violations are found (for pre-commit hooks)'
    )
    parser.add_argument(
        '--ci-mode',
        action='store_true',
        help='CI mode - minimal output, focus on violations'
    )
    parser.add_argument(
        '--score-only',
        action='store_true',
        help='Output only the health score'
    )
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Do not save report file'
    )
    
    args = parser.parse_args()
    
    if not args.ci_mode and not args.score_only:
        print("🏗️  ARCHITECTURAL ANALYSIS TOOL")
        print("=" * 50)
    
    linter = ArchitecturalLinter()
    
    # Analyze specified path
    results = linter.analyze_codebase(args.path)
    
    # Score only mode
    if args.score_only:
        print(f"{results['architectural_health_score']:.1f}")
        return
    
    # Generate report
    report = linter.generate_report()
    
    # CI mode - minimal output
    if args.ci_mode:
        print(f"Health Score: {results['architectural_health_score']:.1f}/100")
        print(f"Total Violations: {results['total_violations']}")
        if results['total_violations'] > 0:
            print("\nTop Violations:")
            for violation, count in list(results['violation_summary'].items())[:5]:
                print(f"  {violation}: {count}")
    else:
        print(report)
    
    # Save detailed results unless disabled
    if not args.no_report:
        report_path = Path('architectural_analysis_report.md')
        with open(report_path, 'w') as f:
            f.write(report)
        
        if not args.ci_mode:
            print(f"\n📊 Detailed report saved to: {report_path}")
            print(f"🎯 Health Score: {results['architectural_health_score']:.1f}/100")
    
    # Check mode - exit with error if violations found
    if (args.check or args.fail_on_violations) and results['total_violations'] > 0:
        if not args.ci_mode:
            print(f"\n❌ Found {results['total_violations']} architectural violations!")
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())