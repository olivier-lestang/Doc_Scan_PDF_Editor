"""Port: on-device OCR engine and language detection.

Port : moteur OCR embarqué et détection de langue.
"""

from typing import Protocol

from lestang_pdf_editor.core.image_buffer import ImageBuffer
from lestang_pdf_editor.core.result import Result
from lestang_pdf_editor.domain.entities.ocr import DetectedLanguage, OcrBlock


class OcrEngine(Protocol):
    """Abstraction over ML Kit / Vision / PaddleOCR / Tesseract, all local.

    Abstraction au-dessus de ML Kit / Vision / PaddleOCR / Tesseract, tous
    en local.
    """

    def recognize_text(
        self, image: ImageBuffer, languages: tuple[str, ...]
    ) -> Result[tuple[OcrBlock, ...], str]:
        """Run OCR on an image in the user-selected languages.

        Lance l'OCR sur une image dans les langues choisies par
        l'utilisateur.
        """
        ...

    def detect_language(self, text: str) -> Result[DetectedLanguage, str]:
        """Detect the language of a recognized text sample.

        Détecte la langue d'un échantillon de texte reconnu.
        """
        ...
