"""On-device OCR engine based on RapidOCR (PP-OCR models via ONNX Runtime).

Moteur OCR embarqué basé sur RapidOCR (modèles PP-OCR via ONNX Runtime).

Models are bundled inside the `rapidocr-onnxruntime` wheel, so OCR runs
100% on-device on Windows/macOS/Linux, x64 and ARM64, with no download and
no network access.
"""

from pathlib import Path
from typing import Any

from lestang_pdf_editor.core.image_buffer import ImageBuffer
from lestang_pdf_editor.core.result import Err, Ok, Result
from lestang_pdf_editor.domain.entities.ocr import DetectedLanguage, OcrBlock


class RapidOcrEngine:
    """OcrEngine running PP-OCR models locally through ONNX Runtime.

    OcrEngine exécutant les modèles PP-OCR en local via ONNX Runtime.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Create the engine; the model is loaded lazily on first use.

        Crée le moteur ; le modèle est chargé paresseusement au premier
        usage.
        """
        self._cache_dir = cache_dir
        self._ocr: Any = None

    def _ensure_loaded(self) -> Any:
        """Load the RapidOCR model once and cache the instance.

        Charge le modèle RapidOCR une fois et met l'instance en cache.
        """
        if self._ocr is None:
            from rapidocr_onnxruntime import RapidOCR

            self._ocr = RapidOCR()
        return self._ocr

    def recognize_text(
        self, image: ImageBuffer, languages: tuple[str, ...]
    ) -> Result[tuple[OcrBlock, ...], str]:
        """Run OCR on an image; `languages` selects the user's choices.

        Lance l'OCR sur une image ; `languages` reflète les choix de
        l'utilisateur (the bundled model covers Latin + Chinese).
        """
        try:
            import numpy as np

            ocr = self._ensure_loaded()
            array = np.frombuffer(image.data, dtype=np.uint8).reshape(
                image.height, image.width, image.channels
            )
            if image.channels == 1:
                array = np.stack([array] * 3, axis=-1)
            result, _elapsed = ocr(array)
            blocks: list[OcrBlock] = []
            if result:
                for box, text, score in result:
                    xs = [point[0] for point in box]
                    ys = [point[1] for point in box]
                    bounding_box = (
                        min(xs) / image.width,
                        min(ys) / image.height,
                        (max(xs) - min(xs)) / image.width,
                        (max(ys) - min(ys)) / image.height,
                    )
                    blocks.append(
                        OcrBlock(
                            text=str(text),
                            bounding_box=bounding_box,
                            confidence=float(score),
                            language=",".join(languages) or "auto",
                        )
                    )
            return Ok(tuple(blocks))
        except Exception as exc:
            return Err(f"OCR failed: {exc}")

    def detect_language(self, text: str) -> Result[DetectedLanguage, str]:
        """Detect the language via the dedicated langdetect detector.

        Détecte la langue via le détecteur langdetect dédié.
        """
        from lestang_pdf_editor.data.ocr.language_detector import (
            LangDetectLanguageDetector,
        )

        return LangDetectLanguageDetector().detect_language(text)
