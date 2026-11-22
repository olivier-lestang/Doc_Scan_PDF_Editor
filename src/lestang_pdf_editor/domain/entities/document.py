"""PDF document entities and version detection/support matrix.

Entités de document PDF et détection de version / matrice de support.
"""

import re
from dataclasses import dataclass
from typing import Literal

from lestang_pdf_editor.core.image_buffer import ImageBuffer

PDF_HEADER_PATTERN = re.compile(rb"%PDF-(\d)\.(\d)")
"""Regex matching the `%PDF-x.y` header at the start of a PDF file.

Regex correspondant à l'en-tête `%PDF-x.y` en début de fichier PDF.
"""

SupportLevel = Literal["full", "read-only", "future-limited"]
"""How much of a PDF version we can handle: full, read-only, or limited.

Niveau de prise en charge d'une version PDF : complet, lecture seule, ou
limité (version future).
"""


@dataclass(frozen=True)
class PdfVersionInfo:
    """Parsed PDF version (major, minor).

    Version PDF analysée (majeure, mineure).
    """

    major: int
    minor: int

    @property
    def is_iso_32000_1(self) -> bool:
        """True for PDF 1.7 (ISO 32000-1:2008).

        Vrai pour PDF 1.7 (ISO 32000-1:2008).
        """
        return (self.major, self.minor) == (1, 7)

    @property
    def is_iso_32000_2(self) -> bool:
        """True for PDF 2.0 (ISO 32000-2:2017/2020).

        Vrai pour PDF 2.0 (ISO 32000-2:2017/2020).
        """
        return (self.major, self.minor) == (2, 0)


def detect_pdf_version(header: bytes) -> PdfVersionInfo | None:
    """Detect the PDF version from the first bytes of a file.

    Détecte la version PDF à partir des premiers octets d'un fichier.
    """
    match = PDF_HEADER_PATTERN.match(header)
    if match is None:
        return None
    return PdfVersionInfo(major=int(match.group(1)), minor=int(match.group(2)))


def support_level(version: PdfVersionInfo) -> SupportLevel:
    """Return the support level for a PDF version.

    Retourne le niveau de support d'une version PDF.

    Full support: PDF 1.4-2.0. Read-only: PDF 1.0-1.3. Future versions
    (> 2.0) open read-only with a warning until the engine is upgraded.
    """
    if version.major > 2 or (version.major == 2 and version.minor > 0):
        return "future-limited"
    if version.major == 1 and version.minor <= 3:
        return "read-only"
    return "full"


@dataclass(frozen=True)
class Page:
    """One page of a scanned or imported document.

    Une page d'un document numérisé ou importé.
    """

    index: int
    image: ImageBuffer | None = None
    ocr_text: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class Document:
    """A document made of ordered pages plus optional PDF metadata.

    Un document composé de pages ordonnées et de métadonnées PDF.
    """

    document_id: str
    pages: tuple[Page, ...]
    pdf_version: PdfVersionInfo | None = None
