#!/usr/bin/env python3
"""
Scraps Registry Manager - PropertyScraper Dell710
Sistema de registro y control de todos los scraps programados
"""

import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

class ScrapsRegistry:
    """
    Gestor del registro completo de scraps con seguimiento de estado
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.registry_file = self.project_root / 'data' / 'scraps_registry.csv'
        self.progress_file = self.project_root / 'data' / 'scraps_progress.json'
        self.setup_logging()
        
        # Definición completa de scraps según tu especificación
        self.websites = {
            1: "inmuebles24",
            2: "casas_y_terrenos", 
            3: "lamudi",
            4: "mitula",
            5: "propiedades",
            6: "segundamano",
            7: "trovit"
        }
        
        self.operations = {
            1: "venta",
            2: "renta"
        }
        
        # Cargar URLs desde el archivo CSV de Lista de URLs
        self.csv_urls_file = self.project_root / 'Lista de URLs.csv'
        self.urls_registry = self.load_urls_from_csv()
        
        # URLs específicas para Inmuebles24 según tu lista (legacy support)
        self.inmuebles24_products = {}
            9: "https://www.inmuebles24.com/desarrollo-horizontal-en-venta-en-jalisco.html",
            10: "https://www.inmuebles24.com/desarrollo-horizontal-vertical-en-venta-en-jalisco.html",
            11: "https://www.inmuebles24.com/desarrollo-vertical-en-venta-en-jalisco.html",
            12: "https://www.inmuebles24.com/duplex-en-venta-en-jalisco.html",
            13: "https://www.inmuebles24.com/edificio-en-venta-en-jalisco.html",
            14: "https://www.inmuebles24.com/huerta-en-venta-en-jalisco.html",
            15: "https://www.inmuebles24.com/inmueble-productivo-urbano-en-venta-en-jalisco.html",
            16: "https://www.inmuebles24.com/local-en-centro-comercial-en-venta-en-jalisco.html",
            17: "https://www.inmuebles24.com/nave-industrial-en-venta-en-jalisco.html",
            18: "https://www.inmuebles24.com/oficinas-en-venta-en-jalisco.html",
            19: "https://www.inmuebles24.com/quinta-en-venta-en-jalisco.html",
            20: "https://www.inmuebles24.com/terreno-comercial-en-venta-en-jalisco.html",
            21: "https://www.inmuebles24.com/terreno-industrial-en-venta-en-jalisco.html",
            22: "https://www.inmuebles24.com/villa-en-venta-en-jalisco.html"
        }
        
        self.initialize_registry()
    
    def setup_logging(self):
        """Configurar logging para el registry"""
        self.logger = logging.getLogger('ScrapsRegistry')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | REGISTRY | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def initialize_registry(self):
        """Inicializar el registro completo de scraps"""
        if not self.registry_file.exists():
            self.create_complete_registry()
        else:
            self.logger.info("📋 Registry existente encontrado")
    
    def create_complete_registry(self):
        """Crear el registro completo de todos los scraps posibles"""
        self.logger.info("🔨 Creando registry completo de scraps...")
        
        # Asegurar que existe el directorio
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        
        scraps = []
        scrap_id = 1
        
        # Generar todos los scraps según el flujo de trabajo especificado
        for website_id, website_name in self.websites.items():
            for operation_id, operation_name in self.operations.items():
                
                if website_name == "inmuebles24":
                    # Para Inmuebles24 usar las URLs específicas
                    for product_id, product_url in self.inmuebles24_products.items():
                        # Ajustar URL para renta si es necesario
                        if operation_name == "renta":
                            product_url = product_url.replace("-en-venta-", "-en-renta-")
                        
                        product_name = self.extract_product_name_from_url(product_url)
                        
                        scrap = {
                            'scrap_id': scrap_id,
                            'website': website_name,
                            'operation': operation_name,
                            'product': product_name,
                            'url': product_url,
                            'status': 'pending',  # pending, running, completed, failed, paused
                            'priority': website_id,  # Prioridad por website
                            'estimated_pages': self.estimate_pages(website_name, product_name),
                            'last_run': None,
                            'next_run': None,
                            'completed_count': 0,
                            'failed_count': 0,
                            'checkpoint_page': 0,
                            'properties_scraped': 0,
                            'execution_time_minutes': 0,
                            'created_date': datetime.now().isoformat(),
                            'notes': ''
                        }
                        scraps.append(scrap)
                        scrap_id += 1
                else:
                    # Para otros websites, crear scraps genéricos
                    scrap = {
                        'scrap_id': scrap_id,
                        'website': website_name,
                        'operation': operation_name,
                        'product': 'general',
                        'url': f"https://www.{website_name}.com/{operation_name}/jalisco",
                        'status': 'pending',
                        'priority': website_id,
                        'estimated_pages': self.estimate_pages(website_name, 'general'),
                        'last_run': None,
                        'next_run': None,
                        'completed_count': 0,
                        'failed_count': 0,
                        'checkpoint_page': 0,
                        'properties_scraped': 0,
                        'execution_time_minutes': 0,
                        'created_date': datetime.now().isoformat(),
                        'notes': ''
                    }
                    scraps.append(scrap)
                    scrap_id += 1
        
        # Guardar en CSV
        self.save_scraps_to_csv(scraps)
        self.logger.info(f"✅ Registry creado con {len(scraps)} scraps")
    
    def extract_product_name_from_url(self, url: str) -> str:
        """Extraer nombre del producto de la URL"""
        # Extraer entre el dominio y "-en-venta" o "-en-renta"
        parts = url.split('/')[-1].replace('.html', '')
        if '-en-venta-' in parts:
            return parts.split('-en-venta-')[0]
        elif '-en-renta-' in parts:
            return parts.split('-en-renta-')[0]
        return parts
    
    def estimate_pages(self, website: str, product: str) -> int:
        """Estimar número de páginas basado en website y producto"""
        estimates = {
            'inmuebles24': {
                'departamentos': 100,
                'casas': 150,
                'terrenos': 80,
                'default': 50
            },
            'default': 50
        }
        
        if website in estimates:
            if any(key in product for key in estimates[website]):
                for key, value in estimates[website].items():
                    if key in product:
                        return value
            return estimates[website].get('default', 50)
        return estimates['default']
    
    def save_scraps_to_csv(self, scraps: List[Dict]):
        """Guardar scraps en archivo CSV"""
        fieldnames = [
            'scrap_id', 'website', 'operation', 'product', 'url', 'status', 'priority',
            'estimated_pages', 'last_run', 'next_run', 'completed_count', 'failed_count',
            'checkpoint_page', 'properties_scraped', 'execution_time_minutes', 
            'created_date', 'notes'
        ]
        
        with open(self.registry_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(scraps)
    
    def load_scraps_from_csv(self) -> List[Dict]:
        """Cargar scraps desde archivo CSV"""
        if not self.registry_file.exists():
            return []
        
        scraps = []
        with open(self.registry_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convertir tipos de datos
                row['scrap_id'] = int(row['scrap_id'])
                row['priority'] = int(row['priority'])
                row['estimated_pages'] = int(row['estimated_pages'])
                row['completed_count'] = int(row['completed_count'])
                row['failed_count'] = int(row['failed_count'])
                row['checkpoint_page'] = int(row['checkpoint_page'])
                row['properties_scraped'] = int(row['properties_scraped'])
                row['execution_time_minutes'] = int(row['execution_time_minutes'])
                scraps.append(row)
        return scraps
    
    def update_scrap_status(self, scrap_id: int, status: str, **kwargs):
        """Actualizar el estado de un scrap específico"""
        scraps = self.load_scraps_from_csv()
        
        for scrap in scraps:
            if scrap['scrap_id'] == scrap_id:
                scrap['status'] = status
                
                # Actualizar campos adicionales
                for key, value in kwargs.items():
                    if key in scrap:
                        scrap[key] = value
                
                # Actualizar timestamp si se completa
                if status == 'completed':
                    scrap['last_run'] = datetime.now().isoformat()
                    scrap['next_run'] = (datetime.now() + timedelta(days=15)).isoformat()
                    scrap['completed_count'] += 1
                elif status == 'failed':
                    scrap['failed_count'] += 1
                elif status == 'running':
                    scrap['last_run'] = datetime.now().isoformat()
                
                break
        
        self.save_scraps_to_csv(scraps)
        self.logger.info(f"📝 Scrap {scrap_id} actualizado a estado: {status}")
    
    def get_next_scraps_to_run(self, max_count: int = 4) -> List[Dict]:
        """Obtener los próximos scraps a ejecutar según prioridades"""
        scraps = self.load_scraps_from_csv()
        
        # Filtrar scraps pendientes o que necesiten re-ejecución
        available_scraps = []
        for scrap in scraps:
            if scrap['status'] == 'pending':
                available_scraps.append(scrap)
            elif scrap['status'] == 'completed' and scrap['next_run']:
                next_run = datetime.fromisoformat(scrap['next_run'])
                if datetime.now() >= next_run:
                    available_scraps.append(scrap)
        
        # Ordenar por prioridad (website) y luego por operation
        available_scraps.sort(key=lambda x: (x['priority'], x['operation']))
        
        # Seleccionar scraps asegurando que no haya duplicados de website
        selected_scraps = []
        used_websites = set()
        
        for scrap in available_scraps:
            if len(selected_scraps) >= max_count:
                break
            
            if scrap['website'] not in used_websites:
                selected_scraps.append(scrap)
                used_websites.add(scrap['website'])
        
        return selected_scraps
    
    def get_registry_stats(self) -> Dict:
        """Obtener estadísticas del registry"""
        scraps = self.load_scraps_from_csv()
        
        stats = {
            'total_scraps': len(scraps),
            'pending': len([s for s in scraps if s['status'] == 'pending']),
            'completed': len([s for s in scraps if s['status'] == 'completed']),
            'failed': len([s for s in scraps if s['status'] == 'failed']),
            'running': len([s for s in scraps if s['status'] == 'running']),
            'paused': len([s for s in scraps if s['status'] == 'paused']),
            'websites': len(set(s['website'] for s in scraps)),
            'total_properties_scraped': sum(s['properties_scraped'] for s in scraps),
            'total_execution_time_hours': sum(s['execution_time_minutes'] for s in scraps) / 60
        }
        
        return stats
    
    def display_registry_status(self):
        """Mostrar estado actual del registry en terminal"""
        stats = self.get_registry_stats()
        
        print("\n" + "="*60)
        print("📋 SCRAPS REGISTRY STATUS")
        print("="*60)
        print(f"📊 Total Scraps: {stats['total_scraps']}")
        print(f"⏳ Pending: {stats['pending']}")
        print(f"✅ Completed: {stats['completed']}")
        print(f"❌ Failed: {stats['failed']}")
        print(f"🔄 Running: {stats['running']}")
        print(f"⏸️  Paused: {stats['paused']}")
        print(f"🌐 Websites: {stats['websites']}")
        print(f"🏠 Properties Scraped: {stats['total_properties_scraped']}")
        print(f"⏱️  Total Execution Time: {stats['total_execution_time_hours']:.1f} hours")
        print("="*60)
    
    def export_progress_report(self) -> str:
        """Exportar reporte de progreso detallado"""
        scraps = self.load_scraps_from_csv()
        stats = self.get_registry_stats()
        
        report_file = self.project_root / 'data' / f'progress_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'stats': stats,
            'scraps_detail': scraps,
            'next_scraps_to_run': self.get_next_scraps_to_run(10)
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📄 Reporte exportado: {report_file}")
        return str(report_file)

if __name__ == "__main__":
    registry = ScrapsRegistry()
    registry.display_registry_status()
