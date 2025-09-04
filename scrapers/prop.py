#!/usr/bin/env python3
"""
Scraper profesional para propiedades.com optimizado para el servidor Dell T710.
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

from utils.url_utils import extract_url_column, load_urls_from_csv
from utils.path_builder import build_path

# Selenium imports
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PropiedadesProfessionalScraper:
    """
    Scraper profesional para propiedades.com con capacidades de resilencia
    Optimizado para ejecución en Dell T710 Ubuntu Server
    """
    
    def __init__(self, output_path=None, headless=True, max_pages=None,
                 resume_from=None, operation_type='venta'):
        self.output_path = output_path
        self.headless = headless
        self.max_pages = max_pages
        self.resume_from = resume_from or 1
        self.operation_type = operation_type  # 'venta' o 'renta'
        
        # Configuración de paths
        self.setup_paths()
        
        # Configuración de logging
        self.setup_logging()
        
        # Checkpoint system
        self.checkpoint_file = self.checkpoint_dir / f"propiedades_{operation_type}_checkpoint.pkl"
        self.checkpoint_interval = 50  # Guardar cada 50 páginas
        
        # Configuración del scraper
        if operation_type == 'venta':
            self.base_url = "https://propiedades.com/df/departamentos"
        else:
            self.base_url = "https://propiedades.com/df/departamentos-en-renta"
        
        self.properties_data = []
        
        # Performance metrics
        self.start_time = None
        self.pages_processed = 0
        self.properties_found = 0
        self.errors_count = 0
        
        self.logger.info(f"🚀 Iniciando Propiedades Professional Scraper")
        self.logger.info(f"   Archivo salida: {output_path}")
        self.logger.info(f"   Operation: {operation_type}")
        self.logger.info(f"   Max pages: {max_pages}")
        self.logger.info(f"   Resume from: {resume_from}")
        self.logger.info(f"   Headless: {headless}")
    
    def setup_paths(self):
        """Configurar estructura de paths del proyecto"""
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / 'logs'
        self.checkpoint_dir = self.logs_dir / 'checkpoints'

        path_info = build_path('Prop', 'Ciudad', self.operation_type, 'Producto')
        self.month_year = path_info.month_year
        self.run_number = int(path_info.run_number)
        self.data_dir = path_info.directory
        self.file_name = path_info.file_name

        for directory in [self.logs_dir, self.checkpoint_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Configurar sistema de logging profesional"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.logs_dir / f"propiedades_{self.operation_type}_professional_{timestamp}.log"
        
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
        Basado en el método híbrido que logró 98% de éxito
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
        Extraer datos de propiedades usando selectores específicos para propiedades.com
        """
        properties = []
        
        try:
            # Selectores específicos para propiedades.com
            property_cards = sb.find_elements(".ad, .property-card, .listing-card")
            
            self.logger.info(f"🏠 Encontrados {len(property_cards)} property cards en la página")
            
            for i, card in enumerate(property_cards):
                try:
                    # Extraer datos básicos con manejo de errores
                    property_data = {
                        'timestamp': datetime.now().isoformat(),
                        'operation_type': self.operation_type,
                        'source_page': sb.get_current_url()
                    }
                    
                    # Título/Descripción
                    try:
                        title_selectors = [
                            ".ad-title a", ".property-title a", ".listing-title a",
                            "h2 a", "h3 a", ".title a"
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
                            property_data['link'] = title_element.get_attribute('href')
                        else:
                            property_data['titulo'] = "N/A"
                            property_data['link'] = "N/A"
                    except:
                        property_data['titulo'] = "N/A"
                        property_data['link'] = "N/A"
                    
                    # Precio
                    try:
                        price_selectors = [
                            ".ad-price", ".property-price", ".listing-price", 
                            ".price", ".precio", "[data-qa='price']"
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
                            ".ad-location", ".property-location", ".listing-location",
                            ".location", ".ubicacion", "[data-qa='location']"
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
                    
                    # Características (m², habitaciones, baños)
                    try:
                        features_selectors = [
                            ".ad-features li", ".property-features li", ".listing-features li",
                            ".features li", ".characteristic", ".amenities li"
                        ]
                        features = []
                        for selector in features_selectors:
                            try:
                                feature_elements = card.find_elements(By.CSS_SELECTOR, selector)
                                features.extend([f.text.strip() for f in feature_elements if f.text.strip()])
                                if features:  # Si encontramos características, usar estas
                                    break
                            except:
                                continue
                        
                        property_data['caracteristicas'] = " | ".join(features) if features else "N/A"
                    except:
                        property_data['caracteristicas'] = "N/A"
                    
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
        Verificar si la página está bloqueada por Cloudflare o sistemas anti-bot
        Retorna True si la página está disponible, False si está bloqueada
        """
        try:
            # Esperar a que carguen elementos de propiedades o verificar bloqueo
            WebDriverWait(sb.driver, timeout).until(
                lambda driver: (
                    driver.find_elements(By.CSS_SELECTOR, ".ad") or
                    driver.find_elements(By.CSS_SELECTOR, ".property-card") or
                    driver.find_elements(By.CSS_SELECTOR, ".listing-card") or
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
                "#captcha"
            ]
            
            for selector in blocking_selectors:
                if sb.is_element_visible(selector):
                    self.logger.warning(f"🚫 Página bloqueada - detectado: {selector}")
                    return False
            
            # Verificar si hay propiedades
            properties_found = (
                sb.find_elements(".ad") or
                sb.find_elements(".property-card") or
                sb.find_elements(".listing-card")
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
                        page_url = f"{self.base_url}?pagina={current_page}"
                    
                    self.logger.info(f"📄 Procesando página {current_page}: {page_url}")
                    
                    # Navegar a la página
                    sb.open(page_url)
                    
                    # Pausa adicional para asegurar carga completa
                    time.sleep(3)
                    
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
                    
                    # Pausa entre páginas (anti-detección)
                    time.sleep(2)
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
    
    def save_results(self) -> str:
        """Guardar resultados en formato CSV con nueva nomenclatura"""
        if not self.properties_data:
            self.logger.warning("⚠️  No hay datos para guardar")
            return None

        # Generar timestamp para archivos
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Archivo CSV principal con nueva nomenclatura o ruta proporcionada
        if self.output_path:
            csv_path = Path(self.output_path)
            csv_filename = csv_path.name
        else:
            csv_filename = self.file_name
            csv_path = self.data_dir / csv_filename

        # Asegurar que el directorio exista
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            if self.properties_data:
                fieldnames = self.properties_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.properties_data)
        
        # Metadata
        metadata = {
            'execution_info': {
                'timestamp': timestamp,
                'operation_type': self.operation_type,
                'total_pages_processed': self.pages_processed,
                'total_properties_found': self.properties_found,
                'errors_count': self.errors_count,
                'execution_time_seconds': (datetime.now() - self.start_time).total_seconds(),
                'csv_filename': csv_filename,
                'log_filename': self.log_file.name
            },
            'system_info': {
                'scraper_version': '1.0.0',
                'python_version': sys.version,
                'headless_mode': self.headless,
                'max_pages_limit': self.max_pages,
                'resume_from_page': self.resume_from
            }
        }
        
        metadata_path = self.data_dir / f"metadata_{timestamp}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"💾 Resultados guardados:")
        self.logger.info(f"   📄 CSV: {csv_path}")
        self.logger.info(f"   📋 Metadata: {metadata_path}")
        
        # Limpiar checkpoint al finalizar exitosamente
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            self.logger.info("🗑️  Checkpoint limpiado")
        
        return str(csv_path)
    
    def run(self) -> Dict:
        """Ejecutar scraping completo y retornar resultados"""
        self.logger.info("🚀 Iniciando scraping profesional de propiedades.com")
        self.logger.info("="*70)
        
        try:
            # Ejecutar scraping
            pages_processed, properties_found = self.scrape_pages()
            
            # Guardar resultados
            csv_path = self.save_results()
            
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
                'operation_type': self.operation_type
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
    parser = argparse.ArgumentParser(description='Propiedades Professional Scraper')
    parser.add_argument('--url', type=str,
                       help='URL única a procesar')
    parser.add_argument('--urls-file', type=str,
                       help='Archivo CSV con URLs a procesar')
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

    args = parser.parse_args()

    if args.gui:
        args.headless = False

    if args.url:
        urls = [args.url]
    else:
        default_csv = Path(__file__).parent.parent / 'URLs' / 'prop_urls.csv'
        csv_path = args.urls_file or default_csv
        url_entries = load_urls_from_csv(csv_path)
        urls = [extract_url_column(row) for row in url_entries]

    success = True
    for target in urls:
        scraper = PropiedadesProfessionalScraper(
            headless=args.headless,
            max_pages=args.pages,
            resume_from=args.resume,
            operation_type=args.operation
        )
        scraper.base_url = target
        result = scraper.run()
        success = success and result.get('success', False)

    sys.exit(0 if success else 1)


def run_scraper(url: str = None, output_path: str | None = None,
                max_pages: int = None, urls_file: str = None) -> List[Dict]:
    """Interface function for orchestrator to handle multiple URLs.

    Parameters
    ----------
    url : str | None
        URL única a procesar.
    output_path : str | None
        Ruta donde se almacenará el CSV resultante.
    max_pages : int | None
        Número máximo de páginas a procesar.
    urls_file : str | None
        Archivo CSV con URLs a procesar.
    """
    if url:
        urls = [url]
    else:
        default_csv = Path(__file__).parent.parent / 'URLs' / 'prop_urls.csv'
        csv_path = urls_file or default_csv
        url_entries = load_urls_from_csv(csv_path)
        urls = [extract_url_column(row) for row in url_entries]

    results: List[Dict] = []
    for target in urls:
        scraper = PropiedadesProfessionalScraper(
            output_path=output_path,
            headless=True,
            max_pages=max_pages,
            resume_from=1,
            operation_type='venta'
        )
        scraper.base_url = target
        results.append(scraper.run())

    return results

if __name__ == "__main__":
    main()
