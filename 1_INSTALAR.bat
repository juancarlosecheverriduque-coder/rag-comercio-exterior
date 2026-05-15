@echo off
chcp 65001 >nul
title RAG Comercio Exterior - Instalador
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       RAG COMERCIO EXTERIOR COLOMBIA                 ║
echo  ║       Instalador automático                          ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Este instalador configurará todo el sistema.
echo  Duración aproximada: 3-5 minutos.
echo.
pause

:: ── 1. Verificar Python ──────────────────────────────────────────────────────
echo.
echo  [1/6] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ✗ Python no está instalado.
    echo.
    echo  Por favor instala Python desde:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANTE: Marca la opción "Add Python to PATH" durante la instalación.
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
echo  ✓ Python encontrado.

:: ── 2. Verificar pip ─────────────────────────────────────────────────────────
echo.
echo  [2/6] Verificando pip...
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ✗ pip no disponible. Intenta reinstalar Python.
    pause
    exit /b 1
)
echo  ✓ pip disponible.

:: ── 3. Instalar dependencias ─────────────────────────────────────────────────
echo.
echo  [3/6] Instalando dependencias (esto toma unos minutos)...
echo.
pip install anthropic chromadb sentence-transformers ^
    requests beautifulsoup4 lxml pypdf2 schedule ^
    flask flask-cors apscheduler tqdm colorama ^
    --quiet --no-warn-script-location

if %errorlevel% neq 0 (
    echo.
    echo  ✗ Error instalando dependencias.
    echo  Verifica tu conexión a internet e intenta de nuevo.
    pause
    exit /b 1
)
echo  ✓ Dependencias instaladas.

:: ── 4. Crear carpetas ────────────────────────────────────────────────────────
echo.
echo  [4/6] Creando estructura de carpetas...
if not exist "datos\legislacion" mkdir "datos\legislacion"
if not exist "datos\vectordb"    mkdir "datos\vectordb"
if not exist "datos\descargas"   mkdir "datos\descargas"
if not exist "logs"              mkdir "logs"
echo  ✓ Carpetas creadas.

:: ── 5. Configurar API key ────────────────────────────────────────────────────
echo.
echo  [5/6] Configurando API key de Anthropic...
echo.

if exist "config.env" (
    echo  ✓ Archivo de configuración ya existe. Saltando.
    goto skip_apikey
)

echo  Necesitas tu API key de Anthropic.
echo  La encuentras en: https://console.anthropic.com/
echo.
set /p APIKEY="  Pega tu API key aquí: "

if "%APIKEY%"=="" (
    echo  ✗ No ingresaste una API key. Puedes configurarla luego editando config.env
    echo ANTHROPIC_API_KEY=TU_API_KEY_AQUI > config.env
) else (
    echo ANTHROPIC_API_KEY=%APIKEY% > config.env
    echo  ✓ API key guardada en config.env
)

:skip_apikey

:: ── 6. Indexar legislación existente ────────────────────────────────────────
echo.
echo  [6/6] Indexando legislación existente...
echo.

:: Copiar archivos de la carpeta legislacion si existe en el escritorio
if exist "%USERPROFILE%\Desktop\legislacion" (
    echo  Encontré carpeta 'legislacion' en el Escritorio. Copiando...
    xcopy "%USERPROFILE%\Desktop\legislacion\*.*" "datos\legislacion\" /E /I /Q
    echo  ✓ Archivos copiados.
)
if exist "%USERPROFILE%\Escritorio\legislacion" (
    echo  Encontré carpeta 'legislacion' en el Escritorio. Copiando...
    xcopy "%USERPROFILE%\Escritorio\legislacion\*.*" "datos\legislacion\" /E /I /Q
    echo  ✓ Archivos copiados.
)

python core\indexador.py --inicial

:: ── Finalizado ───────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  ✓ INSTALACIÓN COMPLETA                             ║
echo  ║                                                      ║
echo  ║  Para usar el sistema:                               ║
echo  ║    → Doble clic en  2_INICIAR.bat                   ║
echo  ║                                                      ║
echo  ║  Se abrirá el navegador automáticamente.             ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause
