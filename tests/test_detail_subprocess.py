import sys
from pathlib import Path

# Ensure project root in path for namespace packages
sys.path.append(str(Path(__file__).resolve().parents[1]))

import orchestrator.advanced_orchestrator as ao


def test_start_scraper_subprocess_queues_detail(monkeypatch, tmp_path):
    """start_scraper_subprocess should queue detail scraper with urls file."""

    # Instanciar orquestador
    orch = ao.AdvancedOrchestrator()

    scrap = {"id": "1", "website": "inm24", "url": "http://example.com"}

    # Path de salida controlado
    output_csv = tmp_path / "base.csv"
    monkeypatch.setattr(orch.registry, "get_output_path", lambda s: output_csv)
    monkeypatch.setattr(orch.registry, "update_scrap_execution", lambda *a, **k: None)

    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append(cmd)
            self.returncode = 0

        def wait(self):
            return 0

    # Simular subprocess.Popen
    monkeypatch.setattr(ao.subprocess, "Popen", FakePopen)

    # Ejecutar hilos inmediatamente
    class ImmediateThread:
        def __init__(self, target, daemon=None):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(ao.threading, "Thread", ImmediateThread)

    orch.start_scraper_subprocess(scrap)

    # Debe haber una llamada para el base y otra para el detalle
    assert len(calls) == 2

    # El comando del scraper de detalle debe contener --urls-file con el path generado
    detail_cmd = calls[1]
    assert any(part == f"--urls-file={output_csv}" for part in detail_cmd)

