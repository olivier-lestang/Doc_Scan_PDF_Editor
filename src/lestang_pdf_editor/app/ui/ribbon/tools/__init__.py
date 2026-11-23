"""Tools tab of the ribbon (page organization, image processing, actions).

Onglet Outils du ruban (organisation des pages, traitement d'image, actions).
"""

import flet as ft

from lestang_pdf_editor.app.ui.ribbon._shared import RibbonContext
from lestang_pdf_editor.app.ui.ribbon.tools import actions, organization, processing


def build_groups(ctx: RibbonContext) -> list[ft.Control]:
    """Return the ribbon groups of the Tools tab.

    Retourne les groupes du ruban de l'onglet Outils.
    """
    return [
        organization.build_group(ctx),
        processing.build_group(ctx),
        actions.build_group(ctx),
    ]
