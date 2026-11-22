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


PDF_FONT_NAMES: dict[str, tuple[str, str, str, str]] = {
    "Helvetica": ("/Helv", "/HeBo", "/HeOb", "/HeBO"),
    "Arial": ("/Helv", "/HeBo", "/HeOb", "/HeBO"),
    "Times New Roman": ("/TiRo", "/TiBo", "/TiIt", "/TiBI"),
    "Courier New": ("/Cour", "/CoBo", "/CoOb", "/CoBO"),
}
"""Base-14 PDF font names: (regular, bold, italic, bold-italic).

Noms de polices PDF de base 14 : (régulier, gras, italique, gras-italique).
"""


def _pdf_font_name(family: str, bold: bool, italic: bool) -> str:
    """Map a UI font family + style to a base-14 PDF font name.

    Convertit une police d'UI + style en nom de police PDF de base 14.
    """
    regular, bold_name, italic_name, bold_italic_name = PDF_FONT_NAMES.get(
        family, PDF_FONT_NAMES["Helvetica"]
    )
    if bold and italic:
        return bold_italic_name
    if bold:
        return bold_name
    if italic:
        return italic_name
    return regular


def _hex_color_array(color: str) -> ArrayObject:
    """Convert a '#RRGGBB' string to a PDF RGB color array.

    Convertit une chaîne « #RRGGBB » en tableau de couleur RVB PDF.
    """
    return ArrayObject(
        [
            FloatObject(int(color[1:3], 16) / 255),
            FloatObject(int(color[3:5], 16) / 255),
            FloatObject(int(color[5:7], 16) / 255),
        ]
    )


def _annotation_to_pdf_dicts(
    annotation: Annotation, page_width: float, page_height: float
) -> list[DictionaryObject]:
    """Build native PDF annotation dictionaries from a domain annotation.

    Construit les dictionnaires d'annotations PDF natifs à partir d'une
    annotation du domaine (plusieurs si soulignement/surlignage de texte).

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
    extra: list[DictionaryObject] = []
    if isinstance(annotation, TextAnnotation):
        annot[NameObject("/Subtype")] = NameObject("/FreeText")
        annot[NameObject("/Contents")] = TextStringObject(annotation.content)
        font_name = _pdf_font_name(
            annotation.font_family, annotation.bold, annotation.italic
        )
        r, g, b = (int(annotation.color[i : i + 2], 16) / 255 for i in (1, 3, 5))
        da = f"{font_name} {annotation.font_size_pt} Tf {r:.3f} {g:.3f} {b:.3f} rg"
        annot[NameObject("/DA")] = TextStringObject(da)
        if annotation.underline:
            underline = DictionaryObject()
            underline[NameObject("/Type")] = NameObject("/Annot")
            underline[NameObject("/Subtype")] = NameObject("/Underline")
            underline[NameObject("/Rect")] = rect
            underline[NameObject("/F")] = NumberObject(4)
            extra.append(underline)
        if annotation.highlight_color:
            highlight = DictionaryObject()
            highlight[NameObject("/Type")] = NameObject("/Annot")
            highlight[NameObject("/Subtype")] = NameObject("/Highlight")
            highlight[NameObject("/Rect")] = rect
            highlight[NameObject("/F")] = NumberObject(4)
            highlight[NameObject("/C")] = _hex_color_array(annotation.highlight_color)
            extra.append(highlight)
    elif isinstance(annotation, RectangleAnnotation):
        annot[NameObject("/Subtype")] = NameObject("/Square")
        annot[NameObject("/C")] = _hex_color_array(annotation.stroke_color)
        annot[NameObject("/BS")] = DictionaryObject(
            {
                NameObject("/W"): FloatObject(annotation.stroke_width_pt),
                NameObject("/S"): NameObject("/S"),
            }
        )
    elif isinstance(annotation, HighlightAnnotation):
        annot[NameObject("/Subtype")] = NameObject("/Highlight")
        annot[NameObject("/C")] = _hex_color_array(annotation.color)
    else:  # pragma: no cover - exhaustive union
        msg = f"unsupported annotation: {annotation!r}"
        raise TypeError(msg)
    return [annot, *extra]


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
            by_page.setdefault(annotation.page_index, []).extend(
                _annotation_to_pdf_dicts(annotation, width, height)
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
