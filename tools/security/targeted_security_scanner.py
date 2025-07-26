#!/usr/bin/env python3
"""
Targeted Security Scanner
Focuses on key security vulnerabilities that need fixing
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class SecurityIssue:
    """A security issue found in the code."""
    file_path: str
    line_number: int
    severity: str
    type: str
    description: str
    code: str
    
class TargetedSecurityScanner:
    """Scanner focused on critical security issues."""
    
    def __init__(self):
        self.issues: List[SecurityIssue] = []
        
    def scan_file(self, file_path: Path) -> List[SecurityIssue]:
        """Scan a single file for critical security issues."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return issues
            
        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
                
            # Check for hardcoded secrets
            if self._contains_hardcoded_secret(line):
                issues.append(SecurityIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    severity='high',
                    type='hardcoded_secret',
                    description='Potential hardcoded credential',
                    code=stripped
                ))
            
            # Check for SQL injection risks
            if self._contains_sql_injection_risk(line):
                issues.append(SecurityIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    severity='high',
                    type='sql_injection',
                    description='Potential SQL injection vulnerability',
                    code=stripped
                ))
            
            # Check for command injection risks
            if self._contains_command_injection_risk(line):
                issues.append(SecurityIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    severity='high',
                    type='command_injection',
                    description='Potential command injection vulnerability',
                    code=stripped
                ))
            
            # Check for weak crypto
            if self._contains_weak_crypto(line):
                issues.append(SecurityIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    severity='medium',
                    type='weak_crypto',
                    description='Weak cryptographic function',
                    code=stripped
                ))
            
            # Check for unsafe deserialization
            if self._contains_unsafe_deserialization(line):
                issues.append(SecurityIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    severity='critical',
                    type='unsafe_deserialization',
                    description='Unsafe deserialization',
                    code=stripped
                ))
            
            # Check for insecure network
            if self._contains_insecure_network(line):
                issues.append(SecurityIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    severity='medium',
                    type='insecure_network',
                    description='Insecure network configuration',
                    code=stripped
                ))
            
            # Check for bare except
            if self._contains_bare_except(line):
                issues.append(SecurityIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    severity='medium',
                    type='bare_except',
                    description='Bare except clause',
                    code=stripped
                ))
        
        return issues
    
    def _contains_hardcoded_secret(self, line: str) -> bool:
        """Check if line contains hardcoded secrets."""
        patterns = [
            r'password\s*=\s*["\'][^"\']{3,}["\']',
            r'secret\s*=\s*["\'][^"\']{10,}["\']',
            r'api_key\s*=\s*["\'][^"\']{10,}["\']',
            r'token\s*=\s*["\'][^"\']{10,}["\']',
            r'key\s*=\s*["\'][^"\']{16,}["\']',
            r'AKIA[0-9A-Z]{16}',
            r'sk-[a-zA-Z0-9]{48}',
            r'ghp_[a-zA-Z0-9]{36}',
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _contains_sql_injection_risk(self, line: str) -> bool:
        """Check if line contains SQL injection risks."""
        patterns = [
            r'execute\s*\(\s*["\'].*?%s.*?["\']',
            r'cursor\.execute\s*\(\s*["\'].*?\+.*?["\']',
            r'query\s*=\s*["\'].*?%s.*?["\']',
            r'\.format\s*\(.*?\)\s*.*?execute',
            r'f["\'].*?SELECT.*?\{.*?\}',
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _contains_command_injection_risk(self, line: str) -> bool:
        """Check if line contains command injection risks."""
        patterns = [
            r'os\.system\s*\(.*?\+',
            r'subprocess\.call\s*\(.*?\+',
            r'subprocess\.run\s*\(.*?\+',
            r'subprocess\.Popen\s*\(.*?\+',
            r'eval\s*\(.*?input',
            r'exec\s*\(.*?input',
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _contains_weak_crypto(self, line: str) -> bool:
        """Check if line contains weak cryptographic functions."""
        patterns = [
            r'\.md5\s*\(',
            r'\.sha1\s*\(',
            r'hashlib\.md5\s*\(',
            r'hashlib\.sha1\s*\(',
            r'random\.random\s*\(',
            r'random\.randint\s*\(',
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _contains_unsafe_deserialization(self, line: str) -> bool:
        """Check if line contains unsafe deserialization."""
        patterns = [
            r'pickle\.loads\s*\(',
            r'pickle\.load\s*\(',
            r'yaml\.load\s*\(',
            r'marshal\.loads\s*\(',
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _contains_insecure_network(self, line: str) -> bool:
        """Check if line contains insecure network configurations."""
        patterns = [
            r'ssl_verify\s*=\s*False',
            r'verify\s*=\s*False',
            r'CERT_NONE',
            r'ssl\.CERT_NONE',
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _contains_bare_except(self, line: str) -> bool:
        """Check if line contains bare except clause."""
        return re.search(r'except\s*:', line) is not None
    
    def scan_directory(self, directory: Path) -> List[SecurityIssue]:
        """Scan all Python files in directory."""
        all_issues = []
        
        for file_path in directory.rglob('*.py'):
            if file_path.is_file():
                issues = self.scan_file(file_path)
                all_issues.extend(issues)
        
        return all_issues
    
    def generate_summary(self, issues: List[SecurityIssue]) -> str:
        """Generate a summary report."""
        if not issues:
            return "✅ No security issues found!"
        
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        
        for issue in issues:
            by_severity[issue.severity] += 1
            by_type[issue.type] += 1
        
        summary = []
        summary.append(f"🔍 Found {len(issues)} security issues")
        summary.append("")
        
        # Severity breakdown
        summary.append("📊 By Severity:")
        for severity in ['critical', 'high', 'medium', 'low']:
            count = by_severity[severity]
            if count > 0:
                summary.append(f"  {severity.upper()}: {count}")
        
        summary.append("")
        
        # Type breakdown
        summary.append("📈 By Type:")
        for issue_type, count in by_type.items():
            summary.append(f"  {issue_type.replace('_', ' ').title()}: {count}")
        
        return "\n".join(summary)

def main():
    """Main function."""
    scanner = TargetedSecurityScanner()
    
    # Scan current directory
    current_dir = Path.cwd()
    print(f"🔍 Scanning directory: {current_dir}")
    
    issues = scanner.scan_directory(current_dir)
    
    # Generate summary
    summary = scanner.generate_summary(issues)
    print(summary)
    
    # Show critical and high issues
    critical_high = [i for i in issues if i.severity in ['critical', 'high']]
    
    if critical_high:
        print("\n🚨 CRITICAL & HIGH SEVERITY ISSUES:")
        print("-" * 50)
        
        for issue in critical_high[:20]:  # Show first 20
            print(f"File: {issue.file_path}:{issue.line_number}")
            print(f"Type: {issue.type}")
            print(f"Severity: {issue.severity}")
            print(f"Code: {issue.code}")
            print("-" * 30)
    
    return len(issues)

if __name__ == "__main__":
    total_issues = main()
    print(f"\n🎯 Total issues found: {total_issues}")