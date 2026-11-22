"""Use cases: enhance one scan, then OCR a page in selected languages.

Cas d'usage : améliorer un scan, puis lancer l'OCR d'une page dans les
langues sélectionnées.
"""

from docscanner.core.image_buffer import ImageBuffer
from docscanner.core.result import Result
from docscanner.domain.entities.ocr import OcrBlock
from docscanner.domain.ports.image_enhancer import ImageEnhancer
from docscanner.domain.ports.ocr_engine import OcrEngine


def enhance_document_image(
    image: ImageBuffer, enhancer: ImageEnhancer
) -> Result[ImageBuffer, str]:
    """Apply one-tap contrast/brightness enhancement to a scanned image.

    Applique l'amélioration en un clic (contraste/luminosité) à une image
    numérisée.
    """
    return enhancer.enhance(image)


def recognize_page_text(
    image: ImageBuffer, ocr: OcrEngine, languages: tuple[str, ...]
) -> Result[tuple[OcrBlock, ...], str]:
    """Run OCR on one page image in the user-selected languages.

    Lance l'OCR sur l'image d'une page dans les langues choisies par
    l'utilisateur.
    """
    return ocr.recognize_text(image, languages)
