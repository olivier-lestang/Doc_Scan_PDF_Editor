"""Language detection with langdetect (pure Python, deterministic seed).

Détection de langue avec langdetect (Python pur, graine déterministe).
"""

from docscanner.core.result import Err, Ok, Result
from docscanner.domain.entities.ocr import DetectedLanguage


class LangDetectLanguageDetector:
    """Detects the language of a text sample using langdetect.

    Détecte la langue d'un échantillon de texte avec langdetect.
    """

    def detect_language(self, text: str) -> Result[DetectedLanguage, str]:
        """Return the most probable language of the given text.

        Retourne la langue la plus probable du texte donné.
        """
        try:
            from langdetect import DetectorFactory, detect_langs

            DetectorFactory.seed = 0
            if not text.strip():
                return Err("empty text: cannot detect language")
            candidates = detect_langs(text)
            if not candidates:
                return Err("no language detected")
            top = candidates[0]
            return Ok(DetectedLanguage(code=top.lang, confidence=float(top.prob)))
        except Exception as exc:
            return Err(f"language detection failed: {exc}")
