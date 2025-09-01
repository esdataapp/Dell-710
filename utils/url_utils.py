"""Utility helpers for working with URL columns in CSV rows."""

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List


def extract_url_column(row: Any) -> str:
    """Return the URL value from a CSV row.

    The function is tolerant to different capitalizations of the column name.
    If no matching header is found, it falls back to the element at index 4.

    Args:
        row: A mapping produced by ``csv.DictReader`` or a sequence from
            ``csv.reader``.

    Returns:
        The URL string if found, otherwise an empty string.
    """
    if isinstance(row, dict):
        for key in ("URL", "Url", "url"):
            if key in row and row[key]:
                return str(row[key]).strip()
        try:
            values: Iterable[Any] = row.values()
            value_list = list(values)
            if len(value_list) > 4:
                return str(value_list[4]).strip()
        except Exception:
            pass
    else:
        try:
            if len(row) > 4:
                return str(row[4]).strip()
        except Exception:
            pass
    return ""


def load_urls_from_csv(path: str) -> List[Dict[str, str]]:
    """Read URL records from a CSV file.

    The CSV is expected to contain a header row. All columns are returned for
    each entry, but rows without a URL value are skipped.
    The URL column name is resolved using :func:`extract_url_column`
    to allow flexible headers.

    Args:
        path: Path to the CSV file.

    Returns:
        A list of dictionaries representing the rows in the CSV file that
        contain a URL.
    """

    records: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if extract_url_column(row):
                records.append(row)

    return records


def load_urls_for_site(urls_dir: str, site: str) -> List[str]:
    """Load all URLs for a given site from CSV files in a directory.

    Args:
        urls_dir: Directory containing CSV files with URL records.
        site: Name of the site to filter by (matches ``PaginaWeb`` column).

    Returns:
        A list of URL strings for the requested site. If the directory does not
        exist, an empty list is returned.
    """

    directory = Path(urls_dir)
    if not directory.exists():
        return []

    site_lower = site.lower()
    urls: List[str] = []

    for csv_file in directory.glob("*.csv"):
        try:
            rows = load_urls_from_csv(str(csv_file))
        except Exception:
            continue
        for row in rows:
            if (row.get("PaginaWeb") or "").strip().lower() == site_lower:
                url_val = extract_url_column(row)
                if url_val:
                    urls.append(url_val)

    return urls
