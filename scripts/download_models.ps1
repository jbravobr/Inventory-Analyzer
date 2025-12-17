# Download de modelos adicionais para o Document Analyzer
# Execute: .\scripts\download_models.ps1
# 
# Uso:
#   .\scripts\download_models.ps1                # Baixa todos
#   .\scripts\download_models.ps1 -Model llama3  # Apenas Llama 3.1 (RECOMENDADO)
#   .\scripts\download_models.ps1 -Model mistral # Apenas Mistral
#   .\scripts\download_models.ps1 -Model tinyllama # Apenas TinyLlama

param(
    [ValidateSet("all", "llama3", "phi3", "mistral", "tinyllama")]
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

# Llama 3.1 8B (RECOMENDADO para portugues)
if ($Model -eq "all" -or $Model -eq "llama3") {
    $llama3File = "$modelsDir\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
    if (Test-Path $llama3File) {
        Write-Host "[OK] Llama 3.1 8B ja esta presente" -ForegroundColor Green
    } else {
        Write-Host "[>>] Baixando Llama 3.1 8B (~4.7 GB) - MELHOR para Portugues..." -ForegroundColor Yellow
        Write-Host "     Isso pode levar varios minutos..." -ForegroundColor Gray
        $llama3Url = "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
        try {
            Invoke-WebRequest -Uri $llama3Url -OutFile $llama3File -UseBasicParsing
            Write-Host "[OK] Llama 3.1 8B baixado com sucesso!" -ForegroundColor Green
        } catch {
            Write-Host "[ERRO] Falha ao baixar Llama 3.1 8B: $_" -ForegroundColor Red
        }
    }
}

# TinyLlama (para recursos limitados)
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

# Phi-3 Mini (NAO recomendado para portugues)
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
Write-Host "  python run.py qa doc.pdf -q 'pergunta' --model llama3-8b   # MELHOR para PT-BR" -ForegroundColor Green
Write-Host "  python run.py qa doc.pdf -q 'pergunta' --model mistral-7b  # Alternativa" -ForegroundColor White
Write-Host "  python run.py qa doc.pdf -q 'pergunta' --model tinyllama   # Recursos limitados" -ForegroundColor White
Write-Host ""
Write-Host "NOTA: O Llama 3.1 8B e recomendado para melhor qualidade em portugues." -ForegroundColor Cyan
Write-Host ""

