@echo off
setlocal ENABLEDELAYEDEXPANSION
REM ============================================
REM Script de Instalacao do llama-cpp-python
REM ============================================
REM
REM Este script instala o llama-cpp-python que e necessario
REM para usar modelos GGUF como Llama 3.1, Mistral e TinyLlama.
REM
REM METODO: Instalacao via wheel pre-compilado (sem necessidade de compilador)
REM
REM Uso:
REM   scripts\install_llama_cpp.cmd
REM

echo.
echo ==============================================
echo   Instalacao do llama-cpp-python
echo ==============================================
echo.

REM Define diretorio do projeto
set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

REM Verifica se o ambiente virtual existe
if not exist "venv\Scripts\python.exe" (
    if not exist ".venv\Scripts\python.exe" (
        echo [ERRO] Ambiente virtual nao encontrado!
        echo Execute primeiro o instalador do projeto.
        goto :error
    ) else (
        set "VENV_PATH=.venv"
    )
) else (
    set "VENV_PATH=venv"
)

set "PIP_EXE=%VENV_PATH%\Scripts\python.exe"

echo Verificando se llama-cpp-python ja esta instalado...
"%PIP_EXE%" -c "import llama_cpp" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [OK] llama-cpp-python ja esta instalado!
    "%PIP_EXE%" -c "import llama_cpp; print('  Versao:', llama_cpp.__version__)"
    goto :success
)

echo.
echo Procurando wheel pre-compilado...

REM Procura wheel na pasta wheels/
set "WHEEL_FOUND=0"
for %%F in (wheels\llama_cpp_python*.whl) do (
    echo   Encontrado: %%~nxF
    echo.
    echo Instalando llama-cpp-python via wheel...
    "%PIP_EXE%" -m pip install "%%F" --no-index --no-deps
    if not errorlevel 1 (
        set "WHEEL_FOUND=1"
        goto :check_install
    ) else (
        echo [AVISO] Falha ao instalar %%~nxF
    )
)

if !WHEEL_FOUND!==0 (
    echo.
    echo [AVISO] Wheel pre-compilado nao encontrado em wheels\
    echo.
    echo Tentando instalar via pip (requer internet)...
    "%PIP_EXE%" -m pip install llama-cpp-python
    if errorlevel 1 (
        echo.
        echo [ERRO] Falha na instalacao via pip!
        echo.
        echo Solucoes:
        echo   1. Baixe o wheel pre-compilado de:
        echo      https://github.com/abetlen/llama-cpp-python/releases
        echo   2. Coloque o arquivo .whl na pasta wheels\
        echo   3. Execute este script novamente
        echo.
        goto :error
    )
)

:check_install
echo.
echo Verificando instalacao...
"%PIP_EXE%" -c "import llama_cpp; print('llama-cpp-python versao:', llama_cpp.__version__)"

if errorlevel 1 (
    echo [AVISO] Instalacao concluida mas verificacao falhou.
    goto :error
)

:success
echo.
echo ==============================================
echo   Instalacao Concluida com Sucesso!
echo ==============================================
echo.
echo Agora voce pode usar modelos GGUF:
echo.
echo   Llama 3.1 8B (RECOMENDADO para portugues):
echo     1. Baixar: scripts\download_models.cmd llama3
echo     2. Usar:   python run.py qa documento.pdf -q "pergunta" --model llama3-8b
echo.
echo   TinyLlama (recursos limitados):
echo     python run.py qa documento.pdf -q "pergunta" --model tinyllama
echo.
echo Verificar status dos modelos:
echo   python run.py models --check
echo.
goto :end

:error
echo.
echo ==============================================
echo   Instalacao com Erros
echo ==============================================
echo.
echo O sistema continuara funcionando com GPT-2 Portuguese.
echo Para usar modelos GGUF, resolva os erros acima.
echo.
exit /b 1

:end
echo.
pause
endlocal
