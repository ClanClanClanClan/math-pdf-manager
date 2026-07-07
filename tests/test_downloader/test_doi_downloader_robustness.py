"""Phase 1b: download-helper robustness (truncation / size / magic byte).

Pure, model-free, network-free unit tests for the shared
``_download_to_file`` guard.  Live-publisher behaviour is covered by the
opt-in network suite (RUN_NETWORK_TESTS=1).
"""
from __future__ import annotations

import types


class _FakeResp:
    def __init__(self, status, body, declared=None, content_type=None):
        self.status_code = status
        self._body = body
        self.headers = {} if declared is None else {"Content-Length": str(declared)}
        if content_type is not None:
            self.headers["Content-Type"] = content_type

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]


def _patch_requests(monkeypatch, resp):
    import downloader.doi_downloader as dl
    fake = types.SimpleNamespace(get=lambda *a, **k: resp)
    monkeypatch.setattr(dl, "requests", fake)
    return dl


class TestDownloadToFile:

    def test_valid_complete_pdf(self, tmp_path, monkeypatch):
        body = b"%PDF-1.5" + b"0" * 4000
        dl = _patch_requests(monkeypatch, _FakeResp(200, body, declared=len(body)))
        out = tmp_path / "x.pdf"
        assert dl._download_to_file("http://x", out) is True
        assert out.exists() and out.stat().st_size == len(body)

    def test_truncated_rejected(self, tmp_path, monkeypatch):
        body = b"%PDF-1.5" + b"0" * 4000
        # Server declares more than we actually receive -> stalled transfer.
        dl = _patch_requests(monkeypatch, _FakeResp(200, body, declared=999999))
        out = tmp_path / "x.pdf"
        assert dl._download_to_file("http://x", out) is False
        assert not out.exists()

    def test_too_small_rejected(self, tmp_path, monkeypatch):
        body = b"%PDF" + b"0" * 10  # 14 bytes — error page / stub
        dl = _patch_requests(monkeypatch, _FakeResp(200, body, declared=len(body)))
        out = tmp_path / "x.pdf"
        assert dl._download_to_file("http://x", out) is False
        assert not out.exists()

    def test_non_pdf_rejected(self, tmp_path, monkeypatch):
        body = b"<html><body>Access denied</body></html>" + b" " * 2000
        dl = _patch_requests(monkeypatch, _FakeResp(200, body, declared=len(body)))
        out = tmp_path / "x.pdf"
        assert dl._download_to_file("http://x", out) is False
        assert not out.exists()

    def test_non_200_rejected(self, tmp_path, monkeypatch):
        dl = _patch_requests(monkeypatch, _FakeResp(403, b"%PDF" + b"0" * 4000, declared=4004))
        out = tmp_path / "x.pdf"
        assert dl._download_to_file("http://x", out) is False
        assert not out.exists()

    def test_no_content_length_still_validates_by_magic_and_size(self, tmp_path, monkeypatch):
        body = b"%PDF-1.5" + b"0" * 4000  # no declared length
        dl = _patch_requests(monkeypatch, _FakeResp(200, body, declared=None))
        out = tmp_path / "x.pdf"
        assert dl._download_to_file("http://x", out) is True


class TestTryDirectDoi:
    """try_direct_doi must apply the SAME guards as _download_to_file
    (it streams the response itself): status check + truncation guard."""

    def test_valid_complete_pdf(self, tmp_path, monkeypatch):
        body = b"%PDF-1.5" + b"0" * 4000
        dl = _patch_requests(monkeypatch, _FakeResp(
            200, body, declared=len(body), content_type="application/pdf"))
        out = tmp_path / "x.pdf"
        assert dl.try_direct_doi("10.1/x", out) is True
        assert out.exists()

    def test_truncated_rejected(self, tmp_path, monkeypatch):
        # Server declares more bytes than delivered -> stalled transfer;
        # the %PDF header alone must NOT let it pass.
        body = b"%PDF-1.5" + b"0" * 4000
        dl = _patch_requests(monkeypatch, _FakeResp(
            200, body, declared=999999, content_type="application/pdf"))
        out = tmp_path / "x.pdf"
        assert dl.try_direct_doi("10.1/x", out) is False
        assert not out.exists()

    def test_non_200_rejected(self, tmp_path, monkeypatch):
        body = b"%PDF-1.5" + b"0" * 4000
        dl = _patch_requests(monkeypatch, _FakeResp(
            403, body, declared=len(body), content_type="application/pdf"))
        out = tmp_path / "x.pdf"
        assert dl.try_direct_doi("10.1/x", out) is False
        assert not out.exists()

    def test_non_pdf_content_type_rejected(self, tmp_path, monkeypatch):
        dl = _patch_requests(monkeypatch, _FakeResp(
            200, b"<html>paywall</html>", declared=20, content_type="text/html"))
        out = tmp_path / "x.pdf"
        assert dl.try_direct_doi("10.1/x", out) is False
        assert not out.exists()


class TestIsValidPdf:

    def test_size_floor(self, tmp_path):
        from downloader.doi_downloader import _is_valid_pdf
        small = tmp_path / "s.pdf"
        small.write_bytes(b"%PDF" + b"0" * 10)
        assert _is_valid_pdf(small) is False
        good = tmp_path / "g.pdf"
        good.write_bytes(b"%PDF" + b"0" * 2000)
        assert _is_valid_pdf(good) is True

    def test_missing_file(self, tmp_path):
        from downloader.doi_downloader import _is_valid_pdf
        assert _is_valid_pdf(tmp_path / "nope.pdf") is False
