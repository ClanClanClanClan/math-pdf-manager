#!/usr/bin/env python3
"""
Fix the comprehensive validator to properly handle multiple authors in filenames.
"""

import re
from pathlib import Path

def fix_comprehensive_validator():
    """Fix the author parsing logic in comprehensive validator."""
    
    validator_path = Path("src/core/validation/comprehensive_validator.py")
    
    # Read the current content
    with open(validator_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Update the filename pattern to better handle multiple authors
    # The current pattern is too simple
    old_pattern = r"self.ACADEMIC_FILENAME_PATTERN = re.compile\(\s*r'\^\\(\[\\^-\\]\\+\\)\\s\*-\\s\*\\(\.\\+\\)\\\\.pdf\$'\s*\\)"
    
    # New pattern that looks for the last dash before .pdf
    new_pattern = '''self.ACADEMIC_FILENAME_PATTERN = re.compile(
            r'^(.+?)\\s*-\\s*([^-]+)\\.pdf$'
        )'''
    
    content = re.sub(old_pattern, new_pattern, content)
    
    # Fix 2: Update the validate_academic_filename method to handle the case better
    # Find the validate_academic_filename method
    validate_method_pattern = r"(def validate_academic_filename\(self, filename: str\) -> ValidationResult:.*?)(# Check basic format.*?)(authors_part, title_part = match\.groups\(\))"
    
    replacement = r'''\1\2# For multiple authors, we need smarter parsing
        # The pattern captures everything before the last dash as authors
        authors_part, title_part = match.groups()
        
        # However, if there are multiple dashes, we need to check if they're author separators
        # or part of the title. A heuristic: if a segment looks like an author name, it's an author
        parts = filename[:-4].split(' - ')  # Remove .pdf and split by ' - '
        
        # Try to determine where authors end and title begins
        author_parts = []
        title_parts = []
        found_title = False
        
        for i, part in enumerate(parts):
            part = part.strip()
            # Check if this looks like an author name (starts with capital, has proper name structure)
            # If we haven't found the title yet and it matches author pattern, it's likely an author
            if not found_title and self._looks_like_author_name(part):
                author_parts.append(part)
            else:
                # Once we find something that doesn't look like an author, the rest is the title
                found_title = True
                title_parts.append(part)
        
        # If we didn't find any title parts, the last part is the title
        if not title_parts and len(author_parts) > 1:
            title_parts.append(author_parts.pop())
        
        # Reconstruct authors and title
        if author_parts and title_parts:
            authors_part = ' - '.join(author_parts)
            title_part = ' - '.join(title_parts)
        else:
            # Fallback to original parsing
            authors_part, title_part = match.groups()'''
    
    content = re.sub(validate_method_pattern, replacement, content, flags=re.DOTALL)
    
    # Fix 3: Add the helper method to check if something looks like an author name
    helper_method = '''
    def _looks_like_author_name(self, text: str) -> bool:
        """Check if text looks like an author name."""
        # Basic heuristic: starts with capital letter, contains mostly letters
        # and common name separators (space, hyphen, apostrophe)
        if not text:
            return False
            
        # Remove common academic titles
        text = re.sub(r'^(Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)\s*', '', text, flags=re.IGNORECASE)
        
        # Check if it matches common author name patterns
        # Single name, First Last, First Middle Last, etc.
        name_patterns = [
            r'^[A-Z][a-z]+$',  # Single name
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+$',  # First Last
            r'^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+$',  # First M. Last
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+$',  # First Middle Last
            r'^[A-Z][a-z]+-[A-Z][a-z]+\s+[A-Z][a-z]+$',  # Hyphenated first name
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+-[A-Z][a-z]+$',  # Hyphenated last name
        ]
        
        for pattern in name_patterns:
            if re.match(pattern, text):
                return True
        
        # Also check if it's a known mathematician
        if any(math_name in text for math_name in self.FAMOUS_MATHEMATICIANS):
            return True
            
        return False
'''
    
    # Find a good place to insert the helper method (after _validate_authors)
    insert_position = content.find("def _validate_title(self")
    if insert_position > 0:
        content = content[:insert_position] + helper_method + "\n    " + content[insert_position:]
    
    # Write the fixed content back
    with open(validator_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed comprehensive validator author parsing")
    
    # Also fix the test to be more explicit about what it expects
    test_path = Path("tests/core/test_comprehensive_validation.py")
    
    with open(test_path, 'r', encoding='utf-8') as f:
        test_content = f.read()
    
    # Update the test to add a clearer test case
    old_test = '''        # Multiple authors
        result = validator.validate_academic_filename("Smith - Jones - Advanced Calculus.pdf")
        assert result.is_valid == True
        assert len(result.metadata['authors']) == 2'''
    
    new_test = '''        # Multiple authors with clear separation
        result = validator.validate_academic_filename("Smith - Jones - Advanced Calculus.pdf")
        assert result.is_valid == True
        # This should parse as authors: "Smith - Jones", title: "Advanced Calculus"
        assert len(result.metadata['authors']) == 2
        
        # Test with clearer formatting
        result = validator.validate_academic_filename("John Smith - Jane Doe - Introduction to Algebra.pdf")
        assert result.is_valid == True
        assert len(result.metadata['authors']) == 2'''
    
    test_content = test_content.replace(old_test, new_test)
    
    with open(test_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print("✅ Updated test for clarity")

if __name__ == "__main__":
    fix_comprehensive_validator()