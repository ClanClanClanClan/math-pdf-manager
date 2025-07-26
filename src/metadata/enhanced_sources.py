#!/usr/bin/env python3
"""
Enhanced Metadata Sources
Comprehensive integrations with major academic APIs for metadata discovery.
"""

import asyncio
import aiohttp
import json
import time
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from urllib.parse import quote, urljoin
import logging

from metadata_fetcher import Metadata, canonicalize

logger = logging.getLogger(__name__)

@dataclass
class EnhancedMetadata(Metadata):
    """Extended metadata with additional fields"""
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    citation_count: int = 0
    influential_citation_count: int = 0
    venue: Optional[str] = None
    venue_type: Optional[str] = None  # journal, conference, preprint
    open_access: bool = False
    pdf_urls: List[str] = field(default_factory=list)
    fields_of_study: List[str] = field(default_factory=list)
    s2_paper_id: Optional[str] = None
    openalex_id: Optional[str] = None
    orcid_ids: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with all fields"""
        base_dict = super().to_dict()
        base_dict.update({
            'abstract': self.abstract,
            'keywords': self.keywords,
            'references': self.references,
            'citations': self.citations,
            'citation_count': self.citation_count,
            'influential_citation_count': self.influential_citation_count,
            'venue': self.venue,
            'venue_type': self.venue_type,
            'open_access': self.open_access,
            'pdf_urls': self.pdf_urls,
            'fields_of_study': self.fields_of_study,
            's2_paper_id': self.s2_paper_id,
            'openalex_id': self.openalex_id,
            'orcid_ids': self.orcid_ids,
            'quality_score': self.quality_score
        })
        return base_dict

class SemanticScholarAPI:
    """Semantic Scholar API integration - excellent for CS/AI papers"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.session = None
        self.rate_limit = 1.0  # 1 second between requests (100 requests/5min without key)
        self.last_request = 0.0
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {'User-Agent': 'AcademicPaperManager/1.0'}
        
        if self.api_key:
            headers['x-api-key'] = self.api_key
            self.rate_limit = 0.1  # 10 requests/second with API key
            
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit_wait(self):
        """Ensure rate limiting compliance"""
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < self.rate_limit:
            wait_time = self.rate_limit - time_since_last
            await asyncio.sleep(wait_time)
        self.last_request = time.time()
    
    async def search_papers(self, query: str, limit: int = 20, fields: Optional[List[str]] = None) -> List[EnhancedMetadata]:
        """Search papers by query string"""
        await self._rate_limit_wait()
        
        if fields is None:
            fields = [
                'paperId', 'title', 'authors', 'year', 'abstract', 'citationCount',
                'influentialCitationCount', 'references', 'citations', 'venue',
                'openAccessPdf', 'fieldsOfStudy', 'externalIds'
            ]
        
        url = f"{self.base_url}/paper/search"
        params = {
            'query': query,
            'limit': min(limit, 100),  # API limit
            'fields': ','.join(fields)
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    papers = data.get('data', [])
                    return [self._parse_s2_paper(paper) for paper in papers]
                elif response.status == 429:
                    logger.warning("Semantic Scholar rate limit exceeded")
                    await asyncio.sleep(60)  # Wait 1 minute
                    return []
                else:
                    logger.error(f"Semantic Scholar search failed: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
            return []
    
    async def get_paper_by_id(self, paper_id: str, fields: Optional[List[str]] = None) -> Optional[EnhancedMetadata]:
        """Get paper by Semantic Scholar ID, DOI, ArXiv ID, etc."""
        await self._rate_limit_wait()
        
        if fields is None:
            fields = [
                'paperId', 'title', 'authors', 'year', 'abstract', 'citationCount',
                'influentialCitationCount', 'references', 'citations', 'venue',
                'openAccessPdf', 'fieldsOfStudy', 'externalIds'
            ]
        
        url = f"{self.base_url}/paper/{paper_id}"
        params = {'fields': ','.join(fields)}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    paper = await response.json()
                    return self._parse_s2_paper(paper)
                elif response.status == 404:
                    logger.debug(f"Paper not found in Semantic Scholar: {paper_id}")
                    return None
                else:
                    logger.error(f"Semantic Scholar get paper failed: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Semantic Scholar get paper error: {e}")
            return None
    
    async def get_citations(self, paper_id: str, limit: int = 100) -> List[EnhancedMetadata]:
        """Get papers that cite this paper"""
        await self._rate_limit_wait()
        
        url = f"{self.base_url}/paper/{paper_id}/citations"
        params = {
            'limit': min(limit, 1000),
            'fields': 'paperId,title,authors,year,citationCount,venue'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    citations = data.get('data', [])
                    return [self._parse_s2_paper(citation.get('citingPaper', {})) for citation in citations]
        except Exception as e:
            logger.error(f"Semantic Scholar citations error: {e}")
        
        return []
    
    async def get_references(self, paper_id: str, limit: int = 100) -> List[EnhancedMetadata]:
        """Get papers referenced by this paper"""
        await self._rate_limit_wait()
        
        url = f"{self.base_url}/paper/{paper_id}/references"
        params = {
            'limit': min(limit, 1000),
            'fields': 'paperId,title,authors,year,citationCount,venue'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    references = data.get('data', [])
                    return [self._parse_s2_paper(ref.get('citedPaper', {})) for ref in references]
        except Exception as e:
            logger.error(f"Semantic Scholar references error: {e}")
        
        return []
    
    def _parse_s2_paper(self, paper: Dict[str, Any]) -> EnhancedMetadata:
        """Parse Semantic Scholar paper data"""
        # Extract basic info
        title = paper.get('title', '')
        year = paper.get('year')
        abstract = paper.get('abstract', '')
        
        # Extract authors
        authors = []
        author_orcids = []
        for author in paper.get('authors', []):
            name = author.get('name', '')
            if name:
                authors.append(name)
            if 'externalIds' in author and author['externalIds'].get('ORCID'):
                author_orcids.append(author['externalIds']['ORCID'])
        
        # Extract external IDs
        external_ids = paper.get('externalIds', {})
        doi = external_ids.get('DOI')
        arxiv_id = external_ids.get('ArXiv')
        
        # Extract venue information
        venue = paper.get('venue', '')
        venue_type = None
        if venue:
            if any(conf_word in venue.lower() for conf_word in ['conference', 'workshop', 'symposium']):
                venue_type = 'conference'
            elif any(journal_word in venue.lower() for journal_word in ['journal', 'transactions', 'proceedings']):
                venue_type = 'journal'
            elif 'arxiv' in venue.lower():
                venue_type = 'preprint'
        
        # Extract open access info
        open_access = False
        pdf_urls = []
        if paper.get('openAccessPdf'):
            open_access = True
            pdf_url = paper['openAccessPdf'].get('url')
            if pdf_url:
                pdf_urls.append(pdf_url)
        
        # Extract fields of study
        fields_of_study = []
        for field in paper.get('fieldsOfStudy', []):
            if isinstance(field, str):
                fields_of_study.append(field)
            elif isinstance(field, dict):
                fields_of_study.append(field.get('category', ''))
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(paper)
        
        return EnhancedMetadata(
            title=title,
            authors=authors,
            published=f"{year}-01-01" if year else "",
            DOI=doi,
            arxiv_id=arxiv_id,
            abstract=abstract,
            citation_count=paper.get('citationCount', 0),
            influential_citation_count=paper.get('influentialCitationCount', 0),
            venue=venue,
            venue_type=venue_type,
            open_access=open_access,
            pdf_urls=pdf_urls,
            fields_of_study=fields_of_study,
            s2_paper_id=paper.get('paperId'),
            orcid_ids=author_orcids,
            quality_score=quality_score,
            source='semantic_scholar'
        )
    
    def _calculate_quality_score(self, paper: Dict[str, Any]) -> float:
        """Calculate quality score based on various factors"""
        score = 0.0
        
        # Citation count (normalized)
        citation_count = paper.get('citationCount', 0)
        if citation_count > 0:
            score += min(citation_count / 100, 0.3)  # Up to 0.3 for citations
        
        # Influential citations (higher weight)
        influential_count = paper.get('influentialCitationCount', 0)
        if influential_count > 0:
            score += min(influential_count / 50, 0.2)  # Up to 0.2 for influential citations
        
        # Venue quality
        venue = paper.get('venue', '').lower()
        if any(top_venue in venue for top_venue in ['nature', 'science', 'cell', 'lancet']):
            score += 0.2
        elif any(good_venue in venue for good_venue in ['ieee', 'acm', 'springer']):
            score += 0.1
        
        # Recent papers get slight boost
        year = paper.get('year', 0)
        if year >= 2020:
            score += 0.1
        elif year >= 2015:
            score += 0.05
        
        # Abstract availability
        if paper.get('abstract'):
            score += 0.05
        
        # Open access availability
        if paper.get('openAccessPdf'):
            score += 0.1
        
        return min(score, 1.0)

class OpenAlexAPI:
    """OpenAlex API integration - comprehensive academic database"""
    
    def __init__(self, email: Optional[str] = None):
        self.email = email  # Polite pool access
        self.base_url = "https://api.openalex.org"
        self.session = None
        self.rate_limit = 0.1  # 10 requests/second for polite pool
        self.last_request = 0.0
    
    async def __aenter__(self):
        headers = {'User-Agent': 'AcademicPaperManager/1.0'}
        if self.email:
            headers['User-Agent'] += f' (mailto:{self.email})'
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit_wait(self):
        """Rate limiting for OpenAlex"""
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        self.last_request = time.time()
    
    async def search_works(self, query: str, limit: int = 25) -> List[EnhancedMetadata]:
        """Search works (papers) in OpenAlex"""
        await self._rate_limit_wait()
        
        url = f"{self.base_url}/works"
        params = {
            'search': query,
            'per-page': min(limit, 200),  # API limit
            'sort': 'cited_by_count:desc'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    works = data.get('results', [])
                    return [self._parse_openalex_work(work) for work in works]
                else:
                    logger.error(f"OpenAlex search failed: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"OpenAlex search error: {e}")
            return []
    
    async def get_work_by_doi(self, doi: str) -> Optional[EnhancedMetadata]:
        """Get work by DOI"""
        await self._rate_limit_wait()
        
        # Clean DOI
        clean_doi = doi.replace('doi:', '').replace('https://doi.org/', '')
        url = f"{self.base_url}/works/doi:{clean_doi}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    work = await response.json()
                    return self._parse_openalex_work(work)
                elif response.status == 404:
                    logger.debug(f"Work not found in OpenAlex: {doi}")
                    return None
        except Exception as e:
            logger.error(f"OpenAlex get work error: {e}")
        
        return None
    
    async def get_related_works(self, work_id: str, limit: int = 20) -> List[EnhancedMetadata]:
        """Get works related to a given work"""
        await self._rate_limit_wait()
        
        url = f"{self.base_url}/works/{work_id}/related_works"
        params = {'per-page': min(limit, 50)}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    works = data.get('results', [])
                    return [self._parse_openalex_work(work) for work in works]
        except Exception as e:
            logger.error(f"OpenAlex related works error: {e}")
        
        return []
    
    def _parse_openalex_work(self, work: Dict[str, Any]) -> EnhancedMetadata:
        """Parse OpenAlex work data"""
        title = work.get('title', '')
        
        # Extract authors
        authors = []
        author_orcids = []
        for authorship in work.get('authorships', []):
            author = authorship.get('author', {})
            display_name = author.get('display_name', '')
            if display_name:
                authors.append(display_name)
            
            orcid = author.get('orcid')
            if orcid:
                # Extract ORCID ID from URL
                orcid_id = orcid.split('/')[-1] if '/' in orcid else orcid
                author_orcids.append(orcid_id)
        
        # Extract publication date
        pub_date = work.get('publication_date', '')
        
        # Extract DOI
        doi = work.get('doi')
        if doi and doi.startswith('https://doi.org/'):
            doi = doi.replace('https://doi.org/', '')
        
        # Extract venue information
        venue = ''
        venue_type = None
        primary_location = work.get('primary_location', {})
        if primary_location:
            source = primary_location.get('source', {})
            venue = source.get('display_name', '')
            source_type = source.get('type')
            if source_type == 'journal':
                venue_type = 'journal'
            elif source_type == 'repository':
                venue_type = 'preprint'
        
        # Extract open access info
        open_access = work.get('open_access', {}).get('is_oa', False)
        
        # Extract PDF URLs
        pdf_urls = []
        for location in work.get('locations', []):
            if location.get('pdf_url'):
                pdf_urls.append(location['pdf_url'])
        
        # Extract concepts (fields of study)
        fields_of_study = []
        for concept in work.get('concepts', []):
            if concept.get('score', 0) > 0.3:  # Only include high-confidence concepts
                fields_of_study.append(concept.get('display_name', ''))
        
        # Extract abstract
        abstract = ''
        inverted_abstract = work.get('abstract_inverted_index')
        if inverted_abstract:
            abstract = self._reconstruct_abstract(inverted_abstract)
        
        return EnhancedMetadata(
            title=title,
            authors=authors,
            published=pub_date,
            DOI=doi,
            abstract=abstract,
            citation_count=work.get('cited_by_count', 0),
            venue=venue,
            venue_type=venue_type,
            open_access=open_access,
            pdf_urls=pdf_urls,
            fields_of_study=fields_of_study,
            openalex_id=work.get('id'),
            orcid_ids=author_orcids,
            quality_score=self._calculate_openalex_quality_score(work),
            source='openalex'
        )
    
    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """Reconstruct abstract from inverted index"""
        try:
            # Create list of (position, word) tuples
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join
            word_positions.sort(key=lambda x: x[0])
            return ' '.join(word for pos, word in word_positions)
        except Exception:
            return ''
    
    def _calculate_openalex_quality_score(self, work: Dict[str, Any]) -> float:
        """Calculate quality score for OpenAlex work"""
        score = 0.0
        
        # Citation count (normalized)
        citation_count = work.get('cited_by_count', 0)
        if citation_count > 0:
            score += min(citation_count / 200, 0.3)
        
        # Open access bonus
        if work.get('open_access', {}).get('is_oa'):
            score += 0.1
        
        # Recent publication bonus
        pub_year = work.get('publication_year', 0)
        if pub_year >= 2020:
            score += 0.1
        elif pub_year >= 2015:
            score += 0.05
        
        # Abstract availability
        if work.get('abstract_inverted_index'):
            score += 0.05
        
        # High concept confidence
        high_confidence_concepts = sum(1 for concept in work.get('concepts', []) 
                                     if concept.get('score', 0) > 0.5)
        if high_confidence_concepts >= 3:
            score += 0.1
        
        return min(score, 1.0)

class ORCIDIntegration:
    """ORCID integration for author information"""
    
    def __init__(self):
        self.base_url = "https://pub.orcid.org/v3.0"
        self.session = None
        self.rate_limit = 0.5  # 2 requests/second (public API limit)
        self.last_request = 0.0
    
    async def __aenter__(self):
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'AcademicPaperManager/1.0'
        }
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _rate_limit_wait(self):
        """Rate limiting for ORCID API"""
        now = time.time()
        time_since_last = now - self.last_request
        if time_since_last < self.rate_limit:
            await asyncio.sleep(self.rate_limit - time_since_last)
        self.last_request = time.time()
    
    async def get_author_works(self, orcid_id: str) -> List[Dict[str, Any]]:
        """Get works for an ORCID author"""
        await self._rate_limit_wait()
        
        # Clean ORCID ID
        clean_orcid = orcid_id.replace('https://orcid.org/', '').replace('orcid.org/', '')
        
        url = f"{self.base_url}/{clean_orcid}/works"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    works_summary = data.get('group', [])
                    
                    # Get detailed information for each work
                    detailed_works = []
                    for group in works_summary[:10]:  # Limit to 10 works
                        work_summary = group.get('work-summary', [])
                        if work_summary:
                            work_detail = await self._get_work_details(clean_orcid, work_summary[0].get('put-code'))
                            if work_detail:
                                detailed_works.append(work_detail)
                    
                    return detailed_works
        except Exception as e:
            logger.error(f"ORCID works error: {e}")
        
        return []
    
    async def _get_work_details(self, orcid_id: str, put_code: str) -> Optional[Dict[str, Any]]:
        """Get detailed work information"""
        await self._rate_limit_wait()
        
        url = f"{self.base_url}/{orcid_id}/work/{put_code}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.debug(f"ORCID work detail error: {e}")
        
        return None
    
    async def search_authors(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for authors by name or other criteria"""
        await self._rate_limit_wait()
        
        url = f"{self.base_url}/search"
        params = {
            'q': query,
            'rows': min(limit, 200)
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result', [])
        except Exception as e:
            logger.error(f"ORCID search error: {e}")
        
        return []

class EnhancedMetadataOrchestrator:
    """Orchestrates multiple metadata sources for comprehensive paper information"""
    
    def __init__(self, semantic_scholar_key: Optional[str] = None, 
                 openalex_email: Optional[str] = None):
        self.semantic_scholar_key = semantic_scholar_key
        self.openalex_email = openalex_email
        
        # Statistics
        self.stats = {
            'queries': 0,
            'semantic_scholar_hits': 0,
            'openalex_hits': 0,
            'orcid_hits': 0,
            'combined_results': 0
        }
    
    async def comprehensive_search(self, query: str, max_results: int = 50) -> List[EnhancedMetadata]:
        """Search across all metadata sources and combine results"""
        self.stats['queries'] += 1
        
        # Search all sources concurrently
        tasks = [
            self._search_semantic_scholar(query, max_results // 2),
            self._search_openalex(query, max_results // 2)
        ]
        
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate results
        all_results = []
        seen_dois = set()
        seen_titles = set()
        
        for results_list in results_lists:
            if isinstance(results_list, list):
                for result in results_list:
                    # Deduplicate by DOI or title
                    identifier = result.DOI or canonicalize(result.title)
                    if identifier and identifier not in seen_dois and identifier not in seen_titles:
                        if result.DOI:
                            seen_dois.add(result.DOI)
                        seen_titles.add(canonicalize(result.title))
                        all_results.append(result)
        
        # Sort by quality score
        all_results.sort(key=lambda x: x.quality_score, reverse=True)
        
        self.stats['combined_results'] += len(all_results)
        return all_results[:max_results]
    
    async def _search_semantic_scholar(self, query: str, limit: int) -> List[EnhancedMetadata]:
        """Search Semantic Scholar"""
        try:
            async with SemanticScholarAPI(self.semantic_scholar_key) as s2:
                results = await s2.search_papers(query, limit)
                self.stats['semantic_scholar_hits'] += len(results)
                return results
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []
    
    async def _search_openalex(self, query: str, limit: int) -> List[EnhancedMetadata]:
        """Search OpenAlex"""
        try:
            async with OpenAlexAPI(self.openalex_email) as openalex:
                results = await openalex.search_works(query, limit)
                self.stats['openalex_hits'] += len(results)
                return results
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return []
    
    async def enrich_metadata(self, metadata: EnhancedMetadata) -> EnhancedMetadata:
        """Enrich existing metadata with additional information from multiple sources"""
        
        # If we have a DOI, try to get more information
        if metadata.DOI:
            enrichment_tasks = []
            
            # Try Semantic Scholar
            if not metadata.s2_paper_id:
                enrichment_tasks.append(self._enrich_from_semantic_scholar(metadata))
            
            # Try OpenAlex
            if not metadata.openalex_id:
                enrichment_tasks.append(self._enrich_from_openalex(metadata))
            
            if enrichment_tasks:
                enrichment_results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
                
                # Merge enriched data
                for result in enrichment_results:
                    if isinstance(result, EnhancedMetadata):
                        metadata = self._merge_metadata(metadata, result)
        
        # Enrich with ORCID data if we have author ORCID IDs
        if metadata.orcid_ids:
            orcid_data = await self._enrich_from_orcid(metadata)
            if orcid_data:
                metadata = self._merge_metadata(metadata, orcid_data)
        
        # Recalculate quality score with enriched data
        metadata.quality_score = self._calculate_combined_quality_score(metadata)
        
        return metadata
    
    async def _enrich_from_semantic_scholar(self, metadata: EnhancedMetadata) -> Optional[EnhancedMetadata]:
        """Enrich from Semantic Scholar"""
        try:
            async with SemanticScholarAPI(self.semantic_scholar_key) as s2:
                if metadata.DOI:
                    enriched = await s2.get_paper_by_id(f"DOI:{metadata.DOI}")
                    return enriched
        except Exception as e:
            logger.debug(f"Semantic Scholar enrichment failed: {e}")
        return None
    
    async def _enrich_from_openalex(self, metadata: EnhancedMetadata) -> Optional[EnhancedMetadata]:
        """Enrich from OpenAlex"""
        try:
            async with OpenAlexAPI(self.openalex_email) as openalex:
                if metadata.DOI:
                    enriched = await openalex.get_work_by_doi(metadata.DOI)
                    return enriched
        except Exception as e:
            logger.debug(f"OpenAlex enrichment failed: {e}")
        return None
    
    async def _enrich_from_orcid(self, metadata: EnhancedMetadata) -> Optional[EnhancedMetadata]:
        """Enrich from ORCID"""
        # This would involve matching the paper to ORCID works
        # Implementation would be more complex
        return None
    
    def _merge_metadata(self, base: EnhancedMetadata, enrichment: EnhancedMetadata) -> EnhancedMetadata:
        """Merge two metadata objects, preferring more complete information"""
        
        # Merge fields, preferring non-empty values
        merged = EnhancedMetadata(**base.to_dict())
        
        for field_name, field_value in enrichment.to_dict().items():
            if field_value and (not getattr(merged, field_name) or 
                              (isinstance(field_value, list) and len(field_value) > len(getattr(merged, field_name)))):
                setattr(merged, field_name, field_value)
        
        # Merge lists
        for list_field in ['keywords', 'references', 'citations', 'pdf_urls', 'fields_of_study', 'orcid_ids']:
            base_list = getattr(merged, list_field) or []
            enrich_list = getattr(enrichment, list_field) or []
            combined = list(set(base_list + enrich_list))  # Remove duplicates
            setattr(merged, list_field, combined)
        
        # Use higher citation counts
        merged.citation_count = max(merged.citation_count, enrichment.citation_count)
        merged.influential_citation_count = max(merged.influential_citation_count, enrichment.influential_citation_count)
        
        return merged
    
    def _calculate_combined_quality_score(self, metadata: EnhancedMetadata) -> float:
        """Calculate comprehensive quality score"""
        score = 0.0
        
        # Citation metrics (40% of score)
        if metadata.citation_count > 0:
            score += min(metadata.citation_count / 100, 0.25)
        if metadata.influential_citation_count > 0:
            score += min(metadata.influential_citation_count / 50, 0.15)
        
        # Content completeness (30% of score)
        if metadata.abstract and len(metadata.abstract) > 100:
            score += 0.1
        if metadata.keywords and len(metadata.keywords) >= 3:
            score += 0.05
        if metadata.fields_of_study and len(metadata.fields_of_study) >= 2:
            score += 0.05
        if metadata.pdf_urls:
            score += 0.1
        
        # Venue quality (20% of score)
        if metadata.venue:
            venue_lower = metadata.venue.lower()
            if any(top in venue_lower for top in ['nature', 'science', 'cell']):
                score += 0.2
            elif any(good in venue_lower for good in ['ieee', 'acm', 'springer']):
                score += 0.15
            elif metadata.venue_type == 'journal':
                score += 0.1
            elif metadata.venue_type == 'conference':
                score += 0.08
        
        # Recency bonus (10% of score)
        if metadata.published:
            try:
                year = int(metadata.published[:4])
                if year >= 2020:
                    score += 0.1
                elif year >= 2015:
                    score += 0.05
            except (ValueError, IndexError):
                pass
        
        return min(score, 1.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get metadata orchestrator statistics"""
        return self.stats.copy()

# Example usage
async def main():
    """Example usage of enhanced metadata sources"""
    
    # Initialize orchestrator
    orchestrator = EnhancedMetadataOrchestrator(
        semantic_scholar_key=None,  # Add your API key
        openalex_email="your-email@domain.com"  # Add your email for polite pool
    )
    
    # Search for papers
    print("Searching for papers on 'neural networks'...")
    results = await orchestrator.comprehensive_search("neural networks", max_results=10)
    
    print(f"Found {len(results)} papers:")
    for i, paper in enumerate(results[:3], 1):
        print(f"\n{i}. {paper.title}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        print(f"   Year: {paper.published[:4] if paper.published else 'Unknown'}")
        print(f"   Citations: {paper.citation_count}")
        print(f"   Quality Score: {paper.quality_score:.3f}")
        print(f"   Venue: {paper.venue}")
        print(f"   Open Access: {paper.open_access}")
        if paper.fields_of_study:
            print(f"   Fields: {', '.join(paper.fields_of_study[:3])}")
    
    # Enrich a paper with more data
    if results:
        print(f"\nEnriching first paper...")
        enriched = await orchestrator.enrich_metadata(results[0])
        print(f"Abstract length: {len(enriched.abstract) if enriched.abstract else 0} chars")
        print(f"PDF URLs: {len(enriched.pdf_urls)}")
        print(f"Enhanced quality score: {enriched.quality_score:.3f}")
    
    # Show statistics
    stats = orchestrator.get_statistics()
    print(f"\nStatistics:")
    print(f"  Queries: {stats['queries']}")
    print(f"  Semantic Scholar hits: {stats['semantic_scholar_hits']}")
    print(f"  OpenAlex hits: {stats['openalex_hits']}")
    print(f"  Combined results: {stats['combined_results']}")

if __name__ == "__main__":
    asyncio.run(main())