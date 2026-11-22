# Lance l'application en mode developpement (le plus rapide pour les essais).
# Usage :  powershell -ExecutionPolicy Bypass -File .\run-dev.ps1
# Toutes les versions sont figees exactement via uv.lock (uv sync --frozen),
# y compris le groupe "desktop" (binaires Flutter) : le Python flet et le
# client desktop/web doivent correspondre, sinon le client leve
# "Unknown control: ...".
uv sync --frozen --group desktop
uv run flet run src/lestang_pdf_editor/app/main.py
