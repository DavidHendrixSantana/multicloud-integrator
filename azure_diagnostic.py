#!/usr/bin/env python3
"""
Script de diagnóstico específico para Azure Blob Storage
"""
import sys
import os
from pathlib import Path

# Add src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import (
    ResourceNotFoundError,
    ClientAuthenticationError,
    HttpResponseError,
    AzureError
)
from config import config

def test_azure_detailed():
    print("=== DIAGNÓSTICO DETALLADO DE AZURE BLOB STORAGE ===\n")
    
    # Verificar configuración
    print("1. Verificando configuración...")
    print(f"   AZURE_STORAGE_ACCOUNT_NAME: {config.azure_storage_account_name}")
    print(f"   AZURE_STORAGE_ACCOUNT_KEY: {'*' * len(config.azure_storage_account_key) if config.azure_storage_account_key else 'No configurado'}")
    print(f"   AZURE_STORAGE_CONNECTION_STRING: {'Configurado' if config.azure_storage_connection_string else 'No configurado'}")
    
    # Validar configuración
    if not config.validate_azure_config():
        print("\n❌ ERROR: Configuración de Azure no es válida")
        print("   Asegúrate de tener configurado:")
        print("   - AZURE_STORAGE_ACCOUNT_NAME")
        print("   - AZURE_STORAGE_ACCOUNT_KEY")
        print("   O alternativamente:")
        print("   - AZURE_STORAGE_CONNECTION_STRING")
        return False
    
    print("✅ Configuración básica válida\n")
    
    # Probar conexión
    print("2. Probando conexión...")
    
    try:
        if config.azure_storage_connection_string:
            print("   Usando connection string...")
            blob_service_client = BlobServiceClient.from_connection_string(
                config.azure_storage_connection_string
            )
        else:
            print("   Usando account name + key...")
            account_url = f"https://{config.azure_storage_account_name}.blob.core.windows.net"
            print(f"   URL: {account_url}")
            blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=config.azure_storage_account_key
            )
        
        print("✅ Cliente BlobService creado correctamente\n")
        
        # Probar listar contenedores
        print("3. Probando listar contenedores...")
        containers_iter = blob_service_client.list_containers()
        containers = []
        # Limitar a 5 contenedores para el diagnóstico
        for i, container in enumerate(containers_iter):
            if i >= 5:
                break
            containers.append(container)
        
        print(f"✅ Conexión exitosa! Se encontraron {len(containers)} contenedores:")
        for container in containers:
            print(f"   - {container.name}")
        
        return True
        
    except ClientAuthenticationError as e:
        print(f"❌ ERROR DE AUTENTICACIÓN:")
        print(f"   {str(e)}")
        print("\n🔧 POSIBLES SOLUCIONES:")
        print("   1. Verifica que el AZURE_STORAGE_ACCOUNT_NAME sea correcto")
        print("   2. Verifica que el AZURE_STORAGE_ACCOUNT_KEY sea válido")
        print("   3. Asegúrate de que la cuenta de almacenamiento exista")
        print("   4. Verifica que no haya espacios extra en las credenciales")
        return False
        
    except HttpResponseError as e:
        print(f"❌ ERROR HTTP ({e.status_code}):")
        print(f"   {str(e)}")
        
        if e.status_code == 404:
            print("\n🔧 POSIBLES SOLUCIONES:")
            print("   1. Verifica que el nombre de la cuenta de almacenamiento sea correcto")
            print("   2. Asegúrate de que la cuenta exista en Azure")
        elif e.status_code == 403:
            print("\n🔧 POSIBLES SOLUCIONES:")
            print("   1. Verifica que el access key sea correcto")
            print("   2. Verifica que la cuenta tenga los permisos necesarios")
        
        return False
        
    except Exception as e:
        print(f"❌ ERROR GENERAL:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_azure_detailed()
    if not success:
        print(f"\n📋 INFORMACIÓN DE AYUDA:")
        print(f"1. Verifica tus credenciales en Azure Portal:")
        print(f"   - Ve a tu Storage Account")
        print(f"   - Security + networking → Access keys")
        print(f"   - Copia el Storage account name y Key1 o Key2")
        print(f"\n2. Asegúrate de que el archivo .env esté configurado correctamente")
        print(f"3. Verifica que no haya espacios o caracteres especiales incorrectos")
        sys.exit(1)
    else:
        print(f"\n🎉 ¡Azure Blob Storage configurado correctamente!")
