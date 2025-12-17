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
REM Verifica status dos modelos
REM ============================================
set "LLAMA3_STATUS=[X] Llama-3.1-8B - Nao encontrado (recomendado PT-BR)"
set "LLAMA3_COLOR=[93m"
if exist "%SCRIPT_DIR%models\generator\Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" (
    set "LLAMA3_STATUS=[!] Llama-3.1-8B - Modelo OK, llama-cpp-python pendente"
    set "LLAMA3_COLOR=[93m"
)

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
echo   %LLAMA3_COLOR%%LLAMA3_STATUS%[0m
echo   %TINYLLAMA_COLOR%%TINYLLAMA_STATUS%[0m
echo   [92m[OK] GPT-2 Portuguese (fallback) - Sempre disponivel[0m
echo   [93mDownload Llama 3.1: scripts\download_models.ps1 -Model llama3[0m
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

echo [96mDomain Knowledge Rules (DKR):[0m
echo   python run.py dkr list                      - Listar regras de dominio
echo   python run.py dkr validate                  - Validar arquivos .rules
echo   python run.py dkr test ^<arquivo.rules^>      - Testar regras
echo   python run.py dkr wizard                    - Assistente para criar regras
echo   python run.py dkr repl                      - Console interativo DKR
echo.

echo [96mOpcoes do Q^&A:[0m
echo   --template ^<nome^>     - Usar template especifico
echo   --model ^<nome^>        - Usar modelo especifico:
echo                           llama3-8b (MELHOR PT-BR), mistral-7b, tinyllama, gpt2-portuguese
echo   --explain             - Mostrar trace das regras DKR aplicadas
echo   --no-dkr              - Desabilitar regras de dominio
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
echo   python run.py qa licencas.pdf -q "Qual a licenca mais critica?" --explain
echo.

echo [93mPara usar modelos GGUF (Llama 3.1, Mistral, TinyLlama):[0m
echo   1. Instalar llama-cpp-python: scripts\install_llama_cpp.cmd
echo   2. Baixar modelo: scripts\download_models.ps1 -Model llama3
echo   3. Verificar: python run.py models --check
echo.
