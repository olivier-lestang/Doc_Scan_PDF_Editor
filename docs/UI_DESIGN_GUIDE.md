# Guide de l'interface (UI) — Lestang PDF Editor

Ce guide explique où se trouve l'UI, comment la modifier, ce qui est
possible, et les conventions suivies par les grands éditeurs de logiciels.
(Généré aussi en PDF : `docs/UI_DESIGN_GUIDE.pdf` via
`uv run python tool/render_pdf.py docs/UI_DESIGN_GUIDE.md docs/UI_DESIGN_GUIDE.pdf`.)

## 1. Où se trouve l'UI dans le code

```
src/lestang_pdf_editor/app/
├── main.py            # point d'entrée Flet : thème (Material 3, bleu #1976D2), F5
├── state.py           # AppState : état global (outil actif, style texte, zoom,
│                      #   réglages persistants...) — testable sans UI
└── ui/
    ├── common.py      # scaffold (fond dégradé bleu), barre d'app custom, snackbars, dialogues
    ├── home.py        # accueil : ouvrir un fichier, fichiers récents
    ├── document_view.py  # éditeur : canevas centré/zoomable, éditeur de texte inline
    │                     #   (_on_tap -> commit), raccourcis clavier (_on_keyboard),
    │                     #   gestes souris (_on_pan_*), panneau annotations + OCR
    ├── ribbon.py      # le ruban (groupes Fichier/Page/Insertion/Style/Image/Affichage/Édition)
    └── settings_view.py  # réglages : nom/prénom, langue, DPI, thème, langues OCR, pages légales
assets/i18n/{en,fr,es,zh}.json   # tous les libellés de l'UI (4 langues)
```

Règle d'architecture : `domain/` (métier pur) ne dépend jamais de l'UI ;
l'UI (`app/ui/`) ne parle au métier que via `AppState` / les ports de
`domain/ports/`.

## 2. Comment modifier l'UI — exemples concrets

- **Changer la couleur du thème** : `THEME_SEED` dans `app/main.py`.
- **Ajouter un bouton au ruban** : ajouter un contrôle dans le groupe
  concerné de `build_ribbon(...)` dans `ui/ribbon.py` (ex. un
  `ft.ElevatedButton` ou `ft.IconButton` avec `on_click`). Un nouveau menu =
  un nouveau `_ribbon_group("...", [...])` dans la `ft.Row`.
- **Changer un libellé** : éditer la clé dans `assets/i18n/fr.json` (et
  en/es/zh — test d'égalité des clés dans `tests/test_app_state.py`).
- **Changer le comportement de saisie de texte** : `ui/document_view.py`,
  fonction `_on_tap` (création de l'éditeur inline au point cliqué) et sa
  closure `commit()` (validation par Entrée ou bouton ✓). Les raccourcis
  globaux sont dans `_on_keyboard` (ils sont ignorés quand le focus est dans
  un champ texte).
- **Changer la palette de couleurs du ruban** : `_color_palette(...)` dans
  `ui/ribbon.py` + les dictionnaires `TEXT_COLORS` / `HIGHLIGHT_COLORS`
  (pastilles de couleur, le hex n'est qu'en info-bulle).
- **Changer le zoom** : `AppState.set_zoom/zoom_in/zoom_out/zoom_fit` dans
  `app/state.py` ; raccourcis Ctrl+molette / Ctrl +/-/0 dans `document_view.py`.
- **Modifier l'apparence d'une page** : `page_scaffold(...)` dans
  `ui/common.py` (fond en dégradé vertical bleu clair, barre d'app custom).

## 3. Ce qui est déjà en place / possible avec Flet 0.28.3

- Vues : accueil, éditeur de document, réglages/légal (mentions légales,
  licences OSS générées, nouveautés depuis CHANGELOG.md, confidentialité).
- Ruban à groupes (style Office) : Fichier, Page, Insertion, Style, Image,
  Affichage, Édition.
- Canevas centré, zoom (boutons, Ctrl+molette, Ctrl +/-/0, ajuster
  largeur/page), vignettes de pages, navigation PgUp/PgDn/Espace.
- Annotations : texte inline (police, taille, gras, italique, souligné,
  couleur, surligneur), cadres, surlignages ; infobulle au survol (auteur +
  horodatage avec fuseau horaire) ; export en annotations PDF natives
  (/FreeText, /Square, /Highlight, /Underline) ; annulation Ctrl+Z ;
  panneau d'annotations avec suppression unitaire.
- Pages : rotation ±90°, suppression, insertion d'un autre PDF (fusion),
  export normal ou aplati (images seules).
- Image : amélioration en un clic (OpenCV : CLAHE, luminosité, débruitage,
  netteté), OCR embarqué (RapidOCR/ONNX) avec langues choisies par
  l'utilisateur + détection de langue (langdetect).
- Thèmes clair/sombre/système (persistés), snackbars, dialogues, fichiers
  récents persistés, réglages persistants entre mises à jour.
- Raccourcis : Ctrl+O ouvrir, Ctrl+E exporter, Ctrl+Z annuler, Ctrl+0 zoom,
  Ctrl +/-, Ctrl+molette, PgUp/PgDn.
- Internationalisation : en/fr/es/zh ; le support droite-à-gauche (arabe,
  hébreu) est prévu par la structure (propriétés directionnelles) pour plus
  tard.

## 4. Conventions des grands éditeurs (ce que l'on applique ici)

- **Ruban (rubbon) à la Microsoft Office** : groupes avec légende,
  séparateurs, raccourcis affichés en info-bulle ; actions fréquentes en
  boutonstexte, secondaires en icônes.
- **Palettes de couleurs** (pastilles) plutôt que codes hex, avec aperçu de
  la couleur courante (comme Word/Photoshop).
- **Annuler/Refaire (Ctrl+Z/Ctrl+Y)**, **zoom** avec pourcentage et
  « ajuster à la page/largeur », **barre d'état** en bas (fichier, page x/y,
  zoom).
- **Thème clair/sombre** suivant le système, couleurs Material 3.
- **Infobulles d'audit** (auteur + date) sur les commentaires — comme les
  révisions Word/Acrobat.
- **PDF natif** : annotations en objets PDF standard (ISO 32000), lisibles
  par tous les lecteurs (Acrobat, Edge, Preview, PDF-XChange…).
- **Sauvegarde transparente** des réglages utilisateur entre les versions.
- **Accessibilité** : tailles de police dynamiques, contrastes, raccourcis
  clavier partout.

## 5. Références utiles (lecture seule)

- Documentation Flet (le framework UI utilisé, version 0.28.3) :
  https://flet.dev/docs
- Material Design 3 (thèmes, couleurs, composants) : https://m3.material.io
- Apple Human Interface Guidelines : https://developer.apple.com/design/human-interface-guidelines
- Microsoft Fluent 2 (rubans, barres de commandes) : https://fluent2.microsoft.design
- Spécification PDF ISO 32000 (annotations natives) : https://www.iso.org/standard/51502.html

Pour aller plus loin dans Flet : la doc des contrôles
(https://flet.dev/docs/controls) liste tous les contrôles disponibles
(boutons, tableaux, onglets, onglets latéraux, barres de navigation,
diaporamas, etc.) — chacun s'ajoute dans `ui/` en suivant le même schéma
que `document_view.py` / `ribbon.py`.
