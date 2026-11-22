"""Document editor view: ribbon, centered zoomable canvas, side panel.

Vue éditeur de document : ruban, canevas centré et zoomable, panneau
latéral (annotations + OCR).
"""

import json
from collections.abc import Callable
from pathlib import Path

import flet as ft

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui.common import page_scaffold, show_message, show_snackbar
from lestang_pdf_editor.app.ui.ribbon import build_ribbon
from lestang_pdf_editor.core.result import Err, Ok
from lestang_pdf_editor.domain.entities.annotation import (
    Annotation,
    HighlightAnnotation,
    RectangleAnnotation,
    TextAnnotation,
)

TOOL_CURSORS = {
    "select": ft.MouseCursor.BASIC,
    "text": ft.MouseCursor.VERTICAL_TEXT,
    "rect": ft.MouseCursor.CLICK,
    "highlight": ft.MouseCursor.CLICK,
}
"""Mouse cursor per tool (the text tool shows a text-insertion cursor).

Curseur de souris par outil (l'outil texte affiche un curseur d'insertion
de texte).
"""

ANNOTATION_ICONS = {
    "text": ft.Icons.TEXT_FIELDS,
    "rectangle": ft.Icons.CROP_SQUARE,
    "highlight": ft.Icons.HIGHLIGHT,
}
"""Icon per annotation kind in the side panel list.

Icône par type d'annotation dans la liste du panneau latéral.
"""


def build_document_view(state: AppState) -> None:
    """Build the document editor view for the open document.

    Construit la vue éditeur pour le document ouvert.
    """
    page = state.page
    page.title = state.t("app_name")

    open_picker = ft.FilePicker(on_result=lambda e: _on_pick_open(state, e))
    save_picker = ft.FilePicker(on_result=lambda e: _on_save(state, e))
    insert_picker = ft.FilePicker(on_result=lambda e: _on_insert(state, e))
    page.overlay.extend([open_picker, save_picker, insert_picker])

    thumbnails = ft.ListView(expand=False, width=140, spacing=8)
    canvas_stack = ft.Stack()
    gesture: ft.GestureDetector | None = None
    annots_list = ft.ListView(expand=True, spacing=4)
    ocr_text = ft.TextField(multiline=True, read_only=True, expand=True, label="OCR")
    right_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(state.t("doc.annotations"), weight=ft.FontWeight.BOLD),
                annots_list,
                ft.Divider(),
                ft.Text(state.t("doc.ocr_result"), weight=ft.FontWeight.BOLD),
                ocr_text,
            ],
            expand=True,
        ),
        width=300,
        padding=8,
        bgcolor="#FFFFFF",
    )
    status = ft.Text("")
    zoom_label = ft.Text("100%")
    search_count = ft.Text("")
    search_field: ft.TextField = ft.TextField(
        hint_text=state.t("doc.search_hint"),
        width=260,
        on_submit=lambda _e: _run_search(
            state, search_field.value or "", search_count, refresh
        ),
    )
    search_bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.SEARCH),
                search_field,
                ft.IconButton(
                    icon=ft.Icons.ARROW_FORWARD,
                    tooltip=state.t("ribbon.next"),
                    on_click=lambda _e: (
                        _run_search(
                            state, search_field.value or "", search_count, refresh
                        )
                        if not state._search_matches
                        else _do_search(state, refresh)
                    ),
                ),
                search_count,
            ],
            spacing=8,
        ),
        padding=6,
        bgcolor="#FFFFFF",
        border=ft.border.only(bottom=ft.BorderSide(1, "#B0BEC5")),
        visible=False,
    )

    def refresh() -> None:
        nonlocal gesture
        gesture = _refresh_all(
            state,
            thumbnails,
            canvas_stack,
            gesture,
            annots_list,
            ocr_text,
            status,
            zoom_label,
        )
        page.update()

    def toggle_tool(tool: str) -> None:
        state.toggle_tool(tool)
        refresh()

    def snack(message: str) -> None:
        show_snackbar(page, message)

    actions: dict[str, Callable[..., None]] = {
        "open": lambda: open_picker.pick_files(
            allowed_extensions=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp"]
        ),
        "export": lambda: _open_export_dialog(state, save_picker, flatten=False),
        "export_flat": lambda: _open_export_dialog(state, save_picker, flatten=True),
        "insert_pdf": lambda: insert_picker.pick_files(allowed_extensions=["pdf"]),
        "prev": state.prev_page,
        "next": state.next_page,
        "rotate_left": lambda: _rotate(state, refresh, -90),
        "rotate_right": lambda: _rotate(state, refresh, 90),
        "delete_page": lambda: _delete_page(state, refresh, snack),
        "undo": lambda: _undo(state, refresh, snack),
        "zoom_in": lambda: _zoom_action(state, refresh, "in"),
        "zoom_out": lambda: _zoom_action(state, refresh, "out"),
        "zoom_reset": lambda: _zoom_action(state, refresh, "reset"),
        "fit_width": lambda: _fit(state, refresh, "width"),
        "fit_page": lambda: _fit(state, refresh, "page"),
        "enhance": lambda: _enhance(state, refresh, snack),
        "ocr": lambda: _run_ocr(state, ocr_text, status, refresh, snack),
        "search": lambda: _toggle_search(state, search_bar, refresh),
        "duplicate": lambda: _duplicate(state, refresh, snack),
        "properties": lambda: _open_properties_dialog(state),
        "stamp": lambda key: _apply_stamp(state, key, refresh, snack),
    }
    state.pending_export = {}

    def on_scroll(event: ft.ScrollEvent) -> None:
        _on_scroll(state, event, refresh)

    gesture = ft.GestureDetector(
        content=canvas_stack,
        # on_tap receives the raw event; on_tap_down is wrapped in TapEvent
        # with local_x/local_y (needed to place the text at the click point).
        on_tap_down=lambda e: _on_tap(state, e, canvas_stack, refresh),
        on_pan_start=lambda e: _on_pan_start(state, e),
        on_pan_update=lambda e: _on_pan_update(state, e),
        on_pan_end=lambda e: _on_pan_end(state, e),
        on_scroll=on_scroll,
    )

    page.on_keyboard_event = lambda e: _on_keyboard(state, e, refresh, actions)

    state.add_listener(refresh)

    ribbon = build_ribbon(state, refresh, toggle_tool, actions)

    canvas_area = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=ft.Column(
            controls=[
                ft.Row(controls=[gesture], scroll=ft.ScrollMode.ALWAYS),
            ],
            scroll=ft.ScrollMode.ALWAYS,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
    body = ft.Row(
        controls=[
            ft.Container(content=thumbnails, padding=4),
            ft.VerticalDivider(width=1),
            canvas_area,
            right_panel,
        ],
        expand=True,
    )
    bottom_bar = ft.Container(
        content=ft.Row(
            controls=[status, zoom_label],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=8,
        bgcolor="#FFFFFF",
        border=ft.border.only(top=ft.BorderSide(1, "#B0BEC5")),
    )
    content = ft.Column(controls=[ribbon, search_bar, body, bottom_bar], expand=True)

    def go_home() -> None:
        from lestang_pdf_editor.app.ui.home import build_home_view

        build_home_view(state)

    page.controls.clear()
    page.controls.append(
        page_scaffold(state, state.t("app_name"), content, on_back=go_home)
    )
    refresh()


def _refresh_all(
    state: AppState,
    thumbnails: ft.ListView,
    canvas_stack: ft.Stack,
    gesture: ft.GestureDetector | None,
    annots_list: ft.ListView,
    ocr_text: ft.TextField,
    status: ft.Text,
    zoom_label: ft.Text,
) -> ft.GestureDetector:
    """Rebuild thumbnails, canvas, side panel and status bar from state.

    Reconstruit vignettes, canevas, panneau latéral et barre de statut.
    """
    thumbnails.controls.clear()
    total = state.page_count()
    for index in range(total):
        png = state.page_png_path(index, 72)
        if isinstance(png, Ok):
            thumbnails.controls.append(
                ft.GestureDetector(
                    content=ft.Image(src=str(png.value), width=120),
                    on_tap=lambda _e, i=index: _select_page(state, i),
                )
            )
    annots_list.controls.clear()
    for position, annotation in enumerate(state.annotations()):
        annots_list.controls.append(_annotation_row(state, position, annotation))
    canvas_stack.controls.clear()
    if state.document is not None and gesture is not None:
        index = state.selected_page
        png = state.page_png_path(index, state.display_dpi())
        if isinstance(png, Ok):
            from PIL import Image

            with Image.open(png.value) as img:
                base_width, base_height = img.size
            scale = state.zoom
            canvas_width = int(base_width * scale)
            canvas_height = int(base_height * scale)
            canvas_stack.width = canvas_width
            canvas_stack.height = canvas_height
            canvas_stack.controls.append(
                ft.Image(
                    src=str(png.value),
                    width=canvas_width,
                    height=canvas_height,
                    fit=ft.ImageFit.FILL,
                )
            )
            canvas_stack.controls.extend(
                _annotation_overlays(state, canvas_width, canvas_height)
            )
        ocr_text.value = state.page_ocr.get(index, "")
        lang = state.page_language.get(index, "")
        name = Path(state.document_path or "").name
        status.value = (
            f"{name} — {state.t('ribbon.page')} {index + 1}/{total}"
            f" — {len(state.annotations())} annotations"
            + (f" — lang: {lang}" if lang else "")
        )
        zoom_label.value = f"{int(state.zoom * 100)}%"
        gesture.mouse_cursor = TOOL_CURSORS[state.tool]
    return gesture


def _annotation_row(
    state: AppState, position: int, annotation: Annotation
) -> ft.Control:
    """Build one row of the annotations side panel (icon + summary + delete).

    Construit une ligne du panneau d'annotations (icône + résumé +
    suppression).
    """
    summary = (
        annotation.content[:40]
        if isinstance(annotation, TextAnnotation)
        else annotation.kind
    )
    return ft.Row(
        controls=[
            ft.Icon(ANNOTATION_ICONS[annotation.kind]),
            ft.Text(
                summary, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip=state.t("ribbon.delete_page").replace("page", "annotation"),
                on_click=lambda _e, p=position: state.remove_annotation_at(p),
            ),
        ],
        spacing=4,
    )


def _select_page(state: AppState, index: int) -> None:
    """Select a page by index and notify listeners.

    Sélectionne une page par son index et notifie les auditeurs.
    """
    state.selected_page = index
    state._notify()


def _annotation_overlays(
    state: AppState, width: int, height: int
) -> list[ft.Container]:
    """Build overlay containers for the current page's annotations.

    Construit les conteneurs de superposition des annotations de la page
    courante (infobulle auteur + horodatage au survol d'un texte).
    """
    overlays: list[ft.Container] = []
    for annotation in state.annotations():
        if annotation.page_index != state.selected_page:
            continue
        x, y, w, h = annotation.rect
        if isinstance(annotation, TextAnnotation):
            tooltip = ""
            if annotation.author or annotation.created_at:
                tooltip = f"{annotation.author}\n{annotation.created_at}"
            overlays.append(
                ft.Container(
                    content=ft.Text(
                        annotation.content,
                        size=annotation.font_size_pt,
                        color=annotation.color,
                        weight=(ft.FontWeight.BOLD if annotation.bold else None),
                        italic=annotation.italic,
                        style=(
                            ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE)
                            if annotation.underline
                            else None
                        ),
                        bgcolor=(
                            ft.Colors.with_opacity(0.45, annotation.highlight_color)
                            if annotation.highlight_color
                            else None
                        ),
                    ),
                    left=x * width,
                    top=y * height,
                    tooltip=tooltip or None,
                )
            )
        elif isinstance(annotation, RectangleAnnotation):
            overlays.append(
                ft.Container(
                    left=x * width,
                    top=y * height,
                    width=w * width,
                    height=h * height,
                    border=ft.border.all(
                        annotation.stroke_width_pt, annotation.stroke_color
                    ),
                )
            )
        elif isinstance(annotation, HighlightAnnotation):
            overlays.append(
                ft.Container(
                    left=x * width,
                    top=y * height,
                    width=w * width,
                    height=h * height,
                    bgcolor=ft.Colors.with_opacity(0.35, annotation.color),
                )
            )
    return overlays


def _local_point(event: object) -> tuple[float, float]:
    """Extract local (x, y) from a pointer event, tolerating raw JSON data.

    Extrait (x, y) en coordonnées locales d'un événement pointeur, même
    si l'événement brut arrive sous forme de données JSON.
    """
    x = getattr(event, "local_x", None)
    y = getattr(event, "local_y", None)
    data = getattr(event, "data", None)
    if (x is None or y is None) and data:
        try:
            parsed = json.loads(str(data))
            x = parsed.get("lx", x)
            y = parsed.get("ly", y)
        except (TypeError, ValueError):
            pass
    return float(x or 0.0), float(y or 0.0)


def _on_tap(
    state: AppState,
    event: ft.TapEvent,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
) -> None:
    """With the text tool, open an inline editor at the exact click point.

    Avec l'outil texte, ouvre un éditeur en ligne au point exact du clic.
    """
    if state.tool != "text" or state.document is None:
        return
    page = state.page
    point_x, point_y = _local_point(event)
    image = state.page_image(state.selected_page, state.display_dpi())
    if isinstance(image, Err):
        return
    canvas_width = image.value.width * state.zoom
    canvas_height = image.value.height * state.zoom
    norm_x = point_x / canvas_width
    norm_y = point_y / canvas_height
    style = state.text_style

    field = ft.TextField(
        label=state.t("doc.text_content"),
        autofocus=True,
        width=260,
        on_submit=lambda _e: commit(),
    )

    def commit() -> None:
        text = (field.value or "").strip()
        if text:
            state.add_annotation(
                TextAnnotation(
                    page_index=state.selected_page,
                    rect=(
                        norm_x,
                        norm_y,
                        260 / canvas_width,
                        40 / canvas_height,
                    ),
                    content=text,
                    font_family=style.font_family,
                    font_size_pt=style.font_size_pt,
                    color=style.text_color,
                    bold=style.bold,
                    italic=style.italic,
                    underline=style.underline,
                    highlight_color=style.highlight_color,
                    author=state.author_name(),
                    created_at=state.new_timestamp(),
                )
            )
        if editor in canvas_stack.controls:
            canvas_stack.controls.remove(editor)
        refresh()

    editor = ft.Container(
        content=ft.Row(
            controls=[
                field,
                ft.IconButton(
                    icon=ft.Icons.CHECK,
                    tooltip=state.t("doc.validate"),
                    on_click=lambda _e: commit(),
                ),
            ],
            spacing=4,
        ),
        left=point_x,
        top=point_y,
        bgcolor="#FFFFFF",
        border=ft.border.all(1, "#1976D2"),
        padding=4,
    )
    canvas_stack.controls.append(editor)
    page.update()


def _on_pan_start(state: AppState, event: ft.DragStartEvent) -> None:
    """Remember the drag start point for rect/highlight tools.

    Mémorise le point de début de glisser pour les outils cadre/surlignage.
    """
    state._drag_start = _local_point(event)
    state._drag_last = state._drag_start


def _on_pan_update(state: AppState, event: ft.DragUpdateEvent) -> None:
    """Track the current drag position (DragEndEvent has no coordinates).

    Suit la position courante du glisser (DragEndEvent n'a pas de
    coordonnées).
    """
    state._drag_last = _local_point(event)


def _on_pan_end(state: AppState, event: ft.DragEndEvent) -> None:
    """Create a rect/highlight annotation from the drag gesture.

    Crée une annotation cadre/surlignage à partir du geste de glisser.
    """
    if state.tool not in ("rect", "highlight") or state.document is None:
        return
    start = getattr(state, "_drag_start", None)
    if start is None:
        return
    end = getattr(state, "_drag_last", None) or start
    image = state.page_image(state.selected_page, state.display_dpi())
    if isinstance(image, Err):
        return
    width = image.value.width * state.zoom
    height = image.value.height * state.zoom
    x1, y1 = start[0] / width, start[1] / height
    x2, y2 = end[0] / width, end[1] / height
    rect = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    if rect[2] < 0.005 or rect[3] < 0.005:
        return
    if state.tool == "rect":
        state.add_annotation(
            RectangleAnnotation(page_index=state.selected_page, rect=rect)
        )
    else:
        state.add_annotation(
            HighlightAnnotation(page_index=state.selected_page, rect=rect)
        )


def _on_keyboard(
    state: AppState,
    event: ft.KeyboardEvent,
    refresh: Callable[[], None],
    actions: dict[str, Callable[[], None]],
) -> None:
    """Handle shortcuts: Ctrl+O/E/Z/0/+/- and PageUp/PageDown navigation.

    Gère les raccourcis : Ctrl+O/E/Z/0/+/- et navigation PgUp/PgDn.
    Shortcuts are ignored while typing in a text field (e.g. the inline
    text editor), so Space and letters keep their normal meaning there.
    """
    state.ctrl_pressed = bool(event.ctrl or event.meta)
    focused = getattr(event, "control", None)
    if isinstance(focused, ft.TextField):
        return
    key = (event.key or "").lower()
    if state.ctrl_pressed:
        if key in ("o",):
            actions["open"]()
        elif key in ("f",):
            actions["search"]()
        elif key in ("d",):
            actions["duplicate"]()
        elif key in ("e",):
            actions["export"]()
        elif key in ("z",):
            actions["undo"]()
        elif key in ("+", "=", "add", "num_add"):
            actions["zoom_in"]()
        elif key in ("-", "_", "subtract", "num_subtract"):
            actions["zoom_out"]()
        elif key == "0":
            actions["zoom_reset"]()
        refresh()
    elif key in ("pageup", "page_up"):
        actions["prev"]()
        refresh()
    elif key in ("pagedown", "page_down", " "):
        actions["next"]()
        refresh()


def _on_scroll(
    state: AppState, event: ft.ScrollEvent, refresh: Callable[[], None]
) -> None:
    """Ctrl/Cmd + mouse wheel zooms the page (works on Win/macOS/Linux).

    Ctrl/Cmd + molette zoome la page (Windows/macOS/Linux).
    """
    if state.ctrl_pressed:
        delta = getattr(event, "scroll_delta_y", 0.0) or 0.0
        if delta:
            state.set_zoom(state.zoom * (1.1 ** (-delta / 50.0)))
            refresh()


def _zoom_action(state: AppState, refresh: Callable[[], None], direction: str) -> None:
    """Apply a zoom button action: "in", "out" or "reset".

    Applique un bouton de zoom : « in », « out » ou « reset ».
    """
    if direction == "in":
        state.zoom_in()
    elif direction == "out":
        state.zoom_out()
    else:
        state.zoom_reset()
    refresh()


def _fit(state: AppState, refresh: Callable[[], None], kind: str) -> None:
    """Zoom to fit page width or whole page in the window.

    Zoom pour ajuster la largeur ou la page entière à la fenêtre.
    """
    state.zoom_fit(kind)
    refresh()


def _rotate(state: AppState, refresh: Callable[[], None], degrees: int) -> None:
    """Rotate the current page and refresh.

    Fait pivoter la page courante et rafraîchit.
    """
    result = state.rotate_page(degrees)
    if isinstance(result, Err):
        show_snackbar(state.page, result.error)
    refresh()


def _delete_page(
    state: AppState, refresh: Callable[[], None], snack: Callable[[str], None]
) -> None:
    """Delete the current page with a snackbar feedback.

    Supprime la page courante avec un retour snackbar.
    """
    result = state.delete_page()
    if isinstance(result, Err):
        snack(result.error)
    refresh()


def _undo(
    state: AppState, refresh: Callable[[], None], snack: Callable[[str], None]
) -> None:
    """Undo the last annotation with a snackbar feedback.

    Annule la dernière annotation avec un retour snackbar.
    """
    result = state.undo()
    if isinstance(result, Err):
        snack(result.error)
    refresh()


def _enhance(
    state: AppState, refresh: Callable[[], None], snack: Callable[[str], None]
) -> None:
    """Run the one-tap enhancement on the current page.

    Lance l'amélioration en un clic sur la page courante.
    """
    result = state.enhance_page(state.selected_page)
    if isinstance(result, Ok):
        snack(state.t("doc.enhanced"))
    else:
        snack(f"Error: {result.error}")
    refresh()


def _run_ocr(
    state: AppState,
    ocr_text: ft.TextField,
    status: ft.Text,
    refresh: Callable[[], None],
    snack: Callable[[str], None],
) -> None:
    """Run OCR on the current page and show the recognized text.

    Lance l'OCR sur la page courante et affiche le texte reconnu.
    """
    result = state.ocr_page(state.selected_page)
    if isinstance(result, Ok):
        ocr_text.value = state.page_ocr.get(state.selected_page, "")
        snack(f"OCR: {len(result.value)} blocks")
    else:
        snack(f"OCR error: {result.error}")
    refresh()


def _on_pick_open(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Reopen another file from the document view (Ctrl+O).

    Rouvre un autre fichier depuis la vue document (Ctrl+O).
    """
    if not event.files:
        return
    path = event.files[0].path or str(Path(event.files[0].name))
    result = state.open_path(path)
    if isinstance(result, Ok):
        build_document_view(state)
    else:
        show_message(state.page, "Error", result.error)


def _on_insert(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Insert all pages of a picked PDF at the end (ribbon action).

    Insère toutes les pages d'un PDF choisi à la fin (action du ruban).
    """
    if not event.files:
        return
    path = event.files[0].path or str(Path(event.files[0].name))
    result = state.insert_pdf(path)
    if isinstance(result, Ok):
        show_snackbar(state.page, f"+{result.value} pages")
        state._notify()
    else:
        show_message(state.page, "Error", result.error)


def _on_save(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Handle the save-file result: export with the pending dialog options.

    Gère le résultat du sélecteur de sauvegarde : exporte avec les options
    de la boîte de dialogue d'export.
    """
    if not event.path or state.document is None:
        return
    pending = state.pending_export
    result = state.export_pdf(
        event.path,
        flatten=bool(pending.get("flatten", False)),
        watermark=str(pending.get("watermark") or "") or None,
        password=str(pending.get("password") or "") or None,
    )
    if isinstance(result, Ok):
        show_snackbar(state.page, f"Saved: {event.path}")
    else:
        show_message(state.page, "Error", result.error)


def _toggle_search(
    state: AppState, search_bar: ft.Container, refresh: Callable[[], None]
) -> None:
    """Show/hide the search bar (Ctrl+F or ribbon button).

    Affiche/masque la barre de recherche (Ctrl+F ou bouton du ruban).
    """
    search_bar.visible = not search_bar.visible
    refresh()


def _run_search(
    state: AppState,
    query: str,
    search_count: ft.Text,
    refresh: Callable[[], None],
) -> None:
    """Run the search over all pages (OCR on the fly) and show the count.

    Lance la recherche sur toutes les pages (OCR à la volée) et affiche le
    nombre de résultats.
    """
    state._search_query = query
    state._search_matches = state.search(query)
    state._search_position = -1
    search_count.value = state.t("doc.search_results").format(
        n=len(state._search_matches)
    )
    refresh()


def _do_search(state: AppState, refresh: Callable[[], None]) -> None:
    """Jump to the next search match (cycling).

    Saute au résultat de recherche suivant (en boucle).
    """
    matches = state._search_matches
    if not matches:
        return
    position = (state._search_position + 1) % len(matches)
    state._search_position = position
    state.selected_page = matches[position]
    state._notify()
    refresh()


def _duplicate(
    state: AppState, refresh: Callable[[], None], snack: Callable[[str], None]
) -> None:
    """Duplicate the current page (Ctrl+D / ribbon).

    Duplique la page courante (Ctrl+D / ruban).
    """
    result = state.duplicate_page()
    if isinstance(result, Err):
        snack(result.error)
    else:
        snack(state.t("ribbon.duplicated").format(n=result.value))
    refresh()


def _apply_stamp(
    state: AppState,
    key: str,
    refresh: Callable[[], None],
    snack: Callable[[str], None],
) -> None:
    """Apply a preset stamp (text + frame) at the center of the page.

    Applique un tampon prédéfini (texte + cadre) au centre de la page.
    """
    from lestang_pdf_editor.app.ui.ribbon import STAMPS

    if key not in STAMPS or state.document is None:
        return
    label_key, color = STAMPS[key]
    label = state.t(label_key)
    state.add_annotation(
        TextAnnotation(
            page_index=state.selected_page,
            rect=(0.35, 0.45, 0.3, 0.08),
            content=label,
            font_size_pt=24,
            color=color,
            bold=True,
            author=state.author_name(),
            created_at=state.new_timestamp(),
        )
    )
    state.add_annotation(
        RectangleAnnotation(
            page_index=state.selected_page,
            rect=(0.34, 0.44, 0.32, 0.1),
            stroke_color=color,
            stroke_width_pt=2,
        )
    )
    snack(label)
    refresh()


def _close(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Close a dialog and refresh the page.

    Ferme une boîte de dialogue et rafraîchit la page.
    """
    dialog.open = False
    page.update()


def _open_export_dialog(
    state: AppState, save_picker: ft.FilePicker, *, flatten: bool
) -> None:
    """Open the export-options dialog, then the save-file picker.

    Ouvre la boîte d'options d'export (filigrane, mot de passe, aplati),
    puis le sélecteur de fichier.
    """
    page = state.page
    watermark_field = ft.TextField(label=state.t("doc.export_watermark"), width=320)
    password_field = ft.TextField(
        label=state.t("doc.export_password"), password=True, width=320
    )
    flatten_check = ft.Checkbox(label=state.t("doc.export_flatten"), value=flatten)
    dialog: ft.AlertDialog

    def confirm(_e: ft.ControlEvent) -> None:
        state.pending_export = {
            "flatten": bool(flatten_check.value),
            "watermark": watermark_field.value or "",
            "password": password_field.value or "",
        }
        dialog.open = False
        page.update()
        save_picker.save_file(file_name="document.pdf", allowed_extensions=["pdf"])

    dialog = ft.AlertDialog(
        title=ft.Text(state.t("doc.export_options")),
        content=ft.Column(
            controls=[watermark_field, password_field, flatten_check], tight=True
        ),
        actions=[
            ft.TextButton(text=state.t("common.ok"), on_click=confirm),
            ft.TextButton(
                text=state.t("common.cancel"), on_click=lambda _e: _close(page, dialog)
            ),
        ],
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


def _open_properties_dialog(state: AppState) -> None:
    """Open the document-properties dialog (metadata + PDF version).

    Ouvre la boîte des propriétés du document (métadonnées + version PDF).
    """
    page = state.page
    current = state.metadata()
    title_field = ft.TextField(
        label=state.t("doc.meta_title"), value=current.get("title", ""), width=320
    )
    author_field = ft.TextField(
        label=state.t("doc.meta_author"), value=current.get("author", ""), width=320
    )
    subject_field = ft.TextField(
        label=state.t("doc.meta_subject"), value=current.get("subject", ""), width=320
    )
    keywords_field = ft.TextField(
        label=state.t("doc.meta_keywords"), value=current.get("keywords", ""), width=320
    )
    info = ft.Text(
        f"{state.pdf_version_label()} — {state.page_count()} "
        f"{state.t('ribbon.page').lower()}s"
    )
    dialog: ft.AlertDialog

    def confirm(_e: ft.ControlEvent) -> None:
        state.set_metadata(
            {
                "title": title_field.value or "",
                "author": author_field.value or "",
                "subject": subject_field.value or "",
                "keywords": keywords_field.value or "",
            }
        )
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        title=ft.Text(state.t("doc.properties")),
        content=ft.Column(
            controls=[info, title_field, author_field, subject_field, keywords_field],
            tight=True,
        ),
        actions=[
            ft.TextButton(text=state.t("common.ok"), on_click=confirm),
            ft.TextButton(
                text=state.t("common.cancel"), on_click=lambda _e: _close(page, dialog)
            ),
        ],
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
