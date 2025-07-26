#!/usr/bin/env python3
"""
High-reliability metadata retriever — v2.1.1
===========================================

Re-engineered from scratch while keeping the public API unchanged.  Highlights
---------------------------------------------------------------------------
* PEP 8/257 compliance + exhaustive type hints.
* Atomic, thread-safe JSON caching.
* Resilient HTTP layer (urllib3.Retry, handles 429/5xx, back-off).
* Unicode-safe canonicalisation (incl. ß→ss, æ→ae, œ→oe, …).
* Multiple providers: Crossref, arXiv, Google Scholar (SerpAPI & scholarly).
* Structured logging (`LOGLEVEL` env var).

All public functions exported in *__all__* match the original names.
"""
from __future__ import annotations

# ────────────────────────── std-lib ─────────────────────────────────────────
import csv
import hashlib
import json
import logging
import os
import unicodedata
import defusedxml.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

# ───────────────────────── 3rd-party ───────────────────────────────────────
import regex as re                       # full Unicode regex engine
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# ───────────────────────── optional deps (graceful fallback) ───────────────
try:
    from utils import strip_latex            # noqa: F401
except Exception:                            # pragma: no cover
    def strip_latex(text: str | None) -> str:
        """Very crude LaTeX stripping fallback."""
        if not text:
            return ""
        # Only strip LaTeX commands that are likely actual LaTeX, not random backslashes
        # Use word boundaries to avoid matching single letters that could be from other processing
        return re.sub(r"\\[A-Za-z]{2,}|[{}]", "", text)

try:
    from utils.security import SecureXMLParser
except Exception:                            # pragma: no cover
    # Fallback to regular XML parser (less secure)
    import xml.etree.ElementTree as ET
    class SecureXMLParser:
        @staticmethod
        def parse_string(xml_string):
            # Fallback XML parser with limited security (defusedxml recommended)
            return ET.fromstring(xml_string)  # nosec B314 - fallback when defusedxml unavailable

try:
    from scholarly import scholarly          # type: ignore
except Exception:                            # pragma: no cover
    scholarly = None                         # type: ignore

# ────────────────────────── logging ────────────────────────────────────────
LOGLEVEL = os.getenv("LOGLEVEL", "INFO").upper()
logging.basicConfig(
    format="[%(levelname)8s] %(name)s — %(message)s", level=LOGLEVEL
)
logger = logging.getLogger("metadata_fetcher")

# ────────────────────────── constants & regexes ────────────────────────────
CACHE_DIR: str = os.getenv("METADATA_CACHE", ".metadata_cache")

RE_DASHES = re.compile(r"[\-–—−‐]", flags=re.UNICODE)
RE_BIDI   = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\x00-\x1f]", flags=re.UNICODE)
RE_WS     = re.compile(r"\s+", flags=re.UNICODE)

_TRANSLIT_TABLE = str.maketrans(
    {
        "ß": "ss", "ẞ": "SS",
        "æ": "ae", "Æ": "AE",
        "œ": "oe", "Œ": "OE",
        "ø": "o",  "Ø": "O",
        "ł": "l",  "Ł": "L",
        # German umlauts
        "ä": "ae", "Ä": "AE",
        "ö": "oe", "Ö": "OE", 
        "ü": "ue", "Ü": "UE",
        # Spanish and other accented characters
        "á": "a", "Á": "A",
        "é": "e", "É": "E",
        "í": "i", "Í": "I",
        "ó": "o", "Ó": "O",
        "ú": "u", "Ú": "U",
        "ñ": "n", "Ñ": "N",
        "ç": "c", "Ç": "C",
        # Greek letters commonly used in mathematics
        "α": "a", "Α": "A",
        "β": "b", "Β": "B",
        "γ": "g", "Γ": "G",
        "δ": "d", "Δ": "D",
        "ε": "e", "Ε": "E",
        "ζ": "z", "Ζ": "Z",
        "η": "e", "Η": "E",
        "θ": "th", "Θ": "Th",
        "ι": "i", "Ι": "I",
        "κ": "k", "Κ": "K",
        "λ": "l", "Λ": "L",
        "μ": "m", "Μ": "M",
        "µ": "m",  # MICRO SIGN (different from Greek mu)
        "ν": "n", "Ν": "N",
        "ξ": "x", "Ξ": "X",
        "ο": "o", "Ο": "O",
        "π": "p", "Π": "P",
        "ρ": "r", "Ρ": "R",
        "σ": "s", "Σ": "S",
        "τ": "t", "Τ": "T",
        "υ": "u", "Υ": "U",
        "φ": "ph", "Φ": "Ph",
        "χ": "ch", "Χ": "Ch",
        "ψ": "ps", "Ψ": "Ps",
        "ω": "o", "Ω": "O",
    }
)

# ────────────────────────── dataclass ──────────────────────────────────────
@dataclass(slots=True)
class Metadata:
    title:      str = ""
    authors:    List[str] | None = None
    published:  str | None = None          # ISO-8601 or bare year
    DOI:        str | None = None
    arxiv_id:   str | None = None
    source:     str = ""

    # legacy helper (keeps [[YYYY,M,D]] when callers expect it)
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.published and not isinstance(self.published, list):
            try:
                y, m, d_ = (int(x) for x in self.published.split("-"))
                d["published"] = [[y, m, d_]]
            except Exception:
                pass
        return d

# ────────────────────────── .env loader ────────────────────────────────────
def _load_dotenv(path: str | Path = ".env") -> None:
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text("utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()

# ────────────────────────── canonicalisation & fuzzing ─────────────────────
def canonicalize(text: str | None) -> str:
    if not text:
        return ""
    text = strip_latex(text)
    text = text.replace("\ufeff", "")
    text = RE_DASHES.sub("-", text)
    text = RE_BIDI.sub("", text)
    text = text.translate(_TRANSLIT_TABLE)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    return RE_WS.sub(" ", text).strip()

def title_match(a: str, b: str, *, threshold: float = 0.88) -> bool:
    return SequenceMatcher(None, canonicalize(a), canonicalize(b)).ratio() >= threshold

# ────────────────────────── author helpers ─────────────────────────────────
def extract_family_given(name: str) -> Tuple[str, str]:
    if not name:
        return "", ""
    parts = [p.strip() for p in name.split(",", 1)]
    if len(parts) == 2:
        return parts[0], parts[1]
    tokens = name.split()
    if len(tokens) >= 2:
        return tokens[-1], " ".join(tokens[:-1])
    return name, ""

def given_name_initials(given: str) -> str:
    parts = re.split(r"[-\s]+", given)
    return "".join(p[0] for p in parts if p).upper()

def normalize_author(name: str) -> str:
    fam, giv = extract_family_given(name)
    # Apply canonicalization to handle accented characters
    fam = canonicalize(fam)
    giv = canonicalize(giv)
    ini = given_name_initials(giv)
    return f"{fam}, {ini}" if ini else fam

def authors_match(
    a: Sequence[str], b: Sequence[str], *, threshold: float = 0.6
) -> bool:
    A = {normalize_author(x) for x in a if x}
    B = {normalize_author(x) for x in b if x}
    if not A or not B:
        return False
    return len(A & B) / max(len(A), len(B)) >= threshold

# ────────────────────────── cache helpers ──────────────────────────────────
def _cache_dir() -> Path:
    p = Path(CACHE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p

def _cache_key(text: str) -> str:
    """Generate cache key using SHA-256 of canonicalized text."""
    return hashlib.sha256(canonicalize(text).encode()).hexdigest()

def _read_cache(key: str) -> Optional[dict]:
    f = _cache_dir() / f"{_cache_key(key)}.json"
    if f.exists():
        try:
            data = json.loads(f.read_text("utf-8"))
            # Return None for corrupted cache (non-dict data)
            return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.warning("[CACHE] read fail %s – %s", f.name, exc)
    return None

def _write_cache(key: str, payload: Mapping[str, Any]) -> None:
    _cache_dir()
    f = Path(CACHE_DIR) / f"{_cache_key(key)}.json"
    tmp = f.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
        os.replace(tmp, f)
    except Exception as exc:
        logger.warning("[CACHE] write fail %s – %s", f.name, exc)

# ────────────────────────── HTTP helpers ───────────────────────────────────
def _session(retries: int = 3, backoff: float = 1.5) -> requests.Session:
    retry_cfg = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry_cfg)
    sess = requests.Session()
    sess.headers.update({"User-Agent": "MetadataFetcher/2.1.1"})
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    return sess

def _get(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    timeout: int = 20,
    retries: int = 3,
    backoff: float = 1.5,
    verbose: bool = False,
) -> Optional[requests.Response]:
    try:
        resp = _session(retries, backoff).get(url, params=params, timeout=timeout)
        if verbose:
            logger.info("GET %s – %s", resp.url, resp.status_code)
        if resp.status_code >= 400:
            return None
        return resp
    except Exception as exc:
        logger.warning("Request error %s – %s", url, exc)
        return None

# ────────────────────────── provider: arXiv ────────────────────────────────
def query_arxiv(arxiv_id: str, *, verbose: bool = False) -> Optional[Dict[str, Any]]:
    key = f"arxiv:{arxiv_id}"
    if (c := _read_cache(key)) is not None:
        return c

    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    resp = _get(url, timeout=15, retries=2, backoff=5, verbose=verbose)
    if not resp:
        return None

    ns = {"a": "https://www.w3.org/2005/Atom"}
    try:
        entry = SecureXMLParser.parse_string(resp.text).find("a:entry", ns)
        if entry is None:
            return None
        # Extract version information
        arxiv_info = extract_arxiv_info(arxiv_id)
        
        meta = {
            "title": strip_latex(entry.findtext("a:title", default="", namespaces=ns).strip()),
            "authors": [n.text.strip() for n in entry.findall("a:author/a:name", ns)],
            "published": entry.findtext("a:published", default="", namespaces=ns)[:10],
            "updated": entry.findtext("a:updated", default="", namespaces=ns)[:10],
            "arxiv_id": arxiv_id,
            "arxiv_base_id": arxiv_info.get("id", arxiv_id),
            "arxiv_version": arxiv_info.get("version"),
            "arxiv_version_num": arxiv_info.get("version_num"),
            "source": "arxiv",
        }
        _write_cache(key, meta)
        return meta
    except Exception as exc:
        logger.warning("arXiv parse error %s – %s", arxiv_id, exc)
        return None

# ────────────────────────── provider: Crossref ─────────────────────────────
_CROSSREF_API = "https://api.crossref.org/works/"

# ────────────────────────── provider: Unpaywall ───────────────────────────
_UNPAYWALL_API = "https://api.unpaywall.org/v2/"

# ────────────────────────── subject classification ────────────────────────
# Mathematical Subject Classification (MSC 2020) primary areas
_MSC_CLASSIFICATIONS = {
    # Pure Mathematics
    "algebra": ["00", "03", "06", "08", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"],
    "analysis": ["26", "28", "30", "31", "32", "33", "34", "35", "37", "39", "40", "41", "42", "43", "44", "45", "46", "47"],
    "geometry_topology": ["14", "51", "52", "53", "54", "55", "57", "58"],
    "probability_statistics": ["60", "62"],
    "discrete_mathematics": ["05", "68"],
    "logic_foundations": ["03"],
    "number_theory": ["11"],
    # Applied Mathematics  
    "numerical_analysis": ["65"],
    "mechanics": ["70", "74", "76"],
    "mathematical_physics": ["81", "82"],
    "optimization": ["49", "90"],
    "systems_control": ["93"],
    "information_theory": ["94"],
    "economics_finance": ["91"],
    "biology_medicine": ["92"],
}

# Keywords for mathematical subject detection
_MATH_KEYWORDS = {
    "algebra": ["algebra", "algebraic", "group theory", "ring theory", "field theory", "homological", 
               "category theory", "representation theory", "lie group", "lie algebra", "polynomial", 
               "polynomials", "group", "ring", "field", "representation"],
    "analysis": ["analysis", "analytic", "differential equations", "pde", "ode", "functional analysis",
               "harmonic analysis", "complex analysis", "real analysis", "measure theory", "integration"],
    "probability_statistics": ["probability", "probabilistic", "stochastic", "random", "statistics", 
                             "statistical", "markov", "brownian", "martingale", "levy"],
    "geometry_topology": ["geometry", "geometric", "topology", "topological", "manifold", "differential geometry",
                         "algebraic geometry", "riemannian", "euclidean", "metric space"],
    "discrete_mathematics": ["graph theory", "combinatorial", "combinatorics", "discrete", "optimization",
                           "algorithm", "computational", "machine", "automaton", "computation", "recursive", 
                           "finite state", "mealy", "automata", "growth"],
    "number_theory": ["number theory", "arithmetic", "diophantine", "prime", "congruence", "modular"],
    "numerical_analysis": ["numerical", "computation", "finite element", "approximation", "algorithm"],
    "mathematical_physics": ["mathematical physics", "quantum", "statistical mechanics", "field theory"],
    "mechanics": ["mechanics", "fluid", "elasticity", "continuum", "dynamics"],
    "optimization": ["optimization", "optimal", "control", "programming", "variational"],
}

def classify_mathematical_subject(title: str, abstract: str = "") -> List[str]:
    """
    Classify a paper into mathematical subject areas based on title and abstract.
    Returns list of subject areas ordered by confidence.
    """
    if not title:
        return []
    
    # Combine title and abstract for analysis
    text = canonicalize(f"{title} {abstract}").lower()
    
    # Score each subject area
    scores = {}
    for subject, keywords in _MATH_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            # Count occurrences of each keyword
            count = text.count(keyword.lower())
            if count > 0:
                # Weight by keyword importance (longer keywords get higher weight)
                weight = len(keyword.split()) * 2 + 1
                score += count * weight
        
        if score > 0:
            scores[subject] = score
    
    # Return subjects sorted by score, with a minimum threshold
    min_score = 2  # Require at least some confidence
    return [subject for subject, score in sorted(scores.items(), 
            key=lambda x: x[1], reverse=True) if score >= min_score]

def enrich_metadata_with_subjects(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich metadata with subject classification information.
    """
    if not metadata:
        return metadata
    
    title = metadata.get("title", "")
    abstract = metadata.get("abstract", "")
    
    subjects = classify_mathematical_subject(title, abstract)
    
    if subjects:
        metadata["mathematical_subjects"] = subjects
        metadata["primary_subject"] = subjects[0] if subjects else None
        
        # Map to MSC codes if available
        msc_codes = []
        for subject in subjects:
            if subject in _MSC_CLASSIFICATIONS:
                msc_codes.extend(_MSC_CLASSIFICATIONS[subject])
        
        if msc_codes:
            metadata["msc_codes"] = list(set(msc_codes))  # Remove duplicates
    
    return metadata

# ────────────────────────── arXiv version detection ───────────────────────
def extract_arxiv_info(arxiv_id: str) -> Dict[str, Any]:
    """
    Extract arXiv ID, version, and other info from arXiv identifier.
    
    Examples:
        "2101.00001v3" -> {"id": "2101.00001", "version": "v3", "version_num": 3}
        "math.AG/0506123" -> {"id": "math.AG/0506123", "version": None, "version_num": None}
    """
    if not arxiv_id:
        return {}
    
    # Handle new format (YYMM.NNNNN[vN])
    match = re.match(r'^(\d{4}\.\d{4,5})(v(\d+))?$', arxiv_id)
    if match:
        base_id = match.group(1)
        version_str = match.group(2)  # e.g., "v3"
        version_num = int(match.group(3)) if match.group(3) else None
        return {
            "id": base_id,
            "version": version_str,
            "version_num": version_num,
            "format": "new"
        }
    
    # Handle old format (subject-class/YYMMnnn[vN])
    match = re.match(r'^([a-z-]+(?:\.[A-Z]{2})?/\d{7})(v(\d+))?$', arxiv_id)
    if match:
        base_id = match.group(1)
        version_str = match.group(2)  # e.g., "v2"
        version_num = int(match.group(3)) if match.group(3) else None
        return {
            "id": base_id,
            "version": version_str,
            "version_num": version_num,
            "format": "old"
        }
    
    # Fallback - return as-is
    return {
        "id": arxiv_id,
        "version": None,
        "version_num": None,
        "format": "unknown"
    }

def get_arxiv_versions(arxiv_id: str, *, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Get all versions of an arXiv paper.
    """
    arxiv_info = extract_arxiv_info(arxiv_id)
    base_id = arxiv_info.get("id", arxiv_id)
    
    key = f"arxiv_versions:{base_id}"
    if (c := _read_cache(key)) is not None:
        return c
    
    # Query arXiv for the base ID to get all versions
    url = f"https://export.arxiv.org/api/query?id_list={base_id}"
    resp = _get(url, timeout=15, retries=2, backoff=5, verbose=verbose)
    if not resp:
        return []
    
    ns = {"a": "https://www.w3.org/2005/Atom"}
    try:
        root = SecureXMLParser.parse_string(resp.text)
        entries = root.findall("a:entry", ns)
        
        versions = []
        for entry in entries:
            # Extract version info from the entry
            entry_id = entry.findtext("a:id", default="", namespaces=ns)
            arxiv_match = re.search(r'arxiv\.org/abs/(.+)$', entry_id)
            if arxiv_match:
                full_id = arxiv_match.group(1)
                version_info = extract_arxiv_info(full_id)
                
                versions.append({
                    "arxiv_id": full_id,
                    "base_id": version_info.get("id", full_id),
                    "version": version_info.get("version"),
                    "version_num": version_info.get("version_num"),
                    "title": strip_latex(entry.findtext("a:title", default="", namespaces=ns).strip()),
                    "published": entry.findtext("a:published", default="", namespaces=ns)[:10],
                    "updated": entry.findtext("a:updated", default="", namespaces=ns)[:10],
                })
        
        # Sort by version number
        versions.sort(key=lambda x: x.get("version_num", 0) or 0)
        
        _write_cache(key, versions)
        return versions
        
    except Exception as exc:
        logger.warning("arXiv versions error %s – %s", base_id, exc)
        return []

def detect_arxiv_updates(current_arxiv_id: str, *, verbose: bool = False) -> Dict[str, Any]:
    """
    Check if there are newer versions of an arXiv paper.
    """
    if not current_arxiv_id:
        return {"has_updates": False, "current_version": None, "latest_version": None}
    
    current_info = extract_arxiv_info(current_arxiv_id)
    current_version = current_info.get("version_num") or 1  # Default to 1 if None
    
    versions = get_arxiv_versions(current_arxiv_id, verbose=verbose)
    if not versions:
        return {"has_updates": False, "current_version": current_version, "latest_version": None}
    
    # Handle case where versions might be a dict (wrong cache data)
    if isinstance(versions, dict):
        return {"has_updates": False, "current_version": current_version, "latest_version": None}
    
    latest_version = max((v.get("version_num") or 1) for v in versions)
    latest_arxiv_id = next(
        (v["arxiv_id"] for v in versions if (v.get("version_num") or 1) == latest_version),
        current_arxiv_id
    )
    
    return {
        "has_updates": latest_version > current_version,
        "current_version": current_version,
        "latest_version": latest_version,
        "latest_arxiv_id": latest_arxiv_id,
        "all_versions": versions,
        "versions_count": len(versions)
    }

def query_crossref(doi: str, *, verbose: bool = False) -> Optional[Dict[str, Any]]:
    key = f"crossref:{doi.lower()}"
    if (c := _read_cache(key)) is not None:
        return c

    resp = _get(_CROSSREF_API + doi, timeout=12, retries=3, backoff=2, verbose=verbose)
    if not resp:
        return None
    try:
        msg = resp.json()["message"]
        meta = {
            "title": msg.get("title", [""])[0],
            "authors": [
                ", ".join(filter(None, [a.get("family"), a.get("given")]))
                for a in msg.get("author", [])
            ],
            "published": "-".join(
                map(str, msg.get("issued", {}).get("date-parts", [[""]])[0])
            ),
            "DOI": doi,
            "source": "crossref",
        }
        _write_cache(key, meta)
        return meta
    except Exception as exc:
        logger.warning("Crossref parse error %s – %s", doi, exc)
        return None

def query_unpaywall(doi: str, *, email: str | None = None, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """Query Unpaywall API for open access information."""
    email = email or os.getenv("UNPAYWALL_EMAIL", "research@example.edu")
    key = f"unpaywall:{doi.lower()}"
    if (c := _read_cache(key)) is not None:
        return c

    url = f"{_UNPAYWALL_API}{doi}"
    params = {"email": email}
    resp = _get(url, params=params, timeout=10, retries=2, backoff=2, verbose=verbose)
    if not resp:
        return None
    
    try:
        data = resp.json()
        if not data.get("is_oa"):
            # Not open access, but cache the negative result
            meta = {
                "DOI": doi,
                "is_open_access": False,
                "oa_locations": [],
                "source": "unpaywall",
            }
        else:
            # Open access available
            oa_locations = []
            for loc in data.get("oa_locations", []):
                oa_locations.append({
                    "url": loc.get("url_for_pdf") or loc.get("url"),
                    "host_type": loc.get("host_type"),  # repository, publisher
                    "license": loc.get("license"),
                    "version": loc.get("version"),  # publishedVersion, acceptedVersion, submittedVersion
                })
            
            meta = {
                "DOI": doi,
                "is_open_access": True,
                "oa_locations": oa_locations,
                "best_oa_location": data.get("best_oa_location", {}).get("url_for_pdf") or 
                                   data.get("best_oa_location", {}).get("url"),
                "oa_date": data.get("oa_date"),
                "journal_is_oa": data.get("journal_is_oa", False),
                "source": "unpaywall",
            }
        
        _write_cache(key, meta)
        return meta
    except Exception as exc:
        logger.warning("Unpaywall parse error %s – %s", doi, exc)
        return None

# ───────────────── provider: Google Scholar (SerpAPI & scholarly) ───────────
_SERP_API_ENDPOINT = "https://serpapi.com/search.json"

def _serpapi_request(query: str, api_key: str, *, verbose: bool = False) -> Optional[dict]:
    params = {
        "engine": "google_scholar",
        "q": query,
        "num": 1,
        "api_key": api_key,
    }
    resp = _get(_SERP_API_ENDPOINT, params=params, timeout=25, retries=2, backoff=4, verbose=verbose)
    if not resp:
        return None
    try:
        return resp.json()
    except Exception:
        return None

def query_google_scholar_serpapi(
    query: str, *, api_key: str | None = None, verbose: bool = False
) -> Optional[Dict[str, Any]]:
    api_key = api_key or os.getenv("SERPAPI_KEY")
    if not api_key:
        return None
    key = f"serpapi:{query}"
    if (c := _read_cache(key)) is not None:
        return c

    data = _serpapi_request(query, api_key, verbose=verbose)
    if not data or not data.get("organic_results"):
        return None
    res = data["organic_results"][0]
    meta = {
        "title": res.get("title", ""),
        "authors": res.get("publication_info", {}).get("authors", []),
        "published": res.get("publication_info", {}).get("year"),
        "source": "scholar_serpapi",
    }
    _write_cache(key, meta)
    return meta

def query_google_scholar_scholarly(
    query: str, *, verbose: bool = False
) -> Optional[Dict[str, Any]]:
    if scholarly is None:
        return None
    key = f"scholarly:{query}"
    if (c := _read_cache(key)) is not None:
        return c
    try:
        pub = next(scholarly.search_pubs(query), None)     # type: ignore[attr-defined]
        if not pub:
            return None
        bib = pub["bib"]
        meta = {
            "title": bib.get("title", ""),
            "authors": bib.get("author", "").split(" and "),
            "published": str(bib.get("pub_year", "")),
            "source": "scholar_html",
        }
        _write_cache(key, meta)
        return meta
    except Exception as exc:
        logger.warning("scholarly error %s – %s", query[:60], exc)
        return None

def query_google_scholar_all(
    query: str, *, verbose: bool = False
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if (r := query_google_scholar_serpapi(query, verbose=verbose)):
        results.append(r)
    if (r := query_google_scholar_scholarly(query, verbose=verbose)):
        results.append(r)
    return results

# ────────────────────────── high-level helpers ──────────────────────────────
def flatten_metadata_dict(meta: Mapping[str, Any]) -> Dict[str, str]:
    def _fmt_date(d: Any) -> str:
        if d is None:
            return ""
        if isinstance(d, list):  # legacy format [[YYYY, M, D]]
            try:
                y, m, d_ = d[0]
                return f"{y:04d}-{m:02d}-{d_:02d}"
            except Exception:
                return str(d)
        return str(d)

    return {
        "title":                meta.get("title", ""),
        "authors":              ", ".join(meta.get("authors", [])),
        "published":            _fmt_date(meta.get("published")),
        "DOI":                  meta.get("DOI", ""),
        "arxiv_id":             meta.get("arxiv_id", ""),
        "source":               meta.get("source", ""),
        "is_open_access":       meta.get("is_open_access", ""),
        "best_oa_location":     meta.get("best_oa_location", ""),
        "journal_is_oa":        meta.get("journal_is_oa", ""),
        "primary_subject":      meta.get("primary_subject", ""),
        "mathematical_subjects": ", ".join(meta.get("mathematical_subjects", [])),
        "msc_codes":            ", ".join(meta.get("msc_codes", [])),
        "has_arxiv_updates":    meta.get("has_arxiv_updates", ""),
        "current_arxiv_version": meta.get("current_arxiv_version", ""),
        "latest_arxiv_version": meta.get("latest_arxiv_version", ""),
        "arxiv_versions_count": meta.get("arxiv_versions_count", ""),
    }

def fetch_metadata_all_sources(
    query: str,
    *,
    doi: str | None = None,
    arxiv_id: str | None = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    metas: List[Dict[str, Any]] = []
    
    # Fetch primary metadata
    if arxiv_id and (m := query_arxiv(arxiv_id, verbose=verbose)):
        metas.append(m)
    if doi and (m := query_crossref(doi, verbose=verbose)):
        metas.append(m)
    metas.extend(query_google_scholar_all(query, verbose=verbose))
    
    # Enrich with open access information if we have a DOI
    effective_doi = doi
    if not effective_doi and metas:
        # Try to get DOI from any of the fetched metadata
        for meta in metas:
            if meta.get("DOI"):
                effective_doi = meta["DOI"]
                break
    
    if effective_doi and (oa_info := query_unpaywall(effective_doi, verbose=verbose)):
        # Merge open access info into existing metadata or add as separate entry
        if metas:
            # Enrich the first metadata entry with OA information
            metas[0].update({
                "is_open_access": oa_info.get("is_open_access", False),
                "oa_locations": oa_info.get("oa_locations", []),
                "best_oa_location": oa_info.get("best_oa_location"),
                "journal_is_oa": oa_info.get("journal_is_oa", False),
            })
        else:
            # Add OA info as standalone metadata
            metas.append(oa_info)
    
    # If no metadata found from external sources, create a basic entry for enrichment
    if not metas and query:
        metas.append({
            "title": query,
            "authors": [],
            "source": "query_only",
        })
    
    # Add subject classification to all metadata entries
    for i, meta in enumerate(metas):
        metas[i] = enrich_metadata_with_subjects(meta)
    
    # Check for arXiv version updates if we have an arXiv ID
    effective_arxiv_id = arxiv_id
    if not effective_arxiv_id and metas:
        # Try to get arXiv ID from any of the fetched metadata
        for meta in metas:
            if meta.get("arxiv_id"):
                effective_arxiv_id = meta["arxiv_id"]
                break
    
    if effective_arxiv_id:
        update_info = detect_arxiv_updates(effective_arxiv_id, verbose=verbose)
        if metas and update_info:
            # Enrich the first metadata entry with version information
            metas[0].update({
                "has_arxiv_updates": update_info.get("has_updates", False),
                "current_arxiv_version": update_info.get("current_version"),
                "latest_arxiv_version": update_info.get("latest_version"),
                "latest_arxiv_id": update_info.get("latest_arxiv_id"),
                "arxiv_versions_count": update_info.get("versions_count", 1),
            })
    
    return metas

def _best_candidate(
    cands: List[Dict[str, Any]],
    query_title: str,
    query_authors: Sequence[str],
) -> Optional[Dict[str, Any]]:
    def _score(m: Dict[str, Any]) -> float:
        s = 0.0
        if title_match(m.get("title", ""), query_title):
            s += 1.0
        if authors_match(m.get("authors", []), query_authors):
            s += 1.0
        if m.get("DOI"):
            s += 0.2
        if m.get("published"):
            s += 0.1
        return s

    return max(cands, key=_score) if cands else None

def batch_metadata_lookup(
    queries: Iterable[Tuple[str, Sequence[str]]],
    *,
    max_workers: int = 6,
    progress_bar: bool = True,
) -> Dict[str, Dict[str, Any]]:
    def _task(tup: Tuple[str, Sequence[str]]) -> Tuple[str, Optional[Dict[str, Any]]]:
        title, authors = tup
        best = _best_candidate(
            fetch_metadata_all_sources(title), title, authors
        )
        return title, best or {}

    results: Dict[str, Dict[str, Any]] = {}
    iterable = tqdm(list(queries), disable=not progress_bar, desc="metadata")
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for fut in as_completed(pool.submit(_task, q) for q in iterable):
            title, meta = fut.result()
            results[title] = meta
    return results

def write_csv_metadata(
    path: str | Path, metadata: Mapping[str, Mapping[str, Any]]
) -> None:
    fieldnames = ["key", "title", "authors", "published", "DOI", "arxiv_id", "source", 
                  "is_open_access", "best_oa_location", "journal_is_oa",
                  "primary_subject", "mathematical_subjects", "msc_codes",
                  "has_arxiv_updates", "current_arxiv_version", "latest_arxiv_version", "arxiv_versions_count"]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for k, m in metadata.items():
            row = {"key": k}
            row.update(flatten_metadata_dict(m))
            w.writerow(row)
    logger.info("Wrote %s (%d rows)", p, len(metadata))

# ────────────────────────── public re-export ───────────────────────────────
__all__ = [
    # low-level helpers
    "canonicalize",
    "title_match",
    "authors_match",
    "extract_family_given",
    "given_name_initials",
    "normalize_author",
    # subject classification
    "classify_mathematical_subject",
    "enrich_metadata_with_subjects",
    # arxiv version detection
    "extract_arxiv_info",
    "get_arxiv_versions",
    "detect_arxiv_updates",
    # metadata processing
    "flatten_metadata_dict",
    "fetch_metadata_all_sources",
    "batch_metadata_lookup",
    "write_csv_metadata",
    # provider functions
    "query_arxiv",
    "query_crossref",
    "query_unpaywall",
    "query_google_scholar_serpapi",
    "query_google_scholar_scholarly",
    "query_google_scholar_all",
]

# ────────────────────────── end of file ────────────────────────────────────