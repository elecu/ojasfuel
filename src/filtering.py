"""Diet resolution and result filtering shared by list, detail and equivalents pages."""

from src.classifier import ProductClassifier

_classifier = ProductClassifier()

_ALLERGY_KIND = 'allergy'


def resolve_diet(product: dict, settings: dict) -> dict:
    """Resolve vegan/vegetarian status. Priority: OFF/SMAE tags > regex classifier.

    Returns {'is_vegan', 'is_vegetarian', 'source': 'off'|'smae'|'ingredients'|'none',
             'classification': <classifier result>}.
    """
    cl = _classifier.classify(product.get('ingredients', '') or '', settings or {},
                              product_name=product.get('name', ''))
    tags = product.get('_off_tags') or {}
    t_vegan, t_veg = tags.get('is_vegan'), tags.get('is_vegetarian')

    if t_vegan is not None or t_veg is not None:
        source = 'smae' if product.get('_source') == 'smae' else 'off'
        is_vegetarian = t_veg if t_veg is not None else cl.get('is_vegetarian')
        is_vegan = t_vegan if t_vegan is not None else cl.get('is_vegan')
        # Gap-filling from the regex classifier must not override OFF's own doubt
        if t_vegan is None and tags.get('vegan_uncertain') and is_vegan:
            is_vegan = None
        if t_veg is None and tags.get('vegetarian_uncertain') and is_vegetarian:
            is_vegetarian = None
        if is_vegan and is_vegetarian is None:
            is_vegetarian = True
        if is_vegan is None and is_vegetarian is False:
            is_vegan = False
    elif cl.get('is_vegan') is not None or cl.get('is_vegetarian') is not None:
        source = 'ingredients'
        is_vegan, is_vegetarian = cl.get('is_vegan'), cl.get('is_vegetarian')
    else:
        source = 'none'
        is_vegan = is_vegetarian = None
    return {'is_vegan': is_vegan, 'is_vegetarian': is_vegetarian,
            'source': source, 'classification': cl}


def allergy_violations(classification: dict) -> list[str]:
    """Only the allergy-related violations of a classifier result."""
    if not classification:
        return []
    viols = classification.get('violations', [])
    kinds = classification.get('violation_kinds', [])
    return [v for v, k in zip(viols, kinds) if k == _ALLERGY_KIND]


def classify_results(products: list, settings: dict) -> list:
    """Classify products and drop those failing country / diet mode.

    Sets p['_classification'] and p['_diet']. Meat/fish/gelatin are always hidden;
    'vegan' mode additionally hides non-vegan; 'both' keeps all vegetarian-compatible.
    """
    settings = settings or {}
    mode = settings.get('mode', 'vegetarian')
    cs = settings.get('countries', {})
    country_tags = cs.get('tags', []) if isinstance(cs, dict) else (cs or [])
    filtered = []
    for p in products:
        diet = resolve_diet(p, settings)
        p['_diet'] = diet
        p['_classification'] = diet['classification']

        if country_tags:
            prod_countries = p.get('countries_tags', [])
            if prod_countries and not any(c in prod_countries for c in country_tags):
                continue

        if diet['is_vegetarian'] is False:
            continue
        if mode == 'vegan' and diet['is_vegan'] is False:
            continue
        filtered.append(p)
    return filtered
