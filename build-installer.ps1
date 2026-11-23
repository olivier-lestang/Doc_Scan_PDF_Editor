# Construit l'executable autonome dans dist\ (Windows).
# Pour un nouvel essai : relancer ce script puis ecraser l'ancien .exe par le
# nouveau (les reglages utilisateur dans %APPDATA% sont conserves).
# Usage :  powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
# Versions figees via uv.lock (uv sync --frozen --group desktop).
uv sync --frozen --group desktop
uv run flet pack src/lestang_pdf_editor/app/main.py `
  --name LestangPdfEditor `
  --product_name "Lestang PDF Editor" `
  --company_name "Olivier Lestang" `
  --file_description "Offline PDF editor and document scanner"
Write-Host "Executable genere dans dist\"
