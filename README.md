# Lestang PDF Editor

Offline document scanner and PDF editor: scan, straighten, enhance, OCR
(in several user-selectable languages), annotate (text with font/size,
rectangles, highlights) and export any PDF. 100% on-device by default.

Everything is processed locally on the device; no image or document ever
leaves the device unless a future opt-in cloud feature is enabled.

## Platforms

Android, iOS, Windows 10/11, macOS, Linux and HarmonyOS, distributed as
store packages (App Store, Google Play, Microsoft Store, Mac App Store,
AppGallery) and as direct installers (APK, .deb/.rpm/AppImage, .exe/.msix,
.dmg/.pkg, .hap). No in-app self-updater: updates come from stores or from
reinstalling the downloaded installer.

## Architecture

Python-first core (Python 3.12+), clean architecture, feature-first layout:

```
src/lestang_pdf_editor/
├── core/       # result types, settings model, feature flags, image buffer
├── domain/     # entities, ports (protocols), use-case services (pure Python)
├── data/       # platform implementations and offline stubs
├── features/   # scanner, enhance, ocr, editor, export, legal, licensing...
└── app/        # entry point (Flet UI on top of the Python core)
```

Thin native shells (Kotlin/Swift) only provide camera preview, ML Kit /
VisionKit document detection and thermal/battery status through platform
channels. PDF engine: pypdfium2 (Apache-2.0) / pypdf (BSD) in Python, with
pdf.js/pdf-lib on web targets later. OCR: ML Kit / Vision on mobile,
PaddleOCR via ONNX Runtime / Tesseract elsewhere, all on-device.

## PDF versions

Full support: PDF 1.4 through 2.0 (ISO 32000-1 and ISO 32000-2), plus
PDF/A, PDF/X, PDF/UA and tagged PDF. PDF 1.0-1.3: read-only. Newer or
unknown versions: opened read-only with a warning, so future PDF versions
are handled by upgrading the engine, not by rewriting the domain.

## Coding standards

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md). Short version:
all code and comments in English, every docstring/comment followed by its
French translation on the next line, lines wrapped at 88 columns, full type
hints (`mypy --strict`), docstrings enforced by ruff (`D` rules), explicit
verb-noun names.

## Run the desktop app (Windows / macOS / Linux)

```bash
uv sync
# desktop runtime needs the pinned "desktop" group (Flutter binaries), installed from uv.lock:
uv sync --frozen --group desktop  # exact versions from uv.lock (incl. desktop group)
uv run flet run src/lestang_pdf_editor/app/main.py
```

Features in the desktop v1: open PDF (any supported version) or image,
page browser, one-tap enhance (contrast/brightness/denoise/sharpen),
on-device OCR with user-selectable languages (fra/eng/spa/chi_sim + more)
and automatic language detection, annotations (text with font size,
rectangles, highlights) exported as native PDF annotations, settings
(UI language en/fr/es/zh, DPI auto or manual) persisted across updates,
and the Legal pages (notice, open-source licenses, release notes, privacy).

Packaging into installers (Windows .exe, macOS .dmg, Linux AppImage/.deb)
is documented in [docs/PACKAGING.md](docs/PACKAGING.md); CI builds them on
`v*` tags (`.github/workflows/release.yml`).

## Development

```bash
uv sync                 # create venv and install deps + dev group
uv run ruff format      # format
uv run ruff check       # lint (docstrings, annotations, line length)
uv run mypy             # strict type check
uv run pytest           # unit tests
uv run python tool/generate_licenses.py   # regenerate assets/licenses.json
```

CI (GitHub Actions) runs the same checks on every push/PR.

## Open the code in VS Code

```powershell
cd "$HOME\projects\Doc_Scan_PDF_Editor"
code .        # or File > Open Folder in VS Code
```

Recommended extensions: **Python**, **Pylance**, **Ruff** (all from the
Marketplace). The `.vscode/settings.json` in the repo points the
interpreter at `.venv` and enables pytest + Ruff. To launch the app from
VS Code: install the pinned desktop group first
(`uv sync --frozen --group desktop`), then press F5 with the
« Lestang PDF Editor (flet run) » configuration (see
`.vscode/launch.json`), or use the integrated terminal with
`uv run flet run src/lestang_pdf_editor/app/main.py`.

## Licensing

The application code is MIT (see [LICENSE](LICENSE)). Third-party
components use permissive licenses only (MIT, BSD, Apache-2.0, OFL);
see [docs/LICENSING_POLICY.md](docs/LICENSING_POLICY.md). The in-app
"Open source licenses" page is generated from the dependency list.

## Legal pages (in-app)

Settings -> Legal contains: Legal notice & copyright, Open source
licenses (generated), Release notes (from CHANGELOG.md), Privacy.
