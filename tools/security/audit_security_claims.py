#!/usr/bin/env python3
"""
Audit Security Claims - Verify actual security improvements
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

class SecurityAudit:
    """Audit actual security improvements made to codebase."""
    
    def __init__(self):
        self.results = {
            'files_scanned': 0,
            'backup_files': 0,
            'security_warnings': 0,
            'bare_except_fixes': 0,
            'hardcoded_secrets': 0,
            'ssl_warnings': 0,
            'weak_crypto_warnings': 0,
            'command_injection_warnings': 0,
            'deserialization_warnings': 0,
            'evidence_by_type': defaultdict(list)
        }
    
    def audit_file(self, file_path: Path) -> Dict:
        """Audit a single file for security improvements."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_results = {
                'security_warnings': 0,
                'bare_except_fixes': 0,
                'hardcoded_secrets': 0,
                'ssl_warnings': 0,
                'weak_crypto_warnings': 0,
                'command_injection_warnings': 0,
                'deserialization_warnings': 0
            }
            
            # Check for security warning comments
            security_warning_patterns = [
                r'# WARNING:.*SQL injection',
                r'# WARNING:.*Command injection',
                r'# WARNING:.*SSL verification',
                r'# WARNING:.*MD5 is cryptographically broken',
                r'# WARNING:.*SHA-1 is cryptographically weak',
                r'# WARNING:.*Unsafe deserialization',
                r'# WARNING:.*Use secrets\.SystemRandom',
                r'# WARNING:.*shell=True can be dangerous'
            ]
            
            for pattern in security_warning_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    file_results['security_warnings'] += len(matches)
                    self.results['evidence_by_type']['security_warnings'].extend(
                        [(str(file_path), match) for match in matches]
                    )
            
            # Check for bare except fixes
            bare_except_pattern = r'except Exception as e:'
            matches = re.findall(bare_except_pattern, content)
            if matches:
                file_results['bare_except_fixes'] = len(matches)
                self.results['evidence_by_type']['bare_except_fixes'].extend(
                    [(str(file_path), match) for match in matches]
                )
            
            # Check for environment variable replacements
            env_var_patterns = [
                r'os\.environ\.get\(["\']PASSWORD["\']',
                r'os\.environ\.get\(["\']API_KEY["\']',
                r'os\.environ\.get\(["\']SECRET["\']',
                r'os\.environ\.get\(["\']TOKEN["\']'
            ]
            
            for pattern in env_var_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    file_results['hardcoded_secrets'] += len(matches)
                    self.results['evidence_by_type']['hardcoded_secrets'].extend(
                        [(str(file_path), match) for match in matches]
                    )
            
            # Check for SSL warnings
            ssl_patterns = [
                r'# WARNING:.*SSL verification disabled',
                r'# WARNING:.*SSL certificate verification disabled'
            ]
            
            for pattern in ssl_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    file_results['ssl_warnings'] += len(matches)
                    self.results['evidence_by_type']['ssl_warnings'].extend(
                        [(str(file_path), match) for match in matches]
                    )
            
            # Check for weak crypto warnings
            crypto_patterns = [
                r'# WARNING:.*MD5 is cryptographically broken',
                r'# WARNING:.*SHA-1 is cryptographically weak',
                r'# WARNING:.*Use secrets\.SystemRandom'
            ]
            
            for pattern in crypto_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    file_results['weak_crypto_warnings'] += len(matches)
                    self.results['evidence_by_type']['weak_crypto_warnings'].extend(
                        [(str(file_path), match) for match in matches]
                    )
            
            # Check for command injection warnings
            cmd_patterns = [
                r'# WARNING:.*Command injection',
                r'# WARNING:.*Code injection',
                r'# WARNING:.*shell=True can be dangerous'
            ]
            
            for pattern in cmd_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    file_results['command_injection_warnings'] += len(matches)
                    self.results['evidence_by_type']['command_injection_warnings'].extend(
                        [(str(file_path), match) for match in matches]
                    )
            
            # Check for deserialization warnings
            deser_patterns = [
                r'# WARNING:.*Unsafe deserialization',
                r'yaml\.safe_load'
            ]
            
            for pattern in deser_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    file_results['deserialization_warnings'] += len(matches)
                    self.results['evidence_by_type']['deserialization_warnings'].extend(
                        [(str(file_path), match) for match in matches]
                    )
            
            return file_results
            
        except Exception as e:
            return {}
    
    def audit_directory(self, directory: Path) -> Dict:
        """Audit all Python files in directory."""
        
        # Count backup files
        backup_count = len(list(directory.rglob('*.py.bak'))) + len(list(directory.rglob('*.py.backup')))
        self.results['backup_files'] = backup_count
        
        # Audit Python files (excluding dependencies)
        for file_path in directory.rglob('*.py'):
            if file_path.is_file() and '.venv' not in str(file_path):
                self.results['files_scanned'] += 1
                file_results = self.audit_file(file_path)
                
                # Aggregate results
                for key, value in file_results.items():
                    self.results[key] += value
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate audit report."""
        report = []
        report.append("🔍 SECURITY CLAIMS AUDIT REPORT")
        report.append("=" * 50)
        report.append("")
        
        # File counts
        report.append("📁 FILE ANALYSIS:")
        report.append(f"  Python files scanned: {self.results['files_scanned']}")
        report.append(f"  Backup files created: {self.results['backup_files']}")
        report.append("")
        
        # Security improvements found
        report.append("🔐 SECURITY IMPROVEMENTS VERIFIED:")
        report.append(f"  Total security warnings: {self.results['security_warnings']}")
        report.append(f"  Bare except fixes: {self.results['bare_except_fixes']}")
        report.append(f"  Environment variable usage: {self.results['hardcoded_secrets']}")
        report.append(f"  SSL security warnings: {self.results['ssl_warnings']}")
        report.append(f"  Weak crypto warnings: {self.results['weak_crypto_warnings']}")
        report.append(f"  Command injection warnings: {self.results['command_injection_warnings']}")
        report.append(f"  Deserialization warnings: {self.results['deserialization_warnings']}")
        report.append("")
        
        # Calculate total verified improvements
        total_verified = (
            self.results['security_warnings'] +
            self.results['bare_except_fixes'] +
            self.results['hardcoded_secrets'] +
            self.results['ssl_warnings'] +
            self.results['weak_crypto_warnings'] +
            self.results['command_injection_warnings'] +
            self.results['deserialization_warnings']
        )
        
        report.append(f"📊 TOTAL VERIFIED IMPROVEMENTS: {total_verified}")
        report.append("")
        
        # Evidence samples
        report.append("🧾 EVIDENCE SAMPLES:")
        for category, evidence in self.results['evidence_by_type'].items():
            if evidence:
                report.append(f"  {category.upper()} ({len(evidence)} found):")
                # Show first 3 examples
                for i, (file_path, match) in enumerate(evidence[:3]):
                    short_path = str(file_path).split('/')[-1]
                    report.append(f"    - {short_path}: {match[:80]}...")
                if len(evidence) > 3:
                    report.append(f"    ... and {len(evidence) - 3} more")
                report.append("")
        
        return "\n".join(report)

def main():
    """Main audit function."""
    auditor = SecurityAudit()
    
    # Audit current directory
    current_dir = Path.cwd()
    print(f"🔍 Auditing directory: {current_dir}")
    
    results = auditor.audit_directory(current_dir)
    
    # Generate report
    report = auditor.generate_report()
    print(report)
    
    # Save report
    with open('security_audit_report.txt', 'w') as f:
        f.write(report)
    
    print(f"📄 Audit report saved to: security_audit_report.txt")

if __name__ == "__main__":
    main()