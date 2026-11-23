"""Edit > Actions ribbon group (undo, search).

Groupe Édition > Actions du ruban (annuler, rechercher).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext, _ribbon_group
from lestang_pdf_editor.app.ui.ribbon.tools.actions import search, undo


def build_group(ctx: RibbonContext) -> ft.Control:
    """Build the Actions group: one control per button module.

    Construit le groupe Actions : un contrôle par module de bouton.
    """
    return _ribbon_group(
        ctx.state.t("ribbon.edit"),
        [undo.control(ctx), search.control(ctx)],
    )
