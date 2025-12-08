# ============================================
# Document Analyzer - Ativação do Ambiente
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
Write-Host "║   DOCUMENT ANALYZER - Ambiente OFFLINE Ativado            ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Perfis disponiveis:" -ForegroundColor Magenta
Write-Host "  inventory        - Escritura de Inventario (herdeiros, bens BTG)" -ForegroundColor White
Write-Host "  meeting_minutes  - Ata de Reuniao de Quotistas (ativos, quantidades)" -ForegroundColor White
Write-Host ""
Write-Host "Comandos:" -ForegroundColor Cyan
Write-Host "  python run.py analyze <arquivo.pdf>                    - Analise (perfil padrao)" -ForegroundColor White
Write-Host "  python run.py analyze <arquivo.pdf> -p inventory       - Analise de Inventario" -ForegroundColor White
Write-Host "  python run.py analyze <arquivo.pdf> -p meeting_minutes - Analise de Ata de Reuniao" -ForegroundColor White
Write-Host "  python run.py profiles                                 - Listar perfis" -ForegroundColor White
Write-Host "  python run.py extract <arquivo.pdf>                    - Apenas extrai texto" -ForegroundColor White
Write-Host "  python run.py info                                     - Ver configuracoes" -ForegroundColor White
Write-Host ""
Write-Host "Exemplos:" -ForegroundColor Yellow
Write-Host "  python run.py analyze escritura.pdf -o ./resultado" -ForegroundColor White
Write-Host "  python run.py analyze ata_quotistas.pdf -p meeting_minutes" -ForegroundColor White
Write-Host ""

