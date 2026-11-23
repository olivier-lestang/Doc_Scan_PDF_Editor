"""Ribbon button: stamp presets dropdown (Insert > Annotations > Stamp).

Bouton du ruban : liste des tampons prédéfinis (Insertion > Annotations >
Tampon).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import STAMPS, RibbonContext


def control(ctx: RibbonContext) -> ft.Control:
    """Build the stamp dropdown (one entry per preset).

    Construit la liste déroulante des tampons (une entrée par prédéfini).
    """
    return ft.Dropdown(
        width=130,
        value="",
        hint_text=ctx.state.t("doc.stamp"),
        options=[
            ft.dropdown.Option(key, ctx.state.t(label_key))
            for key, (label_key, _color) in STAMPS.items()
        ],
        on_change=lambda e: ctx.actions["stamp"](e.control.value),
    )
