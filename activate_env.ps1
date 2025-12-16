# ============================================
# Document Analyzer - Ativacao do Ambiente
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
# Le modo de operacao do config.yaml
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
# Configura variaveis de ambiente baseado no modo
# ============================================
$modelsPath = "$SCRIPT_DIR\models"

# Sempre configura o caminho dos modelos
$env:HF_HOME = $modelsPath
$env:HF_HUB_CACHE = $modelsPath
$env:TRANSFORMERS_CACHE = $modelsPath
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

# Configura encoding UTF-8 para evitar problemas com caracteres especiais
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($defaultMode -eq "offline") {
    # Modo OFFLINE: bloqueia todas as conexoes
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
    Remove-Item Env:TRANSFORMERS_OFFLINE -ErrorAction SilentlyContinue
    Remove-Item Env:HF_HUB_OFFLINE -ErrorAction SilentlyContinue
    Remove-Item Env:HF_DATASETS_OFFLINE -ErrorAction SilentlyContinue
    $modeColor = "Cyan"
    $modeText = "HYBRID (online com fallback)"
}

# ============================================
# Verifica status do TinyLlama
# ============================================
$tinyLlamaPath = "$SCRIPT_DIR\models\generator\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
$tinyLlamaExists = Test-Path $tinyLlamaPath

# Verifica llama-cpp-python
$llamaCppInstalled = $false
try {
    $null = python -c "import llama_cpp" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $llamaCppInstalled = $true
    }
} catch {}

# ============================================
# Exibe banner
# ============================================
Write-Host ""
Write-Host "+============================================================+" -ForegroundColor Green
Write-Host "|   DOCUMENT ANALYZER - Ambiente Ativado                     |" -ForegroundColor Green
Write-Host "+============================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "Modo de operacao: " -NoNewline
Write-Host $modeText -ForegroundColor $modeColor
Write-Host ""

# Status dos modelos
Write-Host "Status dos Modelos:" -ForegroundColor Magenta
if ($tinyLlamaExists -and $llamaCppInstalled) {
    Write-Host "  [OK] TinyLlama-1.1B (GGUF) - Ativo" -ForegroundColor Green
} elseif ($tinyLlamaExists) {
    Write-Host "  [!] TinyLlama-1.1B - Modelo OK, llama-cpp-python pendente" -ForegroundColor Yellow
    Write-Host "      PowerShell: .\scripts\install_llama_cpp.ps1" -ForegroundColor DarkYellow
    Write-Host "      CMD:        scripts\install_llama_cpp.cmd" -ForegroundColor DarkYellow
} else {
    Write-Host "  [X] TinyLlama-1.1B - Nao encontrado" -ForegroundColor Red
}
Write-Host "  [OK] GPT-2 Portuguese (fallback) - Sempre disponivel" -ForegroundColor Green
Write-Host ""

Write-Host "Perfis de Analise:" -ForegroundColor Magenta
Write-Host "  inventory        - Escritura de Inventario (herdeiros, bens BTG)" -ForegroundColor White
Write-Host "  meeting_minutes  - Ata de Reuniao de Quotistas (ativos, quantidades)" -ForegroundColor White
Write-Host ""

Write-Host "Comandos Principais:" -ForegroundColor Cyan
Write-Host "  python run.py analyze <arquivo.pdf>         - Analise de documento" -ForegroundColor White
Write-Host "  python run.py qa <arquivo.pdf> -i           - Q&A interativo" -ForegroundColor White
Write-Host "  python run.py qa <arquivo.pdf> -q ""...""     - Pergunta unica" -ForegroundColor White
Write-Host "  python run.py extract <arquivo.pdf>         - Apenas extrai texto" -ForegroundColor White
Write-Host ""

Write-Host "Gerenciamento:" -ForegroundColor Cyan
Write-Host "  python run.py models --check                - Verificar modelos instalados" -ForegroundColor White
Write-Host "  python run.py ocr-cache --stats             - Estatisticas do cache OCR" -ForegroundColor White
Write-Host "  python run.py qa-cache --stats              - Estatisticas do cache Q&A" -ForegroundColor White
Write-Host "  python run.py qa --list-templates           - Listar templates Q&A" -ForegroundColor White
Write-Host "  python run.py profiles                      - Listar perfis de analise" -ForegroundColor White
Write-Host "  python run.py info                          - Ver configuracoes" -ForegroundColor White
Write-Host ""

Write-Host "Opcoes do Q&A:" -ForegroundColor Cyan
Write-Host "  --template <nome>     - Usar template especifico" -ForegroundColor White
Write-Host "  --model <nome>        - Usar modelo especifico (tinyllama, gpt2-portuguese)" -ForegroundColor White
Write-Host "  --save-txt <arquivo>  - Salvar resposta em arquivo TXT" -ForegroundColor White
Write-Host ""

Write-Host "Flags de Modo:" -ForegroundColor Magenta
Write-Host "  python run.py --offline analyze doc.pdf     - Forca modo offline" -ForegroundColor White
Write-Host "  python run.py --online analyze doc.pdf      - Forca modo online" -ForegroundColor White
Write-Host ""

Write-Host "Exemplos:" -ForegroundColor Yellow
Write-Host "  python run.py analyze escritura.pdf -o ./resultado" -ForegroundColor White
Write-Host "  python run.py qa contrato.pdf -q ""Qual o valor total?"" --save-txt resp.txt" -ForegroundColor White
Write-Host "  python run.py qa documento.pdf -i --template licencas_software" -ForegroundColor White
Write-Host ""
