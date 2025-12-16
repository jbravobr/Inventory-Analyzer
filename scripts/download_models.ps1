# Download de modelos adicionais para o Document Analyzer
# Execute: .\scripts\download_models.ps1
# 
# Uso:
#   .\scripts\download_models.ps1              # Baixa todos
#   .\scripts\download_models.ps1 -Model phi3   # Apenas Phi-3
#   .\scripts\download_models.ps1 -Model mistral # Apenas Mistral

param(
    [ValidateSet("all", "phi3", "mistral", "tinyllama")]
    [string]$Model = "all"
)

# Configura encoding UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Diretorio dos modelos
$modelsDir = "models\generator"

# Verifica se diretorio existe
if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  Download de Modelos GGUF" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# TinyLlama (padrao, ja incluso no repo)
if ($Model -eq "all" -or $Model -eq "tinyllama") {
    $tinyllamaFile = "$modelsDir\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    if (Test-Path $tinyllamaFile) {
        Write-Host "[OK] TinyLlama 1.1B ja esta presente" -ForegroundColor Green
    } else {
        Write-Host "[>>] Baixando TinyLlama 1.1B (~670 MB)..." -ForegroundColor Yellow
        $tinyllamaUrl = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
        try {
            Invoke-WebRequest -Uri $tinyllamaUrl -OutFile $tinyllamaFile -UseBasicParsing
            Write-Host "[OK] TinyLlama 1.1B baixado com sucesso!" -ForegroundColor Green
        } catch {
            Write-Host "[ERRO] Falha ao baixar TinyLlama: $_" -ForegroundColor Red
        }
    }
}

# Phi-3 Mini
if ($Model -eq "all" -or $Model -eq "phi3") {
    $phi3File = "$modelsDir\Phi-3-mini-4k-instruct-q4.gguf"
    if (Test-Path $phi3File) {
        Write-Host "[OK] Phi-3 Mini ja esta presente" -ForegroundColor Green
    } else {
        Write-Host "[>>] Baixando Phi-3 Mini (~2.3 GB)..." -ForegroundColor Yellow
        Write-Host "     Isso pode levar alguns minutos..." -ForegroundColor Gray
        $phi3Url = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
        try {
            Invoke-WebRequest -Uri $phi3Url -OutFile $phi3File -UseBasicParsing
            Write-Host "[OK] Phi-3 Mini baixado com sucesso!" -ForegroundColor Green
        } catch {
            Write-Host "[ERRO] Falha ao baixar Phi-3 Mini: $_" -ForegroundColor Red
        }
    }
}

# Mistral 7B
if ($Model -eq "all" -or $Model -eq "mistral") {
    $mistralFile = "$modelsDir\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    if (Test-Path $mistralFile) {
        Write-Host "[OK] Mistral 7B ja esta presente" -ForegroundColor Green
    } else {
        Write-Host "[>>] Baixando Mistral 7B (~4.1 GB)..." -ForegroundColor Yellow
        Write-Host "     Isso pode levar varios minutos..." -ForegroundColor Gray
        $mistralUrl = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        try {
            Invoke-WebRequest -Uri $mistralUrl -OutFile $mistralFile -UseBasicParsing
            Write-Host "[OK] Mistral 7B baixado com sucesso!" -ForegroundColor Green
        } catch {
            Write-Host "[ERRO] Falha ao baixar Mistral 7B: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  Download Concluido" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verifique os modelos instalados com:" -ForegroundColor Yellow
Write-Host "  python run.py models --check" -ForegroundColor White
Write-Host ""
Write-Host "Para usar um modelo especifico:" -ForegroundColor Yellow
Write-Host "  python run.py qa doc.pdf -q 'pergunta' --model tinyllama" -ForegroundColor White
Write-Host "  python run.py qa doc.pdf -q 'pergunta' --model phi3-mini" -ForegroundColor White
Write-Host "  python run.py qa doc.pdf -q 'pergunta' --model mistral-7b" -ForegroundColor White
Write-Host ""

