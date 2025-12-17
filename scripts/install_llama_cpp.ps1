# ============================================
# Script de Instalacao do llama-cpp-python
# ============================================
# 
# Este script instala o llama-cpp-python que e necessario
# para usar modelos GGUF como Llama 3.1, Mistral e TinyLlama.
#
# METODO: Instalacao via wheel pre-compilado (sem necessidade de compilador)
#
# Uso:
#   .\scripts\install_llama_cpp.ps1
#

Write-Host ""
Write-Host "=============================================="
Write-Host "  Instalacao do llama-cpp-python"
Write-Host "=============================================="
Write-Host ""

# Define diretorio do projeto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
Set-Location $projectDir

# Verifica se o ambiente virtual existe
$venvPath = $null
if (Test-Path ".\venv\Scripts\python.exe") {
    $venvPath = ".\venv"
} elseif (Test-Path ".\.venv\Scripts\python.exe") {
    $venvPath = ".\.venv"
} else {
    Write-Host "[ERRO] Ambiente virtual nao encontrado!" -ForegroundColor Red
    Write-Host "Execute primeiro o instalador do projeto."
    exit 1
}

$pipExe = "$venvPath\Scripts\python.exe"

Write-Host "Verificando se llama-cpp-python ja esta instalado..." -ForegroundColor Cyan

# Verifica se ja esta instalado
$llamaInstalled = $false
try {
    $null = & $pipExe -c "import llama_cpp" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $llamaInstalled = $true
    }
} catch {}

if ($llamaInstalled) {
    Write-Host ""
    Write-Host "[OK] llama-cpp-python ja esta instalado!" -ForegroundColor Green
    & $pipExe -c "import llama_cpp; print('  Versao:', llama_cpp.__version__)"
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "Procurando wheel pre-compilado..." -ForegroundColor Cyan

# Procura wheel na pasta wheels/
$wheelFile = Get-ChildItem "wheels\llama_cpp_python*.whl" -ErrorAction SilentlyContinue | Select-Object -First 1

if ($wheelFile) {
    Write-Host "  Encontrado: $($wheelFile.Name)" -ForegroundColor White
    Write-Host ""
    Write-Host "Instalando llama-cpp-python via wheel..." -ForegroundColor Yellow
    
    & $pipExe -m pip install $wheelFile.FullName --no-index --no-deps
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] llama-cpp-python instalado com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Falha ao instalar via wheel" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[AVISO] Wheel pre-compilado nao encontrado em wheels\" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Tentando instalar via pip (requer internet)..." -ForegroundColor Cyan
    
    & $pipExe -m pip install llama-cpp-python
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERRO] Falha na instalacao via pip!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Solucoes:" -ForegroundColor Yellow
        Write-Host "  1. Baixe o wheel pre-compilado de:"
        Write-Host "     https://github.com/abetlen/llama-cpp-python/releases"
        Write-Host "  2. Coloque o arquivo .whl na pasta wheels\"
        Write-Host "  3. Execute este script novamente"
        Write-Host ""
        exit 1
    }
}

# Verifica instalacao
Write-Host ""
Write-Host "Verificando instalacao..." -ForegroundColor Cyan
& $pipExe -c "import llama_cpp; print('llama-cpp-python versao:', llama_cpp.__version__)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] Instalacao concluida mas verificacao falhou." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=============================================="
Write-Host "  Instalacao Concluida com Sucesso!"
Write-Host "=============================================="
Write-Host ""
Write-Host "Agora voce pode usar modelos GGUF:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Llama 3.1 8B (RECOMENDADO para portugues):" -ForegroundColor Green
Write-Host "    1. Baixar: .\scripts\download_models.ps1 -Model llama3"
Write-Host "    2. Usar:   python run.py qa documento.pdf -q 'pergunta' --model llama3-8b"
Write-Host ""
Write-Host "  TinyLlama (recursos limitados):" -ForegroundColor Yellow
Write-Host "    python run.py qa documento.pdf -q 'pergunta' --model tinyllama"
Write-Host ""
Write-Host "Verificar status dos modelos:" -ForegroundColor Cyan
Write-Host "  python run.py models --check"
Write-Host ""
