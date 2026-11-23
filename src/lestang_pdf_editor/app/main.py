"""Desktop application entry point (Flet UI over the Python core).

Point d'entrée de l'application desktop (UI Flet au-dessus du cœur
Python).

Run in development:
    uv run --with "flet[all]==0.28.3" flet run src/lestang_pdf_editor/app/main.py
"""

import time
import traceback

import flet as ft

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui.home import build_home_view
from lestang_pdf_editor.core.logging_setup import get_logger, setup_logging

THEME_SEED = "#1976D2"
"""Primary color seed of the app theme (professional blue).

Graine de couleur primaire du thème de l'app (bleu professionnel).
"""

logger = get_logger("app")
"""App logger (writes to the rotating log file + console).

Logger de l'app (fichier log rotatif + console).
"""


def main(page: ft.Page) -> None:
    """Flet entry point: log startup, show boot progress, build the home view.

    Point d'entrée Flet : logue le démarrage, affiche la progression du
    chargement, puis construit la vue d'accueil. Any startup error is shown
    on the page (never a blank window).
    Toute erreur de démarrage est affichée sur la page (jamais une fenêtre
    vide).
    """
    started = time.perf_counter()
    try:
        log_path = setup_logging()
        logger.info("app starting (log: %s)", log_path)
        page.theme = ft.Theme(color_scheme_seed=THEME_SEED, use_material3=True)

        progress = ft.ProgressBar(width=360, value=0.0)
        page.controls.clear()
        page.controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Doc Scan PDF Editor", size=28, weight=ft.FontWeight.BOLD
                        ),
                        progress,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                ),
                expand=True,
            )
        )

        def step(value: float, label: str) -> None:
            progress.value = value
            logger.info("startup %.0f%%: %s", value * 100, label)
            page.update()

        step(0.1, "theme set")
        state = AppState()
        step(0.5, "state + engines initialized")
        state.page = page
        state.apply_theme()
        step(0.8, "theme applied")
        build_home_view(state)
        step(1.0, "home view built")
        logger.info("startup done in %.0f ms", (time.perf_counter() - started) * 1000)
    except Exception:
        logger.exception("startup failed")
        page.controls.clear()
        page.controls.append(ft.Text(traceback.format_exc(), color="#C62828", size=14))
        page.update()


def cli() -> None:
    """Console-script entry point: launch the desktop app window.

    Point d'entrée du script console : lance la fenêtre de l'application.
    """
    ft.app(target=main)


if __name__ == "__main__":
    cli()
