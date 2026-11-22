"""Tests for langdetect-based language detection.

Tests de la détection de langue basée sur langdetect.
"""

import pytest

from docscanner.core.result import Ok
from docscanner.data.ocr.language_detector import LangDetectLanguageDetector

pytest.importorskip("langdetect")


def test_detects_french() -> None:
    """A French sentence is detected as French.

    Une phrase en français est détectée comme du français.
    """
    result = LangDetectLanguageDetector().detect_language(
        "Bonjour, ceci est un document important en français."
    )
    assert isinstance(result, Ok)
    assert result.value.code == "fr"


def test_detects_english() -> None:
    """An English sentence is detected as English.

    Une phrase en anglais est détectée comme de l'anglais.
    """
    result = LangDetectLanguageDetector().detect_language(
        "This is an important document written in English."
    )
    assert isinstance(result, Ok)
    assert result.value.code == "en"


def test_empty_text_is_an_error() -> None:
    """Empty text returns an error, not a crash.

    Un texte vide renvoie une erreur, pas un crash.
    """
    from docscanner.core.result import Err

    result = LangDetectLanguageDetector().detect_language("   ")
    assert isinstance(result, Err)
