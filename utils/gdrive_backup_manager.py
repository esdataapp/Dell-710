#!/usr/bin/env python3
"""
Google Drive Backup Manager - PropertyScraper Dell710
Sistema de respaldo automático usando rclone hacia Google Drive
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

class GoogleDriveBackupManager:
    """
    Gestor de respaldos automáticos hacia Google Drive
    Utiliza rclone para sincronizar archivos CSV sin interrumpir scrapers
    """
    
    def __init__(self, config_path=None):
        self.setup_logging()
        
        # Configuración
        self.config = self.load_config(config_path)
        
        # Rutas del sistema
        self.project_root = Path('/home/scraper/PropertyScraper-Dell710') if os.path.exists('/home/scraper') else Path(__file__).parent.parent
        self.data_dir = self.project_root / 'data'
        
        # Configuración de rclone
        self.rclone_remote = 'gdrive'
        self.rclone_base_path = 'PropertyScraper-Dell710-Data'
        
        # Control de respaldos
        self.backup_queue = []
        self.backup_thread = None
        self.backup_running = False
        self.backup_interval = 300  # 5 minutos
        
        # Historial de respaldos
        self.backup_history = []
        self.history_file = self.project_root / 'logs' / 'backup_history.json'
        
        self.logger.info("☁️  Google Drive Backup Manager inicializado")
        self.logger.info(f"   Directorio de datos: {self.data_dir}")
        self.logger.info(f"   Remote rclone: {self.rclone_remote}")
        self.logger.info(f"   Ruta base Drive: {self.rclone_base_path}")
    
    def setup_logging(self):
        """Configurar logging específico para backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Determinar directorio de logs
        if os.path.exists('/home/scraper/PropertyScraper-Dell710/logs'):
            log_dir = Path('/home/scraper/PropertyScraper-Dell710/logs')
        else:
            log_dir = Path(__file__).parent.parent / 'logs'
        
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"gdrive_backup_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | BACKUP | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def load_config(self, config_path):
        """Cargar configuración del sistema"""
        try:
            if config_path is None:
                config_path = Path(__file__).parent.parent / 'config' / 'dell_t710_config.yaml'
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                return {}
        except Exception as e:
            self.logger.warning(f"⚠️  Error cargando configuración: {e}")
            return {}
    
    def check_rclone_config(self) -> bool:
        """Verificar configuración de rclone"""
        try:
            result = subprocess.run(['rclone', 'listremotes'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                remotes = result.stdout.strip().split('\n')
                if f'{self.rclone_remote}:' in remotes:
                    self.logger.info(f"✅ rclone configurado correctamente: {self.rclone_remote}")
                    return True
                else:
                    self.logger.error(f"❌ Remote {self.rclone_remote} no encontrado en rclone")
                    return False
            else:
                self.logger.error(f"❌ Error ejecutando rclone: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error verificando rclone: {e}")
            return False
    
    def get_csv_files_to_backup(self) -> List[Tuple[Path, str]]:
        """Obtener lista de archivos CSV para respaldar"""
        csv_files = []
        
        try:
            # Buscar todos los archivos CSV en la estructura de datos
            for csv_file in self.data_dir.rglob('*.csv'):
                # Calcular ruta relativa desde data_dir
                relative_path = csv_file.relative_to(self.data_dir)
                
                # Construir ruta de destino en Google Drive
                gdrive_path = f"{self.rclone_base_path}/{relative_path}"
                
                csv_files.append((csv_file, gdrive_path))
            
            self.logger.debug(f"📄 Encontrados {len(csv_files)} archivos CSV para respaldo")
            return csv_files
            
        except Exception as e:
            self.logger.error(f"❌ Error buscando archivos CSV: {e}")
            return []
    
    def backup_file_to_gdrive(self, local_file: Path, gdrive_path: str) -> bool:
        """Respaldar archivo individual a Google Drive"""
        try:
            # Verificar que el archivo local existe
            if not local_file.exists():
                self.logger.warning(f"⚠️  Archivo no existe: {local_file}")
                return False
            
            # Crear directorio remoto si no existe
            gdrive_dir = '/'.join(gdrive_path.split('/')[:-1])
            mkdir_cmd = ['rclone', 'mkdir', f'{self.rclone_remote}:{gdrive_dir}']
            
            subprocess.run(mkdir_cmd, capture_output=True, timeout=60)
            
            # Comando de copia
            copy_cmd = [
                'rclone', 'copy',
                str(local_file),
                f'{self.rclone_remote}:{gdrive_dir}',
                '--progress'
            ]
            
            self.logger.debug(f"☁️  Respaldando: {local_file.name} → {gdrive_path}")
            
            result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info(f"✅ Respaldado exitosamente: {local_file.name}")
                return True
            else:
                self.logger.error(f"❌ Error respaldando {local_file.name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏱️  Timeout respaldando {local_file.name}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error respaldando {local_file.name}: {e}")
            return False
    
    def backup_directory_structure(self) -> bool:
        """Respaldar estructura completa de directorios"""
        try:
            self.logger.info("📁 Creando estructura de directorios en Google Drive...")
            
            # Obtener todas las carpetas en data/
            directories = []
            for item in self.data_dir.rglob('*'):
                if item.is_dir():
                    relative_path = item.relative_to(self.data_dir)
                    gdrive_path = f"{self.rclone_base_path}/{relative_path}"
                    directories.append(gdrive_path)
            
            # Crear directorios en lotes
            for directory in directories:
                mkdir_cmd = ['rclone', 'mkdir', f'{self.rclone_remote}:{directory}']
                
                try:
                    result = subprocess.run(mkdir_cmd, capture_output=True, timeout=30)
                    if result.returncode == 0:
                        self.logger.debug(f"📁 Creado: {directory}")
                except:
                    pass  # Ignorar errores (directorio ya existe)
            
            self.logger.info(f"✅ Estructura de directorios creada: {len(directories)} carpetas")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error creando estructura: {e}")
            return False
    
    def backup_website_data(self, website: str, operation: str) -> Dict:
        """Respaldar datos específicos de un website y operación usando rclone copy específico"""
        try:
            self.logger.info(f"☁️  Respaldando datos: {website}/{operation}")
            
            # Construir ruta local
            local_path = self.data_dir / website / operation
            
            if not local_path.exists():
                self.logger.warning(f"⚠️  Directorio no existe: {local_path}")
                return {'success': False, 'error': 'Directory not found'}
            
            # Usar comando rclone copy directo según tu especificación
            # rclone copy /home/esdata/(Directorio) /(Nombre del Archivo) gdrive:/(Directorio)/
            gdrive_dest = f"{self.rclone_base_path}/{website}/{operation}"
            
            # Comando específico para directorio completo
            copy_cmd = [
                'rclone', 'copy',
                str(local_path),
                f'{self.rclone_remote}:{gdrive_dest}',
                '--include', '*.csv',
                '--progress',
                '--transfers', '4',
                '--checkers', '8'
            ]
            
            self.logger.info(f"🔄 Ejecutando: rclone copy {local_path} {self.rclone_remote}:{gdrive_dest}")
            
            result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Contar archivos CSV respaldados
                csv_files = list(local_path.rglob('*.csv'))
                
                self.logger.info(f"✅ Respaldo exitoso: {website}/{operation}")
                self.logger.info(f"   Archivos CSV: {len(csv_files)}")
                
                return {
                    'success': True,
                    'files_backed_up': len(csv_files),
                    'website': website,
                    'operation': operation,
                    'gdrive_path': gdrive_dest
                }
            else:
                self.logger.error(f"❌ Error en rclone copy: {result.stderr}")
                return {
                    'success': False, 
                    'error': result.stderr,
                    'website': website,
                    'operation': operation
                }
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏱️  Timeout respaldando {website}/{operation}")
            return {'success': False, 'error': 'Backup timeout'}
        except Exception as e:
            self.logger.error(f"❌ Error respaldando {website}/{operation}: {e}")
            return {'success': False, 'error': str(e)}

    def perform_backup_batch(self, csv_files: List[Tuple[Path, str]]) -> Dict:
        """Realizar respaldo en lote de archivos CSV"""
        backup_results = {
            'total_files': len(csv_files),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'start_time': datetime.now().isoformat()
        }
        
        try:
            self.logger.info(f"☁️  Iniciando respaldo de {len(csv_files)} archivos CSV...")
            
            # Crear estructura de directorios primero
            self.backup_directory_structure()
            
            # Respaldar archivos individuales
            for local_file, gdrive_path in csv_files:
                try:
                    if self.backup_file_to_gdrive(local_file, gdrive_path):
                        backup_results['successful'] += 1
                    else:
                        backup_results['failed'] += 1
                        backup_results['errors'].append(f"Failed: {local_file.name}")
                    
                    # Pequeña pausa para no saturar
                    time.sleep(1)
                    
                except Exception as e:
                    backup_results['failed'] += 1
                    backup_results['errors'].append(f"Error {local_file.name}: {str(e)}")
                    self.logger.error(f"❌ Error respaldando {local_file.name}: {e}")
            
            backup_results['end_time'] = datetime.now().isoformat()
            backup_results['duration_seconds'] = (
                datetime.fromisoformat(backup_results['end_time']) - 
                datetime.fromisoformat(backup_results['start_time'])
            ).total_seconds()
            
            # Log resumen
            success_rate = (backup_results['successful'] / backup_results['total_files']) * 100 if backup_results['total_files'] > 0 else 0
            
            self.logger.info(f"📊 Respaldo completado:")
            self.logger.info(f"   Total archivos: {backup_results['total_files']}")
            self.logger.info(f"   Exitosos: {backup_results['successful']}")
            self.logger.info(f"   Fallidos: {backup_results['failed']}")
            self.logger.info(f"   Tasa de éxito: {success_rate:.1f}%")
            self.logger.info(f"   Duración: {backup_results['duration_seconds']:.1f}s")
            
            return backup_results
            
        except Exception as e:
            self.logger.error(f"❌ Error en respaldo batch: {e}")
            backup_results['errors'].append(f"Batch error: {str(e)}")
            return backup_results
    
    def save_backup_history(self, backup_result: Dict):
        """Guardar historial de respaldos"""
        try:
            # Cargar historial existente
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.backup_history = json.load(f)
            
            # Agregar nuevo respaldo
            self.backup_history.append(backup_result)
            
            # Mantener solo últimos 100 respaldos
            if len(self.backup_history) > 100:
                self.backup_history = self.backup_history[-100:]
            
            # Guardar historial actualizado
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.backup_history, f, indent=2, ensure_ascii=False)
            
            self.logger.debug("💾 Historial de respaldos actualizado")
            
        except Exception as e:
            self.logger.warning(f"⚠️  Error guardando historial: {e}")
    
    def run_backup_now(self) -> Dict:
        """Ejecutar respaldo inmediato"""
        try:
            self.logger.info("🚀 Iniciando respaldo inmediato a Google Drive...")
            
            # Verificar rclone
            if not self.check_rclone_config():
                return {
                    'success': False,
                    'error': 'rclone no configurado correctamente'
                }
            
            # Obtener archivos para respaldar
            csv_files = self.get_csv_files_to_backup()
            
            if not csv_files:
                self.logger.info("📄 No hay archivos CSV para respaldar")
                return {
                    'success': True,
                    'message': 'No hay archivos para respaldar',
                    'total_files': 0
                }
            
            # Realizar respaldo
            backup_result = self.perform_backup_batch(csv_files)
            backup_result['success'] = backup_result['failed'] == 0
            
            # Guardar en historial
            self.save_backup_history(backup_result)
            
            return backup_result
            
        except Exception as e:
            self.logger.error(f"❌ Error en respaldo inmediato: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def start_automatic_backup(self):
        """Iniciar respaldo automático en background"""
        if self.backup_running:
            self.logger.warning("⚠️  Respaldo automático ya está ejecutándose")
            return False
        
        self.backup_running = True
        
        def backup_loop():
            self.logger.info(f"🔄 Respaldo automático iniciado (cada {self.backup_interval}s)")
            
            while self.backup_running:
                try:
                    # Verificar si hay archivos nuevos
                    csv_files = self.get_csv_files_to_backup()
                    
                    if csv_files:
                        # Filtrar solo archivos modificados recientemente
                        recent_files = []
                        cutoff_time = datetime.now() - timedelta(minutes=self.backup_interval // 60 + 5)
                        
                        for local_file, gdrive_path in csv_files:
                            try:
                                file_mtime = datetime.fromtimestamp(local_file.stat().st_mtime)
                                if file_mtime > cutoff_time:
                                    recent_files.append((local_file, gdrive_path))
                            except:
                                pass
                        
                        if recent_files:
                            self.logger.info(f"☁️  Respaldando {len(recent_files)} archivos nuevos/modificados")
                            backup_result = self.perform_backup_batch(recent_files)
                            self.save_backup_history(backup_result)
                        else:
                            self.logger.debug("📄 No hay archivos nuevos para respaldar")
                    
                    # Esperar siguiente intervalo
                    time.sleep(self.backup_interval)
                    
                except Exception as e:
                    self.logger.error(f"❌ Error en loop de respaldo: {e}")
                    time.sleep(60)  # Esperar 1 minuto en caso de error
        
        # Iniciar thread
        self.backup_thread = threading.Thread(target=backup_loop, name="GoogleDriveBackup")
        self.backup_thread.start()
        
        self.logger.info("✅ Respaldo automático iniciado")
        return True
    
    def stop_automatic_backup(self):
        """Detener respaldo automático"""
        if not self.backup_running:
            return
        
        self.backup_running = False
        
        if self.backup_thread:
            self.backup_thread.join(timeout=30)
        
        self.logger.info("⏹️  Respaldo automático detenido")
    
    def get_backup_status(self) -> Dict:
        """Obtener estado actual del sistema de respaldo"""
        try:
            # Estadísticas básicas
            csv_files = self.get_csv_files_to_backup()
            
            # Último respaldo
            last_backup = None
            if self.backup_history:
                last_backup = self.backup_history[-1]
            
            # Estado de rclone
            rclone_ok = self.check_rclone_config()
            
            return {
                'backup_running': self.backup_running,
                'rclone_configured': rclone_ok,
                'total_csv_files': len(csv_files),
                'backup_interval_seconds': self.backup_interval,
                'last_backup': last_backup,
                'backup_history_count': len(self.backup_history),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

def main():
    """Función principal para testing y control del backup manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Drive Backup Manager')
    parser.add_argument('--backup-now', action='store_true', help='Ejecutar respaldo inmediato')
    parser.add_argument('--start-auto', action='store_true', help='Iniciar respaldo automático')
    parser.add_argument('--status', action='store_true', help='Mostrar estado del sistema')
    parser.add_argument('--list-files', action='store_true', help='Listar archivos para respaldar')
    parser.add_argument('--test-rclone', action='store_true', help='Probar configuración rclone')
    
    args = parser.parse_args()
    
    backup_manager = GoogleDriveBackupManager()
    
    if args.backup_now:
        print("☁️  Ejecutando respaldo inmediato...")
        result = backup_manager.run_backup_now()
        
        if result['success']:
            print(f"✅ Respaldo completado exitosamente")
            print(f"   Archivos respaldados: {result.get('successful', 0)}")
            print(f"   Duración: {result.get('duration_seconds', 0):.1f}s")
        else:
            print(f"❌ Error en respaldo: {result.get('error', 'Unknown')}")
    
    elif args.start_auto:
        print("🔄 Iniciando respaldo automático...")
        backup_manager.start_automatic_backup()
        
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n⏹️  Deteniendo respaldo automático...")
            backup_manager.stop_automatic_backup()
    
    elif args.status:
        status = backup_manager.get_backup_status()
        print("\n📊 Estado del Sistema de Respaldo:")
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif args.list_files:
        csv_files = backup_manager.get_csv_files_to_backup()
        print(f"\n📄 Archivos CSV para respaldar ({len(csv_files)}):")
        
        for local_file, gdrive_path in csv_files[:20]:  # Mostrar primeros 20
            print(f"   {local_file.name} → {gdrive_path}")
        
        if len(csv_files) > 20:
            print(f"   ... y {len(csv_files) - 20} archivos más")
    
    elif args.test_rclone:
        print("🧪 Probando configuración rclone...")
        if backup_manager.check_rclone_config():
            print("✅ rclone configurado correctamente")
        else:
            print("❌ Error en configuración rclone")
    
    else:
        print("Use --backup-now, --start-auto, --status, --list-files, o --test-rclone")

if __name__ == "__main__":
    main()
