#!/usr/bin/env python3
"""
Performance Monitor - PropertyScraper Dell710
Monitor de rendimiento en tiempo real para Dell T710
"""

import os
import sys
import json
import time
import psutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import threading

class DellT710PerformanceMonitor:
    """
    Monitor de rendimiento específico para Dell T710
    Rastrea CPU, memoria, disco y procesos de scraping
    """
    
    def __init__(self, log_interval=60):
        self.log_interval = log_interval  # segundos
        self.setup_logging()
        
        # Estado del monitor
        self.monitoring = False
        self.monitor_thread = None
        
        # Métricas acumuladas
        self.metrics_history = []
        self.max_history_size = 1440  # 24 horas con intervalos de 1 minuto
        
        # Thresholds Dell T710
        self.cpu_warning_threshold = 80
        self.cpu_critical_threshold = 90
        self.memory_warning_threshold = 80
        self.memory_critical_threshold = 90
        self.disk_warning_threshold = 85
        self.disk_critical_threshold = 95
        
        # Archivos de métricas
        self.metrics_file = Path(__file__).parent.parent / 'logs' / 'performance_metrics.json'
        self.alerts_file = Path(__file__).parent.parent / 'logs' / 'performance_alerts.log'
        
        self.logger.info("📊 Performance Monitor Dell T710 inicializado")
        self.logger.info(f"   Intervalo de logging: {log_interval}s")
        self.logger.info(f"   CPU warning/critical: {self.cpu_warning_threshold}%/{self.cpu_critical_threshold}%")
        self.logger.info(f"   Memory warning/critical: {self.memory_warning_threshold}%/{self.memory_critical_threshold}%")
    
    def setup_logging(self):
        """Configurar logging específico para el monitor"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(__file__).parent.parent / 'logs' / f"performance_monitor_{timestamp}.log"
        
        # Asegurar directorio de logs
        log_file.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | PERF | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def get_current_metrics(self) -> Dict:
        """Obtener métricas actuales del sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memoria
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disco
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Red
            net_io = psutil.net_io_counters()
            
            # Procesos Python/Chrome (scrapers)
            python_processes = []
            chrome_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        python_processes.append({
                            'pid': proc.info['pid'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent'],
                            'cmdline': ' '.join(proc.info['cmdline'][:3]) if proc.info['cmdline'] else ''
                        })
                    elif 'chrome' in proc.info['name'].lower():
                        chrome_processes.append({
                            'pid': proc.info['pid'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sistema general
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'uptime_seconds': uptime.total_seconds(),
                    'boot_time': boot_time.isoformat()
                },
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else None
                },
                'memory': {
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'used_gb': memory.used / (1024**3),
                    'percent': memory.percent,
                    'swap_percent': swap.percent,
                    'swap_used_gb': swap.used / (1024**3)
                },
                'disk': {
                    'total_gb': disk_usage.total / (1024**3),
                    'used_gb': disk_usage.used / (1024**3),
                    'free_gb': disk_usage.free / (1024**3),
                    'percent': (disk_usage.used / disk_usage.total) * 100,
                    'read_mb': disk_io.read_bytes / (1024**2) if disk_io else 0,
                    'write_mb': disk_io.write_bytes / (1024**2) if disk_io else 0
                },
                'network': {
                    'bytes_sent_mb': net_io.bytes_sent / (1024**2) if net_io else 0,
                    'bytes_recv_mb': net_io.bytes_recv / (1024**2) if net_io else 0
                },
                'processes': {
                    'python_count': len(python_processes),
                    'chrome_count': len(chrome_processes),
                    'python_processes': python_processes[:5],  # Top 5
                    'chrome_processes': chrome_processes[:5]   # Top 5
                }
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo métricas: {e}")
            return None
    
    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """Verificar alertas basadas en las métricas"""
        alerts = []
        
        try:
            # CPU alerts
            cpu_percent = metrics['cpu']['percent']
            if cpu_percent >= self.cpu_critical_threshold:
                alerts.append({
                    'level': 'CRITICAL',
                    'type': 'CPU',
                    'message': f'CPU usage critical: {cpu_percent:.1f}%',
                    'value': cpu_percent,
                    'threshold': self.cpu_critical_threshold
                })
            elif cpu_percent >= self.cpu_warning_threshold:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'CPU',
                    'message': f'CPU usage high: {cpu_percent:.1f}%',
                    'value': cpu_percent,
                    'threshold': self.cpu_warning_threshold
                })
            
            # Memory alerts
            memory_percent = metrics['memory']['percent']
            if memory_percent >= self.memory_critical_threshold:
                alerts.append({
                    'level': 'CRITICAL',
                    'type': 'MEMORY',
                    'message': f'Memory usage critical: {memory_percent:.1f}%',
                    'value': memory_percent,
                    'threshold': self.memory_critical_threshold
                })
            elif memory_percent >= self.memory_warning_threshold:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'MEMORY',
                    'message': f'Memory usage high: {memory_percent:.1f}%',
                    'value': memory_percent,
                    'threshold': self.memory_warning_threshold
                })
            
            # Disk alerts
            disk_percent = metrics['disk']['percent']
            if disk_percent >= self.disk_critical_threshold:
                alerts.append({
                    'level': 'CRITICAL',
                    'type': 'DISK',
                    'message': f'Disk usage critical: {disk_percent:.1f}%',
                    'value': disk_percent,
                    'threshold': self.disk_critical_threshold
                })
            elif disk_percent >= self.disk_warning_threshold:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'DISK',
                    'message': f'Disk usage high: {disk_percent:.1f}%',
                    'value': disk_percent,
                    'threshold': self.disk_warning_threshold
                })
            
            # Process alerts
            python_count = metrics['processes']['python_count']
            chrome_count = metrics['processes']['chrome_count']
            
            if python_count > 10:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'PROCESSES',
                    'message': f'Many Python processes: {python_count}',
                    'value': python_count,
                    'threshold': 10
                })
            
            if chrome_count > 8:
                alerts.append({
                    'level': 'WARNING',
                    'type': 'PROCESSES',
                    'message': f'Many Chrome processes: {chrome_count}',
                    'value': chrome_count,
                    'threshold': 8
                })
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando alertas: {e}")
        
        return alerts
    
    def log_alerts(self, alerts: List[Dict]):
        """Registrar alertas en archivo específico"""
        if not alerts:
            return
        
        try:
            with open(self.alerts_file, 'a', encoding='utf-8') as f:
                for alert in alerts:
                    timestamp = datetime.now().isoformat()
                    alert_line = f"{timestamp} | {alert['level']:8s} | {alert['type']:8s} | {alert['message']}\n"
                    f.write(alert_line)
                    
                    # También log a consola
                    if alert['level'] == 'CRITICAL':
                        self.logger.critical(f"🚨 {alert['message']}")
                    else:
                        self.logger.warning(f"⚠️  {alert['message']}")
                        
        except Exception as e:
            self.logger.error(f"❌ Error logging alertas: {e}")
    
    def save_metrics(self, metrics: Dict):
        """Guardar métricas en archivo JSON"""
        try:
            # Agregar a historial en memoria
            self.metrics_history.append(metrics)
            
            # Mantener tamaño máximo del historial
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            # Guardar en archivo (últimas 100 métricas)
            recent_metrics = self.metrics_history[-100:]
            
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(recent_metrics, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"❌ Error guardando métricas: {e}")
    
    def monitor_loop(self):
        """Loop principal de monitoreo"""
        self.logger.info("🔄 Iniciando loop de monitoreo...")
        
        while self.monitoring:
            try:
                # Obtener métricas actuales
                metrics = self.get_current_metrics()
                
                if metrics:
                    # Verificar alertas
                    alerts = self.check_alerts(metrics)
                    
                    # Log de alertas
                    if alerts:
                        self.log_alerts(alerts)
                    
                    # Guardar métricas
                    self.save_metrics(metrics)
                    
                    # Log periódico (cada 5 minutos)
                    current_minute = datetime.now().minute
                    if current_minute % 5 == 0 and datetime.now().second < 10:
                        self.logger.info(f"📊 Métricas Dell T710:")
                        self.logger.info(f"   CPU: {metrics['cpu']['percent']:.1f}%")
                        self.logger.info(f"   Memory: {metrics['memory']['percent']:.1f}% ({metrics['memory']['used_gb']:.1f}GB)")
                        self.logger.info(f"   Disk: {metrics['disk']['percent']:.1f}% ({metrics['disk']['used_gb']:.1f}GB)")
                        self.logger.info(f"   Processes: {metrics['processes']['python_count']} Python, {metrics['processes']['chrome_count']} Chrome")
                
                # Esperar siguiente intervalo
                time.sleep(self.log_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Error en monitor loop: {e}")
                time.sleep(60)  # Esperar 1 minuto en caso de error
    
    def start_monitoring(self):
        """Iniciar monitoreo en background"""
        if self.monitoring:
            self.logger.warning("⚠️  Monitor ya está ejecutándose")
            return False
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, name="PerformanceMonitor")
        self.monitor_thread.start()
        
        self.logger.info("✅ Monitoreo de rendimiento iniciado")
        return True
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=30)
        
        self.logger.info("⏹️  Monitoreo de rendimiento detenido")
    
    def get_summary_report(self) -> Dict:
        """Generar reporte resumen de las métricas"""
        if not self.metrics_history:
            return {'error': 'No hay métricas disponibles'}
        
        try:
            recent_metrics = self.metrics_history[-60:]  # Última hora
            
            # Calcular promedios
            avg_cpu = sum(m['cpu']['percent'] for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m['memory']['percent'] for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m['disk']['percent'] for m in recent_metrics) / len(recent_metrics)
            
            # Máximos
            max_cpu = max(m['cpu']['percent'] for m in recent_metrics)
            max_memory = max(m['memory']['percent'] for m in recent_metrics)
            
            # Última métrica
            latest = recent_metrics[-1]
            
            return {
                'period': 'last_hour',
                'samples_count': len(recent_metrics),
                'timestamp': datetime.now().isoformat(),
                'averages': {
                    'cpu_percent': avg_cpu,
                    'memory_percent': avg_memory,
                    'disk_percent': avg_disk
                },
                'maximums': {
                    'cpu_percent': max_cpu,
                    'memory_percent': max_memory
                },
                'current': {
                    'cpu_percent': latest['cpu']['percent'],
                    'memory_percent': latest['memory']['percent'],
                    'memory_used_gb': latest['memory']['used_gb'],
                    'disk_percent': latest['disk']['percent'],
                    'python_processes': latest['processes']['python_count'],
                    'chrome_processes': latest['processes']['chrome_count']
                },
                'dell_t710_optimization': {
                    'cpu_utilization_of_limit': (latest['cpu']['percent'] / self.cpu_warning_threshold) * 100,
                    'memory_utilization_of_limit': (latest['memory']['percent'] / self.memory_warning_threshold) * 100,
                    'estimated_available_scrapers': max(0, int((self.cpu_warning_threshold - latest['cpu']['percent']) / 15))
                }
            }
            
        except Exception as e:
            return {'error': f'Error generando reporte: {str(e)}'}

def main():
    """Función principal para testing del monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dell T710 Performance Monitor')
    parser.add_argument('--start', action='store_true', help='Iniciar monitoreo continuo')
    parser.add_argument('--status', action='store_true', help='Mostrar estado actual')
    parser.add_argument('--report', action='store_true', help='Generar reporte resumen')
    parser.add_argument('--interval', type=int, default=60, help='Intervalo de logging en segundos')
    
    args = parser.parse_args()
    
    monitor = DellT710PerformanceMonitor(log_interval=args.interval)
    
    if args.start:
        print("🚀 Iniciando monitoreo continuo...")
        monitor.start_monitoring()
        
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n⏹️  Deteniendo monitor...")
            monitor.stop_monitoring()
    
    elif args.status:
        print("📊 Estado actual del sistema Dell T710:")
        metrics = monitor.get_current_metrics()
        
        if metrics:
            print(f"\n🖥️  CPU: {metrics['cpu']['percent']:.1f}% ({metrics['cpu']['count']} cores)")
            print(f"💾 Memory: {metrics['memory']['percent']:.1f}% ({metrics['memory']['used_gb']:.1f}GB / {metrics['memory']['total_gb']:.1f}GB)")
            print(f"💿 Disk: {metrics['disk']['percent']:.1f}% ({metrics['disk']['used_gb']:.1f}GB / {metrics['disk']['total_gb']:.1f}GB)")
            print(f"🐍 Python processes: {metrics['processes']['python_count']}")
            print(f"🌐 Chrome processes: {metrics['processes']['chrome_count']}")
            
            # Verificar alertas
            alerts = monitor.check_alerts(metrics)
            if alerts:
                print(f"\n⚠️  Alertas activas:")
                for alert in alerts:
                    print(f"   {alert['level']}: {alert['message']}")
            else:
                print(f"\n✅ Sin alertas activas")
        else:
            print("❌ Error obteniendo métricas")
    
    elif args.report:
        print("📈 Generando reporte resumen...")
        
        # Cargar métricas existentes si las hay
        if monitor.metrics_file.exists():
            try:
                with open(monitor.metrics_file, 'r', encoding='utf-8') as f:
                    monitor.metrics_history = json.load(f)
            except:
                pass
        
        report = monitor.get_summary_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    else:
        print("Use --start, --status, o --report")

if __name__ == "__main__":
    main()
