# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file is also embedded in the app and shown on the "Release notes"
("Nouveautés") page.

## [0.4.0] - 2026-11-23

### Added

- Selected text box shows **8 resize handles** (4 corners + 4 edge
  midpoints); hold any handle to resize, with live control-level updates.
  Move = hold-click drag, re-edit = double-click (already in place, now
  covered by the handles too).
- Thumbnails now bake the annotations in (`page_png_path(..., annotated=True)`
  + PIL drawing) and annotation add/replace/remove bump the session
  revision, so a modified page is reflected in its thumbnail.
- Ribbon reworked into **clickable tabs: File / Home / Insert / Tools**
  (`TABS` in `ribbon/__init__.py`); Home holds all text-editing tools
  (annotations + font). Zoom controls moved out of the ribbon to the
  **bottom-right of the window** (bottom bar, next to the zoom %).
- Page-jump field in the bottom bar (type a page number + Enter).
- Default desktop window size set to **1500x920** (resizable).

## [0.3.4] - 2026-11-23

### Changed

- Tool cursors moved to a shared, reusable module:
  `src/lestang_pdf_editor/app/ui/tool_cursors.py` (`TOOL_CURSORS`,
  `cursor_for_tool()`, `apply_tool_cursor()`) — any view can map a tool to a
  cursor and set it on a GestureDetector. New tools just add an entry there.
- Drag preview (rectangle/highlight/text box) now updates at control level
  (`preview.update()`), so drawing follows the mouse smoothly instead of
  lagging behind (full `page.update()` per pan event).

### Fixed

- Space no longer changes page while typing in a text box: the keyboard is
  owned by the inline editor while it is open (guard on `state._editing`,
  since `KeyboardEvent.control` is not reliably the focused TextField on
  desktop); only Ctrl+Enter (validate) and Escape (cancel) are handled then.

## [0.3.3] - 2026-11-23

### Fixed

- Text tool cursor is now `MouseCursor.TEXT` (upright I-beam ⌶) instead of
  `VERTICAL_TEXT`, which the web renderer maps to the CSS `vertical-text`
  cursor (I-beam rotated 90°).

## [0.3.2] - 2026-11-23

### Fixed

- Thumbnails no longer flash the red « Image must have either "src" or
  "src_base64" » error on every click: the thumbnail strip is rebuilt only
  when the page count changes (existing images keep their `src`), and a
  missing/failed thumbnail now shows the page number (`error_content`)
  instead of the error box. Thumbnail render failures are logged.
- Verified on the wire (WebSocket probe): clicking a tool button sends a
  fresh canvas GestureDetector with `mouseCursor: verticalText`, so the
  I-beam cursor depends only on the client binary applying it.

## [0.3.1] - 2026-11-23

### Fixed

- A right-click (any non-left click) outside an open text box now validates
  it, like a normal click outside (`on_secondary_tap`).
- Tool change is logged with the cursor value sent to the client, so a
  missing I-beam cursor can be diagnosed from the log file
  (`%LOCALAPPDATA%\\LestangPdfEditor\\Logs\\app.log` on Windows).

### Note

- No TTF/OTF font embedding (explicit decision): PDF export keeps mapping
  every font family to the PDF base-14, which needs no font file and no
  license.

## [0.3.0] - 2026-11-23

Version is now bumped automatically on every change (SemVer: MINOR for
features, PATCH for fixes) and shown in the bottom-right status bar.

### Changed

- Text tool: you now type **directly inside the rectangle** (text starts at
  the top-left of the box); the framed "comment" editor with the ✓ button
  is removed. Validate with Ctrl+Enter or by clicking outside, Escape
  cancels, Enter = newline.
- Font family dropdown extended (base-14 + common system fonts: Segoe UI,
  Verdana, Georgia, Consolas, ...). At PDF export every family is mapped
  to the closest base-14 font, so no font file is embedded and the export
  stays portable and license-clean. Bundling/embedding OFL fonts (Liberation,
  DejaVu, Noto) for pixel-exact export is a possible next step.

### Fixed

- Drag-drawn text boxes no longer vanish on mouse release.

## [0.2.0] - 2026-11-23

### Added

- App version shown in a bottom status bar, right-aligned on every view;
  version single-sourced in `lestang_pdf_editor.__version__` (dynamic via
  `[tool.hatch.version]`).
- Active drawing tool shown in the bottom status bar with a click/drag
  hint (i18n en/fr/es/zh).

### Fixed

- Mouse cursor for the text/rectangle/highlight tools: the canvas
  GestureDetector now sets `mouse_cursor` at construction (the Flutter
  client only adds the MouseRegion wrapper when `mouseCursor` is non-null
  at first build), so the I-beam/click cursor now actually appears.
- Word-like text boxes, progress bars + rotating log file, per-button
  ribbon package (`ribbon/<tab>/<group>/<button>.py`).

## [Unreleased]

### Changed

- Package renamed `docscanner` -> `lestang_pdf_editor` (src tree, imports,
  pyproject name `lestang-pdf-editor`, CI coverage target, scripts, docs);
  app user dirs renamed `DocScanPdfEditor` -> `LestangPdfEditor`.
- All dependency versions are pinned exactly through the committed
  `uv.lock` (`uv sync --frozen`); the Flutter runtime packages
  (flet-cli/flet-desktop/flet-desktop-light/flet-web + fastapi) are in a
  pinned `desktop` dependency group installed with
  `uv sync --frozen --group desktop`. Scripts `run-dev.ps1` /
  `build-installer.ps1` now use the frozen lock instead of loose installs,
  which prevents client/server flet mismatches ("Unknown control: ...").

### Added

- Initial project skeleton: Python 3.12 core, clean architecture
  (`core` / `domain` / `data` / `features`), strict ruff + mypy + pytest CI.
- Domain ports: `PdfEngine`, `OcrEngine`, `ImageEnhancer`,
  `SignatureProvider`, `SettingsRepository`, `LicenseManager`,
  `AuthRepository`, `SubscriptionProvider`.
- Offline stubs: `OfflineLicenseManager`, `UnauthenticatedAuthRepository`,
  `LocalSettingsRepository` (versioned JSON in the OS user config dir).
- PDF version detection (PDF 1.0-2.0, ISO 32000-1/2, future versions
  opened read-only with a warning).
- OCR language catalog (`assets/ocr/languages.json`) with user-selectable
  languages (fra, eng, spa, chi_sim bundled; more packs later).
- Feature flags: `account_enabled = false`, `cloud_ocr_enabled = false`.
- MIT license, licensing policy, coding standards, ADRs.

### Added (desktop v1, Flet UI)

- Desktop app (Windows/macOS/Linux) with Flet: open PDF or image, page
  browser, one-tap enhance (OpenCV CLAHE/denoise/sharpen), on-device OCR
  (RapidOCR/ONNX) with user-selectable languages and langdetect language
  detection, annotations (text with font size, rectangles, highlights)
  exported as native PDF annotations via pypdf, PDF export.
- Settings view: UI language (en/fr/es/zh), DPI (auto or manual),
  OCR language selection; persisted as versioned JSON in the OS user
  config dir (survives updates/reinstalls).
- Legal pages: legal notice & copyright, generated open-source licenses
  (`assets/licenses.json`), release notes from CHANGELOG.md, privacy.
- Packaging docs (`docs/PACKAGING.md`) and a release workflow building
  installers on `v*` tags.
- Professional editor UI: Word-like ribbon (font family/size, bold,
  italic, underline, text color, highlight marker), light-blue vertical
  gradient background, page centered in the window, zoom controls
  bottom-right + Ctrl/Cmd+wheel and Ctrl +/- / 0 shortcuts.
- Text tool: text-insertion cursor, inline editor opened exactly at the
  click point, validated with Enter or the visible ✓ button, toggle mode
  (one click adds as many text zones as wanted until clicked again),
  hover tooltip with author (first + last name from settings) and ISO
  timestamp with timezone.
- Styled PDF export: base-14 font mapping (bold/italic), /Underline and
  /Highlight annotations for text style, native /FreeText, /Square.
- User profile (first/last name) in settings for annotation metadata.
- VS Code workspace config (`.vscode/`): interpreter, pytest, Ruff, F5
  launch of the app.
- Professional UI v2: app theme (Material 3, blue seed) with
  light/dark/system mode persisted in settings; home page with title,
  subtitle and persisted recent-files list; full ribbon with File / Page /
  Insert / Style / Image / View / Edit groups; side panel listing
  annotations (with per-item delete) and OCR result; status bar with file
  name, page x/y, annotation count and zoom.
- Page operations: previous/next (PgUp/PgDn), rotate ±90°, delete page,
  insert another PDF (merge), all reflected at export with correct
  annotation index remapping; flatten export (images only).
- Shortcuts: Ctrl+O open, Ctrl+E export, Ctrl+Z undo, Ctrl+0 reset zoom,
  Ctrl +/-, Ctrl+wheel zoom; snackbar feedback.
- Undo stack for annotations (Ctrl+Z / ribbon).
- App version shown in a bottom status bar, right-aligned on every view
  (home, document, settings); version is single-sourced in
  `lestang_pdf_editor.__version__` and read dynamically by hatchling
  (`[tool.hatch.version]`), so `pyproject.toml` no longer duplicates it.
- Text/drawing tools now set the mouse cursor at GestureDetector
  construction time (the Flutter client only adds the MouseRegion wrapper
  when `mouseCursor` is non-null at first build) and the bottom status bar
  shows the active tool with a hint (click or drag on the page), in all 4
  UI languages.
