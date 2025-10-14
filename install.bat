@echo off
REM Script de instalación y configuración para Multi-Cloud CLI en Windows

echo === Multi-Cloud CLI - Instalación y Configuración ===

REM Verificar Python
echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no está instalado o no está en el PATH
    echo Por favor instala Python 3.8 o superior desde https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% detectado

REM Crear entorno virtual
echo Creando entorno virtual...
if not exist "venv" (
    python -m venv venv
    echo ✅ Entorno virtual creado
) else (
    echo ℹ️ Entorno virtual ya existe
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Actualizar pip
echo Actualizando pip...
python -m pip install --upgrade pip

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt

echo ✅ Dependencias instaladas correctamente

REM Configurar archivo .env
echo Configurando archivo .env...
if not exist ".env" (
    copy .env.example .env
    echo ✅ Archivo .env creado desde .env.example
    echo ⚠️ IMPORTANTE: Edita el archivo .env con tus credenciales de cloud providers
) else (
    echo ℹ️ Archivo .env ya existe
)

REM Crear directorios necesarios
echo Creando directorios...
if not exist "logs" mkdir logs
if not exist "temp_transfers" mkdir temp_transfers

echo.
echo === Instalación Completada ===
echo.
echo Próximos pasos:
echo 1. Edita el archivo .env con tus credenciales
echo 2. Prueba la conexión: run.bat test
echo 3. Ver ayuda: run.bat --help
echo.
echo Ejemplos de credenciales:
echo.
echo AWS S3:
echo   AWS_ACCESS_KEY_ID=tu_access_key
echo   AWS_SECRET_ACCESS_KEY=tu_secret_key
echo.
echo Azure Blob Storage:
echo   AZURE_STORAGE_ACCOUNT_NAME=tu_storage_account
echo   AZURE_STORAGE_ACCOUNT_KEY=tu_account_key
echo.
echo Google Cloud Storage:
echo   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
echo   GOOGLE_CLOUD_PROJECT_ID=tu_project_id
echo.
echo ¡Listo para transferir archivos entre clouds! 🚀
pause
