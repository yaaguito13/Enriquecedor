@echo off
echo ========================================================
echo Constructor del Ejecutable EmpresaScout para Windows
echo ========================================================
echo.
echo Asegurate de tener Python instalado y haber ejecutado:
echo pip install pyinstaller flask requests beautifulsoup4 lxml openpyxl duckduckgo-search
echo.
pause

echo Construyendo EmpresaScout.exe...
cd src
pyinstaller --noconfirm --onedir --windowed --icon=NONE --add-data "templates;templates/" --add-data "static;static/" --name "EmpresaScout" app.py

echo.
echo ========================================================
echo ¡Terminado!
echo Tu programa se encuentra en la carpeta src/dist/EmpresaScout/
echo ========================================================
pause
