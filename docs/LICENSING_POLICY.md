# Licensing Policy

The application itself is licensed under the **MIT** license (see `LICENSE`,
SPDX identifier: `MIT`).

## Allowed dependency licenses

Only permissive, royalty-free licenses are allowed:

- MIT
- BSD-2-Clause / BSD-3-Clause
- Apache-2.0
- MPL-2.0 (file-level copyleft, fine for linking; e.g. certifi)
- ISC
- Python Software Foundation License / HPND (e.g. Pillow)
- SIL Open Font License 1.1 (fonts only)
- CC0 / Unlicense (assets only)

## Forbidden dependency licenses

- GPL, LGPL, AGPL (any version) — incompatible with distributed mobile apps
- SSPL
- Royalty-bearing or proprietary licenses without a written exception
- Unknown / missing licenses

Notable exclusions enforced by this policy: PyMuPDF (AGPL) and
poppler/pdftoppm (GPL) must not be used; use `pypdfium2` (Apache-2.0) and
`pypdf` (BSD-3) instead.

## SPDX identifiers

SPDX (ISO/IEC 5962:2021) license identifiers are a machine-readable
convention used in file headers (`SPDX-License-Identifier: MIT`).
They are recommended for automation but **not legally mandatory**: the MIT
license only requires preserving the copyright notice and license text.

## Third-party attribution

- `LICENSE` and `NOTICE`-style attribution live at the repository root.
- The in-app "Open source licenses" page is generated from the dependency
  list (e.g. via a license-scanner step in CI) and embedded as
  `assets/licenses.json`.
- Trademarks: never use "Adobe", "Acrobat", "PDF-XChange" or any third-party
  mark in the app name, UI or marketing.

## Enforcement

CI fails the build if a dependency with a forbidden or unknown license is
introduced (license scan step), and every new dependency must be reviewed
against this list before merge.
