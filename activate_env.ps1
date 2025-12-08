# ============================================
# Inventory Analyzer - Ativação do Ambiente
# ============================================

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# Ativa ambiente virtual
& "$SCRIPT_DIR\venv\Scripts\Activate.ps1"

# Configura PATH
$env:PATH = "$SCRIPT_DIR\bin\poppler\bin;$env:PATH"

if (Test-Path "C:\Program Files\Tesseract-OCR") {
    $env:PATH = "C:\Program Files\Tesseract-OCR;$env:PATH"
}

# Modo OFFLINE do HuggingFace
$env:HF_HOME = "$SCRIPT_DIR\models"
$env:HF_HUB_CACHE = "$SCRIPT_DIR\models"
$env:TRANSFORMERS_CACHE = "$SCRIPT_DIR\models"
$env:HF_DATASETS_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_HUB_OFFLINE = "1"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   INVENTORY ANALYZER - Ambiente OFFLINE Ativado           ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Comandos:" -ForegroundColor Cyan
Write-Host "  python run.py analyze <arquivo.pdf>  - Análise completa" -ForegroundColor White
Write-Host "  python run.py extract <arquivo.pdf>  - Apenas extrai texto" -ForegroundColor White
Write-Host "  python run.py info                   - Ver configurações" -ForegroundColor White
Write-Host ""
Write-Host "Exemplo:" -ForegroundColor Yellow
Write-Host "  python run.py analyze escritura.pdf -o ./resultado" -ForegroundColor White
Write-Host ""

