#!/usr/bin/env python3
"""
Lamudi Professional Scraper - PropertyScraper Dell710
Scraper profesional optimizado para Dell T710 con capacidades de resilencia
"""

import os
import sys
import json
import time
import csv
import logging
import pickle
import calendar
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Selenium imports
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.path_builder import build_path

class LamudiProfessionalScraper:
    """
    Scraper profesional para lamudi.com.mx con capacidades de resilencia
    Optimizado para ejecución en Dell T710 Ubuntu Server
    """
    
    def __init__(self, headless=True, max_pages=None, resume_from=None,
                 operation_type='venta', city=None, product=None):
        self.headless = headless
        self.max_pages = max_pages
        self.resume_from = resume_from or 1
        self.operation_type = operation_type  # 'venta' o 'renta'
        self.city = city or 'Ciudad'
        self.product = product or 'Producto'

        # Configuración de paths
        self.setup_paths(self.city, self.operation_type, self.product)
        
        # Configuración de logging
        self.setup_logging()
        
        # Checkpoint system
        self.checkpoint_file = self.checkpoint_dir / f"lamudi_{operation_type}_checkpoint.pkl"
        self.checkpoint_interval = 50  # Guardar cada 50 páginas
        
        # Configuración del scraper
        if operation_type == 'venta':
            self.base_url = "https://www.lamudi.com.mx/mexico-df/for-sale/"
        else:
            self.base_url = "https://www.lamudi.com.mx/mexico-df/for-rent/"
        
        self.properties_data = []
        self.property_urls = []  # Para el segundo scraper
        
        # Performance metrics
        self.start_time = None
        self.pages_processed = 0
        self.properties_found = 0
        self.errors_count = 0
        
        self.logger.info(f"🚀 Iniciando Lamudi Professional Scraper")
        self.logger.info(f"   Operation: {operation_type}")
        self.logger.info(f"   Max pages: {max_pages}")
        self.logger.info(f"   Resume from: {resume_from}")
        self.logger.info(f"   Headless: {headless}")
    
    def setup_paths(self, city: str, operation: str, product: str):
        """Configurar estructura de paths del proyecto"""
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / 'logs'
        self.checkpoint_dir = self.logs_dir / 'checkpoints'
        self.site_name = 'Lam'

        path_info = build_path(self.site_name, city or 'Ciudad', operation or 'Operacion', product or 'Producto')
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
        log_file = self.logs_dir / f"lamudi_{self.operation_type}_professional_{timestamp}.log"
        
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
        Configuración específica para sitios internacionales como Lamudi
        """
        self.logger.info("🔧 Creando driver profesional optimizado...")
        
        # Configuración específica para Dell T710 y sitios internacionales
        sb_config = {
            'uc': True,  # Usar modo undetectable para sitios más sofisticados
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
            'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale_code': 'es-MX',
            'timeout': 30,
            'chromium_arg': [
                '--no-sandbox',  # Requerido para Ubuntu Server
                '--disable-dev-shm-usage',  # Evita problemas de memoria compartida
                '--disable-gpu',  # No usar GPU en headless
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--ignore-ssl-errors',
                '--ignore-certificate-errors',
                '--allow-running-insecure-content',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
            ]
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
            'property_urls_count': len(self.property_urls),
            'timestamp': datetime.now().isoformat(),
            'operation_type': self.operation_type
        }
        
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint, f)
            self.logger.info(f"💾 Checkpoint guardado: página {page_num}")
        except Exception as e:
            self.logger.error(f"❌ Error guardando checkpoint: {e}")
    
    def extract_property_data(self, sb) -> List[Dict]:
        """
        Extraer datos de propiedades usando selectores específicos para lamudi.com.mx
        """
        properties = []
        
        try:
            # Selectores específicos para lamudi.com.mx
            property_cards = sb.find_elements("[data-testid='listing-card'], .ListingCell-row, .listing-item")
            
            self.logger.info(f"🏠 Encontrados {len(property_cards)} property cards en la página")
            
            for i, card in enumerate(property_cards):
                try:
                    # Extraer datos básicos con manejo de errores
                    property_data = {
                        'timestamp': datetime.now().isoformat(),
                        'operation_type': self.operation_type,
                        'source_page': sb.get_current_url()
                    }
                    
                    # Título/Descripción y URL
                    try:
                        title_selectors = [
                            "[data-testid='listing-card-title'] a",
                            ".ListingCell-KeyInfo-title a",
                            ".listing-title a",
                            "h3 a", "h2 a"
                        ]
                        title_element = None
                        for selector in title_selectors:
                            try:
                                title_element = card.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue
                        
                        if title_element:
                            property_data['titulo'] = title_element.text.strip()
                            property_url = title_element.get_attribute('href')
                            property_data['link'] = property_url
                            # Agregar URL para el segundo scraper
                            if property_url and property_url not in self.property_urls:
                                self.property_urls.append(property_url)
                        else:
                            property_data['titulo'] = "N/A"
                            property_data['link'] = "N/A"
                    except:
                        property_data['titulo'] = "N/A"
                        property_data['link'] = "N/A"
                    
                    # Precio
                    try:
                        price_selectors = [
                            "[data-testid='listing-card-price']",
                            ".ListingCell-KeyInfo-price",
                            ".listing-price", ".price", ".precio"
                        ]
                        price_element = None
                        for selector in price_selectors:
                            try:
                                price_element = card.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue
                        
                        property_data['precio'] = price_element.text.strip() if price_element else "N/A"
                    except:
                        property_data['precio'] = "N/A"
                    
                    # Ubicación
                    try:
                        location_selectors = [
                            "[data-testid='listing-card-location']",
                            ".ListingCell-KeyInfo-address",
                            ".listing-location", ".location", ".address"
                        ]
                        location_element = None
                        for selector in location_selectors:
                            try:
                                location_element = card.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue
                        
                        property_data['ubicacion'] = location_element.text.strip() if location_element else "N/A"
                    except:
                        property_data['ubicacion'] = "N/A"
                    
                    # Tipo de propiedad
                    try:
                        type_selectors = [
                            "[data-testid='listing-card-property-type']",
                            ".property-type", ".listing-type"
                        ]
                        type_element = None
                        for selector in type_selectors:
                            try:
                                type_element = card.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue
                        
                        property_data['tipo_propiedad'] = type_element.text.strip() if type_element else "N/A"
                    except:
                        property_data['tipo_propiedad'] = "N/A"
                    
                    # Área/Superficie
                    try:
                        area_selectors = [
                            "[data-testid='listing-card-area']",
                            ".listing-area", ".surface", ".area"
                        ]
                        area_element = None
                        for selector in area_selectors:
                            try:
                                area_element = card.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue
                        
                        property_data['area'] = area_element.text.strip() if area_element else "N/A"
                    except:
                        property_data['area'] = "N/A"
                    
                    # Habitaciones y baños
                    try:
                        features_selectors = [
                            "[data-testid='listing-card-features']",
                            ".listing-features", ".property-features"
                        ]
                        features_element = None
                        for selector in features_selectors:
                            try:
                                features_element = card.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue
                        
                        if features_element:
                            features_text = features_element.text.strip()
                            property_data['caracteristicas'] = features_text
                        else:
                            property_data['caracteristicas'] = "N/A"
                    except:
                        property_data['caracteristicas'] = "N/A"
                    
                    # Agregar solo si tiene datos válidos
                    if property_data['titulo'] != "N/A" or property_data['precio'] != "N/A":
                        properties.append(property_data)
                        
                except Exception as e:
                    self.logger.warning(f"⚠️  Error extrayendo propiedad {i+1}: {e}")
                    continue
            
            self.logger.info(f"✅ Extraídas {len(properties)} propiedades válidas")
            self.logger.info(f"🔗 URLs recolectadas para segundo scraper: {len(self.property_urls)}")
            return properties
            
        except Exception as e:
            self.logger.error(f"❌ Error en extract_property_data: {e}")
            return []
    
    def wait_and_check_blocking(self, sb, timeout=15) -> bool:
        """
        Verificar si la página está bloqueada por Cloudflare o sistemas anti-bot
        Timeout más largo para sitios internacionales
        """
        try:
            # Esperar a que carguen elementos de propiedades o verificar bloqueo
            WebDriverWait(sb.driver, timeout).until(
                lambda driver: (
                    driver.find_elements(By.CSS_SELECTOR, "[data-testid='listing-card']") or
                    driver.find_elements(By.CSS_SELECTOR, ".ListingCell-row") or
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
                "h1:contains('Checking your browser')",
                ".captcha",
                "#captcha",
                ".robot-check",
                ".security-check"
            ]
            
            for selector in blocking_selectors:
                if sb.is_element_visible(selector):
                    self.logger.warning(f"🚫 Página bloqueada - detectado: {selector}")
                    return False
            
            # Verificar si hay propiedades
            properties_found = (
                sb.find_elements("[data-testid='listing-card']") or
                sb.find_elements(".ListingCell-row") or
                sb.find_elements(".listing-item")
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
            
            while True:
                # Verificar límite de páginas
                if self.max_pages and current_page > self.max_pages:
                    self.logger.info(f"🏁 Límite de páginas alcanzado: {self.max_pages}")
                    break
                
                try:
                    # Construir URL de la página
                    if current_page == 1:
                        page_url = self.base_url
                    else:
                        page_url = f"{self.base_url}?page={current_page}"
                    
                    self.logger.info(f"📄 Procesando página {current_page}: {page_url}")
                    
                    # Navegar a la página
                    sb.open(page_url)
                    
                    # Pausa adicional para sitios internacionales
                    time.sleep(4)
                    
                    # Verificar bloqueo y esperar carga
                    if not self.wait_and_check_blocking(sb):
                        consecutive_failures += 1
                        self.errors_count += 1
                        
                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.error(f"❌ Demasiados fallos consecutivos ({consecutive_failures}). Deteniendo scraping.")
                            break
                        
                        self.logger.warning(f"⚠️  Página {current_page} falló. Intentando siguiente...")
                        current_page += 1
                        time.sleep(8)  # Pausa más larga para sitios internacionales
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
                        # Guardar URLs intermedias para el segundo scraper
                        self.save_urls_for_detailed_scraper()
                    
                    # Log de progreso
                    elapsed = datetime.now() - self.start_time
                    avg_time_per_page = elapsed.total_seconds() / self.pages_processed
                    
                    self.logger.info(f"📊 Progreso - Página: {current_page} | Propiedades: {len(page_properties)} | Total: {self.properties_found} | URLs: {len(self.property_urls)} | Tiempo: {avg_time_per_page:.1f}s/página")
                    
                    # Pausa entre páginas (anti-detección)
                    time.sleep(3)
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
                    
                    time.sleep(8)
                    current_page += 1
        
        return self.pages_processed, self.properties_found
    
    def save_urls_for_detailed_scraper(self):
        """Guardar URLs para el segundo scraper (lamudi_unico_professional)"""
        if not self.property_urls:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        urls_file = self.checkpoint_dir / f"lamudi_{self.operation_type}_urls_{timestamp}.txt"
        
        try:
            with open(urls_file, 'w', encoding='utf-8') as f:
                for url in self.property_urls:
                    f.write(f"{url}\n")
            self.logger.info(f"🔗 URLs guardadas para segundo scraper: {urls_file}")
        except Exception as e:
            self.logger.error(f"❌ Error guardando URLs: {e}")
    
    def save_results(self, city: str, operation: str, product: str) -> str:
        """Guardar resultados en formato CSV con metadata"""
        if not self.properties_data:
            self.logger.warning("⚠️  No hay datos para guardar")
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ciudad = city or 'Ciudad'
        operacion = operation or 'Operacion'
        producto = product or 'Producto'
        run_str = f"{self.run_number:02d}"

        csv_filename = self.file_name
        csv_path = self.run_dir / csv_filename

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if self.properties_data:
                fieldnames = self.properties_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.properties_data)

        # Nueva nomenclatura para archivo de URLs
        current = datetime.now()
        month_abbrev = calendar.month_abbr[current.month]
        year_short = current.strftime("%y")
        urls_filename = (
            f"LamURL_{ciudad}_{operacion}_{producto}_{month_abbrev}{year_short}_{run_str}.csv"
        )
        urls_path = self.run_dir / urls_filename
        if self.property_urls:
            with open(urls_path, 'w', encoding='utf-8') as f:
                for url in self.property_urls:
                    f.write(f"{url}\n")

        metadata = {
            'execution_info': {
                'timestamp': timestamp,
                'operation_type': self.operation_type,
                'total_pages_processed': self.pages_processed,
                'total_properties_found': self.properties_found,
                'total_urls_collected': len(self.property_urls),
                'errors_count': self.errors_count,
                'execution_time_seconds': (datetime.now() - self.start_time).total_seconds(),
                'csv_filename': csv_filename,
                'urls_filename': urls_filename,
                'log_filename': self.log_file.name
            },
            'system_info': {
                'scraper_version': '1.0.0',
                'python_version': sys.version,
                'headless_mode': self.headless,
                'max_pages_limit': self.max_pages,
                'resume_from_page': self.resume_from
            },
            'next_steps': {
                'second_phase_scraper': 'lamudi_unico_professional.py',
                'urls_file_for_second_phase': str(urls_path)
            }
        }

        metadata_path = self.run_dir / f"metadata_{timestamp}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"💾 Resultados guardados:")
        self.logger.info(f"   📄 CSV: {csv_path}")
        self.logger.info(f"   🔗 URLs: {urls_path}")
        self.logger.info(f"   📋 Metadata: {metadata_path}")

        # Limpiar checkpoint al finalizar exitosamente
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            self.logger.info("🗑️  Checkpoint limpiado")

        return str(csv_path)
    
    def run(self) -> Dict:
        """Ejecutar scraping completo y retornar resultados"""
        self.logger.info("🚀 Iniciando scraping profesional de lamudi.com.mx")
        self.logger.info("="*70)
        
        try:
            # Ejecutar scraping
            pages_processed, properties_found = self.scrape_pages()
            
            # Guardar resultados
            csv_path = self.save_results(self.city, self.operation_type, self.product)
            
            # Calcular estadísticas finales
            total_time = datetime.now() - self.start_time
            avg_time_per_page = total_time.total_seconds() / max(pages_processed, 1)
            success_rate = ((pages_processed - self.errors_count) / max(pages_processed, 1)) * 100
            
            results = {
                'success': True,
                'pages_processed': pages_processed,
                'properties_found': properties_found,
                'urls_collected': len(self.property_urls),
                'errors_count': self.errors_count,
                'total_time_seconds': total_time.total_seconds(),
                'avg_time_per_page': avg_time_per_page,
                'success_rate': success_rate,
                'csv_file': csv_path,
                'operation_type': self.operation_type
            }
            
            # Log final
            self.logger.info("="*70)
            self.logger.info("🎉 SCRAPING COMPLETADO EXITOSAMENTE")
            self.logger.info(f"📊 Páginas procesadas: {pages_processed}")
            self.logger.info(f"🏠 Propiedades encontradas: {properties_found}")
            self.logger.info(f"🔗 URLs recolectadas: {len(self.property_urls)}")
            self.logger.info(f"❌ Errores: {self.errors_count}")
            self.logger.info(f"⏱️  Tiempo total: {total_time}")
            self.logger.info(f"⚡ Promedio por página: {avg_time_per_page:.1f}s")
            self.logger.info(f"✅ Tasa de éxito: {success_rate:.1f}%")
            self.logger.info("="*70)
            self.logger.info("🔄 Siguiente fase: Ejecutar lamudi_unico_professional.py con las URLs recolectadas")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error fatal en scraping: {e}")
            return {
                'success': False,
                'error': str(e),
                'pages_processed': self.pages_processed,
                'properties_found': self.properties_found
            }

def run_scraper(url: str, output_path: str, max_pages: int = None) -> Dict:
    """Interface function for the orchestrator.

    Args:
        url: Listing URL to scrape.
        output_path: Path where results should be stored. Used to infer
            city/operation/product when building directories.
        max_pages: Optional limit of pages to scrape.

    Returns:
        Dictionary returned by :meth:`LamudiProfessionalScraper.run`.
    """

    city = product = None
    operation_type = 'venta'

    if output_path:
        out = Path(output_path)
        city = out.parent.parent.name if out.parent.parent.name else None
        operation_code = out.parent.name.lower()
        product = out.stem.split('_')[0]
        op_map = {'ven': 'venta', 'ren': 'renta', 'vnd': 'venta-d', 'vnr': 'venta-r'}
        operation_type = op_map.get(operation_code, operation_code)

    scraper = LamudiProfessionalScraper(
        headless=True,
        max_pages=max_pages,
        resume_from=1,
        operation_type=operation_type,
        city=city,
        product=product,
    )

    if url:
        scraper.base_url = url

    return scraper.run()

def main():
    """Función principal con argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Lamudi Professional Scraper')
    parser.add_argument('--headless', action='store_true', default=True, 
                       help='Ejecutar en modo headless (sin GUI)')
    parser.add_argument('--pages', type=int, default=None, 
                       help='Número máximo de páginas a procesar')
    parser.add_argument('--resume', type=int, default=1,
                       help='Página desde la cual resumir')
    parser.add_argument('--operation', choices=['venta', 'renta'], default='venta',
                       help='Tipo de operación: venta o renta')
    parser.add_argument('--gui', action='store_true',
                       help='Ejecutar con GUI (opuesto a --headless)')
    parser.add_argument('--city', type=str, default=None,
                       help='Ciudad para la estructura de salida')
    parser.add_argument('--product', type=str, default=None,
                       help='Producto para la estructura de salida')
    
    args = parser.parse_args()
    
    # Ajustar headless basado en argumentos
    if args.gui:
        args.headless = False
    
    # Crear y ejecutar scraper
    scraper = LamudiProfessionalScraper(
        headless=args.headless,
        max_pages=args.pages,
        resume_from=args.resume,
        operation_type=args.operation,
        city=args.city,
        product=args.product
    )
    
    results = scraper.run()
    
    # Retornar código de salida apropiado
    sys.exit(0 if results['success'] else 1)

if __name__ == "__main__":
    main()
