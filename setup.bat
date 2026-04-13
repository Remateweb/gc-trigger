@echo off
title RemateWeb GC Trigger - Setup
echo ============================================
echo   RemateWeb GC Trigger - Instalacao
echo ============================================
echo.

REM Verificar se Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Instale Python 3.10+ primeiro.
    pause
    exit /b 1
)

echo [1/2] Instalando dependencias...
pip install -r requirements.txt
echo.

echo [2/2] Pronto! Para iniciar o app, execute:
echo        python app.py
echo.
echo Ou use o start.bat
echo ============================================
pause
