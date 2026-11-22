# ADR 0001: Python-first architecture with thin native shells

- **Status:** accepted
- **Date:** 2026-11-22

## Context

The app must run on Android, iOS, Windows 10/11, macOS, Linux and
HarmonyOS, be distributed as store packages and direct installers, stay
100% on-device, and remain maintainable long term with explicit, typed,
documented code.

## Decision

- The whole business and processing core is written in **Python 3.12+**
  (UI via Flet, which renders with Flutter; heavy libs: OpenCV, NumPy,
  Pillow, pypdfium2, pypdf, ONNX Runtime, Tesseract bindings).
- Thin native shells (Kotlin/Swift) exist only for what Python cannot do
  well on mobile: camera preview, ML Kit / VisionKit document detection,
  thermal and battery status, secure keystore — exposed through platform
  channels.
- Clean architecture, feature-first layout under `src/docscanner/`.
- Distribution: installers only for now (APK, .deb/.rpm/AppImage,
  .exe/.msix, .dmg/.pkg, .hap) plus app stores; **no in-app self-updater**;
  updates come from stores or reinstalling the installer.
- Binaries are built for x86_64 **and ARM64** (Android arm64-v8a,
  Apple Silicon universal2, Windows ARM64 native, Linux aarch64).

## Consequences

- One language for all business logic; native code stays minimal.
- Performance-critical paths can still use native engines (NPU/GPU via
  ML Kit/Vision, PDFium) behind ports, and multi-core/heterogeneous-core
  scheduling is handled in the processing layer.
- The MIT-licensed project stays compatible with its Apache-2.0/BSD
  dependencies (see docs/LICENSING_POLICY.md).
