"""Headless tests for the Word-like text box flow (create/edit/move/cancel).

Tests sans affichage du flux de zone de texte façon Word (créer/éditer/
déplacer/annuler).
"""

from dataclasses import replace
from pathlib import Path

import flet as ft
from pypdf import PdfReader, PdfWriter

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui import document_view as dv
from lestang_pdf_editor.core.result import Ok


class FakePage:
    """Minimal page stub for headless UI-helper tests.

    Page factice minimale pour les tests d'helpers UI sans affichage.
    """

    def __init__(self) -> None:
        """Init the stub with empty overlay/controls lists.

        Initialise le bouchon avec des listes overlay/controls vides.
        """
        self.overlay: list = []
        self.controls: list = []

    def update(self) -> None:
        """No-op page update.

        Mise à jour de page factice (no-op).
        """


def make_state(tmp_path: Path) -> AppState:
    """Create an AppState rooted in temporary directories.

    Crée un AppState ancré dans des répertoires temporaires.
    """
    return AppState(
        config_dir=tmp_path / "config",
        cache_dir=tmp_path / "cache",
        assets_dir=Path(__file__).resolve().parents[1] / "assets",
    )


def test_textbox_create_edit_move_cancel(tmp_path: Path) -> None:
    """Create a text box, commit it, re-edit it, move it, cancel an empty one.

    Crée une zone de texte, la valide, la réédite, la déplace, annule une
    zone vide.
    """
    state = make_state(tmp_path)
    state.page = FakePage()
    pdf = tmp_path / "doc.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with pdf.open("wb") as handle:
        writer.write(handle)
    assert isinstance(state.open_path(str(pdf)), Ok)

    canvas = ft.Stack()
    refresh = lambda: None  # noqa: E731

    # Click with the text tool -> default box -> type -> commit (✓).
    # Clic avec l'outil texte -> zone par défaut -> saisie -> validation (✓).
    dv._open_text_editor(state, canvas, refresh, (0.1, 0.1, 0.3, 0.05))
    assert state._editing is not None
    state._editing["field"].value = "Bonjour"
    dv._commit_editing(state, refresh)
    assert state._editing is None
    anns = state.annotations()
    assert len(anns) == 1
    assert anns[0].content == "Bonjour"
    assert anns[0].rect == (0.1, 0.1, 0.3, 0.05)

    # Double-click -> edit existing -> commit keeps the position.
    # Double-clic -> réédition -> la validation conserve la position.
    dv._start_edit(state, canvas, refresh, 0)
    assert state._editing is not None
    state._editing["field"].value = "Modifié"
    dv._commit_editing(state, refresh)
    assert len(state.annotations()) == 1
    assert state.annotations()[0].content == "Modifié"

    # Drag-move persists the new rect in place.
    # Le déplacement persiste le nouveau rectangle sur place.
    state.replace_annotation(
        0, replace(state.annotations()[0], rect=(0.2, 0.2, 0.3, 0.05))
    )
    assert state.annotations()[0].rect == (0.2, 0.2, 0.3, 0.05)

    # Escape on a new empty box discards it (existing one untouched).
    # Échap sur une nouvelle zone vide l'abandonne (l'existante est gardée).
    dv._open_text_editor(state, canvas, refresh, (0.5, 0.5, 0.3, 0.05))
    dv._cancel_editing(state, refresh)
    assert len(state.annotations()) == 1
    assert state.annotations()[0].content == "Modifié"

    # Export carries the text box as a native PDF annotation.
    # L'export embarque la zone de texte comme annotation PDF native.
    out = tmp_path / "out.pdf"
    assert isinstance(state.export_pdf(str(out)), Ok)
    reader = PdfReader(str(out))
    annots = reader.pages[0].get("/Annots") or []
    contents = [str(a.get_object()["/Contents"]) for a in annots]
    assert "Modifié" in contents


def test_engine_replace_annotation_keeps_order(tmp_path: Path) -> None:
    """replace_annotation edits in place without reordering the list.

    replace_annotation modifie sur place sans changer l'ordre de la liste.
    """
    from lestang_pdf_editor.data.pdf.pypdfium_engine import PypdfiumPdfEngine
    from lestang_pdf_editor.domain.entities.annotation import TextAnnotation

    pdf = tmp_path / "doc.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with pdf.open("wb") as handle:
        writer.write(handle)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    engine.add_annotation(
        doc_id, TextAnnotation(page_index=0, rect=(0, 0, 0.2, 0.1), content="one")
    )
    engine.add_annotation(
        doc_id, TextAnnotation(page_index=0, rect=(0, 0, 0.2, 0.1), content="two")
    )
    result = engine.replace_annotation(
        doc_id,
        0,
        TextAnnotation(page_index=0, rect=(0.1, 0.1, 0.2, 0.1), content="uno"),
    )
    assert isinstance(result, Ok)
    anns = engine.annotations(doc_id)
    assert [a.content for a in anns] == ["uno", "two"]
    assert anns[0].rect == (0.1, 0.1, 0.2, 0.1)
