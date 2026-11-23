"""Ribbon button: document properties (Home > File > Properties).

Bouton du ruban : propriétés du document (Accueil > Fichier > Propriétés).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.INFO,
        tooltip=ctx.state.t("ribbon.properties"),
        on_click=lambda _e: ctx.actions["properties"](),
    )
