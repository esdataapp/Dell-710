#!/usr/bin/env python3
"""Generate the expected ``data`` folder hierarchy for all scrapers.

The structure is based on the combinations found in the ``URLs`` CSV files
(``PaginaWeb``, ``Ciudad``, ``Operacion`` and ``ProductoPaginaWeb``).  For each
combination, directories are created following the pattern::

    data/<PaginaWeb>/<Ciudad>/<Operacion>/<Producto>/<MesAño>/<Run>

where ``MesAño`` uses three letter month abbreviations and the last two digits
of the year (e.g. ``Sep25``) and ``Run`` is ``01`` or ``02``.  A ``README.md``
template describing the expected file naming convention is placed inside every
``Run`` directory.
"""

from __future__ import annotations

import csv
import datetime as dt
import calendar
from pathlib import Path


def _gather_combinations() -> list[tuple[str, str, str, str]]:
    """Collect unique (PaginaWeb, Ciudad, Operacion, Producto) tuples.

    The information is extracted from every ``*_urls.csv`` file inside the
    ``URLs`` directory.
    """

    urls_dir = Path(__file__).resolve().parent.parent / "URLs"
    combos: set[tuple[str, str, str, str]] = set()

    for csv_file in urls_dir.glob("*_urls.csv"):
        with open(csv_file, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                site = (row.get("PaginaWeb") or "").strip()
                city = (row.get("Ciudad") or "").strip()
                op = (row.get("Operacion") or row.get("Operación") or "").strip()
                prod = (row.get("ProductoPaginaWeb") or "").strip()
                if site and city and op and prod:
                    combos.add((site, city, op, prod))

    return sorted(combos)


def _generate_months() -> list[str]:
    """Return month/year identifiers from Aug 2025 through Dec 2026."""

    months: list[str] = []
    for year in range(2025, 2027):
        start_month = 8 if year == 2025 else 1
        for month in range(start_month, 13):
            months.append(f"{calendar.month_abbr[month]}{str(year)[-2:]}")
    return months


def create_data_structure() -> int:
    """Create the full ``data`` folder structure and README templates."""

    combos = _gather_combinations()
    months = _generate_months()
    runs = ["01", "02"]
    base_dir = Path(__file__).resolve().parent.parent / "data"

    print("🏗️  Creando estructura completa de carpetas...")
    print("=" * 60)

    created_count = 0

    for site, city, op, prod in combos:
        print(f"\n📁 Creando estructura para: {site}/{city}/{op}/{prod}")

        for month in months:
            for run in runs:
                folder_path = base_dir / site / city / op / prod / month / run
                folder_path.mkdir(parents=True, exist_ok=True)
                created_count += 1

                readme_path = folder_path / "README.md"
                readme_content = (
                    f"# {site} - {city} - {op} - {prod}\n"
                    f"## {month} - Run {run}\n\n"
                    f"Esta carpeta contiene los archivos generados por el scraper de "
                    f"{site} para {city} ({op}, {prod}) durante {month}, ejecución {run}.\n\n"
                    "### Archivos esperados:\n"
                    f"- `{site}_{city}_{op}_{prod}_{month}_{run}.csv`\n"
                    f"- `metadata_{run}.json`\n"
                    f"- `execution_log_{run}.log`\n\n"
                    "### Información:\n"
                    f"- **Página web**: {site}\n"
                    f"- **Ciudad**: {city}\n"
                    f"- **Operación**: {op}\n"
                    f"- **Producto**: {prod}\n"
                    f"- **Período**: {month}\n"
                    f"- **Ejecución**: {run}\n"
                    f"- **Generado**: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                with open(readme_path, "w", encoding="utf-8") as fh:
                    fh.write(readme_content)

    print("\n✅ Estructura completa creada:")
    print(f"   📁 {len(combos)} combinaciones de PaginaWeb/Ciudad/Operacion/Producto")
    print(f"   📁 {len(months)} meses")
    print(f"   📁 {len(runs)} ejecuciones por mes")
    print(f"   📁 Total de carpetas: {created_count}")
    print(f"   📄 Total de README: {created_count}")

    return created_count


if __name__ == "__main__":
    created = create_data_structure()
    print(f"\n🎉 ¡Estructura completa! {created} carpetas creadas exitosamente")

