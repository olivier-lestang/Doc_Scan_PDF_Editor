"""Ribbon button: insert a PDF (Home > File > Insert PDF).

Bouton du ruban : insérer un PDF (Accueil > Fichier > Insérer PDF).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.IconButton(
        icon=ft.Icons.UPLOAD_FILE,
        tooltip=ctx.state.t("ribbon.insert_pdf"),
        on_click=lambda _e: ctx.actions["insert_pdf"](),
    )
