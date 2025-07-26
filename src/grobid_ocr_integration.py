#!/usr/bin/env python3
"""
FIXED Grobid & OCR Integration for Ultra-Enhanced PDF Parser
Simplified and more robust implementation with enhanced client
"""

import requests
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from dataclasses import dataclass, field

# Import enhanced Grobid client
try:
    from .core.grobid_client import grobid_client, extract_with_grobid
except ImportError:
    try:
        from core.grobid_client import grobid_client, extract_with_grobid
    except ImportError:
        # Fallback - create minimal client if import fails
        grobid_client = None
        extract_with_grobid = None

try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
    
try:
    from utils.security import SecureXMLParser
except ImportError:
    SecureXMLParser = None

# OCR dependencies with better error handling
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# PDF to image conversion
try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GrobidMetadata:
    """Metadata extracted by Grobid"""
    title: str = ""
    authors: List[Dict[str, str]] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    references: List[Dict[str, str]] = field(default_factory=list)
    doi: str = ""
    journal: str = ""
    volume: str = ""
    pages: str = ""
    year: str = ""
    confidence: float = 0.0
    processing_time: float = 0.0


@dataclass
class OCRMetadata:
    """Metadata extracted via OCR"""
    text: str = ""
    confidence: float = 0.0
    language: str = "eng"
    pages_processed: int = 0
    processing_time: float = 0.0
    method: str = "tesseract"
    image_preprocessing: List[str] = field(default_factory=list)


class GrobidClient:
    """Simplified Grobid client"""
    
    def __init__(self, grobid_url: str = "http://localhost:8070", timeout: int = 300):
        """Initialize Grobid client"""
        self.grobid_url = grobid_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Test connection
        self.is_available = self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test if Grobid service is available"""
        try:
            response = self.session.get(
                f"{self.grobid_url}/api/isalive", 
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Grobid connection test failed: {e}")
            return False
    
    def extract_metadata(self, pdf_path: str) -> GrobidMetadata:
        """Extract metadata from PDF using Grobid"""
        if not self.is_available:
            logger.warning("Grobid service not available")
            return GrobidMetadata()
        
        start_time = time.time()
        
        try:
            # Process header only for simplicity
            header_data = self._process_header(pdf_path)
            
            # Create metadata from results
            metadata = self._create_metadata_from_results(header_data)
            metadata.processing_time = time.time() - start_time
            
            return metadata
            
        except Exception as e:
            logger.error(f"Grobid processing failed: {e}")
            return GrobidMetadata(processing_time=time.time() - start_time)
    
    def _process_header(self, pdf_path: str) -> Dict[str, Any]:
        """Process PDF header with Grobid"""
        url = f"{self.grobid_url}/api/processHeaderDocument"
        
        try:
            with open(pdf_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                data = {'consolidateHeader': '1'}
                
                response = self.session.post(
                    url, 
                    files=files, 
                    data=data, 
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return self._parse_grobid_xml(response.text)
                else:
                    logger.warning(f"Grobid header processing failed: {response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"Grobid request failed: {e}")
            return {}
    
    def _parse_grobid_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse Grobid XML output (simplified)"""
        try:
            root = SecureXMLParser.parse_string(xml_content)
            
            # Define namespaces
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            result = {}
            
            # Extract title
            title_elem = root.find('.//tei:titleStmt/tei:title', ns)
            if title_elem is not None and title_elem.text:
                result['title'] = title_elem.text.strip()
            
            # Extract authors (simplified)
            authors = []
            author_elems = root.findall('.//tei:sourceDesc//tei:author', ns)
            
            for author_elem in author_elems:
                author_info = {}
                
                # Personal name
                persname = author_elem.find('.//tei:persName', ns)
                if persname is not None:
                    forename = persname.find('.//tei:forename', ns)
                    surname = persname.find('.//tei:surname', ns)
                    
                    if forename is not None and surname is not None:
                        author_info['firstname'] = forename.text or ""
                        author_info['lastname'] = surname.text or ""
                        author_info['fullname'] = f"{forename.text} {surname.text}".strip()
                
                if author_info:
                    authors.append(author_info)
            
            result['authors'] = authors
            
            # Extract abstract
            abstract_elem = root.find('.//tei:abstract/tei:div/tei:p', ns)
            if abstract_elem is not None and abstract_elem.text:
                result['abstract'] = abstract_elem.text.strip()
            
            return result
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse Grobid XML: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error processing Grobid XML: {e}")
            return {}
    
    def _create_metadata_from_results(self, data: Dict) -> GrobidMetadata:
        """Create GrobidMetadata from parsed results"""
        metadata = GrobidMetadata()
        
        metadata.title = data.get('title', '')
        metadata.authors = data.get('authors', [])
        metadata.abstract = data.get('abstract', '')
        
        # Calculate confidence based on extracted fields
        confidence_factors = [
            1.0 if metadata.title else 0.0,
            1.0 if metadata.authors else 0.0,
            0.5 if metadata.abstract else 0.0,
        ]
        
        metadata.confidence = sum(confidence_factors) / len(confidence_factors)
        
        return metadata


class AdvancedOCRProcessor:
    """Simplified OCR processor"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """Initialize OCR processor"""
        self.is_available = TESSERACT_AVAILABLE and PDF2IMAGE_AVAILABLE
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Test Tesseract availability
        if self.is_available:
            try:
                # More robust version check
                if hasattr(pytesseract, 'get_tesseract_version'):
                    pytesseract.get_tesseract_version()
                else:
                    # Fallback - test with a simple command
                    import subprocess
                    subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
            except Exception as e:
                logger.warning(f"Tesseract not properly configured: {e}")
                self.is_available = False
    
    def extract_text_from_pdf(self, pdf_path: str, language: str = 'eng',
                             max_pages: int = 3, dpi: int = 200) -> OCRMetadata:
        """Extract text from PDF using OCR (simplified)"""
        if not self.is_available:
            logger.warning("OCR not available")
            return OCRMetadata()
        
        start_time = time.time()
        
        try:
            # Convert PDF to images (limited pages for performance)
            images = pdf2image.convert_from_path(
                pdf_path, 
                dpi=dpi, 
                first_page=1, 
                last_page=min(max_pages, 3),  # Limit to 3 pages
                fmt='PNG'
            )
            
            extracted_texts = []
            total_confidence = 0.0
            
            for i, image in enumerate(images):
                logger.debug(f"Processing page {i+1}/{len(images)} with OCR")
                
                # Simple preprocessing
                processed_image = self._simple_preprocess_image(image)
                
                # Extract text
                try:
                    ocr_data = pytesseract.image_to_data(
                        processed_image, 
                        lang=language, 
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # Filter text with reasonable confidence
                    page_text = []
                    confidences = []
                    
                    for j in range(len(ocr_data['text'])):
                        text = ocr_data['text'][j].strip()
                        confidence = int(ocr_data['conf'][j])
                        
                        if text and confidence > 20:  # Lower threshold
                            page_text.append(text)
                            confidences.append(confidence)
                    
                    if page_text:
                        extracted_texts.append(' '.join(page_text))
                        if confidences:
                            total_confidence += sum(confidences) / len(confidences)
                
                except Exception as e:
                    logger.debug(f"OCR failed for page {i+1}: {e}")
                    continue
            
            # Combine all text
            full_text = '\n\n'.join(extracted_texts)
            
            # Calculate average confidence
            avg_confidence = (total_confidence / len(images)) / 100.0 if images else 0.0
            
            metadata = OCRMetadata(
                text=full_text,
                confidence=avg_confidence,
                language=language,
                pages_processed=len(images),
                processing_time=time.time() - start_time,
                method="tesseract",
                image_preprocessing=["simple_preprocess"]
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return OCRMetadata(
                processing_time=time.time() - start_time,
                method="tesseract_failed"
            )
    
    def _simple_preprocess_image(self, image: "Image.Image") -> "Image.Image":
        """Simple image preprocessing for OCR"""
        try:
            # Convert to numpy array
            img_array = np.array(image)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Simple thresholding
            _, img_array = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(img_array)
            
            return processed_image
            
        except Exception as e:
            logger.debug(f"Image preprocessing failed: {e}")
            return image  # Return original if preprocessing fails


class HybridExtractor:
    """Simplified hybrid extractor"""
    
    def __init__(self, grobid_url: str = "http://localhost:8070", 
                 tesseract_path: Optional[str] = None):
        """Initialize hybrid extractor"""
        self.grobid_client = GrobidClient(grobid_url)
        self.ocr_processor = AdvancedOCRProcessor(tesseract_path)
        
        logger.info("Hybrid extractor initialized:")
        logger.info(f"  Grobid available: {self.grobid_client.is_available}")
        logger.info(f"  OCR available: {self.ocr_processor.is_available}")
    
    def extract_metadata_hybrid(self, pdf_path: str, use_ocr_fallback: bool = True,
                               ocr_language: str = 'eng') -> Dict[str, Any]:
        """Extract metadata using hybrid approach (simplified)"""
        results = {
            'pdf_path': pdf_path,
            'extraction_methods': [],
            'grobid_results': None,
            'ocr_results': None,
            'combined_metadata': {},
            'confidence_scores': {},
            'processing_times': {},
            'recommendations': []
        }
        
        start_time = time.time()
        
        # Try Grobid first
        if self.grobid_client.is_available:
            logger.info("Attempting Grobid extraction...")
            try:
                grobid_metadata = self.grobid_client.extract_metadata(pdf_path)
                results['grobid_results'] = grobid_metadata
                results['extraction_methods'].append('grobid')
                results['processing_times']['grobid'] = grobid_metadata.processing_time
                
                # Evaluate Grobid results
                if grobid_metadata.title and grobid_metadata.confidence > 0.3:
                    results['combined_metadata']['title'] = grobid_metadata.title
                    results['combined_metadata']['grobid_authors'] = grobid_metadata.authors
                    results['confidence_scores']['grobid'] = grobid_metadata.confidence
                    
                    logger.info(f"✓ Grobid extraction successful (confidence: {grobid_metadata.confidence:.2f})")
                else:
                    logger.info("✗ Grobid extraction had low confidence")
                    results['recommendations'].append("Consider OCR for scanned document")
                    
            except Exception as e:
                logger.warning(f"Grobid extraction failed: {e}")
                results['recommendations'].append("Check Grobid service status")
        
        # Use OCR if needed
        should_use_ocr = (
            use_ocr_fallback and 
            self.ocr_processor.is_available and
            (not results.get('grobid_results') or 
             results.get('grobid_results', GrobidMetadata()).confidence < 0.3)
        )
        
        if should_use_ocr:
            logger.info("Attempting OCR extraction...")
            try:
                ocr_metadata = self.ocr_processor.extract_text_from_pdf(
                    pdf_path, language=ocr_language
                )
                results['ocr_results'] = ocr_metadata
                results['extraction_methods'].append('ocr')
                results['processing_times']['ocr'] = ocr_metadata.processing_time
                
                if ocr_metadata.text and len(ocr_metadata.text) > 50:
                    results['combined_metadata']['ocr_text'] = ocr_metadata.text
                    results['confidence_scores']['ocr'] = ocr_metadata.confidence
                    
                    logger.info(f"✓ OCR extraction successful (confidence: {ocr_metadata.confidence:.2f})")
                else:
                    logger.info("✗ OCR extraction yielded insufficient text")
                    
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")
        
        # Combine results (simplified)
        final_metadata = self._simple_combine_results(results)
        results['combined_metadata'].update(final_metadata)
        
        results['total_processing_time'] = time.time() - start_time
        
        # Generate simple recommendations
        self._generate_simple_recommendations(results)
        
        return results
    
    def _simple_combine_results(self, results: Dict[str, Any]) -> Dict[str, str]:
        """Simple result combination"""
        combined = {}
        
        # Title selection: Grobid > fallback
        if results.get('grobid_results') and results['grobid_results'].title:
            combined['title'] = results['grobid_results'].title
            combined['title_source'] = 'grobid'
        else:
            combined['title'] = "Unknown Title"
            combined['title_source'] = 'none'
        
        # Authors selection
        if results.get('grobid_results') and results['grobid_results'].authors:
            # Format Grobid authors
            author_names = []
            for author in results['grobid_results'].authors:
                if 'fullname' in author:
                    author_names.append(author['fullname'])
                elif 'firstname' in author and 'lastname' in author:
                    author_names.append(f"{author['firstname']} {author['lastname']}")
            
            if author_names:
                combined['authors'] = ', '.join(author_names)
                combined['authors_source'] = 'grobid'
        else:
            combined['authors'] = "Unknown"
            combined['authors_source'] = 'none'
        
        return combined
    
    def _generate_simple_recommendations(self, results: Dict[str, Any]):
        """Generate simple recommendations"""
        recommendations = results.get('recommendations', [])
        
        # Check extraction success
        if not results['extraction_methods']:
            recommendations.append("No extraction methods succeeded")
        
        # Grobid specific recommendations
        if 'grobid' not in results['extraction_methods'] and self.grobid_client.is_available:
            recommendations.append("Grobid extraction failed")
        elif not self.grobid_client.is_available:
            recommendations.append("Install and start Grobid service for better parsing")
        
        # OCR specific recommendations
        if 'ocr' in results['extraction_methods']:
            recommendations.append("Document processed via OCR - may be scanned image")
        elif not self.ocr_processor.is_available:
            recommendations.append("Install Tesseract for scanned document support")
        
        results['recommendations'] = recommendations


if __name__ == "__main__":
    # Simple demo
    import argparse
    
    parser = argparse.ArgumentParser(description="Fixed Grobid & OCR Integration Demo")
    parser.add_argument("pdf_file", help="PDF file to process")
    parser.add_argument("--grobid-url", default="http://localhost:8070", 
                       help="Grobid service URL")
    parser.add_argument("--ocr-language", default="eng", 
                       help="OCR language code")
    
    args = parser.parse_args()
    
    if not Path(args.pdf_file).exists():
        print(f"Error: File not found: {args.pdf_file}")
        exit(1)
    
    print(f"🔬 Processing: {args.pdf_file}")
    print("=" * 60)
    
    # Test hybrid extraction
    print("Testing hybrid extraction...")
    hybrid = HybridExtractor(args.grobid_url)
    
    results = hybrid.extract_metadata_hybrid(
        args.pdf_file, 
        ocr_language=args.ocr_language
    )
    
    print(f"Methods used: {', '.join(results['extraction_methods'])}")
    print(f"Total processing time: {results['total_processing_time']:.2f}s")
    print()
    
    combined = results['combined_metadata']
    print(f"Title: {combined.get('title', 'Unknown')} (source: {combined.get('title_source', 'unknown')})")
    print(f"Authors: {combined.get('authors', 'Unknown')} (source: {combined.get('authors_source', 'unknown')})")
    
    if results['recommendations']:
        print("\n💡 Recommendations:")
        for rec in results['recommendations']:
            print(f"  - {rec}")
    
    print("\n✅ Processing complete")