# PropertyScraper Dell710 - Documentación Completa

## 📋 Índice
1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema) 
3. [Configuración Inicial](#configuración-inicial)
4. [Instalación y Despliegue](#instalación-y-despliegue)
5. [Uso del Sistema](#uso-del-sistema)
6. [Monitoreo y Mantenimiento](#monitoreo-y-mantenimiento)
7. [Resolución de Problemas](#resolución-de-problemas)
8. [API y Referencias](#api-y-referencias)

---

## 🎯 Descripción General

PropertyScraper Dell710 es un sistema profesional de web scraping diseñado específicamente para extraer datos de propiedades inmobiliarias de múltiples sitios web mexicanos. El sistema está optimizado para ejecutarse en el servidor Dell PowerEdge T710 con Ubuntu Server 24, controlado remotamente desde Windows 11 via SSH.

### 🏆 Características Principales
- **Scraping Resiliente**: Sistema de checkpoints y recuperación automática
- **Concurrencia Optimizada**: Hasta 4 scrapers simultáneos usando 80% de recursos Dell T710
- **Ejecución Bi-mensual**: Automatización cada 15 días con programación inteligente
- **Control Remoto SSH**: Despliegue y monitoreo desde Windows 11
- **Anti-detección Probada**: Técnicas validadas con 98% de éxito en inmuebles24
- **Monitoreo Integral**: Seguimiento de recursos y alertas en tiempo real

### 🏠 Sitios Web Soportados
1. **inmuebles24.com** ✅ (Implementado y probado - 98% éxito)
2. **casasyterrenos.com** 📋 (Planificado)
3. **lamudi.com.mx** 📋 (Planificado)
4. **mitula.com.mx** 📋 (Planificado)
5. **propiedades.com** 📋 (Planificado)
6. **segundamano.mx** 📋 (Planificado)
7. **trovit.com.mx** 📋 (Planificado)

---

## 🏗️ Arquitectura del Sistema

### 🖥️ Componentes Principales

```
┌─────────────────┐    SSH    ┌─────────────────────┐
│   Windows 11    │ ========> │    Dell T710        │
│   (Control)     │           │    (Ejecución)      │
│                 │           │                     │
│ - SSH Client    │           │ - Ubuntu Server 24  │
│ - Monitoring    │           │ - PropertyScraper   │
│ - Deployment    │           │ - Chrome Headless   │
└─────────────────┘           └─────────────────────┘
```

### 📁 Estructura del Proyecto

```
PropertyScraper-Dell710/
├── 🕷️  scrapers/                 # Scrapers individuales por sitio web
│   ├── inmuebles24_professional.py    # ✅ Scraper principal (98% éxito)
│   ├── casas_y_terrenos_scraper.py    # 📋 Futuro
│   └── [otros scrapers]...
│
├── 🎛️  orchestrator/            # Sistema de orquestación
│   ├── concurrent_manager.py          # Gestión de scrapers concurrentes
│   ├── bimonthly_scheduler.py         # Programación bi-mensual
│   └── resource_monitor.py            # Monitor de recursos Dell T710
│
├── 🔧 utils/                    # Utilidades y herramientas
│   ├── create_data_structure.py       # Generador de carpetas automático
│   ├── ssh_connector.py               # Conexiones SSH
│   └── data_validator.py              # Validación de datos
│
├── ⚙️  config/                  # Configuraciones del sistema
│   ├── dell_t710_config.yaml          # Config principal Dell T710
│   ├── scraper_settings.json          # Settings de scrapers
│   └── ssh_config.json                # Configuración SSH
│
├── 📊 monitoring/               # Sistema de monitoreo
│   ├── performance_monitor.py         # Monitor de rendimiento
│   ├── error_handler.py               # Manejo de errores
│   └── progress_tracker.py            # Seguimiento de progreso
│
├── 📝 logs/                     # Logs del sistema
│   ├── checkpoints/                   # Puntos de guardado
│   ├── performance_metrics.json       # Métricas de rendimiento
│   └── [logs por fecha/scraper]...
│
├── 📄 data/                     # Datos organizados
│   ├── inmuebles24/
│   │   ├── venta/
│   │   │   ├── Agosto 2025/
│   │   │   │   ├── 1er_script_del_mes/
│   │   │   │   └── 2do_script_del_mes/
│   │   │   └── [otros meses]...
│   │   └── renta/
│   └── [otros sitios]/
│
├── 🌐 ssh_deployment/           # Scripts de despliegue SSH
│   ├── deploy_to_dell710.py           # Despliegue automatizado
│   ├── remote_executor.py             # Ejecución remota
│   └── sync_results.py                # Sincronización de resultados
│
└── 📚 docs/                     # Documentación completa
    ├── COMPLETE_DOCUMENTATION.md      # Este archivo
    ├── API_REFERENCE.md               # Referencias de API
    └── TROUBLESHOOTING.md             # Solución de problemas
```

### 🔄 Flujo de Ejecución

1. **Programación**: Scheduler verifica si corresponde ejecución (días 1-2 o 15-16)
2. **Despliegue**: SSH sync actualiza código en Dell T710
3. **Orquestación**: Manager inicia scrapers concurrentes según recursos disponibles
4. **Scraping**: Cada scraper procesa páginas con checkpoints cada 50 páginas
5. **Monitoreo**: Performance monitor rastrea CPU/memoria en tiempo real
6. **Recuperación**: Sistema auto-resume desde checkpoints ante fallos
7. **Resultados**: Datos CSV + metadata guardados en estructura organizada

---

## ⚙️ Configuración Inicial

### 🖥️ Requisitos Dell T710
- **Hardware**: Dell PowerEdge T710
- **CPU**: Intel Xeon E5620 (8 cores, 2.40GHz)
- **RAM**: 24GB DDR3 ECC
- **Storage**: RAID0-10 HDDs
- **OS**: Ubuntu Server 24 LTS
- **Network**: Ethernet connection, SSH habilitado

### 🖱️ Requisitos Cliente Windows 11
- **OS**: Windows 11
- **Python**: 3.8+ instalado
- **SSH**: Cliente SSH disponible
- **Network**: Acceso a 192.168.50.54

### 🔐 Configuración SSH

1. **Generar llaves SSH** (desde Windows 11):
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/dell_t710_key
   ```

2. **Copiar llave pública al servidor**:
   ```bash
   ssh-copy-id -i ~/.ssh/dell_t710_key.pub scraper@192.168.50.54
   ```

3. **Probar conexión**:
   ```bash
   ssh -i ~/.ssh/dell_t710_key scraper@192.168.50.54
   ```

### 📦 Preparación del Servidor (Dell T710)

```bash
# 1. Actualizar sistema
sudo apt update && sudo apt upgrade -y

# 2. Instalar Python y pip
sudo apt install python3 python3-pip python3-venv -y

# 3. Instalar Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable -y

# 4. Crear usuario scraper
sudo useradd -m -s /bin/bash scraper
sudo usermod -aG sudo scraper

# 5. Crear entorno virtual
sudo -u scraper python3 -m venv /home/scraper/venv
```

---

## 🚀 Instalación y Despliegue

### 📦 Instalación Local (Windows 11)

1. **Clonar/descargar proyecto**:
   ```bash
   cd "C:\Users\criss\Desktop\TRABAJANDO\0. Scrapts\Scraps_Esdata\"
   # El proyecto ya está en PropertyScraper-Dell710/
   ```

2. **Instalar dependencias**:
   ```bash
   cd PropertyScraper-Dell710
   pip install -r requirements.txt
   ```

3. **Verificar instalación**:
   ```bash
   python quick_deploy.py
   ```

### 🌐 Despliegue en Dell T710

1. **Despliegue automático completo**:
   ```bash
   python ssh_deployment/remote_executor.py --deploy
   ```

2. **Verificar despliegue**:
   ```bash
   python ssh_deployment/remote_executor.py --status
   ```

3. **Crear estructura de datos**:
   ```bash
   # Se ejecuta automáticamente durante el despliegue
   # O manualmente:
   python utils/create_data_structure.py
   ```

### ✅ Verificación de Instalación

1. **Test de scraper local** (5 páginas):
   ```bash
   python scrapers/inmuebles24_professional.py --headless --pages=5
   ```

2. **Test de scraper remoto**:
   ```bash
   python ssh_deployment/remote_executor.py --test-scraper=inmuebles24 --pages=5
   ```

3. **Test de orquestación concurrente**:
   ```bash
   python orchestrator/concurrent_manager.py --test
   ```

---

## 🎮 Uso del Sistema

### 📅 Programación Automática Bi-mensual

El sistema está configurado para ejecutarse automáticamente cada 15 días:

- **1ra Ejecución**: Días 1-2 de cada mes a las 02:00
- **2da Ejecución**: Días 15-16 de cada mes a las 02:00

#### Iniciar Scheduler:
```bash
python orchestrator/bimonthly_scheduler.py --start
```

#### Ver estado del scheduler:
```bash
python orchestrator/bimonthly_scheduler.py --status
```

#### Ejecutar manualmente:
```bash
python orchestrator/bimonthly_scheduler.py --run-now
```

### 🕷️ Ejecución Manual de Scrapers

#### Scraper Individual:
```bash
# Inmuebles24 - Venta (100 páginas)
python scrapers/inmuebles24_professional.py --headless --operation=venta --pages=100

# Inmuebles24 - Renta (50 páginas)
python scrapers/inmuebles24_professional.py --headless --operation=renta --pages=50

# Con GUI para debugging
python scrapers/inmuebles24_professional.py --gui --operation=venta --pages=5
```

#### Scraper Remoto via SSH:
```bash
# Ejecutar en Dell T710
python ssh_deployment/remote_executor.py --test-scraper=inmuebles24 --pages=100
```

### ⚡ Orquestación Concurrente

#### Test básico (2 scrapers):
```bash
python orchestrator/concurrent_manager.py --test
```

#### Ejecución personalizada:
```python
from orchestrator.concurrent_manager import ConcurrentScraperManager

# Crear manager con 3 scrapers concurrentes
manager = ConcurrentScraperManager(max_concurrent=3)

# Configurar scrapers
scrapers = [
    {
        'site': 'inmuebles24',
        'operation': 'venta', 
        'headless': True,
        'max_pages': 100
    },
    {
        'site': 'inmuebles24',
        'operation': 'renta',
        'headless': True, 
        'max_pages': 100
    }
]

# Ejecutar
results = manager.run_batch_scraping(scrapers)
```

### 📊 Monitoreo en Tiempo Real

#### Monitor de rendimiento:
```bash
# Monitoreo continuo
python monitoring/performance_monitor.py --start

# Estado actual
python monitoring/performance_monitor.py --status

# Reporte resumen
python monitoring/performance_monitor.py --report
```

#### Estado del sistema remoto:
```bash
python ssh_deployment/remote_executor.py --status
```

---

## 📊 Monitoreo y Mantenimiento

### 🔍 Logs del Sistema

Los logs se organizan automáticamente:

```
logs/
├── inmuebles24_professional_YYYYMMDD_HHMMSS.log     # Logs de scraper
├── concurrent_manager_YYYYMMDD_HHMMSS.log           # Logs de orquestación
├── bimonthly_scheduler_YYYYMMDD_HHMMSS.log          # Logs de scheduler
├── ssh_executor_YYYYMMDD_HHMMSS.log                 # Logs SSH
├── performance_monitor_YYYYMMDD_HHMMSS.log          # Logs de monitoreo
├── performance_metrics.json                          # Métricas históricas
├── performance_alerts.log                           # Alertas de rendimiento
├── execution_history.json                           # Historial de ejecuciones
└── checkpoints/                                     # Puntos de guardado
    ├── inmuebles24_venta_checkpoint.pkl
    └── inmuebles24_renta_checkpoint.pkl
```

### 📈 Métricas de Rendimiento

El sistema monitorea automáticamente:

- **CPU**: % uso, frecuencia, número de cores
- **Memoria**: % uso, GB usados/disponibles, swap
- **Disco**: % uso, GB usados/libres, I/O
- **Red**: Bytes enviados/recibidos
- **Procesos**: Cantidad de Python/Chrome processes

#### Thresholds de Alerta:
- **CPU Warning**: 80% | **Critical**: 90%
- **Memory Warning**: 80% | **Critical**: 90%
- **Disk Warning**: 85% | **Critical**: 95%

### 🔧 Tareas de Mantenimiento

#### Limpieza automática:
```bash
# Limpiar logs antiguos (>30 días)
find logs/ -name "*.log" -mtime +30 -delete

# Limpiar checkpoints antiguos
rm logs/checkpoints/*.pkl

# Comprimir datos antiguos
find data/ -name "*.csv" -mtime +30 -exec gzip {} \;
```

#### Verificación de salud:
```bash
# Status completo del sistema
python quick_deploy.py

# Verificar integridad de datos
python utils/data_validator.py --check-all

# Test de conectividad SSH
python ssh_deployment/remote_executor.py --status
```

---

## 🚨 Resolución de Problemas

### ❌ Problemas Comunes

#### 1. Error de Conexión SSH
```
ERROR: No se pudo conectar al Dell T710
```
**Solución**:
```bash
# Verificar conectividad
ping 192.168.50.54

# Probar conexión SSH manual
ssh -i ~/.ssh/dell_t710_key scraper@192.168.50.54

# Verificar configuración
cat config/ssh_config.json
```

#### 2. Scraper Bloqueado por Cloudflare
```
WARNING: Página bloqueada - detectado: #challenge-form
```
**Solución**:
- El sistema usa técnicas anti-detección probadas
- Verificar que está usando el scraper híbrido correcto
- Ajustar timing entre páginas
- Revisar User-Agent en configuración

#### 3. Alta Utilización de Recursos
```
CRITICAL: CPU usage critical: 92.1%
```
**Solución**:
```bash
# Verificar scrapers activos
python monitoring/performance_monitor.py --status

# Reducir scrapers concurrentes
# Editar config/dell_t710_config.yaml:
# max_concurrent_scrapers: 2  # Reducir de 4 a 2
```

#### 4. Fallo en Checkpoint/Recuperación
```
ERROR: Error cargando checkpoint
```
**Solución**:
```bash
# Limpiar checkpoints corruptos
rm logs/checkpoints/*.pkl

# Reiniciar scraper desde página específica
python scrapers/inmuebles24_professional.py --resume=25 --pages=100
```

### 🔍 Debugging Avanzado

#### Modo Debug con GUI:
```bash
# Ejecutar con interfaz gráfica para debugging
python scrapers/inmuebles24_professional.py --gui --pages=5
```

#### Logs detallados:
```bash
# Incrementar nivel de logging
# En el scraper, cambiar:
# logging.basicConfig(level=logging.DEBUG)
```

#### Monitoreo en tiempo real:
```bash
# SSH al servidor y monitorear
ssh scraper@192.168.50.54
htop  # Monitor de procesos
iotop # Monitor de I/O
```

### 📞 Escalación de Problemas

Si los problemas persisten:

1. **Recopilar información**:
   ```bash
   # Generar reporte completo
   python monitoring/performance_monitor.py --report > problem_report.json
   
   # Recopilar logs recientes
   tar -czf logs_$(date +%Y%m%d).tar.gz logs/
   ```

2. **Verificar recursos del sistema**:
   ```bash
   python ssh_deployment/remote_executor.py --status
   ```

3. **Documentar**:
   - Timestamp del problema
   - Logs relevantes
   - Configuración utilizada
   - Pasos para reproducir

---

## 📚 API y Referencias

### 🔧 Clases Principales

#### `Inmuebles24ProfessionalScraper`
```python
scraper = Inmuebles24ProfessionalScraper(
    headless=True,           # Modo sin GUI
    max_pages=100,          # Páginas máximas
    resume_from=1,          # Página de inicio
    operation_type='venta'  # 'venta' o 'renta'
)

results = scraper.run()
```

#### `ConcurrentScraperManager`
```python
manager = ConcurrentScraperManager(max_concurrent=4)

scraper_configs = [
    {
        'site': 'inmuebles24',
        'operation': 'venta',
        'headless': True,
        'max_pages': 100
    }
]

results = manager.run_batch_scraping(scraper_configs)
```

#### `DellT710SSHExecutor`
```python
with DellT710SSHExecutor() as executor:
    # Desplegar proyecto
    executor.deploy_project(project_root)
    
    # Ejecutar scraper remoto
    result = executor.execute_scraper('inmuebles24', {
        'headless': True,
        'max_pages': 50,
        'operation': 'venta'
    })
```

### 📋 Configuración de Parámetros

#### Dell T710 Config (YAML):
```yaml
resource_limits:
  max_cpu_usage_percent: 80
  max_memory_usage_percent: 80
  max_concurrent_scrapers: 4

scraping_optimization:
  page_load_timeout: 30
  between_page_delay: 2
  checkpoint_interval: 50
```

#### Scraper Settings (JSON):
```json
{
  "inmuebles24": {
    "base_url": "https://www.inmuebles24.com/departamentos-en-{operation}-en-zapopan-jalisco.html",
    "selectors": {
      "property_cards": "div[data-qa='posting PROPERTY']",
      "title": "h2 a, h3 a",
      "price": ".price, .posting-price",
      "location": ".posting-location"
    }
  }
}
```

### 📊 Estructura de Datos de Salida

#### CSV Propiedades:
```csv
timestamp,operation_type,titulo,precio,ubicacion,caracteristicas,link
2025-08-29T14:30:00,venta,"Departamento en venta","$2,500,000","Zapopan, Jalisco","2 hab | 2 baños | 85m²","https://..."
```

#### Metadata JSON:
```json
{
  "execution_info": {
    "timestamp": "20250829_143000",
    "operation_type": "venta",
    "total_pages_processed": 100,
    "total_properties_found": 2541,
    "execution_time_seconds": 7892.5
  },
  "system_info": {
    "scraper_version": "1.0.0",
    "headless_mode": true,
    "max_pages_limit": 100
  }
}
```

---

## 🎯 Roadmap y Futuras Mejoras

### 📋 Próximas Características

1. **Más Sitios Web**:
   - Implementar scrapers para casasyterrenos.com
   - Agregar soporte para lamudi.com.mx
   - Desarrollar scraper de mitula.com.mx

2. **Mejoras de IA**:
   - Detección inteligente de layouts
   - Adaptación automática a cambios en sitios web
   - Clasificación automática de propiedades

3. **Analytics Avanzado**:
   - Dashboard web para monitoreo
   - Análisis de precios y tendencias
   - Reportes automatizados

4. **Escalabilidad**:
   - Soporte para múltiples servidores
   - Balanceado de carga automático
   - Almacenamiento distribuido

### 🔄 Mantenimiento Continuo

- **Updates mensuales** de dependencias
- **Revisión trimestral** de selectores web
- **Optimización semestral** de rendimiento
- **Backup anual** de configuraciones

---

**Versión**: 1.0.0  
**Fecha**: Agosto 2025  
**Desarrollado para**: Dell PowerEdge T710 + Ubuntu Server 24  
**Control desde**: Windows 11 via SSH
