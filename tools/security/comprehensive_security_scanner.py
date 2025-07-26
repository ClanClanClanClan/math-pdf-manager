#!/usr/bin/env python3
"""
Comprehensive Security Scanner
Identifies and categorizes security vulnerabilities in Python code
"""

import ast
import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class SecurityVulnerability:
    """Represents a security vulnerability."""
    file_path: str
    line_number: int
    severity: str  # critical, high, medium, low
    category: str
    description: str
    code_snippet: str
    fix_suggestion: str

class SecurityScanner:
    """Comprehensive security vulnerability scanner."""
    
    def __init__(self):
        self.vulnerabilities: List[SecurityVulnerability] = []
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, List[Tuple]]:
        """Initialize security vulnerability patterns."""
        return {
            'hardcoded_secrets': [
                (r'password\s*=\s*["\'][^"\']{3,}["\']', 'Hardcoded password'),
                (r'secret\s*=\s*["\'][^"\']{10,}["\']', 'Hardcoded secret'),
                (r'api_key\s*=\s*["\'][^"\']{10,}["\']', 'Hardcoded API key'),
                (r'token\s*=\s*["\'][^"\']{10,}["\']', 'Hardcoded token'),
                (r'key\s*=\s*["\'][^"\']{16,}["\']', 'Hardcoded key'),
                (r'["\'][A-Za-z0-9]{32,}["\']', 'Potential hardcoded credential'),
                (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID'),
                (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
                (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
            ],
            'sql_injection': [
                (r'execute\s*\(\s*["\'].*?%s.*?["\']', 'SQL injection via string formatting'),
                (r'cursor\.execute\s*\(\s*["\'].*?\+.*?["\']', 'SQL injection via concatenation'),
                (r'query\s*=\s*["\'].*?%s.*?["\']', 'SQL injection in query string'),
                (r'\.format\s*\(.*?\)\s*.*?execute', 'SQL injection via .format()'),
                (r'f["\'].*?SELECT.*?\{.*?\}', 'SQL injection via f-string'),
            ],
            'command_injection': [
                (r'os\.system\s*\(.*?\+', 'Command injection via os.system'),
                (r'subprocess\.call\s*\(.*?\+', 'Command injection via subprocess.call'),
                (r'subprocess\.run\s*\(.*?\+', 'Command injection via subprocess.run'),
                (r'subprocess\.Popen\s*\(.*?\+', 'Command injection via subprocess.Popen'),
                (r'eval\s*\(.*?input', 'Code injection via eval'),
                (r'exec\s*\(.*?input', 'Code injection via exec'),
            ],
            'weak_crypto': [
                (r'md5\s*\(', 'Weak hash function MD5'),
                (r'sha1\s*\(', 'Weak hash function SHA1'),
                (r'\.md5\s*\(', 'Weak hash function MD5'),
                (r'\.sha1\s*\(', 'Weak hash function SHA1'),
                (r'DES\s*\(', 'Weak encryption algorithm DES'),
                (r'RC4\s*\(', 'Weak encryption algorithm RC4'),
                (r'random\.random\s*\(', 'Weak random number generator'),
                (r'random\.randint\s*\(', 'Weak random number generator'),
            ],
            'unsafe_deserialization': [
                (r'pickle\.loads\s*\(', 'Unsafe deserialization with pickle'),
                (r'pickle\.load\s*\(', 'Unsafe deserialization with pickle'),
                (r'yaml\.load\s*\(', 'Unsafe deserialization with yaml'),
                (r'marshal\.loads\s*\(', 'Unsafe deserialization with marshal'),
                (r'eval\s*\(', 'Unsafe deserialization with eval'),
            ],
            'path_traversal': [
                (r'open\s*\(.*?\+', 'Path traversal via file operations'),
                (r'os\.path\.join\s*\(.*?input', 'Path traversal via path operations'),
                (r'pathlib\.Path\s*\(.*?input', 'Path traversal via pathlib'),
                (r'\.\./', 'Direct path traversal sequence'),
            ],
            'xss_vulnerabilities': [
                (r'\.innerHTML\s*=', 'XSS via innerHTML'),
                (r'document\.write\s*\(', 'XSS via document.write'),
                (r'\.outerHTML\s*=', 'XSS via outerHTML'),
                (r'dangerouslySetInnerHTML', 'XSS via dangerouslySetInnerHTML'),
            ],
            'insecure_network': [
                (r'ssl_verify\s*=\s*False', 'Disabled SSL verification'),
                (r'verify\s*=\s*False', 'Disabled SSL verification'),
                (r'http://', 'Insecure HTTP protocol'),
                (r'CERT_NONE', 'Disabled certificate verification'),
                (r'ssl\.CERT_NONE', 'Disabled SSL certificate verification'),
            ]
        }
    
    def scan_file(self, file_path: Path) -> List[SecurityVulnerability]:
        """Scan a single file for vulnerabilities."""
        vulnerabilities = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            return vulnerabilities
        
        # Pattern-based scanning
        for category, patterns in self.patterns.items():
            for pattern, description in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        severity = self._determine_severity(category, description)
                        vulnerability = SecurityVulnerability(
                            file_path=str(file_path),
                            line_number=line_num,
                            severity=severity,
                            category=category,
                            description=description,
                            code_snippet=line.strip(),
                            fix_suggestion=self._get_fix_suggestion(category, description)
                        )
                        vulnerabilities.append(vulnerability)
        
        # AST-based scanning for more complex patterns
        try:
            tree = ast.parse(content)
            ast_vulnerabilities = self._scan_ast(tree, str(file_path), lines)
            vulnerabilities.extend(ast_vulnerabilities)
        except SyntaxError:
            pass  # Skip files with syntax errors
        
        return vulnerabilities
    
    def _scan_ast(self, tree: ast.AST, file_path: str, lines: List[str]) -> List[SecurityVulnerability]:
        """Scan AST for complex vulnerabilities."""
        vulnerabilities = []
        
        for node in ast.walk(tree):
            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    line_num = node.lineno
                    vulnerability = SecurityVulnerability(
                        file_path=file_path,
                        line_number=line_num,
                        severity='medium',
                        category='exception_handling',
                        description='Bare except clause catches all exceptions',
                        code_snippet=lines[line_num - 1].strip() if line_num <= len(lines) else '',
                        fix_suggestion='Use specific exception types like "except Exception as e:"'
                    )
                    vulnerabilities.append(vulnerability)
            
            # Check for dangerous function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec']:
                        line_num = node.lineno
                        vulnerability = SecurityVulnerability(
                            file_path=file_path,
                            line_number=line_num,
                            severity='critical',
                            category='code_injection',
                            description=f'Use of dangerous function: {node.func.id}',
                            code_snippet=lines[line_num - 1].strip() if line_num <= len(lines) else '',
                            fix_suggestion=f'Avoid using {node.func.id} with user input'
                        )
                        vulnerabilities.append(vulnerability)
                
                elif isinstance(node.func, ast.Attribute):
                    # Check for dangerous method calls
                    if node.func.attr in ['system', 'popen']:
                        line_num = node.lineno
                        vulnerability = SecurityVulnerability(
                            file_path=file_path,
                            line_number=line_num,
                            severity='high',
                            category='command_injection',
                            description=f'Use of dangerous method: {node.func.attr}',
                            code_snippet=lines[line_num - 1].strip() if line_num <= len(lines) else '',
                            fix_suggestion=f'Use subprocess with proper input sanitization instead of {node.func.attr}'
                        )
                        vulnerabilities.append(vulnerability)
        
        return vulnerabilities
    
    def _determine_severity(self, category: str, description: str) -> str:
        """Determine severity based on category and description."""
        critical_keywords = ['injection', 'eval', 'exec', 'pickle', 'aws', 'api_key', 'token']
        high_keywords = ['password', 'secret', 'key', 'system', 'command']
        medium_keywords = ['md5', 'sha1', 'ssl', 'http', 'random']
        
        desc_lower = description.lower()
        
        if any(keyword in desc_lower for keyword in critical_keywords):
            return 'critical'
        elif any(keyword in desc_lower for keyword in high_keywords):
            return 'high'
        elif any(keyword in desc_lower for keyword in medium_keywords):
            return 'medium'
        else:
            return 'low'
    
    def _get_fix_suggestion(self, category: str, description: str) -> str:
        """Get fix suggestion based on vulnerability type."""
        suggestions = {
            'hardcoded_secrets': 'Use environment variables or secure credential management',
            'sql_injection': 'Use parameterized queries or ORM',
            'command_injection': 'Use subprocess with proper input sanitization',
            'weak_crypto': 'Use SHA-256 or better cryptographic functions',
            'unsafe_deserialization': 'Use safe serialization formats like JSON',
            'path_traversal': 'Validate and sanitize file paths',
            'xss_vulnerabilities': 'Sanitize user input and use safe DOM manipulation',
            'insecure_network': 'Enable SSL verification and use HTTPS',
            'exception_handling': 'Use specific exception types',
            'code_injection': 'Avoid dynamic code execution with user input'
        }
        
        return suggestions.get(category, 'Review and fix the security issue')
    
    def scan_directory(self, directory: Path) -> List[SecurityVulnerability]:
        """Scan all Python files in a directory."""
        all_vulnerabilities = []
        
        for file_path in directory.rglob('*.py'):
            if file_path.is_file():
                vulnerabilities = self.scan_file(file_path)
                all_vulnerabilities.extend(vulnerabilities)
        
        return all_vulnerabilities
    
    def generate_report(self, vulnerabilities: List[SecurityVulnerability]) -> str:
        """Generate a comprehensive security report."""
        if not vulnerabilities:
            return "🎉 No security vulnerabilities found!"
        
        # Group by severity
        by_severity = defaultdict(list)
        for vuln in vulnerabilities:
            by_severity[vuln.severity].append(vuln)
        
        # Group by category
        by_category = defaultdict(list)
        for vuln in vulnerabilities:
            by_category[vuln.category].append(vuln)
        
        report = []
        report.append("🔐 SECURITY VULNERABILITY REPORT")
        report.append("=" * 50)
        report.append(f"Total vulnerabilities found: {len(vulnerabilities)}")
        report.append("")
        
        # Severity breakdown
        report.append("📊 SEVERITY BREAKDOWN:")
        for severity in ['critical', 'high', 'medium', 'low']:
            count = len(by_severity[severity])
            if count > 0:
                report.append(f"  {severity.upper()}: {count}")
        report.append("")
        
        # Category breakdown
        report.append("📈 CATEGORY BREAKDOWN:")
        for category, vulns in by_category.items():
            report.append(f"  {category.replace('_', ' ').title()}: {len(vulns)}")
        report.append("")
        
        # Detailed vulnerabilities
        report.append("🚨 DETAILED VULNERABILITIES:")
        report.append("")
        
        for severity in ['critical', 'high', 'medium', 'low']:
            if by_severity[severity]:
                report.append(f"### {severity.upper()} SEVERITY ###")
                report.append("")
                
                for vuln in by_severity[severity]:
                    report.append(f"File: {vuln.file_path}")
                    report.append(f"Line: {vuln.line_number}")
                    report.append(f"Issue: {vuln.description}")
                    report.append(f"Code: {vuln.code_snippet}")
                    report.append(f"Fix: {vuln.fix_suggestion}")
                    report.append("-" * 30)
                report.append("")
        
        return "\n".join(report)

def main():
    """Main function to run the security scanner."""
    scanner = SecurityScanner()
    
    # Scan current directory
    current_dir = Path.cwd()
    print(f"🔍 Scanning directory: {current_dir}")
    
    vulnerabilities = scanner.scan_directory(current_dir)
    
    # Generate and display report
    report = scanner.generate_report(vulnerabilities)
    print(report)
    
    # Save report to file
    with open('security_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n💾 Report saved to: security_report.txt")
    
    # Return summary
    critical_count = sum(1 for v in vulnerabilities if v.severity == 'critical')
    high_count = sum(1 for v in vulnerabilities if v.severity == 'high')
    
    if critical_count > 0:
        print(f"🚨 CRITICAL: {critical_count} critical vulnerabilities need immediate attention!")
    if high_count > 0:
        print(f"⚠️  HIGH: {high_count} high-severity vulnerabilities found!")
    
    return len(vulnerabilities)

if __name__ == "__main__":
    total_vulns = main()
    sys.exit(0 if total_vulns == 0 else 1)