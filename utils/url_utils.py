"""Utility helpers for working with URL columns in CSV rows."""
from typing import Any, Dict, Iterable


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
