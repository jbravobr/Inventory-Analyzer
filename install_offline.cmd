@echo off
setlocal ENABLEDELAYEDEXPANSION

echo.
echo ============================================
echo  INVENTORY ANALYZER - Instalacao OFFLINE
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
echo [4/4] Criando diretorios de trabalho...
if not exist output mkdir output
if not exist cache mkdir cache

echo.
echo Instalacao concluida com sucesso!
echo Para usar:
echo   1. execute: call venv\Scripts\activate.bat
echo   2. execute: python run.py analyze ^<arquivo.pdf^>
echo.

endlocal