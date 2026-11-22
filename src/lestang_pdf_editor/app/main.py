"""Desktop application entry point (Flet UI over the Python core).

Point d'entrée de l'application desktop (UI Flet au-dessus du cœur
Python).

Run in development:
    uv run --with "flet[all]==0.28.3" flet run src/lestang_pdf_editor/app/main.py
"""

import flet as ft

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui.home import build_home_view

THEME_SEED = "#1976D2"
"""Primary color seed of the app theme (professional blue).

Graine de couleur primaire du thème de l'app (bleu professionnel).
"""


def main(page: ft.Page) -> None:
    """Flet entry point: apply the theme and build the home view.

    Point d'entrée Flet : applique le thème et construit la vue d'accueil.
    """
    page.theme = ft.Theme(color_scheme_seed=THEME_SEED, use_material3=True)
    state = AppState()
    state.page = page
    state.apply_theme()
    build_home_view(state)


def cli() -> None:
    """Console-script entry point: launch the desktop app window.

    Point d'entrée du script console : lance la fenêtre de l'application.
    """
    ft.app(target=main)


if __name__ == "__main__":
    cli()
