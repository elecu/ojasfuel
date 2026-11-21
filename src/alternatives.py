"""Alternative-product finder and macro-matching helpers (shared with Equivalents page)."""

import time

from src.food_tables import GENERIC_SOURCES, TABLE_SOURCES
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


# ── Relevance-first alternative finder ───────────────────────────────────────
# Strategy (why alternatives used to be irrelevant: free-text search on a
# category *name* returned anything sharing a word, ranked only by kcal):
#   1. exact OFF category filter, most specific category first, walking up to
#      parent categories only when there are not enough suitable products;
#   2. country + diet filters inside the query itself;
#   3. when allergies/restrictions are active, load full ingredients for the
#      best candidates (search hits carry none, so they could not be checked);
#   4. rank by category closeness, then category overlap, then macros;
#   5. at most one product per brand (variety), unless that leaves too few.

MAX_CATEGORY_LEVELS = 3
ENRICH_LIMIT = 8
ENRICH_BUDGET_S = 4.0
SEARCH_TIMEOUT_S = 5.0
_RESTRICTION_KEYS = ('no_garlic', 'no_onion', 'no_caffeine', 'no_alcohol', 'no_mushrooms',
                     'no_gelatin', 'jain', 'lacto', 'ovo', 'strict_egg_traces')


def specific_categories(product: dict, levels: int = MAX_CATEGORY_LEVELS) -> list[str]:
    """Canonical (en:) categories, most specific first (OFF lists general → specific)."""
    tags = [t for t in (product.get('categories_tags') or []) if str(t).startswith('en:')]
    out = []
    for t in reversed(tags):
        if t not in out:
            out.append(t)
    return out[:levels]


def _diet_tag(settings: dict) -> str:
    return 'en:vegan' if settings.get('mode') == 'vegan' else 'en:vegetarian'


def needs_ingredients(settings: dict) -> bool:
    """True when suitability depends on the ingredient list, not only diet tags."""
    return any(settings.get(k) for k in settings if str(k).startswith('allergies_')) \
        or any(settings.get(k) for k in _RESTRICTION_KEYS)


def category_overlap(a: dict, b: dict) -> float:
    ta = {t for t in (a.get('categories_tags') or []) if str(t).startswith('en:')}
    tb = {t for t in (b.get('categories_tags') or []) if str(t).startswith('en:')}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _brand_key(p: dict) -> str:
    if p.get('_source') in GENERIC_SOURCES:  # one brand for all: diversify by food type instead
        return (p.get('name') or '').split(',')[0].strip().lower()
    return ((p.get('brand') or '').split(',')[0]).strip().lower()


# ── Preparation state (cooked / raw / dry ...) ───────────────────────────────
# Cooked rice should be replaced by cooked pasta, not by dry pasta (its kcal per
# 100 g are 3x higher, so the "equivalent" grams would be meaningless).
_STATE_WORDS = {
    'cooked': ('cooked', 'boiled', 'baked', 'roasted', 'steamed', 'fried', 'grilled',
               'broiled', 'stewed', 'simmered', 'prepared', 'cocido', 'cocida', 'cocidos',
               'cocidas', 'hervido', 'hervida', 'hervidos', 'hervidas', 'horneado',
               'horneada', 'asado', 'asada', 'frito', 'frita', 'al vapor', 'guisado', 'guisada',
               'microwaved', 'poached', 'braised',
               # French (CIQUAL)
               'cuit', 'cuite', 'cuits', 'cuites', 'bouilli', 'bouillie', 'bouillis',
               'bouillies', 'au four', 'roti', 'rotie', 'rotis', 'roties', 'a la vapeur',
               'cuit vapeur', 'poele', 'poelee', 'saute', 'sautee', 'grille', 'grillee',
               'braise', 'braisee', 'frit', 'frite', 'frites', 'pochee', 'poche', 'mijote'),
    'raw': ('raw', 'uncooked', 'fresh', 'crudo', 'cruda', 'crudos', 'crudas', 'fresco', 'fresca',
            'cru', 'crue', 'crus', 'crues', 'frais', 'fraiche', 'fraiches'),
    'dry': ('dry', 'dried', 'dehydrated', 'seco', 'seca', 'secos', 'secas', 'deshidratado',
            'sec', 'seche', 'secs', 'seches', 'deshydrate', 'deshydratee'),
    'canned': ('canned', 'enlatado', 'enlatada', 'enlatados', 'enlatadas', 'tinned',
               'en conserve', 'appertise', 'appertisee', 'appertises', 'appertisees'),
    'frozen': ('frozen', 'congelado', 'congelada', 'congelados', 'congeladas',
               'surgele', 'surgelee', 'surgeles', 'surgelees'),
}


def prep_state(name: str) -> str | None:
    """Preparation state class of a food name ('cooked', 'raw', 'dry', ...) or None."""
    import re
    import unicodedata
    low = unicodedata.normalize('NFKD', (name or '').lower())
    low = ''.join(c for c in low if not unicodedata.combining(c))
    found = []
    for state, words in _STATE_WORDS.items():
        for w in words:
            m = re.search(r'\b' + re.escape(w) + r'\b', low)
            if m:
                found.append((m.start(), state))
    # "unprepared" (frozen fries, dry mixes) is never cooked; otherwise cooked wins
    # over other words ("pasta, fresh-refrigerated, cooked")
    if 'unprepared' in low:
        found = [f for f in found if f[1] != 'cooked']
    if not found:
        return None
    if any(st == 'cooked' for _, st in found):
        return 'cooked'
    return min(found)[1]


def _apply_state_levels(orig: dict, items: list[dict], base: int) -> None:
    """Same preparation state at `base`, others at `base` + 2 (after the next scope)."""
    st = prep_state(orig.get('name'))
    for c in items:
        c['_level'] = base if (st is None or prep_state(c.get('name')) == st) else base + 2


def smae_by_group(group: str, limit: int = 60, subgroup=None) -> list[dict]:
    """SMAE products in the same SMAE group (and subgroup when given)."""
    from src import smae_client
    out = []
    for e in smae_client._load_db():
        if e.get('group') == group and (subgroup is None or e.get('subgroup') == subgroup):
            out.append(smae_client._smae_to_product(e))
            if len(out) >= limit:
                break
    return out


# ── Cache (10 min) ────────────────────────────────────────────────────────────
_CACHE: dict = {}
_TTL = 600


def _cached(key, fn):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    res = fn()
    _CACHE[key] = (time.time(), res)
    return res


def _default_category_search(category_tag: str, country_tags: list, diet_tag: str,
                             exclude_allergens: list | None = None) -> list[dict]:
    from src.api_client import search_filtered
    # alternatives are secondary info: bounded wait, no retry
    return search_filtered(category_tag, country_tags=country_tags or None,
                           diet_tag=diet_tag, page_size=40,
                           exclude_allergens=exclude_allergens,
                           timeout=SEARCH_TIMEOUT_S, attempts=1)


def _default_lookup(code: str):
    from src.api_client import search_by_barcode
    return search_by_barcode(code)


def _same_product(orig: dict, cand: dict) -> bool:
    if orig.get('id') and orig.get('id') == cand.get('id'):
        return True
    on, cn = (orig.get('name') or '').strip().lower(), (cand.get('name') or '').strip().lower()
    return bool(on) and on == cn


def _enrich(cands: list[dict], lookup_fn) -> None:
    """Replace search hits that still lack ingredients by full products.

    Most hits now carry ingredient tags, so this only runs for the few without;
    bounded by ENRICH_BUDGET_S because the product API can be slow.
    """
    from concurrent.futures import ThreadPoolExecutor
    todo = [(i, c) for i, c in enumerate(cands)
            if not c.get('ingredients') and c.get('_source') not in TABLE_SOURCES and c.get('id')]
    if not todo:
        return

    def load(item):
        i, c = item
        try:
            full = lookup_fn(str(c['id']))
        except Exception:
            return i, None
        return i, full

    from concurrent.futures import wait
    ex = ThreadPoolExecutor(max_workers=6)
    futures = [ex.submit(load, item) for item in todo]
    done, _ = wait(futures, timeout=ENRICH_BUDGET_S)  # never block the page for long
    ex.shutdown(wait=False, cancel_futures=True)
    for f in done:
        i, full = f.result()
        if full:
            full['_level'] = cands[i].get('_level', 0)
            full.setdefault('_off_tags', cands[i].get('_off_tags'))
            cands[i] = full


def _rank_key(orig: dict, c: dict) -> tuple:
    orig_n = orig.get('nutrition') or {}
    cand_n = c.get('nutrition') or {}
    if (orig_n.get('Energy (kcal)') or orig_n.get('Protein (g)')) and cand_n.get('Energy (kcal)'):
        macro = macro_score(orig_n, cand_n, MATCH_MODES['cal_protein'][1])[0]
    else:
        macro = 9.0  # unknown nutrition sorts last within its level
    return (c.get('_level', 9), -round(category_overlap(orig, c), 1), macro)


def _diverse(ranked: list[dict], n: int) -> list[dict]:
    """At most one per brand first; fill with the rest if too few."""
    picked, brands = [], set()
    for c in ranked:
        b = _brand_key(c)
        if b and b in brands:
            continue
        picked.append(c)
        if b:
            brands.add(b)
        if len(picked) >= n:
            return picked
    for c in ranked:
        if c not in picked:
            picked.append(c)
            if len(picked) >= n:
                break
    return picked


def _safe(fn, arg):
    try:
        return fn(arg)
    except Exception:
        return None  # one failing level must not drop the others


def _collect_candidates(product, settings, search_fn, n) -> list[dict]:
    cs = settings.get('countries', {})
    country_tags = list(cs.get('tags') or []) if isinstance(cs, dict) else list(cs or [])
    diet = _diet_tag(settings)
    from src.api_client import ALLERGEN_TAGS
    excl = [t for k, tags in ALLERGEN_TAGS.items() if settings.get(k) for t in tags]
    out = []

    if product.get('_source') == 'smae' and product.get('_smae_group'):
        grp, sub = product['_smae_group'], product.get('_smae_subgroup')
        for lvl, items in enumerate((smae_by_group(grp, subgroup=sub) if sub else [],
                                     smae_by_group(grp))):
            _apply_state_levels(product, items, lvl)
            out.extend(items)
        return out, False

    if product.get('_source') in GENERIC_SOURCES and product.get('_table_category'):
        from src import food_tables
        table = food_tables.get_table(product['_source'])
        cat, sub = product['_table_category'], product.get('_table_subgroup')
        lang = product.get('_name_lang', 'en')
        # variants that only differ by "with/without salt" etc. are not alternatives
        sig = lambda p: tuple((p.get('nutrition') or {}).get(k) for k in
                              ('Energy (kcal)', 'Protein (g)', 'Fat (g)', 'Carbohydrates (g)'))
        items = [c for c in table.by_category(cat, limit=3000, lang=lang) if sig(c) != sig(product)]
        if sub:  # same subgroup first (level 0/2), then the whole group (level 1/3)
            same = [c for c in items if c.get('_table_subgroup') == sub]
            rest = [c for c in items if c.get('_table_subgroup') != sub]
            _apply_state_levels(product, same, 0)
            _apply_state_levels(product, rest, 1)
            return same + rest, False
        _apply_state_levels(product, items, 0)
        for c in items:  # other states: level 1 (no sub-scope for USDA)
            c['_level'] = min(c['_level'], 1)
        return items, False

    cats = specific_categories(product)

    def run(cat):
        return _cached((cat, tuple(country_tags), diet, tuple(excl), id(search_fn)),
                       lambda: (search_fn(cat, country_tags, diet, excl)
                                if search_fn is _default_category_search
                                else search_fn(cat, country_tags, diet)))

    # all category levels at once: total time = slowest query, not the sum
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, len(cats))) as ex:
        results = list(ex.map(lambda c: _safe(run, c), cats))
    incomplete = any(r is None for r in results)
    for lvl, hits in enumerate(results):
        for c in hits or []:
            c = dict(c)
            c['_level'] = lvl
            out.append(c)
    return out, incomplete


def find_alternatives(product: dict, settings: dict, n: int = 3,
                      search_fn=None, lookup_fn=None) -> list[dict]:
    """Up to `n` suitable alternatives (see find_alternatives_ex)."""
    return find_alternatives_ex(product, settings, n, search_fn, lookup_fn)[0]


def find_alternatives_ex(product: dict, settings: dict, n: int = 3,
                         search_fn=None, lookup_fn=None) -> tuple[list[dict], bool]:
    """Up to `n` suitable (verdict 'ok') alternatives from the same category.

    search_fn(category_tag, country_tags, diet_tag) and lookup_fn(code) can be
    injected for tests. Returns (alternatives, incomplete) where incomplete
    means a search failed (network) so the caller may offer a retry.
    Each result has c['_verdict'].
    Products without OFF categories (rare) get no alternatives rather than
    unrelated free-text matches.
    """
    settings = settings or {}
    search_fn = search_fn or _default_category_search
    lookup_fn = lookup_fn or _default_lookup
    try:
        candidates, incomplete = _collect_candidates(product, settings, search_fn, n)
    except Exception:
        return [], True

    seen, uniq = set(), []
    for c in candidates:
        if _same_product(product, c):
            continue
        key = (c.get('name') or '').strip().lower() or c.get('id')
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(c)

    uniq.sort(key=lambda c: _rank_key(product, c))
    if needs_ingredients(settings):
        head = uniq[:ENRICH_LIMIT]
        try:
            _enrich(head, lookup_fn)
        except Exception:
            pass
        uniq = head + uniq[ENRICH_LIMIT:]

    suitable = []
    for c in uniq:
        try:
            v = verdict(c, settings)
        except Exception:
            continue
        if v['status'] == 'ok':
            c['_verdict'] = v
            suitable.append(c)
    suitable.sort(key=lambda c: _rank_key(product, c))
    # incomplete = a network failure may have hidden candidates (caller can retry)
    return _diverse(suitable, n), incomplete
