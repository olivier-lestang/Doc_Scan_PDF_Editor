"""Generate assets/licenses.json from the installed distributions.

Génère assets/licenses.json à partir des distributions installées.

Usage: uv run python tool/generate_licenses.py

Usage : uv run python tool/generate_licenses.py
"""

import json
from importlib import metadata
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "licenses.json"
"""Where the generated license list is written.

Où la liste de licences générée est écrite.
"""


def collect_packages() -> list[dict[str, str]]:
    """Collect name, version, license and copyright of installed dists.

    Collecte nom, version, licence et copyright des distributions
    installées.
    """
    packages: list[dict[str, str]] = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or dist.metadata.get("Summary") or "?"
        version = dist.version or "?"
        license_expression = dist.metadata.get("License-Expression") or ""
        license_text = dist.metadata.get("License") or ""
        classifiers = dist.metadata.get_all("Classifier") or []
        license_classifier = next(
            (c for c in classifiers if c.startswith("License ::")), ""
        )
        license_label = (
            license_expression
            or (license_classifier.split(" :: ")[-1] if license_classifier else "")
            or license_text[:80]
            or "unknown"
        )
        copyright_text = dist.metadata.get("Author") or ""
        packages.append(
            {
                "name": name,
                "version": version,
                "license": license_label,
                "copyright": copyright_text,
            }
        )
    return sorted(packages, key=lambda p: p["name"].lower())


def main() -> None:
    """Write assets/licenses.json for the in-app licenses page.

    Écrit assets/licenses.json pour la page de licences de l'application.
    """
    payload = {"schema_version": 1, "packages": collect_packages()}
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT} ({len(payload['packages'])} packages)")


if __name__ == "__main__":
    main()
