"""
OpenFoodFacts API client.
Mirrors the patterns from test_search.py.
"""

import functools
import requests
import openfoodfacts

_api = openfoodfacts.API(user_agent="SMAEUK/1.0")

# Map OFF countries_tags value → 2-letter country code for SDK subdomain
_CC_MAP = {
    'en:united-kingdom': 'gb',
    'en:spain': 'es',
    'en:france': 'fr',
    'en:germany': 'de',
    'en:italy': 'it',
    'en:united-states': 'us',
    'en:mexico': 'mx',
    'en:argentina': 'ar',
    'en:colombia': 'co',
    'en:chile': 'cl',
    'en:peru': 'pe',
    'en:brazil': 'br',
    'en:canada': 'ca',
    'en:australia': 'au',
    'en:netherlands': 'nl',
    'en:belgium': 'be',
    'en:switzerland': 'ch',
    'en:portugal': 'pt',
    'en:poland': 'pl',
}


@functools.lru_cache(maxsize=32)
def _get_api(cc: str | None) -> openfoodfacts.API:
    """Return an API instance scoped to the given country code (or world if None)."""
    if cc:
        return openfoodfacts.API(user_agent="SMAEUK/1.0", country=cc)
    return _api


def country_tags_to_cc(tags: list) -> str | None:
    """Convert a list of countries_tags to a single OFF country code."""
    for tag in (tags or []):
        cc = _CC_MAP.get(tag)
        if cc:
            return cc
    return None

# Nutrition fields: display_name → OFF field key
NUTRITION_FIELDS = {
    'Energy (kcal)': 'energy_100g',
    'Energy (kJ)': 'energy-kj_100g',
    'Protein (g)': 'proteins_100g',
    'Fat (g)': 'fat_100g',
    'Saturated Fat (g)': 'saturated-fat_100g',
    'Carbohydrates (g)': 'carbohydrates_100g',
    'Sugars (g)': 'sugars_100g',
    'Fiber (g)': 'fiber_100g',
    'Sodium (mg)': 'sodium_100g',
    'Salt (g)': 'salt_100g',
    'Potassium (mg)': 'potassium_100g',
    'Calcium (mg)': 'calcium_100g',
    'Iron (mg)': 'iron_100g',
    'Magnesium (mg)': 'magnesium_100g',
    'Phosphorus (mg)': 'phosphorus_100g',
    'Zinc (mg)': 'zinc_100g',
    'Manganese (mg)': 'manganese_100g',
    'Copper (mg)': 'copper_100g',
    'Selenium (µg)': 'selenium_100g',
    'Iodine (µg)': 'iodine_100g',
    'Vitamin A (µg)': 'vitamin-a_100g',
    'Vitamin B1 (mg)': 'vitamin-b1_100g',
    'Vitamin B2 (mg)': 'vitamin-b2_100g',
    'Vitamin B3 (mg)': 'vitamin-b3_100g',
    'Vitamin B6 (mg)': 'vitamin-b6_100g',
    'Vitamin B9 (µg)': 'vitamin-b9_100g',
    'Vitamin B12 (µg)': 'vitamin-b12_100g',
    'Vitamin C (mg)': 'vitamin-c_100g',
    'Vitamin D (µg)': 'vitamin-d_100g',
    'Vitamin E (mg)': 'vitamin-e_100g',
    'Vitamin K (µg)': 'vitamin-k_100g',
    'Cholesterol (mg)': 'cholesterol_100g',
    'Alcohol (g)': 'alcohol_100g',
    'Caffeine (mg)': 'caffeine_100g',
}

NUTRITION_GROUPS = {
    'Macronutrients': [
        'Energy (kcal)', 'Energy (kJ)', 'Protein (g)', 'Fat (g)',
        'Saturated Fat (g)', 'Carbohydrates (g)', 'Sugars (g)',
        'Fiber (g)', 'Cholesterol (mg)', 'Alcohol (g)',
    ],
    'Minerals': [
        'Sodium (mg)', 'Salt (g)', 'Potassium (mg)', 'Calcium (mg)',
        'Iron (mg)', 'Magnesium (mg)', 'Phosphorus (mg)', 'Zinc (mg)',
        'Manganese (mg)', 'Copper (mg)', 'Selenium (µg)', 'Iodine (µg)',
    ],
    'Vitamins': [
        'Vitamin A (µg)', 'Vitamin B1 (mg)', 'Vitamin B2 (mg)',
        'Vitamin B3 (mg)', 'Vitamin B6 (mg)', 'Vitamin B9 (µg)',
        'Vitamin B12 (µg)', 'Vitamin C (mg)', 'Vitamin D (µg)',
        'Vitamin E (mg)', 'Vitamin K (µg)',
    ],
    'Other': ['Caffeine (mg)'],
}


def _get_nutrient(product: dict, field: str):
    """Try direct access then nested under nutriments."""
    val = product.get(field)
    if val is not None:
        return val
    nutriments = product.get('nutriments', {})
    return nutriments.get(field)


def format_product(raw: dict) -> dict:
    """Normalise a raw OFF product dict into the app's standard format."""
    product_id = raw.get('id') or raw.get('code', 'N/A')
    nutrition = {}
    for display_name, field_key in NUTRITION_FIELDS.items():
        val = _get_nutrient(raw, field_key)
        if val is not None:
            try:
                nutrition[display_name] = float(val)
            except (TypeError, ValueError):
                pass

    return {
        'id': product_id,
        'name': raw.get('product_name') or raw.get('product_name_en', 'Unknown'),
        'brand': raw.get('brands', ''),
        'ingredients': raw.get('ingredients_text') or raw.get('ingredients_text_en', ''),
        'image_url': raw.get('image_url') or raw.get('image_front_url', ''),
        'url': f'https://world.openfoodfacts.org/product/{product_id}',
        'nutrition': nutrition,
        'labels': raw.get('labels', ''),
        'categories': raw.get('categories', ''),
        'quantity': raw.get('quantity', ''),
        'serving_size': raw.get('serving_size', ''),
        'nutriscore': raw.get('nutriscore_grade', '').upper(),
        'countries_tags': raw.get('countries_tags', []),
        '_raw': raw,
    }


_SEARCH_HEADERS = {'User-Agent': 'SMAEUK/1.0'}

_NUTRIMENT_MAP = {
    'Energy (kcal)': 'energy-kcal_100g',
    'Energy (kJ)': 'energy-kj_100g',
    'Protein (g)': 'proteins_100g',
    'Fat (g)': 'fat_100g',
    'Saturated Fat (g)': 'saturated-fat_100g',
    'Carbohydrates (g)': 'carbohydrates_100g',
    'Sugars (g)': 'sugars_100g',
    'Fiber (g)': 'fiber_100g',
    'Sodium (mg)': 'sodium_100g',
    'Salt (g)': 'salt_100g',
    'Potassium (mg)': 'potassium_100g',
    'Calcium (mg)': 'calcium_100g',
    'Iron (mg)': 'iron_100g',
    'Magnesium (mg)': 'magnesium_100g',
    'Phosphorus (mg)': 'phosphorus_100g',
    'Zinc (mg)': 'zinc_100g',
    'Manganese (mg)': 'manganese_100g',
    'Copper (mg)': 'copper_100g',
    'Selenium (µg)': 'selenium_100g',
    'Iodine (µg)': 'iodine_100g',
    'Vitamin A (µg)': 'vitamin-a_100g',
    'Vitamin B1 (mg)': 'vitamin-b1_100g',
    'Vitamin B2 (mg)': 'vitamin-b2_100g',
    'Vitamin B3 (mg)': 'vitamin-b3_100g',
    'Vitamin B6 (mg)': 'vitamin-b6_100g',
    'Vitamin B9 (µg)': 'vitamin-b9_100g',
    'Vitamin B12 (µg)': 'vitamin-b12_100g',
    'Vitamin C (mg)': 'vitamin-c_100g',
    'Vitamin D (µg)': 'vitamin-d_100g',
    'Vitamin E (mg)': 'vitamin-e_100g',
    'Vitamin K (µg)': 'vitamin-k_100g',
    'Cholesterol (mg)': 'cholesterol_100g',
    'Alcohol (g)': 'alcohol_100g',
    'Caffeine (mg)': 'caffeine_100g',
}


def _parse_off_tags(tags: list[str]) -> dict:
    """Parse ingredients_analysis_tags into vegan/vegetarian booleans."""
    tags_set = set(tags or [])
    is_vegan = None
    is_vegetarian = None
    if 'en:vegan' in tags_set:
        is_vegan = True
        is_vegetarian = True
    elif 'en:non-vegan' in tags_set:
        is_vegan = False
    if 'en:vegetarian' in tags_set:
        is_vegetarian = True
    elif 'en:non-vegetarian' in tags_set:
        is_vegetarian = False
    return {'is_vegan': is_vegan, 'is_vegetarian': is_vegetarian}


def _format_search_hit(hit: dict) -> dict:
    """Format a product from search.openfoodfacts.org /search response."""
    nutriments = hit.get('nutriments', {})
    nutrition = {}
    for display_name, key in _NUTRIMENT_MAP.items():
        val = nutriments.get(key)
        if val is None:
            val = nutriments.get(key.replace('_100g', ''))
        if val is not None:
            try:
                nutrition[display_name] = float(val)
            except (TypeError, ValueError):
                pass

    product_id = hit.get('code') or hit.get('id', 'N/A')
    off_tags = _parse_off_tags(hit.get('ingredients_analysis_tags', []))

    return {
        'id': product_id,
        'name': hit.get('product_name') or hit.get('product_name_en', 'Unknown'),
        'brand': hit.get('brands', ''),
        'ingredients': '',  # not available from search API — fetched on Detail load
        'image_url': hit.get('image_url') or hit.get('image_front_url', ''),
        'url': f'https://world.openfoodfacts.org/product/{product_id}',
        'nutrition': nutrition,
        'labels': hit.get('labels', ''),
        'categories': hit.get('categories', ''),
        'quantity': hit.get('quantity', ''),
        'serving_size': hit.get('serving_size', ''),
        'nutriscore': (hit.get('nutriscore_grade') or '').upper(),
        'countries_tags': hit.get('countries_tags', []),
        '_off_tags': off_tags,
        '_needs_full_load': True,
        '_raw': hit,
    }


def search_by_name(query: str, page_size: int = 20, country_code: str | None = None) -> list[dict]:
    """
    Search Open Food Facts by product name.
    country_code: 2-letter ISO code (e.g. 'mx', 'es') — uses country subdomain for better local coverage.
    Primary: search.openfoodfacts.org (passes cc param)
    Fallback: openfoodfacts SDK on country-specific subdomain
    """
    last_error = None
    params = {'q': query, 'page_size': page_size}
    if country_code:
        params['cc'] = country_code  # honoured by search API when supported

    # Primary: modern search API
    for attempt in range(2):
        try:
            resp = requests.get(
                'https://search.openfoodfacts.org/search',
                params=params,
                headers=_SEARCH_HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            hits = resp.json().get('hits', [])
            if hits is not None:
                return [_format_search_hit(h) for h in hits]
        except Exception as e:
            last_error = e

    # Fallback: country-specific SDK instance (uses [cc].openfoodfacts.org)
    try:
        api_instance = _get_api(country_code)
        results = api_instance.product.text_search(query, page_size=page_size)
        products = results.get('products', [])
        return [format_product(p) for p in products]
    except Exception as e:
        last_error = e

    raise RuntimeError(f"Search failed (both endpoints unavailable): {last_error}")


def search_by_barcode(barcode: str) -> dict | None:
    """Look up a product by EAN/UPC barcode. Returns formatted product or None."""
    barcode = barcode.strip()
    try:
        result = _api.product.get(barcode)
        if result and isinstance(result, dict):
            # SDK returns the product dict directly (not wrapped in status/product)
            return format_product(result)
    except Exception:
        pass
    return None
