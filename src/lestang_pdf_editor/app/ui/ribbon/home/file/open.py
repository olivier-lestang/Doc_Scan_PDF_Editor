"""Ribbon button: open a file (Home > File > Open).

Bouton du ruban : ouvrir un fichier (Accueil > Fichier > Ouvrir).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.FILE_OPEN,
        tooltip=f"{ctx.state.t('ribbon.open')} (Ctrl+O)",
        on_click=lambda _e: ctx.actions["open"](),
    )
