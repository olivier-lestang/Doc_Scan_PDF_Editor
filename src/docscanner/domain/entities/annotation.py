"""Annotation model, stored as native PDF annotations for compatibility.

Modèle d'annotations, stocké sous forme d'annotations PDF natives pour la
compatibilité avec tous les lecteurs PDF.
"""

from dataclasses import dataclass
from typing import Literal

Rect = tuple[float, float, float, float]
"""Normalized rectangle (x, y, width, height), each in [0, 1] of the page.

Rectangle normalisé (x, y, largeur, hauteur), chaque valeur dans [0, 1].
"""


@dataclass(frozen=True)
class TextAnnotation:
    """Free-text comment with font family, size and color.

    Commentaire texte libre avec police, taille et couleur.
    """

    kind: Literal["text"] = "text"
    page_index: int = 0
    rect: Rect = (0.0, 0.0, 0.0, 0.0)
    content: str = ""
    font_family: str = "Helvetica"
    font_size_pt: float = 12.0
    color: str = "#000000"


@dataclass(frozen=True)
class RectangleAnnotation:
    """Rectangle (box) drawn on a page.

    Cadre (rectangle) dessiné sur une page.
    """

    kind: Literal["rectangle"] = "rectangle"
    page_index: int = 0
    rect: Rect = (0.0, 0.0, 0.0, 0.0)
    stroke_color: str = "#FF0000"
    stroke_width_pt: float = 1.0


@dataclass(frozen=True)
class HighlightAnnotation:
    """Highlight (marker) over existing content.

    Surlignage (marqueur) par-dessus un contenu existant.
    """

    kind: Literal["highlight"] = "highlight"
    page_index: int = 0
    rect: Rect = (0.0, 0.0, 0.0, 0.0)
    color: str = "#FFFF00"


Annotation = TextAnnotation | RectangleAnnotation | HighlightAnnotation
"""Union of all annotation kinds.

Union de tous les types d'annotations.
"""
