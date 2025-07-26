# ================================================================
#  Mathematician Name Validator — v1.0.0 (2025-07-13, COMPREHENSIVE)
#  Ultra-robust validation system for mathematician names across 8 languages
#  Handles Unicode normalization, script variations, and name variants
# ================================================================

from __future__ import annotations
import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher

# Import YAML with fallback handling
try:
    import yaml
    YAML_AVAILABLE = hasattr(yaml, 'safe_load')
    if not YAML_AVAILABLE:
        # Fallback to manual parsing if standard PyYAML not available
        yaml = None
except ImportError:
    yaml = None
    YAML_AVAILABLE = False

def simple_yaml_load(filepath: Path) -> dict:
    """Simple YAML parser fallback for basic YAML structures"""
    try:
        if YAML_AVAILABLE:
            with open(filepath, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            # Simple regex-based YAML parser for our specific format
            result = {}
            current_entry = None
            current_data = {}
            
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.rstrip()  # Only strip right whitespace
                    
                    if not line or line.strip().startswith('#'):
                        continue
                        
                    # Entry header (no leading spaces, ends with colon)
                    if not line.startswith(' ') and line.endswith(':'):
                        if current_entry and current_data:
                            result[current_entry] = current_data
                        current_entry = line[:-1].strip()
                        current_data = {}
                    
                    # Field line (starts with spaces)
                    elif line.startswith('  ') and ':' in line:
                        try:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Handle quoted strings
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            
                            # Handle empty strings
                            if value == '""' or value == "''":
                                value = ""
                            
                            # Handle lists (simple format)
                            if value.startswith('[') and value.endswith(']'):
                                # Parse simple list: ["item1", "item2"]
                                list_content = value[1:-1].strip()  # Remove brackets
                                if list_content:
                                    items = []
                                    # Simple comma splitting (doesn't handle nested quotes perfectly)
                                    in_quotes = False
                                    current_item = ""
                                    quote_char = None
                                    
                                    for char in list_content:
                                        if char in ['"', "'"] and not in_quotes:
                                            in_quotes = True
                                            quote_char = char
                                        elif char == quote_char and in_quotes:
                                            in_quotes = False
                                            quote_char = None
                                        elif char == ',' and not in_quotes:
                                            item = current_item.strip()
                                            if item.startswith('"') and item.endswith('"'):
                                                item = item[1:-1]
                                            elif item.startswith("'") and item.endswith("'"):
                                                item = item[1:-1]
                                            if item:
                                                items.append(item)
                                            current_item = ""
                                            continue
                                        current_item += char
                                    
                                    # Add last item
                                    if current_item.strip():
                                        item = current_item.strip()
                                        if item.startswith('"') and item.endswith('"'):
                                            item = item[1:-1]
                                        elif item.startswith("'") and item.endswith("'"):
                                            item = item[1:-1]
                                        items.append(item)
                                    
                                    value = items
                                else:
                                    value = []
                            
                            current_data[key] = value
                        except ValueError:
                            # Skip malformed lines
                            continue
                        
                # Add last entry
                if current_entry and current_data:
                    result[current_entry] = current_data
                    
            return result
            
    except Exception as e:
        raise ValueError(f"Error parsing YAML file {filepath}: {str(e)}")
        
# (imports moved to top of file)

# ----------------------------------------------------------------
#  LOGGING AND DEBUG SYSTEM
# ----------------------------------------------------------------

logger = logging.getLogger(__name__)

def normalize_unicode(text: str) -> str:
    """Normalize text to NFC form for consistent comparison"""
    if not text:
        return ""
    return unicodedata.normalize('NFC', text.strip())

# ----------------------------------------------------------------
#  DATA STRUCTURES
# ----------------------------------------------------------------

@dataclass
class MathematicianEntry:
    """Complete information about a mathematician from language YAML files"""
    canonical_latin: str
    canonical_western: str = ""
    all_common_variants: List[str] = field(default_factory=list)
    mathscinet: str = ""
    native_script: str = ""  # CJK, Cyrillic, etc.
    suffixes: str = ""
    viaf: str = ""
    diaspora_flags: List[str] = field(default_factory=list)
    comments: str = ""
    source_file: str = ""
    
    def __post_init__(self):
        """Ensure all string fields are Unicode normalized"""
        self.canonical_latin = normalize_unicode(self.canonical_latin)
        self.canonical_western = normalize_unicode(self.canonical_western)
        self.all_common_variants = [normalize_unicode(v) for v in self.all_common_variants]
        self.mathscinet = normalize_unicode(self.mathscinet)
        self.native_script = normalize_unicode(self.native_script)
        self.suffixes = normalize_unicode(self.suffixes)
        self.comments = normalize_unicode(self.comments)

@dataclass
class ValidationResult:
    """Result of mathematician name validation"""
    is_valid: bool
    canonical_form: Optional[str] = None
    found_variant: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    ambiguity_warning: bool = False
    validation_notes: List[str] = field(default_factory=list)

@dataclass
class ValidationConfig:
    """Configuration for name validation behavior"""
    fuzzy_threshold: float = 0.85
    enable_diacritic_normalization: bool = True
    enable_script_transliteration: bool = True
    flag_ambiguous_names: bool = True
    max_suggestions: int = 5
    case_sensitive: bool = False

# ----------------------------------------------------------------
#  CORE VALIDATOR CLASS
# ----------------------------------------------------------------

class MathematicianNameValidator:
    """
    Ultra-robust mathematician name validation system supporting:
    - 8 language-specific YAML databases
    - Unicode normalization across scripts
    - Fuzzy matching with confidence scoring
    - Ambiguity detection and resolution
    - Performance-optimized lookups
    """
    
    LANGUAGE_FILES = [
        "chinese.yaml", "russian.yaml", "east european.yaml", 
        "french.yaml", "german.yaml", "hungarian.yaml", 
        "indian.yaml", "polish.yaml"
    ]
    
    def __init__(self, base_directory: Optional[Path] = None, config: Optional[ValidationConfig] = None):
        """
        Initialize the validator with language databases
        
        Args:
            base_directory: Directory containing YAML files (defaults to current dir)
            config: Validation configuration settings
        """
        self.base_directory = Path(base_directory) if base_directory else Path.cwd()
        self.config = config or ValidationConfig()
        
        # Core data structures
        self.mathematician_db: Dict[str, MathematicianEntry] = {}
        self.variant_index: Dict[str, str] = {}  # variant -> canonical_id
        self.canonical_index: Dict[str, str] = {}  # canonical_form -> canonical_id
        self.ambiguous_variants: Set[str] = set()
        self.high_collision_names: Set[str] = set()
        
        # Performance optimization
        self._fuzzy_cache: Dict[str, List[Tuple[str, float]]] = {}
        self._load_statistics = {
            'total_mathematicians': 0,
            'total_variants': 0,
            'files_loaded': 0,
            'errors': []
        }
        
        # Load all data
        self._load_all_language_files()
        self._build_indices()
        self._detect_ambiguities()
        
        logger.info(f"Loaded {self._load_statistics['total_mathematicians']} mathematicians "
                   f"with {self._load_statistics['total_variants']} variants from "
                   f"{self._load_statistics['files_loaded']} files")

    def _load_all_language_files(self) -> None:
        """Load and parse all language-specific YAML files"""
        for filename in self.LANGUAGE_FILES:
            # First try base directory, then try data/languages subdirectory
            filepath = self.base_directory / filename
            try:
                if not filepath.exists():
                    filepath = self.base_directory / "data" / "languages" / filename
            except (PermissionError, OSError) as e:
                # Handle permission errors gracefully
                error_msg = f"Permission denied accessing {filename}: {str(e)}"
                self._load_statistics['errors'].append(error_msg)
                logger.error(error_msg)
                continue
            
            try:
                self._load_language_file(filepath, filename)
                self._load_statistics['files_loaded'] += 1
            except Exception as e:
                error_msg = f"Failed to load {filename}: {str(e)}"
                self._load_statistics['errors'].append(error_msg)
                logger.error(error_msg)
                # Continue loading other files rather than failing completely

    def _load_language_file(self, filepath: Path, source_file: str) -> None:
        """Load a single language YAML file into the database"""
        if not filepath.exists():
            raise FileNotFoundError(f"Language file not found: {filepath}")
            
        try:
            # Use fallback YAML parser that works without PyYAML
            data = simple_yaml_load(filepath)
                
            if not isinstance(data, dict):
                raise ValueError(f"Invalid YAML structure in {source_file}")
                
            for entry_id, entry_data in data.items():
                if not isinstance(entry_data, dict):
                    logger.warning(f"Skipping invalid entry {entry_id} in {source_file}")
                    continue
                    
                mathematician = self._parse_mathematician_entry(entry_data, source_file)
                if mathematician:
                    # Use source_file + entry_id as unique key
                    unique_id = f"{source_file}:{entry_id}"
                    self.mathematician_db[unique_id] = mathematician
                    self._load_statistics['total_mathematicians'] += 1
                    
        except Exception as e:
            raise RuntimeError(f"Error loading {source_file}: {str(e)}")

    def _parse_mathematician_entry(self, data: Dict[str, Any], source_file: str) -> Optional[MathematicianEntry]:
        """Parse a single mathematician entry from YAML data"""
        try:
            # Handle different field names across language files
            canonical_latin = data.get('CanonicalLatin', '')
            if not canonical_latin:
                logger.warning(f"Missing CanonicalLatin in entry from {source_file}")
                return None
                
            canonical_western = data.get('CanonicalWestern', '')
            all_variants = data.get('AllCommonVariants', [])
            mathscinet = data.get('MathSciNet', '')
            
            # Handle language-specific script fields
            native_script = (data.get('CJK') or data.get('Cyrillic') or 
                           data.get('NativeScript', ''))
            
            suffixes = data.get('Suffixes', '')
            viaf = data.get('VIAF', '')
            diaspora_flags = data.get('DiasporaFlags', [])
            comments = data.get('Comments', '')
            
            # Ensure all_variants is a list
            if isinstance(all_variants, str):
                all_variants = [all_variants]
            elif not isinstance(all_variants, list):
                all_variants = []
                
            # Ensure diaspora_flags is a list  
            if isinstance(diaspora_flags, str):
                diaspora_flags = [diaspora_flags]
            elif not isinstance(diaspora_flags, list):
                diaspora_flags = []
            
            mathematician = MathematicianEntry(
                canonical_latin=canonical_latin,
                canonical_western=canonical_western,
                all_common_variants=all_variants,
                mathscinet=mathscinet,
                native_script=native_script,
                suffixes=suffixes,
                viaf=viaf,
                diaspora_flags=diaspora_flags,
                comments=comments,
                source_file=source_file
            )
            
            return mathematician
            
        except Exception as e:
            logger.error(f"Error parsing mathematician entry from {source_file}: {str(e)}")
            return None

    def _build_indices(self) -> None:
        """Build optimized lookup indices for fast name resolution"""
        for unique_id, mathematician in self.mathematician_db.items():
            # Index CANONICAL forms (correct spellings) - only the primary canonical
            canonical_normalized = self._normalize_for_lookup(mathematician.canonical_latin)
            if canonical_normalized:
                self.canonical_index[canonical_normalized] = unique_id
                
            # Also index canonical western if it exists AND is not listed as a variant
            if mathematician.canonical_western:
                western_normalized = self._normalize_for_lookup(mathematician.canonical_western)
                if (western_normalized and 
                    western_normalized != canonical_normalized and
                    mathematician.canonical_western not in mathematician.all_common_variants):
                    self.canonical_index[western_normalized] = unique_id
                
            # Index INCORRECT VARIANTS ONLY (not canonical forms)
            # These are the forms that should be flagged
            variant_forms = set(mathematician.all_common_variants)
            
            # Add MathSciNet entry as variant if it's different from canonical
            # AND if it's also listed in AllCommonVariants (meaning it's incorrect)
            if (mathematician.mathscinet and 
                mathematician.mathscinet != mathematician.canonical_latin and
                mathematician.mathscinet in mathematician.all_common_variants):
                variant_forms.add(mathematician.mathscinet)
                
            for variant in variant_forms:
                if not variant:
                    continue
                    
                normalized_variant = self._normalize_for_lookup(variant)
                if normalized_variant:
                    # Skip if this variant is the same as canonical form
                    if normalized_variant == canonical_normalized:
                        continue
                        
                    if normalized_variant in self.variant_index:
                        # Detect potential ambiguity
                        if self.variant_index[normalized_variant] != unique_id:
                            self.ambiguous_variants.add(normalized_variant)
                    else:
                        self.variant_index[normalized_variant] = unique_id
                        self._load_statistics['total_variants'] += 1

    def _normalize_for_lookup(self, name: str) -> str:
        """Normalize name for EXACT lookup (preserves diacritics!)"""
        if not name:
            return ""
            
        # Unicode normalization (NFC)
        normalized = normalize_unicode(name)
        
        # Optional case normalization only
        if not self.config.case_sensitive:
            normalized = normalized.lower()
            
        # DO NOT remove diacritics for exact lookup!
        # "Poincaré" and "Poincare" should be treated as different
        return normalized
        
    def _normalize_for_fuzzy_lookup(self, name: str) -> str:
        """Normalize name for FUZZY matching (removes diacritics)"""
        if not name:
            return ""
            
        # Start with exact normalization
        normalized = self._normalize_for_lookup(name)
        
        # Remove diacritics for fuzzy matching
        if self.config.enable_diacritic_normalization:
            normalized = self._remove_diacritics(normalized)
            
        return normalized

    def _remove_diacritics(self, text: str) -> str:
        """Remove diacritics for fuzzy matching while preserving structure"""
        if not text:
            return ""
        # NFD decomposition, then remove combining characters
        nfd = unicodedata.normalize('NFD', text)
        without_diacritics = ''.join(c for c in nfd 
                                   if unicodedata.category(c) != 'Mn')
        return unicodedata.normalize('NFC', without_diacritics)

    def _detect_ambiguities(self) -> None:
        """Detect high-collision names that need special handling"""
        # Count variant frequencies
        variant_counts = defaultdict(int)
        for variant in self.variant_index:
            # Extract just the surname/key part for collision detection
            if ',' in variant:
                surname = variant.split(',')[0].strip()
            else:
                parts = variant.split()
                surname = parts[-1] if parts else variant
            variant_counts[surname] += 1
            
        # Flag high-collision surnames
        for surname, count in variant_counts.items():
            if count > 5:  # Threshold for "high collision"
                self.high_collision_names.add(surname)
                
        logger.info(f"Detected {len(self.ambiguous_variants)} ambiguous variants "
                   f"and {len(self.high_collision_names)} high-collision names")

    @lru_cache(maxsize=1000)
    def validate_mathematician_name(self, name: str) -> ValidationResult:
        """
        Main validation function - flag INCORRECT variants and suggest canonical forms
        
        Purpose: Only flag names that are INCORRECT variants of known mathematicians.
        - Canonical forms (correct spellings) should NOT be flagged
        - Incorrect variants should be flagged with canonical suggestion
        - Unknown names should NOT be flagged (pass through)
        
        Args:
            name: Name to validate
            
        Returns:
            ValidationResult: is_valid=False only for incorrect variants
        """
        if not name or not name.strip():
            return ValidationResult(is_valid=True, validation_notes=["Empty name - no issue"])
            
        # Security: Limit input length to prevent DoS attacks
        if len(name) > 500:
            return ValidationResult(is_valid=True, validation_notes=["Input too long - treating as unknown"])
            
        name = name.strip()
        normalized_name = self._normalize_for_lookup(name)
        
        # 1. Check if this is a CANONICAL form (correct spelling) - do NOT flag
        if normalized_name in self.canonical_index:
            mathematician_id = self.canonical_index[normalized_name]
            mathematician = self.mathematician_db[mathematician_id]
            
            return ValidationResult(
                is_valid=True,  # Canonical forms are correct, don't flag
                canonical_form=mathematician.canonical_latin,
                found_variant=name,
                confidence_score=1.0,
                ambiguity_warning=False,
                validation_notes=["Canonical form - correct spelling"]
            )
            
        # 2. Check if this is an INCORRECT VARIANT - FLAG IT
        if normalized_name in self.variant_index:
            mathematician_id = self.variant_index[normalized_name]
            mathematician = self.mathematician_db[mathematician_id]
            
            # Check for ambiguity warning
            ambiguous = normalized_name in self.ambiguous_variants
            
            return ValidationResult(
                is_valid=False,  # This is an incorrect variant - flag it
                canonical_form=mathematician.canonical_latin,
                found_variant=name,
                suggestions=[mathematician.canonical_latin],
                confidence_score=1.0,
                ambiguity_warning=ambiguous,
                validation_notes=[f"Incorrect variant - should be '{mathematician.canonical_latin}'"]
            )
            
        # 3. Fuzzy matching for potential incorrect variants
        fuzzy_matches = self._find_fuzzy_matches(name)
        if fuzzy_matches:
            best_match, confidence = fuzzy_matches[0]
            
            # High confidence fuzzy match - likely an incorrect variant
            if confidence >= self.config.fuzzy_threshold:
                # Check if best match is a canonical or variant
                best_normalized = self._normalize_for_lookup(best_match)
                if best_normalized in self.canonical_index:
                    mathematician_id = self.canonical_index[best_normalized]
                elif best_normalized in self.variant_index:
                    mathematician_id = self.variant_index[best_normalized]
                else:
                    # No match found, pass through
                    return ValidationResult(is_valid=True, validation_notes=["Unknown name - no issue"])
                    
                mathematician = self.mathematician_db[mathematician_id]
                
                return ValidationResult(
                    is_valid=False,  # Likely incorrect spelling - flag it
                    canonical_form=mathematician.canonical_latin,
                    found_variant=best_match,
                    suggestions=[mathematician.canonical_latin],
                    confidence_score=confidence,
                    ambiguity_warning=False,
                    validation_notes=[f"Possible misspelling - consider '{mathematician.canonical_latin}' (confidence: {confidence:.2f})"]
                )
            
        # 4. No matches found - this is an unknown name, do NOT flag
        return ValidationResult(
            is_valid=True,  # Unknown names are not flagged
            validation_notes=["Unknown name - no issue"]
        )

    def _find_fuzzy_matches(self, name: str) -> List[Tuple[str, float]]:
        """Find fuzzy matches against canonical forms (to suggest corrections)"""
        if name in self._fuzzy_cache:
            return self._fuzzy_cache[name]
            
        # Use fuzzy normalization for similarity matching
        normalized_input = self._normalize_for_fuzzy_lookup(name)
        matches = []
        
        # Check against CANONICAL forms (to suggest correct spellings)
        for canonical in self.canonical_index:
            # Normalize canonical for fuzzy comparison
            canonical_fuzzy = self._normalize_for_fuzzy_lookup(self._find_original_canonical_form(canonical))
            
            # Use SequenceMatcher for edit distance
            similarity = SequenceMatcher(None, normalized_input, canonical_fuzzy).ratio()
            
            if similarity > 0.6:  # Minimum threshold
                # Find original canonical form for user display
                original_canonical = self._find_original_canonical_form(canonical)
                matches.append((original_canonical, similarity))
                
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Cache results
        self._fuzzy_cache[name] = matches[:10]  # Cache top 10 matches
        
        return matches[:self.config.max_suggestions]

    def _find_original_canonical_form(self, normalized_canonical: str) -> str:
        """Find the original canonical form from normalized lookup key"""
        if normalized_canonical in self.canonical_index:
            mathematician_id = self.canonical_index[normalized_canonical]
            mathematician = self.mathematician_db[mathematician_id]
            
            # Check canonical forms in order of preference
            canonical_forms = [
                mathematician.canonical_latin,
                mathematician.canonical_western,
                mathematician.mathscinet
            ]
            
            for canonical in canonical_forms:
                if canonical and self._normalize_for_lookup(canonical) == normalized_canonical:
                    return canonical
                    
        return normalized_canonical  # Fallback

    def _find_original_variant_form(self, normalized_variant: str) -> str:
        """Find the original variant form from normalized lookup key"""
        if normalized_variant in self.variant_index:
            mathematician_id = self.variant_index[normalized_variant]
            mathematician = self.mathematician_db[mathematician_id]
            
            # Try to find the best matching original variant form
            for variant in mathematician.all_common_variants:
                if variant and self._normalize_for_lookup(variant) == normalized_variant:
                    return variant
                    
        return normalized_variant  # Fallback

    def get_mathematician_info(self, name: str) -> Optional[MathematicianEntry]:
        """Get complete information about a mathematician"""
        validation_result = self.validate_mathematician_name(name)
        
        if validation_result.is_valid and validation_result.canonical_form:
            # Find the mathematician entry
            for mathematician in self.mathematician_db.values():
                if mathematician.canonical_latin == validation_result.canonical_form:
                    return mathematician
                    
        return None

    def suggest_corrections(self, incorrect_name: str, max_suggestions: int = 5) -> List[str]:
        """Provide spelling/variant corrections for incorrect names"""
        fuzzy_matches = self._find_fuzzy_matches(incorrect_name)
        return [match for match, confidence in fuzzy_matches[:max_suggestions]]

    def check_name_ambiguity(self, name: str) -> Dict[str, Any]:
        """Check if a name has ambiguity issues requiring disambiguation"""
        normalized = self._normalize_for_lookup(name)
        
        result = {
            'is_ambiguous': False,
            'ambiguity_type': None,
            'conflicting_entries': [],
            'disambiguation_needed': False
        }
        
        # Check for variant ambiguity
        if normalized in self.ambiguous_variants:
            result['is_ambiguous'] = True
            result['ambiguity_type'] = 'variant_collision'
            result['disambiguation_needed'] = True
            
        # Check for high-collision surname
        surname = normalized.split(',')[0].strip() if ',' in normalized else normalized.split()[-1]
        if surname in self.high_collision_names:
            result['is_ambiguous'] = True
            if not result['ambiguity_type']:
                result['ambiguity_type'] = 'high_collision_surname'
            result['disambiguation_needed'] = True
            
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the loaded database"""
        stats = self._load_statistics.copy()
        stats.update({
            'ambiguous_variants': len(self.ambiguous_variants),
            'high_collision_names': len(self.high_collision_names),
            'cache_hits': len(self._fuzzy_cache),
            'languages_covered': len(self.LANGUAGE_FILES),
            'files_successfully_loaded': stats['files_loaded'],
            'load_errors': stats['errors'],  # Keep the original list
            'num_load_errors': len(stats['errors'])  # Add count separately
        })
        return stats

    def export_problem_cases(self) -> Dict[str, List[str]]:
        """Export problematic cases for manual review"""
        return {
            'ambiguous_variants': list(self.ambiguous_variants),
            'high_collision_names': list(self.high_collision_names),
            'load_errors': self._load_statistics['errors']
        }

# ----------------------------------------------------------------
#  INTEGRATION UTILITIES
# ----------------------------------------------------------------

def integrate_with_filename_checker(filename_checker_instance, validator_instance: MathematicianNameValidator):
    """
    Integration function for filename_checker.py
    
    This adds mathematician name validation to the existing filename validation pipeline
    """
    # Store reference to validator
    filename_checker_instance.mathematician_validator = validator_instance
    
    # Add new validation method
    def validate_mathematician_names(self, title: str, debug: bool = False) -> List[Dict[str, Any]]:
        """Validate mathematician names found in title"""
        if not hasattr(self, 'mathematician_validator'):
            return []
            
        # Extract potential mathematician names from title
        # This is a simplified extraction - real implementation would be more sophisticated
        name_patterns = [
            r'\b([A-ZÜËÏÖÁÉÍÓÚÀÈÌÒÙ][a-züëïöáéíóúàèìòù]+(?:-[A-ZÜËÏÖÁÉÍÓÚÀÈÌÒÙ][a-züëïöáéíóúàèìòù]+)*)\b',
            r'\b([A-ZÜËÏÖÁÉÍÓÚÀÈÌÒÙ][a-züëïöáéíóúàèìòù]+)\s+([A-ZÜËÏÖÁÉÍÓÚÀÈÌÒÙ][a-züëïöáéíóúàèìòù]+)\b'
        ]
        
        issues = []
        for pattern in name_patterns:
            matches = re.finditer(pattern, title)
            for match in matches:
                name = match.group(0)
                result = self.mathematician_validator.validate_mathematician_name(name)
                
                if not result.is_valid and result.suggestions:
                    issues.append({
                        'type': 'mathematician_name_variant',
                        'found': name,
                        'position': match.span(),
                        'suggestions': result.suggestions,
                        'confidence': result.confidence_score,
                        'message': f"Possible incorrect mathematician name variant: '{name}'"
                    })
                elif result.ambiguity_warning:
                    issues.append({
                        'type': 'mathematician_name_ambiguous',
                        'found': name,
                        'position': match.span(),
                        'canonical': result.canonical_form,
                        'message': f"Ambiguous mathematician name: '{name}' - may need disambiguation"
                    })
                    
        return issues
    
    # Bind the method to the filename_checker instance
    import types
    filename_checker_instance.validate_mathematician_names = types.MethodType(
        validate_mathematician_names, filename_checker_instance
    )

# ----------------------------------------------------------------
#  MODULE INITIALIZATION
# ----------------------------------------------------------------

# Global validator instance for module-level usage
_global_validator: Optional[MathematicianNameValidator] = None

def get_global_validator(force_reload: bool = False) -> MathematicianNameValidator:
    """Get or create the global validator instance"""
    global _global_validator
    
    if _global_validator is None or force_reload:
        _global_validator = MathematicianNameValidator()
        
    return _global_validator

def validate_name(name: str) -> ValidationResult:
    """Convenience function for quick name validation"""
    validator = get_global_validator()
    return validator.validate_mathematician_name(name)

def __main__():
    """CLI entry point for testing"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python mathematician_name_validator.py <mathematician_name>")
        sys.exit(1)
        
    name = ' '.join(sys.argv[1:])
    result = validate_name(name)
    
    print(f"Name: {name}")
    print(f"Valid: {result.is_valid}")
    if result.canonical_form:
        print(f"Canonical: {result.canonical_form}")
    if result.suggestions:
        print(f"Suggestions: {', '.join(result.suggestions)}")
    if result.validation_notes:
        print(f"Notes: {', '.join(result.validation_notes)}")

if __name__ == "__main__":
    __main__()