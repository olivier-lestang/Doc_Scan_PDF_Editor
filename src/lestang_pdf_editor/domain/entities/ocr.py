"""OCR entities: selectable language packs and recognized text blocks.

Entités OCR : packs de langues sélectionnables et blocs de texte reconnus.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OcrLanguage:
    """One selectable OCR language pack (data only, processed on-device).

    Un pack de langue OCR sélectionnable (données seules, traitées
    localement).
    """

    code: str
    names: dict[str, str]
    engine_model: str
    bundled: bool
    size_mb: float


@dataclass(frozen=True)
class OcrBlock:
    """One recognized text block with bounding box and confidence.

    Un bloc de texte reconnu avec boîte englobante et confiance.
    """

    text: str
    bounding_box: tuple[float, float, float, float]
    confidence: float
    language: str


@dataclass(frozen=True)
class DetectedLanguage:
    """Language detected on a page or text sample.

    Langue détectée sur une page ou un échantillon de texte.
    """

    code: str
    confidence: float
