"""
USDA FoodData Central "SR Legacy" (2018) generic-food client.

Thin wrapper over the generic table client in src/food_tables.py (kept so that
existing imports keep working). Public-domain data (U.S. Department of
Agriculture, Agricultural Research Service, fdc.nal.usda.gov); src/usda_db.json is
built by scripts/parse_usda.py. Carbohydrates are AVAILABLE carbs (carbs by
difference minus fiber), matching UK/EU/Mexico labels.
"""

from src import food_tables
from src.food_tables import translate_query  # noqa: F401  (re-export)

_TABLE = food_tables.get_table('usda')


def _load_db() -> list[dict]:
    return _TABLE.load()


def _usda_to_product(entry: dict) -> dict:
    """Convert a usda_db.json entry to the shape of api_client.format_product()."""
    return _TABLE.to_product(entry)


def search_by_name(query: str, page_size: int = 20, cc: str | None = None) -> list[dict]:
    """Search USDA foods; every word of the (translated) query must appear."""
    return _TABLE.search_by_name(query, page_size, cc)


def fuzzy_usda(query: str, limit: int = 10, cc: str | None = None) -> list[dict]:
    """Typo-tolerant search: every query word must closely match a name word."""
    return _TABLE.fuzzy(query, limit, cc)


def usda_by_category(category: str, limit: int = 400) -> list[dict]:
    """USDA products of one food category."""
    return _TABLE.by_category(category, limit)


def search_by_barcode(_barcode: str) -> dict | None:
    return None
