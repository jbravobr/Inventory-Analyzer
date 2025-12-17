# ============================================
# Download do Llama 3.1 8B do GitHub Releases
# ============================================
#
# Este script baixa o modelo Llama 3.1 8B diretamente do GitHub Releases
# do repositorio jbravobr/Inventory-Analyzer, ideal para ambientes
# corporativos onde o proxy confia apenas no GitHub.
#
# Uso:
#   .\scripts\download_llama3_github.ps1
#
# O modelo sera baixado em partes e automaticamente juntado.
#

param(
    [string]$OutputDir = "models\generator",
    [switch]$KeepParts,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Configuracoes do repositorio
$Owner = "jbravobr"
$Repo = "Inventory-Analyzer"
$Tag = "models-v1"
$ModelName = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
$ExpectedHash = "7B064F5842BF9532C91456DEDA288A1B672397A54FA729AA665952863033557C"

# Partes do modelo
$Parts = @(
    "$ModelName.001",
    "$ModelName.002",
    "$ModelName.003",
    "$ModelName.004"
)

# URL base dos assets
$BaseUrl = "https://github.com/$Owner/$Repo/releases/download/$Tag"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Download do Llama 3.1 8B (GitHub)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Repositorio: $Owner/$Repo"
Write-Host "Release: $Tag"
Write-Host "Tamanho total: ~4.6 GB"
Write-Host ""

# Verificar se ja existe
$outputFile = Join-Path $OutputDir $ModelName
if ((Test-Path $outputFile) -and -not $Force) {
    Write-Host "[OK] Modelo ja existe: $outputFile" -ForegroundColor Green
    Write-Host "     Use -Force para baixar novamente."
    exit 0
}

# Criar diretorio de saida
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Diretorio temporario para as partes
$tempDir = Join-Path $env:TEMP "llama3_download"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

Write-Host "Baixando partes do modelo..." -ForegroundColor Yellow
Write-Host ""

$totalParts = $Parts.Count
$currentPart = 0

foreach ($part in $Parts) {
    $currentPart++
    $url = "$BaseUrl/$part"
    $partFile = Join-Path $tempDir $part
    
    if (Test-Path $partFile) {
        Write-Host "[$currentPart/$totalParts] $part - ja existe, pulando" -ForegroundColor Gray
        continue
    }
    
    Write-Host "[$currentPart/$totalParts] Baixando $part..." -ForegroundColor White
    
    try {
        # Usar Invoke-WebRequest com progress
        $ProgressPreference = 'SilentlyContinue'  # Acelera o download
        Invoke-WebRequest -Uri $url -OutFile $partFile -UseBasicParsing
        
        $size = (Get-Item $partFile).Length
        $sizeMB = [math]::Round($size / 1MB, 0)
        Write-Host "    OK - $sizeMB MB" -ForegroundColor Green
    }
    catch {
        Write-Host "    ERRO: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Possiveis causas:" -ForegroundColor Yellow
        Write-Host "  1. Release '$Tag' ainda nao existe no repositorio"
        Write-Host "  2. Assets ainda nao foram uploaded"
        Write-Host "  3. Problema de conexao/proxy"
        Write-Host ""
        Write-Host "Verifique: https://github.com/$Owner/$Repo/releases/tag/$Tag"
        exit 1
    }
}

Write-Host ""
Write-Host "Juntando partes..." -ForegroundColor Yellow

# Juntar as partes
try {
    $outputStream = [System.IO.File]::Create($outputFile)
    
    foreach ($part in $Parts) {
        $partFile = Join-Path $tempDir $part
        Write-Host "  Adicionando $part..." -NoNewline
        
        $partStream = [System.IO.File]::OpenRead($partFile)
        $partStream.CopyTo($outputStream)
        $partStream.Close()
        
        Write-Host " OK" -ForegroundColor Green
    }
    
    $outputStream.Close()
}
catch {
    Write-Host " ERRO: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Verificando integridade (SHA256)..." -ForegroundColor Yellow

$hash = Get-FileHash $outputFile -Algorithm SHA256
if ($hash.Hash -eq $ExpectedHash) {
    Write-Host "  Checksum OK!" -ForegroundColor Green
} else {
    Write-Host "  AVISO: Checksum diferente do esperado!" -ForegroundColor Yellow
    Write-Host "    Esperado: $ExpectedHash"
    Write-Host "    Obtido:   $($hash.Hash)"
    Write-Host "  O arquivo pode estar corrompido. Tente novamente com -Force"
}

# Limpar partes temporarias
if (-not $KeepParts) {
    Write-Host ""
    Write-Host "Limpando arquivos temporarios..." -ForegroundColor Gray
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

$finalSize = (Get-Item $outputFile).Length
$finalSizeGB = [math]::Round($finalSize / 1GB, 2)

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Download Concluido!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Modelo salvo em: $outputFile"
Write-Host "Tamanho: $finalSizeGB GB"
Write-Host ""
Write-Host "Para usar:" -ForegroundColor Cyan
Write-Host "  python run.py qa documento.pdf -q 'sua pergunta' --model llama3-8b"
Write-Host ""

