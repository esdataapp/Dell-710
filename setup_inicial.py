#!/usr/bin/env python3
"""
Setup Inicial - PropertyScraper Dell710
Script para configurar el sistema validando los archivos CSV en ``URLs/``
"""

import os
import sys
import csv
import json
import logging
from pathlib import Path
from datetime import datetime

def setup_logging():
    """Configurar logging para setup"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = Path('logs') / f'setup_inicial_{timestamp}.log'
    log_file.parent.mkdir(exist_ok=True, parents=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)8s | SETUP | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def check_urls_files():
    """Verificar que los CSV en URLs/ existen y tienen la estructura correcta"""
    logger = logging.getLogger(__name__)
    logger.info("📄 Verificando archivos CSV en URLs/...")

    urls_dir = Path('URLs')
    if not urls_dir.exists():
        logger.error("❌ Directorio URLs/ no encontrado")
        return False

    csv_files = list(urls_dir.glob('*.csv'))
    if not csv_files:
        logger.error("❌ No se encontraron archivos CSV en URLs/")
        return False

    required_columns = ['PaginaWeb', 'Ciudad', 'Operacion', 'ProductoPaginaWeb', 'URL']
    all_valid = True

    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                logger.warning(f"⚠️ {csv_file.name} está vacío")
                continue

            available = [c.replace('Operación', 'Operacion') for c in rows[0].keys()]
            missing = [col for col in required_columns if col not in available]
            if missing:
                logger.error(f"❌ Columnas faltantes en {csv_file.name}: {missing}")
                all_valid = False
                continue

            logger.info(f"✅ {csv_file.name}: {len(rows)} URLs")
        except Exception as e:
            logger.error(f"❌ Error leyendo {csv_file.name}: {e}")
            all_valid = False

    return all_valid

def create_directory_structure():
    """Crear estructura de directorios necesaria"""
    logger = logging.getLogger(__name__)
    logger.info("📁 Creando estructura de directorios...")
    
    directories = [
        'data',
        'logs',
        'logs/checkpoints',
        'logs/page_samples',
        'config',
        'scrapers',
        'orchestrator',
        'utils',
        'monitoring',
        'ssh_deployment'
    ]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True, parents=True)
        logger.info(f"📂 {dir_name}/")
    
    logger.info("✅ Estructura de directorios creada")

def initialize_registry():
    """Inicializar el registry con las URLs del CSV"""
    logger = logging.getLogger(__name__)
    logger.info("🗂️ Inicializando registry...")
    
    try:
        # Verificar que el archivo utils/enhanced_scraps_registry.py existe
        registry_file = Path('utils') / 'enhanced_scraps_registry.py'
        if not registry_file.exists():
            logger.error("❌ utils/enhanced_scraps_registry.py no encontrado")
            return False

        # Importar y usar el registry desde utils/
        sys.path.append(str(Path('utils').resolve()))
        from utils.enhanced_scraps_registry import EnhancedScrapsRegistry
        
        registry = EnhancedScrapsRegistry()
        
        # Cargar URLs y generar scraps
        logger.info("📥 Cargando URLs desde archivos en URLs/...")
        urls = registry.load_urls_from_csv()
        logger.info(f"✅ {len(urls)} URLs cargadas")
        
        # Obtener estadísticas
        stats = registry.get_registry_stats()
        logger.info("📊 Registry inicializado:")
        logger.info(f"   Scraps activos: {stats.get('scraps_activos', 'N/A')}")
        logger.info(f"   Total scraps: {stats.get('total_scraps', 'N/A')}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Error importando registry: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error inicializando registry: {e}")
        return False

def check_dependencies():
    """Verificar dependencias de Python"""
    logger = logging.getLogger(__name__)
    logger.info("🐍 Verificando dependencias de Python...")
    
    required_packages = [
        'seleniumbase',
        'pandas',
        'psutil',
        'pathlib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package}")
        except ImportError:
            logger.warning(f"❌ {package} no encontrado")
            missing_packages.append(package)
    
    if missing_packages:
        logger.warning("⚠️ Instalar paquetes faltantes:")
        logger.warning(f"pip install {' '.join(missing_packages)}")
        return False
    
    logger.info("✅ Todas las dependencias están instaladas")
    return True

def check_scrapers():
    """Verificar que los scrapers existen"""
    logger = logging.getLogger(__name__)
    logger.info("🤖 Verificando scrapers...")
    
    scrapers_dir = Path('scrapers')
    required_scrapers = [
        'inm24.py',
        'cyt.py',
        'mit.py',
        'lam.py',
        'prop.py',
        'tro.py'
    ]
    
    missing_scrapers = []
    
    for scraper in required_scrapers:
        scraper_path = scrapers_dir / scraper
        if scraper_path.exists():
            logger.info(f"✅ {scraper}")
        else:
            logger.warning(f"❌ {scraper} no encontrado")
            missing_scrapers.append(scraper)
    
    if missing_scrapers:
        logger.warning("⚠️ Scrapers faltantes encontrados")
        return False
    
    logger.info("✅ Todos los scrapers están disponibles")
    return True

def create_config_files():
    """Crear archivos de configuración básicos"""
    logger = logging.getLogger(__name__)
    logger.info("⚙️ Creando archivos de configuración...")
    
    # Configuración básica del orquestador
    orchestrator_config = {
        'max_concurrent_websites': 4,
        'max_cpu_usage': 80,
        'max_memory_usage': 80,
        'checkpoint_interval': 50,
        'default_page_limit': 50,
        'anti_detection': {
            'min_delay': 2,
            'max_delay': 4,
            'user_agents_rotation': True,
            'random_viewport': True
        }
    }
    
    config_dir = Path('config')
    config_dir.mkdir(exist_ok=True, parents=True)
    
    with open(config_dir / 'orchestrator_config.json', 'w', encoding='utf-8') as f:
        json.dump(orchestrator_config, f, indent=2, ensure_ascii=False)
    
    logger.info("📄 orchestrator_config.json creado")
    
    # Configuración de scrapers
    scraper_config = {
        'headless_mode': True,
        'timeout': 30,
        'max_retries': 3,
        'page_load_strategy': 'normal',
        'anti_detection': {
            'stealth_mode': True,
            'disable_images': False,
            'random_user_agent': True
        }
    }
    
    with open(config_dir / 'scraper_config.json', 'w', encoding='utf-8') as f:
        json.dump(scraper_config, f, indent=2, ensure_ascii=False)
    
    logger.info("📄 scraper_config.json creado")
    logger.info("✅ Archivos de configuración creados")

def setup_complete_check():
    """Verificación final de que todo está listo"""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Verificación final del setup...")
    
    checks = [
        ("Archivos CSV en URLs/", check_urls_files()),
        ("Dependencias Python", check_dependencies()),
        ("Scrapers", check_scrapers()),
        ("Registry", initialize_registry())
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    logger.info("\n" + "="*60)
    logger.info("📋 RESUMEN DE VERIFICACIONES")
    logger.info("="*60)
    
    for check_name, result in checks:
        status = "✅ OK" if result else "❌ FALLO"
        logger.info(f"{status:8} {check_name}")
        if result:
            passed_checks += 1
    
    logger.info("="*60)
    logger.info(f"🎯 Resultado: {passed_checks}/{total_checks} verificaciones exitosas")
    
    if passed_checks == total_checks:
        logger.info("🎉 ¡Setup completado exitosamente!")
        logger.info("\n📝 Próximos pasos:")
        logger.info("1. Ejecutar test de integración: python test_integration.py")
        logger.info("2. Ejecutar orquestador: python orchestrator/advanced_orchestrator.py")
        logger.info("3. Monitorear logs en: logs/")
        return True
    else:
        logger.warning("⚠️ Setup incompleto. Resolver los fallos antes de continuar.")
        return False

def main():
    """Función principal del setup"""
    print("🚀 PropertyScraper Dell710 - Setup Inicial")
    print("="*60)
    
    logger = setup_logging()
    
    logger.info("🔧 Iniciando configuración inicial del sistema...")
    
    # Crear estructura de directorios
    create_directory_structure()
    
    # Crear archivos de configuración
    create_config_files()
    
    # Verificación completa
    success = setup_complete_check()
    
    if success:
        logger.info("\n✅ Sistema listo para usar!")
        return 0
    else:
        logger.error("\n❌ Setup incompleto")
        return 1

if __name__ == "__main__":
    sys.exit(main())
