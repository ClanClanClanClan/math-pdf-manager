"""Phase 4: Acquisition engine audit."""
import os
import tempfile

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

httpx = pytest.importorskip("httpx")

# ---------------------------------------------------------------------------
# Mock the publishers module before importing acquisition engine.
#
# The acquisition engine does:
#   from publishers import DownloadResult
#   from publishers.unified_downloader import UnifiedDownloader
#
# These packages may not be installed in the test environment, so we
# inject lightweight stand-ins into sys.modules.
# ---------------------------------------------------------------------------
import sys
from unittest.mock import MagicMock as _MagicMock

# Create mock modules for publishers
mock_publishers = _MagicMock()
mock_download_result = _MagicMock()


@dataclass
class MockDownloadResult:
    success: bool = False
    file_path: Path = None
    error_message: str = ""


mock_publishers.DownloadResult = MockDownloadResult


class MockUnifiedDownloader:
    async def download_from_url(self, url, path):
        return MockDownloadResult(success=True, file_path=path)

    async def download_best_match(self, query, authors=None, download_dir=None):
        return MockDownloadResult(
            success=True,
            file_path=download_dir / "test.pdf" if download_dir else Path("test.pdf"),
        )


mock_publishers.unified_downloader = _MagicMock()
mock_publishers.unified_downloader.UnifiedDownloader = MockUnifiedDownloader

sys.modules["publishers"] = mock_publishers
sys.modules["publishers.unified_downloader"] = mock_publishers.unified_downloader

from acquisition.engine import (
    AcquisitionConfig,
    AcquisitionEngine,
    AcquisitionResult,
    AlternativeStrategy,
    BaseStrategy,
    InstitutionalCredentials,
    InstitutionalStrategy,
    OpenAccessStrategy,
    PreprintStrategy,
    PublisherStrategy,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_config(tmp_path: Path, **overrides) -> AcquisitionConfig:
    """Build an AcquisitionConfig rooted in *tmp_path*."""
    defaults = dict(
        download_dir=tmp_path / "downloads",
        unpaywall_email="test@example.com",
        allow_alternative_sources=False,
        institutional_credentials=None,
    )
    defaults.update(overrides)
    return AcquisitionConfig(**defaults)


def _mock_httpx_response(status_code: int, json_data: dict = None):
    """Return a mock httpx.Response with the given status code and JSON body."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# ============================================================================
# Section 4A: AcquisitionResult dataclass
# ============================================================================


class TestAcquisitionResult:
    """Verify the AcquisitionResult dataclass."""

    def test_success_result(self):
        r = AcquisitionResult(success=True, strategy="open_access", file_path=Path("a.pdf"))
        assert r.success is True
        assert r.strategy == "open_access"
        assert r.file_path == Path("a.pdf")
        assert r.message is None

    def test_failure_result(self):
        r = AcquisitionResult(success=False, strategy="publisher", message="No DOI")
        assert r.success is False
        assert r.message == "No DOI"
        assert r.file_path is None

    def test_defaults(self):
        r = AcquisitionResult(success=False, strategy="none")
        assert r.file_path is None
        assert r.message is None


# ============================================================================
# Section 4B: AcquisitionConfig dataclass
# ============================================================================


class TestAcquisitionConfig:
    """Verify AcquisitionConfig defaults and construction."""

    def test_default_download_dir(self):
        cfg = AcquisitionConfig()
        assert cfg.download_dir == Path("downloads")

    def test_custom_values(self, tmp_path):
        cfg = _make_config(tmp_path, unpaywall_email="me@x.org", allow_alternative_sources=True)
        assert cfg.unpaywall_email == "me@x.org"
        assert cfg.allow_alternative_sources is True

    def test_institutional_credentials_default_reads_env(self):
        """Default factory calls InstitutionalCredentials.from_env()."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the env vars are absent so from_env() returns None
            env_keys = [
                "INSTITUTIONAL_USERNAME",
                "INSTITUTIONAL_PASSWORD",
                "INSTITUTIONAL_PUBLISHER",
                "INSTITUTIONAL_HEADLESS",
                "INSTITUTIONAL_TIMEOUT_MS",
            ]
            clean_env = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, clean_env, clear=True):
                cfg = AcquisitionConfig()
                assert cfg.institutional_credentials is None


# ============================================================================
# Section 4C: InstitutionalCredentials.from_env()
# ============================================================================


class TestInstitutionalCredentialsFromEnv:
    """Verify environment-variable factory for institutional credentials."""

    def test_returns_none_when_no_env(self):
        with patch.dict(os.environ, {}, clear=True):
            assert InstitutionalCredentials.from_env() is None

    def test_returns_none_when_only_username(self):
        with patch.dict(os.environ, {"INSTITUTIONAL_USERNAME": "user"}, clear=True):
            assert InstitutionalCredentials.from_env() is None

    def test_returns_none_when_only_password(self):
        with patch.dict(os.environ, {"INSTITUTIONAL_PASSWORD": "pass"}, clear=True):
            assert InstitutionalCredentials.from_env() is None

    def test_minimal_credentials(self):
        env = {"INSTITUTIONAL_USERNAME": "user", "INSTITUTIONAL_PASSWORD": "pass"}
        with patch.dict(os.environ, env, clear=True):
            creds = InstitutionalCredentials.from_env()
            assert creds is not None
            assert creds.username == "user"
            assert creds.password == "pass"
            assert creds.publisher is None
            assert creds.headless is True
            assert creds.timeout_ms == 120000

    def test_full_credentials(self):
        env = {
            "INSTITUTIONAL_USERNAME": "u",
            "INSTITUTIONAL_PASSWORD": "p",
            "INSTITUTIONAL_PUBLISHER": "Elsevier",
            "INSTITUTIONAL_HEADLESS": "false",
            "INSTITUTIONAL_TIMEOUT_MS": "30000",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = InstitutionalCredentials.from_env()
            assert creds.publisher == "Elsevier"
            assert creds.headless is False
            assert creds.timeout_ms == 30000

    def test_headless_true_by_default(self):
        env = {"INSTITUTIONAL_USERNAME": "u", "INSTITUTIONAL_PASSWORD": "p"}
        with patch.dict(os.environ, env, clear=True):
            creds = InstitutionalCredentials.from_env()
            assert creds.headless is True

    def test_headless_true_explicit(self):
        env = {
            "INSTITUTIONAL_USERNAME": "u",
            "INSTITUTIONAL_PASSWORD": "p",
            "INSTITUTIONAL_HEADLESS": "true",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = InstitutionalCredentials.from_env()
            assert creds.headless is True

    def test_headless_non_false_string_is_true(self):
        """Any value other than 'false' (case-insensitive) keeps headless True."""
        env = {
            "INSTITUTIONAL_USERNAME": "u",
            "INSTITUTIONAL_PASSWORD": "p",
            "INSTITUTIONAL_HEADLESS": "yes",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = InstitutionalCredentials.from_env()
            assert creds.headless is True

    def test_invalid_timeout_falls_back_to_default(self):
        env = {
            "INSTITUTIONAL_USERNAME": "u",
            "INSTITUTIONAL_PASSWORD": "p",
            "INSTITUTIONAL_TIMEOUT_MS": "not_a_number",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = InstitutionalCredentials.from_env()
            assert creds.timeout_ms == 120000


# ============================================================================
# Section 4D: OpenAccessStrategy
# ============================================================================


class TestOpenAccessStrategy:
    """Verify the OpenAccessStrategy against mock Unpaywall responses."""

    @pytest.fixture
    def strategy(self):
        return OpenAccessStrategy()

    @pytest.fixture
    def client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def downloader(self):
        dl = AsyncMock(spec=MockUnifiedDownloader)
        dl.download_from_url = AsyncMock(
            return_value=MockDownloadResult(success=True, file_path=Path("paper.pdf"))
        )
        return dl

    @pytest.mark.asyncio
    async def test_success_with_url_for_pdf(self, strategy, client, downloader, tmp_path):
        """Happy path: Unpaywall returns best_oa_location with url_for_pdf."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "title": "Test paper"}

        resp = _mock_httpx_response(200, {
            "best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"}
        })
        client.get = AsyncMock(return_value=resp)

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is True
        assert result.strategy == "open_access"
        # Verify the Unpaywall API was queried with the correct DOI and email
        client.get.assert_called_once()
        call_args = client.get.call_args
        assert "10.1234/test" in call_args[0][0]
        assert call_args[1]["params"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_success_falls_back_to_url(self, strategy, client, downloader, tmp_path):
        """When url_for_pdf is absent, falls back to url field."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test"}

        resp = _mock_httpx_response(200, {
            "best_oa_location": {"url": "https://example.com/landing"}
        })
        client.get = AsyncMock(return_value=resp)

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is True
        # downloader should have been called with the fallback URL
        downloader.download_from_url.assert_called_once()
        download_url = downloader.download_from_url.call_args[0][0]
        assert download_url == "https://example.com/landing"

    @pytest.mark.asyncio
    async def test_failure_no_doi(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"title": "No DOI paper"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert result.strategy == "open_access"
        assert "No DOI" in result.message or "email" in result.message

    @pytest.mark.asyncio
    async def test_failure_no_email(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path, unpaywall_email=None)
        paper = {"doi": "10.1234/test"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "email" in result.message.lower() or "DOI" in result.message

    @pytest.mark.asyncio
    async def test_failure_404_response(self, strategy, client, downloader, tmp_path):
        """A 404 from Unpaywall means no open access record."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/missing"}

        resp = MagicMock(spec=httpx.Response)
        resp.status_code = httpx.codes.NOT_FOUND
        client.get = AsyncMock(return_value=resp)

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "No open access record" in result.message

    @pytest.mark.asyncio
    async def test_failure_no_oa_location(self, strategy, client, downloader, tmp_path):
        """Response has no best_oa_location at all."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/closed"}

        resp = _mock_httpx_response(200, {"best_oa_location": None})
        client.get = AsyncMock(return_value=resp)

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "unavailable" in result.message.lower()

    @pytest.mark.asyncio
    async def test_failure_oa_location_empty(self, strategy, client, downloader, tmp_path):
        """best_oa_location exists but has no url_for_pdf or url."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/empty_oa"}

        resp = _mock_httpx_response(200, {"best_oa_location": {}})
        client.get = AsyncMock(return_value=resp)

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "unavailable" in result.message.lower()

    @pytest.mark.asyncio
    async def test_download_failure_propagated(self, strategy, client, downloader, tmp_path):
        """When the downloader fails, the strategy reports failure."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test"}

        resp = _mock_httpx_response(200, {
            "best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"}
        })
        client.get = AsyncMock(return_value=resp)
        downloader.download_from_url = AsyncMock(
            return_value=MockDownloadResult(success=False, error_message="Connection refused")
        )

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "Connection refused" in result.message

    @pytest.mark.asyncio
    async def test_doi_sanitized_in_filepath(self, strategy, client, downloader, tmp_path):
        """DOI slashes are replaced with underscores in the download path."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/sub/path"}

        resp = _mock_httpx_response(200, {
            "best_oa_location": {"url_for_pdf": "https://example.com/paper.pdf"}
        })
        client.get = AsyncMock(return_value=resp)

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        download_path = downloader.download_from_url.call_args[0][1]
        assert "/" not in download_path.stem or "_" in str(download_path.name)
        assert "open_access" in str(download_path)


# ============================================================================
# Section 4E: PublisherStrategy
# ============================================================================


class TestPublisherStrategy:
    """Verify the PublisherStrategy delegates to downloader.download_best_match."""

    @pytest.fixture
    def strategy(self):
        return PublisherStrategy()

    @pytest.fixture
    def client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def downloader(self):
        dl = AsyncMock(spec=MockUnifiedDownloader)
        dl.download_best_match = AsyncMock(
            return_value=MockDownloadResult(success=True, file_path=Path("paper.pdf"))
        )
        return dl

    @pytest.mark.asyncio
    async def test_success_with_title(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"title": "A great paper", "authors": ["Smith"]}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is True
        assert result.strategy == "publisher"
        downloader.download_best_match.assert_called_once()
        call_kw = downloader.download_best_match.call_args
        assert call_kw[0][0] == "A great paper"
        assert call_kw[1]["authors"] == ["Smith"]

    @pytest.mark.asyncio
    async def test_success_with_doi_only(self, strategy, client, downloader, tmp_path):
        """When title is absent, DOI is used as query."""
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is True
        call_kw = downloader.download_best_match.call_args
        assert call_kw[0][0] == "10.1234/test"

    @pytest.mark.asyncio
    async def test_title_preferred_over_doi(self, strategy, client, downloader, tmp_path):
        """When both title and DOI are present, title is preferred."""
        config = _make_config(tmp_path)
        paper = {"title": "My title", "doi": "10.1234/test"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        query = downloader.download_best_match.call_args[0][0]
        assert query == "My title"

    @pytest.mark.asyncio
    async def test_failure_no_title_or_doi(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"authors": ["Smith"]}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "Insufficient metadata" in result.message

    @pytest.mark.asyncio
    async def test_download_failure_propagated(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"title": "Some paper"}
        downloader.download_best_match = AsyncMock(
            return_value=MockDownloadResult(success=False, error_message="Publisher refused")
        )

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "Publisher refused" in result.message

    @pytest.mark.asyncio
    async def test_download_dir_is_publisher_subdir(self, strategy, client, downloader, tmp_path):
        """download_best_match receives a 'publisher' subdirectory."""
        config = _make_config(tmp_path)
        paper = {"title": "Test"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        call_kw = downloader.download_best_match.call_args[1]
        assert call_kw["download_dir"] == config.download_dir / "publisher"


# ============================================================================
# Section 4F: PreprintStrategy
# ============================================================================


class TestPreprintStrategy:
    """Verify the PreprintStrategy constructs ArXiv URLs correctly."""

    @pytest.fixture
    def strategy(self):
        return PreprintStrategy()

    @pytest.fixture
    def client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def downloader(self):
        dl = AsyncMock(spec=MockUnifiedDownloader)
        dl.download_from_url = AsyncMock(
            return_value=MockDownloadResult(success=True, file_path=Path("paper.pdf"))
        )
        return dl

    @pytest.mark.asyncio
    async def test_success_simple_id(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"arxiv_id": "2301.12345"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is True
        assert result.strategy == "preprint"
        # Verify URL construction
        url_arg = downloader.download_from_url.call_args[0][0]
        assert url_arg == "https://arxiv.org/pdf/2301.12345.pdf"

    @pytest.mark.asyncio
    async def test_success_slashed_id(self, strategy, client, downloader, tmp_path):
        """Old-style arxiv IDs like 'hep-th/0401001' should work."""
        config = _make_config(tmp_path)
        paper = {"arxiv_id": "hep-th/0401001"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is True
        url_arg = downloader.download_from_url.call_args[0][0]
        assert url_arg == "https://arxiv.org/pdf/hep-th/0401001.pdf"

    @pytest.mark.asyncio
    async def test_slashed_id_sanitized_in_path(self, strategy, client, downloader, tmp_path):
        """Slashes in arxiv_id are replaced with underscores in the download path."""
        config = _make_config(tmp_path)
        paper = {"arxiv_id": "hep-th/0401001"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        download_path = downloader.download_from_url.call_args[0][1]
        # The filename portion should have _ instead of /
        assert "hep-th_0401001" in download_path.name

    @pytest.mark.asyncio
    async def test_failure_no_arxiv_id(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "No preprint identifier" in result.message

    @pytest.mark.asyncio
    async def test_download_failure_propagated(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"arxiv_id": "2301.12345"}
        downloader.download_from_url = AsyncMock(
            return_value=MockDownloadResult(success=False, error_message="Timeout")
        )

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "Timeout" in result.message

    @pytest.mark.asyncio
    async def test_download_dir_is_preprint_subdir(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path)
        paper = {"arxiv_id": "2301.12345"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        download_path = downloader.download_from_url.call_args[0][1]
        assert "preprint" in str(download_path)


# ============================================================================
# Section 4G: AlternativeStrategy (AUDIT FINDING: confirmed stub)
# ============================================================================


class TestAlternativeStrategy:
    """
    Verify AlternativeStrategy behaviour.

    AUDIT FINDING:
        AlternativeStrategy is a non-functional stub. Regardless of the
        allow_alternative_sources flag it *always* returns failure:
          - When disabled: message = "Alternative sources disabled"
          - When enabled:  message = "No alternative strategy implemented"

        This means the configuration flag has no practical effect beyond
        changing the failure message.  Any code that sets
        allow_alternative_sources=True expecting actual alternative-source
        downloads will silently receive a failure result.
    """

    @pytest.fixture
    def strategy(self):
        return AlternativeStrategy()

    @pytest.fixture
    def client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def downloader(self):
        return AsyncMock(spec=MockUnifiedDownloader)

    @pytest.mark.asyncio
    async def test_disabled_returns_disabled_message(self, strategy, client, downloader, tmp_path):
        config = _make_config(tmp_path, allow_alternative_sources=False)
        paper = {"doi": "10.1234/test", "title": "Test"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert result.strategy == "alternative"
        assert "disabled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_enabled_returns_not_implemented(self, strategy, client, downloader, tmp_path):
        """AUDIT FINDING: Even when enabled, alternative strategy is a stub."""
        config = _make_config(tmp_path, allow_alternative_sources=True)
        paper = {"doi": "10.1234/test", "title": "Test"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "implemented" in result.message.lower()

    @pytest.mark.asyncio
    async def test_never_succeeds_regardless_of_paper(self, strategy, client, downloader, tmp_path):
        """No paper metadata combination can make this strategy succeed."""
        config = _make_config(tmp_path, allow_alternative_sources=True)
        paper = {
            "doi": "10.1234/test",
            "title": "Full metadata",
            "authors": ["Smith"],
            "arxiv_id": "2301.00001",
            "url": "https://example.com/paper.pdf",
        }

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)
        assert result.success is False


# ============================================================================
# Section 4H: InstitutionalStrategy
# ============================================================================


class TestInstitutionalStrategy:
    """Verify the InstitutionalStrategy with mock credentials."""

    @pytest.fixture
    def credentials(self):
        return InstitutionalCredentials(
            username="testuser",
            password="testpass",
            publisher="Elsevier",
            headless=True,
            timeout_ms=30000,
        )

    @pytest.fixture
    def client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def downloader(self):
        return AsyncMock(spec=MockUnifiedDownloader)

    @pytest.mark.asyncio
    async def test_failure_no_credentials(self, client, downloader, tmp_path):
        strategy = InstitutionalStrategy(credentials=None)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "publisher": "Elsevier"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "No institutional credentials" in result.message

    @pytest.mark.asyncio
    async def test_failure_no_publisher(self, credentials, client, downloader, tmp_path):
        """If paper has no publisher and credentials have no publisher, fail."""
        creds_no_pub = InstitutionalCredentials(
            username="u", password="p", publisher=None
        )
        strategy = InstitutionalStrategy(credentials=creds_no_pub)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test"}  # no publisher, no source

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "publisher" in result.message.lower()

    @pytest.mark.asyncio
    async def test_success_with_mock_downloader_fn(self, credentials, client, downloader, tmp_path):
        """When a custom downloader_fn is provided and returns a path, succeed."""
        download_path = tmp_path / "institutional" / "elsevier" / "paper.pdf"
        download_path.parent.mkdir(parents=True, exist_ok=True)

        mock_dl_fn = AsyncMock(return_value=(download_path, {"pages": 10}))
        strategy = InstitutionalStrategy(credentials=credentials, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "publisher": "Elsevier"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is True
        assert result.strategy == "institutional"
        assert result.file_path == download_path
        # Verify the callable received the correct arguments
        mock_dl_fn.assert_called_once()
        call_kwargs = mock_dl_fn.call_args[1]
        assert call_kwargs["doi"] == "10.1234/test"
        assert call_kwargs["publisher"] == "Elsevier"
        assert call_kwargs["username"] == "testuser"
        assert call_kwargs["password"] == "testpass"
        assert call_kwargs["headless"] is True
        assert call_kwargs["timeout"] == 30000

    @pytest.mark.asyncio
    async def test_download_returns_none_path(self, credentials, client, downloader, tmp_path):
        """When downloader_fn returns (None, metadata), result is failure."""
        mock_dl_fn = AsyncMock(return_value=(None, {}))
        strategy = InstitutionalStrategy(credentials=credentials, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "publisher": "Elsevier"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "unavailable" in result.message.lower()

    @pytest.mark.asyncio
    async def test_publisher_from_paper_source_field(self, credentials, client, downloader, tmp_path):
        """When paper has 'source' but not 'publisher', 'source' is used."""
        mock_dl_fn = AsyncMock(return_value=(tmp_path / "paper.pdf", {}))
        strategy = InstitutionalStrategy(credentials=credentials, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "source": "Springer"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        call_kwargs = mock_dl_fn.call_args[1]
        assert call_kwargs["publisher"] == "Springer"

    @pytest.mark.asyncio
    async def test_publisher_fallback_to_credentials(self, client, downloader, tmp_path):
        """When paper has no publisher or source, credential publisher is used."""
        creds = InstitutionalCredentials(
            username="u", password="p", publisher="Wiley"
        )
        mock_dl_fn = AsyncMock(return_value=(tmp_path / "paper.pdf", {}))
        strategy = InstitutionalStrategy(credentials=creds, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        call_kwargs = mock_dl_fn.call_args[1]
        assert call_kwargs["publisher"] == "Wiley"

    @pytest.mark.asyncio
    async def test_output_dir_created(self, credentials, client, downloader, tmp_path):
        """The strategy creates the institutional output directory."""
        mock_dl_fn = AsyncMock(return_value=(tmp_path / "paper.pdf", {}))
        strategy = InstitutionalStrategy(credentials=credentials, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "publisher": "Elsevier"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        expected_dir = config.download_dir / "institutional" / "elsevier"
        assert expected_dir.exists()

    @pytest.mark.asyncio
    async def test_publisher_name_sanitized_in_dir(self, credentials, client, downloader, tmp_path):
        """Publisher name with spaces becomes lowercase with underscores."""
        mock_dl_fn = AsyncMock(return_value=(tmp_path / "paper.pdf", {}))
        strategy = InstitutionalStrategy(credentials=credentials, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "publisher": "Oxford University Press"}

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        call_kwargs = mock_dl_fn.call_args[1]
        output_dir = call_kwargs["output_dir"]
        assert "oxford_university_press" in str(output_dir)

    @pytest.mark.asyncio
    async def test_download_exception_handled(self, credentials, client, downloader, tmp_path):
        """If the downloader_fn raises an exception, the strategy catches it."""
        mock_dl_fn = AsyncMock(side_effect=RuntimeError("Browser crashed"))
        strategy = InstitutionalStrategy(credentials=credentials, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {"doi": "10.1234/test", "publisher": "Elsevier"}

        result = await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        assert result.success is False
        assert "failed" in result.message.lower() or "Browser crashed" in result.message

    @pytest.mark.asyncio
    async def test_url_passed_to_downloader(self, credentials, client, downloader, tmp_path):
        """Paper URL is forwarded to the download callable."""
        mock_dl_fn = AsyncMock(return_value=(tmp_path / "paper.pdf", {}))
        strategy = InstitutionalStrategy(credentials=credentials, downloader_fn=mock_dl_fn)
        config = _make_config(tmp_path)
        paper = {
            "doi": "10.1234/test",
            "url": "https://publisher.com/article/123",
            "publisher": "Elsevier",
        }

        await strategy.try_acquire(paper, client=client, downloader=downloader, config=config)

        call_kwargs = mock_dl_fn.call_args[1]
        assert call_kwargs["url"] == "https://publisher.com/article/123"


# ============================================================================
# Section 4I: BaseStrategy
# ============================================================================


class TestBaseStrategy:
    """Verify the BaseStrategy abstract base class."""

    def test_name_attribute(self):
        assert BaseStrategy.name == "base"

    @pytest.mark.asyncio
    async def test_try_acquire_raises_not_implemented(self):
        strategy = BaseStrategy()
        with pytest.raises(NotImplementedError):
            await strategy.try_acquire(
                {},
                client=AsyncMock(),
                downloader=AsyncMock(),
                config=AcquisitionConfig(),
            )


# ============================================================================
# Section 4J: AcquisitionEngine - strategy fallback order
# ============================================================================


class TestAcquisitionEngineFallback:
    """Verify the engine tries strategies in order and stops on first success."""

    @pytest.mark.asyncio
    async def test_stops_on_first_success(self, tmp_path):
        """Engine returns the result from the first successful strategy."""
        s1 = AsyncMock(spec=BaseStrategy)
        s1.name = "first"
        s1.try_acquire = AsyncMock(
            return_value=AcquisitionResult(False, "first", message="nope")
        )

        s2 = AsyncMock(spec=BaseStrategy)
        s2.name = "second"
        s2.try_acquire = AsyncMock(
            return_value=AcquisitionResult(True, "second", file_path=Path("got_it.pdf"))
        )

        s3 = AsyncMock(spec=BaseStrategy)
        s3.name = "third"
        s3.try_acquire = AsyncMock(
            return_value=AcquisitionResult(True, "third", file_path=Path("also.pdf"))
        )

        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[s1, s2, s3],
        )

        result = await engine.acquire_paper({"title": "Test"})

        assert result.success is True
        assert result.strategy == "second"
        # Third strategy should NOT have been called
        s3.try_acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_strategies_fail(self, tmp_path):
        """When every strategy fails, result has strategy='none'."""
        s1 = AsyncMock(spec=BaseStrategy)
        s1.name = "alpha"
        s1.try_acquire = AsyncMock(
            return_value=AcquisitionResult(False, "alpha", message="fail 1")
        )

        s2 = AsyncMock(spec=BaseStrategy)
        s2.name = "beta"
        s2.try_acquire = AsyncMock(
            return_value=AcquisitionResult(False, "beta", message="fail 2")
        )

        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[s1, s2],
        )

        result = await engine.acquire_paper({"title": "Test"})

        assert result.success is False
        assert result.strategy == "none"
        assert "All acquisition strategies failed" in result.message

    @pytest.mark.asyncio
    async def test_first_strategy_succeeds(self, tmp_path):
        """If the first strategy succeeds, no others are invoked."""
        s1 = AsyncMock(spec=BaseStrategy)
        s1.name = "winner"
        s1.try_acquire = AsyncMock(
            return_value=AcquisitionResult(True, "winner", file_path=Path("w.pdf"))
        )

        s2 = AsyncMock(spec=BaseStrategy)
        s2.name = "loser"
        s2.try_acquire = AsyncMock()

        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[s1, s2],
        )

        result = await engine.acquire_paper({"title": "Test"})

        assert result.success is True
        assert result.strategy == "winner"
        s2.try_acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_strategies_list(self, tmp_path):
        """An engine with no strategies should not crash."""
        config = _make_config(tmp_path)
        # Use a failing strategy instead of empty list to avoid default strategies
        failing = AsyncMock(spec=BaseStrategy)
        failing.name = "fail"
        failing.try_acquire = AsyncMock(
            return_value=AcquisitionResult(False, "fail", message="nope")
        )
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[failing],
        )

        result = await engine.acquire_paper({"title": "Test"})

        assert result.success is False

    @pytest.mark.asyncio
    async def test_download_dir_created(self, tmp_path):
        """acquire_paper creates the download directory."""
        config = _make_config(tmp_path)
        failing = AsyncMock(spec=BaseStrategy)
        failing.name = "fail"
        failing.try_acquire = AsyncMock(
            return_value=AcquisitionResult(False, "fail", message="nope")
        )
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[failing],
        )

        await engine.acquire_paper({"title": "Test"})

        assert config.download_dir.exists()


# ============================================================================
# Section 4K: Default strategy order
# ============================================================================


class TestDefaultStrategyOrder:
    """Verify the default strategy list matches the expected priority."""

    def test_default_strategy_order(self, tmp_path):
        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
        )

        names = [s.name for s in engine.strategies]
        assert names == [
            "open_access",
            "institutional",
            "publisher",
            "preprint",
            "alternative",
        ]

    def test_default_has_five_strategies(self, tmp_path):
        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
        )
        assert len(engine.strategies) == 5


# ============================================================================
# Section 4L: batch_acquire()
# ============================================================================


class TestBatchAcquire:
    """Verify batch_acquire processes papers sequentially."""

    @pytest.mark.asyncio
    async def test_processes_all_papers(self, tmp_path):
        call_order = []

        async def mock_try_acquire(paper, *, client, downloader, config):
            call_order.append(paper.get("title"))
            return AcquisitionResult(True, "mock", file_path=Path("ok.pdf"))

        s = AsyncMock(spec=BaseStrategy)
        s.name = "mock"
        s.try_acquire = mock_try_acquire

        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[s],
        )

        papers = [
            {"title": "Paper A"},
            {"title": "Paper B"},
            {"title": "Paper C"},
        ]
        results = await engine.batch_acquire(papers)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert call_order == ["Paper A", "Paper B", "Paper C"]

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, tmp_path):
        """batch_acquire continues even when some papers fail."""
        call_count = 0

        async def mock_try_acquire(paper, *, client, downloader, config):
            nonlocal call_count
            call_count += 1
            if paper.get("title") == "Failing":
                return AcquisitionResult(False, "mock", message="no match")
            return AcquisitionResult(True, "mock", file_path=Path("ok.pdf"))

        s = AsyncMock(spec=BaseStrategy)
        s.name = "mock"
        s.try_acquire = mock_try_acquire

        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[s],
        )

        papers = [
            {"title": "Success 1"},
            {"title": "Failing"},
            {"title": "Success 2"},
        ]
        results = await engine.batch_acquire(papers)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, tmp_path):
        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[],
        )

        results = await engine.batch_acquire([])
        assert results == []

    @pytest.mark.asyncio
    async def test_single_paper(self, tmp_path):
        s = AsyncMock(spec=BaseStrategy)
        s.name = "mock"
        s.try_acquire = AsyncMock(
            return_value=AcquisitionResult(True, "mock", file_path=Path("one.pdf"))
        )

        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[s],
        )

        results = await engine.batch_acquire([{"title": "Only paper"}])

        assert len(results) == 1
        assert results[0].success is True


# ============================================================================
# Section 4M: Engine construction and close
# ============================================================================


class TestEngineConstruction:
    """Verify engine constructor defaults and teardown."""

    def test_custom_strategies_override_defaults(self, tmp_path):
        custom = [OpenAccessStrategy(), PreprintStrategy()]
        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=custom,
        )
        assert len(engine.strategies) == 2
        assert engine.strategies[0].name == "open_access"
        assert engine.strategies[1].name == "preprint"

    def test_default_config_when_none_provided(self):
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
        )
        assert engine.config.download_dir == Path("downloads")

    @pytest.mark.asyncio
    async def test_close_calls_aclose(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=mock_client,
        )

        await engine.close()

        mock_client.aclose.assert_called_once()


# ============================================================================
# Section 4N: Strategy name attributes
# ============================================================================


class TestStrategyNames:
    """Verify each strategy has the expected name attribute."""

    @pytest.mark.parametrize(
        "cls, expected_name",
        [
            (OpenAccessStrategy, "open_access"),
            (PublisherStrategy, "publisher"),
            (PreprintStrategy, "preprint"),
            (AlternativeStrategy, "alternative"),
            (BaseStrategy, "base"),
        ],
    )
    def test_strategy_name(self, cls, expected_name):
        assert cls.name == expected_name

    def test_institutional_strategy_name(self):
        s = InstitutionalStrategy(credentials=None)
        assert s.name == "institutional"


# ============================================================================
# Section 4O: Edge cases
# ============================================================================


class TestEdgeCases:
    """Additional edge-case coverage."""

    @pytest.mark.asyncio
    async def test_open_access_empty_doi(self, tmp_path):
        """Empty-string DOI treated as falsy."""
        strategy = OpenAccessStrategy()
        config = _make_config(tmp_path)
        paper = {"doi": "", "title": "Test"}

        result = await strategy.try_acquire(
            paper,
            client=AsyncMock(spec=httpx.AsyncClient),
            downloader=AsyncMock(),
            config=config,
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_publisher_empty_title_and_empty_doi(self, tmp_path):
        """Both title and DOI as empty strings should fail."""
        strategy = PublisherStrategy()
        config = _make_config(tmp_path)
        paper = {"title": "", "doi": ""}

        result = await strategy.try_acquire(
            paper,
            client=AsyncMock(spec=httpx.AsyncClient),
            downloader=AsyncMock(),
            config=config,
        )

        assert result.success is False
        assert "Insufficient metadata" in result.message

    @pytest.mark.asyncio
    async def test_preprint_empty_arxiv_id(self, tmp_path):
        """Empty-string arxiv_id treated as falsy."""
        strategy = PreprintStrategy()
        config = _make_config(tmp_path)
        paper = {"arxiv_id": ""}

        result = await strategy.try_acquire(
            paper,
            client=AsyncMock(spec=httpx.AsyncClient),
            downloader=AsyncMock(),
            config=config,
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_acquire_paper_with_empty_dict(self, tmp_path):
        """Passing an empty paper dict should not crash."""
        config = _make_config(tmp_path)
        engine = AcquisitionEngine(
            downloader=MagicMock(),
            client=AsyncMock(spec=httpx.AsyncClient),
            config=config,
            strategies=[
                OpenAccessStrategy(),
                PublisherStrategy(),
                PreprintStrategy(),
                AlternativeStrategy(),
            ],
        )

        result = await engine.acquire_paper({})

        assert result.success is False
        assert result.strategy == "none"

    @pytest.mark.asyncio
    async def test_institutional_credentials_direct_construction(self):
        """InstitutionalCredentials can be constructed directly."""
        creds = InstitutionalCredentials(
            username="u", password="p", publisher="IEEE", headless=False, timeout_ms=5000
        )
        assert creds.username == "u"
        assert creds.password == "p"
        assert creds.publisher == "IEEE"
        assert creds.headless is False
        assert creds.timeout_ms == 5000
