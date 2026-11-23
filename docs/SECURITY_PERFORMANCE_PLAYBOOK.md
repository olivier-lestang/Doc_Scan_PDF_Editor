# Security & Performance Playbook

Référence sécurité/performance du projet (pour l'équipe et les contributeurs).
Companion docs: [SECURITY.md](../SECURITY.md) (vulnerability reporting),
[LICENSING_POLICY.md](LICENSING_POLICY.md), [CODING_STANDARDS.md](CODING_STANDARDS.md),
[adr/0001-python-first-architecture.md](adr/0001-python-first-architecture.md),
[adr/0002-account-subscription-eidas.md](adr/0002-account-subscription-eidas.md).

## 1. Security model

### Data residency (100% on-device by default)

- No document content ever leaves the device by default. The only planned
  network uses are the future opt-in account/subscription backend and
  optional cloud OCR, both behind explicit user consent and HTTPS/TLS 1.3
  (ADR 0002). Interfaces exist (`AuthRepository`, `SubscriptionProvider`,
  `SignatureProvider`) but are offline stubs for now.
- The OCR models are **bundled inside the `rapidocr-onnxruntime` wheel**
  (`site-packages/rapidocr_onnxruntime/models/*.onnx`), so OCR is truly
  offline — nothing is downloaded at first use.

### Where files live (and who can read them)

- Settings: OS user config dir via `platformdirs.user_config_dir`
  (`%APPDATA%\LestangPdfEditor` on Windows, `~/Library/Application Support/...`
  on macOS, `~/.config/...` on Linux). They persist across updates by design.
- Render cache (page PNGs) and OCR cache: OS user cache dir via
  `user_cache_dir`. Rendered page PNGs persist there until evicted: the cache
  is keyed by session `revision`, orphans are swept on access, capped at
  `CACHE_MAX_FILES` (300) per document with LRU eviction, and deleted when the
  document is closed.
- On desktop, isolation is **per user account** (NTFS ACLs / POSIX home
  permissions): any process running under the same account can read these
  files — same as Acrobat/PDF-XChange. Other accounts cannot. On mobile
  (iOS/Android/HarmonyOS, later), the OS sandbox fully isolates the app
  container, which is a stronger guarantee.
- Optional hardening (not yet implemented): `chmod 600/700` on the config and
  cache dirs on POSIX, cache wipe on exit, optional at-rest encryption of the
  cache.

### Handling untrusted PDFs

- pypdfium2/pdfium standalone is **not a sandbox**: a malicious PDF may target
  parser bugs. Mitigations: dependencies always up to date (Dependabot +
  secret scanning enabled on the repo), exact pinned versions via `uv.lock`,
  render DPI and page counts capped, pages rendered one at a time.
- Longer term: parse untrusted PDFs in a separate low-privilege subprocess.
- Annotation text is written through pypdf objects (`TextStringObject` etc.,
  properly escaped) and font names come from a fixed allowlist
  (`FONT_FAMILIES`), so no user text is ever injected into PDF operator strings
  like `/DA`. No `eval`/`exec` anywhere on document content.

### Export protection

- Password-protected export uses real **AES-256** (`pypdf` + the pinned
  `cryptography` package, Apache-2.0/BSD license).

### Secrets

- No secrets, tokens or credentials in the repo; secret scanning is on.
  Report vulnerabilities privately per [SECURITY.md](../SECURITY.md). Never
  log document content.

## 2. Performance model

### Threading / async model

- Flet's UI runs an asyncio loop; sync event handlers run in Flet's thread
  pool. All heavy work (open, insert PDF, OCR, enhance, full-document search,
  export, page rendering) runs **off the UI thread** via
  `loop.run_in_executor(...)` inside `async def` handlers, so the UI never
  freezes (this was the fix for the freeze on large PDFs).
- Thumbnails and the canvas are rendered by background tasks
  (`page.run_task` + executor) with a **generation counter**: stale tasks
  abort when the state changes. Page PNGs are cached (see below), so
  navigation is instant after the first render.
- Rule for scheduling coroutines: use `page.run_task`; never call
  `asyncio.run()` on a thread that already runs a loop (use a dedicated
  thread instead) — `_schedule()` in `app/ui/document_view.py` encapsulates
  this.

### pdfium rules (critical)

- pypdfium2 is **not safe for concurrent `FPDF_LoadDocument`**: two threads
  loading a document at once corrupt the library state ("Data format error"
  on every later load; a hard hang on Windows). Rule: **one shared
  `PdfDocument` per session, and every pdfium load/render/close goes through
  the engine's `_pdfium_lock`**.
- Always close page/bitmap explicitly in the right order (bitmap → page →
  document) in a `finally`; otherwise GC finalizers call `FPDF_ClosePage` on a
  freed handle (seen as `WinError 0xC000001D` on Windows).

### CPU / multi-core / energy

- Python's GIL: threads are fine for I/O and for libraries that release the
  GIL during compute (onnxruntime and OpenCV do for inference); for
  CPU-bound batch work over many pages (e.g. OCR of a whole document), use a
  `ProcessPoolExecutor` later if needed.
- Heterogeneous cores (P+E / big.LITTLE): let onnxruntime size its own thread
  pool (`intra_op_num_threads`), or set it explicitly; keep batch sizes small
  so thermal throttling stays gentle. Energy-aware behavior (fewer threads on
  battery) can be added later via OS APIs.
- ARM is mandatory: all deps ship arm64 wheels (Windows ARM64, Apple Silicon,
  Linux aarch64, Android arm64).

### Memory & rendering

- Render one page at a time; thumbnails at 72 dpi; canvas at `display_dpi`
  (auto = 150, user-overridable in Settings); zoom clamped to
  `[ZOOM_MIN, ZOOM_MAX]`; render DPI capped.
- Render cache: files named `page_<doc>_r<revision>_<page>_<dpi>.png`; a hit
  skips rendering; any page mutation (rotate/delete/insert/duplicate/enhance)
  bumps the revision and invalidates old files (swept immediately).
- Page index model: the UI uses **live** indices (deletions applied); the
  engine stores **global** indices. `AppState._to_global()` /
  `live_indices()` convert at the boundary — do not mix them (after a
  deletion, live index 0 must map past the deleted global page).

## 3. Known pitfalls (bugs already hit in this project)

| Symptom | Cause | Fix in place |
| --- | --- | --- |
| `onnxruntime` not installable on Python 3.15 | no cp315 wheels | `requires-python = ">=3.12,<3.13"` |
| `cryptography>=3.1 is required for AES` | pypdf needs it for AES-256 | pinned `cryptography` dep |
| `cv2 has no attribute cvtColor` on Linux | `opencv-python` needs libGL | CI installs `libgl1 libxcb1`; use headless wheel on servers |
| langdetect gives different results per run | nondeterministic RNG | `DetectorFactory.seed = 0` |
| Annotations upside down | PDF origin is bottom-left, images top-left | Y-flip when writing annotations |
| `module 'flet' has no attribute 'PanStartEvent'` | flet 0.28.3 renamed events | use `DragStartEvent/Update/End` |
| `ControlEvent has no attribute local_x` | `on_tap` is raw; `on_tap_down` is a `TapEvent` | use `on_tap_down` for coordinates |
| `DragEndEvent has no attribute local_x` | end event carries no coords | track the last `DragUpdateEvent` |
| `ft.colors` missing / `Column(padding=...)` invalid | 0.28.3 API changes | `ft.Colors.with_opacity`, wrap in `Container` |
| `Unknown control: appbar` | flet-desktop binary mismatch | pinned `desktop` group, `uv sync --frozen --group desktop` |
| F5 fails: `.venv\Scripts\flet` not found | wrong interpreter path on Windows | launch.json uses `.venv\Scripts\flet.exe` |
| UI frozen on a 28-page PDF | concurrent pdfium loads + sync thumbnail render | `_pdfium_lock` + shared doc + background render tasks |
| `Exception ignored in finalize ... FPDF_ClosePage ... 0xC000001D` | GC closing page after document | explicit close bitmap→page→doc in `finally` |
| Stale thumbnails after deleting a page | live vs global index mix-up | `to_global()` conversion in `AppState` |
| Orphan cache files accumulating | cache key had no revision | revision-keyed cache + sweep + cap |
| Blank window / spinner on startup error | exception not surfaced | `main()` renders the traceback in the window |

## 4. How to verify

```bash
uv sync --frozen --group desktop
uv run ruff format --check
uv run ruff check
uv run mypy
uv run pytest --cov=lestang_pdf_editor --cov-report=term-missing
```

CI (`.github/workflows/ci.yml`) runs the same checks on every push/PR;
releases are built by `.github/workflows/release.yml` on `v*` tags.
A multi-OS CI matrix (ubuntu/windows/macos) is planned but not enabled yet.
