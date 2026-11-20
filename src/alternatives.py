"""Alternative-product finder and macro-matching helpers (shared with Equivalents page)."""

import time

from src.verdict import verdict

# ── Match priority config ─────────────────────────────────────────────────────
MATCH_MODES = {
    'cal_only':          ('match_cal_only',          [('Energy (kcal)', 1.0)]),
    'cal_protein':       ('match_cal_protein',        [('Energy (kcal)', 0.5), ('Protein (g)', 0.5)]),
    'cal_protein_carbs': ('match_cal_protein_carbs',  [('Energy (kcal)', 0.4), ('Protein (g)', 0.4), ('Carbohydrates (g)', 0.2)]),
    'protein_carbs':     ('match_protein_carbs',      [('Protein (g)', 0.5), ('Carbohydrates (g)', 0.5)]),
    'carbs_only':        ('match_carbs_only',         [('Carbohydrates (g)', 1.0)]),
    'protein_priority':  ('match_protein_priority',   [('Protein (g)', 0.7), ('Energy (kcal)', 0.3)]),
}


def macro_score(orig: dict, cand: dict, weights: list[tuple[str, float]]) -> tuple[float, dict]:
    score = 0.0
    diffs = {}
    for macro, w in weights:
        o = orig.get(macro, 0) or 0
        c = cand.get(macro, 0) or 0
        rel = abs(c - o) / max(o, 1)
        score += w * rel
        diffs[macro] = (c - o) / max(o, 1) * 100
    return score, diffs


def passes_threshold(orig: dict, cand: dict, macros: list[tuple[str, float]], threshold: float) -> bool:
    for macro, _ in macros:
        o = orig.get(macro, 0) or 0
        c = cand.get(macro, 0) or 0
        if o == 0:
            continue
        if abs(c - o) / o > threshold:
            return False
    return True


def equiv_grams_for_macro(orig_nutr: dict, alt_nutr: dict, macro: str, orig_grams: float) -> float | None:
    """How many grams of alt product match `orig_grams` of orig for a single macro."""
    orig_val = orig_nutr.get(macro, 0) or 0
    alt_per_100 = alt_nutr.get(macro, 0) or 0
    if not orig_val or not alt_per_100:
        return None
    target = orig_val * orig_grams / 100
    return round(target / alt_per_100 * 100, 1)


# ── Query building ────────────────────────────────────────────────────────────
def _category_query(product: dict) -> str:
    tags = product.get('categories_tags') or []
    if tags:
        tag = tags[-1]
        tag = tag.split(':', 1)[-1] if ':' in tag else tag
        q = tag.replace('-', ' ').strip()
        if q:
            return q
    return ' '.join((product.get('name') or '').split()[:2])


def smae_by_group(group: str, limit: int = 30) -> list[dict]:
    """SMAE products belonging to the same SMAE group (public helper)."""
    from src import smae_client
    out = []
    for e in smae_client._load_db():
        if e.get('group') == group:
            out.append(smae_client._smae_to_product(e))
            if len(out) >= limit:
                break
    return out


# ── Cache (query+cc, 10 min) ──────────────────────────────────────────────────
_CACHE: dict = {}
_TTL = 600


def _default_search(query: str, cc: str | None, page_size: int = 20) -> list[dict]:
    from src.api_client import search_by_name as off_search
    from src.smae_client import search_by_name as smae_search
    results = []
    if cc == 'mx':
        results.extend(smae_search(query, page_size=page_size))
    results.extend(off_search(query, page_size=page_size, country_code=cc))
    return results


def _cached_search(search_fn, query: str, cc: str | None) -> list[dict]:
    key = (query, cc, id(search_fn))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    res = search_fn(query, cc)
    _CACHE[key] = (time.time(), res)
    return res


def _same_product(orig: dict, cand: dict) -> bool:
    if orig.get('id') and orig.get('id') == cand.get('id'):
        return True
    on, cn = (orig.get('name') or '').strip().lower(), (cand.get('name') or '').strip().lower()
    return bool(on) and on == cn


def find_alternatives(product: dict, settings: dict, n: int = 3, search_fn=None) -> list[dict]:
    """Up to `n` suitable (verdict 'ok') alternatives, closest macros first.

    `search_fn(query, cc) -> list[dict]` may be injected for tests. Returns []
    on any error. Each result carries c['_verdict'].
    """
    settings = settings or {}
    cs = settings.get('countries', {})
    cc = cs.get('cc') if isinstance(cs, dict) else None
    try:
        candidates: list[dict] = []
        if product.get('_source') == 'smae' and product.get('_smae_group') and search_fn is None:
            candidates.extend(smae_by_group(product['_smae_group']))
        query = _category_query(product)
        if query:
            fn = search_fn or _default_search
            candidates.extend(_cached_search(fn, query, cc))
    except Exception:
        return []

    seen, suitable = set(), []
    for c in candidates:
        if _same_product(product, c):
            continue
        key = (c.get('name') or '').strip().lower() or c.get('id')
        if key in seen:
            continue
        seen.add(key)
        try:
            v = verdict(c, settings)
        except Exception:
            continue
        if v['status'] != 'ok':
            continue
        c['_verdict'] = v
        suitable.append(c)

    orig_n = product.get('nutrition') or {}
    weights = MATCH_MODES['cal_protein'][1]
    if orig_n.get('Energy (kcal)') or orig_n.get('Protein (g)'):
        with_data = [c for c in suitable if (c.get('nutrition') or {}).get('Energy (kcal)')]
        without = [c for c in suitable if c not in with_data]
        with_data.sort(key=lambda c: macro_score(orig_n, c['nutrition'], weights)[0])
        suitable = with_data + without
    return suitable[:n]
