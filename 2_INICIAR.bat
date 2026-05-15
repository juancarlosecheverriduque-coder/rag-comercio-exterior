@echo off
chcp 65001 >nul
title RAG Comercio Exterior - Ejecutando...
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       RAG COMERCIO EXTERIOR COLOMBIA                 ║
echo  ║       Iniciando sistema...                           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

if not exist "config.env" (
    echo  ✗ No encontré config.env
    echo  Ejecuta primero 1_INSTALAR.bat
    pause
    exit /b 1
)

echo  Iniciando servidor y monitor de normas...
echo  El navegador se abrirá en unos segundos.
echo.
echo  Para detener el sistema: cierra esta ventana.
echo.

start "" python core\servidor.py
timeout /t 3 /nobreak >nul
start "" http://localhost:5000
echo  ✓ Sistema activo en http://localhost:5000
echo.
echo  Monitor automático: revisa fuentes cada 6 horas.
echo  Mantén esta ventana abierta mientras usas el sistema.
echo.
pause
