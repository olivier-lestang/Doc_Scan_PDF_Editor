# Packaging desktop installers (Windows / macOS / Linux)

L'application desktop est packagée avec `flet pack` (qui produit un
installeur natif par OS). No store and no website are involved; users
install the downloaded installer directly, and updates are done by
reinstalling the newer installer.

## Prerequisites

```bash
uv sync
# the pinned "desktop" group provides the Flutter runtime binaries, with
# exact versions taken from uv.lock:
uv sync --frozen --group desktop
```

## Windows 10/11 (tested on Windows 11)

On a Windows machine (x64 or ARM64):

```powershell
uv sync --frozen --group desktop  # exact versions from uv.lock (incl. desktop group)
uv run flet pack src/lestang_pdf_editor/app/main.py ^
  --name LestangPdfEditor ^
  --product_name "Lestang PDF Editor" ^
  --company_name "Olivier Lestang" ^
  --file_description "Offline document scanner and PDF editor"
```

This produces a Windows executable/installer under `dist/`.

## macOS

On a Mac (Apple Silicon or Intel; build universal with an x86_64 runner
or use `--arch`):

```bash
uv sync --frozen --group desktop  # exact versions from uv.lock (incl. desktop group)
uv run flet pack src/lestang_pdf_editor/app/main.py \
  --name LestangPdfEditor \
  --product_name "Lestang PDF Editor" \
  --company_name "Olivier Lestang" \
  --macos
```

Produces a `.dmg` under `dist/`. Notarize with Apple credentials before
distribution.

## Linux

On Linux (x64 or aarch64):

```bash
uv sync --frozen --group desktop  # exact versions from uv.lock (incl. desktop group)
uv run flet pack src/lestang_pdf_editor/app/main.py \
  --name lestang-pdf-editor \
  --product_name "Lestang PDF Editor" \
  --company_name "Olivier Lestang" \
  --linux
```

Produces an AppImage (and/or .deb depending on the flet version) under
`dist/`.

## CI release

`.github/workflows/release.yml` builds the installers on tagged releases
(`v*`) using one runner per OS (ubuntu, windows, macos, each x64 and ARM64
where available) and attaches the artifacts to the GitHub Release.

## ARM64 targets

- Windows ARM64 (Copilot+ laptops): native ARM64 build on a `windows-11-arm` runner.
- Linux aarch64: build on an ARM64 runner or with qemu.
- macOS: universal2 covers Intel + Apple Silicon.
- Python wheels used (numpy, opencv-python-headless, pillow, pypdfium2,
  rapidocr-onnxruntime/onnxruntime) all ship win/mac/linux x64+arm64
  binaries, so no source builds are needed.
