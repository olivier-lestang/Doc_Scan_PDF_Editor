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
from typing import TYPE_CHECKING, Any

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
    extra_counts: list[int] = field(default_factory=list)
    copies: list[int] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    revision: int = 0


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

    def revision(self, document_id: str) -> int:
        """Return the session revision (bumped on every page mutation).

        Retourne la révision de la session (incrémentée à chaque
        modification de page) — utilisée pour invalider le cache de rendu.
        """
        session = self._session(document_id)
        return session.revision if session else 0

    def close(self, document_id: str) -> None:
        """Drop the session and free the underlying PDF document.

        Supprime la session et libère le document PDF sous-jacent.
        """
        self._documents.pop(document_id, None)

    def _live_list(self, session: _OpenDocument) -> list[int]:
        """Global indices of the live pages (deleted ones excluded), in order.

        Indices globaux des pages vivantes (supprimées exclues), dans l'ordre.
        """
        total_all = (
            session.base_page_count + sum(session.extra_counts) + len(session.copies)
        )
        return [i for i in range(total_all) if i not in session.deleted]

    def _total_pages(self, session: _OpenDocument) -> int:
        """Total page count including inserted PDFs, minus deleted pages.

        Nombre total de pages (PDF insérés inclus, suppressions exclues).
        """
        return len(self._live_list(session))

    def total_pages(self, document_id: str) -> int:
        """Return the live page count of a document (0 if unknown).

        Retourne le nombre de pages courant d'un document (0 si inconnu).
        """
        session = self._session(document_id)
        if session is None:
            return 0
        return self._total_pages(session)

    def live_indices(self, document_id: str) -> list[int]:
        """Return the global indices of live pages, in display order.

        Retourne les indices globaux des pages vivantes, dans l'ordre
        d'affichage.
        """
        session = self._session(document_id)
        if session is None:
            return []
        return self._live_list(session)

    def to_global(self, document_id: str, live_index: int) -> Result[int, str]:
        """Map a live index (deletions applied) to the global page index.

        Convertit un index live (suppressions appliquées, base 0) en index
        global de page interne.
        """
        live = self.live_indices(document_id)
        if 0 <= live_index < len(live):
            return Ok(live[live_index])
        return Err(f"invalid page index: {live_index}")

    def _resolve(self, session: _OpenDocument, index: int) -> tuple[str, int]:
        """Map a global page index to (source_path, local_index).

        Convertit un index global de page en (chemin source, index local).
        """
        if index < session.base_page_count:
            return session.source_path, index
        local = index - session.base_page_count
        for extra_path, count in zip(
            session.extra_pdfs, session.extra_counts, strict=True
        ):
            if local < count:
                return extra_path, local
            local -= count
        if local < len(session.copies):
            return session.source_path, session.copies[local]
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
        session.revision += 1
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
        session.revision += 1
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
        session.revision += 1
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
        session.extra_counts.append(count)
        session.revision += 1
        return Ok(count)

    def duplicate_page(self, document_id: str, page_index: int) -> Result[int, str]:
        """Duplicate a page (the copy is appended at the end of the document).

        Duplique une page (la copie est ajoutée à la fin du document).
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        if page_index in session.deleted or page_index >= self._total_pages(session):
            return Err(f"invalid page index: {page_index}")
        session.copies.append(page_index)
        session.revision += 1
        return Ok(self._total_pages(session))

    def set_metadata(
        self, document_id: str, metadata: dict[str, str]
    ) -> Result[None, str]:
        """Set document metadata (title, author, subject, keywords).

        Définit les métadonnées du document (titre, auteur, sujet, mots-clés).
        """
        session = self._session(document_id)
        if session is None:
            return Err(f"unknown document: {document_id}")
        session.metadata = dict(metadata)
        return Ok(None)

    def metadata(self, document_id: str) -> dict[str, str]:
        """Return the session metadata (empty dict if unknown document).

        Retourne les métadonnées de la session (dict vide si inconnu).
        """
        session = self._session(document_id)
        if session is None:
            return {}
        return dict(session.metadata)

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
        pdf: Any = None
        page: Any = None
        bitmap: Any = None
        try:
            pdf = pdfium.PdfDocument(source_path)
            page = pdf[local_index]
            rotation = session.rotations.get(page_index, 0)
            if rotation:
                page.set_rotation(rotation)
            bitmap = page.render(scale=dpi / 72.0)
            pil = bitmap.to_pil()
            return Ok(_pil_to_buffer(pil))
        except Exception as exc:
            return Err(f"render page {page_index} failed: {exc}")
        finally:
            # Explicit close in the right order (bitmap, page, document):
            # otherwise the GC finalizers may call FPDF_ClosePage on an
            # already-freed document handle (WinError 0xC000001D).
            # Fermeture explicite dans le bon ordre (bitmap, page, document)
            # : sinon les finaliseurs du GC peuvent appeler FPDF_ClosePage
            # sur un handle déjà libéré (WinError 0xC000001D).
            if bitmap is not None:
                bitmap.close()
            if page is not None:
                page.close()
            if pdf is not None:
                pdf.close()

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
        self,
        document_id: str,
        destination_path: str,
        *,
        flatten: bool,
        watermark: str | None = None,
        password: str | None = None,
    ) -> Result[str, str]:
        """Export the document as PDF with annotations and options.

        Exporte le document en PDF avec annotations et options.

        Includes native annotations, an optional per-page text watermark,
        an optional AES-256 password, and document metadata.

        Inclut les annotations natives, un filigrane texte optionnel par
        page, un mot de passe AES-256 optionnel et les métadonnées.
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
                and not session.copies
            )
            if simple_copy and not flatten:
                writer, mapping = self._build_pdf_copy(session)
            elif session.is_pdf:
                writer, mapping = self._build_pdf_rebuild(session, flatten)
            else:
                writer, mapping = self._build_from_images(session)
            self._apply_annotations(writer, session, mapping)
            self._apply_watermark(writer, mapping, watermark)
            self._apply_metadata(writer, session)
            self._write(writer, destination_path, password)
            return Ok(destination_path)
        except Exception as exc:
            return Err(f"export failed: {exc}")

    def _write(
        self, writer: PdfWriter, destination_path: str, password: str | None
    ) -> None:
        """Encrypt (AES-256) if a password is given, then write the file.

        Chiffre (AES-256) si un mot de passe est fourni, puis écrit le
        fichier.
        """
        if password:
            writer.encrypt(password, algorithm="AES-256")
        with Path(destination_path).open("wb") as handle:
            writer.write(handle)

    def _apply_metadata(self, writer: PdfWriter, session: _OpenDocument) -> None:
        """Write session metadata (title/author/subject/keywords) to the PDF.

        Écrit les métadonnées de la session (titre/auteur/sujet/mots-clés)
        dans le PDF.
        """
        if session.metadata:
            writer.add_metadata(
                {
                    "/Title": session.metadata.get("title", ""),
                    "/Author": session.metadata.get("author", ""),
                    "/Subject": session.metadata.get("subject", ""),
                    "/Keywords": session.metadata.get("keywords", ""),
                }
            )

    def _apply_watermark(
        self,
        writer: PdfWriter,
        mapping: dict[int, int],
        watermark: str | None,
    ) -> None:
        """Add a bottom-center text watermark annotation on every page.

        Ajoute une annotation texte de filigrane en bas au centre de chaque
        page.
        """
        if not watermark:
            return
        for new_index in range(len(writer.pages)):
            page = writer.pages[new_index]
            width = float(page.mediabox.width)
            text_width = len(watermark) * 7.0
            x = max(0.0, (width - text_width) / 2)
            y = 24.0
            annot = DictionaryObject()
            annot[NameObject("/Type")] = NameObject("/Annot")
            annot[NameObject("/Subtype")] = NameObject("/FreeText")
            annot[NameObject("/Rect")] = ArrayObject(
                [
                    FloatObject(x),
                    FloatObject(y),
                    FloatObject(x + text_width),
                    FloatObject(y + 14),
                ]
            )
            annot[NameObject("/F")] = NumberObject(4)
            annot[NameObject("/Contents")] = TextStringObject(watermark)
            annot[NameObject("/DA")] = TextStringObject("/Helv 10 Tf 0.55 0.55 0.55 rg")
            existing = page.get("/Annots")
            array = existing if isinstance(existing, ArrayObject) else ArrayObject()
            array.append(annot)
            page[NameObject("/Annots")] = array

    def _build_pdf_copy(
        self, session: _OpenDocument
    ) -> tuple[PdfWriter, dict[int, int]]:
        """Copy the source PDF into a writer (identity page mapping).

        Copie le PDF source dans un writer (index de pages identique).
        """
        reader = PdfReader(session.source_path)
        writer = PdfWriter()
        writer.append(reader)
        mapping = {i: i for i in range(session.base_page_count)}
        return writer, mapping

    def _build_pdf_rebuild(
        self, session: _OpenDocument, flatten: bool
    ) -> tuple[PdfWriter, dict[int, int]]:
        """Rebuild the PDF page by page (rotations, deletions, inserts, copies).

        Reconstruit le PDF page par page (rotations, suppressions,
        insertions, copies), ou aplati en images si `flatten`.
        """
        total = self._total_pages(session) + len(session.deleted)
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
            tmp_pdf = Path(session.source_path).with_name(
                f".tmp_export_{session.document_id[:8]}.pdf"
            )
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
        return writer, mapping

    def _build_from_images(
        self, session: _OpenDocument
    ) -> tuple[PdfWriter, dict[int, int]]:
        """Rebuild a PDF from page images (image-sourced documents).

        Reconstruit un PDF à partir des images des pages (documents image).
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
        tmp_pdf = Path(session.source_path).with_name(
            f".tmp_export_{session.document_id[:8]}.pdf"
        )
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
        mapping = {old: new for new, old in enumerate(kept)}
        return writer, mapping

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
        total = self._total_pages(session) + len(session.deleted)
        resolved = [self._resolve(session, i) for i in range(total)]
        for annotation in session.annotations:
            if annotation.page_index >= total:
                continue
            # An annotation follows every copy of its source page.
            #
            # Une annotation suit chaque copie de sa page source.
            target = resolved[annotation.page_index]
            for global_index, source in enumerate(resolved):
                if global_index in session.deleted:
                    continue
                new_index = mapping.get(global_index)
                if new_index is None or source != target:
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
