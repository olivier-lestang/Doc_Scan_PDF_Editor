"""Home > File ribbon group (open/export/insert/properties buttons).

Groupe Accueil > Fichier du ruban (boutons ouvrir/exporter/insérer/
propriétés).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.home.file import (
    export,
    export_flat,
    insert_pdf,
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
            insert_pdf.control(ctx),
            properties.control(ctx),
        ],
    )
