#!/usr/bin/env python3
"""
Data Structure Generator - PropertyScraper Dell710
Crea automáticamente la estructura completa de carpetas para todos los sitios web
"""

import os
import datetime
from pathlib import Path

def create_data_structure():
    """Crear estructura completa de carpetas para todos los sitios web"""
    
    # Sitios web principales
    websites = [
        'inmuebles24',
        'casas_y_terrenos', 
        'lamudi',
        'mitula',
        'propiedades',
        'segundamano',
        'trovit'
    ]
    
    # Tipos de operación
    operations = ['venta', 'renta']
    
    # Generar meses (desde agosto 2025 hasta diciembre 2026)
    months = []
    start_year = 2025
    start_month = 8  # Agosto
    
    for year in range(start_year, 2027):  # 2025 y 2026
        month_start = start_month if year == start_year else 1
        month_end = 12
        
        for month in range(month_start, month_end + 1):
            month_names = {
                1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
            }
            months.append(f"{month_names[month]} {year}")
    
    # Ejecuciones por mes
    executions = ['1er_script_del_mes', '2do_script_del_mes']
    
    # Directorio base
    base_dir = Path(__file__).parent.parent / 'data'
    
    print("🏗️  Creando estructura completa de carpetas...")
    print("="*60)
    
    created_count = 0
    
    for website in websites:
        print(f"\n📁 Creando estructura para: {website}")
        
        for operation in operations:
            for month in months:
                for execution in executions:
                    # Ruta completa
                    folder_path = base_dir / website / operation / month / execution
                    
                    # Crear carpeta
                    folder_path.mkdir(parents=True, exist_ok=True)
                    created_count += 1
                    
                    # Crear archivo README en cada carpeta
                    readme_path = folder_path / 'README.md'
                    readme_content = f"""# {website.upper()} - {operation.upper()}
## {month} - {execution.replace('_', ' ').title()}

Esta carpeta contiene los archivos CSV generados por el scraper de {website} 
para propiedades en {operation} durante la ejecución del {execution.replace('_', ' ')}.

### Archivos esperados:
- `{website}_{operation}_{month.replace(' ', '_').lower()}_{execution}.csv`
- `metadata_{execution}.json`
- `execution_log_{execution}.log`

### Información:
- **Sitio web**: {website}
- **Tipo**: {operation}
- **Período**: {month}
- **Ejecución**: {execution}
- **Generado**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write(readme_content)
    
    print(f"\n✅ Estructura completa creada:")
    print(f"   📁 {len(websites)} sitios web")
    print(f"   📁 {len(operations)} tipos de operación")
    print(f"   📁 {len(months)} meses")
    print(f"   📁 {len(executions)} ejecuciones por mes")
    print(f"   📁 Total de carpetas: {created_count}")
    print(f"   📄 Total de README: {created_count}")
    
    return created_count

if __name__ == "__main__":
    created = create_data_structure()
    print(f"\n🎉 ¡Estructura completa! {created} carpetas creadas exitosamente")
