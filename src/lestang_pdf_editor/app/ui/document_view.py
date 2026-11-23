"""Document editor view: ribbon, centered zoomable canvas, side panel.

Vue éditeur de document : ruban, canevas centré et zoomable, panneau
latéral (annotations + OCR).
"""

import asyncio
import json
import threading
from collections.abc import Callable, Coroutine
from functools import partial
from pathlib import Path
from typing import Any

import flet as ft

from lestang_pdf_editor.app.state import AppState
from lestang_pdf_editor.app.ui.common import page_scaffold, show_message, show_snackbar
from lestang_pdf_editor.app.ui.ribbon import build_ribbon
from lestang_pdf_editor.core.logging_setup import get_logger
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


def _schedule(
    page: ft.Page, handler: Callable[..., Coroutine[Any, Any, Any]], *args: Any
) -> None:
    """Schedule an async UI task without ever blocking or crashing the UI.

    Planifie une tâche UI async : via page.run_task quand disponible, sinon
    dans un thread dédié avec sa propre boucle (jamais asyncio.run() sur le
    thread appelant s'il a déjà une boucle en cours), ou en synchrone si
    aucun boucle ne tourne (tests sans affichage).
    """
    run_task = getattr(page, "run_task", None)
    if callable(run_task):
        try:
            run_task(handler, *args)
            return
        except Exception:
            pass  # fall through to the thread-based fallback
    try:
        asyncio.get_running_loop()
        has_loop = True
    except RuntimeError:
        has_loop = False
    if not has_loop:
        asyncio.run(handler(*args))
        return

    def runner() -> None:
        asyncio.run(handler(*args))

    threading.Thread(target=runner, daemon=True).start()


def _spawn(page: ft.Page, coro: Coroutine[Any, Any, Any]) -> None:
    """Run a coroutine as a background UI task without blocking the caller.

    Exécute une coroutine en tâche UI d'arrière-plan sans bloquer l'appelant.
    """

    async def consume() -> None:
        await coro

    _schedule(page, consume)


logger = get_logger("ui")
"""UI logger: one INFO line per user action.

Logger UI : une ligne INFO par action utilisateur.
"""


def _show_progress(state: AppState, value: float | None = None) -> None:
    """Show the progress bar of the active view (indeterminate if value None).

    Affiche la barre de progression de la vue active (indéterminée si
    value est None).
    """
    bar = state.ui_progress
    if bar is not None and state.page is not None:
        bar.visible = True
        bar.value = value
        state.page.update()


def _set_progress(state: AppState, done: int, total: int) -> None:
    """Set the progress bar to done/total (safe from worker threads).

    Règle la barre de progression à done/total (sûr depuis les threads
    workers : page.update() de Flet est thread-safe).
    """
    bar = state.ui_progress
    if bar is not None and total > 0 and state.page is not None:
        bar.value = min(1.0, done / total)
        state.page.update()


def _hide_progress(state: AppState) -> None:
    """Hide the progress bar of the active view.

    Masque la barre de progression de la vue active.
    """
    bar = state.ui_progress
    if bar is not None and state.page is not None:
        bar.visible = False
        state.page.update()


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
    progress_bar = ft.ProgressBar(width=220, value=None, visible=False)
    state.ui_progress = progress_bar
    search_count = ft.Text("")
    search_field: ft.TextField = ft.TextField(
        hint_text=state.t("doc.search_hint"),
        width=260,
        on_submit=lambda _e: _spawn(
            page, _search_async(state, search_field.value or "", search_count, refresh)
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
                        _spawn(
                            page,
                            _search_async(
                                state,
                                search_field.value or "",
                                search_count,
                                refresh,
                            ),
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

    thumb_images: list[ft.Image] = []

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
            thumb_images,
        )
        state._render_generation += 1
        generation = state._render_generation
        _schedule(page, _fill_thumbnails, state, thumb_images, generation)
        _schedule(page, _render_canvas, state, canvas_stack, refresh, generation)
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
        "enhance": lambda: _spawn(page, _enhance_async(state, refresh, snack)),
        "ocr": lambda: _spawn(
            page, _ocr_async(state, ocr_text, status, refresh, snack)
        ),
        "search": lambda: _toggle_search(state, search_bar, refresh),
        "duplicate": lambda: _duplicate(state, refresh, snack),
        "properties": lambda: _open_properties_dialog(state),
        "stamp": lambda key: _apply_stamp(state, key, refresh, snack),
    }

    def _logged(name: str, action: Callable[..., None]) -> Callable[..., None]:
        def run(*args: Any) -> None:
            logger.info("user action: %s", name)
            action(*args)

        return run

    actions = {name: _logged(name, action) for name, action in actions.items()}
    state.pending_export = {}

    def on_scroll(event: ft.ScrollEvent) -> None:
        _on_scroll(state, event, refresh)

    gesture = ft.GestureDetector(
        content=canvas_stack,
        # on_tap receives the raw event; on_tap_down is wrapped in TapEvent
        # with local_x/local_y (needed to place the text at the click point).
        on_tap_down=lambda e: _on_tap(state, e, canvas_stack, refresh),
        on_pan_start=lambda e: _on_pan_start(state, e),
        on_pan_update=lambda e: _on_pan_update(state, e, canvas_stack, refresh),
        on_pan_end=lambda e: _on_pan_end(state, e, canvas_stack, refresh),
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
            controls=[status, progress_bar, zoom_label],
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
    thumb_images: list[ft.Image],
) -> ft.GestureDetector:
    """Rebuild the lightweight structure (no rendering) from the state.

    Reconstruit la structure légère (sans rendu d'images) depuis l'état :
    les vignettes et le canevas sont remplis ensuite en arrière-plan par
    _fill_thumbnails / _render_canvas, pour ne jamais bloquer l'UI même
    sur un gros PDF.
    """
    thumbnails.controls.clear()
    thumb_images.clear()
    total = state.page_count()
    for index in range(total):
        image = ft.Image(width=120, height=160, fit=ft.ImageFit.COVER)
        thumb_images.append(image)
        thumbnails.controls.append(
            ft.GestureDetector(
                content=ft.Stack(
                    controls=[
                        ft.Container(
                            image,
                            width=120,
                            height=160,
                            bgcolor="#ECEFF1",
                            border_radius=4,
                        ),
                        ft.Container(
                            ft.Text(str(index + 1), size=12, color="#607D8B"),
                            alignment=ft.alignment.center,
                        ),
                    ]
                ),
                on_tap=lambda _e, i=index: _select_page(state, i),
            )
        )
    annots_list.controls.clear()
    for position, annotation in enumerate(state.annotations()):
        annots_list.controls.append(_annotation_row(state, position, annotation))
    canvas_stack.controls.clear()
    if state.document is not None and gesture is not None:
        index = state.selected_page
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


async def _fill_thumbnails(
    state: AppState, thumb_images: list[ft.Image], generation: int
) -> None:
    """Render thumbnails in the background, one page at a time.

    Rend les vignettes en arrière-plan, une page à la fois (le cache PNG
    évite de re-rendre les pages déjà vues).
    """
    page = state.page
    loop = asyncio.get_running_loop()
    total = state.page_count()
    for index in range(min(total, len(thumb_images))):
        if generation != state._render_generation:
            return
        result = await loop.run_in_executor(None, state.page_png_path, index, 72)
        if generation != state._render_generation:
            return
        if isinstance(result, Ok):
            thumb_images[index].src = str(result.value)
        if index % 4 == 3:
            page.update()
    page.update()


async def _render_canvas(
    state: AppState,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
    generation: int,
) -> None:
    """Render the current page canvas in the background.

    Rend le canevas de la page courante en arrière-plan (une seule page,
    servie par le cache PNG si déjà rendue).
    """
    page = state.page
    loop = asyncio.get_running_loop()
    if state.document is None:
        return
    index = state.selected_page
    dpi = state.display_dpi()
    result = await loop.run_in_executor(None, state.page_png_and_size, index, dpi)
    if generation != state._render_generation:
        return
    canvas_stack.controls.clear()
    if isinstance(result, Ok):
        path, base_width, base_height = result.value
        scale = state.zoom
        canvas_width = int(base_width * scale)
        canvas_height = int(base_height * scale)
        canvas_stack.width = canvas_width
        canvas_stack.height = canvas_height
        canvas_stack.controls.append(
            ft.Image(
                src=str(path),
                width=canvas_width,
                height=canvas_height,
                fit=ft.ImageFit.FILL,
            )
        )
        canvas_stack.controls.extend(
            _annotation_overlays(
                state, canvas_width, canvas_height, canvas_stack, refresh
            )
        )
    page.update()


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
    state: AppState,
    width: int,
    height: int,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
) -> list[ft.Container]:
    """Build overlay containers for the current page's annotations.

    Construit les conteneurs de superposition des annotations de la page
    courante. Les zones de texte sont interactives (Word-like) : clic =
    sélection, glisser = déplacer, double-clic = rééditer, infobulle auteur
    + horodatage au survol.
    """
    overlays: list[ft.Container] = []
    global_page = state._to_global(state.selected_page)
    for position, annotation in enumerate(state.annotations()):
        if isinstance(global_page, Err) or annotation.page_index != global_page.value:
            continue
        x, y, w, h = annotation.rect
        if isinstance(annotation, TextAnnotation):
            tooltip = ""
            if annotation.author or annotation.created_at:
                tooltip = f"{annotation.author}\n{annotation.created_at}"
            selected = state._selected_annot == position
            text_control = ft.Text(
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
            )
            gesture = ft.GestureDetector(
                content=text_control,
                on_tap=lambda _e, pos=position: _select_annotation(state, pos, refresh),
                on_double_tap=lambda _e, pos=position: _start_edit(
                    state, canvas_stack, refresh, pos
                ),
                on_pan_start=lambda e, pos=position: _move_start(state, e, pos),
                on_pan_update=lambda e: _move_update(state, e),
                on_pan_end=lambda e, pos=position: _move_end(
                    state, e, pos, canvas_stack, refresh
                ),
            )
            overlays.append(
                ft.Container(
                    content=gesture,
                    left=x * width,
                    top=y * height,
                    width=max(40.0, w * width),
                    height=max(24.0, h * height),
                    border=(
                        ft.border.all(1.5, "#1976D2")
                        if selected
                        else ft.border.all(1, "#90CAF9")
                    ),
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


def _canvas_dims(state: AppState, canvas_stack: ft.Stack) -> tuple[float, float]:
    """Return the canvas size in pixels (stack size, or rendered page size).

    Retourne la taille du canevas en pixels (taille du stack, ou taille de
    la page rendue x zoom).
    """
    if canvas_stack.width and canvas_stack.height:
        return float(canvas_stack.width), float(canvas_stack.height)
    image = state.page_image(state.selected_page, state.display_dpi())
    if isinstance(image, Err) or state.document is None:
        return 1.0, 1.0
    return image.value.width * state.zoom, image.value.height * state.zoom


def _open_text_editor(
    state: AppState,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
    rect: tuple[float, float, float, float],
    position: int | None = None,
) -> None:
    """Open an inline editor inside a text box at the given normalized rect.

    Ouvre un éditeur en ligne dans une zone de texte au rectangle normalisé
    donné (position = annotation existante en cas de réédition).
    """
    if state._editing is not None:
        _commit_editing(state, refresh)
    if state.document is None:
        return
    page = state.page
    width, height = _canvas_dims(state, canvas_stack)
    existing = state.annotations()[position] if position is not None else None
    field = ft.TextField(
        value=existing.content if isinstance(existing, TextAnnotation) else "",
        autofocus=True,
        multiline=True,
        expand=True,
        label=state.t("doc.text_content"),
    )

    def commit() -> None:
        _commit_editing(state, refresh)

    editor = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(field, expand=True),
                ft.IconButton(
                    icon=ft.Icons.CHECK,
                    tooltip=state.t("doc.validate"),
                    on_click=lambda _e: commit(),
                ),
            ],
            spacing=2,
        ),
        left=rect[0] * width,
        top=rect[1] * height,
        width=max(120.0, rect[2] * width),
        height=max(44.0, rect[3] * height),
        bgcolor="#FFFFFF",
        border=ft.border.all(1.5, "#1976D2"),
        padding=2,
    )
    state._editing = {
        "field": field,
        "container": editor,
        "rect": rect,
        "position": position,
        "canvas_stack": canvas_stack,
    }
    canvas_stack.controls.append(editor)
    page.update()


def _commit_editing(state: AppState, refresh: Callable[[], None]) -> None:
    """Validate the open text box: keep the text, drop the editor overlay.

    Valide la zone de texte ouverte : conserve le texte (nouvelle annotation
    ou mise à jour de l'existante), retire l'éditeur.
    """
    from dataclasses import replace as dc_replace

    editing = state._editing
    if editing is None:
        return
    canvas_stack = editing["canvas_stack"]
    text = (editing["field"].value or "").strip()
    rect = editing["rect"]
    position = editing["position"]
    if text:
        style = state.text_style
        if position is not None:
            old = state.annotations()[position]
            updated = dc_replace(
                old,
                content=text,
                rect=rect,
                author=state.author_name(),
                created_at=state.new_timestamp(),
            )
            state.replace_annotation(position, updated)
        else:
            state.add_annotation(
                TextAnnotation(
                    page_index=state.selected_page,
                    rect=rect,
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
    container = editing["container"]
    if container in canvas_stack.controls:
        canvas_stack.controls.remove(container)
    state._editing = None
    refresh()


def _cancel_editing(state: AppState, refresh: Callable[[], None]) -> None:
    """Cancel the open editor: discard a new empty box, keep existing text.

    Annule l'éditeur ouvert : abandonne une nouvelle zone vide, conserve le
    texte d'une zone existante.
    """
    editing = state._editing
    if editing is None:
        return
    canvas_stack = editing["canvas_stack"]
    container = editing["container"]
    if container in canvas_stack.controls:
        canvas_stack.controls.remove(container)
    state._editing = None
    refresh()


def _select_annotation(
    state: AppState, position: int, refresh: Callable[[], None]
) -> None:
    """Select an annotation (single click on its overlay).

    Sélectionne une annotation (clic simple sur sa superposition).
    """
    state._selected_annot = position
    refresh()


def _start_edit(
    state: AppState,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
    position: int,
) -> None:
    """Enter edit mode on a text box (double click): pre-fill the editor.

    Passe en édition une zone de texte (double-clic) : éditeur pré-rempli.
    """
    annotations = state.annotations()
    if 0 <= position < len(annotations):
        annotation = annotations[position]
        if isinstance(annotation, TextAnnotation):
            state._selected_annot = None
            _open_text_editor(
                state, canvas_stack, refresh, annotation.rect, position=position
            )


def _move_start(state: AppState, event: ft.DragStartEvent, position: int) -> None:
    """Start moving the selected text box (drag on its overlay).

    Démarre le déplacement de la zone de texte sélectionnée (glisser sur sa
    superposition).
    """
    annotations = state.annotations()
    if 0 <= position < len(annotations):
        state._move = {
            "position": position,
            "start": _local_point(event),
            "orig_rect": annotations[position].rect,
        }
        state._drag_start = None


def _move_update(state: AppState, event: ft.DragUpdateEvent) -> None:
    """Visually move the box while dragging (persist on pan end).

    Déplace visuellement la zone pendant le glisser (persisté au relâchement).
    """
    move = state._move
    if move is None:
        return
    move["current"] = _local_point(event)


def _move_end(
    state: AppState,
    event: ft.DragEndEvent,
    position: int,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
) -> None:
    """Persist the moved text box rect (drag end on its overlay).

    Persiste le rectangle déplacé de la zone de texte (fin du glisser).
    """
    from dataclasses import replace as dc_replace

    move = state._move
    state._move = None
    if move is None or move["position"] != position:
        return
    start = move["start"]
    end = move.get("current") or start
    width, height = _canvas_dims(state, canvas_stack)
    dx = (end[0] - start[0]) / width
    dy = (end[1] - start[1]) / height
    ox, oy, ow, oh = move["orig_rect"]
    new_rect = (ox + dx, oy + dy, ow, oh)
    annotations = state.annotations()
    if 0 <= position < len(annotations):
        state.replace_annotation(
            position, dc_replace(annotations[position], rect=new_rect)
        )
    state._selected_annot = None
    refresh()


def _on_tap(
    state: AppState,
    event: ft.TapEvent,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
) -> None:
    """Handle canvas clicks (commit open text box / open a new one).

    Gère les clics sur le canevas (valide la zone ouverte / en ouvre une
    nouvelle).

    Comportement du clic : valide toute zone de texte ouverte (cliquer
    ailleurs conserve le texte) ; avec l'outil texte, ouvre une zone de
    taille par défaut au point cliqué.
    """
    if state.document is None:
        return
    if state._editing is not None:
        _commit_editing(state, refresh)
        if state.tool != "text":
            return
    if state.tool != "text":
        if state._selected_annot is not None:
            state._selected_annot = None
            refresh()
        return
    point_x, point_y = _local_point(event)
    width, height = _canvas_dims(state, canvas_stack)
    norm_x = min(max(point_x / width, 0.0), 1.0)
    norm_y = min(max(point_y / height, 0.0), 1.0)
    # Default box size when the user just clicks (Word-like auto box):
    # ~30% of the page width, ~5% of its height.
    # Taille par défaut quand l'utilisateur clique simplement (zone auto
    # style Word) : ~30 % de la largeur de page, ~5 % de sa hauteur.
    rect = (norm_x, norm_y, 0.30, 0.05)
    _open_text_editor(state, canvas_stack, refresh, rect)


def _on_pan_start(state: AppState, event: ft.DragStartEvent) -> None:
    """Remember the drag start point for drawing/moving tools.

    Mémorise le point de début de glisser pour les outils de dessin.
    """
    if state._move is not None:
        return
    state._drag_start = _local_point(event)
    state._drag_last = state._drag_start


def _on_pan_update(
    state: AppState,
    event: ft.DragUpdateEvent,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
) -> None:
    """Track the drag and show a live shape preview (rect/highlight/text box).

    Suit le glisser et affiche un aperçu en direct de la forme dessinée
    (cadre / surlignage / zone de texte).
    """
    state._drag_last = _local_point(event)
    if state.tool not in ("rect", "highlight", "text") or state._drag_start is None:
        return
    if state._move is not None:
        return
    start = state._drag_start
    end = state._drag_last
    x = min(start[0], end[0])
    y = min(start[1], end[1])
    w = abs(end[0] - start[0])
    h = abs(end[1] - start[1])
    if w < 3 and h < 3:
        return
    color = "#1976D2" if state.tool != "highlight" else "#FFEB3B"
    preview = state._drag_preview
    if preview is None:
        preview = ft.Container(border=ft.border.all(1.5, color))
        state._drag_preview = preview
        canvas_stack.controls.append(preview)
    preview.left = x
    preview.top = y
    preview.width = w
    preview.height = h
    preview.bgcolor = (
        ft.Colors.with_opacity(0.25, color) if state.tool == "highlight" else None
    )
    if state.page is not None:
        state.page.update()


def _on_pan_end(
    state: AppState,
    event: ft.DragEndEvent,
    canvas_stack: ft.Stack,
    refresh: Callable[[], None],
) -> None:
    """Create the annotation from the drag gesture (shape or text box).

    Crée l'annotation à partir du glisser (forme ou zone de texte dessinée).

    Crée l'annotation à partir du glisser : forme (cadre/surlignage) ou une
    zone de texte de la taille dessinée (outil texte).
    """
    if state._move is not None:
        return
    preview = state._drag_preview
    if preview is not None:
        if preview in canvas_stack.controls:
            canvas_stack.controls.remove(preview)
        state._drag_preview = None
    start = state._drag_start
    end_point = state._drag_last
    state._drag_start = None
    state._drag_last = None
    if start is None or state.document is None:
        return
    if end_point is None:
        end_point = start
    width, height = _canvas_dims(state, canvas_stack)
    x1, y1 = start[0] / width, start[1] / height
    x2, y2 = end_point[0] / width, end_point[1] / height
    rect = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    if state.tool == "text":
        if rect[2] < 0.01 or rect[3] < 0.01:
            rect = (min(x1, 1.0 - 0.30), min(y1, 1.0 - 0.05), 0.30, 0.05)
        _open_text_editor(state, canvas_stack, refresh, rect)
    elif state.tool in ("rect", "highlight"):
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
    key = (event.key or "").lower()
    if isinstance(focused, ft.TextField):
        # While editing a text box: Ctrl+Enter validates (Enter = newline).
        # Pendant l'édition d'une zone : Ctrl+Entrée valide (Entrée = saut de
        # ligne).
        if state._editing is not None and state.ctrl_pressed and key == "enter":
            _commit_editing(state, refresh)
        return
    if key == "escape":
        if state._editing is not None:
            _cancel_editing(state, refresh)
        elif state._selected_annot is not None:
            state._selected_annot = None
            refresh()
        return
    if key in ("delete", "backspace") and state._selected_annot is not None:
        state.remove_annotation_at(state._selected_annot)
        state._selected_annot = None
        refresh()
        return
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


async def _enhance_async(
    state: AppState, refresh: Callable[[], None], snack: Callable[[str], None]
) -> None:
    """Run the one-tap enhancement off the UI thread.

    Lance l'amélioration en un clic hors du thread UI (gros fichiers).
    """
    loop = asyncio.get_running_loop()
    _show_progress(state)
    try:
        result = await loop.run_in_executor(
            None, state.enhance_page, state.selected_page
        )
        if isinstance(result, Ok):
            snack(state.t("doc.enhanced"))
        else:
            snack(f"Error: {result.error}")
        refresh()
    finally:
        _hide_progress(state)


async def _ocr_async(
    state: AppState,
    ocr_text: ft.TextField,
    status: ft.Text,
    refresh: Callable[[], None],
    snack: Callable[[str], None],
) -> None:
    """Run OCR on the current page off the UI thread.

    Lance l'OCR sur la page courante hors du thread UI et affiche le texte
    reconnu.
    """
    loop = asyncio.get_running_loop()
    _show_progress(state)
    try:
        result = await loop.run_in_executor(None, state.ocr_page, state.selected_page)
        if isinstance(result, Ok):
            ocr_text.value = state.page_ocr.get(state.selected_page, "")
            snack(f"OCR: {len(result.value)} blocks")
        else:
            snack(f"OCR error: {result.error}")
        refresh()
    finally:
        _hide_progress(state)


def _on_pick_open(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Reopen another file from the document view (Ctrl+O), off the UI thread.

    Rouvre un autre fichier depuis la vue document (Ctrl+O), hors du thread
    UI pour ne pas figer l'affichage sur un gros fichier.
    """
    if not event.files:
        return
    path = event.files[0].path or str(Path(event.files[0].name))
    _spawn(state.page, _open_async(state, path))


async def _open_async(state: AppState, path: str) -> None:
    """Open a file off the UI thread, then build the document view.

    Ouvre un fichier hors du thread UI, puis construit la vue document.
    """
    loop = asyncio.get_running_loop()
    _show_progress(state)
    try:
        result = await loop.run_in_executor(None, state.open_path, path)
        if isinstance(result, Ok):
            try:
                build_document_view(state)
            except Exception:
                import traceback

                logger.exception("document view build failed")
                show_message(state.page, "Error", traceback.format_exc())
        else:
            show_message(state.page, "Error", result.error)
    finally:
        _hide_progress(state)


def _on_insert(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Insert all pages of a picked PDF at the end (ribbon action).

    Insère toutes les pages d'un PDF choisi à la fin (action du ruban),
    hors du thread UI.
    """
    if not event.files:
        return
    path = event.files[0].path or str(Path(event.files[0].name))
    _spawn(state.page, _insert_async(state, path))


async def _insert_async(state: AppState, path: str) -> None:
    """Insert a PDF off the UI thread, then notify the view.

    Insère un PDF hors du thread UI, puis notifie la vue.
    """
    loop = asyncio.get_running_loop()
    _show_progress(state)
    try:
        result = await loop.run_in_executor(None, state.insert_pdf, path)
        if isinstance(result, Ok):
            show_snackbar(state.page, f"+{result.value} pages")
            state._notify()
        else:
            show_message(state.page, "Error", result.error)
    finally:
        _hide_progress(state)


def _on_save(state: AppState, event: ft.FilePickerResultEvent) -> None:
    """Handle the save-file result: export with the pending dialog options.

    Gère le résultat du sélecteur de sauvegarde : lance l'export avec les
    options de la boîte de dialogue, hors du thread UI.
    """
    if not event.path or state.document is None:
        return
    _spawn(state.page, _export_async(state, event.path))


async def _export_async(state: AppState, destination: str) -> None:
    """Export the PDF off the UI thread, then show the result.

    Exporte le PDF hors du thread UI, puis affiche le résultat.
    """
    pending = state.pending_export
    loop = asyncio.get_running_loop()
    _show_progress(state)
    try:
        result = await loop.run_in_executor(
            None,
            partial(
                state.export_pdf,
                destination,
                flatten=bool(pending.get("flatten", False)),
                watermark=str(pending.get("watermark") or "") or None,
                password=str(pending.get("password") or "") or None,
            ),
        )
        if isinstance(result, Ok):
            show_snackbar(state.page, f"Saved: {destination}")
        else:
            show_message(state.page, "Error", result.error)
    finally:
        _hide_progress(state)


def _toggle_search(
    state: AppState, search_bar: ft.Container, refresh: Callable[[], None]
) -> None:
    """Show/hide the search bar (Ctrl+F or ribbon button).

    Affiche/masque la barre de recherche (Ctrl+F ou bouton du ruban).
    """
    search_bar.visible = not search_bar.visible
    refresh()


async def _search_async(
    state: AppState,
    query: str,
    search_count: ft.Text,
    refresh: Callable[[], None],
) -> None:
    """Run the search over all pages off the UI thread and show the count.

    Lance la recherche sur toutes les pages (OCR à la volée) hors du thread
    UI et affiche le nombre de résultats.
    """
    loop = asyncio.get_running_loop()
    _show_progress(state, 0.0)
    try:
        state._search_query = query
        state._search_matches = await loop.run_in_executor(
            None,
            partial(
                state.search,
                query,
                progress=lambda done, total: _set_progress(state, done, total),
            ),
        )
        state._search_position = -1
        search_count.value = state.t("doc.search_results").format(
            n=len(state._search_matches)
        )
        refresh()
    finally:
        _hide_progress(state)


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
