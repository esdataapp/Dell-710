#!/usr/bin/env python3
"""Display scraping status based solely on URL CSV information.

The script inspects CSV files in ``URLs/`` to determine all available
scraping tasks, loading progress metadata such as ``Status``, ``LastRun``
and ``NextRun`` directly from those files. Based on this information
tasks are classified into "completed", "running", "queued" and
"never-run" (no ``LastRun`` value). Results can be filtered and sorted by
``PaginaWeb`` and ``Ciudad``.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
URLS_DIR = PROJECT_ROOT / "URLs"


@dataclass
class ScrapEntry:
    """Represents a single scraping task defined in the CSV files."""

    pagina_web: str
    ciudad: str
    operacion: str
    producto: str
    url: str
    status: str = ""
    last_run: str = ""
    next_run: str = ""
    scrap_of_month: str = ""
    records: int = 0

    @property
    def key(self) -> Tuple[str, str, str, str]:
        return (
            self.pagina_web,
            self.ciudad,
            self.operacion,
            self.producto,
        )


def load_urls() -> List[ScrapEntry]:
    """Load all URL definitions from ``URLs/`` CSV files."""
    scraps: List[ScrapEntry] = []
    if not URLS_DIR.exists():
        return scraps

    for csv_file in URLS_DIR.glob("*.csv"):
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(
                row for row in f if not row.lstrip().startswith("#")
            )
            for row in reader:
                pagina = row.get("PaginaWeb", "").strip()
                ciudad = row.get("Ciudad", "").strip()
                operacion = row.get("Operacion", row.get("Operación", "")).strip()
                producto = row.get("ProductoPaginaWeb", "").strip()
                url = row.get("URL", "").strip()
                status = row.get("Status", "").strip()
                last_run = row.get("LastRun", "").strip()
                next_run = row.get("NextRun", "").strip()
                scrap_of_month = row.get("ScrapOfMonth", "").strip()
                records_str = row.get("Records", "").strip()
                try:
                    records = int(records_str)
                except ValueError:
                    records = 0
                if pagina and ciudad and operacion and producto:
                    scraps.append(
                        ScrapEntry(
                            pagina_web=pagina,
                            ciudad=ciudad,
                            operacion=operacion,
                            producto=producto,
                            url=url,
                            status=status,
                            last_run=last_run,
                            next_run=next_run,
                            scrap_of_month=scrap_of_month,
                            records=records,
                        )
                    )
    return scraps


def main() -> None:
    parser = argparse.ArgumentParser(description="Show current scraping status")
    parser.add_argument("--pagina-web", help="Filter by PaginaWeb")
    parser.add_argument("--ciudad", help="Filter by Ciudad")
    parser.add_argument(
        "--sort",
        choices=["PaginaWeb", "Ciudad"],
        default="PaginaWeb",
        help="Sort output by this field",
    )
    args = parser.parse_args()

    scraps = load_urls()
    if args.pagina_web:
        scraps = [s for s in scraps if s.pagina_web.lower() == args.pagina_web.lower()]
    if args.ciudad:
        scraps = [s for s in scraps if s.ciudad.lower() == args.ciudad.lower()]
    sort_attr = "pagina_web" if args.sort == "PaginaWeb" else "ciudad"
    scraps.sort(key=lambda s: getattr(s, sort_attr).lower())

    month_year = datetime.now().strftime("%b%y")

    completed: List[ScrapEntry] = []
    running: List[ScrapEntry] = []
    queued: List[ScrapEntry] = []
    never_run: List[ScrapEntry] = []

    status_completed = {"completed", "success", "done"}
    status_running = {"running", "in_progress"}

    for scrap in scraps:
        status = scrap.status.lower()
        if not scrap.last_run:
            never_run.append(scrap)
        elif status in status_completed:
            completed.append(scrap)
        elif status in status_running:
            running.append(scrap)
        else:
            queued.append(scrap)

    # Determine "Scrap of the Month" based on completed tasks.
    completed_tasks = [s for s in scraps if s.status.lower() in status_completed]
    scrap_of_month: Optional[ScrapEntry] = None
    if completed_tasks:
        current_marker = datetime.now().strftime("%Y-%m")
        marked = [s for s in completed_tasks if s.scrap_of_month == current_marker]
        candidates = marked or completed_tasks
        scrap_of_month = max(candidates, key=lambda s: s.records)

    print(f"\n=== SCRAP STATUS ({month_year}) ===\n")
    if completed:
        print("✅ Completed:")
        for scrap in completed:
            print(
                f"   {scrap.pagina_web:8} | {scrap.ciudad:10} | {scrap.operacion:6} | {scrap.producto:12} | "
                f"last: {scrap.last_run or '-'} | next: {scrap.next_run or '-'}"
            )
        print()

    if running:
        print("🏃 Currently running:")
        for scrap in running:
            print(
                f"   {scrap.pagina_web:8} | {scrap.ciudad:10} | {scrap.operacion:6} | {scrap.producto:12} | "
                f"last: {scrap.last_run or '-'} | next: {scrap.next_run or '-'}"
            )
        print()

    if queued:
        print("⏳ Queued:")
        for scrap in queued:
            print(
                f"   {scrap.pagina_web:8} | {scrap.ciudad:10} | {scrap.operacion:6} | {scrap.producto:12} | "
                f"last: {scrap.last_run or '-'} | next: {scrap.next_run or '-'}"
            )
        print()

    if never_run:
        print("🆕 Never run:")
        for scrap in never_run:
            print(
                f"   {scrap.pagina_web:8} | {scrap.ciudad:10} | {scrap.operacion:6} | {scrap.producto:12} | "
                f"next: {scrap.next_run or '-'}"
            )
        print()

    if scrap_of_month:
        print("🌟 Scrap of the Month:")
        print(
            f"   {scrap_of_month.pagina_web:8} | {scrap_of_month.ciudad:10} | "
            f"{scrap_of_month.operacion:6} | {scrap_of_month.producto:12} | "
            f"records: {scrap_of_month.records} | month: {scrap_of_month.scrap_of_month}"
        )
    else:
        print("No scraps found.")


if __name__ == "__main__":
    main()
