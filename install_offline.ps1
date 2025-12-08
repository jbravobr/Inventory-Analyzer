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
Write-Host "[5/5] Configurando ambiente..." -ForegroundColor Yellow

# Cria diretórios necessários
New-Item -ItemType Directory -Path "output" -Force | Out-Null
New-Item -ItemType Directory -Path "cache" -Force | Out-Null

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
Write-Host "  2. Execute: python run.py analyze <arquivo.pdf>" -ForegroundColor White
Write-Host "  3. Ou com perfil: python run.py analyze <arquivo.pdf> -p meeting_minutes" -ForegroundColor White
Write-Host ""

