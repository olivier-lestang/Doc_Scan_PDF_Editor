"""Insert > Insertion ribbon group (insert another PDF).

Groupe Insertion > Insertion du ruban (insérer un autre PDF).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.insert.insertion import insert_pdf


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the Insertion group: one control per button module.

    Construit le groupe Insertion : un contrôle par module de bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.insert"),
        [insert_pdf.control(ctx)],
    )
