#!/usr/bin/env python3
"""Reuse the user's authenticated browser session for institutional downloads.

Why this exists
---------------
A *fresh* institutional (Shibboleth/SAML) login does NOT entitle access at
several publishers — verified end-to-end against Springer with ETH Zürich:
even a clean real-Chrome login (and the user's own Incognito) only ever shows
"Buy article".  Access lives in a **persistent session cookie** the user's
everyday browser already holds (for Springer it's ``sim-inst-token`` +
``idp_session`` on ``.springer.com``), bootstrapped earlier while on the
institution network and long-lived enough to survive travel.

So instead of re-implementing each publisher's bespoke SAML dance (brittle,
and — as proven — unable to succeed from a cold start), we **borrow the
cookies the browser already earned**.  This is publisher-agnostic for the
*auth* half: one importer unlocks every publisher the user has access to.
The only per-publisher part left is the PDF-URL pattern, which already lives
in :func:`downloader.eth_institutional._get_pdf_url`.

Privacy / safety
----------------
* Only cookies whose host matches the academic-publisher allowlist
  (:data:`PUBLISHER_DOMAINS`) are ever read or decrypted.  Cookies for mail,
  banking, etc. are never touched.
* Cookie *names and domains* are stored in Chrome's SQLite in the clear, so we
  can locate the right profile WITHOUT any keychain access.  Decryption (which
  triggers a one-time macOS Keychain "Allow" prompt) only happens when the
  user explicitly imports.
* Decrypted values are never logged.  The cache is written through the
  existing Fernet-encrypted secure store.

macOS Chrome cookie crypto: the per-value blob is ``b"v10"`` + AES-128-CBC
ciphertext, key = PBKDF2-HMAC-SHA1(keychain "Chrome Safe Storage" password,
salt=``b"saltysalt"``, iterations=1003, dklen=16), IV = 16 spaces, PKCS7
padding.  Newer Chrome prepends a 32-byte SHA-256(host) to the plaintext;
we strip it when the decode would otherwise fail.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Cookie-host substrings we are willing to read.  Keep this to academic
# publishers; everything else in the user's browser stays untouched.
PUBLISHER_DOMAINS: tuple[str, ...] = (
    "springer.com",
    "springernature.com",
    "nature.com",
    "onlinelibrary.wiley.com",
    "wiley.com",
    "sciencedirect.com",
    "elsevier.com",
    "tandfonline.com",
    "cambridge.org",
    "academic.oup.com",
    "oup.com",
    "iopscience.iop.org",
    "ams.org",
    "epubs.siam.org",
    "siam.org",
    "degruyter.com",
    "degruyterbrill.com",
    "worldscientific.com",
    "pubsonline.informs.org",
    "informs.org",
    "projecteuclid.org",
    "jstor.org",
    "aip.org",
    "aps.org",
    "acm.org",
    "ieee.org",
)

_KEYCHAIN_SERVICE = "Chrome Safe Storage"
_KEYCHAIN_ACCOUNT = "Chrome"
# Cookie blob in the secure store.
_CACHE_KEY = "browser_cookies_json"

# Seconds between 1601-01-01 (Chrome epoch) and 1970-01-01 (Unix epoch).
_CHROME_EPOCH_OFFSET = 11644473600


def _chrome_base() -> Path:
    # Overridable for tests (point at a synthetic profile tree).
    override = os.environ.get("MATHPDF_CHROME_BASE")
    if override:
        return Path(override)
    return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"


def is_supported() -> bool:
    """True on macOS with pycryptodome available and a Chrome dir present."""
    if sys.platform != "darwin":
        return False
    try:
        import Crypto  # noqa: F401
    except Exception:
        return False
    return _chrome_base().exists()


def iter_profile_dirs() -> list[Path]:
    """Real user profiles (Default, Profile N) that have a Cookies DB."""
    base = _chrome_base()
    out: list[Path] = []
    for p in sorted(base.glob("*")):
        if not p.is_dir():
            continue
        if p.name in ("Guest Profile", "System Profile"):
            continue
        if (p / "Cookies").exists():
            out.append(p)
    return out


def _host_allowed(host: str) -> bool:
    # Exact match or a true subdomain ONLY.  A bare ``endswith(d)`` would also
    # match attacker-registrable look-alikes (``evilwiley.com`` ends with
    # ``wiley.com``, ``notspringer.com`` ends with ``springer.com``), which
    # must never have their cookies read/decrypted.
    h = host.lstrip(".").lower()
    return any(h == d or h.endswith("." + d) for d in PUBLISHER_DOMAINS)


def _snapshot_db(cookies_path: Path) -> Path:
    """Copy the (possibly WAL-journalled, live) cookie DB to a temp file so we
    can read it without disturbing Chrome's session."""
    tmpdir = Path(tempfile.mkdtemp(prefix="mathpdf_ck_"))
    dst = tmpdir / "Cookies"
    for ext in ("", "-wal", "-shm"):
        src = Path(str(cookies_path) + ext)
        if src.exists():
            shutil.copy2(src, str(dst) + ext)
    return dst


def _cleanup_snapshot(dst: Path) -> None:
    try:
        shutil.rmtree(dst.parent, ignore_errors=True)
    except OSError:
        pass


@dataclass
class ProfileScan:
    """What we can see in a profile WITHOUT decrypting anything."""
    profile: str
    cookie_count: int
    domains: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)


def scan_profiles() -> list[ProfileScan]:
    """List, per profile, the publisher cookies present (names/domains only).

    No keychain access, no decryption — safe to call on every cockpit render.
    """
    scans: list[ProfileScan] = []
    for prof_dir in iter_profile_dirs():
        snap = _snapshot_db(prof_dir / "Cookies")
        try:
            con = sqlite3.connect(str(snap))
            rows = con.execute(
                "SELECT host_key, name FROM cookies"
            ).fetchall()
            con.close()
        except Exception as exc:
            logger.debug("scan %s failed: %s", prof_dir.name, exc)
            _cleanup_snapshot(snap)
            continue
        _cleanup_snapshot(snap)
        hits = [(h, n) for (h, n) in rows if _host_allowed(h)]
        if hits:
            scans.append(ProfileScan(
                profile=prof_dir.name,
                cookie_count=len(hits),
                domains=sorted({h.lstrip(".") for h, _ in hits}),
                names=sorted({n for _, n in hits}),
            ))
    return scans


def auto_detect_profile() -> Optional[str]:
    """The profile with the most publisher cookies, or None."""
    scans = scan_profiles()
    if not scans:
        return None
    return max(scans, key=lambda s: s.cookie_count).profile


def _safe_storage_key() -> bytes:
    """Derive the AES key from the macOS Keychain (prompts once to Allow)."""
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Hash import SHA1

    pw = subprocess.check_output(
        ["security", "find-generic-password", "-w",
         "-s", _KEYCHAIN_SERVICE, "-a", _KEYCHAIN_ACCOUNT],
        stderr=subprocess.DEVNULL,
    ).strip()
    return PBKDF2(pw, b"saltysalt", dkLen=16, count=1003, hmac_hash_module=SHA1)


def _decrypt(enc: bytes, key: bytes) -> Optional[str]:
    from Crypto.Cipher import AES

    if not enc or enc[:3] != b"v10":
        return None
    try:
        pt = AES.new(key, AES.MODE_CBC, b" " * 16).decrypt(enc[3:])
        pad = pt[-1]
        if 1 <= pad <= 16:
            pt = pt[:-pad]
        try:
            return pt.decode("utf-8")
        except UnicodeDecodeError:
            # Newer Chrome prepends 32-byte sha256(host) to the plaintext.
            return pt[32:].decode("utf-8", "ignore")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("cookie decrypt failed: %s", exc)
        return None


_SAMESITE = {0: "None", 1: "Lax", 2: "Strict"}


def load_cookies(profile: Optional[str] = None, *, key: Optional[bytes] = None) -> list[dict]:
    """Decrypt this profile's publisher cookies into Playwright cookie dicts.

    Triggers the Keychain prompt (unless ``key`` is supplied, for tests).
    ``profile`` defaults to auto-detected.  Returns ``[]`` if nothing usable
    is found.  Values are never logged.
    """
    if profile is None:
        profile = auto_detect_profile()
    if not profile:
        return []
    cookies_path = _chrome_base() / profile / "Cookies"
    if not cookies_path.exists():
        return []

    if key is None:
        key = _safe_storage_key()
    snap = _snapshot_db(cookies_path)
    out: list[dict] = []

    def _s(v) -> str:
        # text_factory=bytes hands back text columns as raw bytes.
        return v.decode("utf-8", "ignore") if isinstance(v, (bytes, bytearray)) else (v or "")

    try:
        con = sqlite3.connect(str(snap))
        # The encrypted_value column is binary and not valid UTF-8; returning
        # every text column as bytes avoids sqlite's decode crash, and we
        # decode the genuine text columns ourselves.
        con.text_factory = bytes
        rows = con.execute(
            "SELECT host_key, name, encrypted_value, path, expires_utc, "
            "is_secure, is_httponly, samesite FROM cookies"
        ).fetchall()
        con.close()
        for host_key, name, enc, path, expires_utc, is_secure, is_httponly, samesite in rows:
            host = _s(host_key)
            if not _host_allowed(host):
                continue
            enc = bytes(enc) if enc is not None else b""
            val = _decrypt(enc, key)
            if val is None:
                continue
            c: dict = {
                "name": _s(name),
                "value": val,
                "domain": host,
                "path": _s(path) or "/",
                "secure": bool(is_secure),
                "httpOnly": bool(is_httponly),
            }
            ss = _SAMESITE.get(samesite)
            # Chromium rejects sameSite=None on a non-Secure cookie; setting it
            # would make ctx.add_cookies reject the WHOLE batch.  Omit it there.
            if ss and not (ss == "None" and not c["secure"]):
                c["sameSite"] = ss
            if expires_utc and expires_utc > 0:
                c["expires"] = expires_utc / 1_000_000 - _CHROME_EPOCH_OFFSET
            out.append(c)
    finally:
        _cleanup_snapshot(snap)
    return out


# ---------------------------------------------------------------------------
# Encrypted cache (so we don't re-prompt the keychain every download)
# ---------------------------------------------------------------------------

def _store():
    from secure_credential_manager import get_credential_manager
    return get_credential_manager()


def save_cached(cookies: list[dict], profile: Optional[str]) -> bool:
    """Persist cookies (encrypted) with a capture timestamp."""
    blob = json.dumps({
        "captured_at": int(time.time()),
        "profile": profile,
        "cookies": cookies,
    })
    try:
        return _store().store_credential(_CACHE_KEY, blob)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("could not cache browser cookies: %s", exc)
        return False


def load_cached() -> Optional[dict]:
    """Return ``{captured_at, profile, cookies}`` or None."""
    try:
        blob = _store().get_credential(_CACHE_KEY)
    except Exception:
        return None
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not data.get("cookies"):
        return None
    return data


def clear_cached() -> None:
    try:
        _store().delete_credential(_CACHE_KEY)
    except Exception:
        pass


def refresh_from_browser(profile: Optional[str] = None) -> dict:
    """Import + cache cookies from Chrome.  Returns a status summary
    (no cookie values).  Raises on keychain/permission failure."""
    if profile is None:
        profile = auto_detect_profile()
    cookies = load_cookies(profile)
    save_cached(cookies, profile)
    return {
        "profile": profile,
        "count": len(cookies),
        "domains": sorted({c["domain"].lstrip(".") for c in cookies}),
        "captured_at": int(time.time()),
    }


def cookies_for_download(*, allow_import: bool = False) -> list[dict]:
    """Cookies to inject for a download: cached first, optionally importing."""
    cached = load_cached()
    if cached:
        return cached["cookies"]
    if allow_import and is_supported():
        try:
            return load_cookies()
        except Exception as exc:
            logger.debug("on-demand cookie import failed: %s", exc)
    return []


def download_with_session_cookies(
    doi: str, output_dir: Path, cookies: list[dict], *, timeout: int = 30000
) -> Optional[Path]:
    """Download a paper's PDF by injecting borrowed session cookies.

    Publisher-agnostic auth (the cookies), per-publisher PDF URL (reusing
    :func:`downloader.eth_institutional._get_pdf_url`).  Returns the path or
    None.  Synchronous wrapper around the async Playwright flow.
    """
    if not cookies:
        return None
    import asyncio
    coro = _download_async(doi, Path(output_dir), cookies, timeout)
    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)          # normal: no loop running
        # Called from inside a running event loop (e.g. some host contexts) —
        # asyncio.run() would raise; run it on a dedicated thread instead.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(coro)).result()
    except Exception as exc:
        logger.debug("browser-session download failed for %s: %s", doi, exc)
        return None


async def _is_cloudflare(page) -> bool:
    try:
        title = (await page.title()) or ""
    except Exception:
        return False
    if "just a moment" in title.lower() or "attention required" in title.lower():
        return True
    return "__cf_chl" in page.url


async def _await_cloudflare(page, deadline_ms: int = 25000) -> None:
    """Real Chrome auto-solves Cloudflare's managed challenge; give it time."""
    waited = 0
    while waited < deadline_ms and await _is_cloudflare(page):
        await page.wait_for_timeout(1500)
        waited += 1500


# Cloudflare clearance cookies are IP+fingerprint-bound; injecting a stale one
# from another session POISONS a fresh attempt (forces a harder challenge that
# never clears).  Strip them and let the live browser mint its own.
_CF_COOKIE_MARKERS = ("cf_clearance", "__cf_bm", "cf_chl", "cfz_")

# Pull the PDF with an IN-PAGE fetch: the page already passed Cloudflare and
# carries the freshly-minted clearance + the browser's real TLS fingerprint.
# A separate HTTP client (ctx.request / requests) does NOT share that fingerprint
# and gets 403'd by Cloudflare even with identical cookies.
_INPAGE_FETCH_JS = """
async (u) => {
  const r = await fetch(u, {credentials: 'include', headers: {'Accept': 'application/pdf'}});
  if (r.status !== 200) return 'ERR:' + r.status;
  const buf = new Uint8Array(await r.arrayBuffer());
  let s = ''; const CH = 0x8000;
  for (let i = 0; i < buf.length; i += CH) s += String.fromCharCode.apply(null, buf.subarray(i, i + CH));
  return btoa(s);
}
"""


# Verified per-publisher PDF URL templates (workflow-mapped + live-checked
# 2026-06-28).  {doi} is the raw DOI (it lives in the URL PATH, so the embedded
# '/' is fine).  The ?download=true variants are what actually return the binary
# PDF rather than an HTML viewer (SIAM / Wiley / World Scientific).
_PDF_PATTERNS = {
    "epubs.siam.org": "https://epubs.siam.org/doi/pdf/{doi}?download=true",
    "onlinelibrary.wiley.com": "https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}?download=true",
    "www.worldscientific.com": "https://www.worldscientific.com/doi/pdf/{doi}?download=true",
    "www.tandfonline.com": "https://www.tandfonline.com/doi/pdf/{doi}",
    "link.springer.com": "https://link.springer.com/content/pdf/{doi}.pdf",
    "iopscience.iop.org": "https://iopscience.iop.org/article/{doi}/pdf",
    "www.jstor.org": "https://www.jstor.org/stable/pdf/{doi}.pdf?acceptTC=true",
    "projecteuclid.org": "https://projecteuclid.org/journalArticle/Download?urlId={doi}",
    "www.degruyterbrill.com": "https://www.degruyterbrill.com/document/doi/{doi}/pdf",
}

# PDF-link selectors across publishers (workflow-mapped 2026-06-28).
_PDF_SELECTORS = (
    "a#pdfLink",                            # Elsevier ScienceDirect
    'a[data-qa="download-pdf"]',            # JSTOR
    "a.downloadPdf",                        # De Gruyter
    "a.c-pdf-download__link",               # Springer
    'a[href*="/article-pdf/"]',            # OUP
    'a[href*="/doi/pdfdirect/"]',          # Wiley
    'a[href*="/doi/epdf/"]',               # T&F
    'a[href*="/doi/pdf/"]',                # SIAM / T&F / World Scientific
    'a[href*="journalArticle/Download"]',  # Project Euclid
    'a[href*="/content/pdf/"]',            # Springer
    'a[href*="pdfft"]',                    # Elsevier
    'a[href$="/pdf"]',                     # IOP
    'a[data-article-pdf="true"]',
)


async def _collect_candidates(page, doi, article_url):
    """Ordered, de-duplicated candidate PDF URLs for the loaded article page.

    Publishers differ wildly, so we gather several and the caller accepts the
    first that actually returns a %PDF (a URL may 302 to an HTML paywall page
    when un-entitled — the bytes are the source of truth, not the URL).
    """
    from urllib.parse import urljoin
    host = article_url.split("/")[2].lower() if "://" in article_url else ""
    out: list[str] = []

    def add(u):
        if u:
            out.append(urljoin(article_url, u))

    # 1. canonical citation_pdf_url meta (present on most publishers)
    meta = await page.query_selector('meta[name="citation_pdf_url"]')
    if meta:
        add(await meta.get_attribute("content"))
    # 2. verified host pattern
    for h, tmpl in _PDF_PATTERNS.items():
        if h in host:
            add(tmpl.format(doi=doi))
            break
    # 3. eth_institutional legacy patterns (extra coverage)
    try:
        from downloader.eth_institutional import _get_pdf_url
        add(_get_pdf_url(doi, article_url))
    except Exception:
        pass
    # 4. SPA publishers (ScienceDirect) render the PDF link late
    if "sciencedirect.com" in host:
        try:
            await page.wait_for_selector("a#pdfLink", timeout=6000)
        except Exception:
            pass
    # 5. publisher-specific + generic on-page link selectors
    for sel in _PDF_SELECTORS:
        try:
            els = await page.query_selector_all(sel)
        except Exception:
            continue
        for el in els[:3]:
            href = (await el.get_attribute("href")
                    or await el.get_attribute("data-href")
                    or await el.get_attribute("data-pdf-url"))
            if href:
                add(href)

    seen: set = set()
    uniq: list[str] = []
    for u in out:
        if u and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


async def _run_flow(ctx, doi, out, cookies, timeout):
    """Drive an already-prepared browser CONTEXT to fetch the PDF.

    The context's lifecycle (and the browser/process behind it) is owned by the
    launcher's cleanup — we don't close it here.
    """
    import base64

    # Inject auth cookies only — never stale Cloudflare clearance.
    auth_cookies = [c for c in cookies
                    if not any(m in c["name"] for m in _CF_COOKIE_MARKERS)]

    # Hide the residual automation flag (cheap; real headed Chrome + no VPN does
    # the heavy lifting of passing Cloudflare).
    try:
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
    except Exception:
        pass
    try:
        await ctx.add_cookies(auth_cookies)
    except Exception:
        # Never echo the exception — it can contain a cookie value.  Add one at
        # a time so a single malformed cookie can't drop the whole batch.
        ok = 0
        for c in auth_cookies:
            try:
                await ctx.add_cookies([c])
                ok += 1
            except Exception:
                pass
        logger.debug("add_cookies: %d/%d injected individually",
                     ok, len(auth_cookies))

    page = await ctx.new_page()
    await page.goto(f"https://doi.org/{doi}",
                    wait_until="domcontentloaded", timeout=timeout)
    await page.wait_for_timeout(1500)
    if await _is_cloudflare(page):
        await _await_cloudflare(page)
        if await _is_cloudflare(page):
            # Almost always a VPN/datacenter exit IP — Cloudflare won't clear
            # it.  Surface a distinct, actionable signal.
            logger.warning("Cloudflare challenge unresolved for %s "
                           "(turn the VPN OFF — a VPN IP can't pass)", doi)
            _record_diag(doi, "cloudflare", page.url.split("/")[2] if "://" in page.url else "")
            return None
    article_url = page.url

    # Gather candidate PDF URLs (citation meta → verified host pattern →
    # on-page links) and accept the first that returns a real %PDF.
    candidates = await _collect_candidates(page, doi, article_url)
    for url in candidates:
        try:
            b64 = await page.evaluate(_INPAGE_FETCH_JS, url)
        except Exception:
            continue
        if not isinstance(b64, str) or b64.startswith("ERR:") or len(b64) < 1400:
            continue
        try:
            body = base64.b64decode(b64)
        except Exception:
            continue
        if len(body) >= 1024 and body[:4] == b"%PDF":
            out.write_bytes(body)
            return out

    # Fallback: some publishers (AMS, embedded viewers) deliver the PDF via a
    # click that triggers a browser DOWNLOAD / blob rather than a fetchable URL.
    # Click the real download control and capture the download event.
    try:
        btn = await page.query_selector(
            "button.productDetailDownloadPdfButton, a#pdfLink, "
            "a.c-pdf-download__link, a.downloadPdf, "
            'a[data-qa="download-pdf"], a:has-text("Download PDF"), '
            'button:has-text("Download PDF")'
        )
        if btn:
            async with page.expect_download(timeout=12000) as dl_info:
                await btn.click()
            dl = await dl_info.value
            tmp = out.with_suffix(".part")
            await dl.save_as(str(tmp))
            ok = False
            try:
                if tmp.exists() and tmp.stat().st_size >= 1024:
                    with open(tmp, "rb") as fh:
                        ok = fh.read(4) == b"%PDF"
            except OSError:
                ok = False
            if ok:
                tmp.replace(out)
                return out
            tmp.unlink(missing_ok=True)
    except Exception:
        pass

    # No PDF obtained — record WHY so the cockpit can guide the user.
    try:
        reason = await _classify_failure(page)
        _record_diag(doi, reason, page.url.split("/")[2] if "://" in page.url else "")
    except Exception:
        pass
    return None


def _chrome_app() -> Optional[str]:
    for p in ("/Applications/Google Chrome.app",
              os.path.expanduser("~/Applications/Google Chrome.app")):
        if os.path.exists(p):
            return p
    return None


async def _ctx_hidden_cdp(p):
    """macOS preferred launcher: a NEW real-Chrome instance started BACKGROUND
    (`open -g`, never steals focus) and HIDDEN (`open -j`), driven over CDP.

    The window never appears or interrupts the user, yet it is a real rendering
    Chrome — which is the only thing that clears Cloudflare's managed challenge.
    """
    import asyncio
    if sys.platform != "darwin" or not _chrome_app():
        return None
    prof = tempfile.mkdtemp(prefix="mathpdf_cdp_")

    def _kill():
        # Match the unique per-launch profile path (the mkdtemp random suffix
        # makes it specific to OUR Chrome instance).
        subprocess.run(["pkill", "-f", prof],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(prof, ignore_errors=True)

    try:
        # Port 0 = let Chrome pick a free port and report it in the profile's
        # DevToolsActivePort file.  This avoids the TOCTOU of pre-binding a port
        # ourselves and racing another process for it.
        subprocess.Popen(
            ["open", "-na", "Google Chrome", "-g", "-j", "--args",
             "--remote-debugging-port=0", f"--user-data-dir={prof}",
             "--remote-debugging-address=127.0.0.1",
             "--no-first-run", "--no-default-browser-check",
             "--disable-blink-features=AutomationControlled"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        portfile = Path(prof) / "DevToolsActivePort"
        port = None
        for _ in range(40):
            if portfile.exists():
                try:
                    port = int(portfile.read_text().splitlines()[0].strip())
                    break
                except (ValueError, IndexError, OSError):
                    pass
            await asyncio.sleep(0.5)
        if not port:
            _kill()
            return None
        browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    except Exception as exc:
        logger.debug("hidden-cdp launch failed: %s", exc)
        _kill()
        return None

    try:
        # A dedicated context with downloads enabled (the default CDP context
        # has accept_downloads off, which would break the click-capture path).
        ctx = await browser.new_context(accept_downloads=True)
    except Exception:
        try:
            await browser.close()
        except Exception:
            pass
        _kill()
        return None

    async def cleanup():
        try:
            await browser.close()
        except Exception:
            pass
        _kill()

    return ctx, cleanup


async def _ctx_headed_offscreen(p):
    """Fallback: real Chrome, headed but parked far off-screen via quiet_args
    (a window may flicker; only used if the hidden-CDP path is unavailable)."""
    if not _chrome_app():
        return None
    from utils.browser_window import quiet_args
    browser = await p.chromium.launch(
        channel="chrome", headless=False,
        args=quiet_args(["--disable-blink-features=AutomationControlled"]),
    )
    ctx = await browser.new_context(
        viewport={"width": 1440, "height": 1000}, accept_downloads=True)

    async def cleanup():
        try:
            await browser.close()
        except Exception:
            pass

    return ctx, cleanup


async def _ctx_bundled_headless(p):
    """Last resort if Google Chrome isn't installed — bundled headless Chromium
    (won't clear Cloudflare, but works for non-Cloudflare publishers)."""
    browser = await p.chromium.launch(
        headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = await browser.new_context(
        viewport={"width": 1440, "height": 1000}, accept_downloads=True)

    async def cleanup():
        try:
            await browser.close()
        except Exception:
            pass

    return ctx, cleanup


async def _download_async(doi, output_dir, cookies, timeout):
    from playwright.async_api import async_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    import re as _re
    safe = _re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_") or "doi"
    out = output_dir / f"{safe}.pdf"

    # Hidden background Chrome first (no window, no focus theft); off-screen
    # headed next; bundled headless only if Chrome is missing.  Once a launcher
    # produces a context we use its result — bundled headless is never better at
    # Cloudflare, so we don't pay a second full attempt.
    strategies = (_ctx_hidden_cdp, _ctx_headed_offscreen, _ctx_bundled_headless)
    async with async_playwright() as p:
        for strat in strategies:
            try:
                acquired = await strat(p)
            except Exception as exc:
                logger.debug("launcher %s failed: %s", strat.__name__, exc)
                continue
            if not acquired:
                continue
            ctx, cleanup = acquired
            try:
                return await _run_flow(ctx, doi, out, cookies, timeout)
            except Exception as exc:
                logger.debug("flow via %s failed: %s", strat.__name__, exc)
                return None
            finally:
                await cleanup()
    return None


# Institutional-login entry points per publisher (host substring -> name, url).
# Open the URL, sign in via "Access through your institution" -> ETH Zürich.
PUBLISHER_LOGIN = {
    "sciencedirect.com": ("Elsevier / ScienceDirect", "https://www.sciencedirect.com/"),
    "elsevier.com": ("Elsevier / ScienceDirect", "https://www.sciencedirect.com/"),
    "epubs.siam.org": ("SIAM", "https://epubs.siam.org/"),
    "siam.org": ("SIAM", "https://epubs.siam.org/"),
    "ams.org": ("AMS", "https://www.ams.org/journals/"),
    "onlinelibrary.wiley.com": ("Wiley", "https://onlinelibrary.wiley.com/"),
    "wiley.com": ("Wiley", "https://onlinelibrary.wiley.com/"),
    "link.springer.com": ("Springer", "https://link.springer.com/"),
    "springer.com": ("Springer", "https://link.springer.com/"),
    "academic.oup.com": ("Oxford Academic (OUP)", "https://academic.oup.com/"),
    "oup.com": ("Oxford Academic (OUP)", "https://academic.oup.com/"),
    "cambridge.org": ("Cambridge Core", "https://www.cambridge.org/core"),
    "jstor.org": ("JSTOR", "https://www.jstor.org/"),
    "tandfonline.com": ("Taylor & Francis", "https://www.tandfonline.com/"),
    "degruyter": ("De Gruyter", "https://www.degruyterbrill.com/"),
    "worldscientific.com": ("World Scientific", "https://www.worldscientific.com/"),
    "iopscience.iop.org": ("IOP", "https://iopscience.iop.org/"),
    "projecteuclid.org": ("Project Euclid", "https://projecteuclid.org/"),
}

# Last per-DOI failure reason, captured during a download attempt so the cockpit
# can explain WHY (no extra navigation needed).  Single-process; not persisted.
_LAST_DIAG: dict = {}

_REASON_MSG = {
    "cloudflare": "Blocked by Cloudflare — turn your VPN OFF and retry.",
    "needs_login": "Not signed in at this publisher. Open it, sign in via your "
                   "institution (ETH Zürich), then Settings → Refresh from Chrome.",
    "paywalled": "Looks un-subscribed for this article — even your own browser "
                 "may not have it (then only Sci-Hub/manual will get it).",
    "needs_browser": "This publisher's access (ScienceDirect/Elsevier) is "
                     "OAuth-gated and doesn't carry over to automation — open "
                     "it in your browser to download.",
    "no_pdf": "Reached the article but found no downloadable PDF link.",
    "no_session": "No browser session imported yet — Settings → Refresh from Chrome.",
}


def _publisher_for_host(host: str):
    h = (host or "").lower()
    for sub, (name, url) in PUBLISHER_LOGIN.items():
        if sub in h:
            return name, url
    return None, None


async def _classify_failure(page) -> str:
    try:
        host = page.url.split("/")[2].lower() if "://" in page.url else ""
    except Exception:
        host = ""
    if await _is_cloudflare(page):
        return "cloudflare"
    if any(h in host for h in ("id.elsevier.com", "login.", "signin", "aai-logon",
                               "wayf", "/sso", "idp.")):
        return "needs_login"
    # ScienceDirect loads the article but withholds the PDF affordance under
    # cookie-injection (entitlement is OAuth/API-gated) — needs the real browser.
    if "sciencedirect.com" in host:
        return "needs_browser"
    try:
        body = (await page.content()).lower()
    except Exception:
        body = ""
    if any(s in body for s in ("access through your institution",
                               "log in via an institution",
                               "sign in via your institution",
                               "access through your organization",
                               "institutional sign in", "institutional login")):
        return "needs_login"
    if any(s in body for s in ("get access", "purchase", "buy article", "buy pdf",
                               "rent ", "add to cart", "purchase pdf")):
        return "paywalled"
    return "no_pdf"


def _record_diag(doi: str, reason: str, host: str) -> None:
    name, url = _publisher_for_host(host)
    _LAST_DIAG[doi] = {
        "reason": reason, "publisher": name, "login_url": url, "host": host,
        "message": _REASON_MSG.get(reason, reason), "at": int(time.time()),
    }


def last_diagnosis(doi: str):
    """Why the most recent browser-session download for ``doi`` failed (or None)."""
    return _LAST_DIAG.get(doi)


def connect_pages() -> list:
    """Login pages to (re)establish an entitled session, for the publishers the
    user actually has cookies for.  Returns [{publisher, url}]."""
    domains: set = set()
    if is_supported():
        for s in scan_profiles():
            domains.update(s.domains)
    cached = load_cached()
    if cached:
        domains.update(c["domain"].lstrip(".") for c in cached["cookies"])
    out: dict = {}
    for sub, (name, url) in PUBLISHER_LOGIN.items():
        if any(sub in d for d in domains):
            out[name] = url
    return [{"publisher": n, "url": u} for n, u in sorted(out.items())]


def session_status() -> dict:
    """Human-facing status for the cockpit (no values)."""
    cached = load_cached()
    scans = scan_profiles() if is_supported() else []
    status = {
        "supported": is_supported(),
        "detected_profiles": [
            {"profile": s.profile, "count": s.cookie_count, "domains": s.domains}
            for s in scans
        ],
        "has_cache": bool(cached),
    }
    if cached:
        status["cached_profile"] = cached.get("profile")
        status["cached_at"] = cached.get("captured_at")
        status["cached_domains"] = sorted(
            {c["domain"].lstrip(".") for c in cached["cookies"]}
        )
        # Soonest non-session expiry, for a freshness hint.
        exps = [c["expires"] for c in cached["cookies"] if c.get("expires")]
        status["earliest_expiry"] = min(exps) if exps else None
    return status
