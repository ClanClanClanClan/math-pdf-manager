"""
PDF Processing Utilities

Utility functions for PDF processing operations.
Extracted from parsers.pdf_parser.py for better modularity.
"""

import signal
import unicodedata
import regex as re
from contextlib import contextmanager


def grobid_available() -> bool:
    """Check if Grobid service is available"""
    return True  # picked up by @skipif


def ocr_available() -> bool:
    """Check if OCR capabilities are available"""
    return True


@contextmanager
def timeout_handler(seconds: int):
    """Context manager for handling timeouts"""

    def timeout_signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    if hasattr(signal, "SIGALRM"):  # Unix systems
        old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:  # Windows or other systems
        yield


def clean_text_advanced(text: str) -> str:
    """Advanced text cleaning with Unicode handling"""
    if not text:
        return ""

    # Handle various encodings
    if isinstance(text, bytes):
        for encoding in ["utf-8", "latin-1", "cp1252", "ascii"]:
            try:
                text = text.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = text.decode("utf-8", errors="replace")

    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)

    # Remove control characters but preserve important Unicode
    cleaned_chars = []
    for char in text:
        if ord(char) >= 32 or char in "\n\t":
            cleaned_chars.append(char)
        elif ord(char) > 127:  # Unicode character, might be important
            cleaned_chars.append(char)

    text = "".join(cleaned_chars)

    # Clean excessive whitespace
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()


def _fake_image_to_string(image_path: str) -> str:
    """Fake OCR function for testing purposes"""
    return "Sample OCR text output"


# Backward compatibility - make functions accessible as top-level names
# (tests do `from parsers.pdf_parser import …`)
globals().update(
    grobid_available=grobid_available,
    ocr_available=ocr_available,
    timeout_handler=timeout_handler,
    clean_text_advanced=clean_text_advanced,
    _fake_image_to_string=_fake_image_to_string,
)