# ADR 0003: Flet as the desktop GUI framework for V1

- **Status:** accepted
- **Date:** 2026-11-23

## Context

The desktop application (Windows 10/11, macOS, Linux — mobile/tablet later)
must offer a professional, Word/Acrobat-like editor (ribbon with tabs, inline
text boxes with resize handles, zoom, thumbnails, annotations) while keeping
the UI in Python (ADR 0001), 100% on-device, with installers built by CI
(`flet pack`), and a path to Android/iOS later.

Alternatives considered:

| Criterion | Flet 0.28.3 | PySide6 (Qt) | Tkinter | Tauri/Electron |
|---|---|---|---|---|
| UI in pure Python | yes | yes | yes | no (JS/TS frontend) |
| Pro rendering | Flutter (fast, consistent) | native OS widgets | dated | web |
| Rich PDF editor UI | yes (already built) | yes | limited | yes |
| Fine input control (cursor, stylus later) | known quirks, worked around | native, best | poor | good |
| Desktop packaging Win/macOS/Linux | `flet pack` | PyInstaller | py2exe | yes |
| Mobile later | `flet pack` (APK/IPA) | weak | no | yes |
| License | Apache-2.0 | LGPL (or Qt commercial) | PSF | varies |
| Footprint | medium (Flutter runtime) | ~100 MB | none | heavy |

## Decision

- **Stay on Flet 0.28.3 (pinned via `uv.lock`) for the desktop V1.** The app
  already works end-to-end on it (tabs, inline text boxes, handles, zoom,
  thumbnails, export), it keeps one Python codebase, runs fully offline, and
  covers the future mobile targets with the same framework.
- Known Flet 0.28.3 quirks are documented and worked around (see CHANGELOG):
  `PanStartEvent`/`DragStartEvent` naming, tap events without `local_x`
  (we use `on_tap_down`), `KeyboardEvent.control` unreliable (we guard on
  app state instead), `mouseCursor` applied only when set at control build
  time (we rebuild the GestureDetector on tool change and use
  `MouseCursor.TEXT`, not the rotated `VERTICAL_TEXT`, on web).
- Web mode (`flet run --web`) is **not** a distribution target: image `src`
  are local file paths, not served over HTTP. Installers only.

## Consequences

- Desktop V1 ships with Flet; no GUI rewrite cost now.
- Versions stay frozen (`uv.lock`, `uv sync --frozen`) so the Python/Flutter
  client pair never mismatches.
- **Re-evaluation criteria (switch to PySide6/Qt if any becomes a hard
  requirement):** native OS widgets mandatory; fine stylus/tablet input
  needed; LGPL compliance becomes unacceptable for the commercial license
  model. PySide6 is LGPL — sellable with dynamic linking, but it must be
  reviewed by counsel before switching a commercial product to it.
- Tkinter is ruled out for a pro product; Tauri/Electron would drop the
  Python UI (contrary to ADR 0001).
