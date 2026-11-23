"""Tests for page operations: rotation, deletion, PDF insertion, undo.

Tests des opérations sur les pages : rotation, suppression, insertion de
PDF, annulation.
"""

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from lestang_pdf_editor.core.result import Ok
from lestang_pdf_editor.data.pdf.pypdfium_engine import PypdfiumPdfEngine
from lestang_pdf_editor.domain.entities.annotation import TextAnnotation

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
    from lestang_pdf_editor.core.result import Err

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


def test_duplicate_page_appends_copies_with_annotations(tmp_path: Path) -> None:
    """Duplicating a page appends a copy; its annotations follow the source.

    Dupliquer une page ajoute une copie ; ses annotations suivent la source.
    """
    pdf = tmp_path / "doc.pdf"
    make_pdf(pdf, pages=2)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    engine.add_annotation(
        doc_id,
        TextAnnotation(page_index=0, rect=(0.1, 0.1, 0.4, 0.1), content="on-page-0"),
    )
    duplicated = engine.duplicate_page(doc_id, 0)
    assert isinstance(duplicated, Ok) and duplicated.value == 3
    assert engine.total_pages(doc_id) == 3

    out = tmp_path / "out.pdf"
    assert isinstance(engine.export(doc_id, str(out), flatten=False), Ok)
    reader = PdfReader(str(out))
    assert len(reader.pages) == 3
    for index in (0, 2):
        annots = reader.pages[index].get("/Annots") or []
        contents = [str(a.get_object()["/Contents"]) for a in annots]
        assert "on-page-0" in contents
    assert not (reader.pages[1].get("/Annots"))


def test_export_watermark_password_and_metadata(tmp_path: Path) -> None:
    """Watermark on every page, AES-256 password, metadata roundtrip.

    Filigrane sur chaque page, mot de passe AES-256, aller-retour des
    métadonnées.
    """
    pdf = tmp_path / "doc.pdf"
    make_pdf(pdf, pages=2)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    assert isinstance(
        engine.set_metadata(doc_id, {"title": "Rapport", "author": "JD"}), Ok
    )
    assert engine.metadata(doc_id)["title"] == "Rapport"

    out = tmp_path / "secret.pdf"
    result = engine.export(
        doc_id, str(out), flatten=False, watermark="DRAFT", password="s3cret!"
    )
    assert isinstance(result, Ok)
    reader = PdfReader(str(out))
    assert reader.is_encrypted
    assert reader.decrypt("s3cret!") != 0
    assert len(reader.pages) == 2
    for page in reader.pages:
        annots = page.get("/Annots") or []
        contents = [str(a.get_object().get("/Contents", "")) for a in annots]
        assert "DRAFT" in contents
    assert reader.metadata is not None
    assert reader.metadata.title == "Rapport"
    assert reader.metadata.author == "JD"


def test_repeated_renders_do_not_leak_pdfium_handles(tmp_path: Path) -> None:
    """Repeated renders explicitly close bitmap/page/document handles.

    Les rendus répétés ferment explicitement les handles pdfium
    (bitmap -> page -> document) : sinon les finaliseurs du GC appellent
    FPDF_ClosePage sur un document déjà libéré (WinError 0xC000001D).
    """
    import gc

    pdf = tmp_path / "doc.pdf"
    make_pdf(pdf, pages=3)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    for _ in range(10):
        for index in range(3):
            result = engine.page_image(doc_id, index, 72)
            assert isinstance(result, Ok)
        gc.collect()


def test_concurrent_renders_are_serialized_safely(tmp_path: Path) -> None:
    """Concurrent renders from several threads must all succeed.

    Des rendus concurrents depuis plusieurs threads doivent tous réussir :
    pypdfium2 n'est pas sûr en FPDF_LoadDocument concurrent (sinon
    « Data format error » voire blocage), le moteur sérialise via un verrou
    et partage un seul PdfDocument par session.
    """
    import threading

    pdf = tmp_path / "doc.pdf"
    make_pdf(pdf, pages=6)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    results: dict[int, object] = {}

    def work(index: int) -> None:
        results[index] = engine.page_image(doc_id, index, 72)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for index in range(6):
        assert isinstance(results[index], Ok), results[index]
    engine.close(doc_id)
    assert engine.revision(doc_id) == 0
