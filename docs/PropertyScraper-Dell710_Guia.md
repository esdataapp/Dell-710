# Guía Completa de Operación – PropertyScraper Dell710

## Resumen ejecutivo

PropertyScraper Dell710 es un sistema profesional de scraping inmobiliario, optimizado para correr sin interfaz gráfica en un servidor Dell PowerEdge T710 (Ubuntu Server 24) y controlarse desde Windows 11 por SSH. Incluye:
- Scrapers headless con técnicas anti-detección.
- Orquestación concurrente con control de recursos (CPU/Memoria).
- Programación bi-mensual automática (1–2 y 15–16, 02:00).
- Despliegue y ejecución remota por SSH.
- Monitoreo de performance y logs centralizados.
- Respaldo automático a Google Drive con rclone sin bloquear los scrapers.

Objetivo: extraer, de forma robusta y repetible, listados de propiedades para venta/renta desde múltiples portales, almacenarlos en CSV con metadatos y mantener un historial ordenado por sitio/operación/mes/ejecución.

## Arquitectura y componentes

- scrapers/: scrapers por portal con modo 100% headless.
  - inmuebles24_professional.py (probado)
  - casas_y_terrenos_scraper.py (implementado)
  - mitula_scraper.py (implementado)
  - [pendientes planificados]: lamudi, lamudi_unico, propiedades, segundamano, trovit, inmuebles24_unico
- orchestrator/: coordinación y concurrencia.
  - concurrent_manager.py: gestiona colas, hilos y límites por recursos (DellT710ResourceMonitor).
  - bimonthly_scheduler.py: programador bi-mensual que invoca scrapers (vía SSH executor si aplica).
- ssh_deployment/remote_executor.py: despliegue, sync e invocación remota en el servidor por Paramiko.
- monitoring/performance_monitor.py: métricas y alertas de CPU/Memoria/Disco/Red.
- utils/
  - gdrive_backup_manager.py: respaldo a Google Drive por rclone; soporta modo automático en background.
- config/
  - dell_t710_config.yaml: umbrales de recursos, horarios, rutas remotas.
  - ssh_config.json: conexión y paths remotos (sin comentarios JSON).
- data/: salida en CSV + metadata por ejecución.
- logs/: logs por módulo, historial de ejecuciones y checkpoints.
- docs/: documentación (esta guía y docs previos).

Stack principal: Python 3.12+, SeleniumBase/Selenium, Paramiko, psutil, schedule, pandas, rclone (CLI), logging estructurado.

## Flujo de trabajo end-to-end

1) Programación (bimonthly_scheduler.py) verifica si corresponde ejecución (1–2 o 15–16) y hora (02:00). 
2) Orquestación (concurrent_manager.py) calcula scrapers concurrentes óptimos según CPU/Memoria (máx 4) y lanza hilos.
3) Cada scraper opera en Chrome headless, navega, extrae y guarda CSV+metadata con checkpoints periódicos.
4) Al terminar un scraper, se dispara respaldo a Drive con gdrive_backup_manager (por lotes, no bloqueante si se usa modo automático).
5) Monitoreo registra métricas y alerta si se superan umbrales.
6) Logs centralizados permiten auditoría y diagnóstico.

## Organización de datos

Ruta: data/[sitio]/[operacion]/[Mon YYYY]/[01|02]
- CSV resultado principal (uno o varios por ejecución).
- `metadata_run_XX.json` con timing, parámetros y totales.
- `monitor_run_XX.log` con registro de monitoreo.

## Orquestación y concurrencia

- DellT710ResourceMonitor:
  - CPU máx: 80%; Memoria máx: 80% (24 GB → 19.2 GB).
  - Estimación por scraper: ~15% CPU, ~3 GB RAM.
  - Concurrency óptima: min(80/15, 19.2/3, 4) → máx 4 scrapers.
- ConcurrentScraperManager:
  - Cola de tareas: {site, operation, headless, max_pages, priority}.
  - Lanza hilos con seguridad y obtiene resultados.
  - Integra respaldo a Drive al finalizar cada tarea.
- BiMonthlyScheduler:
  - Determina ventana (1–2, 15–16) y respetar hora configurada.
  - Construye plan (por defecto inmuebles24 venta/renta, expandible) y ejecuta (puede ser remoto via SSH executor).

## Ejecución remota por SSH (Windows → Ubuntu)

- remote_executor.py (Paramiko):
  - connect(): abre SSH + SFTP, verifica sistema remoto.
  - sync_project_files(): sincroniza código (excluye patrones definidos).
  - deploy_project(): instala requirements.
  - execute_scraper(): ejecuta un scraper con parámetros y captura salida.

Requisitos previos en el servidor (Ubuntu 24): Python3, pip, Chrome estable, rclone configurado, usuario scraper con venv.

## Respaldo a Google Drive (rclone)

- gdrive_backup_manager.py:
  - Verifica remoto rclone (gdrive:).
  - Crea estructura de directorios espejo de data/.
  - Copia CSVs en lotes; guarda historial de respaldos.
  - start_automatic_backup(): loop en background que detecta archivos nuevos/modificados y los sube.

Recomendado: iniciar el modo automático al comenzar la orquestación para que el respaldo no bloquee scrapers.

## Monitoreo y logs

- performance_monitor.py: registra CPU/Memoria/Disco/Red, con thresholds y reportes.
- Logs por módulo con timestamps en logs/.
- bimonthly_scheduler guarda execution_history.json con resumen de corridas.

## Configuración clave

- config/dell_t710_config.yaml: límites de recursos, horarios (02:00), rutas remotas y python_env, backup base path.
- config/ssh_config.json: host/puerto/usuario/llave y paths remotos (sin comentarios).
- requirements.txt: dependencias (agregados python-docx y markdown-it-py para esta guía).

## Puesta en marcha (Windows 11)

1) Instalar dependencias del proyecto en el entorno Python local.
2) Desplegar en el servidor (opcional si se orquesta localmente): remote_executor --deploy.
3) Probar un scraper corto headless (5 páginas). 
4) Iniciar orquestación de prueba (concurrent_manager --test) y validar logs.
5) Configurar rclone y probar backup (utils/gdrive_backup_manager.py --test-rclone / --backup-now).

## Operación diaria

- Modo programado: iniciar bimonthly_scheduler en background (o usar un servicio/systemd en el servidor).
- Monitoreo: consultar performance_monitor --status y revisar logs.
- Respaldos: mantener rclone configurado; opcional encender modo automático desde la orquestación.

## Cómo agregar un nuevo sitio o scraper

1) Crear scraper en scrapers/ (ej. lamudi_scraper.py) con clase LamudiScraper:
   - Entradas: headless: bool, max_pages: int, operation_type: "venta|renta".
   - Método run() → dict: {success: bool, total_properties: int, output_files: [paths], metadata_path: str}.
   - Respetar tiempos, waits y técnicas de anti-detección usadas en inmuebles24_professional.
   - Guardar CSV+metadata en la ruta data/[sitio]/[operacion]/[Mon YYYY]/[01|02]/.
2) Integrar en ConcurrentScraperManager:
   - Importar la clase.
   - Agregar case en run_scraper_process() para construir e invocar el scraper según config['site'].
3) Agregar al plan del BiMonthlyScheduler:
   - Extender create_execution_plan() con entradas para el nuevo sitio (venta/renta y páginas estimadas).
4) Validar en orquestación:
   - Ejecutar concurrent_manager --test con el nuevo sitio en el plan y verificar éxito y logs.
5) Respaldo:
   - gdrive_backup_manager no requiere cambios; sube cualquier CSV encontrado en data/.
6) Documentación:
   - Opcional: actualizar docs/ con notas específicas del sitio, selectores clave o límites.

Para scrapers de dos fases (ej. principal → *_unico):
- Ejecutar el scraper principal primero; guardar el CSV base.
- Implementar el scraper *_unico que tome el CSV base como entrada, recorra los enlaces o IDs y enriquezca registros.
- Orquestación: modelar como dos tareas secuenciales para ese site; al terminar la primera, encolar la segunda con referencia al archivo generado.

## Resolución de problemas

- SSH falla: revisar conexión, llave, config/ssh_config.json y reachability (ping). 
- Cloudflare/bloqueos: ajustar timings, headers, y confirmar que se usa el perfil headless correcto.
- Uso alto de recursos: bajar max_concurrent en concurrent_manager o en la config; revisar performance_monitor.
- rclone no detecta remoto: ejecutar rclone config y verificar que exista gdrive:.
- JSON inválidos: recordar que ssh_config.json no admite comentarios; usar campo _comment si se necesita.

## Referencias rápidas

- Ejecutar un scraper local:
  - python scrapers/inmuebles24_professional.py --headless --operation=venta --pages=100
- Orquestación de prueba:
  - python orchestrator/concurrent_manager.py --test
- Scheduler (estado / inicio / forzar ejecución):
  - python orchestrator/bimonthly_scheduler.py --status|--start|--run-now
- Despliegue SSH / estado remoto / test remoto:
  - python ssh_deployment/remote_executor.py --deploy|--status|--test-scraper inmuebles24 --pages 5
- Backup a Drive:
  - python utils/gdrive_backup_manager.py --test-rclone|--backup-now|--start-auto|--status

---
Versión: 1.0 • Fecha: 2025-08-29 • Destino: Dell T710 (Ubuntu 24) • Control: Windows 11
