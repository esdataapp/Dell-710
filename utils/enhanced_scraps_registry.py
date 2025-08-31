#!/usr/bin/env python3
"""
Enhanced Scraps Registry Manager - PropertyScraper Dell710
Sistema de registro y control de todos los scraps programados basado en Lista de URLs.csv
"""

import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from url_utils import extract_url_column

class EnhancedScrapsRegistry:
    """
    Gestor del registro completo de scraps con seguimiento de estado
    Adaptado para trabajar con Lista de URLs.csv
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.registry_file = self.project_root / 'data' / 'scraps_registry.csv'
        self.progress_file = self.project_root / 'data' / 'scraps_progress.json'
        self.setup_logging()
        
        # Cargar URLs desde el archivo CSV de Lista de URLs
        self.csv_urls_file = self.project_root / 'Lista de URLs.csv'
        self.urls_registry = self.load_urls_from_csv()
        
        # Mapeo de sitios web
        self.websites = {
            1: "Inmuebles24",
            2: "Casas_y_terrenos", 
            3: "lamudi",
            4: "mitula",
            5: "propiedades",
            6: "trovit"
        }
        
        # Crear directorio de datos si no existe
        self.registry_file.parent.mkdir(exist_ok=True, parents=True)
        
        # Inicializar registry si no existe
        if not self.registry_file.exists():
            self.initialize_registry()
    
    def load_urls_from_csv(self) -> List[Dict]:
        """Cargar todas las URLs desde el archivo CSV"""
        urls_list = []
        
        if not self.csv_urls_file.exists():
            self.logger.warning(f"Archivo CSV no encontrado: {self.csv_urls_file}")
            return urls_list
        
        try:
            with open(self.csv_urls_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(
                    row for row in f if not row.lstrip().startswith('#')
                )

                for idx, row in enumerate(reader, 1):
                    # Normalizar nombres de columnas
                    pagina_web = row.get('PaginaWeb', '').strip()
                    estado = row.get('Estado', '').strip()
                    ciudad = row.get('Ciudad', '').strip()
                    operacion = row.get('Operación', row.get('Operacion', '')).strip()
                    producto = row.get('ProductoPaginaWeb', '').strip()
                    url = extract_url_column(row)

                    if url and pagina_web:
                        # Crear ID único para cada URL
                        url_id = f"{pagina_web.lower()}_{estado.lower()}_{ciudad.lower().replace(' ', '_')}_{operacion.lower()}_{producto.lower().replace(' ', '_')}"
                        url_id = url_id.replace('/', '_').replace('-', '_').replace('ñ', 'n').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
                        
                        url_data = {
                            'id': url_id,
                            'website': pagina_web,
                            'estado': estado,
                            'ciudad': ciudad,
                            'operacion': operacion,
                            'producto': producto,
                            'url': url,
                            'prioridad': self.get_website_priority(pagina_web),
                            'intervalo_dias': self.get_interval_days(pagina_web),
                            'activo': True,
                            'csv_row': idx
                        }
                        urls_list.append(url_data)
            
            self.logger.info(f"Cargadas {len(urls_list)} URLs desde {self.csv_urls_file}")
            return urls_list
            
        except Exception as e:
            self.logger.error(f"Error cargando URLs desde CSV: {e}")
            return urls_list
    
    def get_website_priority(self, website: str) -> int:
        """Obtener prioridad según el sitio web"""
        priorities = {
            'Inmuebles24': 1,
            'Casas_y_terrenos': 2,
            'lamudi': 3,
            'mitula': 4,
            'propiedades': 5,
            'trovit': 6
        }
        return priorities.get(website, 10)
    
    def get_interval_days(self, website: str) -> int:
        """Obtener intervalo de días según el sitio web"""
        intervals = {
            'Inmuebles24': 15,  # Cada 15 días como especificaste
            'Casas_y_terrenos': 7,
            'lamudi': 10,
            'mitula': 14,
            'propiedades': 21,
            'trovit': 14
        }
        return intervals.get(website, 30)
    
    def setup_logging(self):
        """Configurar logging"""
        log_dir = self.project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'scraps_registry.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('EnhancedScrapsRegistry')
    
    def initialize_registry(self):
        """Inicializar el registro CSV con todas las URLs"""
        headers = [
            'id', 'website', 'estado', 'ciudad', 'operacion', 'producto', 'url',
            'prioridad', 'intervalo_dias', 'activo', 'ultima_ejecucion',
            'proxima_ejecucion', 'total_ejecuciones', 'ejecuciones_exitosas',
            'ejecuciones_fallidas', 'ultimo_estado', 'registros_extraidos',
            'tiempo_promedio_minutos', 'observaciones'
        ]
        
        try:
            with open(self.registry_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                # Escribir todas las URLs del CSV
                for url_data in self.urls_registry:
                    row = [
                        url_data['id'],
                        url_data['website'],
                        url_data['estado'],
                        url_data['ciudad'],
                        url_data['operacion'],
                        url_data['producto'],
                        url_data['url'],
                        url_data['prioridad'],
                        url_data['intervalo_dias'],
                        url_data['activo'],
                        '',  # ultima_ejecucion
                        '',  # proxima_ejecucion
                        0,   # total_ejecuciones
                        0,   # ejecuciones_exitosas
                        0,   # ejecuciones_fallidas
                        'Pendiente',  # ultimo_estado
                        0,   # registros_extraidos
                        0,   # tiempo_promedio_minutos
                        ''   # observaciones
                    ]
                    writer.writerow(row)
            
            self.logger.info(f"Registry inicializado con {len(self.urls_registry)} URLs")
            
        except Exception as e:
            self.logger.error(f"Error inicializando registry: {e}")
    
    def get_pending_scraps(self, website: str = None) -> List[Dict]:
        """Obtener scraps pendientes de ejecución"""
        now = datetime.now()
        pending_scraps = []
        
        try:
            if not self.registry_file.exists():
                self.initialize_registry()
            
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    if row['activo'].lower() == 'true':
                        # Filtrar por website si se especifica
                        if website and row['website'].lower() != website.lower():
                            continue
                        
                        # Verificar si es tiempo de ejecutar
                        proxima_ejecucion = row.get('proxima_ejecucion', '')
                        
                        if not proxima_ejecucion:
                            # Primera ejecución
                            pending_scraps.append(dict(row))
                        else:
                            try:
                                proxima_fecha = datetime.fromisoformat(proxima_ejecucion)
                                if now >= proxima_fecha:
                                    pending_scraps.append(dict(row))
                            except ValueError:
                                # Error en formato de fecha, incluir para ejecución
                                pending_scraps.append(dict(row))
            
            # Ordenar por prioridad y luego por tiempo sin ejecutar
            pending_scraps.sort(key=lambda x: (
                int(x.get('prioridad', 10)),
                x.get('ultima_ejecucion', '1900-01-01')
            ))
            
            return pending_scraps
            
        except Exception as e:
            self.logger.error(f"Error obteniendo scraps pendientes: {e}")
            return []
    
    def get_scraps_by_website(self, website: str) -> List[Dict]:
        """Obtener todos los scraps de un sitio web específico"""
        scraps = []
        
        try:
            if not self.registry_file.exists():
                return scraps
            
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    if row['website'].lower() == website.lower():
                        scraps.append(dict(row))
            
            # Ordenar por prioridad
            scraps.sort(key=lambda x: int(x.get('prioridad', 10)))
            return scraps
            
        except Exception as e:
            self.logger.error(f"Error obteniendo scraps por website: {e}")
            return []
    
    def update_scrap_execution(self, scrap_id: str, status: str, records_extracted: int = 0, 
                             execution_time_minutes: float = 0, observations: str = '') -> bool:
        """Actualizar el estado de ejecución de un scrap"""
        try:
            # Leer el registro actual
            rows = []
            updated = False
            
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                for row in reader:
                    if row['id'] == scrap_id:
                        # Actualizar la fila
                        now = datetime.now()
                        intervalo_dias = int(row.get('intervalo_dias', 30))
                        proxima_ejecucion = now + timedelta(days=intervalo_dias)
                        
                        row['ultima_ejecucion'] = now.isoformat()
                        row['proxima_ejecucion'] = proxima_ejecucion.isoformat()
                        row['total_ejecuciones'] = str(int(row.get('total_ejecuciones', 0)) + 1)
                        
                        if status.lower() == 'exitoso':
                            row['ejecuciones_exitosas'] = str(int(row.get('ejecuciones_exitosas', 0)) + 1)
                        else:
                            row['ejecuciones_fallidas'] = str(int(row.get('ejecuciones_fallidas', 0)) + 1)
                        
                        row['ultimo_estado'] = status
                        row['registros_extraidos'] = str(records_extracted)
                        
                        # Actualizar tiempo promedio
                        total_ejecuciones = int(row['total_ejecuciones'])
                        tiempo_anterior = float(row.get('tiempo_promedio_minutos', 0))
                        nuevo_promedio = ((tiempo_anterior * (total_ejecuciones - 1)) + execution_time_minutes) / total_ejecuciones
                        row['tiempo_promedio_minutos'] = str(round(nuevo_promedio, 2))
                        
                        row['observaciones'] = observations
                        updated = True
                    
                    rows.append(row)
            
            if updated:
                # Escribir el archivo actualizado
                with open(self.registry_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                self.logger.info(f"Scrap {scrap_id} actualizado: {status}")
                return True
            else:
                self.logger.warning(f"Scrap {scrap_id} no encontrado para actualizar")
                return False
                
        except Exception as e:
            self.logger.error(f"Error actualizando scrap {scrap_id}: {e}")
            return False
    
    def get_next_scheduled_scrap(self, website: str = None) -> Optional[Dict]:
        """Obtener el próximo scrap programado"""
        pending_scraps = self.get_pending_scraps(website)
        
        if pending_scraps:
            return pending_scraps[0]
        
        return None
    
    def get_statistics(self) -> Dict:
        """Obtener estadísticas del registry"""
        stats = {
            'total_scraps': 0,
            'scraps_activos': 0,
            'por_website': {},
            'total_ejecuciones': 0,
            'ejecuciones_exitosas': 0,
            'ejecuciones_fallidas': 0,
            'promedio_registros': 0
        }
        
        try:
            if not self.registry_file.exists():
                return stats
            
            total_registros = 0
            ejecutados = 0
            
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    stats['total_scraps'] += 1
                    
                    if row['activo'].lower() == 'true':
                        stats['scraps_activos'] += 1
                    
                    website = row['website']
                    if website not in stats['por_website']:
                        stats['por_website'][website] = {
                            'total': 0,
                            'activos': 0,
                            'ejecuciones': 0,
                            'exitosos': 0,
                            'fallidos': 0
                        }
                    
                    stats['por_website'][website]['total'] += 1
                    
                    if row['activo'].lower() == 'true':
                        stats['por_website'][website]['activos'] += 1
                    
                    ejecuciones = int(row.get('total_ejecuciones', 0))
                    exitosos = int(row.get('ejecuciones_exitosas', 0))
                    fallidos = int(row.get('ejecuciones_fallidas', 0))
                    registros = int(row.get('registros_extraidos', 0))
                    
                    stats['total_ejecuciones'] += ejecuciones
                    stats['ejecuciones_exitosas'] += exitosos
                    stats['ejecuciones_fallidas'] += fallidos
                    
                    stats['por_website'][website]['ejecuciones'] += ejecuciones
                    stats['por_website'][website]['exitosos'] += exitosos
                    stats['por_website'][website]['fallidos'] += fallidos
                    
                    if ejecuciones > 0:
                        total_registros += registros
                        ejecutados += 1
            
            if ejecutados > 0:
                stats['promedio_registros'] = round(total_registros / ejecutados, 2)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return stats
    
    def get_output_path(self, scrap_data: Dict) -> Path:
        """Obtener la ruta de salida para un scrap específico"""
        website = scrap_data['website'].lower()
        estado = scrap_data['estado'].lower()
        ciudad = scrap_data['ciudad'].lower().replace(' ', '_')
        operacion = scrap_data['operacion'].lower()
        producto = scrap_data['producto'].lower().replace(' ', '_')
        
        # Crear estructura de carpetas organizada
        output_dir = self.project_root / 'data' / website / estado / ciudad / operacion
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Nombre del archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{producto}_{timestamp}.csv"
        
        return output_dir / filename
    
    def get_backup_path(self, scrap_data: Dict) -> str:
        """Obtener la ruta de backup en Google Drive"""
        website = scrap_data['website']
        estado = scrap_data['estado']
        ciudad = scrap_data['ciudad'].replace(' ', '_')
        operacion = scrap_data['operacion']
        
        # Estructura para Google Drive
        return f"PropertyScraper/{website}/{estado}/{ciudad}/{operacion}/"
    
    def export_registry_report(self) -> str:
        """Exportar reporte completo del registry"""
        report_file = self.project_root / 'logs' / f'registry_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        try:
            stats = self.get_statistics()
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=== REGISTRY REPORT ===\n")
                f.write(f"Generado: {datetime.now()}\n\n")
                
                f.write("ESTADÍSTICAS GENERALES:\n")
                f.write(f"- Total scraps: {stats['total_scraps']}\n")
                f.write(f"- Scraps activos: {stats['scraps_activos']}\n")
                f.write(f"- Total ejecuciones: {stats['total_ejecuciones']}\n")
                f.write(f"- Ejecuciones exitosas: {stats['ejecuciones_exitosas']}\n")
                f.write(f"- Ejecuciones fallidas: {stats['ejecuciones_fallidas']}\n")
                f.write(f"- Promedio registros por ejecución: {stats['promedio_registros']}\n\n")
                
                f.write("POR SITIO WEB:\n")
                for website, data in stats['por_website'].items():
                    f.write(f"\n{website}:\n")
                    f.write(f"  - Total: {data['total']}\n")
                    f.write(f"  - Activos: {data['activos']}\n")
                    f.write(f"  - Ejecuciones: {data['ejecuciones']}\n")
                    f.write(f"  - Exitosos: {data['exitosos']}\n")
                    f.write(f"  - Fallidos: {data['fallidos']}\n")
            
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"Error exportando reporte: {e}")
            return ""

def main():
    """Función de prueba"""
    registry = EnhancedScrapsRegistry()
    
    print("=== ENHANCED SCRAPS REGISTRY ===")
    print(f"URLs cargadas: {len(registry.urls_registry)}")
    
    stats = registry.get_statistics()
    print(f"\nEstadísticas:")
    print(f"- Total scraps: {stats['total_scraps']}")
    print(f"- Scraps activos: {stats['scraps_activos']}")
    
    print(f"\nPor sitio web:")
    for website, data in stats['por_website'].items():
        print(f"  {website}: {data['total']} URLs")
    
    # Mostrar algunos scraps pendientes
    pending = registry.get_pending_scraps()
    print(f"\nScraps pendientes: {len(pending)}")
    
    if pending:
        print("\nPrimeros 5 scraps pendientes:")
        for scrap in pending[:5]:
            print(f"  - {scrap['website']}: {scrap['ciudad']} - {scrap['producto']}")

if __name__ == "__main__":
    main()
