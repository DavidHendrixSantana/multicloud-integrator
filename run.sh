#!/bin/bash
# Ejecutar el CLI Multi-Cloud

# Script de conveniencia para ejecutar la herramienta CLI
# Uso: ./run.sh [comando] [argumentos]

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "Activando entorno virtual..."
    source venv/bin/activate
fi

# Ejecutar CLI con Python
python main.py "$@"
