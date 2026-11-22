"""Tests for the OCR language catalog.

Tests du catalogue de langues OCR.
"""

from pathlib import Path

from docscanner.data.ocr.language_catalog import OcrLanguageCatalog

ASSET = Path(__file__).resolve().parents[1] / "assets" / "ocr" / "languages.json"


def test_catalog_contains_the_four_initial_languages() -> None:
    """French, English, Spanish and Simplified Chinese are bundled.

    Français, anglais, espagnol et chinois simplifié sont embarqués.
    """
    catalog = OcrLanguageCatalog.from_json_file(ASSET)
    bundled_codes = {lang.code for lang in catalog.bundled()}
    assert {"fra", "eng", "spa", "chi_sim"} <= bundled_codes


def test_select_returns_only_chosen_languages() -> None:
    """select() keeps the user's choice and skips unknown codes.

    select() conserve le choix de l'utilisateur et ignore les codes
    inconnus.
    """
    catalog = OcrLanguageCatalog.from_json_file(ASSET)
    chosen = catalog.select(("fra", "chi_sim", "xxx"))
    assert {lang.code for lang in chosen} == {"fra", "chi_sim"}


def test_get_finds_language_by_code() -> None:
    """get() returns the language for a known code, None otherwise.

    get() retourne la langue pour un code connu, None sinon.
    """
    catalog = OcrLanguageCatalog.from_json_file(ASSET)
    eng = catalog.get("eng")
    assert eng is not None
    assert eng.names["fr"] == "Anglais"
    assert catalog.get("xxx") is None
