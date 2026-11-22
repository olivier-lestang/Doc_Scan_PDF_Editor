# Coding Standards

## Language of the code

All code, identifiers, docstrings and comments are written in **English**.

Chaque docstring et chaque commentaire est suivi de sa **traduction
française sur la ligne suivante** (the French translation of every
docstring/comment goes on the next line), so that both audiences can read
the code in an editor.

## Line length

Lines are wrapped at **88 columns** (ruff `line-length = 88`). Long
comments/docstrings must be wrapped; never leave over-long lines, they do
not display well in editors.

## Typing

- Full type hints everywhere; `mypy --strict` must pass.
- Prefer `dataclass(frozen=True)` for value objects, `Protocol` for ports.
- Use `X | None` instead of `Optional[X]`, builtin generics (`tuple`,
  `dict`, `list`), `Literal`/`StrEnum` for closed sets.

## Docstrings and comments

- Google-style docstrings on all modules, classes and public functions
  (enforced by ruff `D` rules).
- Format: English summary/description first, blank line, then the French
  translation on the following line(s), wrapped at 88 columns.

Example:

```python
def detect_document_edges(image: ImageBuffer) -> Result[Quad, str]:
    """Detect the four corners of a document in a photo.

    Détecte les quatre coins d'un document sur une photo.
    """
    ...
```

## Naming

- Functions/methods: verb-noun, explicit, e.g. `detect_document_edges`,
  `apply_perspective_correction`, `enhance_contrast_and_brightness`.
- Booleans start with `is_` / `has_` / `can_`.
- No abbreviations except an allow-list: `id`, `pdf`, `ocr`, `ui`, `url`,
  `dpi`, `rgb`, `json`, `app`.

## Structure

- Clean architecture: `domain` (pure, no I/O) / `data` (implementations) /
  `features` (UI + wiring) / `core` (shared primitives).
- Dependencies point inward: `data` and `features` depend on `domain`,
  never the reverse.
- One logical change per commit; Conventional Commits messages.

## Tests

- `pytest`; every new behavior gets a test.
- Tests must not require heavy native libs (OpenCV, PDFium) at import
  time; heavy imports stay lazy inside `data` implementations.

## Tooling

```bash
uv run ruff format       # format (88 cols)
uv run ruff check        # lint incl. docstrings and annotations
uv run mypy              # strict type check
uv run pytest            # tests
```

All four run in CI on every push and pull request.
