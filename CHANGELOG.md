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
