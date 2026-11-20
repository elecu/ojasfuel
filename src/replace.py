"""Pure logic for the "replace a food" flow (no Streamlit imports)."""

import re

from src.alternatives import equiv_grams_for_macro

MATCH_BASES = {
    'kcal': 'Energy (kcal)',
    'carbs': 'Carbohydrates (g)',
    'protein': 'Protein (g)',
    'fat': 'Fat (g)',
}
_MACROS = ('protein', 'carbs', 'fat')
_NUTR_KEY = {'kcal': 'Energy (kcal)', 'protein': 'Protein (g)',
             'carbs': 'Carbohydrates (g)', 'fat': 'Fat (g)'}
_KCAL_PER_G = {'protein': 4.0, 'carbs': 4.0, 'fat': 9.0}


def parse_serving_grams(product: dict) -> tuple[float | None, str]:
    """Serving size in grams from a product dict -> (grams, label) or (None, '')."""
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


def totals(product: dict, grams: float) -> dict:
    """kcal/protein/carbs/fat for `grams` of product (None when missing)."""
    nutr = product.get('nutrition', {}) or {}
    out = {}
    for k, nk in _NUTR_KEY.items():
        v = nutr.get(nk)
        out[k] = None if v is None else round(v * grams / 100, 2)
    return out


def level_for(similarity: int) -> str:
    if similarity >= 85:
        return 'very'
    if similarity >= 70:
        return 'similar'
    if similarity >= 50:
        return 'partial'
    return 'low'


def _eff_kcal(tot: dict) -> float:
    if tot.get('kcal') is not None:
        return tot['kcal']
    return sum(_KCAL_PER_G[m] * (tot.get(m) or 0) for m in _MACROS)


def equivalent(orig: dict, alt: dict, grams: float, basis: str) -> dict | None:
    """Grams of `alt` that match `grams` of `orig` on `basis`, plus similarity."""
    if basis not in MATCH_BASES:
        return None
    o_n, a_n = orig.get('nutrition', {}) or {}, alt.get('nutrition', {}) or {}
    alt_grams = equiv_grams_for_macro(o_n, a_n, MATCH_BASES[basis], grams)
    if alt_grams is None:
        return None

    srv_g, srv_label = parse_serving_grams(alt)
    portions = round(alt_grams / srv_g, 1) if srv_g and srv_g > 0 else None

    o_t, a_t = totals(orig, grams), totals(alt, alt_grams)
    diffs = {}
    for k in ('kcal',) + _MACROS:
        o_v = o_t[k] if k != 'kcal' else _eff_kcal(o_t)
        a_v = a_t[k] if k != 'kcal' else _eff_kcal(a_t)
        if k != 'kcal' and (o_t[k] is None or a_t[k] is None):
            diffs[k] = None
            continue
        diffs[k] = round(a_v - o_v, 2)

    D = 0.0
    for m in _MACROS:
        if diffs[m] is not None:
            D += _KCAL_PER_G[m] * abs(diffs[m])
    if basis != 'kcal':
        D += abs(diffs['kcal'])
    sim = round(100 * max(0.0, 1 - D / max(_eff_kcal(o_t), 1)))
    return {
        'basis': basis, 'grams': grams, 'alt_grams': alt_grams,
        'alt_portions': portions, 'portion_label': srv_label if portions else '',
        'portion_grams': srv_g if portions else None,
        'orig_totals': o_t, 'alt_totals': a_t, 'diffs': diffs,
        'similarity': sim, 'level': level_for(sim),
    }


def main_differences(eq: dict, k: int = 2) -> list[tuple[str, float]]:
    """Largest macro differences by energy impact: [(macro, delta_g), ...]."""
    items = []
    for m in _MACROS:
        d = eq['diffs'].get(m)
        if d is None or round(d) == 0:
            continue
        items.append((m, d))
    items.sort(key=lambda x: _KCAL_PER_G[x[0]] * abs(x[1]), reverse=True)
    return items[:k]


def rank_by_similarity(orig: dict, candidates: list[dict], grams: float,
                       basis: str) -> list[tuple[dict, dict]]:
    out = []
    for c in candidates:
        eq = equivalent(orig, c, grams, basis)
        if eq is not None:
            out.append((c, eq))
    out.sort(key=lambda x: -x[1]['similarity'])
    return out
