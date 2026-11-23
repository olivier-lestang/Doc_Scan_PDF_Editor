"""Application state: wiring between the UI and the data/domain layers.

État de l'application : câblage entre l'UI et les couches data/domain.

This module deliberately does not import Flet, so the whole state can be
exercised headless in tests.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir, user_config_dir

from lestang_pdf_editor.core.image_buffer import ImageBuffer
from lestang_pdf_editor.core.logging_setup import get_logger
from lestang_pdf_editor.core.result import Err, Ok, Result
from lestang_pdf_editor.core.settings import Settings
from lestang_pdf_editor.data.auth.unauthenticated_auth_repository import (
    UnauthenticatedAuthRepository,
)
from lestang_pdf_editor.data.licensing.offline_license_manager import (
    OfflineLicenseManager,
)
from lestang_pdf_editor.data.ocr.language_catalog import OcrLanguageCatalog
from lestang_pdf_editor.data.ocr.language_detector import LangDetectLanguageDetector
from lestang_pdf_editor.data.ocr.rapid_ocr_engine import RapidOcrEngine
from lestang_pdf_editor.data.pdf.pypdfium_engine import PypdfiumPdfEngine
from lestang_pdf_editor.data.settings.local_settings_repository import (
    LocalSettingsRepository,
)
from lestang_pdf_editor.data.vision.opencv_enhancer import OpenCvEnhancer
from lestang_pdf_editor.domain.entities.annotation import Annotation
from lestang_pdf_editor.domain.entities.document import Document
from lestang_pdf_editor.domain.entities.ocr import OcrBlock

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


@dataclass
class TextStyle:
    """Current text style chosen in the ribbon (Word-like).

    Style de texte courant choisi dans le ruban (façon Word).
    """

    font_family: str = "Helvetica"
    font_size_pt: float = 14.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    highlight_color: str | None = None
    text_color: str = "#000000"


ZOOM_MIN = 0.1
"""Minimum zoom factor (10%).

Facteur de zoom minimal (10 %).
"""

ZOOM_MAX = 8.0
"""Maximum zoom factor (800%).

Facteur de zoom maximal (800 %).
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
    return Path(user_cache_dir("LestangPdfEditor", "Olivier Lestang"))


CACHE_MAX_FILES = 300
"""Maximum number of cached page PNGs kept per document (LRU by mtime).

Nombre maximal de PNG de pages en cache par document (LRU par date).
"""

logger = get_logger("state")
"""State logger: timings of open/render/OCR/enhance/search/export actions.

Logger d'état : durées des actions ouvrir/rendre/OCR/améliorer/rechercher/
exporter (jamais le contenu des documents).
"""


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
            user_config_dir("LestangPdfEditor", "Olivier Lestang")
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
        self.document_path: str = ""
        self.selected_page = 0
        self.tool = "select"
        self.text_style = TextStyle()
        self.zoom = 1.0
        self.ctrl_pressed = False
        self.page_ocr: dict[int, str] = {}
        self.page_language: dict[int, str] = {}
        self.i18n: dict[str, Any] = self._load_i18n()
        self.page: Any = None
        self._drag_start: tuple[float, float] | None = None
        self._drag_last: tuple[float, float] | None = None
        self._search_query = ""
        self._search_matches: list[int] = []
        self._search_position = -1
        self._render_generation = 0
        self.ui_progress: Any = None  # ft.ProgressBar bound by the active view
        self.pending_export: dict[str, object] = {}
        self._listeners: list[Callable[[], None]] = []

    def author_name(self) -> str:
        """Return the user's full name for annotation audit metadata.

        Retourne le nom complet de l'utilisateur pour les annotations.
        """
        name = f"{self.settings.first_name} {self.settings.last_name}".strip()
        return name or "Unknown user"

    def new_timestamp(self) -> str:
        """Return the current local time as ISO 8601 with timezone.

        Retourne l'heure locale courante en ISO 8601 avec fuseau horaire.
        """
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def set_zoom(self, zoom: float) -> None:
        """Set the zoom factor, clamped between ZOOM_MIN and ZOOM_MAX.

        Règle le zoom, borné entre ZOOM_MIN et ZOOM_MAX.
        """
        self.zoom = min(ZOOM_MAX, max(ZOOM_MIN, zoom))
        self._notify()

    def zoom_in(self) -> None:
        """Increase the zoom by 10%.

        Augmente le zoom de 10 %.
        """
        self.set_zoom(self.zoom * 1.1)

    def zoom_out(self) -> None:
        """Decrease the zoom by 10%.

        Diminue le zoom de 10 %.
        """
        self.set_zoom(self.zoom / 1.1)

    def zoom_reset(self) -> None:
        """Reset the zoom to 100%.

        Réinitialise le zoom à 100 %.
        """
        self.set_zoom(1.0)

    def toggle_tool(self, tool: str) -> None:
        """Toggle a tool: clicking the active tool again deselects it.

        Bascule un outil : recliquer sur l'outil actif le désélectionne.
        """
        self.tool = "select" if self.tool == tool else tool
        self._notify()

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

        from lestang_pdf_editor.core.settings import ScanSettings

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
        Also records the file in the persisted recent-files list.
        """
        if self.document is not None:
            self.close_document()
        started = time.perf_counter()
        result = self.pdf_engine.open(path)
        if isinstance(result, Err):
            logger.warning("open failed: %s (%s)", path, result.error)
            return result
        logger.info(
            "open %s: %.0f ms, %d pages, version %s, %.1f MB",
            path,
            (time.perf_counter() - started) * 1000,
            self.page_count(),
            self.pdf_version_label(),
            Path(path).stat().st_size / 1e6,
        )
        self.document = result.value
        self.document_path = path
        self.selected_page = 0
        self.page_ocr.clear()
        self.page_language.clear()
        self._search_matches = []
        self._search_position = -1
        self._record_recent_file(path)
        self._notify()
        return Ok(result.value.document_id)

    def _record_recent_file(self, path: str) -> None:
        """Put a file at the front of the persisted recent-files list.

        Met un fichier en tête de la liste persistée des fichiers récents.
        """
        from dataclasses import replace

        recent = [path]
        recent.extend(p for p in self.settings.recent_files if p != path)
        self.settings = replace(self.settings, recent_files=tuple(recent[:10]))
        self.settings_repo.save(self.settings)

    def set_theme_mode(self, mode: str) -> None:
        """Persist the theme mode ("light", "dark" or "system").

        Persiste le mode de thème (« light », « dark » ou « system »).
        """
        from dataclasses import replace

        self.settings = replace(self.settings, theme_mode=mode)
        self.settings_repo.save(self.settings)
        self.apply_theme()
        self._notify()

    def apply_theme(self) -> None:
        """Apply the persisted theme mode to the bound page, if any.

        Applique le mode de thème persisté à la page associée, si présente.
        """
        if self.page is None:
            return
        import flet as ft

        mode = self.settings.theme_mode
        self.page.theme_mode = {
            "light": ft.ThemeMode.LIGHT,
            "dark": ft.ThemeMode.DARK,
        }.get(mode, ft.ThemeMode.SYSTEM)
        self.page.update()

    def page_count(self) -> int:
        """Return the live page count of the open document (0 if none).

        Retourne le nombre de pages courant du document (0 si aucun).
        """
        if self.document is None:
            return 0
        return self.pdf_engine.total_pages(self.document.document_id)

    def _to_global(self, live_index: int) -> Result[int, str]:
        """Convert a live page index (deletions applied) to a global one.

        Convertit un index de page live (suppressions appliquées, base 0)
        en index global interne du moteur.
        """
        if self.document is None:
            return Err("no document open")
        return self.pdf_engine.to_global(self.document.document_id, live_index)

    def next_page(self) -> None:
        """Select the next page if any.

        Sélectionne la page suivante si elle existe.
        """
        if self.selected_page < self.page_count() - 1:
            self.selected_page += 1
            self._notify()

    def prev_page(self) -> None:
        """Select the previous page if any.

        Sélectionne la page précédente si elle existe.
        """
        if self.selected_page > 0:
            self.selected_page -= 1
            self._notify()

    def rotate_page(self, degrees: int) -> Result[None, str]:
        """Rotate the current page by a multiple of 90 degrees.

        Fait pivoter la page courante par pas de 90 degrés.
        """
        if self.document is None:
            return Err("no document open")
        global_index = self._to_global(self.selected_page)
        if isinstance(global_index, Err):
            return global_index
        return self.pdf_engine.rotate_page(
            self.document.document_id, global_index.value, degrees
        )

    def delete_page(self) -> Result[None, str]:
        """Delete the current page (refused if it is the last one).

        Supprime la page courante (refusé si c'est la dernière).
        """
        if self.document is None:
            return Err("no document open")
        global_index = self._to_global(self.selected_page)
        if isinstance(global_index, Err):
            return global_index
        result = self.pdf_engine.delete_page(
            self.document.document_id, global_index.value
        )
        if isinstance(result, Ok):
            self.selected_page = min(self.selected_page, self.page_count() - 1)
            self._notify()
        return result

    def insert_pdf(self, path: str) -> Result[int, str]:
        """Append all pages of another PDF at the end of the document.

        Ajoute toutes les pages d'un autre PDF à la fin du document.
        """
        if self.document is None:
            return Err("no document open")
        result = self.pdf_engine.insert_pdf(self.document.document_id, path)
        if isinstance(result, Ok):
            self._notify()
        return result

    def duplicate_page(self) -> Result[int, str]:
        """Duplicate the current page (copy appended at the end).

        Duplique la page courante (copie ajoutée à la fin).
        """
        if self.document is None:
            return Err("no document open")
        global_index = self._to_global(self.selected_page)
        if isinstance(global_index, Err):
            return global_index
        result = self.pdf_engine.duplicate_page(
            self.document.document_id, global_index.value
        )
        self._notify()
        return result

    def search(
        self,
        query: str,
        progress: Callable[[int, int], None] | None = None,
    ) -> list[int]:
        """Return page indices whose OCR text contains the query.

        Retourne les index des pages dont le texte OCR contient la requête.
        Pages not yet OCR'd are processed on the fly. `progress(done, total)`
        is called after each page (for the UI progress bar).
        """
        if not query.strip():
            return []
        started = time.perf_counter()
        needle = query.lower()
        matches: list[int] = []
        total = self.page_count()
        for index in range(total):
            if index not in self.page_ocr:
                self.ocr_page(index)
            text = self.page_ocr.get(index, "")
            if needle in text.lower():
                matches.append(index)
            if progress is not None:
                progress(index + 1, total)
        logger.info(
            "search done in %.1f s: %d match(es) on %d page(s)",
            time.perf_counter() - started,
            len(matches),
            total,
        )
        return matches

    def set_metadata(self, metadata: dict[str, str]) -> Result[None, str]:
        """Set document metadata (title, author, subject, keywords).

        Définit les métadonnées du document (titre, auteur, sujet,
        mots-clés).
        """
        if self.document is None:
            return Err("no document open")
        return self.pdf_engine.set_metadata(self.document.document_id, metadata)

    def metadata(self) -> dict[str, str]:
        """Return the current document metadata.

        Retourne les métadonnées courantes du document.
        """
        if self.document is None:
            return {}
        return self.pdf_engine.metadata(self.document.document_id)

    def pdf_version_label(self) -> str:
        """Return a human-readable PDF version label of the open document.

        Retourne un libellé lisible de la version PDF du document ouvert.
        """
        if self.document is None or self.document.pdf_version is None:
            return "-"
        version = self.document.pdf_version
        return f"PDF {version.major}.{version.minor}"

    def undo(self) -> Result[None, str]:
        """Remove the most recently added annotation (Ctrl+Z).

        Retire l'annotation la plus récente (Ctrl+Z).
        """
        if self.document is None:
            return Err("no document open")
        result = self.pdf_engine.remove_last_annotation(self.document.document_id)
        self._notify()
        return result

    def remove_annotation_at(self, position: int) -> Result[None, str]:
        """Remove the annotation at a position in the annotations list.

        Retire l'annotation à une position de la liste des annotations.
        """
        if self.document is None:
            return Err("no document open")
        result = self.pdf_engine.remove_annotation_at(
            self.document.document_id, position
        )
        self._notify()
        return result

    def zoom_fit(self, kind: str) -> None:
        """Set zoom to fit page width or whole page in the window.

        Règle le zoom pour ajuster la largeur ou la page entière à la
        fenêtre.
        """
        if self.document is None:
            return
        image = self.page_image(self.selected_page, self.display_dpi())
        if isinstance(image, Err):
            return
        base_w = image.value.width
        base_h = image.value.height
        page = self.page
        window_w = float(getattr(page, "window_width", 0) or 0) or 1280.0
        window_h = float(getattr(page, "window_height", 0) or 0) or 800.0
        avail_w = max(200.0, window_w - 520.0)
        avail_h = max(200.0, window_h - 220.0)
        if kind == "width":
            self.set_zoom(avail_w / base_w)
        else:
            self.set_zoom(min(avail_w / base_w, avail_h / base_h))

    def close_document(self) -> None:
        """Close the current document and free engine + cache resources.

        Ferme le document courant et libère la session moteur ainsi que le
        cache de rendu associé.
        """
        if self.document is not None:
            doc_id = self.document.document_id
            self.pdf_engine.close(doc_id)
            self._sweep_cache(doc_id[:8], revision=None)
        self.document = None
        self.document_path = ""
        self.selected_page = 0
        self._search_matches = []
        self._search_position = -1
        self._notify()

    def page_image(self, index: int, dpi: int) -> Result[ImageBuffer, str]:
        """Return the raw image of a page at the given DPI.

        Retourne l'image brute d'une page au DPI donné.
        """
        if self.document is None:
            return Err("no document open")
        global_index = self._to_global(index)
        if isinstance(global_index, Err):
            return global_index
        return self.pdf_engine.page_image(
            self.document.document_id, global_index.value, dpi
        )

    def page_png_path(self, index: int, dpi: int) -> Result[Path, str]:
        """Return the cached PNG of a page, rendering it once if needed.

        Retourne le PNG en cache d'une page, en le rendant une seule fois
        si nécessaire. La clé de cache inclut la révision de la session :
        toute modification de page invalide les anciens fichiers.
        """
        if self.document is None:
            return Err("no document open")
        doc_id = self.document.document_id
        revision = self.pdf_engine.revision(doc_id)
        prefix = f"page_{doc_id[:8]}_r{revision}_"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        out = self.cache_dir / f"{prefix}{index}_{dpi}.png"
        if out.exists():
            logger.debug("render cache hit: page %d @%d dpi", index, dpi)
            self._sweep_cache(doc_id[:8], revision=revision)
            return Ok(out)
        started = time.perf_counter()
        result = self.page_image(index, dpi)
        if isinstance(result, Err):
            return result
        logger.debug(
            "rendered page %d @%d dpi in %.0f ms",
            index,
            dpi,
            (time.perf_counter() - started) * 1000,
        )
        from PIL import Image

        buffer = result.value
        image = Image.frombytes("RGB", (buffer.width, buffer.height), buffer.data)
        image.save(out)
        self._sweep_cache(doc_id[:8], revision=revision)
        return Ok(out)

    def page_png_and_size(
        self, index: int, dpi: int
    ) -> Result[tuple[Path, int, int], str]:
        """Return the cached PNG path of a page plus its pixel size.

        Retourne le chemin du PNG en cache d'une page et sa taille en
        pixels (sans re-rendre si le cache est valide).
        """
        png = self.page_png_path(index, dpi)
        if isinstance(png, Err):
            return png
        from PIL import Image

        with Image.open(png.value) as img:
            width, height = img.size
        return Ok((png.value, width, height))

    def _sweep_cache(self, doc_prefix: str, revision: int | None) -> None:
        """Delete stale/orphan cache files and enforce the per-doc cap.

        Supprime les fichiers de cache obsolètes (autre révision, ou tous
        ceux du document à sa fermeture) et applique le plafond
        CACHE_MAX_FILES (LRU par date de modification).
        """
        if not self.cache_dir.exists():
            return
        files = sorted(
            self.cache_dir.glob(f"page_{doc_prefix}_*.png"),
            key=lambda p: p.stat().st_mtime,
        )
        keep_prefix = None if revision is None else f"page_{doc_prefix}_r{revision}_"
        kept: list[Path] = []
        for path in files:
            if keep_prefix is not None and path.name.startswith(keep_prefix):
                kept.append(path)
            else:
                path.unlink(missing_ok=True)
        while len(kept) > CACHE_MAX_FILES:
            oldest = kept.pop(0)
            oldest.unlink(missing_ok=True)

    def enhance_page(self, index: int) -> Result[None, str]:
        """Apply one-tap enhancement to a page and store the result.

        Applique l'amélioration en un clic à une page et stocke le
        résultat.
        """
        if self.document is None:
            return Err("no document open")
        started = time.perf_counter()
        image_result = self.page_image(index, self.ocr_dpi())
        if isinstance(image_result, Err):
            return image_result
        enhanced = self.enhancer.enhance(image_result.value)
        if isinstance(enhanced, Err):
            return enhanced
        logger.info(
            "enhance page %d done in %.0f ms",
            index,
            (time.perf_counter() - started) * 1000,
        )
        global_index = self._to_global(index)
        if isinstance(global_index, Err):
            return global_index
        result = self.pdf_engine.set_page_image(
            self.document.document_id, global_index.value, enhanced.value
        )
        self._notify()
        return result

    def ocr_page(self, index: int) -> Result[tuple[OcrBlock, ...], str]:
        """Run OCR on a page; store text and detected language.

        Lance l'OCR sur une page ; stocke le texte et la langue détectée.
        """
        if self.document is None:
            return Err("no document open")
        started = time.perf_counter()
        image_result = self.page_image(index, self.ocr_dpi())
        if isinstance(image_result, Err):
            return image_result
        blocks_result = self.ocr_engine.recognize_text(
            image_result.value, self.ocr_languages
        )
        if isinstance(blocks_result, Err):
            return blocks_result
        logger.info(
            "ocr page %d done in %.0f ms (%d blocks)",
            index,
            (time.perf_counter() - started) * 1000,
            len(blocks_result.value),
        )
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
        global_index = self._to_global(annotation.page_index)
        if isinstance(global_index, Err):
            return global_index
        annotation = replace(annotation, page_index=global_index.value)
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

    def annotations_for_page(self, live_index: int) -> tuple[Annotation, ...]:
        """Return the annotations attached to one live page index.

        Retourne les annotations attachées à un index de page live donné
        (les annotations stockent l'index global en interne).
        """
        global_index = self._to_global(live_index)
        if isinstance(global_index, Err):
            return ()
        return tuple(
            a for a in self.annotations() if a.page_index == global_index.value
        )

    def export_pdf(
        self,
        destination_path: str,
        *,
        flatten: bool = False,
        watermark: str | None = None,
        password: str | None = None,
    ) -> Result[str, str]:
        """Export the open document as PDF (annotations, options, password).

        Exporte le document en PDF (annotations, options, mot de passe).
        """
        if self.document is None:
            return Err("no document open")
        started = time.perf_counter()
        result = self.pdf_engine.export(
            self.document.document_id,
            destination_path,
            flatten=flatten,
            watermark=watermark,
            password=password,
        )
        if isinstance(result, Ok):
            logger.info(
                "export done in %.0f ms -> %s (%.1f MB, flatten=%s, watermark=%s, "
                "password=%s)",
                (time.perf_counter() - started) * 1000,
                destination_path,
                Path(destination_path).stat().st_size / 1e6,
                flatten,
                bool(watermark),
                bool(password),
            )
        else:
            logger.warning("export failed: %s", result.error)
        return result

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
