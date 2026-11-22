# Contributing

## Workflow

1. Create a branch `vibe/<short-slug>-<id>` or `feat/<name>` from `main`.
2. Use [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
3. Keep commits small and focused; one logical change per commit.
4. Open a pull request (draft while work is in progress) using the PR
   template. Fill in every section of the template.
5. CI must pass: `ruff format --check`, `ruff check`, `mypy`, `pytest`.

## Code standards

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md). In short:
English code and comments, French translation of each docstring/comment on
the next line, 88-column wrap, full type hints, docstrings on all public
API, explicit verb-noun function names, tests for every new behavior.

## License

By contributing, you agree that your contributions are licensed under the
MIT license, like the rest of the project.
