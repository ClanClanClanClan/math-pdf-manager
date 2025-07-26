# Detailed Security Audit Report

**Date:** July 20, 2025  
**Tool:** Bandit v1.8.6  
**Scope:** src/ directory

## High Severity Issues (2)

### 1. Weak MD5 Hash Usage
**Location:** `src/pdf_processing/parsers/base_parser.py:273`  
**Code:**
```python
file_hash=hashlib.md5(pdf_file.read_bytes()).hexdigest()
```
**Risk:** MD5 is cryptographically broken and should not be used for security purposes.  
**CWE:** CWE-327 (Use of a Broken or Risky Cryptographic Algorithm)  
**Fix:** Replace with SHA256:
```python
file_hash=hashlib.sha256(pdf_file.read_bytes()).hexdigest()
```

### 2. Jinja2 XSS Vulnerability
**Location:** `src/reporter.py:260`  
**Code:**
```python
tpl = Environment().from_string(_BUNDLED_TEMPLATE)
```
**Risk:** Jinja2 autoescape is disabled by default, allowing XSS attacks.  
**CWE:** CWE-94 (Code Injection)  
**Fix:** Enable autoescape:
```python
tpl = Environment(autoescape=True).from_string(_BUNDLED_TEMPLATE)
```

## Medium Severity Issues (14)

### 1. URL Open Without Scheme Validation (3 instances)
**Locations:**
- `src/api/arxiv_client.py:71`
- `src/api/arxiv_client.py:123`
- `src/pdf_processing/extractors.py:826`

**Risk:** Could allow file:// or other unexpected URL schemes.  
**Fix:** Validate URL schemes before opening:
```python
if not url.startswith(('http://', 'https://')):
    raise ValueError("Only HTTP(S) URLs allowed")
response = urllib.request.urlopen(url)
```

### 2. XML Parsing Vulnerabilities (4 instances)
**Locations:**
- `src/metadata_fetcher.py:67`
- `src/pdf_processing/extractors.py:38`
- `src/utils/security.py:222`
- `src/utils/security.py:228`
- `src/utils/security.py:266`

**Risk:** XML bombs, XXE attacks, billion laughs attack.  
**Fix:** Use defusedxml:
```python
import defusedxml.ElementTree as ET
root = ET.fromstring(xml_string)
```

### 3. Hugging Face Unsafe Downloads (5 instances)
**Locations:**
- `src/pdf-meta-llm/scripts/finetune.py:53`
- `src/pdf-meta-llm/scripts/finetune.py:76`
- `src/pdf-meta-llm/scripts/finetune.py:94`
- `src/pdf-meta-llm/scripts/predict.py:64`
- `src/pdf-meta-llm/scripts/predict.py:65`

**Risk:** Could download malicious models without version pinning.  
**Fix:** Pin model revisions:
```python
model = AutoModel.from_pretrained("model-name", revision="specific-commit-hash")
```

### 4. Insecure Temp Directory Usage
**Location:** `src/core/security/secure_file_ops.py:30`  
**Risk:** Hardcoded /tmp usage could be predictable.  
**Fix:** Use tempfile module:
```python
import tempfile
temp_dir = tempfile.mkdtemp()
```

## Low Severity Issues (10)

These are primarily:
- Import order suggestions
- String formatting recommendations
- General code quality improvements

## Recommendations

1. **Immediate Actions:**
   - Replace MD5 with SHA256
   - Enable Jinja2 autoescape
   - Add URL scheme validation
   - Switch to defusedxml for all XML parsing

2. **Security Best Practices:**
   - Pin all external model versions
   - Use secure temp file creation
   - Implement input validation for all external data
   - Add security headers for any web-facing components

3. **Ongoing Security:**
   - Run security scans in CI/CD pipeline
   - Keep dependencies updated
   - Regular security audits
   - Security training for developers