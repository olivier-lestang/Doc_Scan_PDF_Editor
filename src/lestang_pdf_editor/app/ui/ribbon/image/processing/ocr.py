"""Ribbon button: OCR (Image > Processing).

Bouton du ruban : OCR (Image > Traitement).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build this ribbon button.

    Construit ce bouton du ruban.
    """
    return ft.ElevatedButton(
        text=ctx.state.t("doc.ocr"),
        icon=ft.Icons.SCANNER,
        on_click=lambda _e: ctx.actions["ocr"](),
    )
