#!/usr/bin/env python3
"""
Enhanced PDF Parser that uses ALL extraction methods:
1. Comprehensive Metadata Fetcher (ArXiv, Crossref, Google Scholar, Unpaywall)
2. ArXiv API (fallback for ArXiv papers)
3. GROBID (if available)
4. PyMuPDF + heuristics
5. LLM enhancement
Then picks the BEST result and ALWAYS applies formatting.
"""

import logging
import os
import re
import sys
import time
from pathlib import Path


logger = logging.getLogger(__name__)

from core.text_processing.normalizer import normalize
from pdf_processing.models import MetadataSource, PDFMetadata
from pdf_processing.parsers.base_parser import UltraEnhancedPDFParser as BaseParser
from validators.author_parser import AuthorParser
from validators.title_normalizer_enhanced import (
    fix_title_capitalization,
    normalize_title,
    process_title_completely,
)

# Import filename checker for proper integration
try:
    from validators.filename_checker import check_filename
    FILENAME_CHECKER_AVAILABLE = True
except ImportError:
    FILENAME_CHECKER_AVAILABLE = False

# Import additional utilities that were missing
try:
    from core.utils.text import extract_dois
    DOI_EXTRACTOR_AVAILABLE = True
except ImportError:
    DOI_EXTRACTOR_AVAILABLE = False

try:
    from validators.mathematician_name_validator import MathematicianNameValidator
    MATHEMATICIAN_VALIDATOR_AVAILABLE = True
except ImportError:
    MATHEMATICIAN_VALIDATOR_AVAILABLE = False

# Import the new advanced heuristics components
try:
    from .advanced_layout_analyzer import AdvancedLayoutAnalyzer
    LAYOUT_ANALYZER_AVAILABLE = True
except ImportError:
    LAYOUT_ANALYZER_AVAILABLE = False

try:
    from .statistical_pattern_matcher import StatisticalPatternMatcher
    PATTERN_MATCHER_AVAILABLE = True
except ImportError:
    PATTERN_MATCHER_AVAILABLE = False

try:
    from .math_notation_handler import MathNotationHandler
    MATH_HANDLER_AVAILABLE = True
except ImportError:
    MATH_HANDLER_AVAILABLE = False

# Import the comprehensive metadata fetcher system
try:
    from metadata_fetcher import (
        authors_match,
        canonicalize,
        extract_arxiv_info,
        fetch_metadata_all_sources,
        title_match,
    )
    METADATA_FETCHER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Metadata fetcher not available: {e}")
    METADATA_FETCHER_AVAILABLE = False


class EnhancedPDFParser(BaseParser):
    """Enhanced parser that tries ALL methods and picks the best result"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize advanced heuristics components
        self.layout_analyzer = AdvancedLayoutAnalyzer() if LAYOUT_ANALYZER_AVAILABLE else None
        self.pattern_matcher = StatisticalPatternMatcher() if PATTERN_MATCHER_AVAILABLE else None
        self.math_handler = MathNotationHandler() if MATH_HANDLER_AVAILABLE else None

        if self.layout_analyzer:
            logger.info("✅ Advanced layout analyzer initialized")
        if self.pattern_matcher:
            logger.info("✅ Statistical pattern matcher initialized")
        if self.math_handler:
            logger.info("✅ Mathematical notation handler initialized")

    def extract_metadata(self, pdf_path: str, **kwargs) -> PDFMetadata:
        """
        Extract metadata using ALL available methods.

        Args:
            pdf_path: Path to PDF file
            **kwargs: Additional options including use_llm

        Returns:
            PDFMetadata with best extraction result
        """
        start_time = time.time()
        pdf_file = Path(pdf_path)

        # Validate input
        self._validate_pdf_file(pdf_file)

        # Initialize results storage
        all_results = []

        # Extract raw text first (needed by all methods)
        text_results = self._multi_engine_extraction(pdf_file, **kwargs)
        best_text_result = max(text_results, key=lambda x: x.get('quality_score', 0))
        raw_text = best_text_result['text']
        text_blocks = best_text_result.get('blocks', [])

        # Method 1: Comprehensive Metadata Fetcher (if available)
        if METADATA_FETCHER_AVAILABLE:
            comprehensive_result = self._fetch_with_metadata_system(pdf_file, raw_text)
            if comprehensive_result:
                all_results.append(("metadata_fetcher", comprehensive_result))
                logger.info(f"🎯 Metadata fetcher extracted: '{comprehensive_result.title[:50]}...' | Authors: '{comprehensive_result.authors[:50] if comprehensive_result.authors else 'None'}...'")
            else:
                logger.info("🚫 Metadata fetcher returned no results")
        else:
            logger.info("❌ Metadata fetcher not available")
        # Method 2: ALWAYS TRY ArXiv API first (fallback if metadata fetcher not available)
        try:
            # Try filename first
            arxiv_id = self.arxiv_client.extract_arxiv_id_from_filename(pdf_file.name)
            if not arxiv_id:
                # CRITICAL: Use advanced vertical detection for ArXiv IDs
                # This handles "vertically from bottom to top on the left-hand side"
                arxiv_id = self.arxiv_client.extract_arxiv_id_from_pdf(pdf_path)
            if not arxiv_id:
                # Final fallback: extract from text content
                arxiv_id = self.arxiv_client.extract_arxiv_id_from_text(raw_text)

            if arxiv_id:
                logger.info(f"🎯 Found ArXiv ID: {arxiv_id}")
                arxiv_metadata = self.arxiv_client.search_by_id(arxiv_id)
                if arxiv_metadata:
                    # Extract authors properly from ArXiv API response
                    authors = []
                    if 'authors' in arxiv_metadata:
                        for author in arxiv_metadata['authors']:
                            if isinstance(author, dict):
                                first = author.get('first', '').strip()
                                last = author.get('last', '').strip()
                                if first and last:
                                    authors.append(f"{first} {last}")
                                elif last:
                                    authors.append(last)
                            elif isinstance(author, str):
                                authors.append(author.strip())

                    result = PDFMetadata(
                        path=str(pdf_file),
                        filename=pdf_file.name,
                        title=arxiv_metadata.get('title', '').strip(),
                        authors="; ".join(authors) if authors else "",
                        abstract=arxiv_metadata.get('abstract', '').strip(),
                        doi=arxiv_metadata.get('doi', ''),
                        arxiv_id=arxiv_id,
                        source=MetadataSource.API,
                        confidence=0.98,  # ArXiv API is gold standard
                        extraction_method="arxiv_api"
                    )
                    all_results.append(("arxiv_api", result))
                    logger.info(f"✅ ArXiv API extracted: '{result.title[:50]}...' | Authors: '{result.authors[:50]}...'")
                else:
                    logger.warning(f"ArXiv ID {arxiv_id} found but API returned no metadata")
            else:
                logger.debug("No ArXiv ID found in filename or text")
        except Exception as e:
            logger.warning(f"ArXiv extraction failed: {e}")

        # Method 3: Try GROBID (if available)
        try:
            from core.grobid_client import GrobidClient
            grobid = GrobidClient()

            if grobid.is_available():
                grobid_result = grobid.process_pdf(str(pdf_file))
                if grobid_result:
                    result = PDFMetadata(
                        path=str(pdf_file),
                        filename=pdf_file.name,
                        title=grobid_result.get('title', ''),
                        authors=grobid_result.get('authors', ''),
                        abstract=grobid_result.get('abstract', ''),
                        source=MetadataSource.API,
                        confidence=0.9,
                        extraction_method="grobid"
                    )
                    all_results.append(("grobid", result))
                    logger.info(f"🔬 GROBID extracted: '{result.title[:50]}...' | Authors: '{result.authors[:50] if result.authors else 'None'}...'")
        except Exception as e:
            logger.warning(f"GROBID extraction failed: {e}")

        # Method 4: Heuristic extraction (always run)
        heuristic_result = self._heuristic_extraction(pdf_file, raw_text, text_blocks)
        all_results.append(("heuristic", heuristic_result))
        logger.info(f"🧮 Heuristic extracted: '{heuristic_result.title[:50]}...' | Authors: '{heuristic_result.authors[:50] if heuristic_result.authors else 'None'}...'")

        # Method 5: LLM extraction (if requested)
        use_llm = kwargs.get('use_llm', False)
        if use_llm:
            try:
                auto_launch = kwargs.get('auto_launch_llm', False)
                llm_result = self._enhance_with_llm(raw_text, pdf_file.name,
                                                   PDFMetadata(path=str(pdf_file), filename=pdf_file.name),
                                                   auto_launch=auto_launch)
                if llm_result and llm_result.title:
                    all_results.append(("llm", llm_result))
                    logger.info(f"✅ LLM extracted: '{llm_result.title[:50]}...' | Authors: '{llm_result.authors[:50] if llm_result.authors else 'None'}...'")
                else:
                    logger.warning("❌ LLM extraction failed or returned empty title")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")

        # Select the best result
        best_result = self._select_best_result(all_results)

        # ALWAYS apply normalization
        best_result = self._apply_normalization(best_result)

        # Set processing time
        best_result.processing_time = time.time() - start_time

        # Cache result
        cache_key = f"{pdf_file.absolute()}:{pdf_file.stat().st_mtime}"
        self.metadata_cache[cache_key] = best_result

        return best_result

    def _heuristic_extraction(self, pdf_file: Path, raw_text: str, text_blocks: list) -> PDFMetadata:
        """Run traditional heuristic extraction with advanced layout analysis"""
        metadata = PDFMetadata(
            path=str(pdf_file),
            filename=pdf_file.name,
            source=MetadataSource.HEURISTIC,
            extraction_method="heuristic"
        )

        # Use advanced layout analyzer if available
        if self.layout_analyzer and text_blocks:
            try:
                # Convert text blocks to TextElements for layout analysis
                from .advanced_layout_analyzer import TextElement
                text_elements = []
                for i, block in enumerate(text_blocks):
                    if isinstance(block, dict) and 'text' in block:
                        bbox = block.get('bbox', [0, 0, 100, 20])
                        text_elements.append(TextElement(
                            text=block['text'],
                            bbox=tuple(bbox),
                            font_name=block.get('font_name', 'Unknown'),
                            font_size=block.get('font_size', 12.0),
                            font_flags=block.get('font_flags', 0),
                            color=block.get('color', 0),
                            page_number=block.get('page', 0),
                            line_number=i
                        ))

                if text_elements:
                    # Analyze layout with advanced analyzer
                    layout = self.layout_analyzer.analyze_layout(text_elements)

                    # Extract title from layout analysis
                    if layout.title_candidates and layout.confidence_score > 0.6:
                        title_text = " ".join([t.text for t in layout.title_candidates])
                        if self.math_handler:
                            title_text = self.math_handler.normalize_mathematical_text(title_text)
                        metadata.title = title_text
                        logger.debug(f"🎯 Advanced layout extracted title: {metadata.title[:50]}...")

                    # Extract authors from layout analysis
                    if layout.author_candidates:
                        authors = []
                        for author_elem in layout.author_candidates:
                            author_text = author_elem.text
                            if self.math_handler:
                                author_text = self.math_handler.normalize_mathematical_text(author_text)
                            authors.append(author_text)
                        metadata.authors = "; ".join(authors)
                        logger.debug(f"🎯 Advanced layout extracted authors: {metadata.authors[:50]}...")

                    # Update confidence based on layout analysis
                    metadata.confidence = max(metadata.confidence, layout.confidence_score)
                else:
                    # Fallback to traditional extraction
                    metadata.title = self._extract_title_multi_method(text_blocks, raw_text)
                    authors_list = self._extract_authors_multi_method(text_blocks, raw_text)
                    metadata.authors = "; ".join(authors_list) if authors_list else ""

            except Exception as e:
                logger.warning(f"Advanced layout analysis failed: {e}, falling back to traditional extraction")
                # Fallback to traditional extraction
                metadata.title = self._extract_title_multi_method(text_blocks, raw_text)
                authors_list = self._extract_authors_multi_method(text_blocks, raw_text)
                metadata.authors = "; ".join(authors_list) if authors_list else ""
        else:
            # Traditional extraction
            metadata.title = self._extract_title_multi_method(text_blocks, raw_text)
            authors_list = self._extract_authors_multi_method(text_blocks, raw_text)
            metadata.authors = "; ".join(authors_list) if authors_list else ""

        # Extract DOI if available
        if DOI_EXTRACTOR_AVAILABLE:
            dois = extract_dois(raw_text)
            if dois:
                metadata.doi = dois[0]
                logger.debug(f"🔬 Heuristic extracted DOI: {metadata.doi}")

        # Extract abstract (from base parser)
        if hasattr(self, '_extract_abstract'):
            metadata.abstract = self._extract_abstract(text_blocks, raw_text)

        # Use pattern matcher to learn from this extraction (if available)
        if self.pattern_matcher and metadata.title:
            try:
                # Extract features from the title
                title_block = next((b for b in text_blocks if metadata.title in str(b.get('text', ''))), None)
                if title_block:
                    self.pattern_matcher.learn_from_extraction(
                        text=metadata.title,
                        font_size=title_block.get('font_size', 12.0),
                        position=title_block.get('bbox', [0, 0, 0, 0])[1] / 800,  # Normalize position
                        is_bold=bool(title_block.get('font_flags', 0) & 16),
                        is_italic=bool(title_block.get('font_flags', 0) & 2),
                        actual_type='title',
                        publisher='Unknown',
                        document_id=pdf_file.stem,
                        success=True
                    )
            except Exception as e:
                logger.debug(f"Pattern learning failed: {e}")

        # Calculate confidence
        metadata.confidence = self._calculate_confidence_score(metadata)

        return metadata

    def _enhance_with_llm(self, raw_text, filename, base_metadata, auto_launch=False):
        """Extract metadata using a local LLM with GBNF grammar constraints.

        Uses ``LLMMetadataExtractor`` (llama-cpp-python + Qwen2.5) for
        grammar-constrained JSON extraction.  Falls back gracefully when
        llama-cpp-python is not installed.
        """
        try:
            from pdf_processing.llm_extractor import LLMMetadataExtractor

            if not LLMMetadataExtractor.is_available():
                logger.info("llama-cpp-python not installed — skipping LLM extraction")
                return None

            # Lazy-init singleton (expensive: loads the GGUF model)
            if not hasattr(self, '_llm_extractor') or self._llm_extractor is None:
                self._llm_extractor = LLMMetadataExtractor()

            # Extract first ~3 pages of text
            text_snippet = raw_text[:8000]
            result = self._llm_extractor.extract(text_snippet)

            if not result or not result.get("title"):
                logger.warning("LLM returned empty title")
                return None

            return PDFMetadata(
                path=base_metadata.path if base_metadata else "",
                filename=filename,
                title=result["title"],
                authors="; ".join(result.get("authors", [])),
                source=MetadataSource.HEURISTIC,
                confidence=0.80,
                extraction_method="llm",
            )

        except ImportError:
            logger.debug("LLM extractor module not available")
            return None
        except Exception as e:
            logger.warning(f"LLM extraction error: {e}")
            return None

    def _fetch_with_metadata_system(self, pdf_file: Path, raw_text: str) -> PDFMetadata | None:
        """Use the comprehensive metadata fetcher system to get high-quality metadata"""
        if not METADATA_FETCHER_AVAILABLE:
            return None

        try:
            # First try to extract ArXiv ID for targeted lookup
            arxiv_id = None
            doi = None

            # Extract DOI if available
            if DOI_EXTRACTOR_AVAILABLE:
                dois = extract_dois(raw_text)
                if dois:
                    doi = dois[0]  # Use the first DOI found
                    logger.debug(f"🔬 Extracted DOI: {doi}")

            # Try to extract ArXiv ID using advanced methods
            if hasattr(self, 'arxiv_client'):
                arxiv_id = self.arxiv_client.extract_arxiv_id_from_filename(pdf_file.name)
                if not arxiv_id:
                    # Use vertical detection for perfect ArXiv ID detection
                    arxiv_id = self.arxiv_client.extract_arxiv_id_from_pdf(str(pdf_file))
                if not arxiv_id:
                    # Final fallback: text extraction
                    arxiv_id = self.arxiv_client.extract_arxiv_id_from_text(raw_text)

            # Try to extract a reasonable query title from the PDF text
            # Use heuristics to find the actual paper title, not journal headers
            lines = raw_text.split('\n')[:30]  # First 30 lines
            query_title = ""

            # Journal header patterns to avoid
            journal_patterns = [
                r'.*\bjournal\b.*',
                r'.*\bsiam\b.*',
                r'.*\belsevier\b.*',
                r'.*\bspringer\b.*',
                r'.*\bieee\b.*',
                r'.*\bacm\b.*',
                r'.*\bcomput\b.*',
                r'.*\bmath\b.*\bcomput\b.*',
                r'.*\bappl\b.*\bmath\b.*',
                r'.*\bannals\b.*',
                r'.*\bproc\b.*',
                r'.*\btrans\b.*',
                r'.*\blett\b.*',
                r'.*\breview\b.*',
                r'.*\bscience\b.*direct.*',
                r'.*contents\s+lists?\s+available.*',
                r'.*\bcommunicated\s+by\b.*',
                r'.*manuscript\s+(received|accepted).*',
                r'^\d+\s*$',  # Just numbers
                r'^[A-Z\s\.\,]{20,}$',  # All caps (likely journal header)
                r'\\mathrm\{[A-Z]\}.*',  # LaTeX mathrm patterns (journal headers)
                r'.*\\mathrm.*',  # Any LaTeX mathrm usage (likely journal headers)
            ]

            for line in lines:
                line = line.strip()
                if (len(line) > 15 and len(line) < 200 and
                    not line.lower().startswith(('http', 'www', 'doi:', 'abstract', 'introduction', 'keywords', 'author', 'email', 'received', 'accepted')) and
                    not re.match(r'^[\d\s\.\-]+$', line)):  # Not just numbers/punctuation

                    # Check if this line matches journal header patterns
                    is_journal_header = False
                    line_lower = line.lower()
                    for pattern in journal_patterns:
                        if re.match(pattern, line_lower):
                            is_journal_header = True
                            break

                    if not is_journal_header:
                        # This looks like a real title
                        query_title = line
                        break

            # If no good title found, use filename as fallback
            if not query_title:
                query_title = pdf_file.stem.replace('_', ' ').replace('-', ' ')

            logger.debug(f"🔍 Metadata fetcher query: title='{query_title[:50]}...' arxiv_id={arxiv_id} doi={doi}")

            # Use the comprehensive metadata fetcher
            metadata_results = fetch_metadata_all_sources(
                query=query_title,
                arxiv_id=arxiv_id,
                doi=doi,
                verbose=False
            )

            if not metadata_results:
                logger.debug("No metadata results from comprehensive fetcher")
                return None

            # Use the first (best) result
            best_metadata = metadata_results[0]

            # Convert to our PDFMetadata format
            authors_list = best_metadata.get('authors', [])
            if isinstance(authors_list, str):
                authors_str = authors_list
            elif isinstance(authors_list, list):
                authors_str = "; ".join(str(a) for a in authors_list if a)
            else:
                authors_str = ""

            result = PDFMetadata(
                path=str(pdf_file),
                filename=pdf_file.name,
                title=best_metadata.get('title', '').strip(),
                authors=authors_str,
                abstract=best_metadata.get('abstract', ''),
                doi=best_metadata.get('DOI', ''),
                arxiv_id=best_metadata.get('arxiv_id', ''),
                source=MetadataSource.API,
                confidence=0.95,  # High confidence in comprehensive system
                extraction_method="metadata_fetcher"
            )

            # Add extra metadata if available
            if hasattr(result, 'extra_metadata'):
                result.extra_metadata = {
                    'source_provider': best_metadata.get('source', ''),
                    'is_open_access': best_metadata.get('is_open_access', False),
                    'mathematical_subjects': best_metadata.get('mathematical_subjects', []),
                    'has_arxiv_updates': best_metadata.get('has_arxiv_updates', False),
                }

            return result

        except Exception as e:
            logger.warning(f"Comprehensive metadata fetcher failed: {e}")
            return None

    def _is_garbage_extraction(self, metadata: PDFMetadata, method: str) -> bool:
        """Detect garbage extractions from any method."""
        import re

        if not metadata.title:
            return True

        title_lower = metadata.title.lower().strip()
        authors_lower = metadata.authors.lower() if metadata.authors else ""

        # --- LLM-specific garbage patterns ---
        llm_garbage_patterns = [
            'extract the title',
            'extract title and authors',
            'from this academic paper',
            'from the academic paper',
            'please extract',
            'identify the title',
            'paper title:',
            'authors:',
            'unknown paper',
            'example paper',
            'academic paper',
            'research paper',
            '<pdf text>',
            '<|im_start|>',
            '<|im_end|>',
            'metadata extraction',
            'return a json',
            'json object',
            'here is the',
            'i found the following',
            'the title of this paper',
            'based on the text',
        ]

        if method == "llm":
            for pattern in llm_garbage_patterns:
                if pattern in title_lower:
                    logger.warning(f"🚫 LLM garbage detected in title: '{metadata.title}'")
                    return True

        # --- Generic garbage patterns (title starts with) ---
        bad_title_starts = [
            'contents lists available',
            'sciencedirect',
            'springer',
            'elsevier',
            'ieee',
            'acm digital library',
            'communicated by',
            'published by',
            'available online',
            'accepted manuscript',
            'copyright',
            'doi:',
            'doi 10.',
            'vol.',
            'volume ',
        ]

        for bad in bad_title_starts:
            if title_lower.startswith(bad):
                logger.warning(f"🚫 Generic garbage detected: '{metadata.title}'")
                return True

        # --- Journal/venue header as title ---
        journal_header_re = re.compile(
            r'^(?:annals|journal|transactions|proceedings|bulletin|letters|reviews?)'
            r'\s+(?:of|in|on)\s+',
            re.IGNORECASE,
        )
        if journal_header_re.match(title_lower):
            logger.warning(f"🚫 Journal header as title: '{metadata.title}'")
            return True

        # Specific venue patterns
        venue_patterns = [
            r'^(?:siam|ams|ieee|acm)\s+(?:j\.|journal|review|trans)',
            r'^(?:inventiones|mathematische|communications?\s+in|advances?\s+in)\s+math',
            r'^\d{4}\s+mathematics\s+subject\s+classification',
            r'^(?:received|accepted|revised)\s+\d',
        ]
        for pat in venue_patterns:
            if re.match(pat, title_lower):
                logger.warning(f"🚫 Venue/header pattern as title: '{metadata.title}'")
                return True

        # --- OCR artifact detection ---
        if len(metadata.title) > 10:
            alpha_count = sum(1 for c in metadata.title if c.isalpha())
            alpha_ratio = alpha_count / len(metadata.title)
            if alpha_ratio < 0.5:
                logger.warning(
                    f"🚫 OCR artifacts detected (alpha ratio {alpha_ratio:.2f}): "
                    f"'{metadata.title[:60]}'"
                )
                return True

        # --- Title-author overlap (title IS the author string) ---
        if metadata.authors and metadata.authors != "Unknown":
            authors_normalized = authors_lower.strip()
            if (len(authors_normalized) > 5 and
                    title_lower == authors_normalized):
                logger.warning(f"🚫 Title equals authors: '{metadata.title}'")
                return True

        # --- Truncated titles (ends with connective words) ---
        if metadata.title and len(metadata.title) > 15:
            title_stripped = metadata.title.rstrip()
            last_word = title_stripped.split()[-1].lower() if title_stripped.split() else ""
            # Only flag single-char or connective endings (not real words)
            truncation_words = {'and', 'the', 'of', 'in', 'for', 'with', 'a', 'an', 'by', 'on', 'to'}
            if last_word in truncation_words and not title_stripped.endswith(('.', '?', '!')):
                logger.debug(f"Possible truncated title: '{metadata.title}'")
                # Don't reject outright — just flag via debug. Many real titles
                # end with "of" etc. (e.g. "A new proof of"). The scoring already
                # penalises these (lines 662-663).

        # --- Suspiciously short or long titles ---
        if len(metadata.title) < 8 or len(metadata.title) > 300:
            logger.warning(f"🚫 Suspicious title length: {len(metadata.title)} chars")
            return True

        # --- Garbage authors ---
        bad_authors = [
            'the author', 'unknown', 'extract', 'paper', 'springer',
            'elsevier', 'ieee', 'microsoft', 'admin', 'user',
        ]
        for bad in bad_authors:
            if authors_lower.strip() == bad:
                logger.warning(f"🚫 Garbage authors detected: '{metadata.authors}'")
                metadata.authors = "Unknown"

        return False

    def _compute_consensus_bonus(self, scored_results: list) -> list:
        """Add consensus bonus when multiple methods agree on the same title.

        Uses rapidfuzz for fuzzy matching (threshold: 85% similarity).
        Each agreeing method adds +30 points to the agreed-upon results.
        """
        from rapidfuzz import fuzz

        n = len(scored_results)
        if n < 2:
            return scored_results

        titles = [
            r[2].title.lower().strip() if r[2].title else ""
            for r in scored_results
        ]
        agreement_counts = [0] * n

        for i in range(n):
            if not titles[i]:
                continue
            for j in range(i + 1, n):
                if not titles[j]:
                    continue
                similarity = fuzz.ratio(titles[i], titles[j])
                if similarity >= 85:
                    agreement_counts[i] += 1
                    agreement_counts[j] += 1

        adjusted = []
        for idx, (score, method, metadata) in enumerate(scored_results):
            if agreement_counts[idx] >= 1:
                consensus_bonus = 30 * agreement_counts[idx]
                logger.info(
                    f"Consensus bonus +{consensus_bonus} for {method}: "
                    f"{agreement_counts[idx]} other method(s) agree on "
                    f"'{metadata.title[:40]}...'"
                )
                score += consensus_bonus
            adjusted.append((score, method, metadata))

        return adjusted

    def _calibrate_confidence(self, metadata: PDFMetadata, method: str) -> float:
        """Recalibrate confidence based on actual extraction quality.

        Methods assign confidence before validation (e.g. ArXiv always 0.98).
        This adjusts the score based on what was actually extracted.
        """
        base = metadata.confidence
        penalties = 0.0

        # Empty or very short title
        if not metadata.title or len(metadata.title.strip()) < 10:
            penalties += 0.3

        # Title looks truncated
        if metadata.title and metadata.title.rstrip().endswith('...'):
            penalties += 0.15

        # No authors
        if not metadata.authors or metadata.authors == "Unknown":
            penalties += 0.2

        # Single-character / tiny authors (parsing error)
        if metadata.authors and len(metadata.authors.strip()) < 3:
            penalties += 0.15

        # Bonuses for strong external signals
        bonus = 0.0
        if metadata.doi:
            bonus += 0.05
        if metadata.abstract and len(metadata.abstract) > 100:
            bonus += 0.05

        calibrated = max(0.0, min(1.0, base - penalties + bonus))

        if abs(calibrated - base) > 0.01:
            logger.debug(
                f"Confidence calibrated for {method}: "
                f"{base:.2f} -> {calibrated:.2f} "
                f"(penalties={penalties:.2f}, bonus={bonus:.2f})"
            )

        return calibrated

    def _select_best_result(self, results: list[tuple]) -> PDFMetadata:
        """Select the best result from all extraction methods with garbage detection"""
        if not results:
            raise ValueError("No extraction results available")

        # First pass: filter out garbage results
        valid_results = []

        for method, metadata in results:
            if not self._is_garbage_extraction(metadata, method):
                valid_results.append((method, metadata))
            else:
                logger.warning(f"🚫 Filtering out garbage result from {method}")

        # If all results are garbage, fall back to heuristic
        if not valid_results:
            logger.warning("⚠️  All results were garbage, using fallback")
            # Find heuristic result as fallback
            for method, metadata in results:
                if method == "heuristic":
                    valid_results = [(method, metadata)]
                    break

        if not valid_results:
            raise ValueError("No valid extraction results available")

        # Score the valid results
        scored_results = []

        for method, metadata in valid_results:
            score = 0

            # CORRECTED scoring - Prioritize comprehensive systems
            method_scores = {
                "metadata_fetcher": 110,  # Comprehensive multi-source system with caching
                "arxiv_api": 100,         # ArXiv API is gold standard for ArXiv papers
                "llm": 90,                # LLM is trained to distinguish journal headers from titles
                "grobid": 80,             # GROBID is good but can produce garbage
                "heuristic": 60,          # Heuristics are basic fallback
            }
            score += method_scores.get(method, 50)

            # Title quality (up to 40 points)
            if metadata.title and metadata.title != "Unknown":
                title_len = len(metadata.title)
                # Reward good title length
                if 15 <= title_len <= 200:
                    score += 25
                elif 10 <= title_len <= 300:
                    score += 15

                # Reward complete-looking titles
                if title_len > 30 and not metadata.title.lower().endswith(('and', 'or', 'with', 'for', 'under')):
                    score += 15

                # Penalize truncated or incomplete titles
                if metadata.title.endswith('...') or title_len < 10:
                    score -= 25
                if any(metadata.title.lower().endswith(word) for word in ['and', 'with', 'for', 'under', 'of']):
                    score -= 15

            # Author quality (up to 25 points)
            if metadata.authors and metadata.authors != "Unknown":
                authors_len = len(metadata.authors)
                if authors_len > 5:
                    score += 15

                # Check for multiple authors
                if ';' in metadata.authors or ',' in metadata.authors:
                    score += 10

                # Penalize single letter or obvious garbage
                if authors_len < 3 or any(bad in metadata.authors.lower() for bad in ['unknown', 'author']):
                    score -= 10

            # Abstract bonus (15 points)
            if metadata.abstract and len(metadata.abstract) > 100:
                score += 15

            # Confidence bonus (up to 20 points) — calibrated by actual quality
            calibrated_conf = self._calibrate_confidence(metadata, method)
            score += calibrated_conf * 20

            # METHOD-SPECIFIC ADJUSTMENTS
            if method == "llm":
                # Extra validation for LLM results
                if (metadata.title and len(metadata.title) > 20 and
                    metadata.authors and metadata.authors != "Unknown"):
                    score += 10  # Bonus for complete LLM extraction
                else:
                    score -= 15  # Penalty for incomplete LLM extraction

            # AUTHOR VALIDATION - Penalize likely parsing errors
            if metadata.authors:
                # Count actual authors (by semicolons/commas)
                if ';' in metadata.authors:
                    actual_author_count = len([a.strip() for a in metadata.authors.split(';') if a.strip()])
                elif ' and ' in metadata.authors.lower():
                    actual_author_count = len([a.strip() for a in metadata.authors.split(' and ') if a.strip()])
                else:
                    actual_author_count = 1

                # Heavy penalty for excessive author counts (likely parsing errors)
                if actual_author_count > 10:
                    score -= 100  # Severe penalty - this is almost certainly wrong
                    logger.debug(f"Excessive authors penalty: -{100} for {actual_author_count} authors in {method}")
                elif actual_author_count > 5:
                    score -= 20  # Moderate penalty for very high counts
                    logger.debug(f"High author count penalty: -{20} for {actual_author_count} authors in {method}")

            # DIACRITIC PRESERVATION BONUS (capped to avoid inflating scores)
            if metadata.authors:
                import unicodedata
                has_diacritics = any(
                    unicodedata.combining(char) or ord(char) > 127
                    for char in metadata.authors
                    if char.isalpha()
                )
                if has_diacritics:
                    score += 20  # Fixed bonus — enough to break ties, not override methods
                    logger.debug(f"Diacritic bonus: +20 for preserving diacritics in {method}")

            scored_results.append((score, method, metadata))
            logger.debug(f"{method} score: {score:.1f} for '{metadata.title[:30]}...'")

        # Apply cross-method consensus bonus
        scored_results = self._compute_consensus_bonus(scored_results)

        # Return the best scoring result
        best_score, best_method, best_metadata = max(scored_results, key=lambda x: x[0])
        logger.info(f"✅ Selected {best_method} result with score {best_score:.1f}")

        return best_metadata

    def _apply_normalization(self, metadata: PDFMetadata) -> PDFMetadata:
        """Apply normalization with safety rollback.

        Checkpoints the original values and reverts if normalization
        produces garbage or empty results.
        """
        # Checkpoint originals
        original_title = metadata.title
        original_authors = metadata.authors

        # Normalize title
        if metadata.title:
            try:
                if self.math_handler:
                    metadata.title = self.math_handler.normalize_mathematical_text(metadata.title)

                metadata.title = normalize(metadata.title)
                metadata.title = normalize_title(metadata.title)
                metadata.title = fix_title_capitalization(metadata.title)

                # Validate: normalization must not destroy the title
                if (not metadata.title or
                        len(metadata.title.strip()) < 5 or
                        metadata.title.strip().lower() in ('unknown', 'untitled', '')):
                    logger.warning(
                        f"Normalization destroyed title, rolling back: "
                        f"'{metadata.title}' -> '{original_title}'"
                    )
                    metadata.title = original_title
            except Exception as e:
                logger.warning(f"Title normalization failed, keeping original: {e}")
                metadata.title = original_title

        # Normalize authors
        if metadata.authors:
            try:
                parser = AuthorParser()
                metadata.authors = normalize(metadata.authors)
                metadata.authors = parser.normalize_author_string(metadata.authors)
                metadata.authors = parser.fix_initial_spacing(metadata.authors)
                metadata.authors = parser.fix_author_suffixes(metadata.authors)

                # Validate: must still have content
                if not metadata.authors or len(metadata.authors.strip()) < 2:
                    logger.warning(
                        f"Normalization destroyed authors, rolling back: "
                        f"'{metadata.authors}' -> '{original_authors}'"
                    )
                    metadata.authors = original_authors

                # Apply mathematician name validation if available
                if MATHEMATICIAN_VALIDATOR_AVAILABLE:
                    try:
                        validator = MathematicianNameValidator()
                        author_list = [a.strip() for a in metadata.authors.split(';') if a.strip()]
                        validated_authors = []

                        for author in author_list:
                            validation_result = validator.validate_name(author)
                            if validation_result.is_valid and validation_result.standardized_form:
                                validated_authors.append(validation_result.standardized_form)
                            else:
                                validated_authors.append(author)

                        if validated_authors:
                            metadata.authors = "; ".join(validated_authors)
                            logger.debug("🎓 Mathematician name validation applied")
                    except Exception as e:
                        logger.debug(f"Mathematician name validation failed: {e}")

            except Exception as e:
                logger.warning(f"Author normalization failed, keeping original: {e}")
                metadata.authors = original_authors

        return metadata

    def _generate_filename_from_metadata(self, metadata: PDFMetadata) -> str:
        """Generate filename from metadata.

        .. deprecated::
            This method produces filenames that do not match the library
            convention (only uses first author, truncates title at 80 chars).
            Use :meth:`CMO.get_canonical_filename` from
            ``arxivbot.models.cmo`` instead for proper filename generation.

        This is kept as a minimal fallback for cases where CMO is not
        available.  It produces ``FirstAuthor - Title.pdf`` which is
        better than nothing but should be corrected by the ingest pipeline.
        """
        import warnings
        warnings.warn(
            "_generate_filename_from_metadata() produces non-standard filenames. "
            "Use CMO.get_canonical_filename() for library-standard filenames.",
            DeprecationWarning,
            stacklevel=2,
        )

        if not metadata.title or metadata.title == "Unknown":
            return None

        # Extract first author for filename (minimal fallback)
        first_author = "Unknown Author"
        if metadata.authors and metadata.authors != "Unknown":
            authors = metadata.authors.replace(';', ',').split(',')
            if authors:
                first_author = authors[0].strip()
                # Remove academic titles
                for prefix in ('Dr. ', 'Prof. ', 'Professor '):
                    if first_author.startswith(prefix):
                        first_author = first_author[len(prefix):]

        title = metadata.title
        filename = f"{first_author} - {title}.pdf"

        # Remove only filesystem-unsafe characters
        for char in ('/', '\\', '\0'):
            filename = filename.replace(char, '–')
        filename = filename.replace(':', ' –')

        # Clean up multiple spaces
        filename = ' '.join(filename.split())

        # UTF-8 byte limit (250 + .pdf)
        encoded = filename.encode('utf-8')
        if len(encoded) > 254:
            filename = encoded[:250].decode('utf-8', 'ignore').rstrip() + '.pdf'

        return filename

    def validate_and_rename_file(self, pdf_path: str, metadata: PDFMetadata) -> str | None:
        """
        Use filename_checker with PROPER configuration to validate and format filenames

        Args:
            pdf_path: Path to the PDF file
            metadata: Extracted metadata (used as fallback if filename_checker fails)

        Returns:
            New filename if renamed, None if no rename needed or failed
        """
        if not FILENAME_CHECKER_AVAILABLE:
            logger.warning("Filename checker not available - using fallback method")
            return self._fallback_rename_method(pdf_path, metadata)

        pdf_file = Path(pdf_path)
        current_filename = pdf_file.name

        try:
            # Load the user's complete configuration for filename_checker
            config_data = self._load_filename_checker_config()

            # Use filename_checker with PROPER configuration
            result = check_filename(
                current_filename,
                known_words=config_data.get('known_words', set()),
                whitelist_pairs=list(config_data.get('multiword_surnames', set())),
                exceptions=config_data.get('exceptions', set()),
                compound_terms=config_data.get('compound_terms', set()),
                capitalization_whitelist=config_data.get('capitalization_whitelist', set()),
                name_dash_whitelist=config_data.get('name_dash_whitelist', set()),
                auto_fix_nfc=True,
                auto_fix_authors=True,
                sentence_case=True
            )

            # Check if filename_checker provided a corrected filename
            if result.corrected_filename and result.corrected_filename != current_filename:
                final_filename = result.corrected_filename

                # Handle duplicate filenames
                new_path = pdf_file.parent / final_filename
                counter = 1
                original_new_path = new_path
                while new_path.exists() and new_path != pdf_file:
                    stem = original_new_path.stem
                    suffix = original_new_path.suffix
                    new_path = original_new_path.parent / f"{stem} ({counter}){suffix}"
                    counter += 1

                # Perform the rename
                try:
                    pdf_file.rename(new_path)
                    logger.info(f"✅ Successfully renamed: {current_filename} → {new_path.name}")
                    return new_path.name
                except Exception as e:
                    logger.error(f"❌ Rename failed for {current_filename}: {e}")
                    return None
            else:
                logger.info(f"✅ Filename already correct: {current_filename}")
                return None

        except Exception as e:
            logger.error(f"❌ Filename validation failed for {current_filename}: {e}")
            # Fall back to metadata-based renaming
            return self._fallback_rename_method(pdf_path, metadata)

    def _load_filename_checker_config(self) -> dict:
        """Load the user's complete configuration for filename_checker"""
        config = {
            'known_words': set(),
            'multiword_surnames': set(),
            'exceptions': set(),
            'compound_terms': set(),
            'capitalization_whitelist': set(),
            'name_dash_whitelist': set()
        }

        try:
            # Try to load the user's configuration using their config system
            from core.config.config_loader import ConfigurationData

            config_data = ConfigurationData()
            script_dir = Path(__file__).parent.parent.parent  # Go up to Scripts directory
            config_data.load_all(None, script_dir)

            config['known_words'] = config_data.known_words
            config['multiword_surnames'] = config_data.multiword_surnames
            config['exceptions'] = config_data.exceptions
            config['compound_terms'] = config_data.compound_terms
            config['capitalization_whitelist'] = config_data.capitalization_whitelist
            config['name_dash_whitelist'] = config_data.name_dash_whitelist

            logger.info(f"✅ Loaded filename_checker config: {len(config['known_words'])} known words, {len(config['exceptions'])} exceptions")

        except Exception as e:
            logger.warning(f"⚠️  Could not load user config, using defaults: {e}")
            # Use some basic defaults that match the user's preferences
            config['known_words'] = {
                'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from',
                'in', 'into', 'nor', 'of', 'on', 'or', 'the', 'to', 'with',
                'via', 'per', 'sub', 'non', 'pre', 'post', 'anti', 'over'
            }
            config['exceptions'] = {
                'LaTeX', 'TeX', 'MATLAB', 'NumPy', 'SciPy', 'PyTorch',
                'PDE', 'ODE', 'SDE', 'BSDE', 'FBSDE', 'McKean-Vlasov'
            }

        return config

    def _fallback_rename_method(self, pdf_path: str, metadata: PDFMetadata) -> str | None:
        """Fallback method when filename_checker fails"""
        pdf_file = Path(pdf_path)
        current_filename = pdf_file.name

        # Apply complete formatting to metadata
        formatted_metadata = self._apply_complete_user_formatting(metadata)

        # Generate proposed filename from formatted metadata
        proposed_filename = self._generate_filename_from_metadata(formatted_metadata)
        if not proposed_filename:
            logger.warning(f"Could not generate filename from metadata for {current_filename}")
            return None

        # Check if rename is needed
        if proposed_filename == current_filename:
            return None

        # Handle duplicate filenames and rename
        new_path = pdf_file.parent / proposed_filename
        counter = 1
        original_new_path = new_path
        while new_path.exists() and new_path != pdf_file:
            stem = original_new_path.stem
            suffix = original_new_path.suffix
            new_path = original_new_path.parent / f"{stem} ({counter}){suffix}"
            counter += 1

        try:
            pdf_file.rename(new_path)
            logger.info(f"✅ Successfully renamed (fallback): {current_filename} → {new_path.name}")
            return new_path.name
        except Exception as e:
            logger.error(f"❌ Fallback rename failed for {current_filename}: {e}")
            return None

    def _apply_complete_user_formatting(self, metadata: PDFMetadata) -> PDFMetadata:
        """Apply the user's COMPLETE formatting pipeline to title and authors"""

        # Create a copy to avoid modifying original
        formatted = PDFMetadata(
            path=metadata.path,
            filename=metadata.filename,
            title=metadata.title,
            authors=metadata.authors,
            abstract=metadata.abstract,
            doi=metadata.doi,
            arxiv_id=metadata.arxiv_id,
            source=metadata.source,
            confidence=metadata.confidence,
            extraction_method=metadata.extraction_method,
            processing_time=metadata.processing_time
        )

        # TITLE FORMATTING PIPELINE - using complete processing with all rules
        if formatted.title and formatted.title != "Unknown":
            try:
                logger.debug(f"🔧 Raw title: '{formatted.title}'")

                # Use the complete title processing pipeline
                # This includes: colon transformation, normalization, text processing
                # (number spelling, ellipsis, quotes, etc.), and British English capitalization
                formatted.title = process_title_completely(formatted.title, from_pdf=True, lang='en')
                logger.debug(f"📝 After complete processing: '{formatted.title}'")

            except Exception as e:
                logger.warning(f"Title formatting failed: {e}")

        # AUTHOR FORMATTING PIPELINE - exactly as user requested
        if formatted.authors and formatted.authors != "Unknown":
            try:
                logger.debug(f"🔧 Raw authors: '{formatted.authors}'")

                # Import and use AuthorParser methods
                from validators.author_parser import fix_authors, normalize_author_string

                # Step 1: fix_authors - handles multiple authors
                formatted.authors = fix_authors(formatted.authors)
                logger.debug(f"👤 After fix_authors: '{formatted.authors}'")

                # Step 2: normalize_author_string - comprehensive normalization
                formatted.authors = normalize_author_string(formatted.authors)
                logger.debug(f"👤 After normalize_author_string: '{formatted.authors}'")

            except Exception as e:
                logger.warning(f"Author formatting failed: {e}")

        return formatted

    def extract_metadata_and_rename(self, pdf_path: str, **kwargs) -> tuple[PDFMetadata, str | None]:
        """
        Extract metadata and rename file using PROPER formatting pipeline.

        Args:
            pdf_path: Path to PDF file
            **kwargs: Additional options for metadata extraction

        Returns:
            Tuple of (metadata, new_filename_if_renamed)
        """
        # Extract metadata first (this applies basic normalization)
        metadata = self.extract_metadata(pdf_path, **kwargs)

        # Apply COMPLETE user formatting and rename file
        new_filename = self.validate_and_rename_file(pdf_path, metadata)

        return metadata, new_filename


# Create an instance for use
enhanced_parser = EnhancedPDFParser()


if __name__ == "__main__":
    # Test the enhanced parser
    import argparse

    parser = argparse.ArgumentParser(description="Test enhanced PDF parser")
    parser.add_argument("pdf_file", help="PDF file to parse")
    parser.add_argument("--llm", action="store_true", help="Use LLM enhancement")
    parser.add_argument("--auto-launch", action="store_true", help="Auto-launch LLM server")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Extract metadata
    metadata = enhanced_parser.extract_metadata(
        args.pdf_file,
        use_llm=args.llm,
        auto_launch_llm=args.auto_launch
    )

    # Display results
    print("\n" + "="*80)
    print(f"Title: {metadata.title}")
    print(f"Authors: {metadata.authors}")
    print(f"Source: {metadata.source}")
    print(f"Method: {metadata.extraction_method}")
    print(f"Confidence: {metadata.confidence:.3f}")
    if metadata.abstract:
        print(f"Abstract: {metadata.abstract[:200]}...")
    print("="*80)
