# Lance l'application en mode developpement (le plus rapide pour les essais).
# Usage :  powershell -ExecutionPolicy Bypass -File .\run-dev.ps1
uv sync
uv run --with "flet[all]==0.28.3" flet run src/docscanner/app/main.py
