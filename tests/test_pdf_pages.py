"""Tests for page operations: rotation, deletion, PDF insertion, undo.

Tests des opérations sur les pages : rotation, suppression, insertion de
PDF, annulation.
"""

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from docscanner.core.result import Ok
from docscanner.data.pdf.pypdfium_engine import PypdfiumPdfEngine
from docscanner.domain.entities.annotation import TextAnnotation

pytest.importorskip("pypdfium2")


def make_pdf(path: Path, pages: int = 1) -> None:
    """Create a PDF with the given number of blank A4 pages.

    Crée un PDF avec le nombre de pages A4 vierges demandé.
    """
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    with path.open("wb") as handle:
        writer.write(handle)


def test_rotate_delete_insert_and_export(tmp_path: Path) -> None:
    """Insert a PDF, delete a page, rotate another: export reflects all.

    Insère un PDF, supprime une page, pivote une autre : l'export reflète
    tout.
    """
    main_pdf = tmp_path / "main.pdf"
    extra_pdf = tmp_path / "extra.pdf"
    make_pdf(main_pdf, pages=2)
    make_pdf(extra_pdf, pages=1)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(main_pdf))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    assert engine.total_pages(doc_id) == 2

    inserted = engine.insert_pdf(doc_id, str(extra_pdf))
    assert isinstance(inserted, Ok) and inserted.value == 1
    assert engine.total_pages(doc_id) == 3

    deleted = engine.delete_page(doc_id, 0)
    assert isinstance(deleted, Ok)
    assert engine.total_pages(doc_id) == 2

    rotated = engine.rotate_page(doc_id, 1, 90)
    assert isinstance(rotated, Ok)

    # Annotation on the deleted page 0 must be skipped at export.
    engine.add_annotation(
        doc_id,
        TextAnnotation(page_index=0, rect=(0.1, 0.1, 0.4, 0.1), content="gone"),
    )
    engine.add_annotation(
        doc_id,
        TextAnnotation(page_index=1, rect=(0.1, 0.1, 0.4, 0.1), content="kept"),
    )
    out = tmp_path / "out.pdf"
    result = engine.export(doc_id, str(out), flatten=False)
    assert isinstance(result, Ok)
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2
    assert int(reader.pages[0].get("/Rotate", 0)) == 90
    annots = reader.pages[0].get("/Annots") or []
    assert len(annots) == 1
    assert str(annots[0].get_object()["/Contents"]) == "kept"


def test_delete_last_page_is_refused(tmp_path: Path) -> None:
    """Deleting the only page of a document is refused.

    Supprimer l'unique page d'un document est refusé.
    """
    pdf = tmp_path / "one.pdf"
    make_pdf(pdf, pages=1)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf))
    assert isinstance(document, Ok)
    from docscanner.core.result import Err

    result = engine.delete_page(document.value.document_id, 0)
    assert isinstance(result, Err)


def test_undo_removes_last_annotation(tmp_path: Path) -> None:
    """remove_last_annotation pops annotations in LIFO order.

    remove_last_annotation retire les annotations en ordre LIFO.
    """
    pdf = tmp_path / "doc.pdf"
    make_pdf(pdf, pages=1)
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
    assert len(engine.annotations(doc_id)) == 2
    assert isinstance(engine.remove_last_annotation(doc_id), Ok)
    remaining = engine.annotations(doc_id)
    assert len(remaining) == 1
    assert isinstance(remaining[0], TextAnnotation)
    assert remaining[0].content == "one"
