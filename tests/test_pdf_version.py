"""Tests for PDF version detection and the support matrix.

Tests de la détection de version PDF et de la matrice de support.
"""

from docscanner.domain.entities.document import (
    detect_pdf_version,
    support_level,
)


def test_detects_pdf_17_as_iso_32000_1() -> None:
    """A `%PDF-1.7` header is detected as ISO 32000-1.

    Un en-tête `%PDF-1.7` est détecté comme ISO 32000-1.
    """
    version = detect_pdf_version(b"%PDF-1.7\n%binary\n")
    assert version is not None
    assert version.is_iso_32000_1
    assert support_level(version) == "full"


def test_detects_pdf_20_as_iso_32000_2() -> None:
    """A `%PDF-2.0` header is detected as ISO 32000-2 with full support.

    Un en-tête `%PDF-2.0` est détecté comme ISO 32000-2, support complet.
    """
    version = detect_pdf_version(b"%PDF-2.0\n")
    assert version is not None
    assert version.is_iso_32000_2
    assert support_level(version) == "full"


def test_old_versions_are_read_only() -> None:
    """PDF 1.0-1.3 are detected and supported read-only.

    Les PDF 1.0 à 1.3 sont détectés et supportés en lecture seule.
    """
    for minor in (0, 1, 2, 3):
        version = detect_pdf_version(f"%PDF-1.{minor}".encode())
        assert version is not None
        assert support_level(version) == "read-only"


def test_pdf_14_is_full_support() -> None:
    """PDF 1.4 (transparency, JBIG2) has full support.

    Le PDF 1.4 (transparence, JBIG2) a un support complet.
    """
    version = detect_pdf_version(b"%PDF-1.4\n")
    assert version is not None
    assert support_level(version) == "full"


def test_future_version_is_limited() -> None:
    """Unknown future versions open read-only with a warning (limited).

    Les versions futures inconnues s'ouvrent en lecture seule avec un
    avertissement (support limité).
    """
    version = detect_pdf_version(b"%PDF-3.0\n")
    assert version is not None
    assert support_level(version) == "future-limited"


def test_invalid_header_returns_none() -> None:
    """A non-PDF header yields None instead of an error.

    Un en-tête non PDF renvoie None au lieu d'une erreur.
    """
    assert detect_pdf_version(b"not a pdf") is None
