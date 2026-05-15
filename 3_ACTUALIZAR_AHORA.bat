@echo off
chcp 65001 >nul
title RAG - Actualizando normas...
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  ACTUALIZACIÓN MANUAL DE NORMAS                     ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Buscando normas nuevas en todas las fuentes...
echo.
python core\monitor.py --ahora
echo.
echo  ✓ Actualización completa.
pause
