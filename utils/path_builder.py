"""Utilities for constructing data paths with standardized month and run logic."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import calendar
from pathlib import Path


@dataclass
class PathInfo:
    """Container for paths and identifiers used when saving scraper output."""
    directory: Path
    file_name: str
    month_year: str
    run_number: str


def build_path(pagina_web: str, ciudad: str, operacion: str, producto: str) -> PathInfo:
    """Build the directory and file name for a scraping run.

    Args:
        pagina_web: Website identifier (e.g. ``"Cyt"``).
        ciudad: City name.
        operacion: Type of operation (e.g. ``"venta"``).
        producto: Product type for the website.

    Returns:
        PathInfo containing the final directory, default file name, month-year
        string and run number.
    """
    project_root = Path(__file__).resolve().parent.parent

    now = datetime.now()
    month_abbr = calendar.month_abbr[now.month]
    year_short = str(now.year)[-2:]
    month_year = f"{month_abbr}{year_short}"

    base_dir = (
        project_root
        / "data"
        / pagina_web.capitalize()
        / ciudad.capitalize()
        / operacion.capitalize()
        / producto.capitalize()
        / month_year
    )

    run = 1
    while (base_dir / f"{run:02d}").exists():
        run += 1
    run_str = f"{run:02d}"

    final_dir = base_dir / run_str
    final_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{pagina_web.lower()}_{month_year}_{run_str}.csv"
    return PathInfo(final_dir, file_name, month_year, run_str)
