# Construit l'executable autonome dans dist\ (Windows).
# Pour un nouvel essai : relancer ce script puis ecraser l'ancien .exe par le
# nouveau (les reglages utilisateur dans %APPDATA% sont conserves).
# Usage :  powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
uv sync
uv pip install "flet==0.28.3" "flet-cli==0.28.3" "flet-desktop==0.28.3" "flet-web==0.28.3"
uv run flet pack src/docscanner/app/main.py `
  --name DocScanPDFEditor `
  --product_name "Doc Scan PDF Editor" `
  --company_name "Olivier Lestang" `
  --file_description "Offline document scanner and PDF editor"
Write-Host "Executable genere dans dist\"
