@echo off
title RemateWeb GC Trigger - Build
echo ============================================
echo   Gerando executavel GC-Trigger.exe
echo ============================================
echo.

REM Instalar PyInstaller se necessario
pip install pyinstaller pillow >nul 2>&1

REM Converter PNG para ICO
python -c "from PIL import Image; img = Image.open('icon.png'); img.save('icon.ico', format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"

echo [1/2] Compilando...
pyinstaller --noconfirm --onefile --windowed ^
    --name "GC-Trigger" ^
    --icon "icon.ico" ^
    --add-data "icon.png;." ^
    app.py

echo.
echo [2/2] Pronto!
echo.
echo O executavel esta em: dist\GC-Trigger.exe
echo ============================================
pause
