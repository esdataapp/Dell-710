#!/usr/bin/env python3
"""
Test Script para PropertyScraper Dell710
Prueba la integración completa con Lista de URLs.csv
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Agregar path del proyecto
sys.path.append(str(Path(__file__).parent))

def setup_logging():
    """Configurar logging para test"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = Path('logs') / f'test_integration_{timestamp}.log'
    log_file.parent.mkdir(exist_ok=True, parents=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)8s | TEST | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def test_enhanced_registry():
    """Test del EnhancedScrapsRegistry"""
    logger = logging.getLogger(__name__)
    logger.info("🧪 Testing EnhancedScrapsRegistry...")
    
    try:
        from utils.enhanced_scraps_registry import EnhancedScrapsRegistry
        
        registry = EnhancedScrapsRegistry()
        
        # Test cargar URLs desde CSV
        logger.info("📄 Probando carga de URLs desde CSV...")
        urls = registry.load_urls_from_csv()
        logger.info(f"✅ URLs cargadas: {len(urls)}")
        
        # Test estadísticas
        stats = registry.get_registry_stats()
        logger.info(f"📊 Estadísticas del registry: {stats}")
        
        # Test obtener próximos scraps
        next_scraps = registry.get_next_scraps_to_run(10)
        logger.info(f"⏭️ Próximos scraps: {len(next_scraps)}")

        if next_scraps:
            sample_scrap = next_scraps[0]
            logger.info(f"🎯 Ejemplo scrap: {sample_scrap['website']} - {sample_scrap['url']}")

            # Test ruta de salida
            output_path = registry.get_output_path(sample_scrap)
            logger.info(f"📁 Ruta salida: {output_path}")
        
        logger.info("✅ EnhancedScrapsRegistry test exitoso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test EnhancedScrapsRegistry: {e}")
        return False

def test_scrapers():
    """Test de scrapers individuales"""
    logger = logging.getLogger(__name__)
    logger.info("🧪 Testing scrapers individuales...")
    
    # Test URLs de ejemplo
    test_urls = {
        'inmuebles24': 'https://www.inmuebles24.com/departamentos-en-venta-en-zapopan-jalisco.html',
        'casas_y_terrenos': 'https://www.casasyterrenos.com/inmuebles/venta/departamentos/jalisco/zapopan',
        'mitula': 'https://casas.mitula.mx/casas/venta-zapopan-jalisco'
    }
    
    # Test directorio de salida
    test_output_dir = Path('data/test_output')
    test_output_dir.mkdir(exist_ok=True, parents=True)
    
    for website, url in test_urls.items():
        try:
            logger.info(f"🧪 Testing scraper {website}...")
            
            # Importar scraper específico
            if website == 'inmuebles24':
                from scrapers.inm24 import run_scraper
            elif website == 'casas_y_terrenos':
                from scrapers.cyt import run_scraper
            elif website == 'mitula':
                from scrapers.mit import run_scraper
            else:
                logger.warning(f"⚠️ Scraper {website} no implementado")
                continue
            
            # Test con límite de 1 página
            output_file = test_output_dir / f'{website}_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            logger.info(f"🚀 Ejecutando test scraper {website} con 1 página...")
            result = run_scraper(url, str(output_file), max_pages=1)
            
            if result.get('success', False):
                logger.info(f"✅ Test {website} exitoso: {result.get('properties_found', 0)} propiedades")
            else:
                logger.error(f"❌ Test {website} falló: {result.get('error', 'Error desconocido')}")
            
        except ImportError as e:
            logger.warning(f"⚠️ No se pudo importar scraper {website}: {e}")
        except Exception as e:
            logger.error(f"❌ Error en test scraper {website}: {e}")
    
    logger.info("🏁 Test de scrapers completado")

def test_orchestrator():
    """Test del orquestador"""
    logger = logging.getLogger(__name__)
    logger.info("🧪 Testing Advanced Orchestrator...")
    
    try:
        from orchestrator.advanced_orchestrator import AdvancedOrchestrator
        
        orchestrator = AdvancedOrchestrator()
        
        # Test obtener siguiente website
        next_website = orchestrator.get_next_website_to_process()
        if next_website:
            logger.info(f"📱 Siguiente website: {next_website}")
            
            # Test obtener scraps para website
            scraps = orchestrator.get_scraps_for_website(next_website)
            logger.info(f"📋 Scraps para {next_website}: {len(scraps)}")
        else:
            logger.info("📝 No hay websites pendientes")
        
        # Test verificar recursos
        resources_ok = orchestrator.check_system_resources()
        logger.info(f"🖥️ Recursos del sistema: {'OK' if resources_ok else 'LIMITADOS'}")
        
        logger.info("✅ Advanced Orchestrator test exitoso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test Advanced Orchestrator: {e}")
        return False

def test_csv_structure():
    """Test de la estructura del CSV"""
    logger = logging.getLogger(__name__)
    logger.info("🧪 Testing estructura Lista de URLs.csv...")
    
    try:
        csv_path = Path('config') / 'Lista de URLs.csv'
        if not csv_path.exists():
            logger.error("❌ Lista de URLs.csv no encontrada")
            return False
        
        import csv
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        logger.info(f"📄 Total filas en CSV: {len(rows)}")
        
        # Verificar columnas requeridas
        required_columns = ['PaginaWeb', 'Estado', 'Ciudad', 'Operación', 'ProductoPaginaWeb', 'URL']
        if rows:
            available_columns = list(rows[0].keys())
            missing_columns = [col for col in required_columns if col not in available_columns]
            
            if missing_columns:
                logger.error(f"❌ Columnas faltantes: {missing_columns}")
                return False
            else:
                logger.info("✅ Todas las columnas requeridas presentes")
        
        # Estadísticas por website
        websites = {}
        for row in rows:
            website = row['PaginaWeb']
            if website not in websites:
                websites[website] = 0
            websites[website] += 1
        
        logger.info("📊 URLs por website:")
        for website, count in websites.items():
            logger.info(f"   {website}: {count} URLs")
        
        logger.info("✅ Estructura CSV test exitoso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test estructura CSV: {e}")
        return False

def run_integration_test():
    """Ejecutar test de integración completo"""
    logger = setup_logging()
    
    logger.info("🚀 Iniciando test de integración PropertyScraper Dell710")
    logger.info("="*80)
    
    tests = [
        ("Estructura CSV", test_csv_structure),
        ("Enhanced Registry", test_enhanced_registry),
        ("Scrapers", test_scrapers),
        ("Orchestrator", test_orchestrator)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Ejecutando test: {test_name}")
        logger.info("-" * 50)
        
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"❌ Error fatal en {test_name}: {e}")
            results[test_name] = False
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("📊 RESUMEN DE TESTS")
    logger.info("="*80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Resultado final: {passed}/{total} tests exitosos")
    
    if passed == total:
        logger.info("🎉 ¡Todos los tests pasaron! Sistema listo para producción.")
    else:
        logger.warning("⚠️ Algunos tests fallaron. Revisar errores antes de ejecutar en producción.")
    
    return passed == total

if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)
