"""Word-like ribbon for the document editor (all action groups).

Ruban façon Word pour l'éditeur de document (tous les groupes d'actions).

Adding a new menu later = adding one more `_ribbon_group(...)` to the row.
"""

from collections.abc import Callable

import flet as ft

from lestang_pdf_editor.app.state import AppState

FONT_FAMILIES = ["Helvetica", "Arial", "Times New Roman", "Courier New"]
"""Font families offered in the ribbon.

Polices proposées dans le ruban.
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


def _color_palette(
    state: AppState,
    refresh: Callable[[], None],
    attr: str,
    colors: dict[str, str],
    allow_none: bool = False,
) -> ft.PopupMenuButton:
    """Build a color-palette popup button (swatches, not hex codes).

    Construit un bouton ouvrant une palette de couleurs (pastilles, pas de
    codes hex). Cliquer sur une pastille règle l'attribut de style `attr`.
    """
    swatches: list[ft.Control] = []
    if allow_none:
        swatches.append(
            ft.Container(
                content=ft.Text("∅", size=12),
                width=SWATCH_SIZE,
                height=SWATCH_SIZE,
                border=ft.border.all(1, "#B0BEC5"),
                tooltip=state.t("ribbon.none"),
                on_click=lambda _e: _set_style(state, refresh, **{attr: None}),
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
                    state, refresh, **{attr: code}
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


STAMPS: dict[str, tuple[str, str]] = {
    "approved": ("doc.stamp_approved", "#2E7D32"),
    "confidential": ("doc.stamp_confidential", "#C62828"),
    "draft": ("doc.stamp_draft", "#F9A825"),
}
"""Stamp presets offered in the Insert group (i18n label key, color).

Tampons prédéfinis proposés dans le groupe Insertion (clé i18n, couleur).
"""


def build_ribbon(
    state: AppState,
    refresh: Callable[[], None],
    toggle_tool: Callable[[str], None],
    actions: dict[str, Callable[..., None]],
) -> ft.Control:
    """Build the full ribbon: file, page, insert, style, image, view, edit.

    Construit le ruban complet : fichier, page, insertion, style, image,
    affichage, édition.
    """
    style = state.text_style
    file_group = _ribbon_group(
        state.t("ribbon.file"),
        [
            ft.IconButton(
                icon=ft.Icons.FILE_OPEN,
                tooltip=f"{state.t('ribbon.open')} (Ctrl+O)",
                on_click=lambda _e: actions["open"](),
            ),
            ft.ElevatedButton(
                text=state.t("doc.export"),
                icon=ft.Icons.SAVE,
                on_click=lambda _e: actions["export"](),
            ),
            ft.IconButton(
                icon=ft.Icons.PICTURE_AS_PDF,
                tooltip=state.t("ribbon.export_flat"),
                on_click=lambda _e: actions["export_flat"](),
            ),
            ft.IconButton(
                icon=ft.Icons.UPLOAD_FILE,
                tooltip=state.t("ribbon.insert_pdf"),
                on_click=lambda _e: actions["insert_pdf"](),
            ),
            ft.IconButton(
                icon=ft.Icons.INFO,
                tooltip=state.t("ribbon.properties"),
                on_click=lambda _e: actions["properties"](),
            ),
        ],
    )
    page_group = _ribbon_group(
        state.t("ribbon.page"),
        [
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                tooltip=f"{state.t('ribbon.prev')} (PgUp)",
                on_click=lambda _e: actions["prev"](),
            ),
            ft.IconButton(
                icon=ft.Icons.ARROW_FORWARD,
                tooltip=f"{state.t('ribbon.next')} (PgDn)",
                on_click=lambda _e: actions["next"](),
            ),
            ft.IconButton(
                icon=ft.Icons.ROTATE_LEFT,
                tooltip=state.t("ribbon.rotate_left"),
                on_click=lambda _e: actions["rotate_left"](),
            ),
            ft.IconButton(
                icon=ft.Icons.ROTATE_RIGHT,
                tooltip=state.t("ribbon.rotate_right"),
                on_click=lambda _e: actions["rotate_right"](),
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip=state.t("ribbon.delete_page"),
                on_click=lambda _e: actions["delete_page"](),
            ),
            ft.IconButton(
                icon=ft.Icons.CONTENT_COPY,
                tooltip=f"{state.t('ribbon.duplicate')} (Ctrl+D)",
                on_click=lambda _e: actions["duplicate"](),
            ),
        ],
    )
    add_text_style = (
        ft.ButtonStyle(bgcolor="#BBDEFB") if state.tool == "text" else ft.ButtonStyle()
    )
    insert_group = _ribbon_group(
        state.t("ribbon.insert"),
        [
            ft.ElevatedButton(
                text=state.t("doc.add_text"),
                icon=ft.Icons.TEXT_FIELDS,
                style=add_text_style,
                on_click=lambda _e: toggle_tool("text"),
            ),
            ft.IconButton(
                icon=ft.Icons.CROP_SQUARE,
                tooltip=state.t("doc.tool_rect"),
                selected=state.tool == "rect",
                on_click=lambda _e: toggle_tool("rect"),
            ),
            ft.IconButton(
                icon=ft.Icons.HIGHLIGHT,
                tooltip=state.t("doc.tool_highlight"),
                selected=state.tool == "highlight",
                on_click=lambda _e: toggle_tool("highlight"),
            ),
            ft.Dropdown(
                width=130,
                value="",
                hint_text=state.t("doc.stamp"),
                options=[
                    ft.dropdown.Option(key, state.t(label_key))
                    for key, (label_key, _color) in STAMPS.items()
                ],
                on_change=lambda e: actions["stamp"](e.control.value),
            ),
        ],
    )
    family = ft.Dropdown(
        width=140,
        value=style.font_family,
        options=[ft.dropdown.Option(name) for name in FONT_FAMILIES],
        on_change=lambda e: _set_style(state, refresh, font_family=e.control.value),
    )
    size = ft.Dropdown(
        width=64,
        value=str(int(style.font_size_pt)),
        options=[ft.dropdown.Option(str(s)) for s in FONT_SIZES],
        on_change=lambda e: _set_style(
            state, refresh, font_size_pt=float(e.control.value or 14)
        ),
    )
    style_group = _ribbon_group(
        state.t("ribbon.font"),
        [
            family,
            size,
            ft.IconButton(
                icon=ft.Icons.FORMAT_BOLD,
                tooltip=state.t("ribbon.bold"),
                selected=style.bold,
                on_click=lambda _e: _toggle_style(state, refresh, "bold"),
            ),
            ft.IconButton(
                icon=ft.Icons.FORMAT_ITALIC,
                tooltip=state.t("ribbon.italic"),
                selected=style.italic,
                on_click=lambda _e: _toggle_style(state, refresh, "italic"),
            ),
            ft.IconButton(
                icon=ft.Icons.FORMAT_UNDERLINED,
                tooltip=state.t("ribbon.underline"),
                selected=style.underline,
                on_click=lambda _e: _toggle_style(state, refresh, "underline"),
            ),
            _color_palette(state, refresh, "text_color", TEXT_COLORS),
            _color_palette(
                state, refresh, "highlight_color", HIGHLIGHT_COLORS, allow_none=True
            ),
        ],
    )
    image_group = _ribbon_group(
        state.t("ribbon.image"),
        [
            ft.ElevatedButton(
                text=state.t("doc.enhance"),
                icon=ft.Icons.AUTO_FIX_HIGH,
                on_click=lambda _e: actions["enhance"](),
            ),
            ft.ElevatedButton(
                text=state.t("doc.ocr"),
                icon=ft.Icons.SCANNER,
                on_click=lambda _e: actions["ocr"](),
            ),
        ],
    )
    view_group = _ribbon_group(
        state.t("ribbon.view"),
        [
            ft.IconButton(
                icon=ft.Icons.REMOVE,
                tooltip=state.t("ribbon.zoom_out"),
                on_click=lambda _e: actions["zoom_out"](),
            ),
            ft.IconButton(
                icon=ft.Icons.ADD,
                tooltip=state.t("ribbon.zoom_in"),
                on_click=lambda _e: actions["zoom_in"](),
            ),
            ft.TextButton(
                text="100%",
                tooltip=state.t("ribbon.zoom_reset"),
                on_click=lambda _e: actions["zoom_reset"](),
            ),
            ft.TextButton(
                text=state.t("ribbon.fit_width"),
                on_click=lambda _e: actions["fit_width"](),
            ),
            ft.TextButton(
                text=state.t("ribbon.fit_page"),
                on_click=lambda _e: actions["fit_page"](),
            ),
        ],
    )
    edit_group = _ribbon_group(
        state.t("ribbon.edit"),
        [
            ft.IconButton(
                icon=ft.Icons.UNDO,
                tooltip=f"{state.t('ribbon.undo')} (Ctrl+Z)",
                on_click=lambda _e: actions["undo"](),
            ),
            ft.IconButton(
                icon=ft.Icons.SEARCH,
                tooltip=f"{state.t('ribbon.search')} (Ctrl+F)",
                on_click=lambda _e: actions["search"](),
            ),
        ],
    )
    return ft.Container(
        content=ft.Row(
            controls=[
                file_group,
                page_group,
                insert_group,
                style_group,
                image_group,
                view_group,
                edit_group,
            ],
            spacing=16,
            scroll=ft.ScrollMode.ALWAYS,
        ),
        padding=8,
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, "#B0BEC5")),
    )
