"""Concrete PdfEngine: render with pypdfium2, annotate/export with pypdf.

Moteur PdfEngine concret : rendu avec pypdfium2, annotation/export avec
pypdf.

Annotations are written as native PDF annotations (/FreeText, /Square,
/Highlight) so every PDF viewer can read them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from docscanner.core.image_buffer import ImageBuffer
from docscanner.core.result import Err, Ok, Result
from docscanner.domain.entities.annotation import (
    Annotation,
    HighlightAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)
from docscanner.domain.entities.document import Document, Page, detect_pdf_version

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
"""File extensions opened as single-page image documents.

Extensions de fichiers ouverts comme documents image d'une page.
"""


@dataclass
class _OpenDocument:
    """Internal session state for one opened document.

    État de session interne pour un document ouvert.
    """

    document_id: str
    source_path: str
    is_pdf: bool
    page_count: int
    pdf_version: object | None
    replacements: dict[int, ImageBuffer] = field(default_factory=dict)
    annotations: list[Annotation] = field(default_factory=list)


def _pil_to_buffer(image: Image.Image) -> ImageBuffer:
    """Convert a PIL image to an RGB ImageBuffer.

    Convertit une image PIL en ImageBuffer RVB.
    """
    rgb = image.convert("RGB")
    return ImageBuffer(
        width=rgb.width,
        height=rgb.height,
        channels=3,
        data=rgb.tobytes(),
    )


def _buffer_to_pil(buffer: ImageBuffer) -> Image.Image:
    """Convert an RGB ImageBuffer back to a PIL image.

    Convertit un ImageBuffer RVB en image PIL.
    """
    from PIL import Image

    return Image.frombytes("RGB", (buffer.width, buffer.height), buffer.data)


def _annotation_to_pdf_dict(
    annotation: Annotation, page_width: float, page_height: float
) -> DictionaryObject:
    """Build a native PDF annotation dictionary from a domain annotation.

    Construit un dictionnaire d'annotation PDF natif à partir d'une
    annotation du domaine.

    Coordinates are normalized (origin top-left); PDF user space has its
    origin at the bottom-left, so Y is flipped here.
    """
    x, y, w, h = annotation.rect
    x1 = x * page_width
    x2 = (x + w) * page_width
    y1 = (1 - (y + h)) * page_height
    y2 = (1 - y) * page_height
    rect = ArrayObject(
        [FloatObject(x1), FloatObject(y1), FloatObject(x2), FloatObject(y2)]
    )
    annot = DictionaryObject()
    annot[NameObject("/Type")] = NameObject("/Annot")
    annot[NameObject("/Rect")] = rect
    annot[NameObject("/F")] = NumberObject(4)
    if isinstance(annotation, TextAnnotation):
        annot[NameObject("/Subtype")] = NameObject("/FreeText")
        annot[NameObject("/Contents")] = TextStringObject(annotation.content)
        font_name = "/Helv"
        if annotation.font_family.lower().startswith("times"):
            font_name = "/TiRo"
        elif annotation.font_family.lower().startswith("courier"):
            font_name = "/Cour"
        da = f"{font_name} {annotation.font_size_pt} Tf 0 g"
        annot[NameObject("/DA")] = TextStringObject(da)
    elif isinstance(annotation, RectangleAnnotation):
        annot[NameObject("/Subtype")] = NameObject("/Square")
        annot[NameObject("/C")] = ArrayObject(
            [
                FloatObject(int(annotation.stroke_color[1:3], 16) / 255),
                FloatObject(int(annotation.stroke_color[3:5], 16) / 255),
                FloatObject(int(annotation.stroke_color[5:7], 16) / 255),
            ]
        )
        annot[NameObject("/BS")] = DictionaryObject(
            {
                NameObject("/W"): FloatObject(annotation.stroke_width_pt),
                NameObject("/S"): NameObject("/S"),
            }
        )
    elif isinstance(annotation, HighlightAnnotation):
        annot[NameObject("/Subtype")] = NameObject("/Highlight")
        annot[NameObject("/C")] = ArrayObject(
            [
                FloatObject(int(annotation.color[1:3], 16) / 255),
                FloatObject(int(annotation.color[3:5], 16) / 255),
                FloatObject(int(annotation.color[5:7], 16) / 255),
            ]
        )
    else:  # pragma: no cover - exhaustive union
        msg = f"unsupported annotation: {annotation!r}"
        raise TypeError(msg)
    return annot


class PypdfiumPdfEngine:
    """PdfEngine backed by pypdfium2 (render) and pypdf (annotate/export).

    Moteur PdfEngine adossé à pypdfium2 (rendu) et pypdf (annotation /
    export).
    """

    def __init__(self) -> None:
        """Create the engine with an empty document registry.

        Crée le moteur avec un registre de documents vide.
        """
        self._documents: dict[str, _OpenDocument] = {}

    def open(self, path: str) -> Result[Document, str]:
        """Open a PDF or image file as a Document.

        Ouvre un fichier PDF ou image comme Document.
        """
        try:
            suffix = Path(path).suffix.lower()
            if suffix in IMAGE_SUFFIXES:
                return self._open_image(path)
            return self._open_pdf(path)
        except Exception as exc:
            return Err(f"cannot open {path}: {exc}")

    def _open_image(self, path: str) -> Result[Document, str]:
        """Open an image file as a single-page document.

        Ouvre un fichier image comme document d'une page.
        """
        from PIL import Image

        with Image.open(path) as pil:
            buffer = _pil_to_buffer(pil)
        document_id = uuid.uuid4().hex
        page = Page(index=0, image=buffer)
        self._documents[document_id] = _OpenDocument(
            document_id=document_id,
            source_path=path,
            is_pdf=False,
            page_count=1,
            pdf_version=None,
            replacements={0: buffer},
        )
        return Ok(Document(document_id=document_id, pages=(page,)))

    def _open_pdf(self, path: str) -> Result[Document, str]:
        """Open a PDF file, reading its version and page count.

        Ouvre un fichier PDF, en lisant sa version et son nombre de pages.
        """
        with Path(path).open("rb") as handle:
            header = handle.read(16)
        version = detect_pdf_version(header)
        reader = PdfReader(path)
        page_count = len(reader.pages)
        document_id = uuid.uuid4().hex
        pages = tuple(Page(index=i) for i in range(page_count))
        self._documents[document_id] = _OpenDocument(
            document_id=document_id,
            source_path=path,
            is_pdf=True,
            page_count=page_count,
            pdf_version=version,
        )
        return Ok(Document(document_id=document_id, pages=pages, pdf_version=version))

    def set_page_image(
        self, document_id: str, page_index: int, image: ImageBuffer
    ) -> Result[None, str]:
        """Replace a page's rendered image (used after enhancement).

        Remplace l'image rendue d'une page (utilisé après amélioration).
        """
        session = self._documents.get(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        session.replacements[page_index] = image
        return Ok(None)

    def page_image(
        self, document_id: str, page_index: int, dpi: int
    ) -> Result[ImageBuffer, str]:
        """Return a page as a raw image (replacement or rendered at DPI).

        Retourne une page en image brute (remplacement ou rendu au DPI).
        """
        session = self._documents.get(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        if page_index in session.replacements:
            return Ok(session.replacements[page_index])
        if not session.is_pdf:
            return Err("image document without stored image")
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(session.source_path)
        page = pdf[page_index]
        bitmap = page.render(scale=dpi / 72.0)
        pil = bitmap.to_pil()
        return Ok(_pil_to_buffer(pil))

    def add_annotation(
        self, document_id: str, annotation: Annotation
    ) -> Result[None, str]:
        """Attach an annotation to the in-memory document session.

        Attache une annotation à la session du document en mémoire.
        """
        session = self._documents.get(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        session.annotations.append(annotation)
        return Ok(None)

    def annotations(self, document_id: str) -> tuple[Annotation, ...]:
        """Return the annotations recorded for a document.

        Retourne les annotations enregistrées pour un document.
        """
        session = self._documents.get(document_id)
        if session is None:
            return ()
        return tuple(session.annotations)

    def export(
        self, document_id: str, destination_path: str, *, flatten: bool
    ) -> Result[str, str]:
        """Export the document as PDF with native annotations.

        Exporte le document en PDF avec des annotations natives.
        """
        session = self._documents.get(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        try:
            if session.is_pdf and not session.replacements and not flatten:
                self._export_pdf_copy(session, destination_path)
            else:
                self._export_from_images(session, destination_path)
            return Ok(destination_path)
        except Exception as exc:
            return Err(f"export failed: {exc}")

    def _export_pdf_copy(self, session: _OpenDocument, destination_path: str) -> None:
        """Copy the source PDF and add the annotations natively.

        Copie le PDF source et ajoute les annotations nativement.
        """
        reader = PdfReader(session.source_path)
        writer = PdfWriter()
        writer.append(reader)
        self._apply_annotations(writer, session)
        with Path(destination_path).open("wb") as handle:
            writer.write(handle)

    def _export_from_images(
        self, session: _OpenDocument, destination_path: str
    ) -> None:
        """Rebuild a PDF from page images, then add annotations.

        Reconstruit un PDF à partir des images des pages, puis ajoute les
        annotations.
        """
        images = [
            _buffer_to_pil(session.replacements[i])
            for i in range(session.page_count)
            if i in session.replacements
        ]
        if not images:
            msg = "no page images available for export"
            raise ValueError(msg)
        tmp_pdf = Path(destination_path).with_suffix(".tmp.pdf")
        images[0].save(
            tmp_pdf,
            save_all=True,
            append_images=images[1:],
            resolution=300.0,
        )
        reader = PdfReader(str(tmp_pdf))
        writer = PdfWriter()
        writer.append(reader)
        self._apply_annotations(writer, session)
        with Path(destination_path).open("wb") as handle:
            writer.write(handle)
        tmp_pdf.unlink(missing_ok=True)

    def _apply_annotations(self, writer: PdfWriter, session: _OpenDocument) -> None:
        """Write all session annotations into the writer's pages.

        Écrit toutes les annotations de la session dans les pages du
        writer.
        """
        by_page: dict[int, list[DictionaryObject]] = {}
        for annotation in session.annotations:
            page = writer.pages[annotation.page_index]
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            by_page.setdefault(annotation.page_index, []).append(
                _annotation_to_pdf_dict(annotation, width, height)
            )
        for page_index, annots in by_page.items():
            page = writer.pages[page_index]
            existing = page.get("/Annots")
            array = existing if isinstance(existing, ArrayObject) else ArrayObject()
            for annot in annots:
                array.append(annot)
            page[NameObject("/Annots")] = array

    def render_page(
        self, document_id: str, page_index: int, dpi: int
    ) -> Result[ImageBuffer, str]:
        """Render one page to a raw image at the requested DPI.

        Rend une page en image brute au DPI demandé.
        """
        return self.page_image(document_id, page_index, dpi)
