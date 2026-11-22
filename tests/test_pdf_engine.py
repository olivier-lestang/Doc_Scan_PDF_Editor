"""Tests for the pypdfium2/pypdf PDF engine (open, render, annotate, export).

Tests du moteur PDF pypdfium2/pypdf (ouverture, rendu, annotation,
export).
"""

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from docscanner.core.result import Ok
from docscanner.data.pdf.pypdfium_engine import PypdfiumPdfEngine
from docscanner.domain.entities.annotation import (
    HighlightAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)

pytest.importorskip("pypdfium2")
Image = pytest.importorskip("PIL.Image")


def make_pdf(path: Path) -> None:
    """Create a one-page A4 PDF at the given path.

    Crée un PDF d'une page A4 au chemin donné.
    """
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with path.open("wb") as handle:
        writer.write(handle)


def make_png(path: Path) -> None:
    """Create a small RGB PNG image at the given path.

    Crée une petite image PNG RVB au chemin donné.
    """
    Image.new("RGB", (320, 200), (200, 210, 220)).save(path)


def test_open_pdf_detects_version_and_pages(tmp_path: Path) -> None:
    """Opening a PDF returns its version and page count.

    L'ouverture d'un PDF retourne sa version et son nombre de pages.
    """
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path)
    engine = PypdfiumPdfEngine()
    result = engine.open(str(pdf_path))
    assert isinstance(result, Ok)
    document = result.value
    assert document.pdf_version is not None
    assert document.pdf_version.is_iso_32000_1 or document.pdf_version.major == 1
    assert len(document.pages) == 1


def test_render_page_returns_rgb_image(tmp_path: Path) -> None:
    """Rendering a page at 100 DPI returns a sized RGB buffer.

    Le rendu d'une page à 100 DPI retourne un tampon RVB dimensionné.
    """
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf_path))
    assert isinstance(document, Ok)
    rendered = engine.render_page(document.value.document_id, 0, 100)
    assert isinstance(rendered, Ok)
    assert rendered.value.channels == 3
    assert rendered.value.width == pytest.approx(595 * 100 / 72, rel=0.05)


def test_export_pdf_with_native_annotations(tmp_path: Path) -> None:
    """Exported PDF contains the FreeText/Square/Highlight annotations.

    Le PDF exporté contient les annotations FreeText/Square/Highlight.
    """
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(pdf_path))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    assert isinstance(
        engine.add_annotation(
            doc_id,
            TextAnnotation(
                page_index=0,
                rect=(0.1, 0.1, 0.5, 0.08),
                content="Hello",
                font_size_pt=18,
            ),
        ),
        Ok,
    )
    engine.add_annotation(
        doc_id, RectangleAnnotation(page_index=0, rect=(0.2, 0.3, 0.4, 0.2))
    )
    engine.add_annotation(
        doc_id, HighlightAnnotation(page_index=0, rect=(0.1, 0.5, 0.6, 0.05))
    )
    out = tmp_path / "out.pdf"
    result = engine.export(doc_id, str(out), flatten=False)
    assert isinstance(result, Ok)
    reader = PdfReader(str(out))
    annots = reader.pages[0].get("/Annots")
    assert annots is not None and len(annots) == 3
    subtypes = {a.get_object()["/Subtype"] for a in annots}
    assert subtypes == {"/FreeText", "/Square", "/Highlight"}


def test_open_image_and_export_as_pdf(tmp_path: Path) -> None:
    """An image file opens as a one-page document and exports to PDF.

    Un fichier image s'ouvre comme document d'une page et s'exporte en PDF.
    """
    png_path = tmp_path / "scan.png"
    make_png(png_path)
    engine = PypdfiumPdfEngine()
    document = engine.open(str(png_path))
    assert isinstance(document, Ok)
    doc_id = document.value.document_id
    assert len(document.value.pages) == 1
    engine.add_annotation(
        doc_id, TextAnnotation(page_index=0, rect=(0.1, 0.1, 0.4, 0.1), content="Note")
    )
    out = tmp_path / "scan.pdf"
    result = engine.export(doc_id, str(out), flatten=False)
    assert isinstance(result, Ok)
    reader = PdfReader(str(out))
    assert len(reader.pages) == 1
    assert len(reader.pages[0].get("/Annots") or []) == 1
