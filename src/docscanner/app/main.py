"""Desktop application entry point (Flet UI over the Python core).

Point d'entrée de l'application desktop (UI Flet au-dessus du cœur
Python).

Run in development:
    uv run flet run src/docscanner/app/main.py
Pack an installer:
    uv run flet pack src/docscanner/app/main.py --name DocScanPDFEditor
"""

import flet as ft

from docscanner.app.state import AppState
from docscanner.app.ui.home import build_home_view


def main(page: ft.Page) -> None:
    """Flet entry point: build the home view bound to a fresh state.

    Point d'entrée Flet : construit la vue d'accueil avec un état neuf.
    """
    state = AppState()
    state.page = page
    build_home_view(state)


def cli() -> None:
    """Console-script entry point: launch the desktop app window.

    Point d'entrée du script console : lance la fenêtre de l'application.
    """
    ft.app(target=main)


if __name__ == "__main__":
    cli()
