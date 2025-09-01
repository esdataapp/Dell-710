#!/usr/bin/env python3
"""
Inmuebles24 Professional Scraper - PropertyScraper Dell710
Scraper profesional optimizado para Dell T710 con capacidades de resilencia
Adaptado para trabajar con ``URLs/inm24_urls.csv``
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

# Selenium imports
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Importar el nuevo sistema de registro (opcional para test independiente)
sys.path.append(str(Path(__file__).parent.parent))
try:
    from enhanced_scraps_registry import EnhancedScrapsRegistry
    registry_available = True
except ImportError:
    print("Warning: EnhancedScrapsRegistry no disponible - ejecutando en modo independiente")
    registry_available = False

class Inmuebles24ProfessionalScraper:
    """
    Scraper profesional para inmuebles24.com con capacidades de resilencia
    Optimizado para ejecución en Dell T710 Ubuntu Server
    Adaptado para trabajar con URLs del registro CSV
    """
    
    def __init__(self, url=None, output_path=None, headless=True, max_pages=None,
                 resume_from=None, operation_type='venta', city=None, product=None):
        # Parámetros principales
        self.target_url = url
        self.output_path = output_path
        self.headless = headless
        self.max_pages = max_pages
        self.resume_from = resume_from or 1
        self.operation_type = operation_type  # venta, renta, venta-d, venta-r
        self.city = city or 'unknown'
        self.product = product or 'general'
        
        # Configuración de paths
        self.setup_paths()
        
        # Configuración de logging
        self.setup_logging()
        
        # Checkpoint system
        self.checkpoint_file = self.checkpoint_dir / f"inmuebles24_checkpoint.pkl"
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
        
        self.logger.info(f"🚀 Iniciando Inmuebles24 Professional Scraper")
        self.logger.info(f"   URL objetivo: {url}")
        self.logger.info(f"   Archivo salida: {output_path}")
        self.logger.info(f"   Max pages: {max_pages}")
        self.logger.info(f"   Resume from: {resume_from}")
        self.logger.info(f"   Headless: {headless}")
        self.logger.info(f"   City: {self.city}")
        self.logger.info(f"   Product: {self.product}")
    
    def setup_paths(self):
        """Configurar estructura de paths del proyecto"""
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / 'logs'
        self.checkpoint_dir = self.project_root / 'logs' / 'checkpoints'
        
        # Mapear operation_type a carpeta
        operation_mapping = {
            'renta': 'ren',
            'venta': 'ven', 
            'venta-d': 'ven-d',
            'venta-r': 'ven-r'
        }
        self.operation_folder = operation_mapping.get(self.operation_type, 'ven')
        
        # Directorio de datos con nueva estructura
        self.data_dir = self.project_root / 'data' / 'inm24'
        
        # Crear directorios si no existen
        for directory in [self.logs_dir, self.checkpoint_dir, self.data_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Configurar sistema de logging profesional"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.logs_dir / f"inmuebles24_professional_{timestamp}.log"
        
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
        Crear driver optimizado para Ubuntu Server sin interfaz gráfica
        """
        self.logger.info("🔧 Creando driver profesional optimizado...")
        
        # Configuración optimizada para Ubuntu Server headless
        sb_config = {
            'headless': True,  # Siempre headless para Ubuntu Server
            'uc': True,  # Usar undetected chrome
            'incognito': True,  # Modo incógnito
            'disable_csp': True,  # Deshabilitar Content Security Policy
            'disable_ws': True,  # Deshabilitar web security
            'block_images': False,  # Permitir imágenes para mejor detección
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
                '--window-size=1920,1080'
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
            'operation_type': self.target_url
        }
        
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint, f)
            self.logger.info(f"💾 Checkpoint guardado: página {page_num}")
        except Exception as e:
            self.logger.error(f"❌ Error guardando checkpoint: {e}")
    
    def extract_property_data(self, sb) -> List[Dict]:
        """
        Extraer datos de propiedades usando selectores probados
        Basado en el método que logró extraer 2541 propiedades exitosamente
        """
        properties = []
        
        try:
            # Selectores probados y optimizados
            property_cards = sb.find_elements("div[data-qa='posting PROPERTY']")
            
            self.logger.info(f"🏠 Encontrados {len(property_cards)} property cards en la página")
            
            for i, card in enumerate(property_cards):
                try:
                    # Extraer datos básicos con manejo de errores
                    property_data = {
                        'timestamp': datetime.now().isoformat(),
                        'source_url': self.target_url,
                        'source_page': sb.get_current_url(),
                        'fuente': 'Inmuebles24'
                    }
                    
                    # Título/Descripción
                    try:
                        title_element = card.find_element(By.CSS_SELECTOR, "h2 a, h3 a, .posting-title a")
                        property_data['titulo'] = title_element.text.strip()
                        property_data['link'] = title_element.get_attribute('href')
                    except:
                        property_data['titulo'] = "N/A"
                        property_data['link'] = "N/A"
                    
                    # Precio
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, ".price, .posting-price, [data-qa='POSTING_CARD_PRICE']")
                        property_data['precio'] = price_element.text.strip()
                    except:
                        property_data['precio'] = "N/A"
                    
                    # Ubicación
                    try:
                        location_element = card.find_element(By.CSS_SELECTOR, ".posting-location, .location, [data-qa='POSTING_CARD_LOCATION']")
                        property_data['ubicacion'] = location_element.text.strip()
                    except:
                        property_data['ubicacion'] = "N/A"
                    
                    # Características (m², habitaciones, baños)
                    try:
                        features = card.find_elements(By.CSS_SELECTOR, ".posting-features li, .features li, .characteristic")
                        features_text = [f.text.strip() for f in features if f.text.strip()]
                        property_data['caracteristicas'] = " | ".join(features_text)
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
        Verificar si la página está bloqueada por Cloudflare
        Retorna True si la página está disponible, False si está bloqueada
        """
        try:
            # Esperar a que carguen elementos de propiedades o verificar bloqueo
            WebDriverWait(sb.driver, timeout).until(
                lambda driver: (
                    driver.find_elements(By.CSS_SELECTOR, "div[data-qa='posting PROPERTY']") or
                    driver.find_elements(By.CSS_SELECTOR, ".posting-card") or
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
                sb.find_elements("div[data-qa='posting PROPERTY']") or
                sb.find_elements(".posting-card") or
                sb.find_elements(".property-card")
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
                        if 'pagina-' in self.target_url:
                            page_url = self.target_url.replace('pagina-1', f'pagina-{current_page}')
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
    
    def detect_pagination(self, sb) -> bool:
        """Detectar si la página tiene paginación"""
        try:
            # Buscar elementos de paginación
            pagination_selectors = [
                '.pagination',
                '.andes-pagination',
                '.pager',
                'a[href*="pagina"]',
                'a[href*="page"]'
            ]
            
            for selector in pagination_selectors:
                if sb.find_elements(selector):
                    self.logger.info(f"✅ Paginación detectada con selector: {selector}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error detectando paginación: {e}")
            return False
    
    def get_script_number(self, month_abbrev, year_short):
        """Detectar automáticamente si es la primera (1) o segunda (2) ejecución del mes"""
        month_year_folder = f"{month_abbrev}{year_short}"
        execution_dir_1 = self.data_dir / self.operation_folder / month_year_folder / "1"
        
        # Si existe la carpeta 1 y tiene archivos CSV, entonces esta es la segunda ejecución
        if execution_dir_1.exists():
            csv_files = list(execution_dir_1.glob("*URL_*.csv"))
            if csv_files:
                return "2"  # Segunda ejecución del mes
        
        return "1"  # Primera ejecución del mes

    def save_results(self) -> str:
        """Guardar resultados en formato CSV en la ruta especificada"""
        if not self.properties_data:
            self.logger.warning("⚠️  No hay datos para guardar")
            return None
        
        # Usar la ruta proporcionada o crear una por defecto
        if self.output_path:
            urls_path = Path(self.output_path)
        else:
            current_date = datetime.now()
            month_abbrev = {
                1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun',
                7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'
            }[current_date.month]
            year_short = str(current_date.year)[-2:]
            script_number = self.get_script_number(month_abbrev, year_short)
            city_code = self.city.replace(' ', '_')
            op_code = self.operation_type.replace('-', '_')
            product_code = self.product.replace(' ', '_')
            filename = f"I24URL_{city_code}_{op_code}_{product_code}_{month_abbrev}{year_short}_{script_number}.csv"

            month_year_folder = f"{month_abbrev}{year_short}"
            script_folder = script_number
            execution_dir = self.data_dir / self.operation_folder / month_year_folder / script_folder
            execution_dir.mkdir(parents=True, exist_ok=True)
            urls_path = execution_dir / filename

        urls_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Guardar CSV
        with open(urls_path, 'w', newline='', encoding='utf-8') as csvfile:
            if self.properties_data:
                fieldnames = self.properties_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.properties_data)

        self.logger.info(f"💾 Resultados guardados en: {urls_path}")
        
        # Limpiar checkpoint al finalizar exitosamente
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            self.logger.info("🗑️  Checkpoint limpiado")
        
        return str(urls_path)
    
    def run(self) -> Dict:
        """Ejecutar scraping completo y retornar resultados"""
        self.logger.info("🚀 Iniciando scraping profesional de inmuebles24.com")
        self.logger.info("="*70)
        
        try:
            # Ejecutar scraping
            pages_processed, properties_found = self.scrape_pages()
            
            # Guardar resultados
            urls_path = self.save_results()
            
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
                'urls_file': urls_path,
                'operation_type': self.operation_type,
                'city': self.city,
                'product': self.product
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
    parser = argparse.ArgumentParser(description='Inmuebles24 Professional Scraper')
    parser.add_argument('--url', type=str, required=True, 
                       help='URL objetivo para hacer scraping')
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
                       choices=['venta', 'renta', 'venta-d', 'venta-r'],
                       help='Tipo de operación: venta, renta, venta-d, venta-r')
    
    args = parser.parse_args()
    
    # Ajustar headless basado en argumentos
    # Por defecto es headless para Ubuntu Server, GUI solo si se especifica --gui
    if args.gui:
        args.headless = False
    else:
        args.headless = True
    
    # Crear y ejecutar scraper
    scraper = Inmuebles24ProfessionalScraper(
        url=args.url,
        output_path=args.output,
        headless=args.headless,
        max_pages=args.pages,
        resume_from=args.resume,
        operation_type=args.operation
    )
    
    results = scraper.run()
    
    # Retornar código de salida apropiado
    sys.exit(0 if results['success'] else 1)

def run_scraper(url: str, output_path: str, max_pages: int = None) -> Dict:
    """
    Función de interfaz para usar desde el orquestador
    """
    scraper = Inmuebles24ProfessionalScraper(
        url=url,
        output_path=output_path,
        headless=True,
        max_pages=max_pages,
        resume_from=1
    )
    
    return scraper.run()

if __name__ == "__main__":
    main()
