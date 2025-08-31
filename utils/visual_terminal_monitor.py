#!/usr/bin/env python3
"""
Visual Terminal Monitor - PropertyScraper Dell710
Monitor visual optimizado para terminal con información en tiempo real
"""

import os
import sys
import time
import json
import curses
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import psutil

# Agregar paths del proyecto
sys.path.append(str(Path(__file__).parent.parent))
from utils.scraps_registry import ScrapsRegistry
from monitoring.performance_monitor import DellT710PerformanceMonitor

class VisualTerminalMonitor:
    """
    Monitor visual para terminal que muestra:
    - Estado de scrapers activos
    - Progreso de orquestación
    - Recursos del sistema
    - Estadísticas de scraps
    - Logs en tiempo real
    """
    
    def __init__(self):
        self.registry = ScrapsRegistry()
        self.performance_monitor = DellT710PerformanceMonitor(log_interval=10)
        
        # Estado del monitor
        self.running = False
        self.update_interval = 2  # segundos
        
        # Datos en tiempo real
        self.active_scrapers = {}
        self.system_metrics = {}
        self.recent_logs = []
        self.max_logs = 10
        
        # Archivos de estado
        self.orchestrator_state_file = Path(__file__).parent.parent / 'data' / 'orchestrator_state.json'
        self.logs_dir = Path(__file__).parent.parent / 'logs'
    
    def get_active_scrapers_info(self) -> Dict:
        """Obtener información de scrapers activos"""
        try:
            # Buscar procesos Python que contengan nombres de scrapers
            scrapers_info = {}
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        
                        # Buscar scrapers conocidos en la línea de comandos
                        scraper_names = [
                            'inmuebles24_professional', 'casas_y_terrenos_scraper',
                            'lamudi_professional', 'mitula_scraper',
                            'propiedades_professional', 'segundamano_professional',
                            'trovit_professional'
                        ]
                        
                        for scraper_name in scraper_names:
                            if scraper_name in cmdline:
                                website = scraper_name.replace('_professional', '').replace('_scraper', '')
                                
                                # Extraer operación de la línea de comandos
                                operation = 'venta'  # default
                                if '--operation=renta' in cmdline:
                                    operation = 'renta'
                                
                                elapsed_time = datetime.now() - datetime.fromtimestamp(proc.info['create_time'])
                                
                                scrapers_info[f"{website}_{operation}"] = {
                                    'pid': proc.info['pid'],
                                    'website': website,
                                    'operation': operation,
                                    'cpu_percent': proc.info['cpu_percent'] or 0,
                                    'memory_percent': proc.info['memory_percent'] or 0,
                                    'elapsed_time': str(elapsed_time).split('.')[0],
                                    'status': 'running'
                                }
                                break
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return scrapers_info
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_orchestrator_state(self) -> Dict:
        """Obtener estado del orquestador"""
        try:
            if self.orchestrator_state_file.exists():
                with open(self.orchestrator_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {'status': 'not_running'}
        except Exception:
            return {'status': 'unknown'}
    
    def get_recent_logs(self) -> List[str]:
        """Obtener logs recientes del sistema"""
        try:
            recent_logs = []
            
            # Buscar archivos de log más recientes
            log_files = []
            for log_file in self.logs_dir.glob('*.log'):
                if log_file.stat().st_mtime > (time.time() - 3600):  # Últimas 1 horas
                    log_files.append(log_file)
            
            # Ordenar por fecha de modificación
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Leer últimas líneas del log más reciente
            if log_files:
                try:
                    with open(log_files[0], 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        recent_logs = lines[-self.max_logs:]  # Últimas 10 líneas
                except:
                    pass
            
            return [line.strip() for line in recent_logs if line.strip()]
            
        except Exception:
            return ["Error reading logs"]
    
    def format_system_info(self) -> List[str]:
        """Formatear información del sistema"""
        try:
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            # Memory info
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_total_gb = memory.total / (1024**3)
            
            # Disk info
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_used_gb = disk.used / (1024**3)
            disk_total_gb = disk.total / (1024**3)
            
            # Network info (optional)
            network = psutil.net_io_counters()
            
            system_info = [
                f"🖥️  DELL T710 SYSTEM STATUS",
                f"├─ CPU:    {cpu_percent:5.1f}% ({cpu_count} cores)",
                f"├─ Memory: {memory_percent:5.1f}% ({memory_used_gb:5.1f}GB / {memory_total_gb:5.1f}GB)",
                f"├─ Disk:   {disk_percent:5.1f}% ({disk_used_gb:5.1f}GB / {disk_total_gb:5.1f}GB)",
                f"└─ Net RX: {network.bytes_recv / (1024**2):5.1f}MB | TX: {network.bytes_sent / (1024**2):5.1f}MB"
            ]
            
            return system_info
            
        except Exception as e:
            return [f"Error getting system info: {e}"]
    
    def format_scrapers_info(self, scrapers: Dict) -> List[str]:
        """Formatear información de scrapers"""
        if not scrapers:
            return ["🕷️  ACTIVE SCRAPERS", "   No active scrapers found"]
        
        if 'error' in scrapers:
            return ["🕷️  ACTIVE SCRAPERS", f"   Error: {scrapers['error']}"]
        
        scraper_lines = ["🕷️  ACTIVE SCRAPERS"]
        
        for key, info in scrapers.items():
            website = info['website'].ljust(15)
            operation = info['operation'].ljust(6)
            cpu = f"{info['cpu_percent']:4.1f}%"
            memory = f"{info['memory_percent']:4.1f}%"
            elapsed = info['elapsed_time'].ljust(8)
            
            scraper_lines.append(
                f"├─ {website} | {operation} | CPU:{cpu} | MEM:{memory} | {elapsed}"
            )
        
        # Cambiar último ├─ por └─
        if len(scraper_lines) > 1:
            scraper_lines[-1] = scraper_lines[-1].replace("├─", "└─")
        
        return scraper_lines
    
    def format_registry_stats(self) -> List[str]:
        """Formatear estadísticas del registry"""
        try:
            stats = self.registry.get_registry_stats()
            
            registry_lines = [
                "📋 SCRAPS REGISTRY",
                f"├─ Total:     {stats['total_scraps']:3d}",
                f"├─ Pending:   {stats['pending']:3d}",
                f"├─ Running:   {stats['running']:3d}",
                f"├─ Completed: {stats['completed']:3d}",
                f"├─ Failed:    {stats['failed']:3d}",
                f"└─ Properties: {stats['total_properties_scraped']:,}"
            ]
            
            return registry_lines
            
        except Exception as e:
            return ["📋 SCRAPS REGISTRY", f"   Error: {e}"]
    
    def format_orchestrator_info(self, state: Dict) -> List[str]:
        """Formatear información del orquestador"""
        if state.get('status') == 'not_running':
            return ["🎛️  ORCHESTRATOR", "   Status: Not Running"]
        
        if state.get('status') == 'unknown':
            return ["🎛️  ORCHESTRATOR", "   Status: Unknown"]
        
        orch_lines = ["🎛️  ORCHESTRATOR"]
        
        if 'active_websites' in state:
            websites = ', '.join(state['active_websites']) if state['active_websites'] else 'None'
            orch_lines.extend([
                f"├─ Running: {state.get('running', False)}",
                f"├─ Active Sites: {state.get('active_scrapers_count', 0)}/4",
                f"├─ Websites: {websites}",
                f"├─ Completed: {state.get('completed_count', 0)}",
                f"└─ Failed: {state.get('failed_count', 0)}"
            ])
        else:
            orch_lines.append("   Status: Active")
        
        return orch_lines
    
    def format_recent_logs(self, logs: List[str]) -> List[str]:
        """Formatear logs recientes"""
        if not logs:
            return ["📝 RECENT LOGS", "   No recent logs"]
        
        log_lines = ["📝 RECENT LOGS"]
        
        for i, log in enumerate(logs[-5:]):  # Últimas 5 líneas
            # Truncar líneas muy largas
            if len(log) > 70:
                log = log[:67] + "..."
            
            # Extraer timestamp si existe
            if " | " in log:
                parts = log.split(" | ")
                if len(parts) >= 3:
                    timestamp = parts[0].split()[-1] if parts[0] else ""
                    level = parts[1].strip() if len(parts) > 1 else ""
                    message = " | ".join(parts[2:]) if len(parts) > 2 else ""
                    
                    # Truncar mensaje
                    if len(message) > 50:
                        message = message[:47] + "..."
                    
                    prefix = "└─" if i == len(logs[-5:]) - 1 else "├─"
                    log_lines.append(f"{prefix} {timestamp} {level}: {message}")
                else:
                    prefix = "└─" if i == len(logs[-5:]) - 1 else "├─"
                    log_lines.append(f"{prefix} {log}")
            else:
                prefix = "└─" if i == len(logs[-5:]) - 1 else "├─"
                log_lines.append(f"{prefix} {log}")
        
        return log_lines
    
    def display_simple_monitor(self):
        """Mostrar monitor simple sin curses para compatibilidad SSH"""
        self.running = True
        
        try:
            while self.running:
                # Limpiar terminal
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Header
                print("=" * 80)
                print(f"PropertyScraper Dell710 Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 80)
                
                # Información del sistema
                system_info = self.format_system_info()
                for line in system_info:
                    print(line)
                
                print()
                
                # Scrapers activos
                scrapers = self.get_active_scrapers_info()
                scraper_info = self.format_scrapers_info(scrapers)
                for line in scraper_info:
                    print(line)
                
                print()
                
                # Estado del orquestador
                orch_state = self.get_orchestrator_state()
                orch_info = self.format_orchestrator_info(orch_state)
                for line in orch_info:
                    print(line)
                
                print()
                
                # Estadísticas del registry
                registry_info = self.format_registry_stats()
                for line in registry_info:
                    print(line)
                
                print()
                
                # Logs recientes
                recent_logs = self.get_recent_logs()
                log_info = self.format_recent_logs(recent_logs)
                for line in log_info:
                    print(line)
                
                print()
                print("=" * 80)
                print("Press Ctrl+C to exit")
                print("=" * 80)
                
                # Esperar antes de la siguiente actualización
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitor stopped by user")
        except Exception as e:
            print(f"❌ Error in monitor: {e}")
        finally:
            self.running = False
    
    def start_monitoring(self):
        """Iniciar monitoreo visual"""
        print("🚀 Starting Visual Terminal Monitor...")
        print("   Compatible with SSH connections")
        print("   Update interval: {} seconds".format(self.update_interval))
        print()
        
        # Usar monitor simple por compatibilidad con SSH
        self.display_simple_monitor()

class CompactMonitor:
    """Monitor compacto para ver estado rápido"""
    
    def __init__(self):
        self.registry = ScrapsRegistry()
    
    def show_status(self):
        """Mostrar estado compacto"""
        try:
            # Scrapers activos
            active_scrapers = {}
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        
                        scraper_names = ['inmuebles24_professional', 'casas_y_terrenos_scraper', 'lamudi_professional']
                        for scraper_name in scraper_names:
                            if scraper_name in cmdline:
                                website = scraper_name.replace('_professional', '').replace('_scraper', '')
                                active_scrapers[website] = proc.info['pid']
                                break
                except:
                    continue
            
            # Stats registry
            stats = self.registry.get_registry_stats()
            
            # Sistema
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            
            # Output compacto
            print(f"🚀 Dell710: CPU:{cpu:4.1f}% MEM:{memory:4.1f}% | Active:{len(active_scrapers)} | Pending:{stats['pending']} Completed:{stats['completed']}")
            
            if active_scrapers:
                websites = ', '.join(active_scrapers.keys())
                print(f"   Running: {websites}")
            
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Visual Terminal Monitor for PropertyScraper Dell710')
    parser.add_argument('--compact', action='store_true', help='Show compact status')
    parser.add_argument('--interval', type=int, default=2, help='Update interval in seconds')
    
    args = parser.parse_args()
    
    if args.compact:
        monitor = CompactMonitor()
        monitor.show_status()
    else:
        monitor = VisualTerminalMonitor()
        monitor.update_interval = args.interval
        monitor.start_monitoring()

if __name__ == "__main__":
    main()
