@echo off
setlocal ENABLEDELAYEDEXPANSION
REM ============================================
REM Download de Modelos GGUF para Document Analyzer
REM ============================================
REM
REM Uso:
REM   scripts\download_models.cmd           # Baixa todos
REM   scripts\download_models.cmd llama3    # Apenas Llama 3.1 (RECOMENDADO)
REM   scripts\download_models.cmd tinyllama # Apenas TinyLlama
REM   scripts\download_models.cmd mistral   # Apenas Mistral
REM   scripts\download_models.cmd phi3      # Apenas Phi-3 (nao recomendado)
REM

REM Define diretorio do projeto
set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

REM Parametro do modelo
set "MODEL=%~1"
if "%MODEL%"=="" set "MODEL=all"

REM Diretorio dos modelos
set "MODELS_DIR=models\generator"
if not exist "%MODELS_DIR%" mkdir "%MODELS_DIR%"

echo.
echo ====================================
echo   Download de Modelos GGUF
echo ====================================
echo.

REM URLs dos modelos
set "LLAMA3_URL=https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
set "LLAMA3_FILE=Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

set "TINYLLAMA_URL=https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
set "TINYLLAMA_FILE=tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

set "MISTRAL_URL=https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
set "MISTRAL_FILE=mistral-7b-instruct-v0.2.Q4_K_M.gguf"

set "PHI3_URL=https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
set "PHI3_FILE=Phi-3-mini-4k-instruct-q4.gguf"

REM Llama 3.1 8B (RECOMENDADO)
if "%MODEL%"=="all" goto :download_llama3
if "%MODEL%"=="llama3" goto :download_llama3
goto :skip_llama3

:download_llama3
if exist "%MODELS_DIR%\%LLAMA3_FILE%" (
    echo [OK] Llama 3.1 8B ja esta presente
) else (
    echo [^>^>] Baixando Llama 3.1 8B (~4.7 GB^) - MELHOR para Portugues...
    echo     Isso pode levar varios minutos...
    echo.
    curl -L -o "%MODELS_DIR%\%LLAMA3_FILE%" "%LLAMA3_URL%"
    if errorlevel 1 (
        echo [ERRO] Falha ao baixar Llama 3.1 8B
        del "%MODELS_DIR%\%LLAMA3_FILE%" 2>nul
    ) else (
        echo [OK] Llama 3.1 8B baixado com sucesso!
    )
)
:skip_llama3

REM TinyLlama (recursos limitados)
if "%MODEL%"=="all" goto :download_tinyllama
if "%MODEL%"=="tinyllama" goto :download_tinyllama
goto :skip_tinyllama

:download_tinyllama
if exist "%MODELS_DIR%\%TINYLLAMA_FILE%" (
    echo [OK] TinyLlama 1.1B ja esta presente
) else (
    echo [^>^>] Baixando TinyLlama 1.1B (~670 MB^)...
    curl -L -o "%MODELS_DIR%\%TINYLLAMA_FILE%" "%TINYLLAMA_URL%"
    if errorlevel 1 (
        echo [ERRO] Falha ao baixar TinyLlama
        del "%MODELS_DIR%\%TINYLLAMA_FILE%" 2>nul
    ) else (
        echo [OK] TinyLlama 1.1B baixado com sucesso!
    )
)
:skip_tinyllama

REM Mistral 7B
if "%MODEL%"=="all" goto :download_mistral
if "%MODEL%"=="mistral" goto :download_mistral
goto :skip_mistral

:download_mistral
if exist "%MODELS_DIR%\%MISTRAL_FILE%" (
    echo [OK] Mistral 7B ja esta presente
) else (
    echo [^>^>] Baixando Mistral 7B (~4.1 GB^)...
    echo     Isso pode levar varios minutos...
    curl -L -o "%MODELS_DIR%\%MISTRAL_FILE%" "%MISTRAL_URL%"
    if errorlevel 1 (
        echo [ERRO] Falha ao baixar Mistral 7B
        del "%MODELS_DIR%\%MISTRAL_FILE%" 2>nul
    ) else (
        echo [OK] Mistral 7B baixado com sucesso!
    )
)
:skip_mistral

REM Phi-3 Mini (nao recomendado para portugues)
if "%MODEL%"=="all" goto :download_phi3
if "%MODEL%"=="phi3" goto :download_phi3
goto :skip_phi3

:download_phi3
if exist "%MODELS_DIR%\%PHI3_FILE%" (
    echo [OK] Phi-3 Mini ja esta presente
) else (
    echo [^>^>] Baixando Phi-3 Mini (~2.3 GB^)...
    echo     AVISO: Nao recomendado para portugues
    curl -L -o "%MODELS_DIR%\%PHI3_FILE%" "%PHI3_URL%"
    if errorlevel 1 (
        echo [ERRO] Falha ao baixar Phi-3 Mini
        del "%MODELS_DIR%\%PHI3_FILE%" 2>nul
    ) else (
        echo [OK] Phi-3 Mini baixado com sucesso!
    )
)
:skip_phi3

echo.
echo ====================================
echo   Download Concluido
echo ====================================
echo.
echo Verifique os modelos instalados com:
echo   python run.py models --check
echo.
echo Para usar um modelo especifico:
echo   python run.py qa doc.pdf -q "pergunta" --model llama3-8b   # MELHOR para PT-BR
echo   python run.py qa doc.pdf -q "pergunta" --model mistral-7b  # Alternativa
echo   python run.py qa doc.pdf -q "pergunta" --model tinyllama   # Recursos limitados
echo.
echo NOTA: O Llama 3.1 8B e recomendado para melhor qualidade em portugues.
echo.

endlocal

