#!/bin/bash
# Script de instalación y configuración para Multi-Cloud CLI

set -e

echo "=== Multi-Cloud CLI - Instalación y Configuración ==="

# Verificar Python
echo "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    echo "Por favor instala Python 3.8 o superior"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION detectado"

# Crear entorno virtual
echo "Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Entorno virtual creado"
else
    echo "ℹ️ Entorno virtual ya existe"
fi

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt

echo "✅ Dependencias instaladas correctamente"

# Configurar archivo .env
echo "Configurando archivo .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Archivo .env creado desde .env.example"
    echo "⚠️ IMPORTANTE: Edita el archivo .env con tus credenciales de cloud providers"
else
    echo "ℹ️ Archivo .env ya existe"
fi

# Crear directorios necesarios
echo "Creando directorios..."
mkdir -p logs
mkdir -p temp_transfers

# Hacer ejecutables los scripts
chmod +x run.sh
chmod +x install.sh

echo ""
echo "=== Instalación Completada ==="
echo ""
echo "Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales"
echo "2. Prueba la conexión: ./run.sh test"
echo "3. Ver ayuda: ./run.sh --help"
echo ""
echo "Ejemplos de credenciales:"
echo ""
echo "AWS S3:"
echo "  AWS_ACCESS_KEY_ID=tu_access_key"
echo "  AWS_SECRET_ACCESS_KEY=tu_secret_key"
echo ""
echo "Azure Blob Storage:"
echo "  AZURE_STORAGE_ACCOUNT_NAME=tu_storage_account"
echo "  AZURE_STORAGE_ACCOUNT_KEY=tu_account_key"
echo ""
echo "Google Cloud Storage:"
echo "  GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json"
echo "  GOOGLE_CLOUD_PROJECT_ID=tu_project_id"
echo ""
echo "¡Listo para transferir archivos entre clouds! 🚀"
