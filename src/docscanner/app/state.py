"""Application state: wiring between the UI and the data/domain layers.

État de l'application : câblage entre l'UI et les couches data/domain.

This module deliberately does not import Flet, so the whole state can be
exercised headless in tests.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir, user_config_dir

from docscanner.core.image_buffer import ImageBuffer
from docscanner.core.result import Err, Ok, Result
from docscanner.core.settings import Settings
from docscanner.data.auth.unauthenticated_auth_repository import (
    UnauthenticatedAuthRepository,
)
from docscanner.data.licensing.offline_license_manager import (
    OfflineLicenseManager,
)
from docscanner.data.ocr.language_catalog import OcrLanguageCatalog
from docscanner.data.ocr.language_detector import LangDetectLanguageDetector
from docscanner.data.ocr.rapid_ocr_engine import RapidOcrEngine
from docscanner.data.pdf.pypdfium_engine import PypdfiumPdfEngine
from docscanner.data.settings.local_settings_repository import (
    LocalSettingsRepository,
)
from docscanner.data.vision.opencv_enhancer import OpenCvEnhancer
from docscanner.domain.entities.annotation import Annotation
from docscanner.domain.entities.document import Document
from docscanner.domain.entities.ocr import OcrBlock

DISPLAY_DPI_AUTO = 150
"""DPI used to render pages on screen when the setting is "auto".

DPI utilisé pour rendre les pages à l'écran quand le réglage est « auto ».
"""

OCR_DPI_AUTO = 300
"""DPI used for OCR and export when the setting is "auto".

DPI utilisé pour l'OCR et l'export quand le réglage est « auto ».
"""

LEGAL_NOTICE = (
    "© 2026 Olivier Lestang. Doc Scan PDF Editor is free software licensed "
    "under the MIT License (see the LICENSE file). Third-party components "
    "are listed on the 'Open source licenses' page. The PDF format "
    "(ISO 32000) is royalty-free."
)
"""Legal notice shown on the in-app legal page.

Mention légale affichée sur la page légale de l'application.
"""

PRIVACY_TEXT = (
    "All processing (scanning, enhancement, OCR, annotations, PDF export) "
    "happens 100% on your device. No document or image is ever sent "
    "anywhere. Settings are stored locally and survive app updates."
)
"""Privacy statement shown on the in-app legal page.

Politique de confidentialité affichée sur la page légale de l'application.
"""


def default_assets_dir() -> Path:
    """Locate the bundled assets directory (source tree or packed app).

    Localise le répertoire d'assets embarqués (arbre source ou app
    packagée).
    """
    candidates = [
        Path(__file__).resolve().parents[3] / "assets",
        Path.cwd() / "assets",
    ]
    for candidate in candidates:
        if (candidate / "i18n").is_dir():
            return candidate
    return candidates[0]


def default_cache_dir() -> Path:
    """Return the OS user cache directory for rendered page images.

    Retourne le répertoire de cache utilisateur de l'OS pour les images
    de pages rendues.
    """
    return Path(user_cache_dir("DocScanPdfEditor", "Olivier Lestang"))


class AppState:
    """Holds engines, settings and the currently open document.

    Contient les moteurs, les réglages et le document ouvert.
    """

    def __init__(
        self,
        config_dir: Path | None = None,
        cache_dir: Path | None = None,
        assets_dir: Path | None = None,
    ) -> None:
        """Wire all engines and load persisted settings and catalogs.

        Câble tous les moteurs et charge les réglages persistés et les
        catalogues.
        """
        base_config = config_dir or Path(
            user_config_dir("DocScanPdfEditor", "Olivier Lestang")
        )
        self.cache_dir = cache_dir or default_cache_dir()
        self.assets_dir = assets_dir or default_assets_dir()
        self.settings_repo = LocalSettingsRepository(config_dir=base_config)
        self.settings: Settings = self.settings_repo.load()
        self.license_manager = OfflineLicenseManager()
        self.auth_repo = UnauthenticatedAuthRepository()
        self.pdf_engine = PypdfiumPdfEngine()
        self.enhancer = OpenCvEnhancer()
        self.ocr_engine = RapidOcrEngine(cache_dir=self.cache_dir / "ocr")
        self.language_detector = LangDetectLanguageDetector()
        self.catalog = OcrLanguageCatalog.from_json_file(
            self.assets_dir / "ocr" / "languages.json"
        )
        self.ocr_languages: tuple[str, ...] = ("eng", "fra")
        self.document: Document | None = None
        self.selected_page = 0
        self.tool = "select"
        self.page_ocr: dict[int, str] = {}
        self.page_language: dict[int, str] = {}
        self.i18n: dict[str, Any] = self._load_i18n()
        self.page: Any = None
        self._drag_start: tuple[float, float] | None = None
        self._listeners: list[Callable[[], None]] = []

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback invoked whenever the state changes.

        Enregistre un rappel invoqué à chaque changement d'état.
        """
        self._listeners.append(listener)

    def _notify(self) -> None:
        """Invoke all registered listeners.

        Invoque tous les rappels enregistrés.
        """
        for listener in self._listeners:
            listener()

    def _load_i18n(self) -> dict[str, Any]:
        """Load the i18n asset for the current UI language (fallback en).

        Charge l'asset i18n de la langue d'UI courante (repli sur en).
        """
        path = self.assets_dir / "i18n" / f"{self.settings.language}.json"
        if not path.exists():
            path = self.assets_dir / "i18n" / "en.json"
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data

    def t(self, key: str) -> str:
        """Translate a dotted key (e.g. "settings.title") for the UI.

        Traduit une clé pointée (ex. « settings.title ») pour l'UI.
        """
        node: Any = self.i18n
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return key
            node = node[part]
        return node if isinstance(node, str) else key

    def set_ui_language(self, code: str) -> None:
        """Change the UI language, persist it and reload translations.

        Change la langue de l'UI, la persiste et recharge les traductions.
        """
        from dataclasses import replace

        self.settings = replace(self.settings, language=code)
        self.settings_repo.save(self.settings)
        self.i18n = self._load_i18n()
        self._notify()

    def set_dpi(self, dpi: object) -> None:
        """Persist the scan DPI setting ("auto" or an int).

        Persiste le réglage de DPI de numérisation (« auto » ou un entier).
        """
        from dataclasses import replace

        from docscanner.core.settings import ScanSettings

        self.settings = replace(
            self.settings,
            scan=ScanSettings(dpi=dpi),  # type: ignore[arg-type]
        )
        self.settings_repo.save(self.settings)
        self._notify()

    def display_dpi(self) -> int:
        """DPI used to render pages on screen (auto -> 150).

        DPI utilisé pour rendre les pages à l'écran (auto -> 150).
        """
        dpi = self.settings.scan.dpi
        return DISPLAY_DPI_AUTO if dpi == "auto" else int(dpi)

    def ocr_dpi(self) -> int:
        """DPI used for OCR and PDF export (auto -> 300).

        DPI utilisé pour l'OCR et l'export PDF (auto -> 300).
        """
        dpi = self.settings.scan.dpi
        return OCR_DPI_AUTO if dpi == "auto" else int(dpi)

    def open_path(self, path: str) -> Result[str, str]:
        """Open a PDF or image file and select its first page.

        Ouvre un fichier PDF ou image et sélectionne sa première page.
        """
        result = self.pdf_engine.open(path)
        if isinstance(result, Err):
            return result
        self.document = result.value
        self.selected_page = 0
        self.page_ocr.clear()
        self.page_language.clear()
        self._notify()
        return Ok(result.value.document_id)

    def close_document(self) -> None:
        """Close the current document.

        Ferme le document courant.
        """
        self.document = None
        self.selected_page = 0
        self._notify()

    def page_count(self) -> int:
        """Return the number of pages of the open document (0 if none).

        Retourne le nombre de pages du document ouvert (0 si aucun).
        """
        if self.document is None:
            return 0
        return len(self.document.pages)

    def page_image(self, index: int, dpi: int) -> Result[ImageBuffer, str]:
        """Return the raw image of a page at the given DPI.

        Retourne l'image brute d'une page au DPI donné.
        """
        if self.document is None:
            return Err("no document open")
        return self.pdf_engine.page_image(self.document.document_id, index, dpi)

    def page_png_path(self, index: int, dpi: int) -> Result[Path, str]:
        """Render a page to a PNG file in the cache dir and return its path.

        Rend une page dans un fichier PNG du répertoire de cache et
        retourne son chemin.
        """
        result = self.page_image(index, dpi)
        if isinstance(result, Err):
            return result
        from PIL import Image

        buffer = result.value
        image = Image.frombytes("RGB", (buffer.width, buffer.height), buffer.data)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        doc_id = self.document.document_id[:8] if self.document else "none"
        out = self.cache_dir / f"page_{doc_id}_{index}_{dpi}.png"
        image.save(out)
        return Ok(out)

    def enhance_page(self, index: int) -> Result[None, str]:
        """Apply one-tap enhancement to a page and store the result.

        Applique l'amélioration en un clic à une page et stocke le
        résultat.
        """
        if self.document is None:
            return Err("no document open")
        image_result = self.page_image(index, self.ocr_dpi())
        if isinstance(image_result, Err):
            return image_result
        enhanced = self.enhancer.enhance(image_result.value)
        if isinstance(enhanced, Err):
            return enhanced
        result = self.pdf_engine.set_page_image(
            self.document.document_id, index, enhanced.value
        )
        self._notify()
        return result

    def ocr_page(self, index: int) -> Result[tuple[OcrBlock, ...], str]:
        """Run OCR on a page; store text and detected language.

        Lance l'OCR sur une page ; stocke le texte et la langue détectée.
        """
        if self.document is None:
            return Err("no document open")
        image_result = self.page_image(index, self.ocr_dpi())
        if isinstance(image_result, Err):
            return image_result
        blocks_result = self.ocr_engine.recognize_text(
            image_result.value, self.ocr_languages
        )
        if isinstance(blocks_result, Err):
            return blocks_result
        blocks = blocks_result.value
        text = "\n".join(block.text for block in blocks)
        self.page_ocr[index] = text
        language_result = self.language_detector.detect_language(text)
        self.page_language[index] = (
            language_result.value.code if isinstance(language_result, Ok) else "unknown"
        )
        self._notify()
        return Ok(blocks)

    def add_annotation(self, annotation: Annotation) -> Result[None, str]:
        """Attach an annotation to the open document.

        Attache une annotation au document ouvert.
        """
        if self.document is None:
            return Err("no document open")
        result = self.pdf_engine.add_annotation(self.document.document_id, annotation)
        self._notify()
        return result

    def annotations(self) -> tuple[Annotation, ...]:
        """Return all annotations of the open document.

        Retourne toutes les annotations du document ouvert.
        """
        if self.document is None:
            return ()
        return self.pdf_engine.annotations(self.document.document_id)

    def export_pdf(self, destination_path: str) -> Result[str, str]:
        """Export the open document (with annotations) as a PDF file.

        Exporte le document ouvert (avec annotations) en fichier PDF.
        """
        if self.document is None:
            return Err("no document open")
        return self.pdf_engine.export(
            self.document.document_id, destination_path, flatten=False
        )

    def load_release_notes(self) -> str:
        """Read the changelog shown on the release-notes page.

        Lit le changelog affiché sur la page « Nouveautés ».
        """
        for candidate in (
            self.assets_dir.parent / "CHANGELOG.md",
            self.assets_dir / "CHANGELOG.md",
        ):
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")
        return ""

    def load_oss_licenses(self) -> str:
        """Read the generated third-party license list.

        Lit la liste générée des licences des composants tiers.
        """
        path = self.assets_dir / "licenses.json"
        if not path.exists():
            return "licenses.json not generated yet"
        raw = json.loads(path.read_text(encoding="utf-8"))
        lines = [
            f"{entry['name']} {entry['version']} — {entry['license']}"
            f" ({entry['copyright']})"
            for entry in raw.get("packages", [])
        ]
        return "\n".join(lines)
