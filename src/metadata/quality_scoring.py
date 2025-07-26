#!/usr/bin/env python3
"""
Metadata Quality Scoring and Source Ranking System
Comprehensive system for evaluating and ranking metadata quality across sources.
"""

import re
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from collections import defaultdict
import logging

from .enhanced_sources import EnhancedMetadata

logger = logging.getLogger(__name__)

@dataclass
class QualityMetrics:
    """Detailed quality metrics for a metadata entry"""
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    freshness_score: float = 0.0
    authority_score: float = 0.0
    consistency_score: float = 0.0
    
    # Sub-metrics
    title_quality: float = 0.0
    author_quality: float = 0.0
    abstract_quality: float = 0.0
    citation_quality: float = 0.0
    venue_quality: float = 0.0
    identifier_quality: float = 0.0
    
    # Detailed breakdown
    missing_fields: List[str] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)
    confidence_factors: Dict[str, float] = field(default_factory=dict)
    
    @property
    def overall_score(self) -> float:
        """Calculate weighted overall quality score"""
        weights = {
            'completeness': 0.25,
            'accuracy': 0.25,
            'authority': 0.20,
            'freshness': 0.15,
            'consistency': 0.15
        }
        
        return (
            self.completeness_score * weights['completeness'] +
            self.accuracy_score * weights['accuracy'] +
            self.authority_score * weights['authority'] +
            self.freshness_score * weights['freshness'] +
            self.consistency_score * weights['consistency']
        )

@dataclass
class SourceRanking:
    """Ranking information for a metadata source"""
    source_name: str
    reliability_score: float = 0.0
    coverage_score: float = 0.0
    freshness_score: float = 0.0
    consistency_score: float = 0.0
    performance_score: float = 0.0
    
    # Historical data
    total_queries: int = 0
    successful_queries: int = 0
    average_response_time: float = 0.0
    last_updated: Optional[datetime] = None
    
    # Quality patterns
    common_issues: List[str] = field(default_factory=list)
    strength_areas: List[str] = field(default_factory=list)
    
    @property
    def overall_ranking(self) -> float:
        """Calculate overall source ranking"""
        weights = {
            'reliability': 0.30,
            'coverage': 0.25,
            'consistency': 0.20,
            'freshness': 0.15,
            'performance': 0.10
        }
        
        return (
            self.reliability_score * weights['reliability'] +
            self.coverage_score * weights['coverage'] +
            self.consistency_score * weights['consistency'] +
            self.freshness_score * weights['freshness'] +
            self.performance_score * weights['performance']
        )
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        return self.successful_queries / max(1, self.total_queries)

class MetadataQualityScorer:
    """Comprehensive metadata quality scoring system"""
    
    def __init__(self):
        # Predefined quality indicators
        self.high_quality_venues = {
            'nature', 'science', 'cell', 'lancet', 'new england journal of medicine',
            'proceedings of the national academy of sciences', 'nature communications',
            'science advances', 'nature biotechnology', 'nature genetics'
        }
        
        self.conference_indicators = {
            'proceedings', 'conference', 'workshop', 'symposium', 'summit',
            'icml', 'nips', 'neurips', 'iclr', 'cvpr', 'iccv', 'eccv',
            'aaai', 'ijcai', 'acl', 'emnlp', 'sigir', 'kdd', 'www'
        }
        
        self.journal_indicators = {
            'journal', 'transactions', 'letters', 'communications', 'review',
            'ieee', 'acm', 'springer', 'elsevier', 'wiley', 'nature', 'science'
        }
        
        # Language patterns for quality assessment
        self.title_quality_patterns = {
            'good': [
                r'^[A-Z][^:]*:',  # Proper title with subtitle
                r'\b(analysis|study|investigation|evaluation|comparison)\b',
                r'\b(novel|new|improved|enhanced|efficient)\b'
            ],
            'poor': [
                r'^[a-z]',  # Lowercase start
                r'[.]{3,}',  # Multiple dots
                r'^(the|a|an)\s',  # Article at start
                r'\?\?\?|\!\!\!',  # Multiple punctuation
            ]
        }
        
        self.abstract_quality_patterns = {
            'good': [
                r'(abstract|summary)[:.]',
                r'\b(background|methods?|results?|conclusions?)\b',
                r'\b(we (present|propose|demonstrate|show|find))\b',
                r'\b\d+(\.\d+)?%\b',  # Percentages
                r'\b(p\s*[<>=]\s*0\.\d+)\b'  # P-values
            ],
            'poor': [
                r'^.{0,50}$',  # Too short
                r'^.{2000,}$',  # Too long
                r'\b(lorem ipsum|placeholder|todo|tbd)\b',
                r'[.]{3,}',  # Ellipsis
            ]
        }
    
    def score_metadata(self, metadata: EnhancedMetadata) -> QualityMetrics:
        """Comprehensively score metadata quality"""
        metrics = QualityMetrics()
        
        # Score individual components
        metrics.title_quality = self._score_title(metadata.title)
        metrics.author_quality = self._score_authors(metadata.authors)
        metrics.abstract_quality = self._score_abstract(metadata.abstract)
        metrics.citation_quality = self._score_citations(metadata.citation_count, metadata.influential_citation_count)
        metrics.venue_quality = self._score_venue(metadata.venue, metadata.venue_type)
        metrics.identifier_quality = self._score_identifiers(metadata.DOI, metadata.arxiv_id, metadata.s2_paper_id)
        
        # Calculate composite scores
        metrics.completeness_score = self._calculate_completeness(metadata, metrics)
        metrics.accuracy_score = self._calculate_accuracy(metadata, metrics)
        metrics.authority_score = self._calculate_authority(metadata, metrics)
        metrics.freshness_score = self._calculate_freshness(metadata)
        metrics.consistency_score = self._calculate_consistency(metadata, metrics)
        
        # Identify issues and missing fields
        metrics.missing_fields = self._identify_missing_fields(metadata)
        metrics.quality_issues = self._identify_quality_issues(metadata, metrics)
        metrics.confidence_factors = self._calculate_confidence_factors(metadata, metrics)
        
        return metrics
    
    def _score_title(self, title: Optional[str]) -> float:
        """Score title quality"""
        if not title or len(title.strip()) < 10:
            return 0.0
        
        score = 0.5  # Base score for having a title
        
        # Length appropriateness
        length = len(title)
        if 20 <= length <= 200:
            score += 0.3
        elif 10 <= length < 20 or 200 < length <= 300:
            score += 0.1
        
        # Pattern matching
        title_lower = title.lower()
        
        # Good patterns
        for pattern in self.title_quality_patterns['good']:
            if re.search(pattern, title_lower):
                score += 0.05  # Small bonuses for each good pattern
        
        # Poor patterns (penalties)
        for pattern in self.title_quality_patterns['poor']:
            if re.search(pattern, title):
                score -= 0.1
        
        # Capitalization check
        words = title.split()
        if words and words[0][0].isupper():
            score += 0.05
        
        # No excessive punctuation
        punct_ratio = sum(1 for c in title if c in '!?.,;:') / len(title)
        if punct_ratio < 0.05:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _score_authors(self, authors: List[str]) -> float:
        """Score author information quality"""
        if not authors:
            return 0.0
        
        score = 0.3  # Base score for having authors
        
        # Number of authors (reasonable range)
        num_authors = len(authors)
        if 1 <= num_authors <= 10:
            score += 0.3
        elif 11 <= num_authors <= 20:
            score += 0.2
        elif num_authors > 50:
            score -= 0.1  # Suspiciously many authors
        
        # Author name format quality
        well_formatted = 0
        for author in authors:
            if self._is_well_formatted_name(author):
                well_formatted += 1
        
        if authors:
            format_ratio = well_formatted / len(authors)
            score += format_ratio * 0.4
        
        return max(0.0, min(1.0, score))
    
    def _is_well_formatted_name(self, name: str) -> bool:
        """Check if author name is well formatted"""
        if not name or len(name) < 3:
            return False
        
        # Should have at least first and last name
        parts = name.split()
        if len(parts) < 2:
            return False
        
        # Should not contain numbers or excessive punctuation
        if re.search(r'\d', name) or name.count('.') > 2:
            return False
        
        # Should start with capital letter
        if not name[0].isupper():
            return False
        
        return True
    
    def _score_abstract(self, abstract: Optional[str]) -> float:
        """Score abstract quality"""
        if not abstract:
            return 0.0
        
        score = 0.2  # Base score for having abstract
        
        # Length appropriateness
        length = len(abstract)
        if 100 <= length <= 2000:
            score += 0.4
        elif 50 <= length < 100 or 2000 < length <= 3000:
            score += 0.2
        elif length < 50:
            score += 0.1
        
        abstract_lower = abstract.lower()
        
        # Good patterns
        good_matches = 0
        for pattern in self.abstract_quality_patterns['good']:
            if re.search(pattern, abstract_lower):
                good_matches += 1
        
        score += min(good_matches * 0.05, 0.2)
        
        # Poor patterns (penalties)
        for pattern in self.abstract_quality_patterns['poor']:
            if re.search(pattern, abstract):
                score -= 0.1
        
        # Sentence structure
        sentences = re.split(r'[.!?]+', abstract)
        if len(sentences) >= 3:
            score += 0.1
        
        # Technical vocabulary (indicates scholarly content)
        technical_words = [
            'methodology', 'analysis', 'results', 'conclusion', 'hypothesis',
            'experiment', 'data', 'significant', 'correlation', 'statistical'
        ]
        tech_count = sum(1 for word in technical_words if word in abstract_lower)
        if tech_count >= 2:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _score_citations(self, citation_count: int, influential_count: int) -> float:
        """Score citation information quality"""
        if citation_count < 0:  # Invalid data
            return 0.0
        
        score = 0.2  # Base score for having citation data
        
        # Citation count scoring (logarithmic)
        if citation_count > 0:
            # Use log scale to avoid over-weighting highly cited papers
            citation_score = min(math.log10(citation_count + 1) / 3.0, 0.5)
            score += citation_score
        
        # Influential citation bonus
        if influential_count > 0:
            influential_ratio = influential_count / max(citation_count, 1)
            if influential_ratio > 0.1:  # > 10% influential citations is good
                score += 0.2
            elif influential_ratio > 0.05:
                score += 0.1
        
        # Reasonable citation counts (not suspicious)
        if citation_count > 10000:  # Suspiciously high
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _score_venue(self, venue: Optional[str], venue_type: Optional[str]) -> float:
        """Score venue quality"""
        if not venue:
            return 0.0
        
        score = 0.2  # Base score for having venue
        
        venue_lower = venue.lower()
        
        # High-quality venue bonus
        for high_venue in self.high_quality_venues:
            if high_venue in venue_lower:
                score += 0.5
                break
        
        # Venue type appropriateness
        if venue_type:
            score += 0.1
            
            # Check venue type consistency
            is_conference = any(indicator in venue_lower for indicator in self.conference_indicators)
            is_journal = any(indicator in venue_lower for indicator in self.journal_indicators)
            
            if venue_type == 'conference' and is_conference:
                score += 0.1
            elif venue_type == 'journal' and is_journal:
                score += 0.1
            elif venue_type in ['conference', 'journal'] and not (is_conference or is_journal):
                score -= 0.1  # Inconsistent
        
        # Publisher recognition
        known_publishers = ['ieee', 'acm', 'springer', 'elsevier', 'wiley', 'nature', 'science']
        if any(pub in venue_lower for pub in known_publishers):
            score += 0.2
        
        return max(0.0, min(1.0, score))
    
    def _score_identifiers(self, doi: Optional[str], arxiv_id: Optional[str], 
                          s2_id: Optional[str]) -> float:
        """Score identifier quality and presence"""
        score = 0.0
        
        # DOI scoring
        if doi:
            if self._is_valid_doi(doi):
                score += 0.5
            else:
                score += 0.2  # Points for having something, penalty for invalid
        
        # ArXiv ID scoring
        if arxiv_id:
            if self._is_valid_arxiv_id(arxiv_id):
                score += 0.3
            else:
                score += 0.1
        
        # Semantic Scholar ID
        if s2_id:
            score += 0.2
        
        return max(0.0, min(1.0, score))
    
    def _is_valid_doi(self, doi: str) -> bool:
        """Check if DOI format is valid"""
        doi_pattern = r'^10\.\d{4,}/[^\s]+$'
        return bool(re.match(doi_pattern, doi))
    
    def _is_valid_arxiv_id(self, arxiv_id: str) -> bool:
        """Check if ArXiv ID format is valid"""
        # New format: YYMM.NNNN or old format: subject-class/YYMMnnn
        new_format = r'^\d{4}\.\d{4,5}(v\d+)?$'
        old_format = r'^[a-z-]+(\.[A-Z]{2})?/\d{7}$'
        return bool(re.match(new_format, arxiv_id) or re.match(old_format, arxiv_id))
    
    def _calculate_completeness(self, metadata: EnhancedMetadata, metrics: QualityMetrics) -> float:
        """Calculate completeness score based on available fields"""
        required_fields = ['title', 'authors', 'published']
        important_fields = ['abstract', 'DOI', 'venue']
        optional_fields = ['keywords', 'fields_of_study', 'citation_count']
        
        score = 0.0
        
        # Required fields (60% of completeness score)
        required_present = 0
        for field in required_fields:
            value = getattr(metadata, field, None)
            if value and (not isinstance(value, list) or len(value) > 0):
                required_present += 1
        
        score += (required_present / len(required_fields)) * 0.6
        
        # Important fields (30% of completeness score)
        important_present = 0
        for field in important_fields:
            value = getattr(metadata, field, None)
            if value and (not isinstance(value, list) or len(value) > 0):
                important_present += 1
        
        score += (important_present / len(important_fields)) * 0.3
        
        # Optional fields (10% of completeness score)
        optional_present = 0
        for field in optional_fields:
            value = getattr(metadata, field, None)
            if value and (not isinstance(value, list) or len(value) > 0):
                optional_present += 1
        
        score += (optional_present / len(optional_fields)) * 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_accuracy(self, metadata: EnhancedMetadata, metrics: QualityMetrics) -> float:
        """Calculate accuracy score based on field quality"""
        field_scores = [
            metrics.title_quality,
            metrics.author_quality,
            metrics.abstract_quality,
            metrics.citation_quality,
            metrics.venue_quality,
            metrics.identifier_quality
        ]
        
        # Weighted average of individual field scores
        weights = [0.25, 0.20, 0.20, 0.15, 0.15, 0.05]
        
        weighted_score = sum(score * weight for score, weight in zip(field_scores, weights))
        return max(0.0, min(1.0, weighted_score))
    
    def _calculate_authority(self, metadata: EnhancedMetadata, metrics: QualityMetrics) -> float:
        """Calculate authority score based on source credibility"""
        score = 0.0
        
        # Source credibility
        source_scores = {
            'semantic_scholar': 0.9,
            'openalex': 0.85,
            'crossref': 0.9,
            'pubmed': 0.95,
            'arxiv': 0.8,
            'google_scholar': 0.7
        }
        
        if metadata.source in source_scores:
            score += source_scores[metadata.source] * 0.3
        
        # Venue authority
        score += metrics.venue_quality * 0.3
        
        # Citation authority
        score += metrics.citation_quality * 0.2
        
        # Identifier authority
        score += metrics.identifier_quality * 0.2
        
        return max(0.0, min(1.0, score))
    
    def _calculate_freshness(self, metadata: EnhancedMetadata) -> float:
        """Calculate freshness score based on publication date"""
        if not metadata.published:
            return 0.0
        
        try:
            pub_date = datetime.strptime(metadata.published[:10], '%Y-%m-%d').date()
            current_date = date.today()
            
            # Calculate age in years
            age_years = (current_date - pub_date).days / 365.25
            
            # Freshness scoring (higher for more recent papers)
            if age_years <= 1:
                return 1.0
            elif age_years <= 3:
                return 0.9
            elif age_years <= 5:
                return 0.8
            elif age_years <= 10:
                return 0.6
            elif age_years <= 20:
                return 0.4
            else:
                return 0.2
                
        except (ValueError, IndexError):
            return 0.0
    
    def _calculate_consistency(self, metadata: EnhancedMetadata, metrics: QualityMetrics) -> float:
        """Calculate consistency score based on internal coherence"""
        score = 1.0  # Start with perfect consistency
        
        # Check venue type consistency
        if metadata.venue and metadata.venue_type:
            venue_lower = metadata.venue.lower()
            is_conference = any(ind in venue_lower for ind in self.conference_indicators)
            is_journal = any(ind in venue_lower for ind in self.journal_indicators)
            
            if metadata.venue_type == 'conference' and not is_conference:
                score -= 0.2
            elif metadata.venue_type == 'journal' and not is_journal:
                score -= 0.2
        
        # Check author count vs citation count reasonableness
        if metadata.authors and metadata.citation_count:
            if len(metadata.authors) > 100 and metadata.citation_count < 10:
                score -= 0.1  # Suspicious: many authors, few citations
        
        # Check publication year consistency
        if metadata.published:
            try:
                pub_year = int(metadata.published[:4])
                current_year = datetime.now().year
                
                if pub_year > current_year:
                    score -= 0.3  # Future publication
                elif pub_year < 1800:
                    score -= 0.3  # Too old to be credible
                    
            except (ValueError, IndexError):
                score -= 0.1  # Invalid date format
        
        # Check fields of study vs venue consistency
        if metadata.fields_of_study and metadata.venue:
            # Basic consistency checks could be implemented here
            pass
        
        return max(0.0, min(1.0, score))
    
    def _identify_missing_fields(self, metadata: EnhancedMetadata) -> List[str]:
        """Identify missing important fields"""
        missing = []
        
        important_fields = {
            'title': metadata.title,
            'authors': metadata.authors,
            'published': metadata.published,
            'abstract': metadata.abstract,
            'DOI': metadata.DOI,
            'venue': metadata.venue,
            'citation_count': metadata.citation_count
        }
        
        for field_name, field_value in important_fields.items():
            if not field_value or (isinstance(field_value, list) and len(field_value) == 0):
                missing.append(field_name)
        
        return missing
    
    def _identify_quality_issues(self, metadata: EnhancedMetadata, metrics: QualityMetrics) -> List[str]:
        """Identify specific quality issues"""
        issues = []
        
        # Title issues
        if metrics.title_quality < 0.3:
            issues.append("Poor title quality")
        
        # Author issues
        if metrics.author_quality < 0.3:
            issues.append("Poor author formatting")
        
        # Abstract issues
        if metadata.abstract and len(metadata.abstract) < 50:
            issues.append("Abstract too short")
        elif metadata.abstract and len(metadata.abstract) > 3000:
            issues.append("Abstract too long")
        
        # Citation issues
        if metadata.citation_count < 0:
            issues.append("Invalid citation count")
        
        # Date issues
        if metadata.published:
            try:
                pub_year = int(metadata.published[:4])
                if pub_year > datetime.now().year:
                    issues.append("Future publication date")
                elif pub_year < 1900:
                    issues.append("Very old publication date")
            except (ValueError, IndexError):
                issues.append("Invalid publication date format")
        
        # Identifier issues
        if metadata.DOI and not self._is_valid_doi(metadata.DOI):
            issues.append("Invalid DOI format")
        
        if metadata.arxiv_id and not self._is_valid_arxiv_id(metadata.arxiv_id):
            issues.append("Invalid ArXiv ID format")
        
        return issues
    
    def _calculate_confidence_factors(self, metadata: EnhancedMetadata, metrics: QualityMetrics) -> Dict[str, float]:
        """Calculate confidence factors for different aspects"""
        factors = {}
        
        # Source confidence
        source_confidence = {
            'semantic_scholar': 0.9,
            'openalex': 0.85,
            'crossref': 0.9,
            'pubmed': 0.95,
            'arxiv': 0.8
        }
        factors['source'] = source_confidence.get(metadata.source, 0.5)
        
        # Identifier confidence
        id_conf = 0.0
        if metadata.DOI and self._is_valid_doi(metadata.DOI):
            id_conf += 0.5
        if metadata.arxiv_id and self._is_valid_arxiv_id(metadata.arxiv_id):
            id_conf += 0.3
        if metadata.s2_paper_id:
            id_conf += 0.2
        factors['identifiers'] = min(1.0, id_conf)
        
        # Content confidence
        factors['content'] = (metrics.title_quality + metrics.abstract_quality) / 2
        
        # Authority confidence
        factors['authority'] = metrics.authority_score
        
        return factors

class SourceRankingSystem:
    """System for ranking and evaluating metadata sources"""
    
    def __init__(self):
        self.source_rankings: Dict[str, SourceRanking] = {}
        self.quality_scorer = MetadataQualityScorer()
        
        # Initialize with default source rankings
        self._initialize_default_rankings()
    
    def _initialize_default_rankings(self):
        """Initialize with known source characteristics"""
        default_sources = {
            'semantic_scholar': SourceRanking(
                source_name='semantic_scholar',
                reliability_score=0.9,
                coverage_score=0.8,  # Strong in CS/AI, weaker elsewhere
                freshness_score=0.9,
                consistency_score=0.85,
                performance_score=0.8,
                strength_areas=['Computer Science', 'AI/ML', 'Citations']
            ),
            'openalex': SourceRanking(
                source_name='openalex',
                reliability_score=0.85,
                coverage_score=0.95,  # Excellent coverage across fields
                freshness_score=0.8,
                consistency_score=0.8,
                performance_score=0.9,
                strength_areas=['Comprehensive Coverage', 'Open Access', 'Author Info']
            ),
            'crossref': SourceRanking(
                source_name='crossref',
                reliability_score=0.95,
                coverage_score=0.7,
                freshness_score=0.8,
                consistency_score=0.9,
                performance_score=0.7,
                strength_areas=['DOI Registry', 'Publisher Data', 'Citations']
            ),
            'arxiv': SourceRanking(
                source_name='arxiv',
                reliability_score=0.8,
                coverage_score=0.4,  # Limited to preprints
                freshness_score=0.95,  # Very fresh
                consistency_score=0.8,
                performance_score=0.9,
                strength_areas=['Preprints', 'Physics', 'Math', 'CS']
            )
        }
        
        self.source_rankings.update(default_sources)
    
    def update_source_ranking(self, source_name: str, metadata_list: List[EnhancedMetadata],
                            response_times: List[float] = None):
        """Update source ranking based on actual performance"""
        if source_name not in self.source_rankings:
            self.source_rankings[source_name] = SourceRanking(source_name=source_name)
        
        ranking = self.source_rankings[source_name]
        
        # Update query statistics
        ranking.total_queries += len(metadata_list)
        ranking.successful_queries += len([m for m in metadata_list if m.title])
        
        # Update response time
        if response_times:
            total_time = sum(response_times)
            total_queries = ranking.total_queries
            ranking.average_response_time = (
                (ranking.average_response_time * (total_queries - len(response_times)) + total_time) / 
                total_queries
            )
        
        # Analyze quality patterns
        quality_scores = []
        common_issues = defaultdict(int)
        
        for metadata in metadata_list:
            if metadata.title:  # Valid metadata
                metrics = self.quality_scorer.score_metadata(metadata)
                quality_scores.append(metrics.overall_score)
                
                # Track common issues
                for issue in metrics.quality_issues:
                    common_issues[issue] += 1
        
        # Update quality-based scores
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            # Update reliability based on average quality
            ranking.reliability_score = self._update_score(ranking.reliability_score, avg_quality, 0.1)
            
            # Update consistency based on quality variance
            quality_variance = sum((q - avg_quality) ** 2 for q in quality_scores) / len(quality_scores)
            consistency_score = max(0, 1 - (quality_variance * 2))  # Low variance = high consistency
            ranking.consistency_score = self._update_score(ranking.consistency_score, consistency_score, 0.1)
        
        # Update common issues
        ranking.common_issues = [issue for issue, count in common_issues.most_common(5)]
        
        # Update performance score based on response time
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            # Good performance: < 1s, Poor performance: > 10s
            perf_score = max(0, min(1, 1 - (avg_response - 1) / 9))
            ranking.performance_score = self._update_score(ranking.performance_score, perf_score, 0.2)
        
        ranking.last_updated = datetime.now()
    
    def _update_score(self, current_score: float, new_measurement: float, learning_rate: float) -> float:
        """Update score using exponential moving average"""
        return current_score * (1 - learning_rate) + new_measurement * learning_rate
    
    def get_ranked_sources(self, field_of_study: Optional[str] = None) -> List[SourceRanking]:
        """Get sources ranked by overall quality"""
        sources = list(self.source_rankings.values())
        
        # Apply field-specific adjustments
        if field_of_study:
            sources = self._apply_field_specific_ranking(sources, field_of_study)
        
        # Sort by overall ranking
        sources.sort(key=lambda x: x.overall_ranking, reverse=True)
        
        return sources
    
    def _apply_field_specific_ranking(self, sources: List[SourceRanking], 
                                    field: str) -> List[SourceRanking]:
        """Apply field-specific ranking adjustments"""
        field_lower = field.lower()
        
        # Field-specific boosts
        field_boosts = {
            'computer science': {'semantic_scholar': 0.1, 'arxiv': 0.05},
            'physics': {'arxiv': 0.15, 'openalex': 0.05},
            'medicine': {'pubmed': 0.2, 'crossref': 0.05},
            'biology': {'pubmed': 0.15, 'openalex': 0.1},
            'mathematics': {'arxiv': 0.1, 'openalex': 0.05}
        }
        
        # Apply boosts
        adjusted_sources = []
        for source in sources:
            adjusted_source = SourceRanking(**source.__dict__)  # Copy
            
            for field_name, boosts in field_boosts.items():
                if field_name in field_lower:
                    boost = boosts.get(source.source_name, 0)
                    adjusted_source.coverage_score = min(1.0, adjusted_source.coverage_score + boost)
                    break
            
            adjusted_sources.append(adjusted_source)
        
        return adjusted_sources
    
    def recommend_sources(self, query_type: str, quality_threshold: float = 0.7) -> List[str]:
        """Recommend best sources for a specific query type"""
        sources = self.get_ranked_sources()
        
        recommendations = []
        for source in sources:
            if source.overall_ranking >= quality_threshold:
                recommendations.append(source.source_name)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def get_source_analysis(self, source_name: str) -> Dict[str, Any]:
        """Get detailed analysis of a specific source"""
        if source_name not in self.source_rankings:
            return {'error': f'Source {source_name} not found'}
        
        ranking = self.source_rankings[source_name]
        
        return {
            'source_name': source_name,
            'overall_ranking': ranking.overall_ranking,
            'success_rate': ranking.success_rate,
            'scores': {
                'reliability': ranking.reliability_score,
                'coverage': ranking.coverage_score,
                'freshness': ranking.freshness_score,
                'consistency': ranking.consistency_score,
                'performance': ranking.performance_score
            },
            'statistics': {
                'total_queries': ranking.total_queries,
                'successful_queries': ranking.successful_queries,
                'average_response_time': ranking.average_response_time
            },
            'strengths': ranking.strength_areas,
            'common_issues': ranking.common_issues,
            'last_updated': ranking.last_updated
        }
    
    def export_rankings(self) -> Dict[str, Any]:
        """Export all rankings for persistence"""
        return {
            source_name: {
                'ranking': ranking.__dict__,
                'analysis': self.get_source_analysis(source_name)
            }
            for source_name, ranking in self.source_rankings.items()
        }

# Example usage and testing
def example_usage():
    """Demonstrate quality scoring and source ranking"""
    
    # Create sample metadata
    sample_metadata = EnhancedMetadata(
        title="Deep Learning for Natural Language Processing: A Comprehensive Survey",
        authors=["Smith, John", "Doe, Jane", "Johnson, Bob"],
        published="2023-01-15",
        abstract="This paper presents a comprehensive survey of deep learning techniques applied to natural language processing. We review recent advances in neural architectures, training methodologies, and applications across various NLP tasks. Our analysis covers transformer models, attention mechanisms, and pre-trained language models.",
        DOI="10.1038/s41586-023-12345-6",
        citation_count=25,
        influential_citation_count=8,
        venue="Nature Machine Intelligence",
        venue_type="journal",
        fields_of_study=["Computer Science", "Natural Language Processing", "Deep Learning"],
        source="semantic_scholar"
    )
    
    # Score metadata quality
    scorer = MetadataQualityScorer()
    metrics = scorer.score_metadata(sample_metadata)
    
    print("Quality Metrics:")
    print(f"  Overall Score: {metrics.overall_score:.3f}")
    print(f"  Completeness: {metrics.completeness_score:.3f}")
    print(f"  Accuracy: {metrics.accuracy_score:.3f}")
    print(f"  Authority: {metrics.authority_score:.3f}")
    print(f"  Freshness: {metrics.freshness_score:.3f}")
    print(f"  Consistency: {metrics.consistency_score:.3f}")
    
    if metrics.quality_issues:
        print(f"  Issues: {', '.join(metrics.quality_issues)}")
    
    if metrics.missing_fields:
        print(f"  Missing: {', '.join(metrics.missing_fields)}")
    
    # Demonstrate source ranking
    ranking_system = SourceRankingSystem()
    
    # Update with sample data
    ranking_system.update_source_ranking(
        'semantic_scholar', 
        [sample_metadata], 
        [1.2]  # 1.2 second response time
    )
    
    # Get recommendations
    recommendations = ranking_system.recommend_sources('literature_review')
    print(f"\nRecommended sources: {', '.join(recommendations)}")
    
    # Get source analysis
    analysis = ranking_system.get_source_analysis('semantic_scholar')
    print(f"\nSemantic Scholar Analysis:")
    print(f"  Overall Ranking: {analysis['overall_ranking']:.3f}")
    print(f"  Success Rate: {analysis['success_rate']:.3f}")
    print(f"  Strengths: {', '.join(analysis['strengths'])}")

if __name__ == "__main__":
    example_usage()