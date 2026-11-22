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


def show_snackbar(page: ft.Page, message: str) -> None:
    """Show a transient snackbar at the bottom of the page.

    Affiche un snackbar transitoire en bas de la page.
    """
    page.snack_bar = ft.SnackBar(content=ft.Text(message))
    page.snack_bar.open = True
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


GRADIENT_TOP = "#E1F5FE"
"""Top color of the vertical light-blue background gradient.

Couleur haute du dégradé vertical bleu clair de l'arrière-plan.
"""

GRADIENT_BOTTOM = "#B3E5FC"
"""Bottom color of the vertical light-blue background gradient.

Couleur basse du dégradé vertical bleu clair de l'arrière-plan.
"""


def page_scaffold(
    state: AppState,
    title: str,
    body: ft.Control,
    on_back: Callable[[], None] | None = None,
) -> ft.Control:
    """Wrap a view in the light-blue vertical gradient + app bar.

    Enveloppe une vue dans le dégradé vertical bleu clair + la barre d'app.
    """
    return ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=[GRADIENT_TOP, GRADIENT_BOTTOM],
        ),
        content=ft.Column(
            controls=[app_bar(state, title, on_back), body],
            expand=True,
        ),
    )


def app_bar(
    state: AppState, title: str, on_back: Callable[[], None] | None = None
) -> ft.Control:
    """Build a custom top app bar (stable controls, no AppBar dependency).

    Construit une barre d'app sur mesure (contrôles de base stables, sans
    dépendre du contrôle AppBar) avec les entrées réglages et retour.
    """
    from docscanner.app.ui.settings_view import build_settings_view

    items = [
        ft.PopupMenuItem(
            text=state.t("settings.title"),
            on_click=lambda _e: build_settings_view(state),
        ),
    ]
    leading: list[ft.Control] = []
    if on_back is not None:
        leading.append(
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _e: on_back())
        )
    return ft.Container(
        content=ft.Row(
            controls=[
                *leading,
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, items=items),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=8,
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, "#B0BEC5")),
    )
