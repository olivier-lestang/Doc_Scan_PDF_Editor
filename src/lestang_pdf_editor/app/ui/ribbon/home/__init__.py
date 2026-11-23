"""Home tab of the ribbon: everything about text editing (annotations + font).

Onglet Accueil du ruban : tout ce qui concerne l'édition de texte
(annotations + police).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.home import annotations, font


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Home tab.

    Retourne les groupes du ruban de l'onglet Accueil.
    """
    return [annotations.build_group(ctx), font.build_group(ctx)]
