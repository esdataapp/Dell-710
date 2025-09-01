#!/usr/bin/env python3
"""
Enhanced Scraps Registry Manager - PropertyScraper Dell710
Sistema de registro y control de todos los scraps programados basado en los
archivos CSV individuales ubicados en el directorio ``URLs/``
"""

import csv
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from url_utils import extract_url_column

class EnhancedScrapsRegistry:
    """
    Gestor del registro completo de scraps con seguimiento de estado
    Adaptado para trabajar con los CSV almacenados en ``URLs/``
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.registry_file = self.project_root / 'data' / 'scraps_registry.csv'
        self.setup_logging()

        # Directorio que contiene los archivos de URLs individuales
        self.csv_urls_dir = self.project_root / 'URLs'

        # Migrar datos del registro antiguo si existe
        self.migrate_registry_to_csv_files()

        # Cargar las URLs con información de progreso
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

    # Columnas de progreso que se almacenarán en cada CSV de URLs
    progress_columns = ['Status', 'LastRun', 'NextRun', 'ScrapOfMonth', 'Records']

    def ensure_csv_progress_columns(self, csv_path: Path) -> None:
        """Asegurar que el archivo CSV contenga las columnas de progreso"""
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(row for row in f if not row.lstrip().startswith('#'))
                fieldnames = reader.fieldnames or []
                # Si todas las columnas existen, no hacer nada
                if all(col in fieldnames for col in self.progress_columns):
                    return

                rows = list(reader)

            # Añadir columnas faltantes con valores por defecto
            new_fieldnames = fieldnames + [col for col in self.progress_columns if col not in fieldnames]
            for row in rows:
                for col in self.progress_columns:
                    row.setdefault(col, 'False' if col == 'ScrapOfMonth' else '')

            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=new_fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        except Exception as e:
            self.logger.error(f"Error asegurando columnas en {csv_path}: {e}")

    def migrate_registry_to_csv_files(self) -> None:
        """Migrar datos del registro central a los archivos CSV individuales"""
        if not self.registry_file.exists():
            return

        self.logger.info("Migrando datos desde scraps_registry.csv a archivos de URLs")
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                registry_rows = list(reader)

            for reg_row in registry_rows:
                website = reg_row.get('website') or reg_row.get('PaginaWeb')
                if not website:
                    continue

                # Mapear website a archivo CSV
                file_map = {
                    'Inmuebles24': 'inm24_urls.csv',
                    'Casas_y_terrenos': 'cyt_urls.csv',
                    'lamudi': 'lam_urls.csv',
                    'mitula': 'mit_urls.csv',
                    'propiedades': 'prop_urls.csv',
                    'trovit': 'tro_urls.csv'
                }
                csv_filename = file_map.get(website)
                if not csv_filename:
                    continue

                csv_path = self.csv_urls_dir / csv_filename
                if not csv_path.exists():
                    continue

                self.ensure_csv_progress_columns(csv_path)

                try:
                    with open(csv_path, 'r', encoding='utf-8-sig') as f:
                        reader = csv.DictReader(row for row in f if not row.lstrip().startswith('#'))
                        fieldnames = reader.fieldnames or []
                        rows = list(reader)

                    # Buscar fila por URL
                    match_idx = None
                    for idx, row in enumerate(rows):
                        if row.get('URL', '').strip() == reg_row.get('url', '').strip():
                            match_idx = idx
                            break

                    if match_idx is not None:
                        row = rows[match_idx]
                        row['Status'] = reg_row.get('ultimo_estado', '')
                        row['LastRun'] = reg_row.get('ultima_ejecucion', '')
                        row['NextRun'] = reg_row.get('proxima_ejecucion', '')
                        # Guardar mes de la última ejecución como ScrapOfMonth
                        last_run = reg_row.get('ultima_ejecucion', '')
                        row['ScrapOfMonth'] = last_run[:7] if last_run else ''
                        row['Records'] = reg_row.get('registros_extraidos', '')
                        rows[match_idx] = row

                        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(rows)
                except Exception as e:
                    self.logger.error(f"Error migrando datos a {csv_path}: {e}")

        except Exception as e:
            self.logger.error(f"Error leyendo scraps_registry.csv: {e}")
        finally:
            try:
                os.remove(self.registry_file)
                self.logger.info("Archivo scraps_registry.csv eliminado tras migración")
            except OSError:
                pass
    
    def load_urls_from_csv(self) -> List[Dict]:
        """Cargar todas las URLs desde los archivos CSV del directorio URLs/"""
        urls_list: List[Dict] = []

        if not self.csv_urls_dir.exists():
            self.logger.warning(f"Directorio de URLs no encontrado: {self.csv_urls_dir}")
            return urls_list

        csv_files = list(self.csv_urls_dir.glob('*.csv'))
        if not csv_files:
            self.logger.warning(f"No se encontraron archivos CSV en {self.csv_urls_dir}")
            return urls_list

        for csv_file in csv_files:
            try:
                # Asegurar que existan las columnas de progreso
                self.ensure_csv_progress_columns(csv_file)

                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(
                        row for row in f if not row.lstrip().startswith('#')
                    )

                    for idx, row in enumerate(reader, 1):
                        pagina_web = row.get('PaginaWeb', '').strip()
                        ciudad = row.get('Ciudad', '').strip()
                        operacion = row.get('Operacion', row.get('Operación', '')).strip()
                        producto = row.get('ProductoPaginaWeb', '').strip()
                        url = extract_url_column(row)

                        if url and pagina_web:
                            url_id = f"{pagina_web.lower()}_{ciudad.lower().replace(' ', '_')}_{operacion.lower()}_{producto.lower().replace(' ', '_')}"
                            url_id = (
                                url_id.replace('/', '_')
                                .replace('-', '_')
                                .replace('ñ', 'n')
                                .replace('é', 'e')
                                .replace('í', 'i')
                                .replace('ó', 'o')
                                .replace('ú', 'u')
                            )

                            url_data = {
                                'id': url_id,
                                'website': pagina_web,
                                'ciudad': ciudad,
                                'operacion': operacion,
                                'producto': producto,
                                'url': url,
                                'prioridad': self.get_website_priority(pagina_web),
                                'intervalo_dias': self.get_interval_days(pagina_web),
                                'activo': True,
                                'csv_row': idx,
                                'csv_file': csv_file.name,
                                'status': row.get('Status', ''),
                                'last_run': row.get('LastRun', ''),
                                'next_run': row.get('NextRun', ''),
                                'scrap_of_month': row.get('ScrapOfMonth', ''),
                                'records': row.get('Records', '')
                            }
                            urls_list.append(url_data)
            except Exception as e:
                self.logger.error(f"Error cargando URLs desde {csv_file}: {e}")

        self.logger.info(
            f"Cargadas {len(urls_list)} URLs desde {len(csv_files)} archivos en {self.csv_urls_dir}"
        )
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
        """Método mantenido por compatibilidad (sin uso)"""
        self.logger.debug("initialize_registry ya no es necesario")
    
    def get_pending_scraps(self, website: str = None) -> List[Dict]:
        """Obtener scraps pendientes de ejecución"""
        now = datetime.now()
        pending_scraps: List[Dict] = []

        try:
            for scrap in self.urls_registry:
                if not scrap.get('activo', True):
                    continue

                if website and scrap['website'].lower() != website.lower():
                    continue

                next_run = scrap.get('next_run', '')

                if not next_run:
                    pending_scraps.append(scrap)
                else:
                    try:
                        if now >= datetime.fromisoformat(next_run):
                            pending_scraps.append(scrap)
                    except ValueError:
                        pending_scraps.append(scrap)

            pending_scraps.sort(
                key=lambda x: (int(x.get('prioridad', 10)), x.get('last_run', '1900-01-01'))
            )
            return pending_scraps

        except Exception as e:
            self.logger.error(f"Error obteniendo scraps pendientes: {e}")
            return []

    def get_next_scraps_to_run(self, max_count: int = 4) -> List[Dict]:
        """Obtener los próximos scraps a ejecutar según prioridades"""
        pending_scraps = self.get_pending_scraps()
        selected_scraps: List[Dict] = []
        used_websites = set()

        for scrap in pending_scraps:
            if len(selected_scraps) >= max_count:
                break
            if scrap['website'] not in used_websites:
                selected_scraps.append(scrap)
                used_websites.add(scrap['website'])

        return selected_scraps
    
    def get_scraps_by_website(self, website: str) -> List[Dict]:
        """Obtener todos los scraps de un sitio web específico"""
        try:
            scraps = [s for s in self.urls_registry if s['website'].lower() == website.lower()]
            scraps.sort(key=lambda x: int(x.get('prioridad', 10)))
            return scraps
        except Exception as e:
            self.logger.error(f"Error obteniendo scraps por website: {e}")
            return []
    
    def update_scrap_execution(self, scrap_id: str, status: str, records_extracted: int = 0,
                             execution_time_minutes: float = 0, observations: str = '') -> bool:
        """Actualizar el estado de ejecución de un scrap"""
        try:
            scrap = next((s for s in self.urls_registry if s['id'] == scrap_id), None)
            if not scrap:
                self.logger.warning(f"Scrap {scrap_id} no encontrado para actualizar")
                return False

            csv_path = self.csv_urls_dir / scrap['csv_file']
            self.ensure_csv_progress_columns(csv_path)

            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(row for row in f if not row.lstrip().startswith('#'))
                fieldnames = reader.fieldnames or []
                rows = list(reader)

            row_index = scrap['csv_row'] - 1
            if row_index >= len(rows):
                self.logger.warning(f"Índice de fila inválido para {scrap_id}")
                return False

            row = rows[row_index]
            now = datetime.now()
            next_run = now + timedelta(days=scrap.get('intervalo_dias', 30))

            row['Status'] = status
            row['LastRun'] = now.isoformat()
            row['NextRun'] = next_run.isoformat()
            row['ScrapOfMonth'] = now.strftime('%Y-%m')
            row['Records'] = str(records_extracted)
            rows[row_index] = row

            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            scrap.update({
                'status': status,
                'last_run': row['LastRun'],
                'next_run': row['NextRun'],
                'scrap_of_month': row['ScrapOfMonth'],
                'records': row['Records']
            })

            self.logger.info(f"Scrap {scrap_id} actualizado: {status}")
            return True

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
            total_registros = 0

            for scrap in self.urls_registry:
                stats['total_scraps'] += 1

                if scrap.get('activo', True):
                    stats['scraps_activos'] += 1

                website = scrap['website']
                if website not in stats['por_website']:
                    stats['por_website'][website] = {
                        'total': 0,
                        'activos': 0,
                        'ejecuciones': 0,
                        'exitosos': 0,
                        'fallidos': 0
                    }

                stats['por_website'][website]['total'] += 1

                if scrap.get('activo', True):
                    stats['por_website'][website]['activos'] += 1

                if scrap.get('last_run'):
                    stats['total_ejecuciones'] += 1
                    stats['por_website'][website]['ejecuciones'] += 1

                    if scrap.get('status', '').lower() == 'exitoso':
                        stats['ejecuciones_exitosas'] += 1
                        stats['por_website'][website]['exitosos'] += 1
                    else:
                        stats['ejecuciones_fallidas'] += 1
                        stats['por_website'][website]['fallidos'] += 1

                    try:
                        total_registros += int(scrap.get('records', 0))
                    except ValueError:
                        pass

            if stats['total_ejecuciones'] > 0:
                stats['promedio_registros'] = round(
                    total_registros / stats['total_ejecuciones'], 2
                )

            return stats

        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return stats

    def get_registry_stats(self) -> Dict:
        """Alias de get_statistics para compatibilidad"""
        return self.get_statistics()

    def get_csv_progress(self, csv_filename: str) -> Dict[str, int]:
        """Obtener resumen de progreso de un archivo CSV específico"""
        progress = {
            'total': 0,
            'completed': 0,
            'pending': 0,
            'success': 0,
            'failed': 0
        }

        csv_path = self.csv_urls_dir / csv_filename
        if not csv_path.exists():
            return progress

        self.ensure_csv_progress_columns(csv_path)
        now = datetime.now()

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(row for row in f if not row.lstrip().startswith('#'))
                for row in reader:
                    progress['total'] += 1
                    status = row.get('Status', '')
                    last_run = row.get('LastRun', '')
                    next_run = row.get('NextRun', '')

                    if last_run:
                        progress['completed'] += 1
                        if status.lower() == 'exitoso':
                            progress['success'] += 1
                        elif status:
                            progress['failed'] += 1

                    if not next_run:
                        progress['pending'] += 1
                    else:
                        try:
                            if datetime.fromisoformat(next_run) <= now:
                                progress['pending'] += 1
                        except ValueError:
                            progress['pending'] += 1

        except Exception as e:
            self.logger.error(f"Error obteniendo progreso de {csv_filename}: {e}")

        return progress

    def get_all_progress(self) -> Dict[str, Dict[str, int]]:
        """Obtener progreso de todos los archivos CSV"""
        progress: Dict[str, Dict[str, int]] = {}

        if not self.csv_urls_dir.exists():
            return progress

        for csv_file in self.csv_urls_dir.glob('*.csv'):
            progress[csv_file.name] = self.get_csv_progress(csv_file.name)

        return progress
    
    def get_output_path(self, scrap_data: Dict) -> Path:
        """Obtener la ruta de salida para un scrap específico"""
        website = scrap_data.get('website', '').lower()
        ciudad = scrap_data.get('ciudad', scrap_data.get('city', '')).lower().replace(' ', '_')
        operacion = scrap_data.get('operacion', scrap_data.get('operation', '')).lower()
        producto = scrap_data.get('producto', scrap_data.get('product', '')).lower().replace(' ', '_')

        # Crear estructura de carpetas organizada
        output_dir = self.project_root / 'data' / website / ciudad / operacion
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Nombre del archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{producto}_{timestamp}.csv"
        
        return output_dir / filename
    
    def get_backup_path(self, scrap_data: Dict) -> str:
        """Obtener la ruta de backup en Google Drive"""
        website = scrap_data.get('website', '')
        ciudad = scrap_data.get('ciudad', scrap_data.get('city', '')).replace(' ', '_')
        operacion = scrap_data.get('operacion', scrap_data.get('operation', ''))

        # Estructura para Google Drive
        return f"PropertyScraper/{website}/{ciudad}/{operacion}/"
    
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
