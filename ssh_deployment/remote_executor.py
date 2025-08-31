#!/usr/bin/env python3
"""
SSH Remote Executor - PropertyScraper Dell710
Ejecuta scrapers remotamente en Dell T710 via SSH desde Windows 11
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import paramiko
import yaml

class DellT710SSHExecutor:
    """
    Ejecutor SSH para Dell T710 Ubuntu Server
    Maneja conexión, despliegue y ejecución remota de scrapers
    """
    
    def __init__(self, config_path=None):
        self.setup_logging()
        
        # Cargar configuración
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'dell_t710_config.yaml'
        
        self.config = self.load_config(config_path)
        self.ssh_config = self.config['ssh_deployment']
        
        # Cliente SSH
        self.ssh_client = None
        self.sftp_client = None
        
        # Estado de conexión
        self.connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
        self.logger.info("🔧 SSH Executor inicializado para Dell T710")
        self.logger.info(f"   Host: {self.ssh_config['connection']['host']}")
        self.logger.info(f"   Usuario: {self.ssh_config['connection']['username']}")
    
    def setup_logging(self):
        """Configurar logging específico para SSH operations"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(__file__).parent.parent / 'logs' / f"ssh_executor_{timestamp}.log"
        
        # Asegurar que existe el directorio de logs
        log_file.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | SSH | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        # Reducir verbosidad de paramiko
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    
    def load_config(self, config_path: Path) -> Dict:
        """Cargar configuración desde archivo YAML"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"✅ Configuración cargada desde: {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"❌ Error cargando configuración: {e}")
            raise
    
    def connect(self) -> bool:
        """Establecer conexión SSH con Dell T710"""
        if self.connected:
            return True
        
        self.connection_attempts += 1
        
        try:
            self.logger.info(f"🔌 Conectando a Dell T710 (intento {self.connection_attempts}/{self.max_connection_attempts})...")
            
            # Crear cliente SSH
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Configuración de conexión
            connection_config = self.ssh_config['connection']
            
            # Conectar
            self.ssh_client.connect(
                hostname=connection_config['host'],
                port=connection_config['port'],
                username=connection_config['username'],
                key_filename=os.path.expanduser(connection_config.get('key_file', '~/.ssh/id_rsa')),
                timeout=connection_config['timeout'],
                auth_timeout=connection_config['timeout']
            )
            
            # Crear cliente SFTP
            self.sftp_client = self.ssh_client.open_sftp()
            
            self.connected = True
            self.logger.info("✅ Conexión SSH establecida exitosamente")
            
            # Verificar sistema remoto
            self.verify_remote_system()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error conectando SSH: {e}")
            
            if self.connection_attempts < self.max_connection_attempts:
                self.logger.info(f"🔄 Reintentando en 10 segundos...")
                time.sleep(10)
                return self.connect()
            else:
                self.logger.error("❌ Se agotaron los intentos de conexión")
                return False
    
    def disconnect(self):
        """Cerrar conexión SSH"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
                self.sftp_client = None
            
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
            
            self.connected = False
            self.logger.info("🔌 Conexión SSH cerrada")
            
        except Exception as e:
            self.logger.warning(f"⚠️  Error cerrando conexión: {e}")
    
    def verify_remote_system(self):
        """Verificar sistema remoto y configuración"""
        try:
            # Verificar información del sistema
            stdin, stdout, stderr = self.ssh_client.exec_command('uname -a && python3 --version && df -h')
            system_info = stdout.read().decode().strip()
            
            self.logger.info("🖥️  Sistema remoto verificado:")
            for line in system_info.split('\n'):
                if line.strip():
                    self.logger.info(f"   {line}")
            
            # Verificar directorio del proyecto
            project_root = self.ssh_config['remote_paths']['project_root']
            stdin, stdout, stderr = self.ssh_client.exec_command(f'ls -la {project_root} || echo "DIRECTORY_NOT_EXISTS"')
            result = stdout.read().decode().strip()
            
            if "DIRECTORY_NOT_EXISTS" in result:
                self.logger.warning(f"⚠️  Directorio del proyecto no existe: {project_root}")
                self.logger.info("🏗️  Será creado durante el despliegue")
            else:
                self.logger.info(f"✅ Directorio del proyecto encontrado: {project_root}")
            
        except Exception as e:
            self.logger.warning(f"⚠️  Error verificando sistema remoto: {e}")
    
    def execute_command(self, command: str, timeout=300) -> Tuple[int, str, str]:
        """Ejecutar comando remoto y retornar (exit_code, stdout, stderr)"""
        if not self.connected:
            raise ConnectionError("No hay conexión SSH activa")
        
        try:
            self.logger.info(f"💻 Ejecutando comando remoto: {command}")
            
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            # Leer salidas
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code == 0:
                self.logger.info(f"✅ Comando ejecutado exitosamente")
            else:
                self.logger.warning(f"⚠️  Comando terminó con código: {exit_code}")
            
            # Log de salida si hay errores
            if stderr_data.strip():
                self.logger.warning(f"stderr: {stderr_data.strip()}")
            
            return exit_code, stdout_data, stderr_data
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando comando: {e}")
            raise
    
    def sync_project_files(self, local_project_root: Path, exclude_patterns=None) -> bool:
        """Sincronizar archivos del proyecto con el servidor remoto"""
        if not self.connected:
            raise ConnectionError("No hay conexión SSH activa")
        
        try:
            remote_root = self.ssh_config['remote_paths']['project_root']
            exclude_patterns = exclude_patterns or self.ssh_config['sync_settings']['exclude_patterns']
            
            self.logger.info(f"📁 Sincronizando proyecto:")
            self.logger.info(f"   Local: {local_project_root}")
            self.logger.info(f"   Remoto: {remote_root}")
            
            # Crear directorio remoto si no existe
            self.execute_command(f"mkdir -p {remote_root}")
            
            # Función recursiva para sincronizar
            def sync_directory(local_dir: Path, remote_dir: str):
                files_synced = 0
                
                for item in local_dir.iterdir():
                    # Verificar patrones de exclusión
                    if any(pattern in str(item) for pattern in exclude_patterns):
                        continue
                    
                    remote_item_path = f"{remote_dir}/{item.name}"
                    
                    if item.is_file():
                        try:
                            # Verificar si el archivo necesita actualización
                            local_mtime = item.stat().st_mtime
                            
                            # Obtener mtime remoto
                            _, stdout, _ = self.ssh_client.exec_command(f"stat -c %Y {remote_item_path} 2>/dev/null || echo 0")
                            remote_mtime = float(stdout.read().decode().strip() or "0")
                            
                            # Sincronizar si es nuevo o más reciente
                            if local_mtime > remote_mtime:
                                self.sftp_client.put(str(item), remote_item_path)
                                files_synced += 1
                                self.logger.debug(f"📄 Sincronizado: {item.name}")
                            
                        except Exception as e:
                            self.logger.warning(f"⚠️  Error sincronizando {item.name}: {e}")
                    
                    elif item.is_dir():
                        # Crear directorio remoto
                        self.execute_command(f"mkdir -p {remote_item_path}")
                        files_synced += sync_directory(item, remote_item_path)
                
                return files_synced
            
            # Ejecutar sincronización
            total_synced = sync_directory(local_project_root, remote_root)
            
            self.logger.info(f"✅ Sincronización completada: {total_synced} archivos")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en sincronización: {e}")
            return False
    
    def deploy_project(self, local_project_root: Path) -> bool:
        """Desplegar proyecto completo en Dell T710"""
        try:
            self.logger.info("🚀 Iniciando despliegue en Dell T710...")
            
            # Conectar si no está conectado
            if not self.connect():
                return False
            
            # Sincronizar archivos
            if not self.sync_project_files(local_project_root):
                return False
            
            # Instalar dependencias
            remote_root = self.ssh_config['remote_paths']['project_root']
            python_env = self.ssh_config['remote_paths']['python_env']
            
            self.logger.info("📦 Instalando dependencias...")
            exit_code, stdout, stderr = self.execute_command(
                f"cd {remote_root} && {python_env} -m pip install -r requirements.txt",
                timeout=600
            )
            
            if exit_code != 0:
                self.logger.error(f"❌ Error instalando dependencias: {stderr}")
                return False
            
            # Verificar instalación
            exit_code, stdout, stderr = self.execute_command(
                f"cd {remote_root} && {python_env} -c 'import seleniumbase; print(\"SeleniumBase OK\")'",
                timeout=60
            )
            
            if exit_code == 0:
                self.logger.info("✅ Verificación de dependencias exitosa")
            else:
                self.logger.warning("⚠️  Problemas en verificación de dependencias")
            
            # Crear estructura de datos
            self.logger.info("🏗️  Creando estructura de datos...")
            exit_code, stdout, stderr = self.execute_command(
                f"cd {remote_root} && {python_env} utils/create_data_structure.py",
                timeout=300
            )
            
            self.logger.info("🎉 Despliegue completado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error en despliegue: {e}")
            return False
    
    def execute_scraper(self, scraper_name: str, parameters: Dict = None) -> Dict:
        """Ejecutar scraper específico remotamente"""
        try:
            if not self.connected:
                if not self.connect():
                    return {'success': False, 'error': 'No se pudo conectar SSH'}
            
            remote_root = self.ssh_config['remote_paths']['project_root']
            python_env = self.ssh_config['remote_paths']['python_env']
            
            # Construir comando
            if scraper_name == 'inmuebles24':
                script_path = f"{remote_root}/scrapers/inmuebles24_professional.py"
                
                # Parámetros por defecto
                params = parameters or {}
                headless_flag = "--headless" if params.get('headless', True) else "--gui"
                operation = params.get('operation', 'venta')
                max_pages = params.get('max_pages', 100)
                
                command = f"cd {remote_root} && {python_env} {script_path} {headless_flag} --operation={operation} --pages={max_pages}"
            else:
                return {'success': False, 'error': f'Scraper no soportado: {scraper_name}'}
            
            self.logger.info(f"🚀 Ejecutando scraper remoto: {scraper_name}")
            self.logger.info(f"   Comando: {command}")
            
            # Ejecutar con timeout extendido
            start_time = datetime.now()
            exit_code, stdout, stderr = self.execute_command(command, timeout=7200)  # 2 horas
            end_time = datetime.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            result = {
                'success': exit_code == 0,
                'scraper': scraper_name,
                'exit_code': exit_code,
                'execution_time_seconds': execution_time,
                'stdout': stdout,
                'stderr': stderr,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            
            if result['success']:
                self.logger.info(f"✅ Scraper {scraper_name} completado exitosamente")
                self.logger.info(f"⏱️  Tiempo de ejecución: {execution_time:.1f} segundos")
            else:
                self.logger.error(f"❌ Scraper {scraper_name} falló con código: {exit_code}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando scraper: {e}")
            return {
                'success': False,
                'error': str(e),
                'scraper': scraper_name
            }
    
    def get_remote_status(self) -> Dict:
        """Obtener estado del sistema remoto"""
        try:
            if not self.connected:
                return {'connected': False}
            
            # Información del sistema
            exit_code, stdout, stderr = self.execute_command(
                "uptime && free -h && df -h && ps aux | grep python | wc -l"
            )
            
            system_info = stdout.strip()
            
            # Estado de recursos
            exit_code, stdout, stderr = self.execute_command(
                "python3 -c \"import psutil; print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')\""
            )
            
            resource_info = stdout.strip()
            
            return {
                'connected': True,
                'system_info': system_info,
                'resource_info': resource_info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

def main():
    """Función principal para testing del SSH executor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dell T710 SSH Executor')
    parser.add_argument('--deploy', action='store_true', help='Desplegar proyecto')
    parser.add_argument('--status', action='store_true', help='Verificar estado remoto')
    parser.add_argument('--test-scraper', choices=['inmuebles24'], help='Probar scraper específico')
    parser.add_argument('--pages', type=int, default=5, help='Páginas para test')
    
    args = parser.parse_args()
    
    # Paths del proyecto
    project_root = Path(__file__).parent.parent
    
    with DellT710SSHExecutor() as executor:
        
        if args.deploy:
            print("🚀 Desplegando proyecto en Dell T710...")
            success = executor.deploy_project(project_root)
            print(f"Resultado: {'✅ Éxito' if success else '❌ Error'}")
        
        elif args.status:
            print("📊 Obteniendo estado del sistema remoto...")
            status = executor.get_remote_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
        
        elif args.test_scraper:
            print(f"🧪 Probando scraper: {args.test_scraper}")
            result = executor.execute_scraper(
                args.test_scraper, 
                {'headless': True, 'max_pages': args.pages, 'operation': 'venta'}
            )
            print(f"Resultado: {'✅ Éxito' if result['success'] else '❌ Error'}")
            if not result['success']:
                print(f"Error: {result.get('error', 'Unknown')}")
        
        else:
            print("Use --deploy, --status, o --test-scraper para ejecutar funciones")

if __name__ == "__main__":
    main()
