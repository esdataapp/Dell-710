import csv
import sys
import logging
from pathlib import Path

# Asegurar que el proyecto esté en el PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from orchestrator import advanced_orchestrator as ao
from utils.enhanced_scraps_registry import EnhancedScrapsRegistry


class DummyOrchestrator(ao.AdvancedOrchestrator):
    def __init__(self):
        # Inicialización mínima para pruebas
        self.registry = EnhancedScrapsRegistry()
        self.logger = logging.getLogger("DummyOrchestrator")


def _create_csv(csv_path):
    header = [
        "PaginaWeb",
        "Ciudad",
        "Operacion",
        "ProductoPaginaWeb",
        "URL",
        "Status",
        "LastRun",
        "NextRun",
        "ScrapOfMonth",
        "Records",
    ]
    rows = [
        ("TestSite", "City", "B", "ProdY", "http://a.com", "pending", "", "", "", ""),
        ("TestSite", "City", "A", "ProdZ", "http://b.com", "pending", "", "", "", ""),
        ("TestSite", "City", "C", "ProdX", "http://c.com", "pending", "", "", "", ""),
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_get_scraps_in_csv_order(tmp_path):
    csv_file = tmp_path / "test_urls.csv"
    _create_csv(csv_file)

    orchestrator = DummyOrchestrator()
    orchestrator.registry.csv_urls_dir = tmp_path

    scraps = orchestrator.get_scraps_for_website("TestSite")

    assert [s["csv_row"] for s in scraps] == [1, 2, 3]
    assert [s["url"] for s in scraps] == [
        "http://a.com",
        "http://b.com",
        "http://c.com",
    ]
    assert [s["operacion"] for s in scraps] == ["B", "A", "C"]
