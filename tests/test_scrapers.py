import sys
from pathlib import Path

# Asegurar que el directorio del proyecto esté en sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scrapers.inm24 import Inmuebles24ProfessionalScraper
from scrapers.cyt import CasasTerrenosProfessionalScraper

def test_inm24_driver_config():
    scraper = Inmuebles24ProfessionalScraper()
    config = scraper.create_professional_driver()
    assert config["headless"] is True
    assert "--no-sandbox" in config["chromium_arg"]


def test_cyt_driver_config():
    scraper = CasasTerrenosProfessionalScraper(headless=False)
    config = scraper.create_professional_driver()
    assert config["headless"] is False
    assert "--disable-gpu" in config["chromium_arg"]
