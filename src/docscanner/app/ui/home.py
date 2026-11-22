"""Home view: open a PDF/image, go to settings, legal pages.

Vue d'accueil : ouvrir un PDF/image, aller aux réglages, pages légales.
"""

from pathlib import Path

import flet as ft

from docscanner.app.state import AppState
from docscanner.app.ui.common import page_scaffold, show_message
from docscanner.core.result import Ok

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
        text=state.t("home.open_file"), on_click=open_file, icon=ft.Icons.UPLOAD_FILE
    )
    welcome = ft.Text(state.t("home.welcome"), size=18, text_align=ft.TextAlign.CENTER)
    body = ft.Column(
        controls=[welcome, open_button],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )
    page.controls.clear()
    page.controls.append(page_scaffold(state, state.t("app_name"), body))
    page.update()


def _on_pick(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Handle the file picker result: open the file or show the error.

    Gère le résultat du sélecteur de fichier : ouvre le fichier ou affiche
    l'erreur.
    """
    if not event.files:
        return
    from docscanner.app.ui.document_view import build_document_view

    path = event.files[0].path or str(Path(event.files[0].name))
    result = state.open_path(path)
    if isinstance(result, Ok):
        build_document_view(state)
    else:
        show_message(state.page, "Error", result.error)
