# ============================================
# Document Analyzer - Ativação do Ambiente
# ============================================

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# Ativa ambiente virtual
& "$SCRIPT_DIR\venv\Scripts\Activate.ps1"

# Configura PATH para Tesseract OCR (se instalado)
if (Test-Path "C:\Program Files\Tesseract-OCR") {
    $env:PATH = "C:\Program Files\Tesseract-OCR;$env:PATH"
}

# ============================================
# Lê modo de operação do config.yaml
# ============================================
$configPath = "$SCRIPT_DIR\config.yaml"
$defaultMode = "offline"

if (Test-Path $configPath) {
    $content = Get-Content $configPath -Raw
    if ($content -match '^\s*mode:\s*["\x27]?(\w+)["\x27]?' -and $Matches[1]) {
        $defaultMode = $Matches[1].ToLower()
    }
}

# ============================================
# Configura variáveis de ambiente baseado no modo
# ============================================
$modelsPath = "$SCRIPT_DIR\models"

# Sempre configura o caminho dos modelos
$env:HF_HOME = $modelsPath
$env:HF_HUB_CACHE = $modelsPath
$env:TRANSFORMERS_CACHE = $modelsPath
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

if ($defaultMode -eq "offline") {
    # Modo OFFLINE: bloqueia todas as conexões
    $env:TRANSFORMERS_OFFLINE = "1"
    $env:HF_HUB_OFFLINE = "1"
    $env:HF_DATASETS_OFFLINE = "1"
    $modeColor = "Yellow"
    $modeText = "OFFLINE (100% local)"
}
elseif ($defaultMode -eq "online") {
    # Modo ONLINE: permite downloads
    $env:TRANSFORMERS_OFFLINE = "0"
    $env:HF_HUB_OFFLINE = "0"
    $env:HF_DATASETS_OFFLINE = "0"
    $modeColor = "Green"
    $modeText = "ONLINE (downloads permitidos)"
}
else {
    # Modo HYBRID: deixa o programa decidir
    # Remove variáveis para permitir decisão dinâmica
    Remove-Item Env:TRANSFORMERS_OFFLINE -ErrorAction SilentlyContinue
    Remove-Item Env:HF_HUB_OFFLINE -ErrorAction SilentlyContinue
    Remove-Item Env:HF_DATASETS_OFFLINE -ErrorAction SilentlyContinue
    $modeColor = "Cyan"
    $modeText = "HYBRID (online com fallback)"
}

# ============================================
# Exibe banner
# ============================================
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   DOCUMENT ANALYZER - Ambiente Ativado                    ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Modo de operação: " -NoNewline
Write-Host $modeText -ForegroundColor $modeColor
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
Write-Host "Flags de modo (override temporario):" -ForegroundColor Magenta
Write-Host "  python run.py --offline analyze doc.pdf   - Forca modo offline" -ForegroundColor White
Write-Host "  python run.py --online analyze doc.pdf    - Forca modo online" -ForegroundColor White
Write-Host "  python run.py --hybrid analyze doc.pdf    - Forca modo hibrido" -ForegroundColor White
Write-Host ""
Write-Host "Exemplos:" -ForegroundColor Yellow
Write-Host "  python run.py analyze escritura.pdf -o ./resultado" -ForegroundColor White
Write-Host "  python run.py analyze ata_quotistas.pdf -p meeting_minutes" -ForegroundColor White
Write-Host "  python run.py --online --allow-download analyze doc.pdf" -ForegroundColor White
Write-Host ""
