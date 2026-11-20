"""Single suitability verdict (ok / no / unknown) for a product and user settings."""

from src.filtering import resolve_diet, ingredients_verifiable

_RESTRICTION_KEYS = (
    'no_alcohol', 'no_caffeine', 'no_mushrooms', 'no_onion', 'no_garlic',
    'no_gelatin', 'jain', 'strict_egg_traces', 'ovo', 'lacto',
)
_ALLERGY_KEYS = (
    'allergies_nuts', 'allergies_peanuts', 'allergies_soy',
    'allergies_mustard', 'allergies_sesame', 'allergies_gluten',
)
_LACTO_OVO_PREFIXES = ('Ovo-vegetarian', 'Lacto-vegetarian')


def _terms_from(violation: str) -> list[str]:
    if ':' not in violation:
        return []
    tail = violation.rsplit(':', 1)[1]
    return [t.strip() for t in tail.split(',') if t.strip()]


def _add_unique(lst: list, items) -> None:
    low = {x.lower() for x in lst}
    for it in items:
        if it and it.lower() not in low:
            lst.append(it)
            low.add(it.lower())


def _declared_allergen_reasons(product: dict, settings: dict, existing: list) -> list[dict]:
    """Allergens the manufacturer declared to OFF (allergens_tags / traces_tags).

    Catches allergens the ingredient regex misses and works for search hits
    that only carry tags. Traces ("may contain") count: for allergies, safe > sorry.
    """
    from src.api_client import ALLERGEN_TAGS
    allergens = set(product.get('allergens_tags') or [])
    traces = set(product.get('traces_tags') or [])
    out = []
    for key, tags in ALLERGEN_TAGS.items():
        if not settings.get(key):
            continue
        name = tags[0].split(':', 1)[-1].replace('-', ' ')
        if allergens & set(tags):
            text = f'Declared allergen: {name}'
        elif traces & set(tags):
            text = f'May contain traces of {name}'
        else:
            continue
        if not any(text == r['text'] for r in existing + out):
            out.append({'kind': 'allergy', 'text': text})
    return out


def verdict(product: dict, settings: dict) -> dict:
    settings = settings or {}
    mode = settings.get('mode', 'vegetarian')
    diet = resolve_diet(product, settings)
    cl = diet['classification'] or {}
    viols = cl.get('violations', []) or []
    kinds = cl.get('violation_kinds', []) or []
    pairs = list(zip(viols, kinds))

    reasons: list[dict] = []
    flagged: list[str] = []

    # 1. allergies (ingredient matches, then OFF-declared allergens / traces)
    for v, k in pairs:
        if k == 'allergy':
            reasons.append({'kind': 'allergy', 'text': v})
            _add_unique(flagged, _terms_from(v))
    reasons.extend(_declared_allergen_reasons(product, settings, reasons))

    # 2. diet
    is_veg, is_vegan = diet['is_vegetarian'], diet['is_vegan']
    diet_no = False
    if mode == 'vegan':
        diet_no = is_vegan is False
    else:  # 'vegetarian' and 'both' only reject non-vegetarian
        diet_no = is_veg is False
    if diet_no:
        diet_texts = [v for v, k in pairs if k == 'diet'
                      and not v.startswith(_LACTO_OVO_PREFIXES)]
        if diet_texts:
            for v in diet_texts:
                reasons.append({'kind': 'diet', 'text': v})
        else:
            label = 'Not vegan' if mode == 'vegan' and is_veg is not False else 'Not vegetarian'
            reasons.append({'kind': 'diet', 'text': label})
        _add_unique(flagged, cl.get('animal_products_found', []))
        if mode == 'vegan':
            _add_unique(flagged, cl.get('dairy_or_eggs_found', []))
    for v, k in pairs:
        if k == 'diet' and v.startswith(_LACTO_OVO_PREFIXES):
            reasons.append({'kind': 'diet', 'text': v})
            _add_unique(flagged, _terms_from(v))
            diet_no = True

    # 3. restrictions
    restriction_no = False
    for v, k in pairs:
        if k == 'restriction':
            reasons.append({'kind': 'restriction', 'text': v})
            _add_unique(flagged, _terms_from(v))
            restriction_no = True

    has_allergy = any(r['kind'] == 'allergy' for r in reasons)
    if has_allergy or diet_no or restriction_no:
        status = 'no'
    else:
        status = 'ok'
        needed = is_vegan if mode == 'vegan' else is_veg
        tags = product.get('_off_tags') or {}
        if needed is None:
            status = 'unknown'
            uncertain = tags.get('vegan_uncertain') if mode == 'vegan' else tags.get('vegetarian_uncertain')
            if uncertain:
                reasons.append({'kind': 'uncertain', 'text': 'Maybe vegan: ingredients incomplete',
                                'reason_key': 'verdict_maybe_vegan'})
            elif not (product.get('ingredients') or '').strip():
                reasons.append({'kind': 'no_data', 'text': 'No ingredients data',
                                'reason_key': 'verdict_no_ingredients'})
            else:
                reasons.append({'kind': 'no_data', 'text': 'Not enough data to decide',
                                'reason_key': 'verdict_no_diet_data'})
        ing = (product.get('ingredients') or '').strip()
        if ing in ('', 'N/A', 'n/a'):
            checks_active = any(settings.get(k) for k in _ALLERGY_KEYS + _RESTRICTION_KEYS)
            if checks_active:
                status = 'unknown'
                if not any(r.get('reason_key') == 'verdict_no_ingredients' for r in reasons):
                    reasons.append({'kind': 'no_data',
                                    'text': 'No ingredients: cannot check allergies/restrictions',
                                    'reason_key': 'verdict_no_ingredients'})

    # Safety gate: with allergies/restrictions active, a 'suitable' answer needs
    # an ingredient list OFF could actually parse (not OCR garbage).
    if status == 'ok' and any(settings.get(k) for k in _ALLERGY_KEYS + _RESTRICTION_KEYS) \
            and (product.get('ingredients') or '').strip() and not ingredients_verifiable(product):
        status = 'unknown'
        reasons.append({'kind': 'no_data',
                        'text': 'Ingredient list could not be verified (unreadable or incomplete)',
                        'reason_key': 'verdict_ingredients_unverified'})

    return {'status': status, 'reasons': reasons, 'source': diet['source'],
            'flagged_terms': flagged, 'diet': diet}
