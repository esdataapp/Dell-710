import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

# Asegurar que el directorio raíz del proyecto está en sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from scrapers.inm24 import Inmuebles24ProfessionalScraper


def test_operation_type_matches_cli_option():
    scraper = Inmuebles24ProfessionalScraper(operation_type='renta')
    # Establecer start_time para evitar dependencias en scrape_pages original
    scraper.start_time = datetime.now()

    with patch.object(Inmuebles24ProfessionalScraper, 'scrape_pages', return_value=(0, 0)), \
         patch.object(Inmuebles24ProfessionalScraper, 'save_results', return_value='dummy.csv'):
        results = scraper.run()

    assert results['operation_type'] == 'renta'
