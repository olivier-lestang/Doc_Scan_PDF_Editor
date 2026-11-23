"""Shared ribbon helpers and constants (not a button file).

Fonctions et constantes partagées du ruban (fichier non-bouton, préfixe
underscore).
"""

from collections.abc import Callable
from typing import NamedTuple

import flet as ft

from lestang_pdf_editor.app.state import AppState


class RibbonContext(NamedTuple):
    """Context passed to every ribbon button builder.

    Contexte passé à chaque constructeur de bouton du ruban.
    """

    state: AppState
    refresh: Callable[[], None]
    toggle_tool: Callable[[str], None]
    actions: dict[str, Callable[..., None]]


FONT_FAMILIES = ["Helvetica", "Arial", "Times New Roman", "Courier New"]
"""Font families offered in the ribbon (Home > Insert > Font).

Polices proposées dans le ruban (Accueil > Insertion > Police).
"""

FONT_SIZES = [8, 10, 12, 14, 18, 24, 32, 48, 72]
"""Font sizes (pt) offered in the ribbon.

Tailles de police (pt) proposées dans le ruban.
"""

TEXT_COLORS = {
    "#000000": "Black",
    "#D32F2F": "Red",
    "#1976D2": "Blue",
    "#388E3C": "Green",
}
"""Text colors offered in the ribbon (hex -> label).

Couleurs de texte proposées dans le ruban (hex -> libellé).
"""

HIGHLIGHT_COLORS = {
    "#FFFF00": "Yellow",
    "#C6FF00": "Green",
    "#40C4FF": "Blue",
    "#FF80AB": "Pink",
}
"""Highlight (marker) colors offered in the ribbon.

Couleurs de surlignage (marqueur) proposées dans le ruban.
"""

SWATCH_SIZE = 20
"""Size (px) of one color swatch in the palette popups.

Taille (px) d'une pastille de couleur dans les palettes.
"""

SWATCHES_PER_ROW = 5
"""Number of swatches per row in the palette popups.

Nombre de pastilles par ligne dans les palettes.
"""

STAMPS: dict[str, tuple[str, str]] = {
    "approved": ("doc.stamp_approved", "#2E7D32"),
    "confidential": ("doc.stamp_confidential", "#C62828"),
    "draft": ("doc.stamp_draft", "#F9A825"),
}
"""Stamp presets (i18n label key, color) for the Insert > Annotations group.

Tampons prédéfinis (clé i18n, couleur) pour le groupe Insertion > Annotations.
"""


def _ribbon_group(caption: str, controls: list[ft.Control]) -> ft.Control:
    """Build one ribbon group: a small caption above a row of controls.

    Construit un groupe du ruban : une légende au-dessus d'une ligne
    d'outils.
    """
    return ft.Column(
        controls=[
            ft.Text(caption, size=10, color="#607D8B"),
            ft.Row(controls=controls, spacing=4),
        ],
        spacing=2,
    )


def _set_style(state: AppState, refresh: Callable[[], None], **kwargs: object) -> None:
    """Update fields of the current text style and refresh the ribbon.

    Met à jour des champs du style de texte courant et rafraîchit le ruban.
    """
    for key, value in kwargs.items():
        setattr(state.text_style, key, value)
    refresh()


def _toggle_style(state: AppState, refresh: Callable[[], None], attr: str) -> None:
    """Toggle a boolean field of the current text style.

    Inverse un champ booléen du style de texte courant.
    """
    setattr(state.text_style, attr, not getattr(state.text_style, attr))
    refresh()


def _color_palette(
    ctx: RibbonContext,
    attr: str,
    colors: dict[str, str],
    allow_none: bool = False,
) -> ft.PopupMenuButton:
    """Build a color-palette popup button (swatches, not hex codes).

    Construit un bouton ouvrant une palette de couleurs (pastilles, pas de
    codes hex). Cliquer sur une pastille règle l'attribut de style `attr`.
    """
    state = ctx.state
    swatches: list[ft.Control] = []
    if allow_none:
        swatches.append(
            ft.Container(
                content=ft.Text("\u2205", size=12),
                width=SWATCH_SIZE,
                height=SWATCH_SIZE,
                border=ft.border.all(1, "#B0BEC5"),
                tooltip=state.t("ribbon.none"),
                on_click=lambda _e: _set_style(state, ctx.refresh, **{attr: None}),
            )
        )
    for hex_code, label in colors.items():
        swatches.append(
            ft.Container(
                bgcolor=hex_code,
                width=SWATCH_SIZE,
                height=SWATCH_SIZE,
                border=ft.border.all(1, "#90A4AE"),
                border_radius=4,
                tooltip=f"{label} {hex_code}",
                on_click=lambda _e, code=hex_code: _set_style(
                    state, ctx.refresh, **{attr: code}
                ),
            )
        )
    rows: list[ft.Control] = []
    for i in range(0, len(swatches), SWATCHES_PER_ROW):
        rows.append(ft.Row(controls=swatches[i : i + SWATCHES_PER_ROW], spacing=4))
    grid = ft.Container(
        content=ft.Column(controls=rows, spacing=4, tight=True), padding=6
    )
    current = getattr(state.text_style, attr) or ""
    return ft.PopupMenuButton(
        content=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        bgcolor=current or "#FFFFFF",
                        width=SWATCH_SIZE,
                        height=SWATCH_SIZE,
                        border=ft.border.all(1, "#455A64"),
                        border_radius=4,
                    ),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN),
                ],
                spacing=2,
            ),
            tooltip=current or state.t("ribbon.none"),
        ),
        items=[ft.PopupMenuItem(content=grid)],
    )
