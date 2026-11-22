"""Release-notes page data (in-app "What's new" / « Nouveautés »).

Données de la page « Nouveautés » de l'application.
"""

from pathlib import Path


def load_release_notes(changelog_path: Path) -> str:
    """Read the changelog shown on the in-app release-notes page.

    Lit le changelog affiché sur la page « Nouveautés » de l'application.
    """
    return changelog_path.read_text(encoding="utf-8")
