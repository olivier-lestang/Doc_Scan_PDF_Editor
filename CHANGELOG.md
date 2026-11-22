# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file is also embedded in the app and shown on the "Release notes"
("Nouveautés") page.

## [Unreleased]

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
