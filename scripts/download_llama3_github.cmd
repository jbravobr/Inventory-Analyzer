@echo off
setlocal ENABLEDELAYEDEXPANSION
REM ============================================
REM Download do Llama 3.1 8B do GitHub Releases
REM ============================================
REM
REM Este script baixa o modelo Llama 3.1 8B diretamente do GitHub Releases
REM do repositorio jbravobr/Inventory-Analyzer, ideal para ambientes
REM corporativos onde o proxy confia apenas no GitHub.
REM
REM Uso:
REM   scripts\download_llama3_github.cmd
REM
REM O modelo sera baixado em partes e automaticamente juntado.
REM

REM Configuracoes
set "OWNER=jbravobr"
set "REPO=Inventory-Analyzer"
set "TAG=models-v1"
set "MODEL_NAME=Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
set "OUTPUT_DIR=models\generator"
set "EXPECTED_HASH=7B064F5842BF9532C91456DEDA288A1B672397A54FA729AA665952863033557C"

REM URL base
set "BASE_URL=https://github.com/%OWNER%/%REPO%/releases/download/%TAG%"

REM Diretorio temporario
set "TEMP_DIR=%TEMP%\llama3_download"

echo.
echo ============================================
echo   Download do Llama 3.1 8B (GitHub)
echo ============================================
echo.
echo Repositorio: %OWNER%/%REPO%
echo Release: %TAG%
echo Tamanho total: ~4.6 GB
echo.

REM Verificar se ja existe
if exist "%OUTPUT_DIR%\%MODEL_NAME%" (
    echo [OK] Modelo ja existe: %OUTPUT_DIR%\%MODEL_NAME%
    echo      Delete o arquivo para baixar novamente.
    goto :end
)

REM Criar diretorios
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo Baixando partes do modelo...
echo.

REM Baixar cada parte
set "PARTS=001 002 003 004"
set "PART_NUM=0"
set "TOTAL_PARTS=4"

for %%P in (%PARTS%) do (
    set /a PART_NUM+=1
    set "PART_FILE=%MODEL_NAME%.%%P"
    set "PART_URL=%BASE_URL%/!PART_FILE!"
    set "PART_PATH=%TEMP_DIR%\!PART_FILE!"
    
    if exist "!PART_PATH!" (
        echo [!PART_NUM!/%TOTAL_PARTS%] !PART_FILE! - ja existe, pulando
    ) else (
        echo [!PART_NUM!/%TOTAL_PARTS%] Baixando !PART_FILE!...
        curl --ssl-no-revoke -L -o "!PART_PATH!" "!PART_URL!"
        if errorlevel 1 (
            echo.
            echo [ERRO] Falha ao baixar !PART_FILE!
            echo.
            echo Possiveis causas:
            echo   1. Release '%TAG%' ainda nao existe no repositorio
            echo   2. Assets ainda nao foram uploaded
            echo   3. Problema de conexao/proxy
            echo.
            echo Verifique: https://github.com/%OWNER%/%REPO%/releases/tag/%TAG%
            goto :error
        )
        echo     OK
    )
)

echo.
echo Juntando partes...

REM Juntar as partes usando copy /b
set "OUTPUT_FILE=%OUTPUT_DIR%\%MODEL_NAME%"
copy /b "%TEMP_DIR%\%MODEL_NAME%.001"+"%TEMP_DIR%\%MODEL_NAME%.002"+"%TEMP_DIR%\%MODEL_NAME%.003"+"%TEMP_DIR%\%MODEL_NAME%.004" "%OUTPUT_FILE%" >nul

if errorlevel 1 (
    echo [ERRO] Falha ao juntar as partes
    goto :error
)

echo   OK - Partes juntadas com sucesso

echo.
echo Limpando arquivos temporarios...
rmdir /s /q "%TEMP_DIR%" 2>nul

echo.
echo ============================================
echo   Download Concluido!
echo ============================================
echo.
echo Modelo salvo em: %OUTPUT_FILE%
echo.
echo Para usar:
echo   python run.py qa documento.pdf -q "sua pergunta" --model llama3-8b
echo.
goto :end

:error
echo.
echo ============================================
echo   Download com Erros
echo ============================================
echo.
exit /b 1

:end
endlocal

