#!/usr/bin/env python3
"""
Casas y Terrenos Professional Scraper - PropertyScraper Dell710
Scraper profesional optimizado para Dell T710 con capacidades de resilencia
Adaptado para trabajar con ``URLs/cyt_urls.csv``
"""

import os
import sys
import json
import time
import csv
import logging
import pickle
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

from utils.url_utils import (
    extract_url_column,
    load_urls_from_csv,
    load_urls_for_site,
)
from utils.path_builder import build_path
from utils.browser_config import get_chromium_args

# Selenium imports
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class CasasTerrenosProfessionalScraper:
    """
    Scraper profesional para casasyterrenos.com con capacidades de resilencia
    Optimizado para ejecución en Dell T710 Ubuntu Server
    Adaptado para trabajar con URLs del registro CSV
    """
    
    def __init__(self, url=None, output_path=None, headless=True, max_pages=None,
                 resume_from=None, operation_type='venta', ciudad='Ciudad',
                 operacion='Operacion', producto='Producto'):
        # Parámetros principales
        self.target_url = url
        self.output_path = output_path
        self.headless = headless
        self.max_pages = max_pages
        self.resume_from = resume_from or 1
        self.operation_type = operation_type  # venta, renta, etc.
        self.ciudad = ciudad
        self.operacion = operacion
        self.producto = producto

        # Configuración de paths
        self.setup_paths(ciudad, operacion, producto)
        
        # Configuración de logging
        self.setup_logging()
        
        # Checkpoint system
        self.checkpoint_file = self.checkpoint_dir / f"{self.site_name}_checkpoint.pkl"
        self.checkpoint_interval = 50  # Guardar cada 50 páginas
        
        # Datos del scraping
        self.properties_data = []
        
        # Performance metrics
        self.start_time = None
        self.pages_processed = 0
        self.properties_found = 0
        self.errors_count = 0
        
        # Configuración anti-detección
        self.user_agents = [
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
        
        # Selectores específicos para Casas y Terrenos
        self.selectors = {
            'property_cards': '.property-card, .listing-item, .property-item, .inmueble-item',
            'title': 'h2 a, h3 a, .property-title a, .titulo-inmueble a',
            'price': '.price, .precio, .property-price, .precio-inmueble',
            'location': '.location, .ubicacion, .property-location, .ubicacion-inmueble',
            'area': '.area, .superficie, .property-area, .mt2',
            'rooms': '.rooms, .recamaras, .bedrooms, .habitaciones',
            'bathrooms': '.bathrooms, .banos', 
            'features': '.features, .caracteristicas, .amenities',
            'description': '.description, .descripcion',
            'images': '.property-images img, .galeria img, .fotos img',
            'contact': '.contact-info, .telefono, .whatsapp',
            'next_page': '.pagination .next, .paginacion .siguiente, a[rel="next"]'
        }
        
        self.logger.info(f"🚀 Iniciando {self.site_name} Professional Scraper")
        self.logger.info(f"   URL objetivo: {url}")
        self.logger.info(f"   Archivo salida: {output_path}")
        self.logger.info(f"   Max pages: {max_pages}")
        self.logger.info(f"   Resume from: {resume_from}")
        self.logger.info(f"   Headless: {headless}")
    
    def setup_paths(self, ciudad: str, operacion: str, producto: str):
        """Configurar estructura de paths del proyecto"""
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / 'logs'
        self.checkpoint_dir = self.logs_dir / 'checkpoints'
        self.site_name = 'CyT'

        path_info = build_path(self.site_name, ciudad, operacion, producto)
        self.month_year = path_info.month_year
        self.run_number = int(path_info.run_number)
        self.run_dir = path_info.directory
        self.data_dir = self.run_dir
        self.file_name = path_info.file_name

        for directory in [self.logs_dir, self.checkpoint_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Configurar sistema de logging profesional"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.logs_dir / f"{self.site_name}_professional_{timestamp}.log"
        
        # Configuración de logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.log_file = log_file
    
    def create_professional_driver(self):
        """
        Crear driver optimizado para Dell T710 con técnicas anti-detección probadas
        """
        self.logger.info("🔧 Creando driver profesional optimizado...")
        
        # Configuración específica para Dell T710
        sb_config = {
            'headless': self.headless,
            'disable_dev_shm_usage': True,
            'disable_gpu': True,
            'disable_features': 'VizDisplayCompositor',
            'disable_extensions': True,
            'disable_plugins': True,
            'disable_images': False,  # Mantener imágenes para mejor detección
            'disable_javascript': False,
            'block_images': False,
            'maximize_window': not self.headless,
            'window_size': "1920,1080" if self.headless else None,
            'user_agent': random.choice(self.user_agents),
            'locale_code': 'es-MX',
            'timeout': 30,
            'chromium_arg': get_chromium_args()
        }
        
        return sb_config
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Cargar checkpoint anterior si existe"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                self.logger.info(f"📂 Checkpoint cargado: página {checkpoint.get('last_page', 0)}")
                return checkpoint
            except Exception as e:
                self.logger.warning(f"⚠️  Error cargando checkpoint: {e}")
        return None
    
    def save_checkpoint(self, page_num: int):
        """Guardar checkpoint del progreso actual"""
        checkpoint = {
            'last_page': page_num,
            'properties_count': len(self.properties_data),
            'timestamp': datetime.now().isoformat(),
            'target_url': self.target_url
        }
        
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint, f)
            self.logger.info(f"💾 Checkpoint guardado: página {page_num}")
        except Exception as e:
            self.logger.error(f"❌ Error guardando checkpoint: {e}")
    
    def extract_property_data(self, sb) -> List[Dict]:
        """
        Extraer datos de propiedades usando selectores optimizados para Casas y Terrenos
        """
        properties = []
        
        try:
            # Buscar elementos de propiedades con múltiples selectores
            property_cards = []
            selectors_to_try = self.selectors['property_cards'].split(', ')
            
            for selector in selectors_to_try:
                try:
                    elements = sb.find_elements(selector)
                    if elements:
                        property_cards = elements
                        self.logger.info(f"✅ Encontrados {len(elements)} property cards con selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not property_cards:
                self.logger.warning("⚠️  No se encontraron property cards")
                return properties
            
            for i, card in enumerate(property_cards):
                try:
                    # Extraer datos básicos con manejo de errores
                    property_data = {
                        'timestamp': datetime.now().isoformat(),
                        'source_url': self.target_url,
                        'source_page': sb.get_current_url(),
                        'fuente': self.site_name
                    }
                    
                    # Título/Descripción
                    try:
                        title_selectors = self.selectors['title'].split(', ')
                        for selector in title_selectors:
                            try:
                                title_element = card.find_element(By.CSS_SELECTOR, selector)
                                property_data['titulo'] = title_element.text.strip()
                                property_data['link'] = title_element.get_attribute('href') or ''
                                break
                            except:
                                continue
                        else:
                            property_data['titulo'] = "N/A"
                            property_data['link'] = "N/A"
                    except:
                        property_data['titulo'] = "N/A"
                        property_data['link'] = "N/A"
                    
                    # Precio
                    try:
                        price_selectors = self.selectors['price'].split(', ')
                        for selector in price_selectors:
                            try:
                                price_element = card.find_element(By.CSS_SELECTOR, selector)
                                property_data['precio'] = price_element.text.strip()
                                break
                            except:
                                continue
                        else:
                            property_data['precio'] = "N/A"
                    except:
                        property_data['precio'] = "N/A"
                    
                    # Ubicación
                    try:
                        location_selectors = self.selectors['location'].split(', ')
                        for selector in location_selectors:
                            try:
                                location_element = card.find_element(By.CSS_SELECTOR, selector)
                                property_data['ubicacion'] = location_element.text.strip()
                                break
                            except:
                                continue
                        else:
                            property_data['ubicacion'] = "N/A"
                    except:
                        property_data['ubicacion'] = "N/A"
                    
                    # Área/Superficie
                    try:
                        area_selectors = self.selectors['area'].split(', ')
                        for selector in area_selectors:
                            try:
                                area_element = card.find_element(By.CSS_SELECTOR, selector)
                                property_data['area'] = area_element.text.strip()
                                break
                            except:
                                continue
                        else:
                            property_data['area'] = "N/A"
                    except:
                        property_data['area'] = "N/A"
                    
                    # Habitaciones
                    try:
                        rooms_selectors = self.selectors['rooms'].split(', ')
                        for selector in rooms_selectors:
                            try:
                                rooms_element = card.find_element(By.CSS_SELECTOR, selector)
                                property_data['habitaciones'] = rooms_element.text.strip()
                                break
                            except:
                                continue
                        else:
                            property_data['habitaciones'] = "N/A"
                    except:
                        property_data['habitaciones'] = "N/A"
                    
                    # Baños
                    try:
                        bathrooms_selectors = self.selectors['bathrooms'].split(', ')
                        for selector in bathrooms_selectors:
                            try:
                                bathrooms_element = card.find_element(By.CSS_SELECTOR, selector)
                                property_data['banos'] = bathrooms_element.text.strip()
                                break
                            except:
                                continue
                        else:
                            property_data['banos'] = "N/A"
                    except:
                        property_data['banos'] = "N/A"
                    
                    # Características
                    try:
                        features_elements = card.find_elements(By.CSS_SELECTOR, self.selectors['features'])
                        features_text = [f.text.strip() for f in features_elements if f.text.strip()]
                        property_data['caracteristicas'] = " | ".join(features_text) if features_text else "N/A"
                    except:
                        property_data['caracteristicas'] = "N/A"
                    
                    # Descripción
                    try:
                        description_element = card.find_element(By.CSS_SELECTOR, self.selectors['description'])
                        property_data['descripcion'] = description_element.text.strip()
                    except:
                        property_data['descripcion'] = "N/A"
                    
                    # Imágenes
                    try:
                        image_elements = card.find_elements(By.CSS_SELECTOR, self.selectors['images'])
                        images = [img.get_attribute('src') for img in image_elements if img.get_attribute('src')]
                        property_data['imagenes'] = " | ".join(images) if images else "N/A"
                    except:
                        property_data['imagenes'] = "N/A"
                    
                    # Información de contacto
                    try:
                        contact_element = card.find_element(By.CSS_SELECTOR, self.selectors['contact'])
                        property_data['contacto'] = contact_element.text.strip()
                    except:
                        property_data['contacto'] = "N/A"
                    
                    # Agregar solo si tiene datos válidos
                    if property_data['titulo'] != "N/A" or property_data['precio'] != "N/A":
                        properties.append(property_data)
                        
                except Exception as e:
                    self.logger.warning(f"⚠️  Error extrayendo propiedad {i+1}: {e}")
                    continue
            
            self.logger.info(f"✅ Extraídas {len(properties)} propiedades válidas")
            return properties
            
        except Exception as e:
            self.logger.error(f"❌ Error en extract_property_data: {e}")
            return []
    
    def wait_and_check_blocking(self, sb, timeout=10) -> bool:
        """
        Verificar si la página está disponible o bloqueada
        """
        try:
            # Esperar a que carguen elementos de propiedades o verificar bloqueo
            WebDriverWait(sb.driver, timeout).until(
                lambda driver: (
                    driver.find_elements(By.CSS_SELECTOR, ".property-card") or
                    driver.find_elements(By.CSS_SELECTOR, ".listing-item") or
                    driver.find_elements(By.CSS_SELECTOR, "#challenge-form") or
                    driver.find_elements(By.CSS_SELECTOR, ".cf-browser-verification")
                )
            )
            
            # Verificar si hay elementos de bloqueo
            blocking_selectors = [
                "#challenge-form",
                ".cf-browser-verification", 
                ".cf-checking-browser",
                "title:contains('Just a moment')",
                "h1:contains('Checking your browser')"
            ]
            
            for selector in blocking_selectors:
                if sb.is_element_visible(selector):
                    self.logger.warning(f"🚫 Página bloqueada - detectado: {selector}")
                    return False
            
            # Verificar si hay propiedades
            properties_found = (
                sb.find_elements(".property-card") or
                sb.find_elements(".listing-item") or
                sb.find_elements(".property-item")
            )
            
            if properties_found:
                self.logger.info(f"✅ Página cargada correctamente - {len(properties_found)} propiedades detectadas")
                return True
            else:
                self.logger.warning("⚠️  Página cargada pero sin propiedades detectadas")
                return False
                
        except TimeoutException:
            self.logger.error("❌ Timeout esperando que cargue la página")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error verificando bloqueo: {e}")
            return False
    
    def detect_pagination(self, sb) -> bool:
        """Detectar si la página tiene paginación"""
        try:
            # Buscar elementos de paginación
            pagination_selectors = [
                '.pagination',
                '.paginacion',
                '.pager',
                'a[href*="pagina"]',
                'a[href*="page"]',
                '.next',
                '.siguiente'
            ]
            
            for selector in pagination_selectors:
                if sb.find_elements(selector):
                    self.logger.info(f"✅ Paginación detectada con selector: {selector}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error detectando paginación: {e}")
            return False
    
    def scrape_pages(self) -> Tuple[int, int]:
        """
        Método principal de scraping con resilencia y checkpoints
        Retorna (total_pages, total_properties)
        """
        self.start_time = datetime.now()
        
        # Cargar checkpoint si existe
        checkpoint = self.load_checkpoint()
        if checkpoint and self.resume_from == 1:
            self.resume_from = checkpoint.get('last_page', 1) + 1
            self.logger.info(f"🔄 Resumiendo desde página {self.resume_from}")
        
        with SB(**self.create_professional_driver()) as sb:
            
            current_page = self.resume_from
            consecutive_failures = 0
            max_consecutive_failures = 5
            
            # Verificar si la URL tiene paginación
            has_pagination = True
            if not self.target_url:
                self.logger.error("❌ No se proporcionó URL objetivo")
                return 0, 0
            
            while True:
                # Verificar límite de páginas
                if self.max_pages and current_page > self.max_pages:
                    self.logger.info(f"🏁 Límite de páginas alcanzado: {self.max_pages}")
                    break
                
                try:
                    # Construir URL de la página
                    if current_page == 1:
                        page_url = self.target_url
                    else:
                        # Detectar patrón de paginación en la URL
                        if 'pagina=' in self.target_url:
                            page_url = self.target_url.replace('pagina=1', f'pagina={current_page}')
                        elif '?' in self.target_url:
                            page_url = f"{self.target_url}&pagina={current_page}"
                        else:
                            page_url = f"{self.target_url}?pagina={current_page}"
                    
                    self.logger.info(f"📄 Procesando página {current_page}: {page_url}")
                    
                    # Navegar a la página
                    sb.open(page_url)
                    
                    # Verificar bloqueo y esperar carga
                    if not self.wait_and_check_blocking(sb):
                        consecutive_failures += 1
                        self.errors_count += 1
                        
                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.error(f"❌ Demasiados fallos consecutivos ({consecutive_failures}). Deteniendo scraping.")
                            break
                        
                        self.logger.warning(f"⚠️  Página {current_page} falló. Intentando siguiente...")
                        current_page += 1
                        time.sleep(5)  # Pausa antes del siguiente intento
                        continue
                    
                    # Extraer datos de propiedades
                    page_properties = self.extract_property_data(sb)
                    
                    if not page_properties:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.warning(f"⚠️  Sin propiedades por {consecutive_failures} páginas consecutivas. Posible fin de resultados.")
                            break
                    else:
                        consecutive_failures = 0  # Reset contador de fallos
                        self.properties_data.extend(page_properties)
                        self.properties_found += len(page_properties)
                    
                    self.pages_processed += 1
                    
                    # Guardar checkpoint cada N páginas
                    if current_page % self.checkpoint_interval == 0:
                        self.save_checkpoint(current_page)
                    
                    # Log de progreso
                    elapsed = datetime.now() - self.start_time
                    avg_time_per_page = elapsed.total_seconds() / self.pages_processed
                    
                    self.logger.info(f"📊 Progreso - Página: {current_page} | Propiedades: {len(page_properties)} | Total: {self.properties_found} | Tiempo: {avg_time_per_page:.1f}s/página")
                    
                    # Verificar si hay paginación
                    if current_page == 1 and has_pagination:
                        has_pagination = self.detect_pagination(sb)
                        if not has_pagination:
                            self.logger.info("ℹ️  URL sin paginación detectada - procesando solo esta página")
                            break
                    
                    # Pausa entre páginas (anti-detección)
                    time.sleep(random.uniform(2, 4))
                    current_page += 1
                    
                except KeyboardInterrupt:
                    self.logger.info("⏹️  Scraping interrumpido por usuario")
                    self.save_checkpoint(current_page - 1)
                    break
                    
                except Exception as e:
                    consecutive_failures += 1
                    self.errors_count += 1
                    self.logger.error(f"❌ Error en página {current_page}: {e}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.error("❌ Demasiados errores consecutivos. Deteniendo.")
                        break
                    
                    time.sleep(5)
                    current_page += 1
        
        return self.pages_processed, self.properties_found

    def save_results(self, ciudad: str, operacion: str, producto: str) -> str:
        """Guardar resultados en formato CSV en la ruta especificada"""
        if not self.properties_data:
            self.logger.warning("⚠️  No hay datos para guardar")
            return None

        if self.output_path:
            csv_path = Path(self.output_path)
        else:
            csv_path = self.run_dir / self.file_name

        csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if self.properties_data:
                fieldnames = self.properties_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.properties_data)

        self.logger.info(f"💾 Resultados guardados en: {csv_path}")

        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            self.logger.info("🗑️  Checkpoint limpiado")

        return str(csv_path)
    
    def run(self) -> Dict:
        """Ejecutar scraping completo y retornar resultados"""
        self.logger.info(f"🚀 Iniciando scraping profesional de {self.site_name}")
        self.logger.info("="*70)
        
        try:
            # Ejecutar scraping
            pages_processed, properties_found = self.scrape_pages()
            
            # Guardar resultados
            csv_path = self.save_results(self.ciudad, self.operacion, self.producto)
            
            # Calcular estadísticas finales
            total_time = datetime.now() - self.start_time
            avg_time_per_page = total_time.total_seconds() / max(pages_processed, 1)
            success_rate = ((pages_processed - self.errors_count) / max(pages_processed, 1)) * 100
            
            results = {
                'success': True,
                'pages_processed': pages_processed,
                'properties_found': properties_found,
                'errors_count': self.errors_count,
                'total_time_seconds': total_time.total_seconds(),
                'avg_time_per_page': avg_time_per_page,
                'success_rate': success_rate,
                'csv_file': csv_path,
                'target_url': self.target_url
            }
            
            # Log final
            self.logger.info("="*70)
            self.logger.info("🎉 SCRAPING COMPLETADO EXITOSAMENTE")
            self.logger.info(f"📊 Páginas procesadas: {pages_processed}")
            self.logger.info(f"🏠 Propiedades encontradas: {properties_found}")
            self.logger.info(f"❌ Errores: {self.errors_count}")
            self.logger.info(f"⏱️  Tiempo total: {total_time}")
            self.logger.info(f"⚡ Promedio por página: {avg_time_per_page:.1f}s")
            self.logger.info(f"✅ Tasa de éxito: {success_rate:.1f}%")
            self.logger.info("="*70)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error fatal en scraping: {e}")
            return {
                'success': False,
                'error': str(e),
                'pages_processed': self.pages_processed,
                'properties_found': self.properties_found
            }

def main():
    """Función principal con argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Casas y Terrenos Professional Scraper')
    parser.add_argument('--url', type=str,
                       help='URL única a procesar')
    parser.add_argument('--urls-file', type=str,
                       help='Archivo CSV con URLs a procesar')
    parser.add_argument('--output', type=str,
                       help='Archivo de salida CSV')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Ejecutar en modo headless (sin GUI)')
    parser.add_argument('--pages', type=int, default=None,
                       help='Número máximo de páginas a procesar')
    parser.add_argument('--resume', type=int, default=1,
                       help='Página desde la cual resumir')
    parser.add_argument('--gui', action='store_true',
                       help='Ejecutar con GUI (opuesto a --headless)')
    parser.add_argument('--operation', type=str, default='venta',
                       choices=['venta', 'renta'],
                       help='Tipo de operación: venta, renta')
    parser.add_argument('--ciudad', type=str, default='Ciudad',
                       help='Ciudad para la estructura de salida')
    parser.add_argument('--operacion', type=str, default='Operacion',
                       help='Operación para la estructura de salida')
    parser.add_argument('--producto', type=str, default='Producto',
                       help='Producto para la estructura de salida')
    
    args = parser.parse_args()
    
    # Ajustar headless basado en argumentos
    if args.gui:
        args.headless = False
    
    if args.gui:
        args.headless = False

    urls: List[str]
    if args.url:
        urls = [args.url]
    elif args.urls_file:
        url_entries = load_urls_from_csv(args.urls_file)
        urls = [extract_url_column(row) for row in url_entries]
    else:
        urls_dir = Path(__file__).parent.parent / 'URLs'
        urls = load_urls_for_site(urls_dir, 'casas_y_terrenos')

    success = True
    for target in urls:
        scraper = CasasTerrenosProfessionalScraper(
            url=target,
            output_path=args.output,
            headless=args.headless,
            max_pages=args.pages,
            resume_from=args.resume,
            operation_type=args.operation,
            ciudad=args.ciudad,
            operacion=args.operacion,
            producto=args.producto
        )
        result = scraper.run()
        success = success and result.get('success', False)

    sys.exit(0 if success else 1)

def run_scraper(url: str = None, output_path: str = None,
                max_pages: int = None, urls_file: str = None,
                ciudad: str = 'Ciudad', operacion: str = 'Operacion',
                producto: str = 'Producto') -> List[Dict]:
    """Interface function used by orchestrator for multiple URLs."""
    if url:
        urls = [url]
    elif urls_file:
        url_entries = load_urls_from_csv(urls_file)
        urls = [extract_url_column(row) for row in url_entries]
    else:
        urls_dir = Path(__file__).parent.parent / 'URLs'
        urls = load_urls_for_site(urls_dir, 'casas_y_terrenos')

    results: List[Dict] = []
    for target in urls:
        scraper = CasasTerrenosProfessionalScraper(
            url=target,
            output_path=output_path,
            headless=True,
            max_pages=max_pages,
            resume_from=1,
            ciudad=ciudad,
            operacion=operacion,
            producto=producto
        )
        results.append(scraper.run())

    return results

if __name__ == "__main__":
    main()
