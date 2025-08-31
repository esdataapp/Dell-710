# Nuevos Scrapers Profesionales - PropertyScraper Dell710

## 📋 Resumen de Scrapers Creados

Se han creado **6 nuevos scrapers profesionales** siguiendo los mismos patrones anti-detección y de resilencia que `inmuebles24_professional.py`:

### Scrapers de Fase Única:
1. **`propiedades_professional.py`** - Scraper completo para propiedades.com
2. **`segundamano_professional.py`** - Scraper completo para segundamano.mx
3. **`trovit_professional.py`** - Scraper completo para trovit.com.mx

### Scrapers de Dos Fases:
4. **`lamudi_professional.py`** - Fase 1: Recolección de URLs de lamudi.com.mx
5. **`lamudi_unico_professional.py`** - Fase 2: Extracción detallada de propiedades individuales
6. **`inmuebles24_unico_professional.py`** - Fase 2: Extracción detallada de propiedades individuales

---

## 🔧 Características Técnicas Implementadas

### ✅ Anti-Detección Avanzada
- **SeleniumBase UC Mode**: Modo undetectable para sitios sofisticados
- **Chrome Headless Optimizado**: Configuración específica para Dell T710
- **User Agent Consistency**: Mozilla/5.0 Linux x86_64 Chrome 120.0.0.0
- **Timing Anti-Bot**: Pausas inteligentes entre páginas y propiedades
- **Resource Optimization**: Configuración para hardware limitado

### ✅ Sistema de Resilencia
- **Checkpoint System**: Guardado automático cada 50 páginas/25 propiedades
- **Resume Functionality**: Continuación desde punto de interrupción
- **Error Recovery**: Manejo de fallos consecutivos con límites configurables
- **Graceful Degradation**: Continuar procesamiento ante errores individuales

### ✅ Logging Profesional
- **Structured Logging**: Formato consistente con timestamps
- **Progress Tracking**: Métricas de rendimiento en tiempo real
- **Error Classification**: Categorización de tipos de errores
- **Performance Analytics**: Tiempo promedio por página/propiedad

### ✅ Organización de Datos
- **Hierarchical Storage**: `data/[site]/[operation]/[month]/[phase]/`
- **CSV + Metadata**: Archivos de datos con información de ejecución
- **URL Management**: Para scrapers de dos fases con archivos de URLs
- **Timestamp Tracking**: Trazabilidad completa de ejecuciones

---

## 📁 Estructura de Archivos Creados

```
PropertyScraper-Dell710/
├── scrapers/
│   ├── propiedades_professional.py      # ✅ NUEVO
│   ├── segundamano_professional.py      # ✅ NUEVO
│   ├── trovit_professional.py           # ✅ NUEVO
│   ├── lamudi_professional.py           # ✅ NUEVO (Fase 1)
│   ├── lamudi_unico_professional.py     # ✅ NUEVO (Fase 2)
│   └── inmuebles24_unico_professional.py # ✅ NUEVO (Fase 2)
├── data/
│   ├── propiedades/[venta|renta]/
│   ├── segundamano/[venta|renta]/
│   ├── trovit/[venta|renta]/
│   ├── lamudi/[venta|renta]/
│   └── inmuebles24/[venta|renta]/
└── logs/
    └── checkpoints/
```

---

## 🚀 Ejecución de Scrapers

### Scrapers de Fase Única

```bash
# Propiedades.com
python scrapers/propiedades_professional.py --headless --pages 100 --operation venta
python scrapers/propiedades_professional.py --headless --pages 50 --operation renta

# SegundaMano.mx
python scrapers/segundamano_professional.py --headless --pages 100 --operation venta
python scrapers/segundamano_professional.py --headless --pages 50 --operation renta

# Trovit.com.mx
python scrapers/trovit_professional.py --headless --pages 100 --operation venta
python scrapers/trovit_professional.py --headless --pages 50 --operation renta
```

### Scrapers de Dos Fases

#### Lamudi (Proceso completo):
```bash
# Fase 1: Recolectar URLs
python scrapers/lamudi_professional.py --headless --pages 50 --operation venta

# Fase 2: Extraer detalles (automáticamente encuentra el archivo de URLs más reciente)
python scrapers/lamudi_unico_professional.py --headless --operation venta
```

#### Inmuebles24 (Proceso completo):
```bash
# Fase 1: Ya existe (inmuebles24_professional.py)
python scrapers/inmuebles24_professional.py --headless --pages 50 --operation venta

# Fase 2: Extraer detalles
python scrapers/inmuebles24_unico_professional.py --headless --operation venta
```

---

## ⚙️ Opciones de Línea de Comandos

Todos los scrapers soportan las siguientes opciones:

```bash
--headless          # Ejecutar sin GUI (por defecto: True)
--gui               # Ejecutar con GUI (sobrescribe --headless)
--pages N           # Máximo número de páginas a procesar
--properties N      # Máximo número de propiedades (solo scrapers _unico)
--resume N          # Resumir desde página/índice específico
--operation TYPE    # 'venta' o 'renta' (por defecto: venta)
--urls-file PATH    # Archivo de URLs (solo scrapers _unico)
```

### Ejemplos avanzados:

```bash
# Scraping con límites específicos
python scrapers/propiedades_professional.py --headless --pages 25 --operation renta

# Resume desde página específica
python scrapers/trovit_professional.py --headless --resume 75 --pages 100

# Scraping con GUI para debugging
python scrapers/lamudi_professional.py --gui --pages 5

# Procesar URLs específicas
python scrapers/lamudi_unico_professional.py --urls-file data/lamudi/venta/urls.txt --properties 100
```

---

## 🔄 Integración con Orchestrator

### Actualizar `concurrent_manager.py`

Agregar los nuevos sitios al routing de scrapers:

```python
# En concurrent_manager.py, actualizar SCRAPER_CONFIGS
SCRAPER_CONFIGS = {
    'inmuebles24': {
        'script_path': 'scrapers/inmuebles24_professional.py',
        'max_concurrent': 2,
        'resource_weight': 0.4
    },
    'propiedades': {
        'script_path': 'scrapers/propiedades_professional.py',
        'max_concurrent': 2,
        'resource_weight': 0.3
    },
    'segundamano': {
        'script_path': 'scrapers/segundamano_professional.py',
        'max_concurrent': 2,
        'resource_weight': 0.3
    },
    'trovit': {
        'script_path': 'scrapers/trovit_professional.py',
        'max_concurrent': 1,
        'resource_weight': 0.4
    },
    'lamudi': {
        'script_path': 'scrapers/lamudi_professional.py',
        'max_concurrent': 1,
        'resource_weight': 0.4
    }
}

# Agregar configuración para scrapers de segunda fase
SECOND_PHASE_SCRAPERS = {
    'lamudi_unico': 'scrapers/lamudi_unico_professional.py',
    'inmuebles24_unico': 'scrapers/inmuebles24_unico_professional.py'
}
```

### Actualizar `bimonthly_scheduler.py`

Incluir todos los sitios en la programación bimensual:

```python
# En bimonthly_scheduler.py, actualizar SITE_CONFIGS
SITE_CONFIGS = {
    'inmuebles24': {
        'pages_venta': 150,
        'pages_renta': 75,
        'priority': 1,
        'two_phase': True
    },
    'propiedades': {
        'pages_venta': 100,
        'pages_renta': 50,
        'priority': 2,
        'two_phase': False
    },
    'segundamano': {
        'pages_venta': 100,
        'pages_renta': 50,
        'priority': 3,
        'two_phase': False
    },
    'trovit': {
        'pages_venta': 80,
        'pages_renta': 40,
        'priority': 4,
        'two_phase': False
    },
    'lamudi': {
        'pages_venta': 75,
        'pages_renta': 40,
        'priority': 5,
        'two_phase': True
    }
}
```

---

## 📊 Workflow de Dos Fases

### Flujo de Inmuebles24:
1. **Fase 1**: `inmuebles24_professional.py` genera CSV con columna 'link'
2. **Fase 2**: `inmuebles24_unico_professional.py` lee URLs del CSV y extrae detalles
3. **Resultado**: CSV con datos básicos + CSV con detalles completos

### Flujo de Lamudi:
1. **Fase 1**: `lamudi_professional.py` genera CSV + archivo de URLs (*.txt)
2. **Fase 2**: `lamudi_unico_professional.py` lee URLs del archivo y extrae detalles
3. **Resultado**: CSV con datos básicos + CSV con detalles completos

---

## 🛠️ Troubleshooting y Maintenance

### Verificar Estado de Checkpoints:
```bash
ls -la logs/checkpoints/
# Archivos *.pkl indican scraping en progreso
```

### Limpiar Checkpoints (si es necesario):
```bash
rm logs/checkpoints/*_checkpoint.pkl
```

### Monitorear Logs en Tiempo Real:
```bash
tail -f logs/propiedades_venta_professional_*.log
tail -f logs/lamudi_unico_venta_professional_*.log
```

### Verificar Rendimiento:
- **Páginas por minuto**: Objetivo 2-3 páginas/min para scrapers simples
- **Propiedades por minuto**: Objetivo 10-15 prop/min para scrapers _unico
- **Tasa de éxito**: Objetivo >85% para scraping estable
- **Uso de CPU/RAM**: Mantener <80% en Dell T710

---

## 🎯 Próximos Pasos

### 1. Pruebas Individuales
Ejecutar cada scraper nuevo con límites pequeños para validar funcionamiento:

```bash
python scrapers/propiedades_professional.py --gui --pages 3
python scrapers/segundamano_professional.py --gui --pages 3
python scrapers/trovit_professional.py --gui --pages 3
python scrapers/lamudi_professional.py --gui --pages 3
```

### 2. Integración Gradual
1. Actualizar `concurrent_manager.py` con un sitio a la vez
2. Probar ejecución concurrente con sitios conocidos
3. Validar que no hay conflictos de recursos

### 3. Automatización Completa
1. Integrar en `bimonthly_scheduler.py`
2. Configurar monitoreo automático
3. Establecer alertas de fallos

### 4. Optimización Continua
- Ajustar timing basado en rendimiento observado
- Refinar selectores si cambian los sitios web
- Optimizar concurrencia según capacidad del servidor

---

## 📈 Métricas de Éxito Esperadas

Con los 6 nuevos scrapers implementados:

- **Cobertura total**: 5 sitios principales de inmuebles en México
- **Datos mensuales**: ~15,000-25,000 propiedades recolectadas
- **Tasa de éxito**: >90% con técnicas anti-detección probadas
- **Tiempo de ejecución**: 3-5 horas para ciclo completo bimensual
- **Reliability**: Sistema robusto con recuperación automática

El sistema PropertyScraper-Dell710 ahora está equipado con scrapers profesionales para todos los sitios objetivo, manteniendo los mismos estándares de calidad y resilencia que el scraper original de inmuebles24.
