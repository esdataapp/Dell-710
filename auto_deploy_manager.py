#!/usr/bin/env python3
"""
Auto Deploy Script - PropertyScraper Dell710
Script de despliegue automatizado completo desde Windows 11 al Dell T710
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

class AutoDeployManager:
    """
    Gestor de despliegue automatizado que:
    - Verifica pre-requisitos en Windows 11
    - Establece conexión SSH con Dell T710
    - Instala dependencias remotas
    - Configura entorno Python remoto
    - Despliega código del proyecto
    - Ejecuta verificaciones post-despliegue
    - Inicia servicios automáticamente
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.ssh_host = "192.168.50.54"
        self.ssh_user = "esdata"
        self.remote_path = "/home/esdata/PropertyScraper-Dell710"
        
        # Configuración de despliegue
        self.python_version = "3.12"
        self.venv_path = "/home/esdata/venv"
        
        # Estado del despliegue
        self.deployment_log = []
        self.success_steps = 0
        self.total_steps = 12
        
        # Archivo de log
        self.log_file_path = self.project_root / 'logs' / f'deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        self.log_file_path.parent.mkdir(exist_ok=True, parents=True)
        
        print("🚀 Auto Deploy Manager - PropertyScraper Dell710")
        print(f"   Target: {self.ssh_user}@{self.ssh_host}")
        print(f"   Remote path: {self.remote_path}")
        print(f"   Deployment log: {self.log_file_path}")
    
    def log(self, message: str, level: str = "INFO"):
        """Log con timestamp y nivel"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}"
        
        self.deployment_log.append(log_entry)
        print(log_entry)
        
        # Escribir a archivo
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    
    def step(self, step_num: int, description: str):
        """Marcar paso del despliegue"""
        self.log(f"📋 Step {step_num}/{self.total_steps}: {description}")
    
    def success(self, message: str):
        """Marcar éxito"""
        self.success_steps += 1
        self.log(f"✅ {message}", "SUCCESS")
    
    def error(self, message: str):
        """Marcar error"""
        self.log(f"❌ {message}", "ERROR")
    
    def warning(self, message: str):
        """Marcar advertencia"""
        self.log(f"⚠️ {message}", "WARNING")
    
    def execute_local_command(self, command: str, timeout: int = 60) -> Dict:
        """Ejecutar comando local"""
        try:
            result = subprocess.run(
                command.split() if isinstance(command, str) else command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True if os.name == 'nt' else False
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
    
    def execute_remote_command(self, command: str, timeout: int = 60) -> Dict:
        """Ejecutar comando remoto"""
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
    
    def check_local_prerequisites(self) -> bool:
        """Verificar pre-requisitos locales"""
        self.step(1, "Checking local prerequisites")
        
        # Verificar SSH
        ssh_result = self.execute_local_command("ssh -V")
        if not ssh_result['success']:
            self.error("SSH client not found. Please install OpenSSH or Git for Windows")
            return False
        self.success(f"SSH client available: {ssh_result['stderr'].split()[0] if ssh_result['stderr'] else 'Unknown version'}")
        
        # Verificar rsync (opcional)
        rsync_result = self.execute_local_command("rsync --version")
        if rsync_result['success']:
            self.success("rsync available for fast sync")
        else:
            self.warning("rsync not available, will use SCP as fallback")
        
        # Verificar estructura del proyecto
        essential_files = [
            'orchestrator/advanced_orchestrator.py',
            'utils/scraps_registry.py',
            'utils/gdrive_backup_manager.py',
            'master_controller.py',
            'requirements.txt'
        ]
        
        missing_files = []
        for file_path in essential_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.error(f"Missing essential files: {', '.join(missing_files)}")
            return False
        
        self.success("All essential project files found")
        return True
    
    def test_ssh_connection(self) -> bool:
        """Probar conexión SSH"""
        self.step(2, "Testing SSH connection")
        
        try:
            # Probar conexión básica
            result = self.execute_remote_command("echo 'SSH_TEST_OK'", timeout=10)
            
            if result['success'] and "SSH_TEST_OK" in result['stdout']:
                self.success("SSH connection established")
                return True
            else:
                self.error(f"SSH connection failed: {result.get('stderr', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.error(f"SSH connection error: {e}")
            return False
    
    def check_remote_environment(self) -> bool:
        """Verificar entorno remoto"""
        self.step(3, "Checking remote environment")
        
        # Verificar SO
        os_result = self.execute_remote_command("lsb_release -d")
        if os_result['success']:
            os_info = os_result['stdout'].strip()
            self.success(f"Remote OS: {os_info}")
        else:
            self.warning("Could not determine remote OS version")
        
        # Verificar Python
        python_result = self.execute_remote_command("python3 --version")
        if python_result['success']:
            python_version = python_result['stdout'].strip()
            self.success(f"Python available: {python_version}")
        else:
            self.error("Python 3 not found on remote system")
            return False
        
        # Verificar espacio en disco
        disk_result = self.execute_remote_command("df -h /home | tail -1")
        if disk_result['success']:
            disk_info = disk_result['stdout'].strip().split()
            if len(disk_info) >= 4:
                available = disk_info[3]
                self.success(f"Disk space available: {available}")
            else:
                self.warning("Could not parse disk space information")
        
        # Verificar memoria
        mem_result = self.execute_remote_command("free -h | grep Mem")
        if mem_result['success']:
            mem_info = mem_result['stdout'].strip()
            self.success(f"Memory info: {mem_info}")
        
        return True
    
    def setup_remote_directories(self) -> bool:
        """Configurar directorios remotos"""
        self.step(4, "Setting up remote directories")
        
        directories = [
            self.remote_path,
            f"{self.remote_path}/data",
            f"{self.remote_path}/logs",
            f"{self.remote_path}/orchestrator",
            f"{self.remote_path}/utils",
            f"{self.remote_path}/scrapers",
            f"{self.remote_path}/monitoring",
            f"{self.remote_path}/config"
        ]
        
        for directory in directories:
            result = self.execute_remote_command(f"mkdir -p {directory}")
            if not result['success']:
                self.error(f"Failed to create directory: {directory}")
                return False
        
        self.success("Remote directories created")
        return True
    
    def setup_python_environment(self) -> bool:
        """Configurar entorno Python remoto"""
        self.step(5, "Setting up Python virtual environment")
        
        # Verificar si venv ya existe
        venv_check = self.execute_remote_command(f"test -d {self.venv_path}")
        
        if venv_check['success']:
            self.success("Virtual environment already exists")
        else:
            # Crear nuevo venv
            self.log("Creating new virtual environment...")
            venv_result = self.execute_remote_command(f"python3 -m venv {self.venv_path}", timeout=120)
            
            if not venv_result['success']:
                self.error(f"Failed to create virtual environment: {venv_result.get('stderr', 'Unknown error')}")
                return False
            
            self.success("Virtual environment created")
        
        # Verificar pip
        pip_result = self.execute_remote_command(f"{self.venv_path}/bin/pip --version")
        if pip_result['success']:
            self.success(f"pip available: {pip_result['stdout'].strip()}")
        else:
            self.error("pip not available in virtual environment")
            return False
        
        return True
    
    def sync_project_files(self) -> bool:
        """Sincronizar archivos del proyecto"""
        self.step(6, "Syncing project files")
        
        # Intentar con rsync primero
        if self.sync_with_rsync():
            return True
        
        # Fallback a SCP
        return self.sync_with_scp()
    
    def sync_with_rsync(self) -> bool:
        """Sincronizar con rsync"""
        try:
            exclude_patterns = [
                '--exclude=.git',
                '--exclude=__pycache__',
                '--exclude=*.pyc',
                '--exclude=logs/*.log',
                '--exclude=data/*/',
                '--exclude=*.tmp',
                '--exclude=.env'
            ]
            
            cmd = [
                'rsync', '-avz', '--delete', '--progress'
            ] + exclude_patterns + [
                f'{self.project_root}/',
                f'{self.ssh_user}@{self.ssh_host}:{self.remote_path}/'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.success("Project files synced with rsync")
                return True
            else:
                self.warning(f"rsync failed: {result.stderr}")
                return False
                
        except FileNotFoundError:
            self.warning("rsync not available")
            return False
        except Exception as e:
            self.warning(f"rsync error: {e}")
            return False
    
    def sync_with_scp(self) -> bool:
        """Sincronizar con SCP"""
        try:
            self.log("Using SCP for file transfer...")
            
            # Archivos esenciales para copiar
            essential_files = [
                'orchestrator/advanced_orchestrator.py',
                'utils/scraps_registry.py',
                'utils/gdrive_backup_manager.py',
                'utils/visual_terminal_monitor.py',
                'utils/checkpoint_recovery.py',
                'master_controller.py',
                'system_setup.py',
                'requirements.txt',
                'config/dell_t710_config.yaml',
                'config/ssh_config.json'
            ]
            
            # Copiar archivos individuales
            for file_path in essential_files:
                local_file = self.project_root / file_path
                if local_file.exists():
                    remote_file = f"{self.remote_path}/{file_path}"
                    
                    # Asegurar que el directorio remoto existe
                    remote_dir = '/'.join(remote_file.split('/')[:-1])
                    mkdir_result = self.execute_remote_command(f"mkdir -p {remote_dir}")
                    
                    # Copiar archivo
                    cmd = ['scp', str(local_file), f'{self.ssh_user}@{self.ssh_host}:{remote_file}']
                    result = subprocess.run(cmd, timeout=60)
                    
                    if result.returncode == 0:
                        self.log(f"   ✅ {file_path}")
                    else:
                        self.log(f"   ❌ {file_path}")
                        return False
                else:
                    self.warning(f"Local file not found: {file_path}")
            
            # Copiar directorios completos
            directories_to_copy = ['scrapers']
            
            for directory in directories_to_copy:
                local_dir = self.project_root / directory
                if local_dir.exists():
                    cmd = ['scp', '-r', str(local_dir), f'{self.ssh_user}@{self.ssh_host}:{self.remote_path}/']
                    result = subprocess.run(cmd, timeout=120)
                    
                    if result.returncode == 0:
                        self.log(f"   ✅ {directory}/")
                    else:
                        self.log(f"   ❌ {directory}/")
            
            self.success("Project files synced with SCP")
            return True
            
        except Exception as e:
            self.error(f"SCP sync failed: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """Instalar dependencias"""
        self.step(7, "Installing Python dependencies")
        
        # Actualizar pip
        pip_upgrade = self.execute_remote_command(
            f"{self.venv_path}/bin/pip install --upgrade pip",
            timeout=120
        )
        
        if pip_upgrade['success']:
            self.success("pip upgraded")
        else:
            self.warning("pip upgrade failed, continuing...")
        
        # Instalar dependencias del requirements.txt
        install_result = self.execute_remote_command(
            f"cd {self.remote_path} && {self.venv_path}/bin/pip install -r requirements.txt",
            timeout=600  # 10 minutos para instalación
        )
        
        if install_result['success']:
            self.success("Python dependencies installed")
            return True
        else:
            self.error(f"Dependency installation failed: {install_result.get('stderr', 'Unknown error')}")
            return False
    
    def setup_system_dependencies(self) -> bool:
        """Configurar dependencias del sistema"""
        self.step(8, "Setting up system dependencies")
        
        # Verificar Chrome/Chromium
        chrome_result = self.execute_remote_command("which google-chrome || which chromium-browser")
        if chrome_result['success']:
            self.success("Chrome/Chromium browser found")
        else:
            self.warning("Chrome/Chromium not found, may need manual installation")
        
        # Verificar rclone
        rclone_result = self.execute_remote_command("which rclone")
        if rclone_result['success']:
            self.success("rclone found")
        else:
            self.warning("rclone not found, Google Drive backup may not work")
        
        # Configurar permisos
        chmod_result = self.execute_remote_command(f"chmod +x {self.remote_path}/*.py")
        if chmod_result['success']:
            self.success("Python scripts made executable")
        
        return True
    
    def configure_services(self) -> bool:
        """Configurar servicios"""
        self.step(9, "Configuring services")
        
        # Crear script de inicio
        startup_script = f"""#!/bin/bash
# PropertyScraper Dell710 Startup Script
cd {self.remote_path}
source {self.venv_path}/bin/activate

echo "PropertyScraper Dell710 - Ready for operation"
echo "Use: python master_controller.py --interactive"
"""
        
        startup_path = f"{self.remote_path}/start_scraper.sh"
        
        # Escribir script de inicio
        write_result = self.execute_remote_command(f"cat > {startup_path} << 'EOF'\n{startup_script}\nEOF")
        if write_result['success']:
            # Hacer ejecutable
            chmod_result = self.execute_remote_command(f"chmod +x {startup_path}")
            if chmod_result['success']:
                self.success("Startup script created")
            else:
                self.error("Failed to make startup script executable")
                return False
        else:
            self.error("Failed to create startup script")
            return False
        
        return True
    
    def run_post_deployment_tests(self) -> bool:
        """Ejecutar pruebas post-despliegue"""
        self.step(10, "Running post-deployment tests")
        
        # Probar importaciones de Python
        import_test = self.execute_remote_command(
            f"cd {self.remote_path} && {self.venv_path}/bin/python -c 'import selenium, seleniumbase, paramiko, rclone; print(\"All imports successful\")'",
            timeout=30
        )
        
        if import_test['success']:
            self.success("Python imports test passed")
        else:
            self.error(f"Python imports test failed: {import_test.get('stderr', 'Unknown error')}")
            return False
        
        # Probar script principal
        main_test = self.execute_remote_command(
            f"cd {self.remote_path} && {self.venv_path}/bin/python master_controller.py --test",
            timeout=30
        )
        
        if main_test['success']:
            self.success("Master controller test passed")
        else:
            self.warning("Master controller test had issues, check manually")
        
        return True
    
    def setup_monitoring(self) -> bool:
        """Configurar monitoreo"""
        self.step(11, "Setting up monitoring")
        
        # Crear directorio de logs si no existe
        logs_result = self.execute_remote_command(f"mkdir -p {self.remote_path}/logs")
        
        # Probar visual monitor
        monitor_test = self.execute_remote_command(
            f"cd {self.remote_path} && {self.venv_path}/bin/python utils/visual_terminal_monitor.py --test",
            timeout=15
        )
        
        if monitor_test['success']:
            self.success("Visual monitoring system ready")
        else:
            self.warning("Visual monitoring test failed")
        
        return True
    
    def finalize_deployment(self) -> bool:
        """Finalizar despliegue"""
        self.step(12, "Finalizing deployment")
        
        # Crear archivo de estado de despliegue
        deployment_info = {
            'deployment_date': datetime.now().isoformat(),
            'version': '1.0',
            'deployed_by': 'auto_deploy_manager',
            'target_host': self.ssh_host,
            'target_user': self.ssh_user,
            'remote_path': self.remote_path,
            'python_venv': self.venv_path,
            'status': 'completed'
        }
        
        info_json = json.dumps(deployment_info, indent=2)
        
        result = self.execute_remote_command(
            f"cat > {self.remote_path}/deployment_info.json << 'EOF'\n{info_json}\nEOF"
        )
        
        if result['success']:
            self.success("Deployment info saved")
        
        # Mostrar resumen
        self.success(f"Deployment completed successfully! ({self.success_steps}/{self.total_steps} steps)")
        
        print(f"\n🎯 DEPLOYMENT SUMMARY")
        print(f"="*50)
        print(f"✅ Target: {self.ssh_user}@{self.ssh_host}")
        print(f"✅ Remote path: {self.remote_path}")
        print(f"✅ Python venv: {self.venv_path}")
        print(f"✅ Startup script: {self.remote_path}/start_scraper.sh")
        print(f"\n🚀 Quick start commands:")
        print(f"   ssh {self.ssh_user}@{self.ssh_host}")
        print(f"   cd {self.remote_path}")
        print(f"   python master_controller.py --interactive")
        
        return True
    
    def run_full_deployment(self) -> bool:
        """Ejecutar despliegue completo"""
        try:
            self.log("🚀 Starting full deployment process...")
            
            # Ejecutar todos los pasos
            steps = [
                self.check_local_prerequisites,
                self.test_ssh_connection,
                self.check_remote_environment,
                self.setup_remote_directories,
                self.setup_python_environment,
                self.sync_project_files,
                self.install_dependencies,
                self.setup_system_dependencies,
                self.configure_services,
                self.run_post_deployment_tests,
                self.setup_monitoring,
                self.finalize_deployment
            ]
            
            for step_func in steps:
                if not step_func():
                    self.error(f"Deployment failed at step: {step_func.__name__}")
                    return False
            
            self.log("🎉 Full deployment completed successfully!")
            return True
            
        except Exception as e:
            self.error(f"Deployment failed with exception: {e}")
            return False
    
    def run_quick_sync(self) -> bool:
        """Sincronización rápida de código"""
        self.log("⚡ Starting quick code sync...")
        
        if not self.test_ssh_connection():
            return False
        
        if not self.sync_project_files():
            return False
        
        self.success("Quick sync completed!")
        return True
    
    def run_update_deployment(self) -> bool:
        """Actualización de despliegue existente"""
        self.log("🔄 Starting update deployment...")
        
        steps = [
            self.test_ssh_connection,
            self.sync_project_files,
            self.install_dependencies,
            self.run_post_deployment_tests
        ]
        
        for step_func in steps:
            if not step_func():
                self.error(f"Update failed at step: {step_func.__name__}")
                return False
        
        self.success("Update deployment completed!")
        return True

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Auto Deploy Manager for PropertyScraper Dell710')
    
    parser.add_argument('--full', action='store_true', help='Run full deployment')
    parser.add_argument('--sync', action='store_true', help='Quick code sync only')
    parser.add_argument('--update', action='store_true', help='Update existing deployment')
    parser.add_argument('--test-ssh', action='store_true', help='Test SSH connection only')
    parser.add_argument('--check-local', action='store_true', help='Check local prerequisites only')
    
    args = parser.parse_args()
    
    deployer = AutoDeployManager()
    
    if args.full:
        success = deployer.run_full_deployment()
        sys.exit(0 if success else 1)
    
    elif args.sync:
        success = deployer.run_quick_sync()
        sys.exit(0 if success else 1)
    
    elif args.update:
        success = deployer.run_update_deployment()
        sys.exit(0 if success else 1)
    
    elif args.test_ssh:
        if deployer.test_ssh_connection():
            print("✅ SSH connection successful")
            sys.exit(0)
        else:
            print("❌ SSH connection failed")
            sys.exit(1)
    
    elif args.check_local:
        if deployer.check_local_prerequisites():
            print("✅ Local prerequisites OK")
            sys.exit(0)
        else:
            print("❌ Local prerequisites failed")
            sys.exit(1)
    
    else:
        print("\n🚀 Auto Deploy Manager - PropertyScraper Dell710")
        print("="*50)
        print("\n📋 Available commands:")
        print("  --full        : Run complete deployment")
        print("  --sync        : Quick code synchronization")
        print("  --update      : Update existing deployment")
        print("  --test-ssh    : Test SSH connection")
        print("  --check-local : Check local prerequisites")
        print("\n🎯 Quick start:")
        print("  python auto_deploy_manager.py --test-ssh")
        print("  python auto_deploy_manager.py --full")
        print("\n💡 For interactive management after deployment:")
        print("  python master_controller.py --interactive")

if __name__ == "__main__":
    main()
