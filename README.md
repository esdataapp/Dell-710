# PropertyScraper Dell710 - Professional Web Scraping System

## 🎯 Descripción del Proyecto

Sistema profesional de web scraping diseñado específicamente para el servidor Dell T710 con Ubuntu Server 24. Implementa scraping concurrente, resiliente y automatizado para múltiples sitios web de bienes raíces con ejecución remota SSH desde Windows 11.

## 🏗️ Arquitectura del Sistema

### Hardware Target
- **Servidor**: Dell PowerEdge T710 
- **CPU**: Intel Xeon E5620 (8 cores, 2.40GHz)
- **RAM**: 24GB DDR3 ECC
- **Storage**: RAID0-10 HDDs
- **OS**: Ubuntu Server 24 LTS
- **Network**: SSH access via 192.168.50.54

### Software Stack
- **Lenguaje**: Python 3.12+
- **Web Scraping**: SeleniumBase (proven Cloudflare bypass)
- **Orchestration**: Custom concurrent manager
- **Remote Execution**: SSH + Paramiko
- **Monitoring**: Real-time logging + progress tracking
- **Data Format**: CSV + JSON metadata

### Componentes Principales

| Componente | Función |
|------------|---------|
| `master_controller.py` | Control central SSH desde Windows |
| `auto_deploy_manager.py` | Despliegue automatizado del sistema |
| `advanced_orchestrator.py` | Orquestación concurrente de scrapers |
| `enhanced_scraps_registry.py` | Registro y seguimiento de ejecuciones |
| `checkpoint_recovery.py` | Recuperación tras interrupciones |
| `gdrive_backup_manager.py` | Backup automático a Google Drive |
| `system_setup.py` | Verificación completa del entorno |

## 📁 Estructura del Proyecto

```
PropertyScraper-Dell710/
├── scrapers/                 # Scrapers individuales por sitio web
│   ├── inm24.py             # Inmuebles24 scraper
│   ├── inm24_det.py         # Inmuebles24 detallado scraper
│   ├── cyt.py               # Casas y Terrenos scraper
│   ├── lam.py               # Lamudi scraper
│   ├── lam_det.py           # Lamudi detallado scraper
│   ├── mit.py               # Mitula scraper
│   ├── prop.py              # Propiedades scraper
│   └── tro.py               # Trovit scraper
├── orchestrator/             # Sistema de orquestación concurrente
│   ├── advanced_orchestrator.py
│   ├── bimonthly_scheduler.py
│   └── concurrent_manager.py
├── utils/                    # Utilidades y herramientas
│   ├── create_data_structure.py
│   ├── checkpoint_recovery.py
│   ├── gdrive_backup_manager.py
│   ├── enhanced_scraps_registry.py
│   └── url_utils.py
├── URLs/                    # Archivos de URLs por sitio (cyt_urls.csv, mit_urls.csv, ...)
├── config/                   # Configuraciones del sistema
│   ├── dell_t710_config.yaml
│   └── ssh_config.json
├── monitoring/               # Sistema de monitoreo
│   └── performance_monitor.py
├── logs/                     # Logs del sistema
├── data/                     # Datos estructurados con nueva nomenclatura
│   ├── inm24/               # Inmuebles24 data
│   │   ├── venta/          # Operación venta
│   │   ├── renta/          # Operación renta
│   │   ├── venta-d/        # Venta desarrollos
│   │   └── venta-r/        # Venta remates
│   ├── cyt/                 # Casas y Terrenos data
│   ├── lam/                 # Lamudi data
│   ├── mit/                 # Mitula data
│   ├── prop/                # Propiedades data
│   └── tro/                 # Trovit data
├── ssh_deployment/           # Scripts de despliegue SSH
│   └── remote_executor.py
└── docs/                     # Documentación completa
```

## 🚀 Características Principales

### ✅ Resilencia y Recuperación
- **Checkpoint System**: Puntos de guardado cada 50 páginas
- **Auto-Resume**: Continúa automáticamente tras interrupciones
- **Error Recovery**: Manejo inteligente de errores de red/servidor
- **Power Outage Protection**: Recuperación tras apagados inesperados

### ⚡ Concurrencia Optimizada
- **Resource Management**: Utiliza 80% de recursos Dell T710 (6.4 cores)
- **Concurrent Scrapers**: Hasta 4 scrapers simultáneos por sitio
- **Load Balancing**: Distribución inteligente de carga
- **Memory Management**: Control de memoria para evitar OOM

### 🕒 Automatización Bi-mensual
- **Scheduled Execution**: Cada 15 días automáticamente
- **Intelligent Timing**: Evita horas pico de los sitios web
- **Data Organization**: Estructura automática por fecha/ejecución
- **Result Sync**: Sincronización automática de resultados

### 🔒 Cloudflare Bypass Probado
- **Hybrid Technique**: Método probado con 98% éxito
- **Headless Operation**: Operación sin GUI en servidor
- **Anti-Detection**: Configuración optimizada para evadir detección
- **Success Rate**: 2541 propiedades extraídas exitosamente

## 🎯 Sitios Web Objetivo

1. **inmuebles24.com** ✅ (Implementado y probado - `inm24.py`, `inm24_det.py`)
2. **casasyterrenos.com** ✅ (Implementado - `cyt.py`)
3. **lamudi.com.mx** ✅ (Implementado - `lam.py`, `lam_det.py`)
4. **mitula.com.mx** ✅ (Implementado - `mit.py`)
5. **propiedades.com** ✅ (Implementado - `prop.py`)
6. **trovit.com.mx** ✅ (Implementado - `tro.py`)

## 📊 Organización de Datos

### Nueva Estructura Optimizada
```
data/{scraper_abrev}/{operation_abrev}/{mesAño}/{script}/
```

### Nomenclatura de Scrapers
- **inm24**: Inmuebles24 general
- **inm24_det**: Inmuebles24 detallado  
- **cyt**: Casas y Terrenos
- **lam**: Lamudi general
- **lam_det**: Lamudi detallado
- **mit**: Mitula
- **prop**: Propiedades
- **tro**: Trovit

### Tipos de Operación
- **venta**: Venta general
- **renta**: Renta general
- **venta-d**: Venta desarrollos (solo Inmuebles24)
- **venta-r**: Venta remates (solo Inmuebles24)

### Archivos de URLs

Los archivos CSV en `URLs/` son la única fuente de URLs del sistema. Los
scrapers y el orquestador inspeccionan automáticamente todos los archivos en
esta carpeta, por lo que no se requieren rutas hardcodeadas ni nombres de
archivo específicos. Cada CSV comparte las siguientes columnas:

```csv
PaginaWeb,Ciudad,Operacion,ProductoPaginaWeb,URL
casas_y_terrenos,Guadalajara,Rentar,Edificios,https://...
```

Notas de nomenclatura:

- `Operacion` sin tilde.
- Operaciones en minúsculas: `venta`, `renta`, `venta-d`, `venta-r`.
- `venta-d` y `venta-r` aplican solo para Inmuebles24 (desarrollos y remates).

### Ejemplo de Ruta Actualizada
```
data/inm24/venta/ago2025/1/
├── inm24_venta_ago_2025_script_1.csv
├── metadata_script_1.json
└── execution_log_script_1.log
```

### Programación de Ejecuciones
- **1ra Ejecución**: Día 1-2 de cada mes
- **2da Ejecución**: Día 15-16 de cada mes
- **Duración Estimada**: 4-8 horas por sitio web completo
- **Total Propiedades**: 15,000+ por ejecución

## 🖥️ Ejecución SSH Remota

### Desde Windows 11 → Dell T710 Ubuntu
```bash
# Conexión SSH automatizada
ssh scraper@192.168.50.54

# Ejecución de scraper específico
python3 /home/scraper/PropertyScraper-Dell710/scrapers/inm24.py

# Monitoreo en tiempo real
tail -f /home/scraper/PropertyScraper-Dell710/logs/progress_monitor.log
```

## ⚙️ Configuración Dell T710

### Recursos Asignados
- **CPU Cores**: 6.4 cores (80% de 8 cores)
- **Memory**: 19.2GB (80% de 24GB)
- **Concurrent Scrapers**: 4 máximo
- **Disk I/O**: Optimizado para RAID0-10

### Monitoreo de Performance
- **CPU Usage**: Máximo 80%
- **Memory Usage**: Máximo 80%
- **Network**: Bandwidth monitoring
- **Temperature**: Thermal monitoring

## 📝 Quick Start

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   # Opcional: dependencias de desarrollo y pruebas
   pip install -r dev-requirements.txt
   ```

2. **Crear estructura de datos**:
   ```bash
   python utils/create_data_structure.py
   ```

3. **Ejecutar scraper individual**:
   ```bash
   # Inmuebles24 general
   python scrapers/inm24.py --headless --pages=100

   # Casas y Terrenos
   python scrapers/cyt.py --headless --pages=50

   # Lamudi
   python scrapers/lam.py --headless --pages=75
   ```

4. **Ejecutar orquestación completa**:
   ```bash
   python orchestrator/advanced_orchestrator.py
   ```

5. **Programar ejecución bi-mensual**:
   ```bash
   python orchestrator/bimonthly_scheduler.py
   ```

6. **Revisar estado de los scraps**:
   ```bash
   python monitoring/scrap_status.py --pagina-web Mit --ciudad Gdl
   ```
   Muestra ejecuciones completadas (runs `01`/`02`), tareas en curso según
   `data/orchestrator_state.json` y tareas en cola. Se puede filtrar por
   `PaginaWeb` y `Ciudad` y ordenar la salida.

## 🏆 Resultados Probados

### Test exitoso - Inmuebles24 (`inm24.py`)
- **Páginas procesadas**: 100
- **Propiedades extraídas**: 2,541
- **Éxito rate**: 98%
- **Tiempo total**: ~3 horas
- **Modo**: Headless (sin GUI)

### Sistema completamente migrado
- **8 Scrapers**: Todos funcionales con nueva nomenclatura
- **SeleniumBase**: Configuración estandarizada y compatible
- **Estructura de datos**: Optimizada con abreviaciones
- **URLs/**: Carpeta con los CSV individuales; única fuente de URLs del sistema.

---

**Desarrollado para**: Dell PowerEdge T710  
**Optimizado para**: Ubuntu Server 24  
**Control remoto**: SSH desde Windows 11  
**Frecuencia**: Bi-mensual (cada 15 días)
