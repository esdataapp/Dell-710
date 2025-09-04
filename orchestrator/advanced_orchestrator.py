#!/usr/bin/env python3
"""
Advanced Orchestrator - PropertyScraper Dell710
Orquestador avanzado con lógica de flujo de trabajo según especificaciones
Adaptado para trabajar con los archivos CSV individuales ubicados en ``URLs/``
"""

import os
import sys
import json
import time
import threading
import subprocess
import logging
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
import signal

# Agregar paths del proyecto
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from enhanced_scraps_registry import EnhancedScrapsRegistry

# Importar scrapers específicos
try:
    sys.path.append(str(Path(__file__).parent.parent / 'scrapers'))
    from inm24 import run_scraper as run_inmuebles24
    from inm24_det import run_scraper as run_inm24_det
    from cyt import run_scraper as run_casas_terrenos
    from mit import run_scraper as run_mitula
    from lam import run_scraper as run_lam
    from lam_det import run_scraper as run_lam_det
    from prop import run_scraper as run_prop
    from tro import run_scraper as run_trovit
    scrapers_available = True
except ImportError as e:
    logging.warning(f"No se pudieron importar scrapers específicos: {e}")
    scrapers_available = False

# Importar otros componentes opcionales
try:
    from utils.gdrive_backup_manager import GoogleDriveBackupManager
    backup_available = True
except ImportError:
    backup_available = False

try:
    from monitoring.performance_monitor import DellT710PerformanceMonitor
    monitoring_available = True
except ImportError:
    monitoring_available = False

class AdvancedOrchestrator:
    """
    Orquestador avanzado que implementa la lógica de flujo de trabajo:
    1. Una página web a la vez
    2. Todas las operaciones de esa página web
    3. Todos los productos de cada operación
    4. Máximo 4 scrapers paralelos pero en páginas web diferentes
    """
    
    def __init__(self):
        self.setup_logging()
        
        # Componentes principales
        self.registry = EnhancedScrapsRegistry()
        
        # Componentes opcionales
        if backup_available:
            self.backup_manager = GoogleDriveBackupManager()
        else:
            self.backup_manager = None
            
        if monitoring_available:
            self.performance_monitor = DellT710PerformanceMonitor(log_interval=30)
        else:
            self.performance_monitor = None
        
        # Estado del orquestador
        self.running = False
        # {website: {thread, scrap, started_at, result}}
        self.active_scrapers = {}
        self.completed_scrapers = []
        self.failed_scrapers = []
        
        # Configuración Dell T710
        self.max_concurrent_websites = 4  # Máximo 4 páginas web simultáneas
        self.max_cpu_usage = 80
        self.max_memory_usage = 80

        # Mapear identificadores de sitios web a sus funciones run_scraper
        self.scraper_functions = {
            'inm24': run_inmuebles24,
            'inm24_det': run_inm24_det,
            'cyt': run_casas_terrenos,
            'mit': run_mitula,
            'lam': run_lam,
            'lam_det': run_lam_det,
            'prop': run_prop,
            'tro': run_trovit,
        }

        # Dependencias: scraper base -> scraper de detalle
        self.detail_dependencies = {
            'inm24': 'inm24_det',
            'lam': 'lam_det',
        }
        
        # Archivos de estado
        self.state_file = Path(__file__).parent.parent / 'data' / 'orchestrator_state.json'
        self.checkpoint_dir = Path(__file__).parent.parent / 'logs' / 'checkpoints'
        self.checkpoint_dir.mkdir(exist_ok=True, parents=True)
        
        # Control de interrupciones
        signal.signal(signal.SIGINT, self.graceful_shutdown)
        signal.signal(signal.SIGTERM, self.graceful_shutdown)
        
        self.logger.info("🎛️ Advanced Orchestrator inicializado")
        self.logger.info(f"   Max concurrent websites: {self.max_concurrent_websites}")
        self.logger.info(f"   CPU/Memory limits: {self.max_cpu_usage}%/{self.max_memory_usage}%")
    
    def setup_logging(self):
        """Configurar logging avanzado"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(__file__).parent.parent / 'logs' / f'advanced_orchestrator_{timestamp}.log'
        log_file.parent.mkdir(exist_ok=True, parents=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | ORCH | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def check_system_resources(self) -> bool:
        """Verificar si hay recursos disponibles para ejecutar más scrapers"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        if cpu_percent > self.max_cpu_usage:
            self.logger.warning(f"⚠️ CPU usage high: {cpu_percent:.1f}% > {self.max_cpu_usage}%")
            return False
        
        if memory_percent > self.max_memory_usage:
            self.logger.warning(f"⚠️ Memory usage high: {memory_percent:.1f}% > {self.max_memory_usage}%")
            return False
        
        return True
    
    def get_next_website_to_process(self) -> Optional[str]:
        """
        Obtener la siguiente página web a procesar según el flujo de trabajo:
        - Una página web a la vez
        - Completar todas las operaciones y productos de esa página web
        """
        next_scraps = self.registry.get_next_scraps_to_run(20)  # Obtener más para análisis
        
        if not next_scraps:
            return None
        
        # Agrupar por website
        websites_with_pending = {}
        for scrap in next_scraps:
            website = scrap['website']
            if website not in websites_with_pending:
                websites_with_pending[website] = []
            websites_with_pending[website].append(scrap)
        
        # Encontrar website que no esté siendo procesado actualmente
        for website, scraps in websites_with_pending.items():
            if website not in self.active_scrapers:
                return website
        
        return None
    
    def get_scraps_for_website(self, website: str) -> List[Dict]:
        """
        Obtener todos los scraps pendientes para una página web específica
        Ordenados por: operación -> producto
        """
        all_scraps = self.registry.load_urls_from_csv()
        
        website_scraps = []
        for scrap in all_scraps:
            if (scrap['website'] == website and 
                (scrap['status'] == 'pending' or 
                 (scrap['status'] == 'completed' and scrap['next_run'] and 
                  datetime.now() >= datetime.fromisoformat(scrap['next_run'])))):
                website_scraps.append(scrap)
        
        # Ordenar por operación y producto
        website_scraps.sort(key=lambda x: (x['operacion'], x['producto']))
        
        return website_scraps
    
    def start_scraper_for_scrap(self, scrap: Dict) -> Optional[threading.Thread]:
        """Iniciar un scraper para un scrap específico usando scrapers integrados"""
        try:
            if not scrapers_available:
                self.logger.error("❌ Scrapers específicos no disponibles, usando subprocess")
                return self.start_scraper_subprocess(scrap)
            
            # Usar scrapers integrados
            website = scrap['website'].lower()
            scraper_func = self.scraper_functions.get(website)
            if not scraper_func:
                self.logger.error(f"❌ Scraper no disponible para {website}")
                self.registry.update_scrap_execution(scrap['id'], 'failed')
                return None

            url = scrap['url']
            output_path = self.registry.get_output_path(scrap)

            # Crear directorio de salida
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Actualizar registry a running
            self.registry.update_scrap_execution(
                scrap['id'],
                'running'
            )

            # Ejecutar scraper en hilo separado
            scraper_thread = threading.Thread(
                target=self.run_scraper_thread,
                args=(website, scraper_func, url, output_path),
                daemon=True
            )
            scraper_thread.start()

            return scraper_thread  # Retornar thread para monitoreo
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando scraper para {scrap['website']}: {e}")
            self.registry.update_scrap_execution(scrap['id'], 'failed')
            return None
    
    def run_scraper_thread(self, website: str, scraper_func, url: str, output_path: str):
        """Ejecutar scraper en hilo separado y almacenar el resultado en el hilo."""
        thread = threading.current_thread()
        try:
            self.logger.info(f"🚀 Ejecutando scraper para {website}: {url}")

            # Ejecutar scraper correspondiente usando la función mapeada
            if website in {'inm24_det', 'lam_det'}:
                result = scraper_func(urls_file=url, output_path=output_path)
            else:
                result = scraper_func(url=url, output_path=output_path, max_pages=None)

            # Algunos scrapers retornan listas de resultados
            if isinstance(result, list):
                result = result[0] if result else {}

            # Guardar resultado en el hilo para su posterior procesamiento
            thread.result = result

            # Verificar si hay scraper de detalle dependiente
            if result.get('success', False):
                detail_site = self.detail_dependencies.get(website)
                if detail_site:
                    detail_func = self.scraper_functions.get(detail_site)
                    detail_input = result.get('csv_file', url)
                    if detail_func and detail_input:
                        try:
                            self.logger.info(
                                f"📥 Ejecutando scraper dependiente {detail_site} con {detail_input}"
                            )
                            detail_func(urls_file=detail_input, output_path=None)
                        except Exception as e:
                            self.logger.error(
                                f"❌ Error ejecutando scraper dependiente {detail_site}: {e}"
                            )

        except Exception as e:
            # Registrar el error y almacenar estado de fallo en el hilo
            self.logger.error(f"❌ Error en scraper thread {website}: {e}")
            thread.result = {'success': False, 'error': str(e)}
    
    def start_scraper_subprocess(self, scrap: Dict) -> Optional[subprocess.Popen]:
        """Método de respaldo usando subprocess"""
        try:
            # Determinar el script de scraper a usar
            scraper_script = self.get_scraper_script(scrap['website'])
            if not scraper_script:
                self.logger.error(f"❌ No se encontró scraper para {scrap['website']}")
                return None
            
            # Preparar comando
            python_path = "/home/esdata/venv/bin/python"  # Asumiendo venv en servidor
            script_path = f"/home/esdata/PropertyScraper-Dell710/scrapers/{scraper_script}"
            
            cmd = [
                python_path, script_path,
                "--headless",
                f"--url={scrap['url']}",
                f"--output={self.registry.get_output_path(scrap)}",
                "--pages=50"  # Límite por defecto
            ]
            
            self.logger.info(f"🚀 Iniciando scraper subprocess: {' '.join(cmd)}")
            
            # Iniciar proceso
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Actualizar registry
            self.registry.update_scrap_execution(
                scrap['id'],
                'running'
            )
            
            return process
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando subprocess para {scrap['website']}: {e}")
            self.registry.update_scrap_execution(scrap['id'], 'failed')
            return None
    
    def get_scraper_script(self, website: str) -> Optional[str]:
        """Obtener el nombre del script de scraper para una página web"""
        scraper_mapping = {
            'inmuebles24': 'inm24.py',
            'casas_y_terrenos': 'cyt.py',
            'mitula': 'mit.py',
            'lamudi': 'lam.py',
            'propiedades': 'prop.py',
            'trovit': 'tro.py'
        }
        return scraper_mapping.get(website)
    
    def monitor_active_scrapers(self):
        """Monitorear scrapers activos y manejar completaciones/fallos"""
        completed_websites = []

        for website, scraper_info in list(self.active_scrapers.items()):
            thread = scraper_info['thread']
            scrap = scraper_info['scrap']

            # Verificar si el hilo terminó
            if not thread.is_alive():
                # Asegurar que el hilo haya finalizado completamente
                thread.join()
                result = getattr(thread, 'result', {'success': False})

                # Guardar resultado en la entrada del scraper
                scraper_info['result'] = result

                if result.get('success', False):
                    self.logger.info(f"✅ Scraper completado exitosamente: {website}")
                    self.registry.update_scrap_execution(
                        scrap['id'],
                        'completed',
                        records_extracted=result.get('properties_found', 0),
                        execution_time_minutes=int(result.get('total_time_seconds', 0) / 60)
                    )
                    self.completed_scrapers.append(scrap)

                    # Programar backup
                    self.schedule_backup(website, scrap)

                else:
                    self.logger.error(f"❌ Scraper falló: {website}")
                    self.registry.update_scrap_execution(scrap['id'], 'failed')
                    self.failed_scrapers.append(scrap)

                completed_websites.append(website)

        # Remover scrapers completados
        for website in completed_websites:
            del self.active_scrapers[website]
    
    def schedule_backup(self, website: str, scrap: Dict):
        """Programar backup de los resultados a Google Drive"""
        if not self.backup_manager:
            self.logger.warning("⚠️ Backup manager no disponible")
            return
            
        try:
            # Determinar directorio de datos
            data_dir = f"/home/esdata/PropertyScraper-Dell710/data/{website}/{scrap['operacion']}"
            
            # Ejecutar backup en hilo separado para no bloquear
            backup_thread = threading.Thread(
                target=self.backup_manager.backup_website_data,
                args=(website, scrap['operacion']),
                daemon=True
            )
            backup_thread.start()
            
            self.logger.info(f"☁️ Backup programado para {website}/{scrap['operacion']}")
            
        except Exception as e:
            self.logger.error(f"❌ Error programando backup: {e}")

    def load_tasks_from_urls_dir(self, urls_dir: Path = None) -> Dict[str, List[Dict]]:
        """Inspeccionar la carpeta URLs/ y generar tareas agrupadas por sitio"""
        if urls_dir is None:
            urls_dir = Path(__file__).parent.parent / 'URLs'

        tasks_by_site: Dict[str, List[Dict]] = {}

        if not urls_dir.exists():
            self.logger.warning(f"📁 Carpeta no encontrada: {urls_dir}")
            return tasks_by_site

        for csv_file in urls_dir.glob('*.csv'):
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        website = (row.get('PaginaWeb') or '').strip()
                        url = (row.get('URL') or '').strip()
                        if not website or not url:
                            continue

                        task = {
                            'website': website.lower(),
                            'ciudad': row.get('Ciudad', '').strip(),
                            'operacion': (row.get('Operación') or row.get('Operacion') or row.get('Operacin') or '').strip().lower(),
                            'producto': row.get('ProductoPaginaWeb', '').strip(),
                            'url': url
                        }
                        tasks_by_site.setdefault(task['website'], []).append(task)
            except Exception as e:
                self.logger.error(f"❌ Error leyendo {csv_file}: {e}")

        return tasks_by_site

    def build_output_path(self, task: Dict) -> str:
        """Construir la ruta de salida para una tarea"""
        safe_city = task['ciudad'].lower().replace(' ', '_')
        safe_product = task['producto'].lower().replace(' ', '_')
        operation = task['operacion']
        website = task['website']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        output_dir = Path(__file__).parent.parent / 'data' / 'batch_csv' / website / safe_city / operation
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir / f"{safe_product}_{timestamp}.csv")

    def run_single_task(self, task: Dict):
        """Ejecutar el scraper adecuado para una tarea"""
        website = task['website']
        url = task['url']
        output_path = self.build_output_path(task)

        try:
            if website == 'inmuebles24':
                run_inmuebles24(url, output_path, max_pages=None)
            elif website == 'casas_y_terrenos':
                run_casas_terrenos(url, output_path, max_pages=None)
            elif website == 'mitula':
                run_mitula(url, output_path, max_pages=None)
            else:
                self.logger.warning(f"⚠️ Scraper no disponible para {website}")
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando tarea para {website}: {e}")

    def process_batch_site(self, website: str, tasks: List[Dict]):
        """Procesar secuencialmente todas las tareas de un sitio"""
        self.logger.info(f"🌐 Procesando {len(tasks)} tareas para {website}")
        for task in tasks:
            if not self.running:
                break
            self.run_single_task(task)
        self.logger.info(f"✅ Sitio completado: {website}")

    def run_batch_from_csv(self, urls_dir: Path = None):
        """Ejecutar el flujo completo a partir de los CSVs en ``urls_dir``.

        Si ``urls_dir`` no se especifica, se utiliza por defecto la carpeta
        ``URLs/`` en la raíz del proyecto.
        """
        tasks_by_site = self.load_tasks_from_urls_dir(urls_dir)
        if not tasks_by_site:
            self.logger.info("📝 No se encontraron tareas en URLs/")
            return

        self.running = True
        websites = list(tasks_by_site.keys())
        active_threads: Dict[str, threading.Thread] = {}

        while self.running and (websites or active_threads):
            # Lanzar nuevos sitios si hay capacidad
            while websites and len(active_threads) < self.max_concurrent_websites:
                website = websites.pop(0)
                thread = threading.Thread(
                    target=self.process_batch_site,
                    args=(website, tasks_by_site[website]),
                    daemon=True
                )
                thread.start()
                active_threads[website] = thread

            # Verificar sitios completados
            for website in list(active_threads.keys()):
                if not active_threads[website].is_alive():
                    active_threads.pop(website)

            if not active_threads and not websites:
                break

            time.sleep(5)

        self.running = False
        self.logger.info("✅ Proceso por lotes completado")
    
    def process_website_completely(self, website: str):
        """
        Procesar completamente una página web:
        - Todas las operaciones (venta, renta)
        - Todos los productos de cada operación
        """
        self.logger.info(f"🌐 Iniciando procesamiento completo de: {website}")
        
        website_scraps = self.get_scraps_for_website(website)
        if not website_scraps:
            self.logger.info(f"📝 No hay scraps pendientes para {website}")
            return
        
        self.logger.info(f"📋 {len(website_scraps)} scraps encontrados para {website}")
        
        # Procesar scraps uno por uno para esta página web
        for scrap in website_scraps:
            if not self.running:
                break
            
            # Verificar recursos antes de cada scraper
            if not self.check_system_resources():
                self.logger.warning("⚠️ Recursos insuficientes, esperando...")
                time.sleep(60)
                continue
            
            # Iniciar scraper
            thread = self.start_scraper_for_scrap(scrap)
            if thread:
                # Registrar scraper activo
                self.active_scrapers[website] = {
                    'thread': thread,
                    'scrap': scrap,
                    'started_at': datetime.now(),
                    'result': None
                }

                # Esperar a que termine este scraper antes del siguiente
                while thread.is_alive() and self.running:
                    time.sleep(30)  # Verificar cada 30 segundos
                    self.display_progress()

                # Asegurarse de que el hilo haya finalizado
                thread.join()

                # Manejar resultado
                self.monitor_active_scrapers()

                # Pausa entre scraps para evitar sobrecarga
                time.sleep(10)
        
        self.logger.info(f"✅ Procesamiento completo de {website} terminado")
    
    def run_orchestration(self):
        """Ejecutar orquestación principal"""
        self.logger.info("🎛️ Iniciando orquestación avanzada...")
        self.running = True
        
        # Iniciar monitor de rendimiento si está disponible
        if self.performance_monitor:
            self.performance_monitor.start_monitoring()
        
        try:
            while self.running:
                # Verificar si podemos iniciar más websites
                if len(self.active_scrapers) < self.max_concurrent_websites:
                    
                    # Obtener siguiente website a procesar
                    next_website = self.get_next_website_to_process()
                    
                    if next_website:
                        # Verificar recursos
                        if self.check_system_resources():
                            # Iniciar procesamiento de website en hilo separado
                            website_thread = threading.Thread(
                                target=self.process_website_completely,
                                args=(next_website,),
                                daemon=True
                            )
                            website_thread.start()
                            
                            self.logger.info(f"🌐 Website {next_website} iniciado en hilo separado")
                        else:
                            self.logger.warning("⚠️ Recursos insuficientes para nuevo website")
                    else:
                        self.logger.info("📝 No hay más websites pendientes")
                
                # Monitorear scrapers activos
                self.monitor_active_scrapers()
                
                # Mostrar progreso
                self.display_progress()
                
                # Guardar estado
                self.save_state()
                
                # Verificar si hay trabajo pendiente
                if not self.active_scrapers and not self.get_next_website_to_process():
                    self.logger.info("✅ Toda la orquestación completada")
                    break
                
                # Esperar antes del siguiente ciclo
                time.sleep(30)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️ Orquestación interrumpida por usuario")
        finally:
            self.graceful_shutdown()
    
    def display_progress(self):
        """Mostrar progreso visual en terminal"""
        stats = self.registry.get_registry_stats()
        
        print(f"\n{'='*80}")
        print(f"🎛️ ORCHESTRATOR STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")
        print(f"🔄 Active Websites: {len(self.active_scrapers)}/{self.max_concurrent_websites}")
        
        for website, info in self.active_scrapers.items():
            elapsed = datetime.now() - info['started_at']
            scrap = info['scrap']
            print(f"   🌐 {website:15} | {scrap['operacion']:5} | {scrap['producto']:20} | ⏱️ {str(elapsed).split('.')[0]}")
        
        print(f"\n📊 Registry Stats:")
        print(f"   ✅ Completed: {stats['completed']:3d}")
        print(f"   ❌ Failed:    {stats['failed']:3d}")
        print(f"   ⏳ Pending:   {stats['pending']:3d}")
        print(f"   🔄 Running:   {stats['running']:3d}")
        print(f"   🏠 Properties: {stats['total_properties_scraped']:,}")
        
        # Recursos del sistema
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        print(f"\n🖥️ System Resources:")
        print(f"   CPU: {cpu_percent:5.1f}% | Memory: {memory_percent:5.1f}%")
        
        print(f"{'='*80}")
    
    def save_state(self):
        """Guardar estado actual del orquestador"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'running': self.running,
            'active_scrapers_count': len(self.active_scrapers),
            'active_websites': list(self.active_scrapers.keys()),
            'completed_count': len(self.completed_scrapers),
            'failed_count': len(self.failed_scrapers)
        }
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    
    def graceful_shutdown(self, signum=None, frame=None):
        """Apagado gradual del orquestador"""
        if not self.running:
            return
        
        self.logger.info("🛑 Iniciando apagado gradual...")
        self.running = False
        
        # Terminar scrapers activos de forma gradual
        for website, scraper_info in self.active_scrapers.items():
            thread = scraper_info['thread']
            scrap = scraper_info['scrap']

            self.logger.info(f"⏹️ Terminando scraper: {website}")

            try:
                # Esperar a que el hilo termine de forma natural
                if thread.is_alive():
                    thread.join(timeout=30)

                # Actualizar estado a pausado para reanudar después
                self.registry.update_scrap_execution(scrap['id'], 'paused')

            except Exception as e:
                self.logger.error(f"❌ Error terminando {website}: {e}")
        
        # Detener monitor de rendimiento si está disponible
        if self.performance_monitor:
            self.performance_monitor.stop_monitoring()
        
        # Guardar estado final
        self.save_state()
        
        self.logger.info("✅ Apagado gradual completado")
    
    def resume_from_checkpoint(self):
        """Reanudar desde checkpoint después de interrupción"""
        self.logger.info("🔄 Reanudando desde checkpoint...")
        
        # Cargar scraps pausados
        scraps = self.registry.load_urls_from_csv()
        paused_scraps = [s for s in scraps if s['status'] == 'paused']
        
        if paused_scraps:
            self.logger.info(f"📋 {len(paused_scraps)} scraps pausados encontrados")
            
            # Cambiar estado a pending para que sean procesados
            for scrap in paused_scraps:
                self.registry.update_scrap_execution(scrap['id'], 'pending')
        
        # Iniciar orquestación normal
        self.run_orchestration()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced Orchestrator for PropertyScraper Dell710')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--batch-from-csv', action='store_true', help='Ejecutar scraping en lote usando URLs/*.csv')
    
    args = parser.parse_args()
    
    orchestrator = AdvancedOrchestrator()
    
    if args.status:
        orchestrator.registry.display_registry_status()
        orchestrator.display_progress()
    elif args.resume:
        orchestrator.resume_from_checkpoint()
    elif args.batch_from_csv:
        orchestrator.run_batch_from_csv()
    else:
        orchestrator.run_orchestration()
