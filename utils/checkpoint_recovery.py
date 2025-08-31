#!/usr/bin/env python3
"""
Checkpoint Recovery System - PropertyScraper Dell710
Sistema de recuperación automática tras interrupciones (apagones, desconexiones)
"""

import os
import sys
import json
import time
import pickle
import logging
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Agregar paths del proyecto
sys.path.append(str(Path(__file__).parent.parent))
from utils.enhanced_scraps_registry import EnhancedScrapsRegistry

class CheckpointRecoverySystem:
    """
    Sistema de recuperación que maneja:
    - Checkpoints automáticos cada N páginas
    - Recuperación tras apagones/desconexiones
    - Restauración del estado del orquestador
    - Continuación desde el último punto guardado
    """
    
    def __init__(self):
        self.setup_logging()
        
        # Componentes
        self.registry = EnhancedScrapsRegistry()
        
        # Directorios de checkpoint
        self.project_root = Path(__file__).parent.parent
        self.checkpoint_dir = self.project_root / 'logs' / 'checkpoints'
        self.recovery_dir = self.project_root / 'logs' / 'recovery'
        
        # Crear directorios
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivos de estado
        self.orchestrator_checkpoint = self.checkpoint_dir / 'orchestrator_state.json'
        self.scrapers_checkpoint = self.checkpoint_dir / 'active_scrapers.json'
        self.system_state_file = self.checkpoint_dir / 'system_state.json'
        
        # Configuración
        self.checkpoint_interval = 300  # 5 minutos
        self.max_recovery_attempts = 3
        
        self.logger.info("🔄 Checkpoint Recovery System inicializado")
        self.logger.info(f"   Checkpoint dir: {self.checkpoint_dir}")
        self.logger.info(f"   Recovery dir: {self.recovery_dir}")
    
    def setup_logging(self):
        """Configurar logging del sistema de recuperación"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(__file__).parent.parent / 'logs' / f'checkpoint_recovery_{timestamp}.log'
        log_file.parent.mkdir(exist_ok=True, parents=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | RECOVERY | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)

    def load_registry_data(self) -> List[Dict]:
        """Cargar datos completos del registry"""
        try:
            if not self.registry.registry_file.exists():
                return []
            with open(self.registry.registry_file, 'r', encoding='utf-8') as f:
                return list(csv.DictReader(f))
        except Exception as e:
            self.logger.error(f"❌ Error cargando registry: {e}")
            return []

    def reset_scrap_status(self, scrap_id: str) -> bool:
        """Restablecer estado de un scrap a 'Pendiente'"""
        try:
            if not self.registry.registry_file.exists():
                return False

            rows = []
            updated = False
            with open(self.registry.registry_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row['id'] == scrap_id:
                        row['ultimo_estado'] = 'Pendiente'
                        row['ultima_ejecucion'] = ''
                        row['proxima_ejecucion'] = ''
                        updated = True
                    rows.append(row)

            if updated:
                with open(self.registry.registry_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

            return updated

        except Exception as e:
            self.logger.error(f"❌ Error restableciendo scrap {scrap_id}: {e}")
            return False
    
    def create_system_checkpoint(self, orchestrator_state: Dict = None, active_scrapers: List[Dict] = None) -> bool:
        """Crear checkpoint completo del sistema"""
        try:
            checkpoint_data = {
                'timestamp': datetime.now().isoformat(),
                'system_info': self.get_system_state(),
                'orchestrator_state': orchestrator_state or {},
                'active_scrapers': active_scrapers or [],
                'registry_stats': self.registry.get_registry_stats(),
                'checkpoint_version': '1.0'
            }
            
            # Guardar checkpoint principal
            with open(self.system_state_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            # Crear copia de seguridad con timestamp
            backup_file = self.checkpoint_dir / f'system_checkpoint_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("💾 Checkpoint del sistema creado")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error creando checkpoint: {e}")
            return False
    
    def get_system_state(self) -> Dict:
        """Obtener estado actual del sistema"""
        try:
            import psutil
            
            # CPU y memoria
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # Procesos Python activos (scrapers)
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        
                        # Buscar scrapers conocidos
                        scraper_names = [
                            'inmuebles24_professional', 'casas_y_terrenos_scraper',
                            'lamudi_professional', 'mitula_scraper',
                            'propiedades_professional', 'segundamano_professional',
                            'trovit_professional', 'advanced_orchestrator'
                        ]
                        
                        for scraper_name in scraper_names:
                            if scraper_name in cmdline:
                                python_processes.append({
                                    'pid': proc.info['pid'],
                                    'script': scraper_name,
                                    'cmdline': cmdline,
                                    'start_time': datetime.fromtimestamp(proc.info['create_time']).isoformat()
                                })
                                break
                except:
                    continue
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'python_processes': python_processes,
                'active_scrapers_count': len(python_processes),
                'system_uptime': time.time() - psutil.boot_time()
            }
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error obteniendo estado del sistema: {e}")
            return {'error': str(e)}
    
    def save_orchestrator_checkpoint(self, orchestrator_state: Dict) -> bool:
        """Guardar checkpoint específico del orquestador"""
        try:
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'orchestrator_state': orchestrator_state,
                'active_websites': orchestrator_state.get('active_websites', []),
                'completed_count': orchestrator_state.get('completed_count', 0),
                'failed_count': orchestrator_state.get('failed_count', 0)
            }
            
            with open(self.orchestrator_checkpoint, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            
            self.logger.debug("💾 Orchestrator checkpoint guardado")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando orchestrator checkpoint: {e}")
            return False
    
    def save_scraper_checkpoint(self, scraper_id: str, progress_data: Dict) -> bool:
        """Guardar checkpoint de un scraper específico"""
        try:
            checkpoint_file = self.checkpoint_dir / f'scraper_{scraper_id}_checkpoint.pkl'
            
            checkpoint_data = {
                'timestamp': datetime.now().isoformat(),
                'scraper_id': scraper_id,
                'progress': progress_data,
                'current_page': progress_data.get('current_page', 0),
                'properties_scraped': progress_data.get('properties_scraped', 0),
                'last_successful_url': progress_data.get('last_successful_url', ''),
                'session_data': progress_data.get('session_data', {})
            }
            
            # Guardar en formato pickle para preservar objetos Python
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            
            # También guardar versión JSON legible
            json_file = self.checkpoint_dir / f'scraper_{scraper_id}_checkpoint.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({k: v for k, v in checkpoint_data.items() if k != 'session_data'}, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"💾 Scraper checkpoint guardado: {scraper_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando scraper checkpoint {scraper_id}: {e}")
            return False
    
    def detect_interruption(self) -> Dict:
        """Detectar si hubo una interrupción del sistema"""
        try:
            # Verificar si existen checkpoints
            if not self.system_state_file.exists():
                return {'interrupted': False, 'reason': 'No previous execution'}
            
            # Cargar último checkpoint
            with open(self.system_state_file, 'r', encoding='utf-8') as f:
                last_checkpoint = json.load(f)
            
            last_timestamp = datetime.fromisoformat(last_checkpoint['timestamp'])
            time_since_checkpoint = datetime.now() - last_timestamp
            
            # Buscar procesos activos del checkpoint anterior
            previous_processes = last_checkpoint.get('system_info', {}).get('python_processes', [])
            current_processes = self.get_system_state().get('python_processes', [])
            
            # Comparar PIDs
            previous_pids = {p['pid'] for p in previous_processes}
            current_pids = {p['pid'] for p in current_processes}
            
            missing_processes = []
            for proc in previous_processes:
                if proc['pid'] not in current_pids:
                    missing_processes.append(proc)
            
            # Determinar si hubo interrupción
            interrupted = False
            reasons = []
            
            # Tiempo excesivo desde último checkpoint
            if time_since_checkpoint > timedelta(minutes=30):
                interrupted = True
                reasons.append(f"Long time since last checkpoint: {time_since_checkpoint}")
            
            # Procesos faltantes
            if missing_processes:
                interrupted = True
                reasons.append(f"Missing processes: {len(missing_processes)}")
            
            # Verificar scraps en progreso en registry
            scraps = self.load_registry_data()
            in_progress = [s for s in scraps if s.get('ultimo_estado', '').lower() == 'en_progreso']

            if in_progress:
                interrupted = True
                reasons.append(f"Scraps in progress: {len(in_progress)}")

            return {
                'interrupted': interrupted,
                'reasons': reasons,
                'last_checkpoint': last_checkpoint,
                'time_since_checkpoint': str(time_since_checkpoint),
                'missing_processes': missing_processes,
                'in_progress_scraps': len(in_progress)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error detectando interrupción: {e}")
            return {'interrupted': False, 'error': str(e)}
    
    def recover_orchestrator_state(self) -> Optional[Dict]:
        """Recuperar estado del orquestador desde checkpoint"""
        try:
            if not self.orchestrator_checkpoint.exists():
                self.logger.info("📋 No hay checkpoint del orquestador")
                return None
            
            with open(self.orchestrator_checkpoint, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            orchestrator_state = checkpoint['orchestrator_state']
            checkpoint_time = datetime.fromisoformat(checkpoint['timestamp'])
            
            self.logger.info(f"🔄 Recuperando estado del orquestador desde: {checkpoint_time}")
            self.logger.info(f"   Active websites: {orchestrator_state.get('active_websites', [])}")
            self.logger.info(f"   Completed: {orchestrator_state.get('completed_count', 0)}")
            
            return orchestrator_state
            
        except Exception as e:
            self.logger.error(f"❌ Error recuperando estado del orquestador: {e}")
            return None
    
    def recover_scraper_state(self, scraper_id: str) -> Optional[Dict]:
        """Recuperar estado de un scraper específico"""
        try:
            checkpoint_file = self.checkpoint_dir / f'scraper_{scraper_id}_checkpoint.pkl'
            
            if not checkpoint_file.exists():
                self.logger.info(f"📋 No hay checkpoint para scraper: {scraper_id}")
                return None
            
            with open(checkpoint_file, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            progress = checkpoint_data['progress']
            checkpoint_time = datetime.fromisoformat(checkpoint_data['timestamp'])
            
            self.logger.info(f"🔄 Recuperando scraper {scraper_id} desde: {checkpoint_time}")
            self.logger.info(f"   Current page: {progress.get('current_page', 0)}")
            self.logger.info(f"   Properties scraped: {progress.get('properties_scraped', 0)}")
            
            return checkpoint_data
            
        except Exception as e:
            self.logger.error(f"❌ Error recuperando scraper {scraper_id}: {e}")
            return None
    
    def cleanup_old_checkpoints(self, days_old: int = 7):
        """Limpiar checkpoints antiguos"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_old)
            cleaned_count = 0
            
            for checkpoint_file in self.checkpoint_dir.glob('*checkpoint*.json'):
                try:
                    file_time = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        checkpoint_file.unlink()
                        cleaned_count += 1
                except:
                    continue
            
            for checkpoint_file in self.checkpoint_dir.glob('*checkpoint*.pkl'):
                try:
                    file_time = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        checkpoint_file.unlink()
                        cleaned_count += 1
                except:
                    continue
            
            if cleaned_count > 0:
                self.logger.info(f"🧹 Limpiados {cleaned_count} checkpoints antiguos")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error limpiando checkpoints: {e}")
    
    def create_recovery_report(self, interruption_data: Dict) -> str:
        """Crear reporte de recuperación"""
        try:
            report_file = self.recovery_dir / f'recovery_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            report = {
                'generated_at': datetime.now().isoformat(),
                'interruption_detected': interruption_data,
                'available_checkpoints': self.list_available_checkpoints(),
                'registry_stats': self.registry.get_registry_stats(),
                'recovery_actions_taken': [],
                'system_state': self.get_system_state()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 Reporte de recuperación creado: {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"❌ Error creando reporte: {e}")
            return ""
    
    def list_available_checkpoints(self) -> Dict:
        """Listar checkpoints disponibles"""
        try:
            checkpoints = {
                'system_checkpoints': [],
                'orchestrator_checkpoints': [],
                'scraper_checkpoints': []
            }
            
            # System checkpoints
            for checkpoint_file in self.checkpoint_dir.glob('system_checkpoint_*.json'):
                file_time = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                checkpoints['system_checkpoints'].append({
                    'file': checkpoint_file.name,
                    'timestamp': file_time.isoformat(),
                    'size_kb': checkpoint_file.stat().st_size / 1024
                })
            
            # Orchestrator checkpoint
            if self.orchestrator_checkpoint.exists():
                file_time = datetime.fromtimestamp(self.orchestrator_checkpoint.stat().st_mtime)
                checkpoints['orchestrator_checkpoints'].append({
                    'file': self.orchestrator_checkpoint.name,
                    'timestamp': file_time.isoformat(),
                    'size_kb': self.orchestrator_checkpoint.stat().st_size / 1024
                })
            
            # Scraper checkpoints
            for checkpoint_file in self.checkpoint_dir.glob('scraper_*_checkpoint.pkl'):
                file_time = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                scraper_id = checkpoint_file.stem.replace('scraper_', '').replace('_checkpoint', '')
                checkpoints['scraper_checkpoints'].append({
                    'scraper_id': scraper_id,
                    'file': checkpoint_file.name,
                    'timestamp': file_time.isoformat(),
                    'size_kb': checkpoint_file.stat().st_size / 1024
                })
            
            return checkpoints
            
        except Exception as e:
            self.logger.error(f"❌ Error listando checkpoints: {e}")
            return {}
    
    def auto_recovery_sequence(self) -> bool:
        """Ejecutar secuencia automática de recuperación"""
        try:
            self.logger.info("🔄 Iniciando secuencia de recuperación automática...")
            
            # 1. Detectar interrupción
            interruption_data = self.detect_interruption()
            
            if not interruption_data['interrupted']:
                self.logger.info("✅ No se detectó interrupción del sistema")
                return True
            
            self.logger.warning("⚠️ Interrupción detectada:")
            for reason in interruption_data['reasons']:
                self.logger.warning(f"   - {reason}")
            
            # 2. Crear reporte
            report_file = self.create_recovery_report(interruption_data)
            
            # 3. Recuperar scraps en progreso
            scraps = self.load_registry_data()
            in_progress = [s for s in scraps if s.get('ultimo_estado', '').lower() == 'en_progreso']

            recovery_count = 0
            for scrap in in_progress:
                try:
                    if self.reset_scrap_status(scrap['id']):
                        recovery_count += 1
                        self.logger.info(
                            f"🔄 Scraper recuperado: {scrap['website']} ({scrap['operacion']})"
                        )
                except Exception as e:
                    self.logger.error(f"❌ Error recuperando scrap {scrap.get('id')}: {e}")

            if recovery_count > 0:
                self.logger.info(f"✅ {recovery_count} scrapers marcados para recuperación")
            
            # 4. Limpiar checkpoints antiguos
            self.cleanup_old_checkpoints()
            
            # 5. Crear nuevo checkpoint del sistema
            self.create_system_checkpoint()
            
            self.logger.info("✅ Secuencia de recuperación completada")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en secuencia de recuperación: {e}")
            return False

def main():
    """Función principal del sistema de recuperación"""
    parser = argparse.ArgumentParser(description='Checkpoint Recovery System for PropertyScraper Dell710')
    
    parser.add_argument('--detect-interruption', action='store_true', help='Detect system interruption')
    parser.add_argument('--auto-recovery', action='store_true', help='Run automatic recovery sequence')
    parser.add_argument('--list-checkpoints', action='store_true', help='List available checkpoints')
    parser.add_argument('--cleanup-old', action='store_true', help='Cleanup old checkpoints')
    parser.add_argument('--create-checkpoint', action='store_true', help='Create system checkpoint')
    parser.add_argument('--recovery-report', action='store_true', help='Generate recovery report')
    
    args = parser.parse_args()
    
    recovery_system = CheckpointRecoverySystem()
    
    if args.detect_interruption:
        print("🔍 Detectando interrupciones del sistema...")
        interruption_data = recovery_system.detect_interruption()
        print(json.dumps(interruption_data, indent=2, ensure_ascii=False))
    
    elif args.auto_recovery:
        print("🔄 Ejecutando recuperación automática...")
        success = recovery_system.auto_recovery_sequence()
        if success:
            print("✅ Recuperación completada exitosamente")
        else:
            print("❌ Error en recuperación")
    
    elif args.list_checkpoints:
        print("📋 Checkpoints disponibles:")
        checkpoints = recovery_system.list_available_checkpoints()
        print(json.dumps(checkpoints, indent=2, ensure_ascii=False))
    
    elif args.cleanup_old:
        print("🧹 Limpiando checkpoints antiguos...")
        recovery_system.cleanup_old_checkpoints()
    
    elif args.create_checkpoint:
        print("💾 Creando checkpoint del sistema...")
        success = recovery_system.create_system_checkpoint()
        if success:
            print("✅ Checkpoint creado")
        else:
            print("❌ Error creando checkpoint")
    
    elif args.recovery_report:
        print("📄 Generando reporte de recuperación...")
        interruption_data = recovery_system.detect_interruption()
        report_file = recovery_system.create_recovery_report(interruption_data)
        print(f"📄 Reporte creado: {report_file}")
    
    else:
        print("\n🔄 Checkpoint Recovery System")
        print("="*40)
        print("\n📋 Comandos disponibles:")
        print("  --detect-interruption : Detectar interrupciones")
        print("  --auto-recovery      : Recuperación automática")
        print("  --list-checkpoints   : Listar checkpoints")
        print("  --cleanup-old        : Limpiar checkpoints antiguos")
        print("  --create-checkpoint  : Crear checkpoint")
        print("  --recovery-report    : Generar reporte")
        print("\n💡 Ejemplos:")
        print("  python checkpoint_recovery.py --detect-interruption")
        print("  python checkpoint_recovery.py --auto-recovery")

if __name__ == "__main__":
    main()
