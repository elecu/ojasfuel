"""Shared UI helpers for OjasFuel pages."""

import re

from src.i18n import t

# Nutrient display keys whose i18n key is not simply nutrient_<slug>.
_SPECIAL_KEYS = {
    'Energy (kcal)': 'nutrient_energy_kcal',
    'Energy (kJ)': 'nutrient_energy_kj',
}


def _slug(nutrient_key: str) -> str:
    base = nutrient_key.split(' (')[0].strip().lower()
    return re.sub(r'[^a-z0-9]+', '_', base).strip('_')


def nutrient_i18n_key(nutrient_key: str) -> str:
    return _SPECIAL_KEYS.get(nutrient_key) or f'nutrient_{_slug(nutrient_key)}'


def tn(nutrient_key: str) -> str:
    """Translated nutrient label (with unit); falls back to the English name."""
    key = nutrient_i18n_key(nutrient_key)
    txt = t(key)
    return nutrient_key if txt == key else txt


def tn_short(nutrient_key: str) -> str:
    """Translated label without the trailing unit."""
    return tn(nutrient_key).split(' (')[0]


def nutrient_unit(nutrient_key: str) -> str:
    return nutrient_key.rsplit('(', 1)[-1].rstrip(')') if '(' in nutrient_key else ''


def fmt_value(value) -> str:
    """Round a nutrient value sensibly for display."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if v == 0:
        return '0'
    a = abs(v)
    if a >= 100:
        return f'{v:.0f}'
    if a >= 10:
        return f'{v:.1f}'.rstrip('0').rstrip('.')
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def parse_serving_grams(product: dict) -> tuple[float | None, str]:
    """
    Serving size in grams from a product dict.
    Returns (grams, display_label) or (None, '').
    """
    srv_str = product.get('serving_size', '') or ''
    m = re.search(r'\(?\s*(\d+(?:[.,]\d+)?)\s*g\b\s*\)?', srv_str, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(',', '.')), srv_str

    raw = product.get('_raw', {}) or {}
    qty = raw.get('serving_quantity')
    if qty:
        try:
            g = float(qty)
            return g, (srv_str or f'{g}g')
        except (TypeError, ValueError):
            pass

    smae_g = product.get('_smae_portion_g')
    if smae_g:
        try:
            return float(smae_g), (srv_str or f'{smae_g} g')
        except (TypeError, ValueError):
            pass
    return None, ''


def diet_source_label(source: str) -> str:
    """Human label for where a diet classification came from."""
    if source == 'off':
        return t('diet_source_off')
    if source == 'smae':
        return t('diet_source_smae')
    if source == 'ingredients':
        return t('diet_source_ingredients')
    return t('diet_source_none')
