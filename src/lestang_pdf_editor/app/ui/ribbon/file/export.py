"""Ribbon button: export as PDF (Home > File > Export).

Bouton du ruban : exporter en PDF (Accueil > Fichier > Exporter).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.ElevatedButton(
        text=ctx.state.t("doc.export"),
        icon=ft.Icons.SAVE,
        on_click=lambda _e: ctx.actions["export"](),
    )
