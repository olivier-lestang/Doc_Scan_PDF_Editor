"""Insert tab of the ribbon (insert another PDF into the document).

Onglet Insertion du ruban (insérer un autre PDF dans le document).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.insert import insertion


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Insert tab.

    Retourne les groupes du ruban de l'onglet Insertion.
    """
    return [insertion.build_group(ctx)]
