"""Headless end-to-end test of AppState on a generated PDF and image.

Test de bout en bout sans affichage de AppState sur un PDF et une image
générés.
"""

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.core.result import Ok
from lestang_pdf_editor.domain.entities.annotation import TextAnnotation

pytest.importorskip("pypdfium2")
Image = pytest.importorskip("PIL.Image")


def make_pdf(path: Path) -> None:
    """Create a two-page PDF at the given path.

    Crée un PDF de deux pages au chemin donné.
    """
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=595, height=842)
    with path.open("wb") as handle:
        writer.write(handle)


def make_state(tmp_path: Path) -> AppState:
    """Create an AppState rooted in temporary directories.

    Crée un AppState racine dans des répertoires temporaires.
    """
    return AppState(
        config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache",
        assets_dir=Path(__file__).resolve().parents[1] / "assets",
    )


def test_open_render_annotate_export_roundtrip(tmp_path: Path) -> None:
    """Open a PDF, render a page PNG, annotate, export: all succeed.

    Ouvrir un PDF, rendre une page en PNG, annoter, exporter : tout réussit.
    """
    state = make_state(tmp_path)
    pdf_path = tmp_path / "doc.pdf"
    make_pdf(pdf_path)
    opened = state.open_path(str(pdf_path))
    assert isinstance(opened, Ok)
    assert state.page_count() == 2
    png = state.page_png_path(0, 100)
    assert isinstance(png, Ok) and png.value.exists()
    assert isinstance(
        state.add_annotation(
            TextAnnotation(page_index=0, rect=(0.1, 0.1, 0.5, 0.08), content="Note")
        ),
        Ok,
    )
    out = tmp_path / "exported.pdf"
    exported = state.export_pdf(str(out))
    assert isinstance(exported, Ok)
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2
    assert len(reader.pages[0].get("/Annots") or []) == 1


def test_settings_persist_across_state_instances(tmp_path: Path) -> None:
    """DPI and UI language set on one state are reloaded by a new one.

    Le DPI et la langue d'UI réglés sur un état sont rechargés par un
    nouvel état.
    """
    state = make_state(tmp_path)
    state.set_dpi(600)
    state.set_ui_language("fr")
    reloaded = make_state(tmp_path)
    assert reloaded.settings.scan.dpi == 600
    assert reloaded.settings.language == "fr"
    assert reloaded.t("settings.title") == "Réglages"


def test_zoom_is_clamped_and_toggle_tool_works(tmp_path: Path) -> None:
    """Zoom stays within bounds; tools toggle on repeated clicks.

    Le zoom reste dans les bornes ; les outils se basculent au 2e clic.
    """
    from lestang_pdf_editor.app.state import ZOOM_MAX, ZOOM_MIN

    state = make_state(tmp_path)
    assert state.zoom == 1.0
    for _ in range(200):
        state.zoom_in()
    assert state.zoom == ZOOM_MAX
    for _ in range(400):
        state.zoom_out()
    assert state.zoom == ZOOM_MIN
    state.zoom_reset()
    assert state.zoom == 1.0
    state.toggle_tool("text")
    assert state.tool == "text"
    state.toggle_tool("text")
    assert state.tool == "select"


def test_author_and_timestamp(tmp_path: Path) -> None:
    """Author name comes from settings; timestamp carries the timezone.

    Le nom d'auteur vient des réglages ; l'horodatage porte le fuseau
    horaire.
    """
    from dataclasses import replace

    state = make_state(tmp_path)
    state.settings = replace(state.settings, first_name="Jean", last_name="Dupont")
    assert state.author_name() == "Jean Dupont"
    ts = state.new_timestamp()
    assert "+" in ts or "-" in ts[19:] or "Z" in ts  # timezone offset present


def test_recent_files_and_theme_persist(tmp_path: Path) -> None:
    """Opened files land in recent_files; theme mode persists.

    Les fichiers ouverts vont dans recent_files ; le thème persiste.
    """
    pdf_a = tmp_path / "a.pdf"
    pdf_b = tmp_path / "b.pdf"
    for path in (pdf_a, pdf_b):
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with path.open("wb") as handle:
            writer.write(handle)
    state = make_state(tmp_path)
    assert state.open_path(str(pdf_a)).__class__.__name__ == "Ok"
    assert state.open_path(str(pdf_b)).__class__.__name__ == "Ok"
    state.set_theme_mode("dark")
    reloaded = make_state(tmp_path)
    assert reloaded.settings.recent_files[0] == str(pdf_b)
    assert str(pdf_a) in reloaded.settings.recent_files
    assert reloaded.settings.theme_mode == "dark"


def test_i18n_files_have_identical_keys() -> None:
    """All four i18n assets expose exactly the same keys as en.json.

    Les quatre assets i18n exposent exactement les mêmes clés que en.json.
    """
    import json

    assets = Path(__file__).resolve().parents[1] / "assets" / "i18n"
    reference = json.loads((assets / "en.json").read_text(encoding="utf-8"))

    def keys(node: object, prefix: str = "") -> set[str]:
        out: set[str] = set()
        if isinstance(node, dict):
            for key, value in node.items():
                out |= keys(value, f"{prefix}{key}.")
        else:
            out.add(prefix.rstrip("."))
        return out

    reference_keys = keys(reference)
    for code in ("fr", "es", "zh"):
        other = json.loads((assets / f"{code}.json").read_text(encoding="utf-8"))
        assert keys(other) == reference_keys, code
