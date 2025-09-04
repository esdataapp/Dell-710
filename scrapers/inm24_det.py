#!/usr/bin/env python3
"""
Inmuebles24 Unico Professional Scraper - PropertyScraper Dell710
Scraper profesional para detalles de propiedades individuales de Inmuebles24
Optimizado para Dell T710 con capacidades de resilencia
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
from utils.path_builder import build_path

# Selenium imports
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class Inmuebles24UnicoProfessionalScraper:
    """
    Scraper profesional para detalles de propiedades individuales de inmuebles24.com
    Segunda fase del proceso de scraping - procesa URLs individuales
    """
    
    def __init__(self, urls_file=None, headless=True, max_properties=None, resume_from=None, operation_type='venta'):
        self.urls_file = urls_file
        self.headless = headless
        self.max_properties = max_properties
        self.resume_from = resume_from or 0
        self.operation_type = operation_type
        
        # Configuración de paths
        self.setup_paths()
        
        # Configuración de logging
        self.setup_logging()
        
        # Checkpoint system
        self.checkpoint_file = self.checkpoint_dir / f"inmuebles24_unico_{operation_type}_checkpoint.pkl"
        self.checkpoint_interval = 25  # Guardar cada 25 propiedades procesadas
        
        # Cargar URLs
        self.property_urls = self.load_urls()
        self.properties_data = []
        
        # Performance metrics
        self.start_time = None
        self.properties_processed = 0
        self.successful_extractions = 0
        self.errors_count = 0
        
        self.logger.info(f"🚀 Iniciando Inmuebles24 Unico Professional Scraper")
        self.logger.info(f"   URLs file: {urls_file}")
        self.logger.info(f"   Total URLs: {len(self.property_urls)}")
        self.logger.info(f"   Operation: {operation_type}")
        self.logger.info(f"   Max properties: {max_properties}")
        self.logger.info(f"   Resume from: {resume_from}")
        self.logger.info(f"   Headless: {headless}")
    
    def setup_paths(self):
        """Configurar estructura de paths del proyecto"""
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / 'logs'
        self.checkpoint_dir = self.logs_dir / 'checkpoints'

        path_info = build_path('Inm24', 'Ciudad', self.operation_type, 'Detalle')
        self.month_year = path_info.month_year
        self.run_number = int(path_info.run_number)
        self.data_dir = path_info.directory

        for directory in [self.logs_dir, self.checkpoint_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Configurar sistema de logging profesional"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.logs_dir / f"inmuebles24_unico_{self.operation_type}_professional_{timestamp}.log"
        
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
    
    def load_urls(self) -> List[str]:
        """Cargar URLs desde archivo o desde el CSV más reciente de inmuebles24_professional"""
        urls = []
        
        if not self.urls_file:
            # Buscar el CSV más reciente del primer script (I24_URLs_*.csv)
            pattern = f"I24_URLs_*.csv"
            csv_files = list(self.data_dir.glob(f"**/{pattern}"))
            if csv_files:
                latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
                self.logger.info(f"📂 Usando CSV más reciente: {latest_csv}")
                
                # Extraer URLs del CSV
                try:
                    import pandas as pd
                    df = pd.read_csv(latest_csv)
                    if 'link' in df.columns:
                        urls = df['link'].dropna().tolist()
                        self.logger.info(f"📂 Extraídas {len(urls)} URLs del CSV")
                    else:
                        self.logger.error("❌ Columna 'link' no encontrada en el CSV")
                except Exception as e:
                    self.logger.error(f"❌ Error leyendo CSV: {e}")
            else:
                # Buscar archivo de URLs de texto con nueva nomenclatura
                pattern = f"I24_URLs_*.txt"
                url_files = list(self.data_dir.glob(f"**/{pattern}"))
                if url_files:
                    self.urls_file = max(url_files, key=lambda x: x.stat().st_mtime)
                    self.logger.info(f"📂 Usando archivo de URLs: {self.urls_file}")
                else:
                    self.logger.error("❌ No se encontró archivo de URLs ni CSV")
                    return []
        
        # Si tenemos archivo de URLs específico, usarlo
        if self.urls_file and not urls:
            try:
                with open(self.urls_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                self.logger.info(f"📂 Cargadas {len(urls)} URLs desde {self.urls_file}")
            except Exception as e:
                self.logger.error(f"❌ Error cargando URLs: {e}")
        
        return urls
    
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
            'block_images': False  # Permitir imágenes para mejor detección
        }
        
        return sb_config
    
    def load_checkpoint(self) -> Optional[Dict]:
        """Cargar checkpoint anterior si existe"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                self.logger.info(f"📂 Checkpoint cargado: propiedad {checkpoint.get('last_index', 0)}")
                return checkpoint
            except Exception as e:
                self.logger.warning(f"⚠️  Error cargando checkpoint: {e}")
        return None
    
    def save_checkpoint(self, index: int):
        """Guardar checkpoint del progreso actual"""
        checkpoint = {
            'last_index': index,
            'properties_processed': self.properties_processed,
            'successful_extractions': self.successful_extractions,
            'timestamp': datetime.now().isoformat(),
            'operation_type': self.operation_type
        }
        
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint, f)
            self.logger.info(f"💾 Checkpoint guardado: índice {index}")
        except Exception as e:
            self.logger.error(f"❌ Error guardando checkpoint: {e}")
    
    def extract_detailed_property_data(self, sb, url: str) -> Optional[Dict]:
        """
        Extraer datos detallados de una propiedad individual de inmuebles24
        Maneja tanto propiedades regulares como patrocinadas
        """
        try:
            # Verificar si es una propiedad patrocinada
            is_sponsored = self.is_sponsored_property(sb, url)
            
            # Datos básicos
            property_data = {
                'timestamp': datetime.now().isoformat(),
                'operation_type': self.operation_type,
                'property_url': url,
                'is_sponsored': is_sponsored
            }
            
            if is_sponsored:
                self.logger.info(f"🔸 Detectada propiedad patrocinada: {url}")
                return self.extract_sponsored_property_data(sb, property_data)
            else:
                self.logger.info(f"🔹 Procesando propiedad regular: {url}")
                return self.extract_regular_property_data(sb, property_data)
                
        except Exception as e:
            self.logger.error(f"❌ Error extrayendo datos detallados: {e}")
            return None
    
    def is_sponsored_property(self, sb, url: str) -> bool:
        """
        Detectar si una propiedad es patrocinada basándose en indicadores comunes
        """
        try:
            # Indicadores de propiedades patrocinadas
            sponsored_indicators = [
                ".sponsored",
                ".patrocinado", 
                "[data-sponsored='true']",
                ".premium",
                ".destacado",
                ".featured"
            ]
            
            for selector in sponsored_indicators:
                if sb.is_element_present(selector):
                    return True
            
            # Verificar en el HTML si contiene palabras clave
            page_source = sb.get_page_source().lower()
            sponsored_keywords = ['patrocinado', 'sponsored', 'premium', 'destacado', 'featured']
            
            for keyword in sponsored_keywords:
                if keyword in page_source:
                    return True
                    
            # Verificar estructura diferente (propiedades patrocinadas suelen tener menos elementos)
            regular_elements = [
                "h1.title-property",
                ".property-features",
                ".property-description"
            ]
            
            missing_elements = 0
            for selector in regular_elements:
                if not sb.is_element_present(selector):
                    missing_elements += 1
            
            # Si faltan más de la mitad de elementos regulares, probablemente es patrocinada
            if missing_elements >= len(regular_elements) / 2:
                return True
                
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️  Error detectando propiedad patrocinada: {e}")
            return False
    
    def extract_sponsored_property_data(self, sb, url: str) -> Optional[Dict]:
        """
        Extraer datos de propiedades patrocinadas con selectores alternativos
        """
        try:
            # Inicializar diccionario de datos de propiedad
            property_data = {
                'url': url,
                'titulo': "N/A",
                'precio': "N/A",
                'ubicacion': "N/A",
                'tipo_propiedad': "N/A",
                'superficie_total': "N/A",
                'superficie_cubierta': "N/A",
                'habitaciones': "N/A",
                'banos': "N/A",
                'cocheras': "N/A",
                'caracteristicas': "N/A",
                'descripcion': "N/A",
                'contacto': "N/A"
            }
            
            # Título para propiedades patrocinadas
            try:
                sponsored_title_selectors = [
                    "h1",
                    "h2", 
                    ".title",
                    ".name",
                    "[class*='title']",
                    "[class*='name']"
                ]
                title = self.get_text_by_selectors(sb, sponsored_title_selectors)
                property_data['titulo'] = title
            except:
                property_data['titulo'] = "Propiedad Patrocinada - Título no disponible"
            
            # Precio para propiedades patrocinadas
            try:
                sponsored_price_selectors = [
                    "[class*='price']",
                    "[class*='precio']",
                    ".amount",
                    ".cost"
                ]
                price = self.get_text_by_selectors(sb, sponsored_price_selectors)
                property_data['precio'] = price
            except:
                property_data['precio'] = "Precio no disponible"
            
            # Ubicación básica
            try:
                sponsored_location_selectors = [
                    "[class*='location']",
                    "[class*='address']",
                    "[class*='ubicacion']",
                    ".zone",
                    ".area"
                ]
                location = self.get_text_by_selectors(sb, sponsored_location_selectors)
                property_data['ubicacion'] = location
            except:
                property_data['ubicacion'] = "Ubicación no disponible"
            
            # Campos específicos para propiedades patrocinadas
            property_data['tipo_propiedad'] = "Patrocinada"
            property_data['superficie_total'] = "N/A"
            property_data['superficie_cubierta'] = "N/A"
            property_data['habitaciones'] = "N/A"
            property_data['banos'] = "N/A"
            property_data['cocheras'] = "N/A"
            property_data['descripcion'] = "Propiedad patrocinada - Descripción limitada"
            property_data['caracteristicas'] = "Ver detalles en la página original"
            property_data['contacto'] = "N/A"
            property_data['telefono'] = "N/A"
            
            self.logger.info(f"✅ Datos básicos extraídos de propiedad patrocinada")
            return property_data
            
        except Exception as e:
            self.logger.error(f"❌ Error extrayendo propiedad patrocinada: {e}")
            return None
    
    def extract_regular_property_data(self, sb, url: str) -> Optional[Dict]:
        """
        Extraer datos de propiedades regulares usando selectores específicos de inmuebles24
        """
        try:
            self.logger.info("🏠 Extrayendo datos de propiedad regular...")
            
            # Inicializar diccionario de datos de propiedad
            property_data = {
                'url': url,
                'titulo': "N/A",
                'precio': "N/A",
                'ubicacion': "N/A",
                'tipo_propiedad': "N/A",
                'superficie_total': "N/A",
                'superficie_cubierta': "N/A",
                'habitaciones': "N/A",
                'banos': "N/A",
                'cocheras': "N/A",
                'caracteristicas': "N/A",
                'descripcion': "N/A",
                'contacto': "N/A",
                'operacion': "N/A",
                'mantenimiento': "N/A",
                'anunciante': "N/A",
                'codigo_anunciante': "N/A",
                'codigo_inmuebles24': "N/A",
                'tiempo_publicacion': "N/A"
            }
            
            # 1. Título principal
            try:
                title_element = sb.find_element("h1.title-property")
                property_data['titulo'] = title_element.text.strip()
            except:
                property_data['titulo'] = "N/A"
            
            # 2. Tipo de inmueble, área, recámaras y estacionamientos desde h2
            try:
                h2_element = sb.find_element("h2.title-type-sup-property")
                h2_text = h2_element.text
                tokens = [t.strip() for t in h2_text.replace("·", "|").split("|") if t.strip()]
                
                property_data['tipo_propiedad'] = tokens[0] if len(tokens) > 0 else "N/A"
                property_data['superficie_total'] = tokens[1] if len(tokens) > 1 else "N/A"
                
                # Extraer número de recámaras
                if len(tokens) > 2:
                    import re
                    match = re.search(r"(\d+)", tokens[2])
                    property_data['habitaciones'] = match.group(1) if match else "N/A"
                
                # Extraer estacionamientos
                if len(tokens) > 3:
                    match = re.search(r"(\d+)", tokens[3])
                    property_data['cocheras'] = match.group(1) if match else "N/A"
                    
            except Exception as e:
                self.logger.warning(f"No se pudo extraer info del h2: {e}")
            
            # 3. Precio y operación
            try:
                price_container = sb.find_element(".price-container-property")
                price_value_div = price_container.find_element(By.CSS_SELECTOR, ".price-value")
                
                # Determinar operación
                price_text = price_value_div.text.lower()
                if "venta" in price_text:
                    property_data['operacion'] = "venta"
                elif "renta" in price_text:
                    property_data['operacion'] = "renta"
                
                # Extraer precio
                try:
                    span_precio = price_value_div.find_element(By.TAG_NAME, "span")
                    property_data['precio'] = span_precio.text.strip()
                except:
                    property_data['precio'] = "N/A"
                
                # Extraer mantenimiento/expensas
                try:
                    extra_div = price_container.find_element(By.CSS_SELECTOR, ".price-extra")
                    span_mant = extra_div.find_element(By.CSS_SELECTOR, ".price-expenses")
                    property_data['mantenimiento'] = span_mant.text.strip()
                except:
                    property_data['mantenimiento'] = "N/A"
                    
            except Exception as e:
                self.logger.warning(f"No se pudo extraer precio: {e}")
            
            # 4. Dirección/Ubicación
            try:
                location_div = sb.find_element(".section-location-property")
                h4_element = location_div.find_element(By.TAG_NAME, "h4")
                property_data['ubicacion'] = h4_element.text.strip()
            except Exception as e:
                self.logger.warning(f"No se pudo extraer ubicación: {e}")
            
            # 5. Descripción completa
            try:
                desc_section = sb.find_element("section.article-section-description")
                long_desc = desc_section.find_element(By.ID, "longDescription")
                property_data['descripcion'] = long_desc.text.strip()
            except Exception as e:
                self.logger.warning(f"No se pudo extraer descripción: {e}")
            
            # 6. Información del anunciante
            try:
                anunciante_element = sb.find_element('[data-qa="linkMicrositioAnunciante"]')
                property_data['anunciante'] = anunciante_element.text.strip()
                property_data['contacto'] = anunciante_element.text.strip()
            except Exception as e:
                self.logger.warning(f"No se pudo extraer anunciante: {e}")
            
            # 7. Códigos del anuncio
            try:
                codes_section = sb.find_element("#reactPublisherCodes")
                lis = codes_section.find_elements(By.TAG_NAME, "li")
                
                for li in lis:
                    text = li.text.strip()
                    if "Cód. del anunciante" in text:
                        parts = text.split(":")
                        property_data['codigo_anunciante'] = parts[1].strip() if len(parts) > 1 else "N/A"
                    elif "Cód. Inmuebles24" in text:
                        parts = text.split(":")
                        property_data['codigo_inmuebles24'] = parts[1].strip() if len(parts) > 1 else "N/A"
            except Exception as e:
                self.logger.warning(f"No se pudieron extraer códigos: {e}")
            
            # 8. Tiempo de publicación
            try:
                user_views = sb.find_element("#user-views")
                p_element = user_views.find_element(By.TAG_NAME, "p")
                property_data['tiempo_publicacion'] = p_element.text.strip()
            except Exception as e:
                self.logger.warning(f"No se pudo extraer tiempo publicación: {e}")
            
            # 9. Información detallada de iconos
            try:
                features_ul = sb.find_element("#section-icon-features-property")
                lis = features_ul.find_elements(By.CSS_SELECTOR, "li.icon-feature")
                
                for li in lis:
                    try:
                        icon = li.find_element(By.TAG_NAME, "i")
                        classes = icon.get_attribute("class") or ""
                        text = li.text.strip()
                        
                        if "icon-stotal" in classes:
                            property_data['superficie_total'] = text
                        elif "icon-scubierta" in classes:
                            property_data['superficie_cubierta'] = text
                        elif "icon-bano" in classes:
                            property_data['banos'] = text
                        elif "icon-cochera" in classes:
                            property_data['cocheras'] = text
                        elif "icon-dormitorio" in classes:
                            property_data['habitaciones'] = text
                    except:
                        continue
                        
            except Exception as e:
                self.logger.warning(f"No se pudieron extraer características detalladas: {e}")
            
            # 10. Extraer características adicionales (botones expandibles)
            try:
                caracteristicas_list = []
                container = sb.find_element("#reactGeneralFeatures")
                buttons = container.find_elements(By.TAG_NAME, "button")
                
                for button in buttons:
                    try:
                        # Click en el botón para expandir
                        sb.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.5)
                        sb.execute_script("arguments[0].click();", button)
                        time.sleep(1)
                        
                        # Extraer información del contenido expandido
                        details_container = container.find_elements(By.TAG_NAME, "div")[1]
                        features = [elem.text.strip() for elem in details_container.find_elements(By.TAG_NAME, "span") if elem.text.strip()]
                        
                        button_text = button.find_element(By.TAG_NAME, "span").text.strip()
                        if features:
                            caracteristicas_list.append(f"{button_text}: {'; '.join(features)}")
                            
                    except:
                        continue
                
                property_data['caracteristicas'] = " | ".join(caracteristicas_list) if caracteristicas_list else "N/A"
                
            except Exception as e:
                self.logger.warning(f"No se pudieron extraer características expandibles: {e}")
            
            # Verificar que se extrajo información básica
            if property_data['titulo'] != "N/A" or property_data['precio'] != "N/A":
                self.logger.info(f"✅ Datos regulares extraídos exitosamente")
                return property_data
            else:
                self.logger.warning(f"⚠️  No se pudo extraer información básica de propiedad regular")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error extrayendo propiedad regular: {e}")
            return None
        """
        Extraer datos de propiedades regulares (no patrocinadas)
        """
        try:
            # Título principal
            try:
                title_selectors = [
                    "h1.title-property",
                    "h1.property-title",
                    "h1[data-qa='property-title']",
                    "h1"
                ]
                title = self.get_text_by_selectors(sb, title_selectors)
                property_data['titulo'] = title
            except:
                property_data['titulo'] = "N/A"
            
            # Precio
            try:
                price_selectors = [
                    ".price-property",
                    ".property-price",
                    "[data-qa='property-price']",
                    ".price",
                    ".precio"
                ]
                price = self.get_text_by_selectors(sb, price_selectors)
                property_data['precio'] = price
            except:
                property_data['precio'] = "N/A"
            
            # Ubicación detallada
            try:
                location_selectors = [
                    ".location-property",
                    ".property-location",
                    "[data-qa='property-location']",
                    ".address",
                    ".ubicacion"
                ]
                location = self.get_text_by_selectors(sb, location_selectors)
                property_data['ubicacion'] = location
            except:
                property_data['ubicacion'] = "N/A"
            
            # Tipo de propiedad
            try:
                type_selectors = [
                    ".property-type",
                    "[data-qa='property-type']",
                    ".type"
                ]
                prop_type = self.get_text_by_selectors(sb, type_selectors)
                property_data['tipo_propiedad'] = prop_type
            except:
                property_data['tipo_propiedad'] = "N/A"
            
            # Superficie/Área
            try:
                surface_selectors = [
                    ".surface-property",
                    ".property-surface",
                    "[data-qa='surface']",
                    ".superficie",
                    ".area"
                ]
                surface = self.get_text_by_selectors(sb, surface_selectors)
                property_data['superficie_total'] = surface
            except:
                property_data['superficie_total'] = "N/A"
            
            # Características principales (habitaciones, baños, etc.)
            try:
                features_selectors = [
                    ".features-property",
                    ".property-features",
                    "[data-qa='features']",
                    ".characteristics"
                ]
                features_element = None
                for selector in features_selectors:
                    try:
                        features_element = sb.find_element(selector)
                        break
                    except:
                        continue
                
                if features_element:
                    # Extraer características específicas
                    feature_items = features_element.find_elements(By.CSS_SELECTOR, "li, .feature-item, .characteristic")
                    features = [item.text.strip() for item in feature_items if item.text.strip()]
                    property_data['caracteristicas'] = " | ".join(features)
                else:
                    # Buscar características individuales
                    rooms = self.get_text_by_selectors(sb, [".rooms", ".bedrooms", ".habitaciones"])
                    bathrooms = self.get_text_by_selectors(sb, [".bathrooms", ".banos", ".baños"])
                    property_data['caracteristicas'] = f"Habitaciones: {rooms} | Baños: {bathrooms}"
            except:
                property_data['caracteristicas'] = "N/A"
            
            # Descripción completa
            try:
                description_selectors = [
                    ".description-property",
                    ".property-description",
                    "[data-qa='description']",
                    ".description"
                ]
                description = self.get_text_by_selectors(sb, description_selectors)
                property_data['descripcion'] = description
            except:
                property_data['descripcion'] = "N/A"
            
            # Información del contacto/agente
            try:
                contact_selectors = [
                    ".contact-property",
                    ".agent-info",
                    "[data-qa='contact']",
                    ".contact-info"
                ]
                contact = self.get_text_by_selectors(sb, contact_selectors)
                property_data['contacto'] = contact
            except:
                property_data['contacto'] = "N/A"
            
            # Campos adicionales para compatibilidad
            property_data['superficie_cubierta'] = "N/A"
            property_data['habitaciones'] = "N/A"
            property_data['banos'] = "N/A"
            property_data['cocheras'] = "N/A"
            property_data['telefono'] = "N/A"
            
            # Verificar que se extrajo al menos información básica
            if property_data['titulo'] != "N/A" or property_data['precio'] != "N/A":
                self.logger.info(f"✅ Datos regulares extraídos exitosamente")
                return property_data
            else:
                self.logger.warning(f"⚠️  No se pudo extraer información básica de propiedad regular")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error extrayendo propiedad regular: {e}")
            return None

    def extract_detailed_property_data(self, sb, url):
        """
        Método principal que determina el tipo de propiedad y extrae los datos
        """
        try:
            self.logger.info(f"🔍 Iniciando extracción de datos para URL: {url}")
            
            # Verificar si es una propiedad patrocinada
            if self.is_sponsored_property(sb, url):
                self.logger.info("📢 Detectada propiedad patrocinada")
                return self.extract_sponsored_property_data(sb, url)
            else:
                self.logger.info("🏠 Detectada propiedad regular")
                return self.extract_regular_property_data(sb, url)
                
        except Exception as e:
            self.logger.error(f"❌ Error extrayendo datos de {url}: {e}")
            return None

    def get_text_by_selectors(self, sb, selectors: List[str]) -> str:
        """Helper para probar múltiples selectores y retornar el primer texto encontrado"""
        for selector in selectors:
            try:
                element = sb.find_element(selector)
                text = element.text.strip()
                if text:
                    return text
            except:
                continue
        return "N/A"
    
    def wait_and_check_blocking(self, sb, timeout=15) -> bool:
        """
        Verificar si la página está bloqueada o cargada correctamente
        Específico para inmuebles24
        """
        try:
            # Esperar a que carguen elementos de la página de detalle
            WebDriverWait(sb.driver, timeout).until(
                lambda driver: (
                    driver.find_elements(By.CSS_SELECTOR, "h1") or
                    driver.find_elements(By.CSS_SELECTOR, ".title-property") or
                    driver.find_elements(By.CSS_SELECTOR, "#challenge-form") or
                    driver.find_elements(By.CSS_SELECTOR, ".cf-browser-verification")
                )
            )
            
            # Verificar elementos de bloqueo específicos de inmuebles24
            blocking_selectors = [
                "#challenge-form",
                ".cf-browser-verification", 
                ".cf-checking-browser",
                "title:contains('Just a moment')",
                "h1:contains('Checking your browser')",
                ".captcha",
                "#captcha",
                ".access-denied",
                ".blocked-access"
            ]
            
            for selector in blocking_selectors:
                if sb.is_element_visible(selector):
                    self.logger.warning(f"🚫 Página bloqueada - detectado: {selector}")
                    return False
            
            # Verificar si la página tiene contenido de propiedad
            content_found = (
                sb.find_elements("h1") or
                sb.find_elements(".title-property") or
                sb.find_elements(".property-title") or
                sb.find_elements(".price-property")
            )
            
            if content_found:
                self.logger.debug("✅ Página de detalle cargada correctamente")
                return True
            else:
                self.logger.warning("⚠️  Página cargada pero sin contenido detectado")
                return False
                
        except TimeoutException:
            self.logger.error("❌ Timeout esperando que cargue la página de detalle")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error verificando bloqueo: {e}")
            return False
    
    def scrape_properties(self) -> Tuple[int, int]:
        """
        Método principal de scraping de propiedades individuales
        Retorna (total_processed, successful_extractions)
        """
        self.start_time = datetime.now()
        
        if not self.property_urls:
            self.logger.error("❌ No hay URLs para procesar")
            return 0, 0
        
        # Cargar checkpoint si existe
        checkpoint = self.load_checkpoint()
        if checkpoint and self.resume_from == 0:
            self.resume_from = checkpoint.get('last_index', 0)
            self.logger.info(f"🔄 Resumiendo desde índice {self.resume_from}")
        
        with SB(**self.create_professional_driver()) as sb:
            
            start_index = self.resume_from
            end_index = len(self.property_urls)
            
            if self.max_properties:
                end_index = min(start_index + self.max_properties, end_index)
            
            consecutive_failures = 0
            max_consecutive_failures = 10
            
            for i in range(start_index, end_index):
                url = self.property_urls[i]
                
                try:
                    self.logger.info(f"🏠 Procesando propiedad {i+1}/{len(self.property_urls)}: {url}")
                    
                    # Navegar a la página de la propiedad
                    sb.open(url)
                    
                    # Pausa para carga (crucial para inmuebles24)
                    time.sleep(4)
                    
                    # Verificar bloqueo y esperar carga
                    if not self.wait_and_check_blocking(sb):
                        consecutive_failures += 1
                        self.errors_count += 1
                        
                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.error(f"❌ Demasiados fallos consecutivos ({consecutive_failures}). Deteniendo.")
                            break
                        
                        self.logger.warning(f"⚠️  Propiedad {i+1} falló. Continuando...")
                        time.sleep(8)  # Pausa más larga para inmuebles24
                        continue
                    
                    # Extraer datos de la propiedad
                    property_data = self.extract_detailed_property_data(sb, url)
                    
                    if property_data:
                        self.properties_data.append(property_data)
                        self.successful_extractions += 1
                        consecutive_failures = 0  # Reset contador
                        self.logger.info(f"✅ Datos extraídos exitosamente para propiedad {i+1}")
                    else:
                        consecutive_failures += 1
                        self.errors_count += 1
                        self.logger.warning(f"⚠️  No se pudieron extraer datos de propiedad {i+1}")
                    
                    self.properties_processed += 1
                    
                    # Guardar checkpoint cada N propiedades
                    if (i + 1) % self.checkpoint_interval == 0:
                        self.save_checkpoint(i)
                    
                    # Log de progreso
                    elapsed = datetime.now() - self.start_time
                    avg_time_per_property = elapsed.total_seconds() / self.properties_processed
                    success_rate = (self.successful_extractions / self.properties_processed) * 100
                    
                    self.logger.info(f"📊 Progreso - Procesadas: {self.properties_processed} | Exitosas: {self.successful_extractions} | Tasa éxito: {success_rate:.1f}% | Tiempo: {avg_time_per_property:.1f}s/prop")
                    
                    # Pausa entre propiedades (anti-detección para inmuebles24)
                    time.sleep(3)
                    
                except KeyboardInterrupt:
                    self.logger.info("⏹️  Scraping interrumpido por usuario")
                    self.save_checkpoint(i)
                    break
                    
                except Exception as e:
                    consecutive_failures += 1
                    self.errors_count += 1
                    self.logger.error(f"❌ Error procesando propiedad {i+1}: {e}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.error("❌ Demasiados errores consecutivos. Deteniendo.")
                        break
                    
                    time.sleep(8)
        
        return self.properties_processed, self.successful_extractions
    
    def save_results(self) -> str:
        """Guardar resultados en formato CSV con metadata"""
        if not self.properties_data:
            self.logger.warning("⚠️  No hay datos para guardar")
            return None
        
        # Generar timestamp para archivos
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        run_str = f"{self.run_number:02d}"
        current = datetime.now()
        month_abbrev = calendar.month_abbr[current.month]
        year_short = current.strftime("%y")

        execution_dir = self.data_dir
        execution_dir.mkdir(parents=True, exist_ok=True)

        csv_filename = f"inm24_{month_abbrev}{year_short}_{run_str}.csv"
        csv_path = execution_dir / csv_filename
        
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
                'total_urls_provided': len(self.property_urls),
                'properties_processed': self.properties_processed,
                'successful_extractions': self.successful_extractions,
                'errors_count': self.errors_count,
                'execution_time_seconds': (datetime.now() - self.start_time).total_seconds(),
                'csv_filename': csv_filename,
                'log_filename': self.log_file.name,
                'urls_file_used': str(self.urls_file) if self.urls_file else None
            },
            'system_info': {
                'scraper_version': '1.0.0',
                'scraper_type': 'detailed_individual_properties',
                'python_version': sys.version,
                'headless_mode': self.headless,
                'max_properties_limit': self.max_properties,
                'resume_from_index': self.resume_from
            }
        }
        
        metadata_path = execution_dir / f"metadata_unico_{timestamp}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"💾 Resultados guardados:")
        self.logger.info(f"   📄 CSV Detalles: {csv_path}")
        self.logger.info(f"   📋 Metadata: {metadata_path}")
        
        # Limpiar checkpoint al finalizar exitosamente
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            self.logger.info("🗑️  Checkpoint limpiado")
        
        return str(csv_path)
    
    def run(self) -> Dict:
        """Ejecutar scraping completo y retornar resultados"""
        self.logger.info("🚀 Iniciando scraping detallado de propiedades Inmuebles24")
        self.logger.info("="*70)
        
        try:
            # Ejecutar scraping
            properties_processed, successful_extractions = self.scrape_properties()
            
            if properties_processed == 0:
                return {
                    'success': False,
                    'error': 'No se procesaron propiedades',
                    'properties_processed': 0,
                    'successful_extractions': 0
                }
            
            # Guardar resultados
            csv_path = self.save_results()
            
            # Calcular estadísticas finales
            total_time = datetime.now() - self.start_time
            avg_time_per_property = total_time.total_seconds() / max(properties_processed, 1)
            success_rate = (successful_extractions / max(properties_processed, 1)) * 100
            
            results = {
                'success': True,
                'properties_processed': properties_processed,
                'successful_extractions': successful_extractions,
                'errors_count': self.errors_count,
                'total_time_seconds': total_time.total_seconds(),
                'avg_time_per_property': avg_time_per_property,
                'success_rate': success_rate,
                'csv_file': csv_path,
                'operation_type': self.operation_type
            }
            
            # Log final
            self.logger.info("="*70)
            self.logger.info("🎉 SCRAPING DETALLADO COMPLETADO EXITOSAMENTE")
            self.logger.info(f"📊 Propiedades procesadas: {properties_processed}")
            self.logger.info(f"✅ Extracciones exitosas: {successful_extractions}")
            self.logger.info(f"❌ Errores: {self.errors_count}")
            self.logger.info(f"⏱️  Tiempo total: {total_time}")
            self.logger.info(f"⚡ Promedio por propiedad: {avg_time_per_property:.1f}s")
            self.logger.info(f"✅ Tasa de éxito: {success_rate:.1f}%")
            self.logger.info("="*70)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error fatal en scraping: {e}")
            return {
                'success': False,
                'error': str(e),
                'properties_processed': self.properties_processed,
                'successful_extractions': self.successful_extractions
            }

def run_scraper(urls_file: str, output_path: str | None = None,
                max_properties: int = None) -> Dict:
    """Interface function for orchestrator usage."""

    operation_type = 'venta'
    if urls_file:
        name = Path(urls_file).name.upper()
        if '_REN_' in name:
            operation_type = 'renta'
        elif '_VND_' in name:
            operation_type = 'venta-d'
        elif '_VNR_' in name:
            operation_type = 'venta-r'

    scraper = Inmuebles24UnicoProfessionalScraper(
        urls_file=urls_file,
        headless=True,
        max_properties=max_properties,
        resume_from=0,
        operation_type=operation_type,
    )

    return scraper.run()

def main():
    """Función principal con argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Inmuebles24 Unico Professional Scraper')
    parser.add_argument('--urls-file', type=str, default=None,
                       help='Archivo con URLs de propiedades a procesar')
    parser.add_argument('--headless', action='store_true', default=True, 
                       help='Ejecutar en modo headless (sin GUI)')
    parser.add_argument('--properties', type=int, default=None, 
                       help='Número máximo de propiedades a procesar')
    parser.add_argument('--resume', type=int, default=0, 
                       help='Índice desde el cual resumir')
    parser.add_argument('--operation', choices=['venta', 'renta'], default='venta',
                       help='Tipo de operación: venta o renta')
    parser.add_argument('--gui', action='store_true', 
                       help='Ejecutar con GUI (opuesto a --headless)')
    
    args = parser.parse_args()
    
    # Ajustar headless basado en argumentos
    # Por defecto es headless para Ubuntu Server, GUI solo si se especifica --gui
    if args.gui:
        args.headless = False
    else:
        args.headless = True
    
    # Crear y ejecutar scraper
    scraper = Inmuebles24UnicoProfessionalScraper(
        urls_file=args.urls_file,
        headless=args.headless,
        max_properties=args.properties,
        resume_from=args.resume,
        operation_type=args.operation
    )
    
    results = scraper.run()
    
    # Retornar código de salida apropiado
    sys.exit(0 if results['success'] else 1)

if __name__ == "__main__":
    main()
