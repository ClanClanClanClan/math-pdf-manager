"""
Enhanced Grobid Client with Fallback Integration

Production-ready Grobid client that gracefully handles:
- Grobid service availability
- Fallback to local extraction methods
- Proper error handling and logging
"""

import requests
import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class GrobidClient:
    """Enhanced Grobid client with intelligent fallbacks"""
    
    def __init__(self, 
                 grobid_server: str = "http://localhost:8070",
                 timeout: int = 30,
                 max_retries: int = 3):
        self.grobid_server = grobid_server.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self._service_available = None
        self._last_check = 0
        self._check_interval = 300  # 5 minutes
        
    def is_available(self) -> bool:
        """Check if Grobid service is available with caching"""
        current_time = time.time()
        
        # Use cached result if recent
        if (self._service_available is not None and 
            current_time - self._last_check < self._check_interval):
            return self._service_available
        
        try:
            response = requests.get(
                f"{self.grobid_server}/api/isalive",
                timeout=5
            )
            self._service_available = response.status_code == 200
            
        except requests.RequestException:
            self._service_available = False
            
        self._last_check = current_time
        
        if self._service_available:
            logger.info("✅ Grobid service is available")
        else:
            logger.warning("⚠️ Grobid service not available - using fallback methods")
            
        return self._service_available
    
    def process_pdf(self, pdf_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Process PDF with Grobid or fallback to local extraction"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None
            
        # Try Grobid service first
        if self.is_available():
            result = self._process_with_grobid(pdf_path)
            if result:
                return result
                
        # Fallback to local extraction
        logger.info("Using fallback extraction method")
        return self._process_with_fallback(pdf_path)
    
    def _process_with_grobid(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """Process PDF using Grobid service"""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                data = {
                    'consolidateHeader': '1',
                    'consolidateCitations': '1'
                }
                
                response = requests.post(
                    f"{self.grobid_server}/api/processFulltextDocument",
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Grobid processed: {pdf_path.name}")
                    return self._parse_grobid_response(response.text)
                else:
                    logger.warning(f"Grobid failed with status {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Grobid processing failed: {e}")
            return None
    
    def _process_with_fallback(self, pdf_path: Path) -> Dict[str, Any]:
        """Fallback processing using existing extractors"""
        try:
            # Use existing PDF processing infrastructure
            try:
                from pdf_processing.extractors import (
                    AdvancedArxivExtractor,
                    AdvancedJournalExtractor,
                    AdvancedSSRNExtractor
                )
            except ImportError:
                from pdf_processing.extractors import (
                    AdvancedArxivExtractor,
                    AdvancedJournalExtractor,
                    AdvancedSSRNExtractor
                )
            
            # Simple text extraction for fallback
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            text_blocks = []
            full_text = ""
            
            for page_num in range(min(3, len(doc))):  # First 3 pages
                page = doc[page_num]
                text = page.get_text()
                full_text += text + "\n"
                
                # Create text blocks (simplified)
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:
                        block_text = ""
                        for line in block["lines"]:
                            for span in line["spans"]:
                                block_text += span["text"] + " "
                        if block_text.strip():
                            text_blocks.append({
                                "text": block_text.strip(),
                                "bbox": block.get("bbox", [0, 0, 0, 0])
                            })
            
            doc.close()
            
            # Try different extractors
            extractors = [
                AdvancedArxivExtractor(),
                AdvancedJournalExtractor(),
                AdvancedSSRNExtractor()
            ]
            
            best_result = {"title": "", "authors": "", "confidence": 0.0}
            
            for extractor in extractors:
                try:
                    title, title_conf = extractor.extract_title(full_text, text_blocks)
                    authors, author_conf = extractor.extract_authors(full_text, text_blocks)
                    
                    confidence = (title_conf + author_conf) / 2
                    if confidence > best_result["confidence"]:
                        best_result = {
                            "title": title or "",
                            "authors": authors or "",
                            "confidence": confidence,
                            "extractor": extractor.__class__.__name__
                        }
                        
                except Exception as e:
                    logger.debug(f"Extractor {extractor.__class__.__name__} failed: {e}")
                    continue
            
            logger.info(f"Fallback extraction completed with confidence: {best_result['confidence']:.2f}")
            return best_result
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return {
                "title": "Unknown Title",
                "authors": "Unknown Authors", 
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _parse_grobid_response(self, xml_response: str) -> Dict[str, Any]:
        """Parse Grobid XML response"""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_response)
            
            # Extract title
            title_elem = root.find(".//title[@level='a']")
            title = title_elem.text if title_elem is not None else ""
            
            # Extract authors
            authors = []
            for author in root.findall(".//author"):
                forename = author.find(".//forename")
                surname = author.find(".//surname")
                
                if forename is not None and surname is not None:
                    authors.append(f"{forename.text} {surname.text}")
                elif surname is not None:
                    authors.append(surname.text)
            
            # Extract abstract
            abstract_elem = root.find(".//abstract")
            abstract = abstract_elem.text if abstract_elem is not None else ""
            
            return {
                "title": title.strip(),
                "authors": ", ".join(authors),
                "abstract": abstract.strip(),
                "confidence": 0.95,  # High confidence for Grobid
                "source": "Grobid"
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Grobid response: {e}")
            return {
                "title": "Parse Error",
                "authors": "Unknown",
                "confidence": 0.0,
                "error": str(e)
            }


# Global instance for easy access
grobid_client = GrobidClient()


def extract_with_grobid(pdf_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Convenience function for Grobid extraction"""
    return grobid_client.process_pdf(pdf_path)


# Backward compatibility
class _FakeGrobidClient:
    """Fake Grobid client for testing when service unavailable"""
    
    def process_fulltext_document(self, *args, **kwargs):
        logger.info("Using fake Grobid client for testing")
        return {
            "title": "Sample Title (Fake Grobid)",
            "authors": [{"first": "John", "last": "Doe"}],
            "confidence": 0.1
        }
    
    def is_available(self):
        return False