"""
OpenFoodFacts API client.
Mirrors the patterns from test_search.py.
"""

import functools
import os
import requests
import openfoodfacts

from src.barcode import barcode_variants, normalize_barcode

_api = openfoodfacts.API(user_agent="OjasFuel/1.0")

# Map OFF countries_tags value → 2-letter country code for SDK subdomain
_CC_MAP = {
    'en:united-kingdom': 'gb',
    'en:spain': 'es',
    'en:france': 'fr',
    'en:germany': 'de',
    'en:italy': 'it',
    'en:united-states': 'us',
    'en:mexico': 'mx',
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
        return openfoodfacts.API(user_agent="OjasFuel/1.0", country=cc)
    return _api


def country_tags_to_cc(tags: list) -> str | None:
    """Convert a list of countries_tags to a single OFF country code."""
    for tag in (tags or []):
        cc = _CC_MAP.get(tag)
        if cc:
            return cc
    return None

# Nutrition fields: display_name → OFF nutriment key (per 100 g).
# OFF stores every *_100g value in grams except energy (kcal / kJ),
# so mg / µg display units need a conversion factor.
NUTRITION_FIELDS = {
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
    'Vitamin B3 (mg)': 'vitamin-pp_100g',
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

# grams → display unit
_UNIT_FACTOR = {'mg': 1000.0, 'µg': 1_000_000.0}


def _display_unit(display_name: str) -> str:
    return display_name.rsplit('(', 1)[-1].rstrip(')') if '(' in display_name else ''


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


def extract_nutrition(nutriments: dict) -> dict:
    """Convert an OFF `nutriments` dict into {display_name: value} in display units."""
    nutriments = nutriments or {}
    nutrition = {}
    for display_name, key in NUTRITION_FIELDS.items():
        val = nutriments.get(key)
        if val is None and display_name == 'Energy (kcal)':
            # Some products only have kJ → derive kcal
            kj = nutriments.get('energy-kj_100g')
            if kj is None and nutriments.get('energy_100g_unit', 'kJ') in ('kJ', None):
                kj = nutriments.get('energy_100g')
            if kj is not None:
                try:
                    val = float(kj) / 4.184
                except (TypeError, ValueError):
                    val = None
        if val is None:
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        num *= _UNIT_FACTOR.get(_display_unit(display_name), 1.0)
        nutrition[display_name] = round(num, 3)
    # Derive sodium from salt (and vice versa) when only one is present
    if 'Sodium (mg)' not in nutrition and 'Salt (g)' in nutrition:
        nutrition['Sodium (mg)'] = round(nutrition['Salt (g)'] / 2.5 * 1000, 1)
    return nutrition


def _brands_str(b) -> str:
    if isinstance(b, (list, tuple)):
        return ', '.join(str(x) for x in b if x)
    return b or ''


def _raw_ingredients_text(raw: dict) -> str:
    return (raw.get('ingredients_text') or raw.get('ingredients_text_en')
            or raw.get('ingredients_text_es') or '')


def _tags_to_text(tags) -> str:
    """['en:wheat-flour', 'en:sugar'] → 'wheat flour, sugar' (canonical English)."""
    words = []
    for t in tags or []:
        w = str(t).split(':', 1)[-1].replace('-', ' ').strip()
        if w and w not in words:
            words.append(w)
    return ', '.join(words)


def _ingredients_text(raw: dict) -> str:
    """Real ingredient text, else OFF's normalised ingredient tags.

    The search API returns no ingredient text but does return ingredients_tags,
    which lets lists and alternatives check allergies without a slow lookup.
    """
    return _raw_ingredients_text(raw) or _tags_to_text(raw.get('ingredients_tags'))


def format_product(raw: dict) -> dict:
    """Normalise a raw OFF product dict into the app's standard format."""
    product_id = raw.get('code') or raw.get('id') or 'N/A'
    return {
        'id': product_id,
        'name': raw.get('product_name') or raw.get('product_name_en') or raw.get('product_name_es') or 'Unknown',
        'brand': _brands_str(raw.get('brands', '')),
        'ingredients': _ingredients_text(raw),
        '_ingredients_from_tags': not _raw_ingredients_text(raw) and bool(raw.get('ingredients_tags')),
        # OFF's normalised ingredients (canonical English) — classified together
        # with the label text — and how well OFF could parse the list
        '_ingredients_tags_text': _tags_to_text(raw.get('ingredients_tags')),
        '_ingr_parsed_n': raw.get('ingredients_n'),
        '_ingr_unknown_n': raw.get('unknown_ingredients_n'),
        'allergens_tags': list(raw.get('allergens_tags') or []),
        'traces_tags': list(raw.get('traces_tags') or []),
        'image_url': raw.get('image_url') or raw.get('image_front_url', ''),
        'url': f'https://world.openfoodfacts.org/product/{product_id}',
        'nutrition': extract_nutrition(raw.get('nutriments', {})),
        'labels': _brands_str(raw.get('labels', '')),
        'categories': _brands_str(raw.get('categories', '')),
        'categories_tags': raw.get('categories_tags', []),
        'quantity': raw.get('quantity', ''),
        'serving_size': raw.get('serving_size', ''),
        'nutriscore': (raw.get('nutriscore_grade') or '').upper(),
        'countries_tags': raw.get('countries_tags', []),
        '_off_tags': _parse_off_tags(raw.get('ingredients_analysis_tags', [])),
        '_raw': raw,
    }


_SEARCH_HEADERS = {'User-Agent': 'OjasFuel/1.0'}
_SEARCH_FIELDS = ','.join([
    'code', 'product_name', 'brands', 'quantity', 'serving_size', 'labels',
    'ingredients_text', 'nutriments', 'ingredients_analysis_tags',
    'categories_tags', 'countries_tags', 'image_url', 'nutriscore_grade',
    'ingredients_tags', 'allergens_tags', 'traces_tags',
    'ingredients_n', 'unknown_ingredients_n',
])



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
    return {
        'is_vegan': is_vegan,
        'is_vegetarian': is_vegetarian,
        # OFF itself is unsure (incomplete ingredient list) → never claim vegan
        'vegan_uncertain': bool(tags_set & {'en:maybe-vegan', 'en:vegan-status-unknown'}),
        'vegetarian_uncertain': bool(tags_set & {'en:maybe-vegetarian', 'en:vegetarian-status-unknown'}),
    }


def _format_search_hit(hit: dict) -> dict:
    """Format a product from search.openfoodfacts.org /search response."""
    product = format_product(hit)
    # tag-derived ingredients are enough to classify, but the detail page
    # should still load the real label text
    product['_needs_full_load'] = not _raw_ingredients_text(hit)
    return product


def search_by_name(query: str, page_size: int = 20, country_code: str | None = None) -> list[dict]:
    """
    Search Open Food Facts by product name.
    country_code: 2-letter ISO code (e.g. 'mx', 'es') — uses country subdomain for better local coverage.
    Primary: search.openfoodfacts.org (passes cc param)
    Fallback: openfoodfacts SDK on country-specific subdomain
    """
    last_error = None
    params = {'q': query, 'page_size': page_size, 'fields': _SEARCH_FIELDS}
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


def _quote_tag(tag: str) -> str:
    return '"' + str(tag).replace('\\', '').replace('"', '') + '"'


# settings allergy key → OFF allergens_tags values
ALLERGEN_TAGS = {
    'allergies_nuts': ['en:nuts'],
    'allergies_peanuts': ['en:peanuts'],
    'allergies_soy': ['en:soybeans'],
    'allergies_mustard': ['en:mustard'],
    'allergies_sesame': ['en:sesame-seeds'],
    'allergies_gluten': ['en:gluten'],
}


def build_filter_query(category_tag: str, country_tags: list | None = None,
                       diet_tag: str | None = None, exclude_allergens: list | None = None) -> str:
    """Lucene-style query for search.openfoodfacts.org exact-tag filtering.

    e.g. categories_tags:"en:cocoa-and-hazelnuts-spreads"
         AND (countries_tags:"en:mexico") AND ingredients_analysis_tags:"en:vegan"
    """
    parts = [f'categories_tags:{_quote_tag(category_tag)}']
    if country_tags:
        parts.append('(' + ' OR '.join(f'countries_tags:{_quote_tag(c)}' for c in country_tags) + ')')
    if diet_tag:
        parts.append(f'ingredients_analysis_tags:{_quote_tag(diet_tag)}')
    q = ' AND '.join(parts)
    for a in exclude_allergens or []:
        q += f' AND NOT allergens_tags:{_quote_tag(a)} AND NOT traces_tags:{_quote_tag(a)}'
    return q


def search_filtered(category_tag: str, country_tags: list | None = None,
                    diet_tag: str | None = None, page_size: int = 30,
                    exclude_allergens: list | None = None, timeout: float = 8,
                    attempts: int = 2) -> list[dict]:
    """Products in an exact OFF category (optionally country/diet-filtered).

    Unlike search_by_name (free text), every hit really belongs to the category.
    Raises OFFConnectionError on network failure.
    """
    params = {'q': build_filter_query(category_tag, country_tags, diet_tag, exclude_allergens),
              'page_size': page_size, 'fields': _SEARCH_FIELDS}
    last_error = None
    for _ in range(max(1, attempts)):
        try:
            resp = requests.get('https://search.openfoodfacts.org/search', params=params,
                                headers=_SEARCH_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return [_format_search_hit(h) for h in (resp.json().get('hits') or [])]
        except Exception as e:  # noqa: BLE001 — retried once, then surfaced
            last_error = e
    raise OFFConnectionError(f'Filtered search failed: {last_error}')


class OFFConnectionError(Exception):
    """Raised when Open Food Facts could not be reached (network/timeout/5xx)."""


_PROD_URL = 'https://world.openfoodfacts.org'
_STAGING_URL = 'https://world.openfoodfacts.net'


def _secret(name: str) -> str | None:
    val = os.environ.get(name)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(name)  # type: ignore[no-any-return]
    except Exception:
        return None


def _off_base_url() -> str:
    return _STAGING_URL if (_secret('OFF_ENV') or '').lower() == 'staging' else _PROD_URL


# off nutriment key (without _100g) → display unit
_WRITE_UNITS = {k[:-5]: _display_unit(d) or 'g' for d, k in NUTRITION_FIELDS.items()}
_WRITE_UNITS['energy-kcal'] = 'kcal'
_WRITE_UNITS['energy-kj'] = 'kJ'


def _nutrition_to_write_fields(nutrition: dict) -> dict:
    """Convert {'nutriment_sodium_100g': 400 (mg)} → OFF write params."""
    out = {}
    for key, val in (nutrition or {}).items():
        if val is None or not str(val).strip():
            continue
        name = key
        if name.startswith('nutriment_'):
            name = name[len('nutriment_'):]
        if name.endswith('_100g'):
            name = name[:-5]
        try:
            num = float(str(val).replace(',', '.'))
        except ValueError:
            continue
        unit = _WRITE_UNITS.get(name, 'g')
        out[f'nutriment_{name}'] = f'{num:g}'
        out[f'nutriment_{name}_unit'] = unit
    if out:
        out['nutrition_data_per'] = '100g'
    return out


def _json_or_none(resp):
    try:
        return resp.json()
    except Exception:
        return None


def submit_product(
    barcode: str,
    name: str,
    brand: str = '',
    quantity: str = '',
    ingredients: str = '',
    countries: str = '',
    nutrition: dict | None = None,
    photo_bytes: bytes | None = None,
) -> dict:
    """Submit a product to Open Food Facts.

    nutrition: keys like 'nutriment_sodium_100g', values in the DISPLAY unit
    (kcal, kJ, g, mg, µg); converted to OFF's nutriment_<n> + _unit format.
    Credentials: OFF_USER / OFF_PASSWORD (env or st.secrets), else anonymous off/off.
    OFF_ENV=staging targets world.openfoodfacts.net.

    Returns {'ok': bool, 'error': str|None, 'photo_ok': bool|None, 'url': str}.
    """
    base = _off_base_url()
    code = normalize_barcode(barcode)
    user = _secret('OFF_USER') or 'off'
    password = _secret('OFF_PASSWORD') or 'off'
    staging = base == _STAGING_URL
    http_auth = ('off', 'off') if staging else None
    headers = {'User-Agent': 'OjasFuel/1.0'}
    creds = {'user_id': user, 'password': password}
    result = {'ok': False, 'error': None, 'photo_ok': None, 'url': f'{base}/product/{code}'}

    data = {'code': code, 'product_name': name.strip(), **creds}
    if brand.strip():
        data['brands'] = brand.strip()
    if quantity.strip():
        data['quantity'] = quantity.strip()
    if ingredients.strip():
        data['ingredients_text'] = ingredients.strip()
    if countries.strip():
        data['countries'] = countries.strip()
    data.update(_nutrition_to_write_fields(nutrition or {}))

    try:
        resp = requests.post(f'{base}/cgi/product_jqm2.pl', data=data, timeout=20,
                             headers=headers, auth=http_auth)
    except requests.RequestException as exc:
        result['error'] = f'Connection error: {exc}'
        return result
    body = _json_or_none(resp)
    if body is None:
        result['error'] = f'Unexpected response from Open Food Facts (HTTP {resp.status_code}, not JSON)'
        return result
    if not resp.ok or body.get('status') != 1:
        result['error'] = body.get('status_verbose') or f'HTTP {resp.status_code}'
        return result
    result['ok'] = True

    if photo_bytes:
        try:
            presp = requests.post(
                f'{base}/cgi/product_image_upload.pl',
                data={'code': code, 'imagefield': 'front_en', **creds},
                files={'imgupload_front_en': ('front.jpg', photo_bytes, 'image/jpeg')},
                timeout=40, headers=headers, auth=http_auth,
            )
            pbody = _json_or_none(presp)
            result['photo_ok'] = bool(presp.ok and pbody is not None
                                      and pbody.get('status') in ('status ok', 1, 'ok'))
        except requests.RequestException:
            result['photo_ok'] = False

    return result


def _fetch_barcode_once(code: str) -> dict | None:
    """GET one barcode. None = not found. Raises requests.RequestException on network trouble."""
    resp = requests.get(
        f'https://world.openfoodfacts.org/api/v2/product/{code}.json',
        headers=_SEARCH_HEADERS, timeout=(6, 12),
    )
    if resp.status_code == 404:
        body = _json_or_none(resp)
        if body is not None:
            return None
    if resp.status_code >= 500 or resp.status_code == 429:
        raise requests.HTTPError(f'HTTP {resp.status_code}')
    body = _json_or_none(resp)
    if body is None:
        raise requests.RequestException('non-JSON response')
    if body.get('status') == 1 and isinstance(body.get('product'), dict):
        prod = body['product']
        prod.setdefault('code', code)
        return prod
    return None


def search_by_barcode(barcode: str) -> dict | None:
    """Look up a product by barcode (tries UPC/EAN variants).

    Returns a formatted product, None if genuinely not found, and raises
    OFFConnectionError if every attempt failed due to network problems.
    """
    variants = barcode_variants(barcode)
    net_failures = 0
    attempts = 0
    last_exc = None
    for code in variants:
        for attempt in range(2):  # 1 retry on network error
            attempts += 1
            try:
                raw = _fetch_barcode_once(code)
                break
            except requests.RequestException as exc:
                last_exc = exc
                raw = None
                if attempt == 1:
                    net_failures += 1
        else:
            continue
        if raw:
            return format_product(raw)
    if variants and net_failures == len(variants):
        raise OFFConnectionError(str(last_exc))
    return None
