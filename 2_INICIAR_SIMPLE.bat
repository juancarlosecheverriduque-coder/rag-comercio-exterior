@echo off
chcp 65001 >nul
title RAG Comercio Exterior - Servidor
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       RAG COMERCIO EXTERIOR COLOMBIA                 ║
echo  ║       Iniciando servidor...                          ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

if not exist "config.env" (
    echo  ✗ No encontré config.env
    echo  Edita manualmente el archivo y agrega tu API key
    pause
    exit /b 1
)

echo  Iniciando servidor en http://localhost:5000
echo.
echo  Abre el navegador y ve a: http://localhost:5000
echo.
echo  Para detener: cierra esta ventana
echo.

python core\servidor.py
pause
