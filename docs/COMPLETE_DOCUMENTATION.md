# PropertyScraper Dell710 - Documentation

## Overview
PropertyScraper Dell710 is a web‑scraping toolkit designed to run on a Dell PowerEdge T710 with Ubuntu Server 24. The project collects real estate listings from several Mexican property portals and stores the results in CSV files with accompanying metadata. Scripts can be executed individually or orchestrated concurrently and scheduled for bi‑monthly runs.

## Project Structure
```
PropertyScraper-Dell710/
├── scrapers/                     # Site specific scrapers
│   ├── inm24.py                  # Inmuebles24 scraper (phase 1)
│   ├── inm24_det.py              # Inmuebles24 detailed scraper (phase 2)
│   ├── cyt.py                    # Casas y Terrenos scraper
│   ├── lam.py                    # Lamudi scraper (phase 1)
│   ├── lam_det.py                # Lamudi detailed scraper (phase 2)
│   ├── mit.py                    # Mitula scraper
│   ├── prop.py                   # Propiedades.com scraper
│   └── tro.py                    # Trovit scraper
├── orchestrator/
│   ├── advanced_orchestrator.py  # Concurrent execution manager
│   ├── bimonthly_scheduler.py    # Bi‑monthly scheduler
│   └── concurrent_manager.py     # Legacy concurrent runner
├── utils/
│   ├── browser_config.py
│   ├── checkpoint_recovery.py
│   ├── create_data_structure.py
│   ├── enhanced_scraps_registry.py
│   ├── gdrive_backup_manager.py
│   ├── path_builder.py
│   └── url_utils.py
├── URLs/                         # CSV files with URL inputs
├── config/
│   ├── dell_t710_config.yaml     # Resource limits and paths
│   └── ssh_config.json           # SSH connection details
├── monitoring/
│   └── performance_monitor.py
├── logs/                         # Execution logs and checkpoints
├── data/                         # Scraped data and metadata
└── tests/
    ├── test_detail_subprocess.py
    └── test_scrap_order.py
```

## Supported Sites and Scrapers
| Site | Script(s) |
|------|-----------|
| Inmuebles24 | `inm24.py`, `inm24_det.py` |
| Casas y Terrenos | `cyt.py` |
| Lamudi | `lam.py`, `lam_det.py` |
| Mitula | `mit.py` |
| Propiedades | `prop.py` |
| Trovit | `tro.py` |

`inm24_det.py` and `lam_det.py` perform second‑phase detailed scraping using URL lists produced by their phase‑1 counterparts.

## Usage
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Prepare data folders**
   ```bash
   python utils/create_data_structure.py
   ```
3. **Run a scraper**
   ```bash
   python scrapers/inm24.py --headless --pages 100
   ```
4. **Run the orchestrator**
   ```bash
   python orchestrator/advanced_orchestrator.py
   ```
5. **Schedule bi‑monthly execution**
   ```bash
   python orchestrator/bimonthly_scheduler.py
   ```

## Data Layout
Results are stored under `data/{scraper}/{operation}/{month}/{run}/` and accompanied by JSON metadata and logs. The `URLs/` directory holds input URL CSVs used by detail scrapers.

## Backup and Monitoring
`utils/gdrive_backup_manager.py` can mirror the `data/` directory to Google Drive using rclone. Runtime metrics are collected by `monitoring/performance_monitor.py`.

---
This document reflects the current codebase and scraper filenames. For additional details see inline comments within each module.
