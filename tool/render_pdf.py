"""Render a Markdown-ish text file to a simple A4 PDF (via Pillow).

Rend un fichier texte façon Markdown en un PDF A4 simple (via Pillow).

Usage: uv run python tool/render_pdf.py <source.md> <destination.pdf>

Usage : uv run python tool/render_pdf.py docs/UI_DESIGN_GUIDE.md docs/UI_DESIGN_GUIDE.pdf
"""

import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PAGE_W, PAGE_H = 2480, 3508  # A4 at 300 dpi
MARGIN = 220
LINE_H = 64
BODY_SIZE = 44
HEAD_SIZE = 64
TITLE_SIZE = 84
"""Font sizes used to render the PDF (300 dpi A4).

Tailles de police utilisées pour le rendu du PDF (A4 à 300 dpi).
"""


def load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    """Load DejaVu regular/bold if available, else the default bitmap font.

    Charge DejaVu régulier/gras si disponible, sinon la police bitmap par
    défaut.
    """
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]

    def pick(paths: list[str]) -> ImageFont.FreeTypeFont:
        for path in paths:
            if Path(path).exists():
                return ImageFont.truetype(path, BODY_SIZE)
        return ImageFont.load_default()

    regular = pick(candidates)
    bold = pick(bold_candidates)
    return regular, bold


def render_pdf(source: Path, destination: Path) -> None:
    """Render the source text file into a paginated A4 PDF.

    Rend le fichier texte source en un PDF A4 paginé.
    """
    regular, bold = load_fonts()
    lines = source.read_text(encoding="utf-8").splitlines()
    pages: list[Image.Image] = []
    current = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(current)
    y = MARGIN

    def new_page() -> None:
        nonlocal current, draw, y
        pages.append(current)
        current = Image.new("RGB", (PAGE_W, PAGE_H), "white")
        draw = ImageDraw.Draw(current)
        y = MARGIN

    for raw in lines:
        line = raw.rstrip()
        if y > PAGE_H - MARGIN - LINE_H:
            new_page()
        if line.startswith("# "):
            draw.text((MARGIN, y), line[2:], fill="black", font=bold)
            y += HEAD_SIZE + 20
        elif line.startswith("## "):
            draw.text((MARGIN, y), line[3:], fill="#1976D2", font=bold)
            y += HEAD_SIZE
        elif not line.strip():
            y += LINE_H // 2
        else:
            text = line.lstrip("- ").strip()
            wrapped = textwrap.wrap(
                text,
                width=88,
                initial_indent="• " if line.lstrip().startswith("-") else "",
            )
            for wrapped_line in wrapped:
                draw.text((MARGIN, y), wrapped_line, fill="black", font=regular)
                y += LINE_H
    if pages or y > MARGIN:
        pages.append(current)

    # page numbers
    for index, page_image in enumerate(pages, start=1):
        draw = ImageDraw.Draw(page_image)
        label = f"{index} / {len(pages)}"
        draw.text(
            (PAGE_W - MARGIN - draw.textlength(label, font=regular), PAGE_H - 140),
            label,
            fill="#607D8B",
            font=regular,
        )
    pages[0].save(
        destination,
        save_all=True,
        append_images=pages[1:],
        resolution=300.0,
    )
    print(f"wrote {destination} ({len(pages)} pages)")


def main() -> None:
    """CLI entry: render_pdf.py <source.md> <destination.pdf>.

    Entrée CLI : render_pdf.py <source.md> <destination.pdf>.
    """
    if len(sys.argv) != 3:
        msg = "usage: render_pdf.py <source.md> <destination.pdf>"
        raise SystemExit(msg)
    render_pdf(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
