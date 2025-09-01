#!/usr/bin/env python3
"""
Concurrent Scraper Manager - PropertyScraper Dell710
Gestiona múltiples scrapers concurrentes optimizados para Dell T710
"""

import os
import sys
import json
import time
import threading
import multiprocessing
import queue
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
import argparse
import importlib

# Import de scrapers
sys.path.append(str(Path(__file__).parent.parent / 'scrapers'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

SCRAPER_MAP = {
    "inm24": ("inm24", "Inmuebles24ProfessionalScraper"),
    "inm24_det": ("inm24_det", "Inmuebles24UnicoProfessionalScraper"),
    "lam": ("lam", "LamudiProfessionalScraper"),
    "lam_det": ("lam_det", "LamudiUnicoProfessionalScraper"),
    "cyt": ("cyt", "CasasTerrenosProfessionalScraper"),
    "mit": ("mit", "MitulaProfessionalScraper"),
    "prop": ("prop", "PropiedadesProfessionalScraper"),
    "tro": ("tro", "TrovitProfessionalScraper"),
}

SCRAPER_CLASSES = {
    key: getattr(importlib.import_module(mod), cls)
    for key, (mod, cls) in SCRAPER_MAP.items()
}

from gdrive_backup_manager import GoogleDriveBackupManager

class DellT710ResourceMonitor:
    """Monitor de recursos específico para Dell T710"""
    
    def __init__(self):
        # Especificaciones Dell T710
        self.total_cores = 8  # Intel Xeon E5620
        self.total_memory_gb = 24  # 24GB DDR3 ECC
        self.max_cpu_usage = 80  # Máximo 80% de uso
        self.max_memory_usage = 80  # Máximo 80% de memoria
        
        # Recursos disponibles para scraping
        self.available_cores = int(self.total_cores * (self.max_cpu_usage / 100))  # 6.4 cores
        self.available_memory_gb = int(self.total_memory_gb * (self.max_memory_usage / 100))  # 19.2 GB
        
        self.logger = logging.getLogger(__name__)
    
    def get_current_usage(self) -> Dict:
        """Obtener uso actual de recursos"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'memory_available_gb': memory.available / (1024**3),
            'processes_count': len(psutil.pids())
        }
    
    def can_start_new_process(self, estimated_cpu_per_process=15, estimated_memory_gb=3) -> bool:
        """Verificar si se puede iniciar un nuevo proceso de scraping"""
        current = self.get_current_usage()
        
        # Verificar CPU
        projected_cpu = current['cpu_percent'] + estimated_cpu_per_process
        if projected_cpu > self.max_cpu_usage:
            self.logger.warning(f"⚠️  CPU limit reached: {projected_cpu:.1f}% > {self.max_cpu_usage}%")
            return False
        
        # Verificar memoria
        projected_memory_gb = current['memory_used_gb'] + estimated_memory_gb
        if projected_memory_gb > self.available_memory_gb:
            self.logger.warning(f"⚠️  Memory limit reached: {projected_memory_gb:.1f}GB > {self.available_memory_gb}GB")
            return False
        
        return True
    
    def get_optimal_concurrent_scrapers(self) -> int:
        """Calcular número óptimo de scrapers concurrentes"""
        # Basado en CPU: cada scraper usa ~15% CPU
        cpu_based = int(self.max_cpu_usage / 15)
        
        # Basado en memoria: cada scraper usa ~3GB
        memory_based = int(self.available_memory_gb / 3)
        
        # Tomar el menor para ser conservador
        optimal = min(cpu_based, memory_based, 4)  # Máximo 4 scrapers
        
        self.logger.info(f"🧮 Calculando scrapers concurrentes óptimos:")
        self.logger.info(f"   CPU-based: {cpu_based}")
        self.logger.info(f"   Memory-based: {memory_based}")
        self.logger.info(f"   Optimal: {optimal}")
        
        return max(1, optimal)

class ConcurrentScraperManager:
    """
    Gestor de scrapers concurrentes optimizado para Dell T710
    """
    
    def __init__(self, max_concurrent=None):
        self.setup_logging()
        
        # Monitor de recursos Dell T710
        self.resource_monitor = DellT710ResourceMonitor()
        
        # Configuración de concurrencia
        self.max_concurrent = max_concurrent or self.resource_monitor.get_optimal_concurrent_scrapers()
        
        # Google Drive Backup Manager
        self.backup_manager = None
        try:
            self.backup_manager = GoogleDriveBackupManager()
            self.logger.info("☁️  Google Drive Backup habilitado")
        except Exception as e:
            self.logger.warning(f"⚠️  Google Drive Backup no disponible: {e}")
        
        # Estado del manager
        self.active_scrapers = {}
        self.completed_scrapers = {}
        self.failed_scrapers = {}
        self.scraper_queue = queue.Queue()
        self.task_dependencies = {}
        
        # Threading
        self.manager_thread = None
        self.monitoring_thread = None
        self.shutdown_event = threading.Event()
        
        # Configuración de paths
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / 'logs'
        self.logs_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"🚀 Concurrent Scraper Manager iniciado")
        self.logger.info(f"   Max concurrent scrapers: {self.max_concurrent}")
        self.logger.info(f"   Available cores: {self.resource_monitor.available_cores}")
        self.logger.info(f"   Available memory: {self.resource_monitor.available_memory_gb:.1f}GB")
    
    def setup_logging(self):
        """Configurar logging del manager"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(__file__).parent.parent / 'logs' / f"concurrent_manager_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.log_file = log_file
    
    def add_scraper_task(self, scraper_config: Dict):
        """Agregar tarea de scraping a la cola"""
        task_id = f"{scraper_config['site']}_{scraper_config['operation']}_{datetime.now().strftime('%H%M%S')}"
        
        task = {
            'id': task_id,
            'config': scraper_config,
            'added_at': datetime.now(),
            'priority': scraper_config.get('priority', 1)
        }
        
        self.scraper_queue.put(task)
        self.logger.info(f"➕ Tarea agregada: {task_id}")
        
        return task_id
    
    def run_scraper_process(self, task: Dict) -> Dict:
        """Ejecutar un scraper en proceso separado"""
        task_id = task['id']
        config = task['config']
        
        try:
            self.logger.info(f"🚀 Iniciando scraper: {task_id}")
            site = config['site']

            # Configurar scraper basado en el sitio
            if site in ('inmuebles24', 'inm24'):
                scraper_cls = SCRAPER_CLASSES['inm24']
                scraper = scraper_cls(
                    headless=config.get('headless', True),
                    max_pages=config.get('max_pages'),
                    operation_type=config.get('operation', 'venta'),
                    city=config.get('city'),
                    product=config.get('product')
                )

            elif site in ('inmuebles24_det', 'inm24_det'):
                scraper_cls = SCRAPER_CLASSES['inm24_det']
                scraper = scraper_cls(
                    urls_file=config.get('urls_file'),
                    headless=config.get('headless', True),
                    max_properties=config.get('max_properties'),
                    operation_type=config.get('operation', 'venta'),
                    city=config.get('city'),
                    product=config.get('product')
                )

            elif site in ('lamudi', 'lam'):
                scraper_cls = SCRAPER_CLASSES['lam']
                scraper = scraper_cls(
                    headless=config.get('headless', True),
                    max_pages=config.get('max_pages'),
                    resume_from=config.get('resume_from'),
                    operation_type=config.get('operation', 'venta'),
                    city=config.get('city'),
                    product=config.get('product')
                )

            elif site in ('lamudi_det', 'lam_det'):
                scraper_cls = SCRAPER_CLASSES['lam_det']
                scraper = scraper_cls(
                    urls_file=config.get('urls_file'),
                    headless=config.get('headless', True),
                    max_properties=config.get('max_properties'),
                    operation_type=config.get('operation', 'venta'),
                    city=config.get('city'),
                    product=config.get('product')
                )

            elif site in ('casas_y_terrenos', 'cyt'):
                scraper_cls = SCRAPER_CLASSES['cyt']
                scraper = scraper_cls(
                    headless=config.get('headless', True),
                    max_pages=config.get('max_pages'),
                    operation_type=config.get('operation', 'venta')
                )

            elif site in ('mitula', 'mit'):
                scraper_cls = SCRAPER_CLASSES['mit']
                scraper = scraper_cls(
                    url=config.get('url'),
                    headless=config.get('headless', True),
                    max_pages=config.get('max_pages'),
                    resume_from=config.get('resume_from'),
                    operation_type=config.get('operation', 'venta')
                )

            elif site in ('propiedades', 'prop'):
                scraper_cls = SCRAPER_CLASSES['prop']
                scraper = scraper_cls(
                    headless=config.get('headless', True),
                    max_pages=config.get('max_pages'),
                    resume_from=config.get('resume_from'),
                    operation_type=config.get('operation', 'venta')
                )

            elif site in ('trovit', 'tro'):
                scraper_cls = SCRAPER_CLASSES['tro']
                scraper = scraper_cls(
                    url=config.get('url'),
                    headless=config.get('headless', True),
                    max_pages=config.get('max_pages'),
                    resume_from=config.get('resume_from'),
                    operation_type=config.get('operation', 'venta')
                )

            else:
                raise ValueError(f"Sitio no soportado: {site}")

            # Ejecutar scraper
            result = scraper.run()
            result['task_id'] = task_id
            result['site'] = site
            if result.get('csv_file'):
                self.logger.info(f"📄 CSV generado por {task_id}: {result['csv_file']}")
            
            # Iniciar respaldo en background si fue exitoso
            if result.get('success', False) and self.backup_manager:
                try:
                    self.logger.info(f"☁️  Iniciando respaldo de {config['site']} en background...")
                    backup_result = self.backup_manager.run_backup_now()
                    
                    if backup_result.get('success', False):
                        self.logger.info(f"✅ Respaldo completado para {config['site']}")
                        result['backup_success'] = True
                    else:
                        self.logger.warning(f"⚠️  Respaldo falló para {config['site']}: {backup_result.get('error', 'Unknown')}")
                        result['backup_success'] = False
                        
                except Exception as e:
                    self.logger.warning(f"⚠️  Error en respaldo automático: {e}")
                    result['backup_success'] = False
            
            return result
                
        except Exception as e:
            self.logger.error(f"❌ Error en scraper {task_id}: {e}")
            return {
                'task_id': task_id,
                'site': config['site'],
                'success': False,
                'error': str(e)
            }
    
    def monitor_resources(self):
        """Monitorear recursos del sistema en tiempo real"""
        while not self.shutdown_event.is_set():
            try:
                usage = self.resource_monitor.get_current_usage()
                
                # Log cada 5 minutos
                if datetime.now().minute % 5 == 0 and datetime.now().second < 5:
                    self.logger.info(f"📊 Recursos Dell T710:")
                    self.logger.info(f"   CPU: {usage['cpu_percent']:.1f}%")
                    self.logger.info(f"   Memory: {usage['memory_percent']:.1f}% ({usage['memory_used_gb']:.1f}GB)")
                    self.logger.info(f"   Active scrapers: {len(self.active_scrapers)}")
                
                # Verificar alertas
                if usage['cpu_percent'] > 85:
                    self.logger.warning(f"⚠️  CPU alta: {usage['cpu_percent']:.1f}%")
                
                if usage['memory_percent'] > 85:
                    self.logger.warning(f"⚠️  Memoria alta: {usage['memory_percent']:.1f}%")
                
                time.sleep(30)  # Monitorear cada 30 segundos
                
            except Exception as e:
                self.logger.error(f"❌ Error en monitoring: {e}")
                time.sleep(60)
    
    def manage_scrapers(self):
        """Gestionar scrapers concurrentes"""
        while not self.shutdown_event.is_set():
            try:
                # Limpiar scrapers completados
                completed_ids = []
                for scraper_id, thread_info in self.active_scrapers.items():
                    if not thread_info['thread'].is_alive():
                        completed_ids.append(scraper_id)
                
                for scraper_id in completed_ids:
                    thread_info = self.active_scrapers.pop(scraper_id)
                    
                    # Obtener resultado
                    if hasattr(thread_info['thread'], 'result'):
                        result = thread_info['thread'].result
                        if result.get('success', False):
                            self.completed_scrapers[scraper_id] = result
                            self.logger.info(f"✅ Scraper completado: {scraper_id}")

                            # Programar scraper dependiente si aplica
                            urls_file = result.get('urls_file')
                            site = thread_info['task']['config']['site']
                            if urls_file and site in ('inmuebles24', 'inm24', 'lamudi', 'lam'):
                                detail_site = 'inm24_det' if site in ('inmuebles24', 'inm24') else 'lam_det'
                                detail_config = {
                                    'site': detail_site,
                                    'operation': thread_info['task']['config'].get('operation'),
                                    'city': result.get('city') or thread_info['task']['config'].get('city'),
                                    'product': result.get('product') or thread_info['task']['config'].get('product'),
                                    'urls_file': urls_file,
                                    'headless': thread_info['task']['config'].get('headless', True),
                                    'priority': thread_info['task']['config'].get('priority', 1)
                                }
                                new_task_id = self.add_scraper_task(detail_config)
                                self.task_dependencies[new_task_id] = {
                                    'depends_on': scraper_id,
                                    'csv_file': urls_file
                                }
                                self.logger.info(
                                    f"🔁 Scraper dependiente programado: {new_task_id} -> {scraper_id} ({urls_file})")
                        else:
                            self.failed_scrapers[scraper_id] = result
                            self.logger.error(f"❌ Scraper falló: {scraper_id}")
                
                # Iniciar nuevos scrapers si hay espacio y recursos
                while (len(self.active_scrapers) < self.max_concurrent and 
                       not self.scraper_queue.empty() and
                       self.resource_monitor.can_start_new_process()):
                    
                    try:
                        task = self.scraper_queue.get_nowait()
                        
                        # Crear thread para el scraper
                        def run_with_result(task):
                            thread = threading.current_thread()
                            thread.result = self.run_scraper_process(task)
                        
                        thread = threading.Thread(
                            target=run_with_result,
                            args=(task,),
                            name=f"Scraper-{task['id']}"
                        )
                        
                        # Iniciar thread
                        thread.start()
                        
                        # Registrar scraper activo
                        self.active_scrapers[task['id']] = {
                            'thread': thread,
                            'task': task,
                            'started_at': datetime.now()
                        }
                        
                        self.logger.info(f"🟢 Scraper iniciado: {task['id']}")
                        
                    except queue.Empty:
                        break
                    except Exception as e:
                        self.logger.error(f"❌ Error iniciando scraper: {e}")
                
                time.sleep(10)  # Verificar cada 10 segundos
                
            except Exception as e:
                self.logger.error(f"❌ Error en manage_scrapers: {e}")
                time.sleep(30)
    
    def start(self):
        """Iniciar el manager de scrapers"""
        self.logger.info("🚀 Iniciando Concurrent Scraper Manager...")
        
        # Iniciar thread de monitoreo de recursos
        self.monitoring_thread = threading.Thread(
            target=self.monitor_resources,
            name="ResourceMonitor"
        )
        self.monitoring_thread.start()
        
        # Iniciar thread de gestión de scrapers
        self.manager_thread = threading.Thread(
            target=self.manage_scrapers,
            name="ScraperManager"
        )
        self.manager_thread.start()
        
        self.logger.info("✅ Manager iniciado exitosamente")
    
    def stop(self):
        """Detener el manager de scrapers"""
        self.logger.info("⏹️  Deteniendo Concurrent Scraper Manager...")
        
        # Señalar shutdown
        self.shutdown_event.set()
        
        # Esperar a que terminen los scrapers activos
        for scraper_id, thread_info in self.active_scrapers.items():
            self.logger.info(f"⏳ Esperando scraper: {scraper_id}")
            thread_info['thread'].join(timeout=30)
        
        # Esperar threads del manager
        if self.manager_thread:
            self.manager_thread.join(timeout=10)
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        self.logger.info("✅ Manager detenido exitosamente")
    
    def get_status(self) -> Dict:
        """Obtener estado actual del manager"""
        resources = self.resource_monitor.get_current_usage()
        
        return {
            'active_scrapers': len(self.active_scrapers),
            'completed_scrapers': len(self.completed_scrapers),
            'failed_scrapers': len(self.failed_scrapers),
            'queue_size': self.scraper_queue.qsize(),
            'max_concurrent': self.max_concurrent,
            'resources': resources,
            'uptime_seconds': (datetime.now() - datetime.now()).total_seconds() if hasattr(self, 'start_time') else 0
        }
    
    def run_batch_scraping(self, scraper_configs: List[Dict]) -> Dict:
        """Ejecutar lote de scrapers y esperar resultados"""
        self.logger.info(f"🎯 Iniciando batch scraping con {len(scraper_configs)} scrapers")
        
        # Agregar todas las tareas
        task_ids = []
        for config in scraper_configs:
            task_id = self.add_scraper_task(config)
            task_ids.append(task_id)
        
        # Iniciar manager
        self.start()
        
        try:
            # Esperar a que todas las tareas se completen
            while True:
                total_completed = len(self.completed_scrapers) + len(self.failed_scrapers)
                
                if total_completed >= len(task_ids):
                    self.logger.info("🏁 Todas las tareas completadas")
                    break
                
                # Log de progreso cada minuto
                if datetime.now().second == 0:
                    self.logger.info(f"📊 Progreso: {total_completed}/{len(task_ids)} completadas")
                
                time.sleep(10)
            
            # Recopilar resultados
            results = {
                'total_tasks': len(task_ids),
                'completed': len(self.completed_scrapers),
                'failed': len(self.failed_scrapers),
                'success_rate': (len(self.completed_scrapers) / len(task_ids)) * 100,
                'results': {
                    'completed': dict(self.completed_scrapers),
                    'failed': dict(self.failed_scrapers)
                }
            }
            
            self.logger.info(f"📊 Batch scraping completado:")
            self.logger.info(f"   Total: {results['total_tasks']}")
            self.logger.info(f"   Completados: {results['completed']}")
            self.logger.info(f"   Fallidos: {results['failed']}")
            self.logger.info(f"   Tasa de éxito: {results['success_rate']:.1f}%")
            
            return results
            
        finally:
            self.stop()

def main():
    """Función principal para testing del manager"""
    parser = argparse.ArgumentParser(description='Concurrent Scraper Manager')
    parser.add_argument('--concurrent', type=int, default=None,
                       help='Máximo número de scrapers concurrentes')
    parser.add_argument('--test', action='store_true',
                       help='Ejecutar test básico')
    
    args = parser.parse_args()
    
    if args.test:
        # Test básico con inmuebles24
        manager = ConcurrentScraperManager(max_concurrent=args.concurrent)
        
        # Configurar tareas de prueba
        test_configs = [
            {
                'site': 'inmuebles24',
                'operation': 'venta',
                'headless': True,
                'max_pages': 5,
                'priority': 1
            },
            {
                'site': 'inmuebles24',
                'operation': 'renta',
                'headless': True,
                'max_pages': 5,
                'priority': 1
            }
        ]
        
        # Ejecutar test
        results = manager.run_batch_scraping(test_configs)
        
        print("\n" + "="*50)
        print("🎉 TEST COMPLETADO")
        print(f"Resultados: {results}")
        print("="*50)
    
    else:
        print("Use --test para ejecutar test básico")

if __name__ == "__main__":
    main()
