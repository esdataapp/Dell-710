#!/usr/bin/env python3
"""
Quick Deploy Script - PropertyScraper Dell710
Script de despliegue rápido para Dell T710
"""

import os
import sys
import json
from pathlib import Path
import subprocess

def main():
    """Script principal de despliegue rápido"""
    print("🚀 PropertyScraper Dell710 - Quick Deploy")
    print("="*50)
    
    project_root = Path(__file__).parent
    
    print("📁 Verificando estructura del proyecto...")
    
    # Verificar directorios principales
    required_dirs = [
        'scrapers', 'orchestrator', 'utils', 'config', 
        'monitoring', 'logs', 'data', 'ssh_deployment', 'docs'
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"✅ {dir_name}/")
        else:
            print(f"❌ {dir_name}/ - FALTANTE")
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"\n⚠️  Directorios faltantes: {', '.join(missing_dirs)}")
        print("Ejecute utils/create_data_structure.py primero")
        return False
    
    # Verificar archivos principales
    print("\n📄 Verificando archivos principales...")
    
    key_files = [
        'scrapers/inmuebles24_professional.py',
        'orchestrator/concurrent_manager.py',
        'orchestrator/bimonthly_scheduler.py',
        'ssh_deployment/remote_executor.py',
        'utils/create_data_structure.py',
        'config/dell_t710_config.yaml',
        'requirements.txt'
    ]
    
    missing_files = []
    for file_path in key_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - FALTANTE")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Archivos faltantes: {len(missing_files)}")
        return False
    
    # Verificar estructura de datos
    print("\n📂 Verificando estructura de datos...")
    data_dir = project_root / 'data'
    
    if data_dir.exists():
        websites = list(data_dir.iterdir())
        print(f"✅ Estructura de datos creada: {len(websites)} sitios web")
        
        # Verificar estructura de inmuebles24
        inmuebles24_dir = data_dir / 'inmuebles24'
        if inmuebles24_dir.exists():
            operations = list(inmuebles24_dir.iterdir())
            print(f"✅ inmuebles24: {len(operations)} tipos de operación")
        else:
            print("❌ inmuebles24 directory missing")
    else:
        print("❌ Estructura de datos no creada")
        print("Ejecute: python utils/create_data_structure.py")
    
    print("\n🔧 Comandos disponibles:")
    print("="*50)
    
    print("\n📦 1. Instalar dependencias:")
    print("   pip install -r requirements.txt")
    
    print("\n🧪 2. Probar scraper local (5 páginas):")
    print("   python scrapers/inmuebles24_professional.py --headless --pages=5")
    
    print("\n🌐 3. Desplegar en Dell T710:")
    print("   python ssh_deployment/remote_executor.py --deploy")
    
    print("\n🖥️  4. Verificar estado remoto:")
    print("   python ssh_deployment/remote_executor.py --status")
    
    print("\n🧪 5. Probar scraper remoto:")
    print("   python ssh_deployment/remote_executor.py --test-scraper=inmuebles24 --pages=5")
    
    print("\n⚡ 6. Ejecutar orquestación concurrente:")
    print("   python orchestrator/concurrent_manager.py --test")
    
    print("\n📅 7. Iniciar scheduler bi-mensual:")
    print("   python orchestrator/bimonthly_scheduler.py --start")
    
    print("\n📊 8. Ver estado del scheduler:")
    print("   python orchestrator/bimonthly_scheduler.py --status")
    
    print("\n" + "="*50)
    print("🎯 Proyecto PropertyScraper Dell710 listo para usar")
    print("📚 Ver README.md para documentación completa")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
