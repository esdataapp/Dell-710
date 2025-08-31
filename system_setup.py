#!/usr/bin/env python3
"""
System Setup and Verification - PropertyScraper Dell710
Script para configurar y verificar que todo el sistema esté listo
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class SystemSetupVerification:
    """
    Verificador y configurador del sistema completo:
    - Verificar SSH connection
    - Verificar Google Drive (rclone)
    - Verificar estructura de datos
    - Verificar scrapers
    - Configurar registry inicial
    - Test de funcionalidad completa
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent if Path(__file__).parent.name != 'PropertyScraper-Dell710' else Path(__file__).parent
        self.ssh_host = "192.168.50.54"
        self.ssh_user = "esdata"
        
        print("🔧 System Setup and Verification")
        print(f"   Project root: {self.project_root}")
        print(f"   SSH Target: {self.ssh_user}@{self.ssh_host}")
    
    def verify_local_environment(self) -> Dict:
        """Verificar entorno local (Windows 11)"""
        results = {
            'python_version': None,
            'required_packages': [],
            'ssh_client': False,
            'rsync_available': False,
            'project_structure': False
        }
        
        try:
            # Python version
            results['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            print(f"✅ Python: {results['python_version']}")
            
            # Required packages
            required_packages = [
                'psutil', 'pyyaml', 'requests', 'pandas', 'selenium', 'seleniumbase'
            ]
            
            missing_packages = []
            for package in required_packages:
                try:
                    __import__(package)
                    results['required_packages'].append(f"{package}: ✅")
                except ImportError:
                    missing_packages.append(package)
                    results['required_packages'].append(f"{package}: ❌")
            
            if missing_packages:
                print(f"⚠️  Missing packages: {missing_packages}")
                print("   Install with: pip install " + " ".join(missing_packages))
            else:
                print("✅ All required packages available")
            
            # SSH client
            try:
                result = subprocess.run(['ssh', '-V'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    results['ssh_client'] = True
                    print("✅ SSH client available")
                else:
                    print("❌ SSH client not working")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                print("❌ SSH client not found")
            
            # rsync
            try:
                result = subprocess.run(['rsync', '--version'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    results['rsync_available'] = True
                    print("✅ rsync available")
                else:
                    print("⚠️  rsync not available (will use SCP)")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                print("⚠️  rsync not found (will use SCP)")
            
            # Project structure
            required_dirs = ['scrapers', 'orchestrator', 'utils', 'config', 'monitoring']
            missing_dirs = []
            
            for dir_name in required_dirs:
                dir_path = self.project_root / dir_name
                if dir_path.exists():
                    print(f"✅ {dir_name}/ directory exists")
                else:
                    missing_dirs.append(dir_name)
                    print(f"❌ {dir_name}/ directory missing")
            
            results['project_structure'] = len(missing_dirs) == 0
            
            return results
            
        except Exception as e:
            print(f"❌ Error verifying local environment: {e}")
            return results
    
    def test_ssh_connection(self) -> bool:
        """Probar conexión SSH al Dell T710"""
        try:
            print(f"🧪 Testing SSH connection to {self.ssh_user}@{self.ssh_host}...")
            
            # Test básico de conexión
            cmd = [
                'ssh', '-o', 'ConnectTimeout=10',
                '-o', 'BatchMode=yes',
                f'{self.ssh_user}@{self.ssh_host}',
                'echo "SSH_CONNECTION_TEST_OK"'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and "SSH_CONNECTION_TEST_OK" in result.stdout:
                print("✅ SSH connection successful")
                
                # Test de comandos adicionales
                commands_to_test = [
                    'python3 --version',
                    'which rclone',
                    'ls -la /home/esdata/',
                    'df -h'
                ]
                
                for test_cmd in commands_to_test:
                    try:
                        full_cmd = [
                            'ssh', f'{self.ssh_user}@{self.ssh_host}', test_cmd
                        ]
                        test_result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
                        
                        if test_result.returncode == 0:
                            print(f"   ✅ {test_cmd}: {test_result.stdout.strip()[:50]}")
                        else:
                            print(f"   ⚠️  {test_cmd}: {test_result.stderr.strip()[:50]}")
                    except:
                        print(f"   ❌ {test_cmd}: timeout or error")
                
                return True
            else:
                print(f"❌ SSH connection failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ SSH connection timeout")
            return False
        except Exception as e:
            print(f"❌ SSH connection error: {e}")
            return False
    
    def verify_remote_environment(self) -> Dict:
        """Verificar entorno remoto (Dell T710)"""
        results = {
            'python_available': False,
            'rclone_configured': False,
            'project_directory': False,
            'venv_available': False,
            'google_drive_access': False,
            'disk_space': None,
            'system_resources': {}
        }
        
        try:
            print("🔍 Verifying remote environment...")
            
            # Python availability
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 'python3 --version']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results['python_available'] = True
                python_version = result.stdout.strip()
                print(f"✅ Remote Python: {python_version}")
            else:
                print("❌ Python not available on remote")
            
            # rclone configuration
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 'rclone listremotes']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and 'gdrive:' in result.stdout:
                results['rclone_configured'] = True
                print("✅ rclone configured with Google Drive")
                
                # Test Google Drive access
                cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 'rclone ls gdrive: --max-depth 1']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    results['google_drive_access'] = True
                    print("✅ Google Drive access working")
                else:
                    print("⚠️  Google Drive access issues")
            else:
                print("❌ rclone not configured properly")
            
            # Project directory
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 'ls -la /home/esdata/PropertyScraper-Dell710/']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results['project_directory'] = True
                print("✅ Project directory exists on remote")
            else:
                print("⚠️  Project directory not found on remote")
            
            # Virtual environment
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 'ls -la /home/esdata/venv/bin/python']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results['venv_available'] = True
                print("✅ Python virtual environment available")
            else:
                print("⚠️  Virtual environment not found")
            
            # Disk space
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 'df -h /home']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                disk_info = result.stdout.strip().split('\n')[-1]
                results['disk_space'] = disk_info
                print(f"✅ Disk space: {disk_info}")
            
            # System resources
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 
                   'echo "CPU: $(nproc) cores"; echo "RAM: $(free -h | grep Mem | awk \'{print $2}\')"; echo "Load: $(uptime | cut -d\',\' -f4-)"']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results['system_resources'] = result.stdout.strip()
                print(f"✅ System resources: {result.stdout.strip()}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error verifying remote environment: {e}")
            return results
    
    def setup_remote_project(self) -> bool:
        """Configurar proyecto en servidor remoto"""
        try:
            print("🚀 Setting up project on remote server...")
            
            # Crear directorio del proyecto
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 
                   f'mkdir -p /home/esdata/PropertyScraper-Dell710']
            result = subprocess.run(cmd, timeout=30)
            
            # Crear estructura de directorios
            directories = [
                'scrapers', 'orchestrator', 'utils', 'config', 'monitoring',
                'data', 'logs', 'logs/checkpoints'
            ]
            
            for directory in directories:
                cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 
                       f'mkdir -p /home/esdata/PropertyScraper-Dell710/{directory}']
                subprocess.run(cmd, timeout=10)
            
            print("✅ Remote project structure created")
            
            # Sincronizar archivos principales
            print("📁 Syncing main project files...")
            
            if self.sync_essential_files():
                print("✅ Essential files synced")
                return True
            else:
                print("❌ Error syncing files")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up remote project: {e}")
            return False
    
    def sync_essential_files(self) -> bool:
        """Sincronizar archivos esenciales al servidor"""
        try:
            # Archivos y directorios esenciales
            essential_items = [
                'orchestrator/advanced_orchestrator.py',
                'utils/scraps_registry.py',
                'utils/gdrive_backup_manager.py',
                'utils/visual_terminal_monitor.py',
                'utils/checkpoint_recovery.py',
                'config/dell_t710_config.yaml',
                'config/ssh_config.json',
                'requirements.txt'
            ]
            
            for item in essential_items:
                local_path = self.project_root / item
                if local_path.exists():
                    remote_path = f'/home/esdata/PropertyScraper-Dell710/{item}'
                    
                    # Crear directorio remoto
                    remote_dir = '/'.join(remote_path.split('/')[:-1])
                    cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', f'mkdir -p {remote_dir}']
                    subprocess.run(cmd, timeout=10)
                    
                    # Copiar archivo
                    cmd = ['scp', str(local_path), f'{self.ssh_user}@{self.ssh_host}:{remote_path}']
                    result = subprocess.run(cmd, timeout=60)
                    
                    if result.returncode == 0:
                        print(f"   ✅ {item}")
                    else:
                        print(f"   ❌ {item}")
                else:
                    print(f"   ⚠️  {item} not found locally")
            
            return True
            
        except Exception as e:
            print(f"❌ Error syncing files: {e}")
            return False
    
    def initialize_system_data(self) -> bool:
        """Inicializar datos del sistema"""
        try:
            print("📋 Initializing system data...")
            
            # Ejecutar inicialización del registry
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 
                   'cd /home/esdata/PropertyScraper-Dell710 && /home/esdata/venv/bin/python utils/scraps_registry.py']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Scraps registry initialized")
            else:
                print(f"⚠️  Registry initialization: {result.stderr}")
            
            # Crear estructura de datos
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 
                   'cd /home/esdata/PropertyScraper-Dell710 && /home/esdata/venv/bin/python utils/create_data_structure.py']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ Data structure created")
            else:
                print(f"⚠️  Data structure: {result.stderr}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error initializing system data: {e}")
            return False
    
    def run_comprehensive_test(self) -> Dict:
        """Ejecutar test comprehensivo del sistema"""
        test_results = {
            'local_environment': {},
            'ssh_connection': False,
            'remote_environment': {},
            'project_setup': False,
            'data_initialization': False,
            'scraper_test': False,
            'orchestrator_test': False,
            'backup_test': False,
            'overall_status': 'UNKNOWN'
        }
        
        try:
            print("\n" + "="*60)
            print("🧪 COMPREHENSIVE SYSTEM TEST")
            print("="*60)
            
            # 1. Local environment
            print("\n1️⃣ LOCAL ENVIRONMENT")
            test_results['local_environment'] = self.verify_local_environment()
            
            # 2. SSH connection
            print("\n2️⃣ SSH CONNECTION")
            test_results['ssh_connection'] = self.test_ssh_connection()
            
            if not test_results['ssh_connection']:
                print("❌ Cannot continue without SSH connection")
                test_results['overall_status'] = 'FAILED'
                return test_results
            
            # 3. Remote environment
            print("\n3️⃣ REMOTE ENVIRONMENT")
            test_results['remote_environment'] = self.verify_remote_environment()
            
            # 4. Project setup
            print("\n4️⃣ PROJECT SETUP")
            test_results['project_setup'] = self.setup_remote_project()
            
            # 5. Data initialization
            print("\n5️⃣ DATA INITIALIZATION")
            test_results['data_initialization'] = self.initialize_system_data()
            
            # 6. Test scraper (basic)
            print("\n6️⃣ SCRAPER TEST")
            test_results['scraper_test'] = self.test_basic_scraper()
            
            # 7. Test backup
            print("\n7️⃣ BACKUP TEST")
            test_results['backup_test'] = self.test_backup_system()
            
            # Calculate overall status
            critical_tests = [
                test_results['ssh_connection'],
                test_results['project_setup'],
                test_results['data_initialization']
            ]
            
            if all(critical_tests):
                test_results['overall_status'] = 'PASSED'
            else:
                test_results['overall_status'] = 'FAILED'
            
            return test_results
            
        except Exception as e:
            print(f"❌ Error in comprehensive test: {e}")
            test_results['overall_status'] = 'ERROR'
            return test_results
    
    def test_basic_scraper(self) -> bool:
        """Test básico de un scraper"""
        try:
            print("🕷️ Testing basic scraper functionality...")
            
            # Test simple del registry
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 
                   'cd /home/esdata/PropertyScraper-Dell710 && /home/esdata/venv/bin/python utils/scraps_registry.py']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Scraper registry test passed")
                return True
            else:
                print(f"❌ Scraper test failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing scraper: {e}")
            return False
    
    def test_backup_system(self) -> bool:
        """Test del sistema de backup"""
        try:
            print("☁️ Testing backup system...")
            
            # Test rclone
            cmd = ['ssh', f'{self.ssh_user}@{self.ssh_host}', 
                   'cd /home/esdata/PropertyScraper-Dell710 && /home/esdata/venv/bin/python utils/gdrive_backup_manager.py --test-rclone']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Backup system test passed")
                return True
            else:
                print(f"⚠️  Backup system issues: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing backup: {e}")
            return False
    
    def display_final_report(self, test_results: Dict):
        """Mostrar reporte final"""
        print("\n" + "="*60)
        print("📊 FINAL SYSTEM REPORT")
        print("="*60)
        
        # Status general
        status = test_results['overall_status']
        if status == 'PASSED':
            print("🎉 SYSTEM STATUS: ✅ READY FOR OPERATION")
        elif status == 'FAILED':
            print("⚠️  SYSTEM STATUS: ❌ NEEDS ATTENTION")
        else:
            print("🤔 SYSTEM STATUS: ❓ UNKNOWN")
        
        print("\n📋 Test Results:")
        print(f"   SSH Connection: {'✅' if test_results['ssh_connection'] else '❌'}")
        print(f"   Project Setup:  {'✅' if test_results['project_setup'] else '❌'}")
        print(f"   Data Init:      {'✅' if test_results['data_initialization'] else '❌'}")
        print(f"   Scraper Test:   {'✅' if test_results['scraper_test'] else '❌'}")
        print(f"   Backup Test:    {'✅' if test_results['backup_test'] else '❌'}")
        
        if status == 'PASSED':
            print("\n🚀 Next Steps:")
            print("   1. python ssh_launcher.py --test-connection")
            print("   2. python ssh_launcher.py --launch-orchestrator")
            print("   3. python ssh_launcher.py --monitor")
        else:
            print("\n🔧 Required Actions:")
            if not test_results['ssh_connection']:
                print("   - Fix SSH connection to Dell T710")
            if not test_results['project_setup']:
                print("   - Complete project setup on remote server")
            if not test_results['data_initialization']:
                print("   - Initialize system data")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='System Setup and Verification for PropertyScraper Dell710')
    
    parser.add_argument('--local-only', action='store_true', help='Check local environment only')
    parser.add_argument('--ssh-test', action='store_true', help='Test SSH connection only')
    parser.add_argument('--remote-setup', action='store_true', help='Setup remote project')
    parser.add_argument('--full-test', action='store_true', help='Run comprehensive test')
    
    args = parser.parse_args()
    
    setup_system = SystemSetupVerification()
    
    if args.local_only:
        print("🖥️ Checking local environment...")
        results = setup_system.verify_local_environment()
    
    elif args.ssh_test:
        print("🔗 Testing SSH connection...")
        success = setup_system.test_ssh_connection()
        if success:
            print("✅ SSH connection working")
        else:
            print("❌ SSH connection failed")
    
    elif args.remote_setup:
        print("🚀 Setting up remote project...")
        success = setup_system.setup_remote_project()
        if success:
            print("✅ Remote setup completed")
        else:
            print("❌ Remote setup failed")
    
    elif args.full_test:
        print("🧪 Running comprehensive test...")
        test_results = setup_system.run_comprehensive_test()
        setup_system.display_final_report(test_results)
    
    else:
        print("\n🔧 System Setup and Verification")
        print("="*40)
        print("\n📋 Available commands:")
        print("  --local-only    : Check local environment")
        print("  --ssh-test      : Test SSH connection")
        print("  --remote-setup  : Setup remote project")
        print("  --full-test     : Run comprehensive test")
        print("\n💡 Recommended workflow:")
        print("  1. python system_setup.py --local-only")
        print("  2. python system_setup.py --ssh-test")
        print("  3. python system_setup.py --full-test")

if __name__ == "__main__":
    main()
