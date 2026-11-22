"""Shared UI helpers: dialogs, i18n, colors.

Utilitaires d'UI partagés : boîtes de dialogue, i18n, couleurs.
"""

from collections.abc import Callable

import flet as ft

from docscanner.app.state import AppState


def show_message(page: ft.Page, title: str, message: str) -> None:
    """Open a modal message dialog on the page.

    Ouvre une boîte de dialogue modale sur la page.
    """
    dialog: ft.AlertDialog = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[ft.TextButton("OK", on_click=lambda _e: _close_dialog(page, dialog))],
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


def _close_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Close a dialog and refresh the page.

    Ferme une boîte de dialogue et rafraîchit la page.
    """
    dialog.open = False
    page.update()


def show_scrollable_text(
    page: ft.Page, title: str, content: str, width: int = 640
) -> None:
    """Open a modal dialog showing long scrollable text (legal pages).

    Ouvre une boîte de dialogue modale avec un texte long déroulable
    (pages légales).
    """
    dialog: ft.AlertDialog = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Container(
            content=ft.Text(content, selectable=True),
            width=width,
            height=480,
        ),
        actions=[ft.TextButton("OK", on_click=lambda _e: _close_dialog(page, dialog))],
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


def app_bar(
    state: AppState, title: str, on_back: Callable[[], None] | None = None
) -> ft.AppBar:
    """Build the app bar with settings and legal menu entries.

    Construit la barre d'app avec les entrées réglages et légal.
    """
    from docscanner.app.ui.settings_view import build_settings_view

    items = [
        ft.PopupMenuItem(
            text=state.t("settings.title"),
            on_click=lambda _e: build_settings_view(state),
        ),
    ]
    if on_back is not None:
        items.append(ft.PopupMenuItem(text="←", on_click=lambda _e: on_back()))
    return ft.AppBar(
        title=ft.Text(title),
        actions=[
            ft.PopupMenuButton(items=items),
        ],
    )
