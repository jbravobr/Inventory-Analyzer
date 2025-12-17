# Script de Instalacao do llama-cpp-python
# ==========================================
# 
# Este script instala o llama-cpp-python que e necessario
# para usar modelos GGUF como Llama 3.1, Mistral e TinyLlama.
#
# IMPORTANTE: Requer compilador C++ instalado (Visual Studio Build Tools)
#
# Uso:
#   .\scripts\install_llama_cpp.ps1
#

Write-Host "=============================================="
Write-Host "  Instalacao do llama-cpp-python"
Write-Host "=============================================="
Write-Host ""

# Verifica se o ambiente virtual esta ativado
if (-not $env:VIRTUAL_ENV) {
    Write-Host "[AVISO] Ambiente virtual nao detectado." -ForegroundColor Yellow
    Write-Host "Ativando ambiente virtual..."
    
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        . .\.venv\Scripts\Activate.ps1
    } elseif (Test-Path ".\venv\Scripts\Activate.ps1") {
        . .\venv\Scripts\Activate.ps1
    } else {
        Write-Host "[ERRO] Ambiente virtual nao encontrado!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Verificando pre-requisitos..." -ForegroundColor Cyan

# Verifica se cmake esta instalado
$cmake = Get-Command cmake -ErrorAction SilentlyContinue
if (-not $cmake) {
    Write-Host "[AVISO] CMake nao encontrado." -ForegroundColor Yellow
    Write-Host "Tentando instalar via pip..."
    pip install cmake
}

Write-Host ""
Write-Host "Instalando llama-cpp-python..." -ForegroundColor Cyan
Write-Host "(Isso pode demorar alguns minutos)"
Write-Host ""

# Tenta instalar
$result = pip install llama-cpp-python 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] llama-cpp-python instalado com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verificando instalacao..."
    python -c "import llama_cpp; print('llama-cpp-python versao:', llama_cpp.__version__)"
    
    Write-Host ""
    Write-Host "Agora voce pode usar modelos GGUF:"
    Write-Host ""
    Write-Host "  Llama 3.1 8B (RECOMENDADO para portugues):" -ForegroundColor Cyan
    Write-Host "    1. Baixar: .\scripts\download_models.ps1 -Model llama3"
    Write-Host "    2. Usar:   python run.py qa documento.pdf -q 'pergunta' --model llama3-8b"
    Write-Host ""
    Write-Host "  TinyLlama (recursos limitados):" -ForegroundColor Yellow
    Write-Host "    python run.py qa documento.pdf -q 'pergunta' --model tinyllama"
} else {
    Write-Host ""
    Write-Host "[ERRO] Falha na instalacao!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possiveis causas:"
    Write-Host "  1. Compilador C++ nao instalado"
    Write-Host "  2. CMake nao encontrado"
    Write-Host ""
    Write-Host "Solucoes:"
    Write-Host "  1. Instale Visual Studio Build Tools:"
    Write-Host "     https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    Write-Host ""
    Write-Host "  2. Ou use GPT-2 Portuguese (funciona sem compilacao):"
    Write-Host "     python run.py qa documento.pdf -q 'pergunta' --model gpt2-portuguese"
    Write-Host ""
    Write-Host "Detalhes do erro:"
    Write-Host $result
}

