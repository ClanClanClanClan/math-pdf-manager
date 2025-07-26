# SIAM Publisher System - Implementation Specification

## 🎯 **Implementation Priority: NEXT TARGET**

**Status**: 🚧 Ready for Implementation  
**Priority**: High (Next after IEEE completion)  
**Template**: Use proven IEEE architecture pattern  
**Timeline**: Next development session  

---

## 📋 **SIAM Overview**

### **Publisher Details**
- **Full Name**: Society for Industrial and Applied Mathematics
- **URL**: https://epubs.siam.org/
- **Focus**: Applied mathematics, computational science, data science
- **Access Model**: Subscription-based with institutional access
- **Paper Types**: Journal articles, conference proceedings, books

### **Why SIAM is Next Priority**
1. **High-Value Target**: Major applied mathematics publisher
2. **Institutional Access**: Likely covered by ETH Zurich subscription
3. **Clear Architecture**: Can follow proven IEEE authentication pattern
4. **Research Relevance**: Critical for applied mathematics research

---

## 🏗️ **Implementation Architecture**

### **🔌 Publisher Interface Implementation**

Following the proven IEEE pattern:

```python
class SIAMPublisher(PublisherInterface):
    """SIAM (Society for Industrial and Applied Mathematics) publisher"""
    
    @property
    def publisher_name(self) -> str:
        return "SIAM"
    
    @property  
    def base_url(self) -> str:
        return "https://epubs.siam.org"
    
    def can_handle(self, identifier: str) -> bool:
        # Handle SIAM DOIs: 10.1137/...
        # Handle SIAM URLs: epubs.siam.org/...
        
    def authenticate(self) -> bool:
        # Implement institutional authentication
        # Follow IEEE pattern for ETH Zurich login
        
    def download_paper(self, identifier: str) -> DownloadResult:
        # Use authenticated session to download PDF
        # Follow IEEE cookie extraction pattern
```

### **🎯 Implementation Strategy**

#### **Phase 1: Research & Analysis** 
1. **Manual Testing**: Test SIAM authentication flow manually
2. **DOM Analysis**: Inspect SIAM login interface and modals
3. **Network Analysis**: Understand authentication endpoints
4. **PDF Access**: Determine PDF download mechanisms

#### **Phase 2: Authentication Implementation**
1. **Institution Login**: Implement ETH Zurich authentication for SIAM
2. **Session Management**: Extract and manage authentication cookies  
3. **Error Handling**: Robust error handling for authentication failures
4. **Security**: Proper credential handling and security measures

#### **Phase 3: Download Implementation**
1. **PDF Access**: Implement authenticated PDF download
2. **Metadata Extraction**: Extract paper metadata from SIAM pages
3. **DOI Resolution**: Handle SIAM DOI formats (10.1137/...)
4. **Quality Assurance**: Validate downloaded content

#### **Phase 4: Testing & Validation**
1. **Unit Tests**: Comprehensive testing of SIAM components
2. **Integration Tests**: Test with real SIAM papers
3. **Error Scenarios**: Test authentication failures, network issues
4. **Performance**: Optimize for speed and reliability

---

## 🔍 **SIAM Technical Analysis**

### **🌐 URL Patterns**

SIAM uses predictable URL patterns:

```
Journal Articles:
https://epubs.siam.org/doi/10.1137/[paper-id]

Conference Proceedings: 
https://epubs.siam.org/doi/book/10.1137/[book-id]

PDF Access:
https://epubs.siam.org/doi/pdf/10.1137/[paper-id]
```

### **🔑 DOI Pattern Recognition**

```python
SIAM_DOI_PATTERN = r"10\.1137\/\w+"

def is_siam_doi(doi: str) -> bool:
    """Check if DOI belongs to SIAM"""
    return re.match(SIAM_DOI_PATTERN, doi) is not None

def extract_siam_paper_id(doi: str) -> str:
    """Extract SIAM paper ID from DOI"""
    # Extract ID after 10.1137/
    return doi.split("10.1137/")[1]
```

### **🔐 Authentication Flow (Predicted)**

Based on common academic publisher patterns:

```
1. Navigate to SIAM paper URL
   https://epubs.siam.org/doi/10.1137/[paper-id]
   
2. Detect paywall/login requirement
   Look for "Sign In" or "Access through institution" links
   
3. Institutional login
   Click institutional access (likely similar to IEEE)
   
4. ETH Zurich authentication
   Use existing ETH credentials from IEEE implementation
   
5. Session extraction
   Extract authentication cookies from browser
   
6. PDF download  
   Use authenticated session to download PDF
```

---

## 💻 **Implementation Template**

### **🏗️ Basic Structure**

```python
#!/usr/bin/env python3
"""
publishers/siam_publisher.py - SIAM Publisher Implementation
Based on proven IEEE architecture pattern
"""

import requests
import re
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from . import PublisherInterface, DownloadResult, publisher_registry
from ..auth.manager import AuthenticationManager
from ..core.exceptions import AuthenticationError, DownloadError


class SIAMPublisher(PublisherInterface):
    """SIAM (Society for Industrial and Applied Mathematics) publisher"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.auth_manager = AuthenticationManager()
        
    @property
    def publisher_name(self) -> str:
        return "SIAM"
    
    @property
    def base_url(self) -> str:
        return "https://epubs.siam.org"
    
    def can_handle(self, identifier: str) -> bool:
        """Check if this publisher can handle the given identifier"""
        # SIAM DOI pattern: 10.1137/...
        if "10.1137/" in identifier:
            return True
            
        # SIAM URL patterns
        if "epubs.siam.org" in identifier:
            return True
            
        return False
    
    def authenticate(self) -> bool:
        """Authenticate with SIAM using institutional login"""
        try:
            # Follow IEEE authentication pattern
            # 1. Initialize browser session
            # 2. Navigate to SIAM institutional login
            # 3. Use ETH Zurich authentication 
            # 4. Extract session cookies
            
            self.logger.info("Starting SIAM authentication...")
            
            # TODO: Implement using IEEE pattern as template
            
            return True
            
        except Exception as e:
            self.logger.error(f"SIAM authentication failed: {e}")
            raise AuthenticationError(f"SIAM authentication failed: {e}")
    
    def download_paper(self, identifier: str) -> DownloadResult:
        """Download paper from SIAM"""
        try:
            self.logger.info(f"Downloading SIAM paper: {identifier}")
            
            # 1. Resolve DOI to paper ID
            paper_id = self._resolve_paper_id(identifier)
            
            # 2. Authenticate if needed
            if not self.session:
                if not self.authenticate():
                    raise AuthenticationError("SIAM authentication required")
            
            # 3. Download PDF
            pdf_url = f"{self.base_url}/doi/pdf/10.1137/{paper_id}"
            
            # TODO: Implement download using IEEE pattern
            
            return DownloadResult(
                success=True,
                file_path=None,  # TODO: Implement
                metadata={}  # TODO: Extract metadata
            )
            
        except Exception as e:
            self.logger.error(f"SIAM download failed: {e}")
            return DownloadResult(
                success=False,
                error=str(e)
            )
    
    def _resolve_paper_id(self, identifier: str) -> str:
        """Extract SIAM paper ID from identifier"""
        if "10.1137/" in identifier:
            return identifier.split("10.1137/")[1]
        
        # Handle URL formats
        # TODO: Parse SIAM URLs to extract paper ID
        
        raise ValueError(f"Cannot extract SIAM paper ID from: {identifier}")


# Register publisher
publisher_registry.register("siam", SIAMPublisher)
```

---

## 🧪 **Testing Strategy**

### **📋 Test Cases**

#### **Unit Tests**
```python
def test_siam_doi_recognition():
    """Test SIAM DOI pattern recognition"""
    publisher = SIAMPublisher()
    
    # Valid SIAM DOIs
    assert publisher.can_handle("10.1137/1.9781611972000")
    assert publisher.can_handle("10.1137/S0036144504444506")
    
    # Invalid DOIs
    assert not publisher.can_handle("10.1109/INVALID")
    assert not publisher.can_handle("arXiv:2101.00001")

def test_paper_id_extraction():
    """Test extraction of SIAM paper IDs"""
    publisher = SIAMPublisher()
    
    paper_id = publisher._resolve_paper_id("10.1137/S0036144504444506")
    assert paper_id == "S0036144504444506"
```

#### **Integration Tests**
```python
def test_siam_authentication():
    """Test SIAM institutional authentication"""
    publisher = SIAMPublisher()
    
    # Test authentication flow
    result = publisher.authenticate()
    assert result is True
    assert publisher.session is not None

def test_siam_paper_download():
    """Test downloading actual SIAM paper"""
    publisher = SIAMPublisher()
    
    # Use a known SIAM paper DOI
    test_doi = "10.1137/S0036144504444506"
    
    result = publisher.download_paper(test_doi)
    assert result.success is True
    assert result.file_path.exists()
```

### **🎯 Target Papers for Testing**

```python
SIAM_TEST_PAPERS = [
    {
        "doi": "10.1137/S0036144504444506",
        "title": "The World of Mathematical Equations", 
        "type": "journal_article"
    },
    {
        "doi": "10.1137/1.9781611972000",
        "title": "Numerical Methods Book",
        "type": "book"
    },
    {
        "doi": "10.1137/110856137", 
        "title": "Computational Mathematics Paper",
        "type": "journal_article"
    }
]
```

---

## 🔄 **Implementation Checklist**

### **🏗️ Development Tasks**

#### **Research Phase** ✅ Ready
- [ ] Manual SIAM authentication testing
- [ ] DOM structure analysis for login flows
- [ ] Network analysis of authentication endpoints
- [ ] PDF access mechanism investigation

#### **Core Implementation**
- [ ] Create `src/publishers/siam_publisher.py`
- [ ] Implement `SIAMPublisher` class following IEEE pattern
- [ ] Add SIAM DOI recognition and URL handling
- [ ] Implement institutional authentication flow

#### **Authentication System**
- [ ] ETH Zurich login for SIAM (reuse IEEE components)
- [ ] Session cookie extraction and management
- [ ] Authentication error handling
- [ ] Secure credential storage integration

#### **Download System** 
- [ ] Authenticated PDF download implementation
- [ ] Metadata extraction from SIAM pages
- [ ] File naming and storage integration
- [ ] Content validation and error handling

#### **Testing & Quality**
- [ ] Unit tests for all SIAM components
- [ ] Integration tests with real SIAM papers
- [ ] Error scenario testing (auth failures, network issues)
- [ ] Performance optimization and benchmarking

#### **Documentation**
- [ ] Update this specification with implementation details
- [ ] Add SIAM examples to usage documentation
- [ ] Create troubleshooting guide for SIAM-specific issues
- [ ] Update architecture documentation

---

## 🚀 **Success Criteria**

### **📊 Functional Requirements**
- [ ] **Authentication**: ETH Zurich institutional login working for SIAM
- [ ] **Download**: Successfully download PDFs from SIAM papers
- [ ] **Metadata**: Extract complete metadata from SIAM papers
- [ ] **Integration**: Seamless integration with existing pdfmgr CLI

### **📈 Quality Requirements**
- [ ] **Reliability**: 95%+ success rate for accessible papers
- [ ] **Performance**: < 30 second average download time
- [ ] **Security**: Pass all security validation tests
- [ ] **Error Handling**: Graceful handling of all error scenarios

### **🧪 Testing Requirements**
- [ ] **Coverage**: 90%+ test coverage for SIAM components
- [ ] **Integration**: Successfully test with 10+ different SIAM papers
- [ ] **Error Cases**: Test authentication failures, network timeouts
- [ ] **Performance**: Benchmark against IEEE performance metrics

---

## 🎯 **Next Steps**

### **🚀 Implementation Plan**

1. **Immediate (Next Session)**:
   - Start with manual SIAM authentication research
   - Analyze SIAM website structure and authentication flow
   - Create basic `SIAMPublisher` class structure

2. **Development Phase**:
   - Implement authentication using IEEE pattern as template
   - Add PDF download functionality
   - Create comprehensive test suite

3. **Testing & Integration**:
   - Test with multiple SIAM papers
   - Integrate with existing pdfmgr CLI
   - Performance optimization and error handling

4. **Documentation & Completion**:
   - Update documentation with working implementation
   - Create usage examples and troubleshooting guide
   - Prepare for Springer implementation

---

**🎯 Ready for implementation using the proven IEEE architecture as a template. The foundation is solid and the pattern is established.**

---

*This specification provides a complete roadmap for implementing SIAM publisher support following the proven IEEE pattern.*