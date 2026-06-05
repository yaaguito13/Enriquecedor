@echo off
echo ========================================================
echo Constructor del Ejecutable EmpresaScout para Windows
echo ========================================================
echo.
echo Instalando dependencias automaticamente...
pip install pyinstaller flask requests beautifulsoup4 lxml openpyxl duckduckgo-search

echo.
echo Construyendo EmpresaScout.exe...
cd src
pyinstaller --noconfirm --onefile --windowed --icon="logo.ico" --add-data "templates;templates/" --add-data "static;static/" --name "EmpresaScout" app.py

echo.
echo ========================================================
echo ¡Terminado!
echo Si todo ha ido bien, se ha creado la carpeta "dist" dentro de "src".
echo Ruta exacta: src\dist\EmpresaScout\
echo ========================================================
pause
