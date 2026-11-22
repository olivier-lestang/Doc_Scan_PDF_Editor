"""Port: PDF engine (open, render, annotate, export), any PDF version.

Port : moteur PDF (ouverture, rendu, annotation, export), toute version.
"""

from typing import Protocol

from docscanner.core.image_buffer import ImageBuffer
from docscanner.core.result import Result
from docscanner.domain.entities.annotation import Annotation
from docscanner.domain.entities.document import Document


class PdfEngine(Protocol):
    """Abstraction over the PDFium / pdf.js / PDFKit backends.

    Abstraction au-dessus des moteurs PDFium / pdf.js / PDFKit.
    """

    def open(self, path: str) -> Result[Document, str]:
        """Open a PDF file of any supported version.

        Ouvre un fichier PDF de toute version supportée.
        """
        ...

    def render_page(
        self, document_id: str, page_index: int, dpi: int
    ) -> Result[ImageBuffer, str]:
        """Render one page to a raw image at the requested DPI.

        Rend une page en image brute au DPI demandé.
        """
        ...

    def add_annotation(
        self, document_id: str, annotation: Annotation
    ) -> Result[None, str]:
        """Attach a native PDF annotation (text, square, highlight).

        Attache une annotation PDF native (texte, cadre, surlignage).
        """
        ...

    def export(
        self, document_id: str, destination_path: str, *, flatten: bool
    ) -> Result[str, str]:
        """Export the document with native annotations or flattened.

        Exporte le document avec annotations natives ou aplati.
        """
        ...
