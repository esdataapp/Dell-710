#!/usr/bin/env python3
"""
Test de Orquestación - Windows 11
Prueba específica para Windows con múltiples scrapers por página web
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Configurar path del proyecto
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def setup_logging():
    """Configurar logging para el test"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = project_root / 'logs' / f'test_orquestacion_windows_{timestamp}.log'
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

def create_test_csv():
    """Crear un CSV de prueba con URLs limitadas para testing"""
    logger = logging.getLogger(__name__)
    logger.info("📄 Creando CSV de prueba...")
    
    test_urls = [
        # Inmuebles24 - 3 URLs
        {
            'PaginaWeb': 'Inmuebles24',
            'Estado': 'Jalisco',
            'Ciudad': 'Zapopan',
            'Operación': 'Venta',
            'ProductoPaginaWeb': 'Departamentos',
            'URL': 'https://www.inmuebles24.com/departamentos-en-venta-en-zapopan-jalisco.html'
        },
        {
            'PaginaWeb': 'Inmuebles24',
            'Estado': 'Jalisco',
            'Ciudad': 'Zapopan',
            'Operación': 'Venta',
            'ProductoPaginaWeb': 'Casas',
            'URL': 'https://www.inmuebles24.com/casas-en-venta-en-zapopan-jalisco.html'
        },
        {
            'PaginaWeb': 'Inmuebles24',
            'Estado': 'Jalisco',
            'Ciudad': 'Guadalajara',
            'Operación': 'Renta',
            'ProductoPaginaWeb': 'Departamentos',
            'URL': 'https://www.inmuebles24.com/departamentos-en-renta-en-guadalajara-jalisco.html'
        },
        
        # Casas y Terrenos - 2 URLs
        {
            'PaginaWeb': 'Casas_y_terrenos',
            'Estado': 'Jalisco',
            'Ciudad': 'Zapopan',
            'Operación': 'Venta',
            'ProductoPaginaWeb': 'Casas',
            'URL': 'https://www.casasyterrenos.com/inmuebles/venta/casas/jalisco/zapopan'
        },
        {
            'PaginaWeb': 'Casas_y_terrenos',
            'Estado': 'Jalisco',
            'Ciudad': 'Guadalajara',
            'Operación': 'Venta',
            'ProductoPaginaWeb': 'Departamentos',
            'URL': 'https://www.casasyterrenos.com/inmuebles/venta/departamentos/jalisco/guadalajara'
        },
        
        # Mitula - 2 URLs
        {
            'PaginaWeb': 'mitula',
            'Estado': 'Jalisco',
            'Ciudad': 'Zapopan',
            'Operación': 'Venta',
            'ProductoPaginaWeb': 'Casas',
            'URL': 'https://casas.mitula.mx/casas/venta-zapopan-jalisco'
        },
        {
            'PaginaWeb': 'mitula',
            'Estado': 'Jalisco',
            'Ciudad': 'Guadalajara',
            'Operación': 'Venta',
            'ProductoPaginaWeb': 'Departamentos',
            'URL': 'https://departamentos.mitula.mx/departamentos/venta-guadalajara-jalisco'
        }
    ]
    
    # Guardar CSV de prueba
    test_csv_path = project_root / 'Lista_de_URLs_TEST.csv'
    
    import csv
    with open(test_csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['PaginaWeb', 'Estado', 'Ciudad', 'Operación', 'ProductoPaginaWeb', 'URL']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_urls)
    
    logger.info(f"✅ CSV de prueba creado: {test_csv_path}")
    logger.info(f"📊 Total URLs de prueba: {len(test_urls)}")
    
    return test_csv_path

def test_single_scraper(website: str, url: str, output_dir: Path, max_pages: int = 20):
    """Probar un scraper individual"""
    logger = logging.getLogger(__name__)
    
    try:
        # Crear directorio de salida
        output_dir.mkdir(exist_ok=True, parents=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'{website}_test_{timestamp}.csv'
        
        logger.info(f"🚀 Iniciando test scraper: {website}")
        logger.info(f"   URL: {url}")
        logger.info(f"   Páginas: {max_pages}")
        logger.info(f"   Salida: {output_file}")
        
        # Importar y ejecutar scraper según el website
        if website.lower() == 'inmuebles24':
            from scrapers.inmuebles24_professional import run_scraper
        elif website.lower() == 'casas_y_terrenos':
            from scrapers.casas_terrenos_professional import run_scraper
        elif website.lower() == 'mitula':
            from scrapers.mitula_professional import run_scraper
        else:
            logger.error(f"❌ Scraper no disponible para: {website}")
            return {'success': False, 'error': f'Scraper no disponible para {website}'}
        
        # Ejecutar scraper
        start_time = datetime.now()
        result = run_scraper(url, str(output_file), max_pages=max_pages)
        end_time = datetime.now()
        
        execution_time = (end_time - start_time).total_seconds() / 60
        
        if result.get('success', False):
            logger.info(f"✅ Test {website} completado exitosamente")
            logger.info(f"   Propiedades encontradas: {result.get('properties_found', 0)}")
            logger.info(f"   Páginas procesadas: {result.get('pages_processed', 0)}")
            logger.info(f"   Tiempo ejecución: {execution_time:.2f} minutos")
            
            # Verificar que el archivo se creó
            if output_file.exists():
                file_size = output_file.stat().st_size
                logger.info(f"   Archivo CSV: {file_size} bytes")
            
            return {
                'success': True,
                'website': website,
                'properties_found': result.get('properties_found', 0),
                'pages_processed': result.get('pages_processed', 0),
                'execution_time_minutes': execution_time,
                'output_file': str(output_file)
            }
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"❌ Test {website} falló: {error_msg}")
            return {
                'success': False,
                'website': website,
                'error': error_msg,
                'execution_time_minutes': execution_time
            }
            
    except ImportError as e:
        logger.error(f"❌ Error importando scraper {website}: {e}")
        return {'success': False, 'website': website, 'error': f'Import error: {e}'}
    except Exception as e:
        logger.error(f"❌ Error ejecutando test {website}: {e}")
        return {'success': False, 'website': website, 'error': str(e)}

def test_registry_integration():
    """Probar la integración con el registry"""
    logger = logging.getLogger(__name__)
    logger.info("🧪 Probando integración con EnhancedScrapsRegistry...")
    
    try:
        # Importar registry
        sys.path.append(str(project_root / 'utils'))
        from enhanced_scraps_registry import EnhancedScrapsRegistry
        
        # Crear registry temporal para pruebas
        registry = EnhancedScrapsRegistry()
        
        # Cargar URLs de prueba 
        test_csv_path = create_test_csv()
        
        # Temporalmente cambiar el path del CSV para la prueba
        original_csv_path = registry.csv_file
        registry.csv_file = test_csv_path
        
        # Cargar URLs del CSV de prueba
        urls = registry.load_urls_from_csv()
        logger.info(f"✅ URLs cargadas desde CSV de prueba: {len(urls)}")
        
        # Obtener estadísticas
        stats = registry.get_registry_stats()
        logger.info(f"📊 Estadísticas del registry:")
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")
        
        # Obtener próximos scraps para testing
        next_scraps = registry.get_next_scraps_to_run(10)
        logger.info(f"⏭️ Próximos scraps disponibles: {len(next_scraps)}")
        
        # Mostrar algunos ejemplos
        for i, scrap in enumerate(next_scraps[:3]):
            logger.info(f"📋 Scrap {i+1}: {scrap['website']} - {scrap['product']}")
        
        # Restaurar path original
        registry.csv_file = original_csv_path
        
        logger.info("✅ Test de registry completado")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en test registry: {e}")
        return False

def run_orchestration_test():
    """Ejecutar prueba completa de orquestación"""
    logger = logging.getLogger(__name__)
    
    logger.info("🎛️ INICIANDO PRUEBA DE ORQUESTACIÓN WINDOWS 11")
    logger.info("="*80)
    
    # Crear estructura de directorios para pruebas
    test_data_dir = project_root / 'data' / 'test_windows'
    test_data_dir.mkdir(exist_ok=True, parents=True)
    
    # Test 1: Registry Integration
    logger.info("\n📋 Test 1: Registry Integration")
    logger.info("-" * 50)
    registry_ok = test_registry_integration()
    
    # Test 2: Scrapers Individuales
    logger.info("\n🤖 Test 2: Scrapers Individuales")
    logger.info("-" * 50)
    
    # URLs de prueba específicas por website
    test_scenarios = [
        {
            'website': 'Inmuebles24',
            'url': 'https://www.inmuebles24.com/departamentos-en-venta-en-zapopan-jalisco.html',
            'max_pages': 20
        },
        {
            'website': 'Casas_y_terrenos', 
            'url': 'https://www.casasyterrenos.com/inmuebles/venta/casas/jalisco/zapopan',
            'max_pages': 20
        },
        {
            'website': 'mitula',
            'url': 'https://casas.mitula.mx/casas/venta-zapopan-jalisco',
            'max_pages': 20
        }
    ]
    
    results = []
    threads = []
    
    # Ejecutar scrapers en paralelo (simulando orquestación)
    for scenario in test_scenarios:
        output_dir = test_data_dir / scenario['website']
        
        # Crear hilo para cada scraper
        thread = threading.Thread(
            target=lambda s=scenario, od=output_dir: results.append(
                test_single_scraper(s['website'], s['url'], od, s['max_pages'])
            ),
            daemon=True
        )
        
        threads.append(thread)
        thread.start()
        
        logger.info(f"🚀 Hilo iniciado para {scenario['website']}")
        
        # Pequeña pausa entre inicios para evitar sobrecarga
        time.sleep(5)
    
    # Esperar a que terminen todos los hilos
    logger.info("\n⏳ Esperando resultados de todos los scrapers...")
    
    for i, thread in enumerate(threads):
        thread.join(timeout=1800)  # 30 minutos máximo por scraper
        if thread.is_alive():
            logger.warning(f"⚠️ Scraper {i+1} aún ejecutándose después de 30 minutos")
        else:
            logger.info(f"✅ Scraper {i+1} completado")
    
    # Analizar resultados
    logger.info("\n📊 ANÁLISIS DE RESULTADOS")
    logger.info("="*80)
    
    successful_scrapers = 0
    total_properties = 0
    total_time = 0
    
    for result in results:
        if result:
            website = result.get('website', 'Unknown')
            success = result.get('success', False)
            properties = result.get('properties_found', 0)
            exec_time = result.get('execution_time_minutes', 0)
            
            status = "✅ ÉXITO" if success else "❌ FALLO"
            logger.info(f"{status:8} {website:15} | Props: {properties:4d} | Tiempo: {exec_time:6.2f}min")
            
            if success:
                successful_scrapers += 1
                total_properties += properties
                total_time += exec_time
    
    # Resumen final
    logger.info("="*80)
    logger.info("🎯 RESUMEN FINAL")
    logger.info(f"✅ Scrapers exitosos: {successful_scrapers}/{len(test_scenarios)}")
    logger.info(f"🏠 Total propiedades: {total_properties:,}")
    logger.info(f"⏱️ Tiempo total: {total_time:.2f} minutos")
    
    if successful_scrapers > 0:
        avg_time = total_time / successful_scrapers
        avg_properties = total_properties / successful_scrapers
        logger.info(f"📈 Promedio por scraper: {avg_properties:.1f} props, {avg_time:.2f} min")
    
    # Verificar archivos generados
    logger.info("\n📁 Archivos generados:")
    for website_dir in test_data_dir.iterdir():
        if website_dir.is_dir():
            csv_files = list(website_dir.glob('*.csv'))
            logger.info(f"   {website_dir.name}: {len(csv_files)} archivos CSV")
            for csv_file in csv_files:
                size_kb = csv_file.stat().st_size / 1024
                logger.info(f"     - {csv_file.name} ({size_kb:.1f} KB)")
    
    # Evaluación final
    success_rate = (successful_scrapers / len(test_scenarios)) * 100
    logger.info(f"\n🎉 Tasa de éxito: {success_rate:.1f}%")
    
    if success_rate >= 80:
        logger.info("🎉 ¡Prueba de orquestación EXITOSA!")
        logger.info("✅ Sistema listo para ejecución en producción")
    elif success_rate >= 50:
        logger.info("⚠️ Prueba PARCIALMENTE exitosa")
        logger.info("🔧 Revisar scrapers fallidos antes de producción")
    else:
        logger.error("❌ Prueba FALLIDA")
        logger.error("🚨 Revisar configuración antes de continuar")
    
    return success_rate >= 80

def main():
    """Función principal"""
    logger = setup_logging()
    
    logger.info("🪟 PropertyScraper Dell710 - Test Orquestación Windows 11")
    logger.info(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"💻 Directorio: {project_root}")
    logger.info("="*80)
    
    try:
        # Verificar que estamos en Windows
        if os.name != 'nt':
            logger.warning("⚠️ Este script está optimizado para Windows 11")
        
        # Ejecutar prueba completa
        success = run_orchestration_test()
        
        logger.info("\n🏁 Test de orquestación completado")
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("⏹️ Prueba interrumpida por usuario")
        return 1
    except Exception as e:
        logger.error(f"❌ Error fatal en prueba: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
