@echo off
REM ============================================
REM Document Analyzer - Ativação do Ambiente
REM ============================================

REM Define o diretório do script
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Ativa ambiente virtual
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

REM Configura PATH para Tesseract OCR (se instalado)
if exist "C:\Program Files\Tesseract-OCR" (
    set "PATH=C:\Program Files\Tesseract-OCR;%PATH%"
)

REM ============================================
REM Lê modo de operação do config.yaml
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
REM Configura variáveis de ambiente baseado no modo
REM ============================================
set "MODELS_PATH=%SCRIPT_DIR%models"

REM Sempre configura o caminho dos modelos
set "HF_HOME=%MODELS_PATH%"
set "HF_HUB_CACHE=%MODELS_PATH%"
set "TRANSFORMERS_CACHE=%MODELS_PATH%"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"

if /i "%DEFAULT_MODE%"=="offline" (
    REM Modo OFFLINE: bloqueia todas as conexões
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
REM Exibe banner
REM ============================================
echo.
echo [92m+===========================================================+[0m
echo [92m^|   DOCUMENT ANALYZER - Ambiente Ativado                   ^|[0m
echo [92m+===========================================================+[0m
echo.
echo Modo de operacao: %MODE_COLOR%%MODE_TEXT%[0m
echo.
echo [95mPerfis disponiveis:[0m
echo   inventory        - Escritura de Inventario (herdeiros, bens BTG)
echo   meeting_minutes  - Ata de Reuniao de Quotistas (ativos, quantidades)
echo.
echo [96mComandos:[0m
echo   python run.py analyze ^<arquivo.pdf^>                    - Analise (perfil padrao)
echo   python run.py analyze ^<arquivo.pdf^> -p inventory       - Analise de Inventario
echo   python run.py analyze ^<arquivo.pdf^> -p meeting_minutes - Analise de Ata de Reuniao
echo   python run.py profiles                                 - Listar perfis
echo   python run.py extract ^<arquivo.pdf^>                    - Apenas extrai texto
echo   python run.py info                                     - Ver configuracoes
echo.
echo [95mFlags de modo (override temporario):[0m
echo   python run.py --offline analyze doc.pdf   - Forca modo offline
echo   python run.py --online analyze doc.pdf    - Forca modo online
echo   python run.py --hybrid analyze doc.pdf    - Forca modo hibrido
echo.
echo [93mExemplos:[0m
echo   python run.py analyze escritura.pdf -o ./resultado
echo   python run.py analyze ata_quotistas.pdf -p meeting_minutes
echo   python run.py --online --allow-download analyze doc.pdf
echo.
