@echo off
REM Ejecutar el CLI Multi-Cloud en Windows

REM Script de conveniencia para ejecutar la herramienta CLI
REM Uso: run.bat [comando] [argumentos]

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
)

REM Ejecutar CLI con Python
python main.py %*
