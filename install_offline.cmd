@echo off
setlocal ENABLEDELAYEDEXPANSION

echo.
echo ============================================
echo  DOCUMENT ANALYZER - Instalacao OFFLINE
echo ============================================
echo.

echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado no PATH.
    exit /b 1
)
echo   OK - Python encontrado
echo.

echo [2/4] Criando ambiente virtual...
if exist venv (
    echo   Removendo ambiente virtual existente...
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo ERRO ao criar ambiente virtual.
    exit /b 1
)
echo   OK - Ambiente virtual criado
echo.

echo [3/4] Instalando pacotes offline...
set PIP_EXE=venv\Scripts\python.exe

for %%F in (wheels\*.whl) do (
    echo   Instalando %%~nxF ...
    "%PIP_EXE%" -m pip install "%%F" --no-index --no-deps
    if errorlevel 1 (
        echo ERRO ao instalar %%~nxF
        exit /b 1
    )
)

echo.
echo [4/5] Instalando llama-cpp-python...
REM Verifica se ja existe o llama_cpp instalado
"%PIP_EXE%" -c "import llama_cpp" >nul 2>&1
if errorlevel 1 (
    set LLAMA_INSTALLED=0
    for %%F in (wheels\llama_cpp_python*.whl) do (
        echo   Instalando %%~nxF ...
        "%PIP_EXE%" -m pip install "%%F" --no-index --no-deps >nul 2>&1
        if not errorlevel 1 (
            echo   [OK] llama-cpp-python instalado! TinyLlama e Llama 3.1 disponiveis.
            set LLAMA_INSTALLED=1
        )
    )
    if !LLAMA_INSTALLED!==0 (
        echo   [AVISO] Wheel llama-cpp-python nao encontrado na pasta wheels\
        echo          Modelos GGUF nao estarao disponiveis.
    )
) else (
    echo   [OK] llama-cpp-python ja instalado - TinyLlama e Llama 3.1 disponiveis
)
echo.

echo [5/5] Criando diretorios de trabalho...
if not exist output mkdir output
if not exist cache mkdir cache
if not exist cache\qa_responses mkdir cache\qa_responses
if not exist cache\dkr mkdir cache\dkr
if not exist domain_rules mkdir domain_rules

echo.
echo ============================================
echo  Instalacao concluida com sucesso!
echo ============================================
echo.
echo Perfis disponiveis:
echo   inventory        - Escritura de Inventario
echo   meeting_minutes  - Ata de Reuniao de Quotistas
echo.
echo Para usar:
echo   1. execute: call venv\Scripts\activate.bat
echo   2. Analise: python run.py analyze ^<arquivo.pdf^>
echo   3. Q^&A:     python run.py qa ^<arquivo.pdf^> -q "sua pergunta"
echo.
echo Comandos adicionais:
echo   python run.py qa --list-templates      # Templates Q^&A disponiveis
echo   python run.py dkr list                 # Regras de dominio disponiveis
echo   python run.py models                   # Modelos de linguagem disponiveis
echo.

endlocal