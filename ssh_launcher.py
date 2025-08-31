#!/usr/bin/env python3
"""
SSH Launcher - PropertyScraper Dell710
Script para lanzar scrapers y orquestación desde Windows 11 hacia Dell T710
"""

import os
import sys
import json
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class SSHLauncher:
    """
    Launcher para ejecutar scrapers remotamente en Dell T710 desde Windows 11
    Maneja conexión SSH, sincronización de código y monitoreo remoto
    """
    
    def __init__(self):
        self.setup_config()
        
        # Configuración SSH para Dell T710
        self.ssh_host = "192.168.50.54"
        self.ssh_user = "esdata"  # Usuario según tu especificación
        self.ssh_timeout = 30
        
        # Rutas remotas en Dell T710
        self.remote_project_root = "/home/esdata/PropertyScraper-Dell710"
        self.remote_python = "/home/esdata/venv/bin/python"
        
        # Rutas locales
        self.local_project_root = Path(__file__).parent.parent
        
        print("🔧 SSH Launcher inicializado")
        print(f"   SSH Target: {self.ssh_user}@{self.ssh_host}")
        print(f"   Remote Path: {self.remote_project_root}")
    
    def setup_config(self):
        """Configurar paths y verificar conexión"""
        # Verificar que estamos en Windows
        if os.name != 'nt':
            print("⚠️  Este script está diseñado para Windows 11")
        
        # Verificar SSH disponible
        try:
            result = subprocess.run(['ssh', '-V'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ SSH client disponible")
            else:
                print("❌ SSH client no encontrado")
        except FileNotFoundError:
            print("❌ SSH client no instalado")
    
    def test_ssh_connection(self) -> bool:
        """Probar conexión SSH al Dell T710"""
        try:
            print(f"🧪 Probando conexión SSH a {self.ssh_user}@{self.ssh_host}...")
            
            cmd = [
                'ssh', '-o', 'ConnectTimeout=10',
                '-o', 'BatchMode=yes',
                f'{self.ssh_user}@{self.ssh_host}',
                'echo "Connection successful"'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("✅ Conexión SSH exitosa")
                return True
            else:
                print(f"❌ Error de conexión SSH: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Timeout en conexión SSH")
            return False
        except Exception as e:
            print(f"❌ Error probando SSH: {e}")
            return False
    
    def sync_project_code(self) -> bool:
        """Sincronizar código del proyecto al servidor remoto"""
        try:
            print("📁 Sincronizando código al Dell T710...")
            
            # Usar rsync para sincronización eficiente
            # Excluir archivos innecesarios
            exclude_patterns = [
                '--exclude=.git',
                '--exclude=__pycache__',
                '--exclude=*.pyc',
                '--exclude=logs/*.log',
                '--exclude=data/*',
                '--exclude=checkpoints/*'
            ]
            
            cmd = [
                'rsync', '-avz', '--delete'
            ] + exclude_patterns + [
                f'{self.local_project_root}/',
                f'{self.ssh_user}@{self.ssh_host}:{self.remote_project_root}/'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ Código sincronizado exitosamente")
                return True
            else:
                print(f"❌ Error sincronizando código: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Timeout sincronizando código")
            return False
        except FileNotFoundError:
            print("⚠️  rsync no disponible, usando SSH copy...")
            return self.sync_with_ssh_copy()
        except Exception as e:
            print(f"❌ Error sincronizando: {e}")
            return False
    
    def sync_with_ssh_copy(self) -> bool:
        """Sincronización alternativa usando SCP"""
        try:
            print("📁 Sincronizando con SCP...")
            
            # Crear directorio remoto si no existe
            mkdir_cmd = [
                'ssh', f'{self.ssh_user}@{self.ssh_host}',
                f'mkdir -p {self.remote_project_root}'
            ]
            subprocess.run(mkdir_cmd, timeout=30)
            
            # Copiar archivos principales
            important_files = [
                'orchestrator/*.py',
                'scrapers/*.py',
                'utils/*.py',
                'config/*.yaml',
                'config/*.json',
                'requirements.txt'
            ]
            
            for pattern in important_files:
                files = list(self.local_project_root.glob(pattern))
                for file_path in files:
                    if file_path.is_file():
                        # Crear directorio remoto
                        remote_dir = f"{self.remote_project_root}/{file_path.parent.relative_to(self.local_project_root)}"
                        mkdir_cmd = [
                            'ssh', f'{self.ssh_user}@{self.ssh_host}',
                            f'mkdir -p {remote_dir}'
                        ]
                        subprocess.run(mkdir_cmd, timeout=30)
                        
                        # Copiar archivo
                        remote_file = f"{self.remote_project_root}/{file_path.relative_to(self.local_project_root)}"
                        scp_cmd = ['scp', str(file_path), f'{self.ssh_user}@{self.ssh_host}:{remote_file}']
                        subprocess.run(scp_cmd, timeout=60)
            
            print("✅ Archivos principales copiados")
            return True
            
        except Exception as e:
            print(f"❌ Error con SCP: {e}")
            return False
    
    def execute_remote_command(self, command: str, background=False, timeout=None) -> subprocess.Popen:
        """Ejecutar comando remoto en Dell T710"""
        try:
            if background:
                # Para procesos en background, usar nohup
                remote_cmd = f'cd {self.remote_project_root} && nohup {command} > /dev/null 2>&1 &'
            else:
                remote_cmd = f'cd {self.remote_project_root} && {command}'
            
            ssh_cmd = [
                'ssh', '-t',  # Forzar terminal para interactividad
                f'{self.ssh_user}@{self.ssh_host}',
                remote_cmd
            ]
            
            print(f"🚀 Ejecutando: {command}")
            
            if background:
                # Para background, no capturar output
                process = subprocess.Popen(ssh_cmd)
            else:
                # Para foreground, mantener output visible
                process = subprocess.Popen(
                    ssh_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
            
            return process
            
        except Exception as e:
            print(f"❌ Error ejecutando comando remoto: {e}")
            return None
    
    def launch_orchestrator(self, resume=False) -> bool:
        """Lanzar orquestador avanzado en Dell T710"""
        try:
            print("🎛️ Lanzando Advanced Orchestrator...")
            
            if not self.test_ssh_connection():
                return False
            
            if not self.sync_project_code():
                return False
            
            # Preparar comando
            orchestrator_script = f"{self.remote_python} {self.remote_project_root}/orchestrator/advanced_orchestrator.py"
            
            if resume:
                orchestrator_script += " --resume"
            
            # Ejecutar en background
            process = self.execute_remote_command(orchestrator_script, background=True)
            
            if process:
                print("✅ Orquestador lanzado en background")
                print("📋 Use monitor para ver progreso:")
                print(f"   python {Path(__file__).name} --monitor")
                return True
            else:
                print("❌ Error lanzando orquestador")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def launch_single_scraper(self, website: str, operation: str, pages: int = 50) -> bool:
        """Lanzar un scraper individual"""
        try:
            print(f"🕷️ Lanzando scraper: {website} ({operation})")
            
            if not self.test_ssh_connection():
                return False
            
            if not self.sync_project_code():
                return False
            
            # Mapear website a script
            scraper_mapping = {
                'inmuebles24': 'inmuebles24_professional.py',
                'casas_y_terrenos': 'casas_y_terrenos_scraper.py',
                'lamudi': 'lamudi_professional.py',
                'mitula': 'mitula_scraper.py',
                'propiedades': 'propiedades_professional.py',
                'segundamano': 'segundamano_professional.py',
                'trovit': 'trovit_professional.py'
            }
            
            script_name = scraper_mapping.get(website)
            if not script_name:
                print(f"❌ Scraper no encontrado para: {website}")
                return False
            
            # Preparar comando
            scraper_cmd = (
                f"{self.remote_python} {self.remote_project_root}/scrapers/{script_name} "
                f"--headless --operation={operation} --pages={pages}"
            )
            
            # Ejecutar con output visible
            process = self.execute_remote_command(scraper_cmd, background=False)
            
            if process:
                # Mostrar output en tiempo real
                try:
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            print(line.rstrip())
                        
                        # Verificar si el proceso terminó
                        if process.poll() is not None:
                            break
                    
                    return_code = process.wait()
                    
                    if return_code == 0:
                        print("✅ Scraper completado exitosamente")
                        return True
                    else:
                        print(f"❌ Scraper falló con código: {return_code}")
                        return False
                        
                except KeyboardInterrupt:
                    print("\n⏹️ Scraper interrumpido por usuario")
                    process.terminate()
                    return False
            else:
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def show_remote_monitor(self):
        """Mostrar monitor remoto en tiempo real"""
        try:
            print("📊 Conectando al monitor remoto...")
            
            if not self.test_ssh_connection():
                return False
            
            # Comando para monitor
            monitor_cmd = f"{self.remote_python} {self.remote_project_root}/utils/visual_terminal_monitor.py"
            
            # Ejecutar monitor interactivo
            process = self.execute_remote_command(monitor_cmd, background=False)
            
            if process:
                try:
                    # Mantener conexión activa
                    process.wait()
                except KeyboardInterrupt:
                    print("\n⏹️ Monitor desconectado")
                    process.terminate()
            
        except Exception as e:
            print(f"❌ Error en monitor remoto: {e}")
    
    def show_registry_status(self):
        """Mostrar estado del registry remotamente"""
        try:
            print("📋 Obteniendo estado del registry...")
            
            if not self.test_ssh_connection():
                return False
            
            status_cmd = f"{self.remote_python} {self.remote_project_root}/utils/scraps_registry.py"
            
            process = self.execute_remote_command(status_cmd, background=False)
            
            if process:
                try:
                    output, _ = process.communicate(timeout=30)
                    print(output)
                except subprocess.TimeoutExpired:
                    print("❌ Timeout obteniendo estado")
                    process.terminate()
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def backup_results(self):
        """Ejecutar backup de resultados a Google Drive"""
        try:
            print("☁️ Iniciando backup a Google Drive...")
            
            if not self.test_ssh_connection():
                return False
            
            backup_cmd = f"{self.remote_python} {self.remote_project_root}/utils/gdrive_backup_manager.py --backup-now"
            
            process = self.execute_remote_command(backup_cmd, background=False)
            
            if process:
                try:
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            print(line.rstrip())
                        
                        if process.poll() is not None:
                            break
                    
                    return_code = process.wait()
                    
                    if return_code == 0:
                        print("✅ Backup completado")
                        return True
                    else:
                        print(f"❌ Backup falló")
                        return False
                        
                except KeyboardInterrupt:
                    print("\n⏹️ Backup interrumpido")
                    process.terminate()
                    return False
            
        except Exception as e:
            print(f"❌ Error en backup: {e}")
            return False

def main():
    """Función principal del launcher"""
    parser = argparse.ArgumentParser(description='SSH Launcher for PropertyScraper Dell710')
    
    parser.add_argument('--test-connection', action='store_true', help='Test SSH connection')
    parser.add_argument('--sync-code', action='store_true', help='Sync project code')
    parser.add_argument('--launch-orchestrator', action='store_true', help='Launch orchestrator')
    parser.add_argument('--resume-orchestrator', action='store_true', help='Resume orchestrator from checkpoint')
    parser.add_argument('--monitor', action='store_true', help='Show remote monitor')
    parser.add_argument('--status', action='store_true', help='Show registry status')
    parser.add_argument('--backup', action='store_true', help='Run backup to Google Drive')
    
    parser.add_argument('--scraper', type=str, help='Launch specific scraper (website name)')
    parser.add_argument('--operation', type=str, choices=['venta', 'renta'], default='venta', help='Operation type')
    parser.add_argument('--pages', type=int, default=50, help='Number of pages to scrape')
    
    args = parser.parse_args()
    
    launcher = SSHLauncher()
    
    if args.test_connection:
        launcher.test_ssh_connection()
    
    elif args.sync_code:
        launcher.sync_project_code()
    
    elif args.launch_orchestrator:
        launcher.launch_orchestrator(resume=False)
    
    elif args.resume_orchestrator:
        launcher.launch_orchestrator(resume=True)
    
    elif args.monitor:
        launcher.show_remote_monitor()
    
    elif args.status:
        launcher.show_registry_status()
    
    elif args.backup:
        launcher.backup_results()
    
    elif args.scraper:
        launcher.launch_single_scraper(args.scraper, args.operation, args.pages)
    
    else:
        print("\n🚀 PropertyScraper Dell710 - SSH Launcher")
        print("="*50)
        print("\n📋 Comandos disponibles:")
        print("  --test-connection     : Probar conexión SSH")
        print("  --sync-code          : Sincronizar código")
        print("  --launch-orchestrator: Lanzar orquestador")
        print("  --resume-orchestrator: Reanudar orquestador")
        print("  --monitor            : Monitor visual remoto")
        print("  --status             : Estado del registry")
        print("  --backup             : Backup a Google Drive")
        print("\n🕷️ Scrapers individuales:")
        print("  --scraper inmuebles24 --operation venta --pages 100")
        print("  --scraper casas_y_terrenos --operation renta")
        print("\n💡 Ejemplos:")
        print("  python ssh_launcher.py --test-connection")
        print("  python ssh_launcher.py --launch-orchestrator")
        print("  python ssh_launcher.py --monitor")
        print("  python ssh_launcher.py --scraper inmuebles24 --pages 50")

if __name__ == "__main__":
    main()
