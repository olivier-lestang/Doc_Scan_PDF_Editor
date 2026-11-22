# Lance l'application en mode developpement (le plus rapide pour les essais).
# Usage :  powershell -ExecutionPolicy Bypass -File .\run-dev.ps1
# Les versions flet sont figees exactement (Python + client desktop/web doivent
# correspondre, sinon le client Flutter leve "Unknown control: ...").
uv sync
uv pip install "flet==0.28.3" "flet-cli==0.28.3" "flet-desktop==0.28.3" "flet-web==0.28.3"
uv run flet run src/docscanner/app/main.py
