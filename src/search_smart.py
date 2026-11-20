"""Smart search: typo-tolerant SMAE lookup, autocomplete, simple query filters."""

import re

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from src import smae_client
from src.smae_client import _normalize, _load_db, _smae_to_product
from src.filtering import classify_results
from src.verdict import verdict
from src.blocklists import ALLERGIES_GLUTEN
from src.classifier import _find_matches

_NORM_NAMES: list | None = None


def _names() -> list[tuple[str, dict]]:
    global _NORM_NAMES
    if _NORM_NAMES is None:
        _NORM_NAMES = [(_normalize(e['name']), e) for e in _load_db()]
    return _NORM_NAMES


def _max_typos(word: str) -> int:
    return 1 if len(word) <= 5 else 2


def _word_close(q: str, word: str) -> bool:
    """Typo-tolerant word match: same first letter and at most 1-2 edits.

    Plain similarity ratios are too loose ("banana" ~ "manzana" scores 77).
    """
    if not q or not word or q[0] != word[0]:
        return False
    if word.startswith(q):
        return True
    # plurals: "frijoles" → "frijol", "manzanas" → "manzana"
    if q.startswith(word) and len(word) >= 4 and len(q) - len(word) <= 2:
        return True
    return Levenshtein.distance(q, word) <= _max_typos(q)


def fuzzy_smae(query: str, limit: int = 10, score_cutoff: int = 75) -> list[dict]:
    """Typo-tolerant SMAE search: every query word must closely match a word of the name."""
    q = _normalize((query or '').strip())
    if not q:
        return []
    q_words = q.split()
    scored = []
    for name, e in _names():
        name_words = name.split()
        if not all(any(_word_close(qw, nw) for nw in name_words) for qw in q_words):
            continue
        s = fuzz.WRatio(q, name)
        bonus = 0 if name == q else (1 if name.startswith(q) else 2)
        scored.append((bonus, -s, len(name), e))
    scored.sort(key=lambda x: x[:3])
    return [_smae_to_product(e) for *_, e in scored[:limit]]


def suggest(prefix: str, history: list[str], limit: int = 8) -> list[str]:
    p = _normalize((prefix or '').strip())
    if not p:
        return []
    out, seen = [], set()

    def add(s):
        k = _normalize(s)
        if k not in seen and len(out) < limit:
            seen.add(k)
            out.append(s)

    for h in history or []:
        if p in _normalize(h):
            add(h)
    starts = [e['name'] for n, e in _names() if n.startswith(p)]
    contains = [e['name'] for n, e in _names() if not n.startswith(p) and p in n]
    for nm in sorted(starts, key=len) + sorted(contains, key=len):
        add(nm)
    return out


_COMMON = {
    'es': ['plátano', 'manzana', 'aguacate', 'frijol', 'tortilla de maíz', 'arroz',
           'avena', 'queso panela', 'nopal', 'lentejas'],
    'en': ['banana', 'apple', 'avocado', 'beans', 'corn tortilla', 'rice',
           'oats', 'panela cheese', 'cactus (nopal)', 'lentils'],
}


# English (or other) names → SMAE Spanish name, used when country is Mexico
_SMAE_ALIASES = {
    'banana': 'plátano', 'bananas': 'plátano', 'apple': 'manzana', 'apples': 'manzana',
    'avocado': 'aguacate', 'beans': 'frijol', 'black beans': 'frijol negro',
    'corn tortilla': 'tortilla de maíz', 'tortilla': 'tortilla', 'rice': 'arroz',
    'oats': 'avena', 'oatmeal': 'avena', 'panela cheese': 'queso panela',
    'cactus (nopal)': 'nopal', 'cactus': 'nopal', 'nopal': 'nopal', 'lentils': 'lentejas',
    'orange': 'naranja', 'mango': 'mango', 'papaya': 'papaya', 'tomato': 'jitomate',
    'potato': 'papa', 'carrot': 'zanahoria', 'spinach': 'espinaca', 'onion': 'cebolla',
    'chickpeas': 'garbanzo', 'peanuts': 'cacahuate', 'almonds': 'almendra',
    'milk': 'leche', 'egg': 'huevo', 'eggs': 'huevo', 'bread': 'pan', 'pineapple': 'piña',
    'strawberry': 'fresa', 'strawberries': 'fresa', 'watermelon': 'sandía', 'melon': 'melón',
    'pear': 'pera', 'grapes': 'uva', 'lemon': 'limón', 'lime': 'limón', 'corn': 'elote',
    'squash': 'calabacita', 'zucchini': 'calabacita', 'broccoli': 'brócoli', 'lettuce': 'lechuga',
}


def smae_alias(query: str) -> str:
    return _SMAE_ALIASES.get((query or '').strip().lower(), query)


def common_foods(lang: str) -> list[str]:
    return list(_COMMON.get((lang or 'en')[:2], _COMMON['en']))


# ── Query parsing ─────────────────────────────────────────────────────────────
_FILTER_PATTERNS = [
    ('gluten_free', r'\bsin\s+gluten\b|\bgluten[\s-]*free\b'),
    ('vegan', r'\bveganos?\b|\bveganas?\b|\bvegan\b'),
    ('high_protein', r'\balto\s+en\s+prote[ií]nas?\b|\balta\s+en\s+prote[ií]nas?\b|\bhigh[\s-]+protein\b'
                     r'|\bcon\s+prote[ií]nas?\b|\bwith\s+protein\b'),
    ('sugar_free', r'\bsin\s+az[uú]car(?:es)?\b|\bsugar[\s-]*free\b|\bno\s+sugar\b'),
]


def parse_query(q: str) -> dict:
    text = q or ''
    filters = {'vegan': False, 'gluten_free': False, 'high_protein': False, 'sugar_free': False}
    for key, pat in _FILTER_PATTERNS:
        text, n = re.subn(pat, ' ', text, flags=re.IGNORECASE)
        if n:
            filters[key] = True
    return {'keywords': ' '.join(text.split()), 'filters': filters}


def apply_filters(products: list, filters: dict) -> list:
    from src.blocklists import ALLERGIES_GLUTEN
    from src.classifier import _find_matches
    filters = filters or {}
    out = []
    for p in products:
        n = p.get('nutrition') or {}
        if filters.get('high_protein') and (n.get('Protein (g)') or 0) < 10:
            continue
        if filters.get('sugar_free'):
            sugars = n.get('Sugars (g)')
            if sugars is None or sugars > 0.5:
                continue
        if filters.get('gluten_free') and not _is_gluten_free(p):
            continue
        if filters.get('vegan'):
            if verdict(p, {'mode': 'vegan'})['status'] != 'ok':
                continue
        out.append(p)
    return out


# SMAE groups whose foods are naturally gluten-free (no wheat/barley/rye)
_SMAE_GLUTEN_FREE_GROUPS = {'Verduras', 'Frutas', 'Leguminosas'}


def _is_gluten_free(p: dict) -> bool:
    """Require positive evidence — celiac safety: unknown is NOT gluten-free."""
    labels = (p.get('labels') or '').lower()
    if any(s in labels for s in ('gluten-free', 'gluten free', 'sin gluten', 'sans gluten')):
        return True
    if p.get('_source') == 'smae':
        # SMAE has no ingredient list (only a name hint), so trust the group only
        return p.get('_smae_group') in _SMAE_GLUTEN_FREE_GROUPS
    ingredients = (p.get('ingredients') or '').lower()
    if not ingredients:
        return False
    return not _find_matches(ingredients, ALLERGIES_GLUTEN)


def smart_search(query: str, settings: dict, history=None) -> tuple[list[dict], bool]:
    """Returns (products, off_failed)."""
    settings = settings or {}
    parsed = parse_query(query)
    kw = parsed['keywords'] or (query or '').strip()
    if not kw:
        return [], False
    cs = settings.get('countries', {})
    cc = cs.get('cc') if isinstance(cs, dict) else None

    results, seen = [], set()

    def add(items):
        for p in items:
            k = (p.get('name') or '').lower()
            if k not in seen:
                seen.add(k)
                results.append(p)

    if cc == 'mx':
        smae_kw = smae_alias(kw)
        smae = smae_client.search_by_name(smae_kw, page_size=20)
        add(smae)
        if len(smae) < 5:
            add(fuzzy_smae(smae_kw, limit=10))
    off_failed = False
    try:
        from src import api_client
        add(api_client.search_by_name(kw, page_size=20, country_code=cc))
    except Exception:
        off_failed = True

    results = apply_filters(results, parsed['filters'])
    return classify_results(results, settings), off_failed


def single_clear_match(products: list, query: str) -> dict | None:
    if len(products) == 1:
        return products[0]
    q = _normalize((query or '').strip())
    exact = [p for p in products if _normalize(p.get('name') or '') == q]
    return exact[0] if len(exact) == 1 else None
