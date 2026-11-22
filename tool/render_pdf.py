"""Render a Markdown-ish text file to a styled A4 PDF (via Pillow).

Rend un fichier texte façon Markdown en un PDF A4 stylisé (via Pillow).

Produces a cover page (blue gradient, large title) and body pages with
blue headings, bullets, dark code blocks and a footer with page numbers.

Produit une page de couverture (dégradé bleu, grand titre) et des pages de
corps avec titres bleus, puces, blocs de code sombres et un pied de page.

Usage: uv run python tool/render_pdf.py <source.md> <destination.pdf>

Usage : uv run python tool/render_pdf.py <source.md> <destination.pdf>
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PAGE_W, PAGE_H = 2480, 3508  # A4 at 300 dpi
MARGIN = 210
BODY_TOP = 300  # first content line on body pages (below the header)
BODY_BOTTOM = PAGE_H - 260

INK = "#212121"
MUTED = "#607D8B"
BLUE_DARK = "#0D47A1"
BLUE = "#1565C0"
BLUE_LIGHT = "#42A5F5"
CODE_BG = "#263238"
CODE_INK = "#ECEFF1"
CODE_CHIP = "#ECEFF1"
RULE = "#B0BEC5"
WHITE = "#FFFFFF"
COVER_SUB = "#E3F2FD"
ACCENT = "#FFC107"

TITLE_SIZE = 118
SUB_SIZE = 52
H1_SIZE = 80
H2_SIZE = 62
H3_SIZE = 50
BODY_SIZE = 46
CODE_SIZE = 40
HEADER_SIZE = 34

BODY_LINE = 74
CODE_LINE = 64

FONT_FILES = {
    "regular": "DejaVuSans.ttf",
    "bold": "DejaVuSans-Bold.ttf",
    "mono": "DejaVuSansMono.ttf",
}
"""Font file names looked up in DejaVu / cv2-bundled / Windows font dirs.

Noms des fichiers de police cherchés dans les dossiers DejaVu / cv2 / Windows.
"""


def _font_dirs() -> list[Path]:
    """Return candidate directories that may contain TrueType fonts.

    Retourne les dossiers candidats pouvant contenir des polices TrueType.
    """
    dirs = [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/dejavu"),
        Path("C:/Windows/Fonts"),
    ]
    try:
        import cv2

        dirs.append(Path(cv2.__file__).resolve().parent / "qt" / "fonts")
    except ImportError:
        pass
    return dirs


def load_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    """Load regular/bold/mono plus heading sizes, with safe fallbacks.

    Charge les polices régulière/gras/mono et les tailles de titres, avec
    repli sûr.
    """
    found: dict[str, Path] = {}
    for directory in _font_dirs():
        for name, filename in FONT_FILES.items():
            candidate = directory / filename
            if name not in found and candidate.exists():
                found[name] = candidate
        arial_bold = directory / "arialbd.ttf"
        if "bold" not in found and arial_bold.exists():
            found["bold"] = arial_bold

    def font(name: str, size: int) -> ImageFont.FreeTypeFont:
        path = found.get(name)
        if path is not None:
            return ImageFont.truetype(str(path), size)
        return ImageFont.load_default(size=size)

    return {
        "regular": font("regular", BODY_SIZE),
        "bold": font("bold", BODY_SIZE),
        "mono": font("mono", CODE_SIZE),
        "title": font("bold", TITLE_SIZE),
        "sub": font("regular", SUB_SIZE),
        "h1": font("bold", H1_SIZE),
        "h2": font("bold", H2_SIZE),
        "h3": font("bold", H3_SIZE),
        "header": font("regular", HEADER_SIZE),
    }


def strip_markup(text: str) -> str:
    """Remove ** and ` markers to measure the visible width of a line.

    Retire les marqueurs ** et ` pour mesurer la largeur visible d'une ligne.
    """
    return text.replace("**", "").replace("`", "")


def _draw_code_chip(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
) -> float:
    """Draw inline code text on a light rounded chip; return the end x.

    Dessine un texte de code inline sur un fond arrondi clair ; renvoie le x.
    """
    width = draw.textlength(text, font=font)
    draw.rounded_rectangle(
        [x - 6, y - 2, x + width + 6, y + CODE_SIZE + 8],
        radius=10,
        fill=CODE_CHIP,
    )
    draw.text((x, y + 2), text, fill=BLUE_DARK, font=font)
    return x + width + draw.textlength(" ", font=font)


def draw_rich(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    fonts: dict[str, ImageFont.FreeTypeFont],
    color: str = INK,
) -> float:
    """Draw a line with **bold** and `code` inline segments; return end x.

    Dessine une ligne avec des segments **gras** et `code` ; renvoie le x final.
    """
    bold = False
    code = False
    cursor = x
    segment = ""

    def flush() -> None:
        nonlocal cursor, segment
        if not segment:
            return
        if code:
            cursor = _draw_code_chip(draw, cursor, y, segment, fonts["mono"])
        else:
            font = fonts["bold"] if bold else fonts["regular"]
            draw.text((cursor, y), segment, fill=color, font=font)
            cursor += draw.textlength(segment, font=font)
        segment = ""

    for char in text:
        if char == "*" and segment.endswith("*"):
            segment = segment[:-1]
            flush()
            bold = not bold
            continue
        if char == "`":
            flush()
            code = not code
            continue
        segment += char
    flush()
    return cursor


def wrap_words(
    text: str,
    max_width: float,
    font: ImageFont.FreeTypeFont,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """Wrap a (possibly marked-up) line into lines fitting max_width.

    Découpe une ligne (éventuellement balisée) en lignes tenant dans max_width.
    """
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}".strip()
        if draw.textlength(strip_markup(candidate), font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def parse_blocks(
    lines: list[str],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Parse markdown-ish lines into (cover blocks, body blocks).

    Analyse les lignes façon Markdown en blocs (couverture, corps).
    """
    blocks: list[tuple[str, str]] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(("p", " ".join(paragraph)))
            paragraph = []

    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                blocks.append(("code", "\n".join(code_lines)))
                code_lines = []
            else:
                flush_paragraph()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(raw.rstrip("\n"))
            continue
        if not line.strip():
            flush_paragraph()
            continue
        if line.startswith("### "):
            flush_paragraph()
            blocks.append(("h3", line[4:]))
        elif line.startswith("## "):
            flush_paragraph()
            blocks.append(("h2", line[3:]))
        elif line.startswith("# "):
            flush_paragraph()
            blocks.append(("h1", line[2:]))
        elif line.strip() == "---":
            flush_paragraph()
            blocks.append(("rule", ""))
        elif line.lstrip().startswith("- "):
            flush_paragraph()
            blocks.append(("bullet", line.lstrip()[2:]))
        else:
            paragraph.append(line.strip())
    flush_paragraph()
    if in_code and code_lines:
        blocks.append(("code", "\n".join(code_lines)))

    cover: list[tuple[str, str]] = []
    if blocks and blocks[0][0] == "h1":
        cover.append(blocks.pop(0))
        while blocks and blocks[0][0] == "p":
            cover.append(blocks.pop(0))
    return cover, blocks


def gradient_background(top: str, bottom: str) -> Image.Image:
    """Build a full-page vertical gradient image between two hex colors.

    Construit une image pleine page en dégradé vertical entre deux couleurs.
    """
    image = Image.new("RGB", (PAGE_W, PAGE_H))
    top_rgb = tuple(int(top[i : i + 2], 16) for i in (1, 3, 5))
    bottom_rgb = tuple(int(bottom[i : i + 2], 16) for i in (1, 3, 5))
    draw = ImageDraw.Draw(image)
    for y in range(PAGE_H):
        ratio = y / PAGE_H
        color = tuple(
            round(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * ratio) for i in range(3)
        )
        draw.line([(0, y), (PAGE_W, y)], fill=color)
    return image


class PdfRenderer:
    """Paginate styled blocks onto A4 pages and save the PDF.

    Pagine des blocs stylisés sur des pages A4 et enregistre le PDF.
    """

    def __init__(
        self, fonts: dict[str, ImageFont.FreeTypeFont], doc_title: str
    ) -> None:
        """Store fonts and start with an empty cover page.

        Mémorise les polices et démarre avec une page de couverture vide.
        """
        self.fonts = fonts
        self.doc_title = doc_title
        self.pages: list[Image.Image] = []
        self.current = gradient_background(BLUE_DARK, BLUE_LIGHT)
        self.draw = ImageDraw.Draw(self.current)
        self.y = 0.0
        self.on_cover = True

    def new_body_page(self) -> None:
        """Finish the current page and start a fresh white body page.

        Termine la page courante et démarre une page de corps blanche.
        """
        self.pages.append(self.current)
        self.current = Image.new("RGB", (PAGE_W, PAGE_H), WHITE)
        self.draw = ImageDraw.Draw(self.current)
        self.y = float(BODY_TOP)
        self.on_cover = False

    def ensure_space(self, height: float) -> None:
        """Start a new body page when the remaining space is too small.

        Démarre une nouvelle page si l'espace restant est insuffisant.
        """
        if self.on_cover:
            return
        if self.y + height > BODY_BOTTOM:
            self.new_body_page()

    def render_cover(self, blocks: list[tuple[str, str]]) -> None:
        """Render the cover page: big title, subtitle, accent bar.

        Rend la page de couverture : grand titre, sous-titre, barre d'accent.
        """
        title = ""
        subtitle = ""
        for kind, text in blocks:
            if kind == "h1" and not title:
                title = text
            elif kind == "p" and not subtitle:
                subtitle = text
        y = PAGE_H * 0.28
        for line in wrap_words(
            title, PAGE_W - 2 * MARGIN, self.fonts["title"], self.draw
        ):
            self.draw.text((MARGIN, y), line, fill=WHITE, font=self.fonts["title"])
            y += TITLE_SIZE + 18
        y += 40
        self.draw.rounded_rectangle(
            [MARGIN, y, MARGIN + 420, y + 16], radius=8, fill=ACCENT
        )
        y += 70
        for line in wrap_words(
            subtitle, PAGE_W - 2 * MARGIN, self.fonts["sub"], self.draw
        ):
            self.draw.text((MARGIN, y), line, fill=COVER_SUB, font=self.fonts["sub"])
            y += SUB_SIZE + 16
        self.draw.text(
            (MARGIN, PAGE_H - 190),
            "Lestang PDF Editor",
            fill=COVER_SUB,
            font=self.fonts["header"],
        )

    def render_blocks(self, blocks: list[tuple[str, str]]) -> None:
        """Render all body blocks with pagination.

        Rend tous les blocs du corps avec pagination.
        """
        for kind, text in blocks:
            if kind == "h1":
                self.ensure_space(H1_SIZE + 90)
                self.draw.text(
                    (MARGIN, self.y), text, fill=BLUE_DARK, font=self.fonts["h1"]
                )
                self.y += H1_SIZE + 14
                self.draw.line(
                    [(MARGIN, self.y), (MARGIN + 700, self.y)],
                    fill=BLUE_LIGHT,
                    width=8,
                )
                self.y += 46
            elif kind == "h2":
                self.ensure_space(H2_SIZE + 70)
                self.draw.text((MARGIN, self.y), text, fill=BLUE, font=self.fonts["h2"])
                self.y += H2_SIZE + 34
            elif kind == "h3":
                self.ensure_space(H3_SIZE + 56)
                self.draw.text((MARGIN, self.y), text, fill=INK, font=self.fonts["h3"])
                self.y += H3_SIZE + 26
            elif kind == "rule":
                self.ensure_space(60)
                self.draw.line(
                    [(MARGIN, self.y + 20), (PAGE_W - MARGIN, self.y + 20)],
                    fill=RULE,
                    width=3,
                )
                self.y += 60
            elif kind == "code":
                code_lines = text.split("\n") or [""]
                height = len(code_lines) * CODE_LINE + 56
                self.ensure_space(height)
                self.draw.rounded_rectangle(
                    [MARGIN, self.y, PAGE_W - MARGIN, self.y + height - 20],
                    radius=18,
                    fill=CODE_BG,
                )
                cy = self.y + 28
                for code_line in code_lines:
                    self.draw.text(
                        (MARGIN + 36, cy),
                        code_line,
                        fill=CODE_INK,
                        font=self.fonts["mono"],
                    )
                    cy += CODE_LINE
                self.y += height + 16
            elif kind == "bullet":
                wrapped = wrap_words(
                    text, PAGE_W - 2 * MARGIN - 60, self.fonts["regular"], self.draw
                )
                self.ensure_space(BODY_LINE * len(wrapped) + 10)
                self.draw.ellipse(
                    [MARGIN + 8, self.y + 26, MARGIN + 28, self.y + 46], fill=BLUE
                )
                for line in wrapped:
                    draw_rich(self.draw, MARGIN + 60, self.y, line, self.fonts, INK)
                    self.y += BODY_LINE
                self.y += 6
            else:
                wrapped = wrap_words(
                    text, PAGE_W - 2 * MARGIN, self.fonts["regular"], self.draw
                )
                self.ensure_space(BODY_LINE * len(wrapped) + 10)
                for line in wrapped:
                    draw_rich(self.draw, MARGIN, self.y, line, self.fonts, INK)
                    self.y += BODY_LINE
                self.y += 14

    def finish(self, destination: Path) -> None:
        """Add headers/footers to body pages and save the PDF file.

        Ajoute en-têtes/pieds de page aux pages de corps et enregistre le PDF.
        """
        self.pages.append(self.current)
        total = len(self.pages)
        for index, page_image in enumerate(self.pages):
            draw = ImageDraw.Draw(page_image)
            if index > 0:
                draw.text(
                    (MARGIN, 110), self.doc_title, fill=MUTED, font=self.fonts["header"]
                )
                draw.line([(MARGIN, 170), (PAGE_W - MARGIN, 170)], fill=RULE, width=2)
            label = f"{index + 1} / {total}"
            width = draw.textlength(label, font=self.fonts["header"])
            draw.text(
                (PAGE_W - MARGIN - width, PAGE_H - 130),
                label,
                fill=MUTED,
                font=self.fonts["header"],
            )
            if index > 0:
                draw.line(
                    [(MARGIN, PAGE_H - 170), (PAGE_W - MARGIN, PAGE_H - 170)],
                    fill=RULE,
                    width=2,
                )
        self.pages[0].save(
            destination,
            save_all=True,
            append_images=self.pages[1:],
            resolution=300.0,
        )
        print(f"wrote {destination} ({total} pages)")


def render_pdf(source: Path, destination: Path) -> None:
    """Render the source markdown-ish file into a styled A4 PDF.

    Rend le fichier source façon Markdown en un PDF A4 stylisé.
    """
    fonts = load_fonts()
    lines = source.read_text(encoding="utf-8").splitlines()
    cover, body = parse_blocks(lines)
    doc_title = next((text for kind, text in cover if kind == "h1"), source.stem)
    renderer = PdfRenderer(fonts, doc_title)
    renderer.render_cover(cover)
    renderer.new_body_page()
    renderer.render_blocks(body)
    renderer.finish(destination)


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
