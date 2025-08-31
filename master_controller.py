#!/usr/bin/env python3
"""
Master Control Script - PropertyScraper Dell710
Script principal que coordina todo el sistema desde Windows 11
"""

import os
import sys
import json
import time
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class MasterController:
    """
    Controlador maestro que maneja:
    - Conexión y monitoreo SSH
    - Lanzamiento y control de orquestador
    - Monitoreo visual en tiempo real
    - Recuperación automática tras interrupciones
    - Backup automático a Google Drive
    - Registro completo de actividades
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.ssh_host = "192.168.50.54"
        self.ssh_user = "esdata"
        
        # Estado del controlador
        self.connected = False
        self.orchestrator_running = False
        self.monitoring = False
        self.auto_recovery_enabled = True
        
        # Threads de control
        self.monitor_thread = None
        self.connection_monitor_thread = None
        self.auto_backup_thread = None
        
        # Archivos de estado
        self.state_file = self.project_root / 'data' / 'master_controller_state.json'
        self.session_log = self.project_root / 'logs' / f'session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Crear directorios necesarios
        self.state_file.parent.mkdir(exist_ok=True, parents=True)
        self.session_log.parent.mkdir(exist_ok=True, parents=True)
        
        self.setup_logging()
        
        print("🎛️ Master Controller - PropertyScraper Dell710")
        print(f"   Target: {self.ssh_user}@{self.ssh_host}")
        print(f"   Session log: {self.session_log}")
    
    def setup_logging(self):
        """Configurar logging de la sesión"""
        self.log_file = open(self.session_log, 'w', encoding='utf-8')
        self.log(f"🚀 Master Controller session started at {datetime.now()}")
    
    def log(self, message: str):
        """Log con timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        if hasattr(self, 'log_file') and self.log_file:
            self.log_file.write(log_entry + '\n')
            self.log_file.flush()
    
    def test_connection(self) -> bool:
        """Probar conexión SSH"""
        try:
            cmd = [
                'ssh', '-o', 'ConnectTimeout=5',
                '-o', 'BatchMode=yes',
                f'{self.ssh_user}@{self.ssh_host}',
                'echo "CONNECTION_OK"'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and "CONNECTION_OK" in result.stdout:
                self.connected = True
                return True
            else:
                self.connected = False
                return False
                
        except Exception:
            self.connected = False
            return False
    
    def execute_remote_command(self, command: str, timeout: int = 30) -> Dict:
        """Ejecutar comando remoto y retornar resultado"""
        try:
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', command]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command timeout',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'returncode': -1
            }
    
    def sync_project_code(self) -> bool:
        """Sincronizar código del proyecto"""
        self.log("📁 Sincronizando código del proyecto...")
        
        try:
            # Usar rsync si está disponible
            exclude_patterns = [
                '--exclude=.git',
                '--exclude=__pycache__',
                '--exclude=*.pyc',
                '--exclude=logs/*.log',
                '--exclude=data/*/',
                '--exclude=*.tmp'
            ]
            
            cmd = [
                'rsync', '-avz', '--delete'
            ] + exclude_patterns + [
                f'{self.project_root}/',
                f'{self.ssh_user}@{self.ssh_host}:/home/esdata/PropertyScraper-Dell710/'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                self.log("✅ Código sincronizado exitosamente")
                return True
            else:
                self.log(f"❌ Error sincronizando: {result.stderr}")
                return False
                
        except FileNotFoundError:
            # Fallback a SCP
            self.log("⚠️ rsync no disponible, usando SCP...")
            return self.sync_with_scp()
        except Exception as e:
            self.log(f"❌ Error en sincronización: {e}")
            return False
    
    def sync_with_scp(self) -> bool:
        """Sincronización alternativa con SCP"""
        try:
            essential_files = [
                'orchestrator/advanced_orchestrator.py',
                'utils/scraps_registry.py',
                'utils/gdrive_backup_manager.py',
                'utils/visual_terminal_monitor.py',
                'utils/checkpoint_recovery.py',
                'ssh_launcher.py',
                'system_setup.py'
            ]
            
            for file_path in essential_files:
                local_file = self.project_root / file_path
                if local_file.exists():
                    remote_path = f'/home/esdata/PropertyScraper-Dell710/{file_path}'
                    
                    # Crear directorio remoto
                    remote_dir = '/'.join(remote_path.split('/')[:-1])
                    cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', f'mkdir -p {remote_dir}']
                    subprocess.run(cmd, timeout=10)
                    
                    # Copiar archivo
                    cmd = ['scp', str(local_file), f'{self.ssh_user}@{self.ssh_host}:{remote_path}']
                    result = subprocess.run(cmd, timeout=30)
                    
                    if result.returncode == 0:
                        self.log(f"   ✅ {file_path}")
                    else:
                        self.log(f"   ❌ {file_path}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error con SCP: {e}")
            return False
    
    def check_orchestrator_status(self) -> Dict:
        """Verificar estado del orquestador remoto"""
        try:
            # Buscar proceso del orquestador
            result = self.execute_remote_command(
                "ps aux | grep 'advanced_orchestrator.py' | grep -v grep",
                timeout=10
            )
            
            if result['success'] and result['stdout'].strip():
                self.orchestrator_running = True
                
                # Obtener información del proceso
                process_info = result['stdout'].strip().split()
                pid = process_info[1] if len(process_info) > 1 else 'unknown'
                
                return {
                    'running': True,
                    'pid': pid,
                    'status': 'active'
                }
            else:
                self.orchestrator_running = False
                return {
                    'running': False,
                    'status': 'stopped'
                }
                
        except Exception as e:
            return {
                'running': False,
                'error': str(e),
                'status': 'unknown'
            }
    
    def launch_orchestrator(self, resume: bool = False) -> bool:
        """Lanzar orquestador en Dell T710"""
        try:
            self.log("🎛️ Lanzando Advanced Orchestrator...")
            
            # Verificar conexión
            if not self.test_connection():
                self.log("❌ No hay conexión SSH")
                return False
            
            # Sincronizar código
            if not self.sync_project_code():
                self.log("❌ Error sincronizando código")
                return False
            
            # Verificar si ya está corriendo
            status = self.check_orchestrator_status()
            if status['running']:
                self.log(f"⚠️ Orchestrator ya está corriendo (PID: {status.get('pid', 'unknown')})")
                return True
            
            # Preparar comando
            cmd = 'cd /home/esdata/PropertyScraper-Dell710 && nohup /home/esdata/venv/bin/python orchestrator/advanced_orchestrator.py'
            
            if resume:
                cmd += ' --resume'
            
            cmd += ' > /dev/null 2>&1 &'
            
            # Ejecutar en background
            result = self.execute_remote_command(cmd, timeout=15)
            
            if result['success']:
                self.log("✅ Orchestrator lanzado exitosamente")
                self.orchestrator_running = True
                
                # Verificar que efectivamente esté corriendo
                time.sleep(3)
                status = self.check_orchestrator_status()
                if status['running']:
                    self.log(f"✅ Orchestrator confirmado activo (PID: {status.get('pid', 'unknown')})")
                    return True
                else:
                    self.log("❌ Orchestrator no se inició correctamente")
                    return False
            else:
                self.log(f"❌ Error lanzando orchestrator: {result.get('stderr', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error: {e}")
            return False
    
    def stop_orchestrator(self) -> bool:
        """Detener orquestador remotamente"""
        try:
            self.log("⏹️ Deteniendo orchestrator...")
            
            # Buscar y terminar proceso
            result = self.execute_remote_command(
                "pkill -f 'advanced_orchestrator.py'",
                timeout=10
            )
            
            # Esperar un momento
            time.sleep(3)
            
            # Verificar que se detuvo
            status = self.check_orchestrator_status()
            if not status['running']:
                self.log("✅ Orchestrator detenido exitosamente")
                self.orchestrator_running = False
                return True
            else:
                self.log("⚠️ Orchestrator puede seguir corriendo")
                return False
                
        except Exception as e:
            self.log(f"❌ Error deteniendo orchestrator: {e}")
            return False
    
    def get_system_status(self) -> Dict:
        """Obtener estado completo del sistema"""
        try:
            # Estado de conexión
            connection_ok = self.test_connection()
            
            # Estado del orquestador
            orchestrator_status = self.check_orchestrator_status()
            
            # Recursos del sistema
            system_cmd = (
                "echo 'CPU:' $(cat /proc/loadavg | cut -d' ' -f1-3); "
                "echo 'MEM:' $(free | grep Mem | awk '{printf \"%.1f%%\", $3/$2 * 100.0}'); "
                "echo 'DISK:' $(df /home | tail -1 | awk '{print $5}')"
            )
            
            system_result = self.execute_remote_command(system_cmd, timeout=10)
            system_info = system_result['stdout'] if system_result['success'] else 'Error getting system info'
            
            # Estado de scrapers activos
            scrapers_cmd = "ps aux | grep -E '(inm24|cyt|lam|mit|prop|seg|tro)\\.py' | grep -v grep | wc -l"
            scrapers_result = self.execute_remote_command(scrapers_cmd, timeout=10)
            active_scrapers = int(scrapers_result['stdout'].strip()) if scrapers_result['success'] else 0
            
            return {
                'timestamp': datetime.now().isoformat(),
                'connection': connection_ok,
                'orchestrator': orchestrator_status,
                'system_info': system_info,
                'active_scrapers': active_scrapers,
                'master_controller_running': True
            }
            
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'connection': False
            }
    
    def start_continuous_monitoring(self):
        """Iniciar monitoreo continuo"""
        if self.monitoring:
            self.log("⚠️ Monitoreo ya está activo")
            return
        
        self.monitoring = True
        self.log("🔄 Iniciando monitoreo continuo...")
        
        def monitor_loop():
            while self.monitoring:
                try:
                    # Obtener estado
                    status = self.get_system_status()
                    
                    # Mostrar estado compacto
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    connection_icon = "🟢" if status['connection'] else "🔴"
                    orchestrator_icon = "🟢" if status['orchestrator']['running'] else "🔴"
                    
                    print(f"\r[{timestamp}] {connection_icon} SSH | {orchestrator_icon} ORCH | Scrapers: {status['active_scrapers']} | {status['system_info'].replace(chr(10), ' ')}", end='', flush=True)
                    
                    # Auto-recovery si está habilitado
                    if self.auto_recovery_enabled:
                        if not status['connection']:
                            self.log("\n⚠️ Conexión perdida, intentando reconectar...")
                            time.sleep(5)
                            continue
                        
                        if not status['orchestrator']['running'] and self.orchestrator_running:
                            self.log("\n⚠️ Orchestrator se detuvo, intentando recuperar...")
                            success = self.launch_orchestrator(resume=True)
                            if success:
                                self.log("✅ Orchestrator recuperado")
                            else:
                                self.log("❌ Error recuperando orchestrator")
                    
                    # Guardar estado
                    self.save_state(status)
                    
                    # Esperar antes del siguiente check
                    time.sleep(5)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.log(f"\n❌ Error en monitoreo: {e}")
                    time.sleep(10)
            
            self.monitoring = False
            print()  # Nueva línea al terminar
        
        # Iniciar thread de monitoreo
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        if self.monitoring:
            self.monitoring = False
            self.log("⏹️ Deteniendo monitoreo...")
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
    
    def save_state(self, status: Dict):
        """Guardar estado actual"""
        try:
            state = {
                'last_update': datetime.now().isoformat(),
                'system_status': status,
                'controller_config': {
                    'ssh_host': self.ssh_host,
                    'ssh_user': self.ssh_user,
                    'auto_recovery_enabled': self.auto_recovery_enabled,
                    'monitoring': self.monitoring
                }
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.log(f"⚠️ Error guardando estado: {e}")
    
    def show_detailed_status(self):
        """Mostrar estado detallado"""
        status = self.get_system_status()
        
        print("\n" + "="*60)
        print("📊 DETAILED SYSTEM STATUS")
        print("="*60)
        print(f"🕐 Timestamp: {status['timestamp']}")
        print(f"🔗 SSH Connection: {'✅ Connected' if status['connection'] else '❌ Disconnected'}")
        
        orch = status['orchestrator']
        if orch['running']:
            print(f"🎛️ Orchestrator: ✅ Running (PID: {orch.get('pid', 'unknown')})")
        else:
            print(f"🎛️ Orchestrator: ❌ Stopped")
        
        print(f"🕷️ Active Scrapers: {status['active_scrapers']}")
        print(f"🖥️ System: {status['system_info']}")
        print("="*60)
    
    def run_interactive_session(self):
        """Ejecutar sesión interactiva"""
        self.log("🎮 Iniciando sesión interactiva")
        
        try:
            # Verificar conexión inicial
            if not self.test_connection():
                self.log("❌ No se pudo establecer conexión SSH inicial")
                return False
            
            # Iniciar monitoreo
            self.start_continuous_monitoring()
            
            print(f"\n🎛️ Master Controller - Sesión Interactiva")
            print(f"   Target: {self.ssh_user}@{self.ssh_host}")
            print(f"   Commands: help, status, launch, stop, monitor, backup, exit")
            print(f"   Monitoring: {'✅ Active' if self.monitoring else '❌ Inactive'}")
            
            while True:
                try:
                    command = input("\n> ").strip().lower()
                    
                    if command == 'help':
                        print("\n📋 Available commands:")
                        print("   status  - Show detailed system status")
                        print("   launch  - Launch orchestrator")
                        print("   stop    - Stop orchestrator")
                        print("   resume  - Resume orchestrator from checkpoint")
                        print("   monitor - Toggle monitoring")
                        print("   backup  - Run manual backup")
                        print("   sync    - Sync project code")
                        print("   logs    - Show recent logs")
                        print("   exit    - Exit session")
                    
                    elif command == 'status':
                        self.show_detailed_status()
                    
                    elif command == 'launch':
                        success = self.launch_orchestrator(resume=False)
                        if success:
                            print("✅ Orchestrator launched")
                        else:
                            print("❌ Failed to launch orchestrator")
                    
                    elif command == 'resume':
                        success = self.launch_orchestrator(resume=True)
                        if success:
                            print("✅ Orchestrator resumed")
                        else:
                            print("❌ Failed to resume orchestrator")
                    
                    elif command == 'stop':
                        success = self.stop_orchestrator()
                        if success:
                            print("✅ Orchestrator stopped")
                        else:
                            print("❌ Failed to stop orchestrator")
                    
                    elif command == 'monitor':
                        if self.monitoring:
                            self.stop_monitoring()
                            print("⏹️ Monitoring stopped")
                        else:
                            self.start_continuous_monitoring()
                            print("🔄 Monitoring started")
                    
                    elif command == 'backup':
                        print("☁️ Running manual backup...")
                        result = self.execute_remote_command(
                            'cd /home/esdata/PropertyScraper-Dell710 && /home/esdata/venv/bin/python utils/gdrive_backup_manager.py --backup-now',
                            timeout=120
                        )
                        if result['success']:
                            print("✅ Backup completed")
                        else:
                            print(f"❌ Backup failed: {result.get('stderr', 'Unknown error')}")
                    
                    elif command == 'sync':
                        success = self.sync_project_code()
                        if success:
                            print("✅ Code synchronized")
                        else:
                            print("❌ Sync failed")
                    
                    elif command == 'logs':
                        result = self.execute_remote_command(
                            'cd /home/esdata/PropertyScraper-Dell710 && /home/esdata/venv/bin/python utils/visual_terminal_monitor.py --compact',
                            timeout=30
                        )
                        if result['success']:
                            print(result['stdout'])
                        else:
                            print("❌ Error getting logs")
                    
                    elif command in ['exit', 'quit']:
                        break
                    
                    elif command == '':
                        continue
                    
                    else:
                        print(f"❓ Unknown command: {command}. Type 'help' for available commands.")
                
                except KeyboardInterrupt:
                    print("\n⏸️ Use 'exit' to quit")
                    continue
                except EOFError:
                    break
            
            # Cleanup
            self.stop_monitoring()
            self.log("👋 Sesión interactiva terminada")
            return True
            
        except Exception as e:
            self.log(f"❌ Error en sesión interactiva: {e}")
            return False
        finally:
            if hasattr(self, 'log_file') and self.log_file:
                self.log_file.close()

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Master Controller for PropertyScraper Dell710')
    
    parser.add_argument('--test', action='store_true', help='Test SSH connection')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--launch', action='store_true', help='Launch orchestrator')
    parser.add_argument('--resume', action='store_true', help='Resume orchestrator')
    parser.add_argument('--stop', action='store_true', help='Stop orchestrator')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--interactive', action='store_true', help='Run interactive session')
    parser.add_argument('--sync', action='store_true', help='Sync project code')
    
    args = parser.parse_args()
    
    controller = MasterController()
    
    if args.test:
        print("🧪 Testing SSH connection...")
        if controller.test_connection():
            print("✅ SSH connection successful")
        else:
            print("❌ SSH connection failed")
    
    elif args.status:
        controller.show_detailed_status()
    
    elif args.launch:
        success = controller.launch_orchestrator(resume=False)
        if success:
            print("✅ Orchestrator launched successfully")
        else:
            print("❌ Failed to launch orchestrator")
    
    elif args.resume:
        success = controller.launch_orchestrator(resume=True)
        if success:
            print("✅ Orchestrator resumed successfully")
        else:
            print("❌ Failed to resume orchestrator")
    
    elif args.stop:
        success = controller.stop_orchestrator()
        if success:
            print("✅ Orchestrator stopped successfully")
        else:
            print("❌ Failed to stop orchestrator")
    
    elif args.sync:
        success = controller.sync_project_code()
        if success:
            print("✅ Project code synchronized")
        else:
            print("❌ Failed to sync code")
    
    elif args.monitor:
        print("🔄 Starting continuous monitoring (Ctrl+C to stop)...")
        controller.start_continuous_monitoring()
        try:
            while controller.monitoring:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️ Stopping monitor...")
            controller.stop_monitoring()
    
    elif args.interactive:
        controller.run_interactive_session()
    
    else:
        print("\n🎛️ Master Controller - PropertyScraper Dell710")
        print("="*50)
        print("\n📋 Available commands:")
        print("  --test        : Test SSH connection")
        print("  --status      : Show system status")
        print("  --launch      : Launch orchestrator")
        print("  --resume      : Resume orchestrator")
        print("  --stop        : Stop orchestrator")
        print("  --sync        : Sync project code")
        print("  --monitor     : Continuous monitoring")
        print("  --interactive : Interactive session")
        print("\n🚀 Quick start:")
        print("  python master_controller.py --test")
        print("  python master_controller.py --launch")
        print("  python master_controller.py --interactive")

if __name__ == "__main__":
    main()
