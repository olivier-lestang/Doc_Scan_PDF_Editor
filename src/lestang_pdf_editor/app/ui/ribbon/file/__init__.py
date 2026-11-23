"""File tab > File ribbon group (open/export/export-flat/properties buttons).

Onglet Fichier > groupe Fichier du ruban (boutons ouvrir/exporter/
exporter aplati/propriétés).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.file import (
    export,
    export_flat,
    open,
    properties,
)


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the File group: one control per button module.

    Construit le groupe Fichier : un contrôle par module de bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.file"),
        [
            open.control(ctx),
            export.control(ctx),
            export_flat.control(ctx),
            properties.control(ctx),
        ],
    )
