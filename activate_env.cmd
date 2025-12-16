@echo off
REM ============================================
REM Document Analyzer - Ativacao do Ambiente
REM ============================================

REM Define o diretorio do script
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Ativa ambiente virtual
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

REM Configura PATH para Tesseract OCR (se instalado)
if exist "C:\Program Files\Tesseract-OCR" (
    set "PATH=C:\Program Files\Tesseract-OCR;%PATH%"
)

REM ============================================
REM Le modo de operacao do config.yaml
REM ============================================
set "DEFAULT_MODE=offline"
set "CONFIG_FILE=%SCRIPT_DIR%config.yaml"

if exist "%CONFIG_FILE%" (
    for /f "tokens=2 delims=: " %%a in ('findstr /r /c:"^  mode:" "%CONFIG_FILE%" 2^>nul') do (
        set "DEFAULT_MODE=%%~a"
    )
)

REM Remove aspas se houver
set "DEFAULT_MODE=%DEFAULT_MODE:"=%"

REM ============================================
REM Configura variaveis de ambiente baseado no modo
REM ============================================
set "MODELS_PATH=%SCRIPT_DIR%models"

REM Sempre configura o caminho dos modelos
set "HF_HOME=%MODELS_PATH%"
set "HF_HUB_CACHE=%MODELS_PATH%"
set "TRANSFORMERS_CACHE=%MODELS_PATH%"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"

REM Configura encoding UTF-8
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul 2>&1

if /i "%DEFAULT_MODE%"=="offline" (
    REM Modo OFFLINE: bloqueia todas as conexoes
    set "TRANSFORMERS_OFFLINE=1"
    set "HF_HUB_OFFLINE=1"
    set "HF_DATASETS_OFFLINE=1"
    set "MODE_TEXT=OFFLINE (100%% local)"
    set "MODE_COLOR=[93m"
) else if /i "%DEFAULT_MODE%"=="online" (
    REM Modo ONLINE: permite downloads
    set "TRANSFORMERS_OFFLINE=0"
    set "HF_HUB_OFFLINE=0"
    set "HF_DATASETS_OFFLINE=0"
    set "MODE_TEXT=ONLINE (downloads permitidos)"
    set "MODE_COLOR=[92m"
) else (
    REM Modo HYBRID: deixa o programa decidir
    set "TRANSFORMERS_OFFLINE="
    set "HF_HUB_OFFLINE="
    set "HF_DATASETS_OFFLINE="
    set "MODE_TEXT=HYBRID (online com fallback)"
    set "MODE_COLOR=[96m"
)

REM ============================================
REM Verifica status do TinyLlama
REM ============================================
set "TINYLLAMA_STATUS=[X] TinyLlama - Nao encontrado"
set "TINYLLAMA_COLOR=[91m"
if exist "%SCRIPT_DIR%models\generator\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" (
    set "TINYLLAMA_STATUS=[!] TinyLlama - Modelo OK, llama-cpp-python pendente"
    set "TINYLLAMA_COLOR=[93m"
)

REM ============================================
REM Exibe banner
REM ============================================
echo.
echo [92m+============================================================+[0m
echo [92m^|   DOCUMENT ANALYZER - Ambiente Ativado                     ^|[0m
echo [92m+============================================================+[0m
echo.
echo Modo de operacao: %MODE_COLOR%%MODE_TEXT%[0m
echo.

echo [95mStatus dos Modelos:[0m
echo   %TINYLLAMA_COLOR%%TINYLLAMA_STATUS%[0m
echo   [92m[OK] GPT-2 Portuguese (fallback) - Sempre disponivel[0m
echo.

echo [95mPerfis de Analise:[0m
echo   inventory        - Escritura de Inventario (herdeiros, bens BTG)
echo   meeting_minutes  - Ata de Reuniao de Quotistas (ativos, quantidades)
echo.

echo [96mComandos Principais:[0m
echo   python run.py analyze ^<arquivo.pdf^>         - Analise de documento
echo   python run.py qa ^<arquivo.pdf^> -i           - Q^&A interativo
echo   python run.py qa ^<arquivo.pdf^> -q "..."     - Pergunta unica
echo   python run.py extract ^<arquivo.pdf^>         - Apenas extrai texto
echo.

echo [96mGerenciamento:[0m
echo   python run.py models --check                - Verificar modelos instalados
echo   python run.py ocr-cache --stats             - Estatisticas do cache OCR
echo   python run.py qa-cache --stats              - Estatisticas do cache Q^&A
echo   python run.py qa --list-templates           - Listar templates Q^&A
echo   python run.py profiles                      - Listar perfis de analise
echo   python run.py info                          - Ver configuracoes
echo.

echo [96mOpcoes do Q^&A:[0m
echo   --template ^<nome^>     - Usar template especifico
echo   --model ^<nome^>        - Usar modelo especifico (tinyllama, gpt2-portuguese)
echo   --save-txt ^<arquivo^>  - Salvar resposta em arquivo TXT
echo.

echo [95mFlags de Modo:[0m
echo   python run.py --offline analyze doc.pdf     - Forca modo offline
echo   python run.py --online analyze doc.pdf      - Forca modo online
echo.

echo [93mExemplos:[0m
echo   python run.py analyze escritura.pdf -o ./resultado
echo   python run.py qa contrato.pdf -q "Qual o valor total?" --save-txt resp.txt
echo   python run.py qa documento.pdf -i --template licencas_software
echo.

echo [93mPara ativar TinyLlama (melhor qualidade):[0m
echo   scripts\install_llama_cpp.cmd       (Prompt de Comando)
echo   .\scripts\install_llama_cpp.ps1     (PowerShell)
echo   python run.py models --check
echo.
