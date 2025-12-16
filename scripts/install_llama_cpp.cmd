@echo off
REM ============================================
REM Script de Instalacao do llama-cpp-python
REM ============================================
REM
REM Este script instala o llama-cpp-python que e necessario
REM para usar modelos GGUF como TinyLlama.
REM
REM IMPORTANTE: Requer compilador C++ instalado (Visual Studio Build Tools)
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
if not exist "venv\Scripts\activate.bat" (
    if not exist ".venv\Scripts\activate.bat" (
        echo [ERRO] Ambiente virtual nao encontrado!
        echo Execute primeiro o instalador do projeto.
        goto :error
    ) else (
        set "VENV_PATH=.venv"
    )
) else (
    set "VENV_PATH=venv"
)

REM Ativa ambiente virtual
echo Ativando ambiente virtual...
call "%VENV_PATH%\Scripts\activate.bat"

if errorlevel 1 (
    echo [ERRO] Falha ao ativar ambiente virtual!
    goto :error
)

echo.
echo Verificando pre-requisitos...

REM Verifica se cmake esta instalado
where cmake >nul 2>&1
if errorlevel 1 (
    echo [AVISO] CMake nao encontrado.
    echo Tentando instalar via pip...
    pip install cmake
    if errorlevel 1 (
        echo [AVISO] Nao foi possivel instalar CMake via pip.
        echo O CMake pode ser necessario para compilacao.
    )
)

echo.
echo Instalando llama-cpp-python...
echo (Isso pode demorar alguns minutos)
echo.

REM Tenta instalar
pip install llama-cpp-python

if errorlevel 1 (
    echo.
    echo [ERRO] Falha na instalacao!
    echo.
    echo Possiveis causas:
    echo   1. Compilador C++ nao instalado
    echo   2. CMake nao encontrado
    echo.
    echo Solucoes:
    echo   1. Instale Visual Studio Build Tools:
    echo      https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo.
    echo   2. Ou use GPT-2 Portuguese (funciona sem compilacao):
    echo      python run.py qa documento.pdf -q "pergunta" --model gpt2-portuguese
    echo.
    goto :error
)

echo.
echo [OK] llama-cpp-python instalado com sucesso!
echo.
echo Verificando instalacao...
python -c "import llama_cpp; print('llama-cpp-python versao:', llama_cpp.__version__)"

if errorlevel 1 (
    echo [AVISO] Instalacao concluida mas verificacao falhou.
    goto :end
)

echo.
echo ==============================================
echo   Instalacao Concluida!
echo ==============================================
echo.
echo Agora voce pode usar o TinyLlama:
echo   python run.py qa documento.pdf -q "pergunta" --model tinyllama
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
echo Para usar TinyLlama, resolva os erros acima.
echo.
exit /b 1

:end
echo.
pause

