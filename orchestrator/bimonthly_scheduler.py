#!/usr/bin/env python3
"""
Bi-Monthly Scheduler - PropertyScraper Dell710
Sistema de programación automática cada 15 días
"""

import os
import sys
import json
import time
import schedule
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import threading

# Importar módulos del proyecto
sys.path.append(str(Path(__file__).parent.parent))
from ssh_deployment.remote_executor import DellT710SSHExecutor
from orchestrator.concurrent_manager import ConcurrentScraperManager

class BiMonthlyScheduler:
    """
    Programador automático para ejecuciones bi-mensuales
    Cada 15 días ejecuta scrapers en Dell T710
    """
    
    def __init__(self, config_path=None):
        self.setup_logging()
        
        # Cargar configuración
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'dell_t710_config.yaml'
        
        self.config = self.load_config(config_path)
        self.schedule_config = self.config['scheduling']['bimonthly_schedule']
        
        # Estado del scheduler
        self.running = False
        self.scheduler_thread = None
        self.current_execution = None
        
        # Registro de ejecuciones
        self.execution_history = []
        self.history_file = Path(__file__).parent.parent / 'logs' / 'execution_history.json'
        
        self.logger.info("📅 Bi-Monthly Scheduler inicializado")
        self.logger.info(f"   1ra ejecución: días {self.schedule_config['first_execution']['day_of_month']} a las {self.schedule_config['first_execution']['hour']:02d}:{self.schedule_config['first_execution']['minute']:02d}")
        self.logger.info(f"   2da ejecución: días {self.schedule_config['second_execution']['day_of_month']} a las {self.schedule_config['second_execution']['hour']:02d}:{self.schedule_config['second_execution']['minute']:02d}")
    
    def setup_logging(self):
        """Configurar logging del scheduler"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(__file__).parent.parent / 'logs' / f"bimonthly_scheduler_{timestamp}.log"
        
        # Asegurar directorio de logs
        log_file.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | SCHEDULER | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def load_config(self, config_path: Path) -> Dict:
        """Cargar configuración"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            self.logger.error(f"❌ Error cargando configuración: {e}")
            raise
    
    def load_execution_history(self) -> List[Dict]:
        """Cargar historial de ejecuciones"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                self.logger.info(f"📂 Historial cargado: {len(history)} ejecuciones")
                return history
            else:
                self.logger.info("📂 No hay historial previo")
                return []
        except Exception as e:
            self.logger.warning(f"⚠️  Error cargando historial: {e}")
            return []
    
    def save_execution_history(self):
        """Guardar historial de ejecuciones"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.execution_history, f, indent=2, ensure_ascii=False)
            self.logger.info("💾 Historial guardado")
        except Exception as e:
            self.logger.error(f"❌ Error guardando historial: {e}")
    
    def should_execute_today(self) -> Optional[int]:
        """
        Verificar si hoy corresponde ejecutar y qué número de ejecución
        Retorna: 1 para primera ejecución del mes, 2 para segunda, None si no corresponde
        """
        today = datetime.now()
        current_day = today.day
        
        # Verificar primera ejecución del mes (días 1-2)
        if current_day in self.schedule_config['first_execution']['day_of_month']:
            return 1
        
        # Verificar segunda ejecución del mes (días 15-16)
        if current_day in self.schedule_config['second_execution']['day_of_month']:
            return 2
        
        return None
    
    def was_already_executed_today(self, execution_number: int) -> bool:
        """Verificar si ya se ejecutó hoy"""
        today = datetime.now().date()
        
        for record in self.execution_history:
            execution_date = datetime.fromisoformat(record['start_time']).date()
            if execution_date == today and record['execution_number'] == execution_number:
                self.logger.info(f"✅ Ya se ejecutó hoy la ejecución #{execution_number}")
                return True
        
        return False
    
    def create_execution_plan(self, execution_number: int) -> List[Dict]:
        """Crear plan de ejecución para scrapers"""
        
        # Configuración base de scrapers
        base_scrapers = [
            {
                'site': 'inmuebles24',
                'operation': 'venta',
                'headless': True,
                'max_pages': 100,  # Páginas completas para producción
                'priority': 1
            },
            {
                'site': 'inmuebles24', 
                'operation': 'renta',
                'headless': True,
                'max_pages': 100,
                'priority': 1
            }
        ]
        
        # TODO: Agregar más scrapers cuando estén implementados
        # {
        #     'site': 'casas_y_terrenos',
        #     'operation': 'venta',
        #     'headless': True,
        #     'max_pages': 50,
        #     'priority': 2
        # }
        
        self.logger.info(f"📋 Plan de ejecución #{execution_number} creado:")
        for i, scraper in enumerate(base_scrapers, 1):
            self.logger.info(f"   {i}. {scraper['site']} - {scraper['operation']} ({scraper['max_pages']} páginas)")
        
        return base_scrapers
    
    def execute_scrapers_remotely(self, execution_number: int, scraper_plan: List[Dict]) -> Dict:
        """Ejecutar scrapers remotamente en Dell T710"""
        execution_id = f"bimonthly_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        execution_record = {
            'execution_id': execution_id,
            'execution_number': execution_number,
            'start_time': datetime.now().isoformat(),
            'scraper_plan': scraper_plan,
            'results': {},
            'success': False,
            'total_properties': 0,
            'errors': []
        }
        
        try:
            self.logger.info(f"🚀 Iniciando ejecución bi-mensual #{execution_number}")
            self.logger.info(f"   ID: {execution_id}")
            self.logger.info(f"   Scrapers planificados: {len(scraper_plan)}")
            
            # Usar SSH executor para ejecución remota
            with DellT710SSHExecutor() as ssh_executor:
                
                # Verificar estado del sistema antes de empezar
                status = ssh_executor.get_remote_status()
                if not status.get('connected', False):
                    raise Exception("No se pudo conectar al Dell T710")
                
                self.logger.info(f"🖥️  Sistema remoto disponible")
                
                # Ejecutar cada scraper
                for i, scraper_config in enumerate(scraper_plan, 1):
                    scraper_id = f"{scraper_config['site']}_{scraper_config['operation']}"
                    
                    self.logger.info(f"🔄 Ejecutando scraper {i}/{len(scraper_plan)}: {scraper_id}")
                    
                    try:
                        # Ejecutar scraper remotamente
                        result = ssh_executor.execute_scraper(
                            scraper_config['site'],
                            scraper_config
                        )
                        
                        execution_record['results'][scraper_id] = result
                        
                        if result['success']:
                            self.logger.info(f"✅ Scraper {scraper_id} completado exitosamente")
                            # TODO: Extraer número de propiedades del stdout
                        else:
                            self.logger.error(f"❌ Scraper {scraper_id} falló")
                            execution_record['errors'].append(f"Scraper {scraper_id} falló: {result.get('error', 'Unknown')}")
                        
                    except Exception as e:
                        error_msg = f"Error ejecutando {scraper_id}: {str(e)}"
                        self.logger.error(f"❌ {error_msg}")
                        execution_record['errors'].append(error_msg)
            
            # Calcular estadísticas finales
            successful_scrapers = sum(1 for r in execution_record['results'].values() if r.get('success', False))
            total_scrapers = len(scraper_plan)
            success_rate = (successful_scrapers / total_scrapers) * 100 if total_scrapers > 0 else 0
            
            execution_record['success'] = successful_scrapers > 0
            execution_record['success_rate'] = success_rate
            execution_record['successful_scrapers'] = successful_scrapers
            execution_record['total_scrapers'] = total_scrapers
            
        except Exception as e:
            error_msg = f"Error fatal en ejecución: {str(e)}"
            self.logger.error(f"❌ {error_msg}")
            execution_record['errors'].append(error_msg)
        
        finally:
            execution_record['end_time'] = datetime.now().isoformat()
            execution_record['duration_seconds'] = (
                datetime.fromisoformat(execution_record['end_time']) - 
                datetime.fromisoformat(execution_record['start_time'])
            ).total_seconds()
        
        # Log final
        if execution_record['success']:
            self.logger.info(f"🎉 Ejecución #{execution_number} completada exitosamente")
            self.logger.info(f"   Scrapers exitosos: {execution_record.get('successful_scrapers', 0)}/{execution_record.get('total_scrapers', 0)}")
            self.logger.info(f"   Duración: {execution_record['duration_seconds']:.1f} segundos")
        else:
            self.logger.error(f"❌ Ejecución #{execution_number} falló")
            for error in execution_record['errors']:
                self.logger.error(f"   {error}")
        
        return execution_record
    
    def run_scheduled_execution(self):
        """Ejecutar scraping programado si corresponde"""
        try:
            # Cargar historial
            self.execution_history = self.load_execution_history()
            
            # Verificar si corresponde ejecutar hoy
            execution_number = self.should_execute_today()
            
            if execution_number is None:
                self.logger.info(f"📅 Hoy no corresponde ejecución programada")
                return
            
            # Verificar si ya se ejecutó hoy
            if self.was_already_executed_today(execution_number):
                self.logger.info(f"✅ Ejecución #{execution_number} ya realizada hoy")
                return
            
            # Verificar hora
            now = datetime.now()
            if execution_number == 1:
                scheduled_hour = self.schedule_config['first_execution']['hour']
                scheduled_minute = self.schedule_config['first_execution']['minute']
            else:
                scheduled_hour = self.schedule_config['second_execution']['hour']
                scheduled_minute = self.schedule_config['second_execution']['minute']
            
            # Permitir ejecución si es después de la hora programada
            if now.hour < scheduled_hour or (now.hour == scheduled_hour and now.minute < scheduled_minute):
                self.logger.info(f"⏰ Esperando hora programada: {scheduled_hour:02d}:{scheduled_minute:02d}")
                return
            
            self.logger.info(f"🎯 Iniciando ejecución programada #{execution_number}")
            
            # Crear plan de ejecución
            scraper_plan = self.create_execution_plan(execution_number)
            
            # Ejecutar scrapers
            execution_record = self.execute_scrapers_remotely(execution_number, scraper_plan)
            
            # Guardar en historial
            self.execution_history.append(execution_record)
            self.save_execution_history()
            
        except Exception as e:
            self.logger.error(f"❌ Error en ejecución programada: {e}")
    
    def start_scheduler(self):
        """Iniciar el scheduler en background"""
        if self.running:
            self.logger.warning("⚠️  Scheduler ya está ejecutándose")
            return
        
        self.running = True
        
        # Programar verificaciones cada hora
        schedule.every().hour.do(self.run_scheduled_execution)
        
        def scheduler_loop():
            self.logger.info("🔄 Scheduler iniciado - verificando cada hora")
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Verificar cada minuto
                except Exception as e:
                    self.logger.error(f"❌ Error en scheduler loop: {e}")
                    time.sleep(300)  # Esperar 5 minutos en caso de error
        
        self.scheduler_thread = threading.Thread(target=scheduler_loop, name="BiMonthlyScheduler")
        self.scheduler_thread.start()
        
        self.logger.info("✅ Scheduler iniciado exitosamente")
    
    def stop_scheduler(self):
        """Detener el scheduler"""
        if not self.running:
            return
        
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        schedule.clear()
        self.logger.info("⏹️  Scheduler detenido")
    
    def get_next_execution_info(self) -> Dict:
        """Obtener información de la próxima ejecución"""
        now = datetime.now()
        current_day = now.day
        
        # Determinar próxima ejecución
        if current_day < 15:
            # Próxima es la segunda del mes actual
            next_execution = 2
            next_days = self.schedule_config['second_execution']['day_of_month']
            next_hour = self.schedule_config['second_execution']['hour']
            next_minute = self.schedule_config['second_execution']['minute']
            next_month = now.month
            next_year = now.year
        else:
            # Próxima es la primera del mes siguiente
            next_execution = 1
            next_days = self.schedule_config['first_execution']['day_of_month']
            next_hour = self.schedule_config['first_execution']['hour']
            next_minute = self.schedule_config['first_execution']['minute']
            
            if now.month == 12:
                next_month = 1
                next_year = now.year + 1
            else:
                next_month = now.month + 1
                next_year = now.year
        
        # Calcular fecha exacta (primer día disponible)
        next_date = datetime(next_year, next_month, next_days[0], next_hour, next_minute)
        
        time_until = next_date - now
        
        return {
            'execution_number': next_execution,
            'date': next_date.isoformat(),
            'days_until': time_until.days,
            'hours_until': time_until.total_seconds() / 3600,
            'formatted_date': next_date.strftime('%Y-%m-%d %H:%M'),
            'description': f"Ejecución #{next_execution} del mes"
        }

def main():
    """Función principal para testing y control del scheduler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bi-Monthly Scheduler for PropertyScraper Dell710')
    parser.add_argument('--start', action='store_true', help='Iniciar scheduler en background')
    parser.add_argument('--run-now', action='store_true', help='Ejecutar scraping inmediatamente')
    parser.add_argument('--status', action='store_true', help='Mostrar estado y próxima ejecución')
    parser.add_argument('--history', action='store_true', help='Mostrar historial de ejecuciones')
    
    args = parser.parse_args()
    
    scheduler = BiMonthlyScheduler()
    
    if args.start:
        print("🚀 Iniciando scheduler bi-mensual...")
        scheduler.start_scheduler()
        
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n⏹️  Deteniendo scheduler...")
            scheduler.stop_scheduler()
    
    elif args.run_now:
        print("▶️  Ejecutando scraping inmediatamente...")
        scheduler.run_scheduled_execution()
    
    elif args.status:
        next_info = scheduler.get_next_execution_info()
        print(f"\n📊 Estado del Scheduler:")
        print(f"   Próxima ejecución: {next_info['description']}")
        print(f"   Fecha: {next_info['formatted_date']}")
        print(f"   En {next_info['days_until']} días ({next_info['hours_until']:.1f} horas)")
    
    elif args.history:
        scheduler.execution_history = scheduler.load_execution_history()
        print(f"\n📚 Historial de Ejecuciones ({len(scheduler.execution_history)} registros):")
        
        for record in scheduler.execution_history[-10:]:  # Últimas 10
            start_time = datetime.fromisoformat(record['start_time'])
            success_icon = "✅" if record.get('success', False) else "❌"
            print(f"   {success_icon} {start_time.strftime('%Y-%m-%d %H:%M')} - Ejecución #{record['execution_number']} - {record.get('successful_scrapers', 0)}/{record.get('total_scrapers', 0)} scrapers")
    
    else:
        print("Use --start, --run-now, --status, o --history")

if __name__ == "__main__":
    main()
