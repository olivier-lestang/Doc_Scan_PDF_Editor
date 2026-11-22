"""Concrete PdfEngine: render with pypdfium2, annotate/export with pypdf.

Moteur PdfEngine concret : rendu avec pypdfium2, annotation/export avec
pypdf.

Supports page rotation, page deletion, PDF insertion (merge), annotation
undo, and writes native PDF annotations (/FreeText, /Square, /Highlight,
/Underline) so every PDF viewer can read them.
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

from lestang_pdf_editor.core.image_buffer import ImageBuffer
from lestang_pdf_editor.core.result import Err, Ok, Result
from lestang_pdf_editor.domain.entities.annotation import (
    Annotation,
    HighlightAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)
from lestang_pdf_editor.domain.entities.document import (
    Document,
    Page,
    detect_pdf_version,
)

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
"""File extensions opened as single-page image documents.

Extensions de fichiers ouverts comme documents image d'une page.
"""

PDF_FONT_NAMES: dict[str, tuple[str, str, str, str]] = {
    "Helvetica": ("/Helv", "/HeBo", "/HeOb", "/HeBO"),
    "Arial": ("/Helv", "/HeBo", "/HeOb", "/HeBO"),
    "Times New Roman": ("/TiRo", "/TiBo", "/TiIt", "/TiBI"),
    "Courier New": ("/Cour", "/CoBo", "/CoOb", "/CoBO"),
}
"""Base-14 PDF font names: (regular, bold, italic, bold-italic).

Noms de polices PDF de base 14 : (régulier, gras, italique, gras-italique).
"""


@dataclass
class _OpenDocument:
    """Internal session state for one opened document.

    État de session interne pour un document ouvert.
    """

    document_id: str
    source_path: str
    is_pdf: bool
    base_page_count: int
    pdf_version: object | None
    replacements: dict[int, ImageBuffer] = field(default_factory=dict)
    rotations: dict[int, int] = field(default_factory=dict)
    deleted: set[int] = field(default_factory=set)
    extra_pdfs: list[str] = field(default_factory=list)
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
            base_page_count=1,
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
            base_page_count=page_count,
            pdf_version=version,
        )
        return Ok(Document(document_id=document_id, pages=pages, pdf_version=version))

    def _session(self, document_id: str) -> _OpenDocument | None:
        """Return the session for a document id, or None.

        Retourne la session d'un document, ou None.
        """
        return self._documents.get(document_id)

    def _total_pages(self, session: _OpenDocument) -> int:
        """Total page count including inserted PDFs, minus deleted pages.

        Nombre total de pages (PDF insérés inclus, suppressions exclues).
        """
        extra = sum(len(PdfReader(p).pages) for p in session.extra_pdfs)
        return session.base_page_count + extra - len(session.deleted)

    def total_pages(self, document_id: str) -> int:
        """Return the live page count of a document (0 if unknown).

        Retourne le nombre de pages courant d'un document (0 si inconnu).
        """
        session = self._session(document_id)
        if session is None:
            return 0
        return self._total_pages(session)

    def _resolve(self, session: _OpenDocument, index: int) -> tuple[str, int]:
        """Map a global page index to (source_path, local_index).

        Convertit un index global de page en (chemin source, index local).
        """
        if index < session.base_page_count:
            return session.source_path, index
        local = index - session.base_page_count
        for extra_path in session.extra_pdfs:
            count = len(PdfReader(extra_path).pages)
            if local < count:
                return extra_path, local
            local -= count
        msg = f"page index out of range: {index}"
        raise IndexError(msg)

    def set_page_image(
        self, document_id: str, page_index: int, image: ImageBuffer
    ) -> Result[None, str]:
        """Replace a page's rendered image (used after enhancement).

        Remplace l'image rendue d'une page (utilisé après amélioration).
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        session.replacements[page_index] = image
        return Ok(None)

    def rotate_page(
        self, document_id: str, page_index: int, degrees: int
    ) -> Result[None, str]:
        """Rotate a page by a multiple of 90 degrees.

        Fait pivoter une page par pas de 90 degrés.
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        current = session.rotations.get(page_index, 0)
        total = (current + degrees) % 360
        if total:
            session.rotations[page_index] = total
        else:
            session.rotations.pop(page_index, None)
        if not session.is_pdf and page_index in session.replacements:
            pil = _buffer_to_pil(session.replacements[page_index])
            pil = pil.rotate(-degrees, expand=True)
            session.replacements[page_index] = _pil_to_buffer(pil)
        return Ok(None)

    def delete_page(self, document_id: str, page_index: int) -> Result[None, str]:
        """Mark a page as deleted (refused if it is the last page).

        Marque une page comme supprimée (refusé si c'est la dernière).
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        if self._total_pages(session) <= 1:
            return Err("cannot delete the last page")
        session.deleted.add(page_index)
        session.replacements.pop(page_index, None)
        session.rotations.pop(page_index, None)
        return Ok(None)

    def insert_pdf(self, document_id: str, path: str) -> Result[int, str]:
        """Append all pages of another PDF at the end of the document.

        Ajoute toutes les pages d'un autre PDF à la fin du document.
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        try:
            count = len(PdfReader(path).pages)
        except Exception as exc:
            return Err(f"cannot read {path}: {exc}")
        session.extra_pdfs.append(path)
        return Ok(count)

    def remove_last_annotation(self, document_id: str) -> Result[None, str]:
        """Undo: remove the most recently added annotation.

        Annulation : retire l'annotation la plus récente.
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        if session.annotations:
            session.annotations.pop()
        return Ok(None)

    def remove_annotation_at(
        self, document_id: str, position: int
    ) -> Result[None, str]:
        """Remove the annotation at the given position in the list.

        Retire l'annotation à la position donnée dans la liste.
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        if 0 <= position < len(session.annotations):
            session.annotations.pop(position)
        return Ok(None)

    def page_image(
        self, document_id: str, page_index: int, dpi: int
    ) -> Result[ImageBuffer, str]:
        """Return a page as a raw image (replacement or rendered at DPI).

        Retourne une page en image brute (remplacement ou rendu au DPI).
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        if page_index in session.deleted:
            return Err(f"page {page_index} was deleted")
        if page_index in session.replacements:
            return Ok(session.replacements[page_index])
        if not session.is_pdf:
            return Err("image document without stored image")
        import pypdfium2 as pdfium

        source_path, local_index = self._resolve(session, page_index)
        pdf = pdfium.PdfDocument(source_path)
        page = pdf[local_index]
        rotation = session.rotations.get(page_index, 0)
        if rotation:
            page.set_rotation(rotation)
        bitmap = page.render(scale=dpi / 72.0)
        pil = bitmap.to_pil()
        return Ok(_pil_to_buffer(pil))

    def add_annotation(
        self, document_id: str, annotation: Annotation
    ) -> Result[None, str]:
        """Attach an annotation to the in-memory document session.

        Attache une annotation à la session du document en mémoire.
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        session.annotations.append(annotation)
        return Ok(None)

    def annotations(self, document_id: str) -> tuple[Annotation, ...]:
        """Return the annotations recorded for a document.

        Retourne les annotations enregistrées pour un document.
        """
        session = self._session(document_id)
        if session is None:
            return ()
        return tuple(session.annotations)

    def export(
        self, document_id: str, destination_path: str, *, flatten: bool
    ) -> Result[str, str]:
        """Export the document as PDF with native annotations.

        Exporte le document en PDF avec des annotations natives.
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        try:
            simple_copy = (
                session.is_pdf
                and not session.replacements
                and not session.rotations
                and not session.deleted
                and not session.extra_pdfs
            )
            if simple_copy and not flatten:
                self._export_pdf_copy(session, destination_path)
            elif session.is_pdf:
                self._export_pdf_rebuild(session, destination_path, flatten)
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
        mapping = {i: i for i in range(session.base_page_count)}
        self._apply_annotations(writer, session, mapping)
        with Path(destination_path).open("wb") as handle:
            writer.write(handle)

    def _export_pdf_rebuild(
        self,
        session: _OpenDocument,
        destination_path: str,
        flatten: bool,
    ) -> None:
        """Rebuild the PDF page by page (rotations, deletions, inserts).

        Reconstruit le PDF page par page (rotations, suppressions,
        insertions), ou aplati en images si `flatten`.
        """
        total = session.base_page_count + sum(
            len(PdfReader(p).pages) for p in session.extra_pdfs
        )
        kept: list[int] = [i for i in range(total) if i not in session.deleted]
        mapping = {old: new for new, old in enumerate(kept)}
        if flatten:
            images = []
            for global_index in kept:
                result = self.page_image(session.document_id, global_index, 300)
                if isinstance(result, Err):
                    raise ValueError(result.error)
                images.append(_buffer_to_pil(result.value))
            if not images:
                msg = "no pages to export"
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
            tmp_pdf.unlink(missing_ok=True)
        else:
            readers: dict[str, PdfReader] = {}
            writer = PdfWriter()
            for global_index in kept:
                source_path, local_index = self._resolve(session, global_index)
                reader = readers.setdefault(source_path, PdfReader(source_path))
                page = reader.pages[local_index]
                rotation = session.rotations.get(global_index, 0)
                if rotation:
                    page.rotate(rotation)
                writer.add_page(page)
        self._apply_annotations(writer, session, mapping)
        with Path(destination_path).open("wb") as handle:
            writer.write(handle)

    def _export_from_images(
        self, session: _OpenDocument, destination_path: str
    ) -> None:
        """Rebuild a PDF from page images, then add annotations.

        Reconstruit un PDF à partir des images des pages, puis ajoute les
        annotations.
        """
        kept = [i for i in range(session.base_page_count) if i not in session.deleted]
        images = [
            _buffer_to_pil(session.replacements[i])
            for i in kept
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
        mapping = {old: new for new, old in enumerate(kept)}
        self._apply_annotations(writer, session, mapping)
        with Path(destination_path).open("wb") as handle:
            writer.write(handle)
        tmp_pdf.unlink(missing_ok=True)

    def _apply_annotations(
        self,
        writer: PdfWriter,
        session: _OpenDocument,
        mapping: dict[int, int],
    ) -> None:
        """Write all session annotations into the writer's pages.

        Écrit toutes les annotations de la session dans les pages du
        writer (avec recalcul d'index après suppressions).
        """
        by_page: dict[int, list[DictionaryObject]] = {}
        for annotation in session.annotations:
            new_index = mapping.get(annotation.page_index)
            if new_index is None:
                continue
            page = writer.pages[new_index]
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            by_page.setdefault(new_index, []).extend(
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
