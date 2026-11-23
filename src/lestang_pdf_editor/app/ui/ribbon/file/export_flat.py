"""Ribbon button: export flattened (Home > File > Export flat).

Bouton du ruban : exporter aplati (Accueil > Fichier > Export aplati).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.PICTURE_AS_PDF,
        tooltip=ctx.state.t("ribbon.export_flat"),
        on_click=lambda _e: ctx.actions["export_flat"](),
    )
