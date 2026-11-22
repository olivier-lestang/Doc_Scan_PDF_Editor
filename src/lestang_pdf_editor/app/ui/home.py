"""Home view: open a file, recent files, settings, legal pages.

Vue d'accueil : ouvrir un fichier, fichiers récents, réglages, pages
légales.
"""

from pathlib import Path

import flet as ft

from lestang_pdf_editor import __version__
from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui.common import page_scaffold, show_message
from lestang_pdf_editor.core.result import Ok

ALLOWED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp"]
"""File extensions accepted by the open-file picker.

Extensions acceptées par le sélecteur d'ouverture de fichier.
"""


def build_home_view(state: AppState) -> None:
    """Build the home view on the page bound to the state.

    Construit la vue d'accueil sur la page associée à l'état.
    """
    page = state.page
    page.title = state.t("app_name")

    file_picker = ft.FilePicker(on_result=lambda e: _on_pick(state, e))
    page.overlay.append(file_picker)

    def open_file(_e: ft.ControlEvent) -> None:
        file_picker.pick_files(allowed_extensions=ALLOWED_EXTENSIONS)

    open_button = ft.ElevatedButton(
        text=state.t("home.open_file"),
        icon=ft.Icons.UPLOAD_FILE,
        on_click=open_file,
        style=ft.ButtonStyle(padding=20, text_style=ft.TextStyle(size=18)),
    )
    title = ft.Text(state.t("app_name"), size=32, weight=ft.FontWeight.BOLD)
    subtitle = ft.Text(state.t("home.welcome"), size=16, text_align=ft.TextAlign.CENTER)

    recent_controls: list[ft.Control] = []
    if state.settings.recent_files:
        recent_controls.append(
            ft.Text(state.t("home.recent"), size=14, weight=ft.FontWeight.BOLD)
        )
        for path in state.settings.recent_files:
            recent_controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE),
                    title=ft.Text(Path(path).name),
                    subtitle=ft.Text(path, size=11),
                    on_click=lambda _e, p=path: _open_path(state, p),
                )
            )
    recent_panel = ft.Container(
        content=ft.Column(controls=recent_controls, spacing=4),
        width=560,
        padding=12,
        bgcolor="#FFFFFF",
        border_radius=8,
        visible=bool(recent_controls),
    )
    footer = ft.Text(f"v{__version__} — MIT", size=11, color="#607D8B")

    body = ft.Column(
        controls=[
            title,
            subtitle,
            open_button,
            recent_panel,
            footer,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
        scroll=ft.ScrollMode.ALWAYS,
        spacing=16,
    )
    page.controls.clear()
    page.controls.append(page_scaffold(state, state.t("app_name"), body))
    page.update()


def _open_path(state: AppState, path: str) -> None:
    """Open a file from the recent list.

    Ouvre un fichier depuis la liste des récents.
    """
    from lestang_pdf_editor.app.ui.document_view import build_document_view

    result = state.open_path(path)
    if isinstance(result, Ok):
        build_document_view(state)
    else:
        show_message(state.page, "Error", result.error)


def _on_pick(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Handle the file picker result: open the file or show the error.

    Gère le résultat du sélecteur de fichier : ouvre le fichier ou affiche
    l'erreur.
    """
    if not event.files:
        return
    path = event.files[0].path or str(Path(event.files[0].name))
    _open_path(state, path)
