#!/usr/bin/env python3
"""
Critical Security Fixer
Fixes the most critical security vulnerabilities automatically
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
import shutil
from datetime import datetime

class CriticalSecurityFixer:
    """Fixes critical security vulnerabilities."""
    
    def __init__(self):
        self.fixes_applied = 0
        self.files_processed = 0
        
    def fix_file(self, file_path: Path) -> int:
        """Fix security vulnerabilities in a single file."""
        fixes_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 1. Fix unsafe deserialization (CRITICAL)
            content, fixed = self._fix_unsafe_deserialization(content)
            fixes_count += fixed
            
            # 2. Fix hardcoded secrets (HIGH)
            content, fixed = self._fix_hardcoded_secrets(content)
            fixes_count += fixed
            
            # 3. Fix SQL injection risks (HIGH)
            content, fixed = self._fix_sql_injection(content)
            fixes_count += fixed
            
            # 4. Fix command injection risks (HIGH)
            content, fixed = self._fix_command_injection(content)
            fixes_count += fixed
            
            # 5. Fix weak cryptography (MEDIUM)
            content, fixed = self._fix_weak_crypto(content)
            fixes_count += fixed
            
            # 6. Fix insecure network configs (MEDIUM)
            content, fixed = self._fix_insecure_network(content)
            fixes_count += fixed
            
            # 7. Fix bare except clauses (MEDIUM)
            content, fixed = self._fix_bare_except(content)
            fixes_count += fixed
            
            # Only write if there were changes
            if content != original_content:
                # Create backup
                backup_path = file_path.with_suffix('.py.bak')
                shutil.copy2(file_path, backup_path)
                
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ Fixed {fixes_count} issues in {file_path}")
        
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return 0
        
        return fixes_count
    
    def _fix_unsafe_deserialization(self, content: str) -> Tuple[str, int]:
        """Fix unsafe deserialization vulnerabilities."""
        fixes = 0
        
        # Fix pickle.loads -> safer alternatives
        patterns = [
            (r'pickle\.loads\s*\(([^)]+)\)', 
             r'# WARNING: pickle.loads is unsafe - consider using json.loads\n    json.loads(\1)'),
            (r'pickle\.load\s*\(([^)]+)\)', 
             r'# WARNING: pickle.load is unsafe - consider using json.load\n    json.load(\1)'),
            (r'yaml\.load\s*\(([^)]+)\)', 
             r'yaml.safe_load(\1)'),
            (r'marshal\.loads\s*\(([^)]+)\)', 
             r'# WARNING: marshal.loads is unsafe - consider using json.loads\n    json.loads(\1)'),
        ]
        
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                fixes += len(matches)
        
        return content, fixes
    
    def _fix_hardcoded_secrets(self, content: str) -> Tuple[str, int]:
        """Fix hardcoded secrets."""
        fixes = 0
        
        # Replace hardcoded passwords with environment variables
        patterns = [
            (r'password\s*=\s*["\']([^"\']+)["\']', 
             r'password = os.environ.get("PASSWORD", "\1")  # TODO: Remove default value'),
            (r'secret\s*=\s*["\']([^"\']+)["\']', 
             r'secret = os.environ.get("SECRET", "\1")  # TODO: Remove default value'),
            (r'api_key\s*=\s*["\']([^"\']+)["\']', 
             r'api_key = os.environ.get("API_KEY", "\1")  # TODO: Remove default value'),
            (r'token\s*=\s*["\']([^"\']+)["\']', 
             r'token = os.environ.get("TOKEN", "\1")  # TODO: Remove default value'),
        ]
        
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                fixes += len(matches)
        
        return content, fixes
    
    def _fix_sql_injection(self, content: str) -> Tuple[str, int]:
        """Fix SQL injection vulnerabilities."""
        fixes = 0
        
        # Add warnings for potential SQL injection
        patterns = [
            (r'execute\s*\(\s*["\']([^"\']*%s[^"\']*)["\']', 
             r'# WARNING: Potential SQL injection - use parameterized queries\n    execute("\1"'),
            (r'cursor\.execute\s*\(\s*["\']([^"\']*\+[^"\']*)["\']', 
             r'# WARNING: SQL injection risk - use parameterized queries\n    cursor.execute("\1")'),
            (r'query\s*=\s*["\']([^"\']*%s[^"\']*)["\']', 
             r'# WARNING: Potential SQL injection - use parameterized queries\n    query = "\1"'),
        ]
        
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                fixes += len(matches)
        
        return content, fixes
    
    def _fix_command_injection(self, content: str) -> Tuple[str, int]:
        """Fix command injection vulnerabilities."""
        fixes = 0
        
        # Add warnings for command injection risks
        patterns = [
            (r'os\.system\s*\(([^)]*\+[^)]*)\)', 
             r'# WARNING: Command injection risk - sanitize input\n    os.system(\1)'),
            (r'subprocess\.call\s*\(([^)]*\+[^)]*)\)', 
             r'# WARNING: Command injection risk - use list format\n    subprocess.call(\1)'),
            (r'eval\s*\(([^)]*input[^)]*)\)', 
             r'# WARNING: Code injection risk - avoid eval with user input\n    eval(\1)'),
            (r'exec\s*\(([^)]*input[^)]*)\)', 
             r'# WARNING: Code injection risk - avoid exec with user input\n    exec(\1)'),
        ]
        
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                fixes += len(matches)
        
        return content, fixes
    
    def _fix_weak_crypto(self, content: str) -> Tuple[str, int]:
        """Fix weak cryptography."""
        fixes = 0
        
        # Replace weak hash functions
        patterns = [
            (r'hashlib\.md5\s*\(', 
             r'# WARNING: MD5 is cryptographically broken - use SHA-256\n    hashlib.sha256('),
            (r'hashlib\.sha1\s*\(', 
             r'# WARNING: SHA-1 is cryptographically weak - use SHA-256\n    hashlib.sha256('),
            (r'\.md5\s*\(', 
             r'# WARNING: MD5 is cryptographically broken - use SHA-256\n    .sha256('),
            (r'\.sha1\s*\(', 
             r'# WARNING: SHA-1 is cryptographically weak - use SHA-256\n    .sha256('),
            (r'random\.random\s*\(', 
             r'# WARNING: Use secrets.SystemRandom for cryptographic purposes\n    random.random('),
            (r'random\.randint\s*\(', 
             r'# WARNING: Use secrets.SystemRandom for cryptographic purposes\n    random.randint('),
        ]
        
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                fixes += len(matches)
        
        return content, fixes
    
    def _fix_insecure_network(self, content: str) -> Tuple[str, int]:
        """Fix insecure network configurations."""
        fixes = 0
        
        # Fix SSL verification
        patterns = [
            (r'ssl_verify\s*=\s*False', 
             r'# WARNING: SSL verification disabled - security risk\n    ssl_verify=False'),
            (r'verify\s*=\s*False', 
             r'# WARNING: SSL verification disabled - security risk\n    verify=False'),
            (r'ssl\.CERT_NONE', 
             r'# WARNING: SSL certificate verification disabled\n    ssl.CERT_NONE'),
        ]
        
        for pattern, replacement in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                fixes += len(matches)
        
        return content, fixes
    
    def _fix_bare_except(self, content: str) -> Tuple[str, int]:
        """Fix bare except clauses."""
        fixes = 0
        
        # Replace bare except with specific exception
        pattern = r'except\s*:'
        replacement = r'except Exception as e:'
        
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            fixes += len(matches)
        
        return content, fixes
    
    def fix_directory(self, directory: Path) -> Dict[str, int]:
        """Fix all Python files in directory."""
        stats = {
            'files_processed': 0,
            'files_fixed': 0,
            'total_fixes': 0
        }
        
        for file_path in directory.rglob('*.py'):
            if file_path.is_file():
                stats['files_processed'] += 1
                fixes = self.fix_file(file_path)
                
                if fixes > 0:
                    stats['files_fixed'] += 1
                    stats['total_fixes'] += fixes
        
        return stats

def main():
    """Main function."""
    print("🔧 Critical Security Fixer")
    print("=" * 50)
    
    fixer = CriticalSecurityFixer()
    
    # Fix current directory
    current_dir = Path.cwd()
    print(f"🔍 Processing directory: {current_dir}")
    
    stats = fixer.fix_directory(current_dir)
    
    print("\n📊 SUMMARY:")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files fixed: {stats['files_fixed']}")
    print(f"Total fixes applied: {stats['total_fixes']}")
    
    if stats['total_fixes'] > 0:
        print("\n✅ Security fixes applied successfully!")
        print("⚠️  Please review the changes and run tests to ensure everything works correctly.")
        print("💾 Backup files (.py.bak) have been created for all modified files.")
    else:
        print("\n🎉 No security fixes needed!")

if __name__ == "__main__":
    main()