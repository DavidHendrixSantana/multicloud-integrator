# Multi-Cloud File Transfer CLI

Un script CLI en Python para copiar archivos entre AWS S3, Azure Blob Storage y Google Cloud Storage.

## Características

- ✅ Soporte para AWS S3, Azure Blob Storage y Google Cloud Storage
- ✅ Transferencias directas entre proveedores cloud
- ✅ Autenticación segura con cada proveedor
- ✅ Sistema de reintentos automáticos para resiliencia
- ✅ Logging detallado en JSON y formato legible
- ✅ Interfaz CLI intuitiva con Rich UI
- ✅ Transferencias en lote desde archivos JSON
- ✅ Manejo robusto de errores

## Instalación

1. **Clona el repositorio:**
```bash
git clone <repository-url>
cd cli_multi_nube
```

2. **Instala las dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configura las credenciales:**
```bash
cp .env.example .env
# Edita .env con tus credenciales de cloud providers
```

## Configuración

### Variables de Entorno

Copia `.env.example` a `.env` y configura las credenciales necesarias:

#### AWS S3
```env
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_DEFAULT_REGION=us-east-1
```

#### Azure Blob Storage
```env
AZURE_STORAGE_ACCOUNT_NAME=tu_storage_account
AZURE_STORAGE_ACCOUNT_KEY=tu_account_key
# O alternativamente:
# AZURE_STORAGE_CONNECTION_STRING=tu_connection_string
```

#### Google Cloud Storage
```env
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
GOOGLE_CLOUD_PROJECT_ID=tu_project_id
```

### Configuración de Aplicación
```env
LOG_LEVEL=INFO
MAX_RETRIES=3
RETRY_DELAY=2
CHUNK_SIZE=8388608
TIMEOUT=300
```

## Uso

### Comandos Principales

#### Probar Conexiones
```bash
python src/cli.py test
```

#### Listar Archivos
```bash
# Listar archivos en S3
python src/cli.py list s3://mi-bucket/

# Listar archivos en Azure
python src/cli.py list azure://mi-container/

# Listar archivos en GCP
python src/cli.py list gcs://mi-bucket/
```

#### Copiar Archivos
```bash
# Entre proveedores cloud
python src/cli.py copy s3://bucket/file.txt azure://container/file.txt

# Subir archivo local
python src/cli.py copy ./local-file.txt s3://bucket/remote-file.txt

# Descargar archivo
python src/cli.py copy azure://container/file.txt ./downloaded-file.txt

# Con metadatos (para uploads)
python src/cli.py copy ./file.txt gcs://bucket/file.txt --metadata '{"author": "cli", "version": "1.0"}'
```

#### Información de Archivos
```bash
python src/cli.py info s3://bucket/file.txt
```

#### Eliminar Archivos
```bash
python src/cli.py delete gcs://bucket/file.txt --force
```

#### Transferencias en Lote
```bash
# Crear archivo JSON con transferencias
echo '[
  {"source": "s3://bucket1/file1.txt", "destination": "azure://container/file1.txt"},
  {"source": "azure://container/file2.txt", "destination": "gcs://bucket2/file2.txt"}
]' > transfers.json

# Ejecutar transferencias
python src/cli.py batch transfers.json
```

#### Verificar Configuración
```bash
python src/cli.py config-check
```

#### Listar Proveedores Soportados
```bash
python src/cli.py providers
```

### Formatos de URL

| Proveedor | Formato | Ejemplo |
|-----------|---------|---------|
| AWS S3 | `s3://bucket/path/file` | `s3://mi-bucket/carpeta/archivo.txt` |
| Azure Blob | `azure://container/path/file` | `azure://mi-container/carpeta/archivo.txt` |
| Google Cloud Storage | `gcs://bucket/path/file` | `gcs://mi-bucket/carpeta/archivo.txt` |

## Ejemplos de Uso

### 1. Migración de S3 a Azure
```bash
# Listar archivos origen
python src/cli.py list s3://old-bucket/ --format json > files.json

# Copiar archivos críticos
python src/cli.py copy s3://old-bucket/important-data.zip azure://new-container/backup/important-data.zip

# Verificar copia
python src/cli.py info azure://new-container/backup/important-data.zip
```

### 2. Backup Multi-Cloud
```bash
# Backup local a múltiples clouds
python src/cli.py copy ./backup.tar.gz s3://backup-bucket/daily/backup-$(date +%Y%m%d).tar.gz
python src/cli.py copy ./backup.tar.gz azure://backup-container/daily/backup-$(date +%Y%m%d).tar.gz
python src/cli.py copy ./backup.tar.gz gcs://backup-bucket/daily/backup-$(date +%Y%m%d).tar.gz
```

### 3. Sincronización Entre Proveedores
```bash
# Crear lista de transferencias para sincronización
python src/cli.py list s3://source-bucket/ --format json | \
  jq -r '.[] | {"source": "s3://source-bucket/\(.name)", "destination": "azure://dest-container/\(.name)"}' | \
  jq -s '.' > sync-transfers.json

# Ejecutar sincronización
python src/cli.py batch sync-transfers.json
```

## Logging

### Archivos de Log
Los logs se guardan en el directorio `logs/` con formato timestamp:
- `multi_cloud_cli_YYYYMMDD_HHMMSS.log`

### Niveles de Log
- `DEBUG`: Información detallada de debugging
- `INFO`: Información general de operaciones
- `WARNING`: Advertencias y reintentos
- `ERROR`: Errores de operaciones

### Formato de Logs
Los logs incluyen información estructurada:
```json
{
  "timestamp": "2025-01-15T10:30:45.123456",
  "level": "info",
  "logger": "transfer_manager",
  "operation": "s3_upload",
  "source_path": "./file.txt",
  "destination": "s3://bucket/file.txt",
  "bytes_transferred": 1048576,
  "duration_seconds": 2.34,
  "speed": "447.7 KB/s"
}
```

## Estructura del Proyecto

```
cli_multi_nube/
├── src/
│   ├── __init__.py              # Módulo principal
│   ├── cli.py                   # Interfaz CLI
│   ├── config.py                # Gestión de configuración
│   ├── logger.py                # Sistema de logging
│   ├── utils.py                 # Utilidades y reintentos
│   ├── transfer_manager.py      # Gestor de transferencias
│   └── connectors/
│       ├── __init__.py          # Factory de conectores
│       ├── base.py              # Clases base abstractas
│       ├── s3_connector.py      # Conector AWS S3
│       ├── azure_connector.py   # Conector Azure Blob
│       └── gcp_connector.py     # Conector Google Cloud
├── logs/                        # Archivos de log
├── tests/                       # Tests unitarios
├── requirements.txt             # Dependencias Python
├── .env.example                 # Plantilla de configuración
├── .gitignore                   # Archivos ignorados por Git
└── README.md                    # Documentación
```

## Manejo de Errores y Resiliencia

### Reintentos Automáticos
- Configurables vía `MAX_RETRIES` y `RETRY_DELAY`
- Backoff exponencial para evitar saturar APIs
- Reintentos solo para errores transitorios

### Validación
- Verificación de credenciales al inicio
- Validación de URLs y paths
- Comprobación de existencia de archivos

### Recuperación
- Limpieza automática de archivos temporales
- Manejo graceful de interrupciones (Ctrl+C)
- Logging detallado para debugging

## Limitaciones y Consideraciones

### Limitaciones
- Las transferencias entre proveedores diferentes requieren descarga temporal
- No soporte para transferencias resumibles (aún)
- Límites de tamaño dependen de los proveedores cloud

### Consideraciones de Seguridad
- Credenciales almacenadas en archivo .env (no commitear)
- Archivos temporales se eliminan automáticamente
- Logs no contienen información sensible

### Performance
- Transferencias optimizadas por chunks
- Progreso visual para operaciones largas
- Transferencias paralelas en modo batch

## Troubleshooting

### Errores Comunes

#### Error de Autenticación
```bash
# Verificar configuración
python src/cli.py config-check

# Probar conexiones
python src/cli.py test
```

#### Archivo No Encontrado
```bash
# Verificar existencia
python src/cli.py info cloud://bucket/file

# Listar contenido del directorio
python src/cli.py list cloud://bucket/
```

#### Permisos Insuficientes
- Verificar permisos IAM/RBAC en el proveedor cloud
- Confirmar que las credenciales tienen acceso al recurso

### Logs de Debug
```bash
# Habilitar modo verbose
python src/cli.py --verbose copy source destination

# Revisar logs detallados
tail -f logs/multi_cloud_cli_*.log
```

## Contribuciones

Para contribuir al proyecto:
1. Fork el repositorio
2. Crea una branch para tu feature
3. Implementa tests para nuevas funcionalidades
4. Ejecuta los tests existentes
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT. Ver archivo LICENSE para detalles.
