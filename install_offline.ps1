# ============================================
# Document Analyzer - Instalação Offline
# ============================================
# Este script instala todas as dependências sem conexão com internet
# Requisitos: Python 3.14 já instalado no sistema
# ============================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   DOCUMENT ANALYZER - Instalação OFFLINE                  ║" -ForegroundColor Cyan
Write-Host "║   Analisador de Documentos com Multiplos Perfis           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Detectar diretório do script
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

Write-Host "[1/5] Verificando Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Python não encontrado." -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ $pythonVersion encontrado" -ForegroundColor Green

Write-Host ""
Write-Host "[2/5] Criando ambiente virtual..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  → Removendo ambiente virtual existente..."
    Remove-Item -Recurse -Force "venv"
}
python -m venv venv
Write-Host "  ✓ Ambiente virtual criado" -ForegroundColor Green

Write-Host ""
Write-Host "[3/5] Ativando ambiente virtual..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "  ✓ Ambiente ativado" -ForegroundColor Green

Write-Host ""
Write-Host "[4/5] Instalando pacotes offline..." -ForegroundColor Yellow

$wheelFiles = Get-ChildItem "wheels\*.whl"
$total = $wheelFiles.Count
$current = 0

foreach ($wheel in $wheelFiles) {
    $current++
    $percent = [math]::Round(($current / $total) * 100)
    Write-Progress -Activity "Instalando pacotes" -Status "$current de $total - $($wheel.Name)" -PercentComplete $percent
    pip install $wheel.FullName --no-index --no-deps --quiet 2>$null
}
Write-Progress -Activity "Instalando pacotes" -Completed

$installed = pip list --format=freeze | Measure-Object -Line
Write-Host "  ✓ $($installed.Lines) pacotes instalados" -ForegroundColor Green

Write-Host ""
Write-Host "[5/6] Instalando llama-cpp-python..." -ForegroundColor Yellow

# Verifica se llama_cpp já está instalado
$llamaInstalled = $false
try {
    $null = python -c "import llama_cpp" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $llamaInstalled = $true
    }
} catch {}

if (-not $llamaInstalled) {
    $wheelFile = Get-ChildItem "wheels\llama_cpp_python*.whl" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($wheelFile) {
        Write-Host "  → Instalando $($wheelFile.Name)..."
        pip install $wheelFile.FullName --no-index --no-deps --quiet 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ llama-cpp-python instalado! TinyLlama e Llama 3.1 disponíveis." -ForegroundColor Green
            $llamaInstalled = $true
        } else {
            Write-Host "  ⚠ Erro ao instalar llama-cpp-python" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠ Wheel llama-cpp-python não encontrado na pasta wheels\" -ForegroundColor Yellow
        Write-Host "    Modelos GGUF não estarão disponíveis." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  ✓ llama-cpp-python já instalado - TinyLlama e Llama 3.1 disponíveis" -ForegroundColor Green
}

Write-Host ""
Write-Host "[6/6] Configurando ambiente..." -ForegroundColor Yellow

# Cria diretórios necessários
New-Item -ItemType Directory -Path "output" -Force | Out-Null
New-Item -ItemType Directory -Path "cache" -Force | Out-Null
New-Item -ItemType Directory -Path "cache\qa_responses" -Force | Out-Null
New-Item -ItemType Directory -Path "cache\dkr" -Force | Out-Null
New-Item -ItemType Directory -Path "domain_rules" -Force | Out-Null

Write-Host "  ✓ Diretórios criados" -ForegroundColor Green

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              INSTALAÇÃO CONCLUÍDA COM SUCESSO!            ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Perfis disponiveis:" -ForegroundColor Magenta
Write-Host "  inventory        - Escritura de Inventario (herdeiros, bens BTG)" -ForegroundColor White
Write-Host "  meeting_minutes  - Ata de Reuniao de Quotistas (ativos, quantidades)" -ForegroundColor White
Write-Host ""
Write-Host "Para usar:" -ForegroundColor Cyan
Write-Host "  1. Execute: .\activate_env.ps1" -ForegroundColor White
Write-Host "  2. Analise: python run.py analyze <arquivo.pdf>" -ForegroundColor White
Write-Host "  3. Q&A:     python run.py qa <arquivo.pdf> -q `"sua pergunta`"" -ForegroundColor White
Write-Host ""
Write-Host "Comandos adicionais:" -ForegroundColor Cyan
Write-Host "  python run.py qa --list-templates      # Templates Q&A disponiveis" -ForegroundColor White
Write-Host "  python run.py dkr list                 # Regras de dominio disponiveis" -ForegroundColor White
Write-Host "  python run.py models                   # Modelos de linguagem disponiveis" -ForegroundColor White
Write-Host ""

