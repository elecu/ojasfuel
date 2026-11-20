import pytest
from src.verdict import verdict
from src.alternatives import find_alternatives
from src import search_smart as ss
from src import smae_client


def P(name, ing, **kw):
    # simulate an ingredient list OFF parsed successfully (see ingredients_verifiable)
    kw.setdefault('_ingr_parsed_n', len(ing.split(',')) if ing else None)
    kw.setdefault('_ingr_unknown_n', 0)
    return {'id': name, 'name': name, 'ingredients': ing, 'nutrition': kw.pop('nutrition', {}), **kw}


def test_meat_no():
    v = verdict(P('x', 'chicken, salt'), {'mode': 'vegetarian'})
    assert v['status'] == 'no' and v['reasons'][0]['kind'] == 'diet' and v['flagged_terms']


def test_allergy_beats_diet_and_first():
    v = verdict(P('x', 'chicken, peanuts'), {'mode': 'vegetarian', 'allergies_peanuts': True})
    assert v['status'] == 'no'
    assert [r['kind'] for r in v['reasons']][0] == 'allergy'
    assert 'diet' in [r['kind'] for r in v['reasons']]


def test_allergy_only():
    v = verdict(P('x', 'sugar, peanuts'), {'mode': 'vegetarian', 'allergies_peanuts': True})
    assert v['status'] == 'no'


def test_vegan_mode_dairy_no_vegetarian_ok():
    p = P('x', 'whole milk, sugar')
    assert verdict(p, {'mode': 'vegan'})['status'] == 'no'
    assert verdict(p, {'mode': 'vegetarian'})['status'] == 'ok'
    assert verdict(p, {'mode': 'both'})['status'] == 'ok'


def test_maybe_vegan_unknown():
    p = P('x', 'sugar', _off_tags={'is_vegan': None, 'is_vegetarian': True, 'vegan_uncertain': True})
    v = verdict(p, {'mode': 'vegan'})
    assert v['status'] == 'unknown' and v['reasons'][0]['kind'] == 'uncertain'
    assert v['reasons'][0]['reason_key'] == 'verdict_maybe_vegan'


def test_smae_platano_ok():
    p = smae_client.search_by_name('Plátano', page_size=1)[0]
    v = verdict(p, {'mode': 'vegan', 'allergies_nuts': True})
    assert v['status'] == 'ok' and v['source'] == 'smae'


def test_no_ingredients_with_allergies_unknown():
    p = P('x', '', _off_tags={'is_vegan': True, 'is_vegetarian': True})
    assert verdict(p, {'mode': 'vegan'})['status'] == 'ok'
    v = verdict(p, {'mode': 'vegan', 'allergies_soy': True})
    assert v['status'] == 'unknown' and v['reasons'][-1]['reason_key'] == 'verdict_no_ingredients'


def test_restriction_no():
    v = verdict(P('x', 'water, garlic'), {'mode': 'vegetarian', 'no_garlic': True})
    assert v['status'] == 'no' and v['reasons'][-1]['kind'] == 'restriction'


def test_find_alternatives_only_suitable_and_excludes_original():
    cats = ['en:cereals']
    orig = P('Orig', 'oats', categories_tags=cats, nutrition={'Energy (kcal)': 100, 'Protein (g)': 5})
    pool = [
        orig,
        P('Meat', 'chicken', categories_tags=cats, nutrition={'Energy (kcal)': 100, 'Protein (g)': 5}),
        P('Milk', 'whole milk', categories_tags=cats, nutrition={'Energy (kcal)': 100, 'Protein (g)': 5}),
        P('Peanut', 'peanuts', categories_tags=cats, nutrition={'Energy (kcal)': 100, 'Protein (g)': 5}),
        P('Far', 'rice', categories_tags=cats, nutrition={'Energy (kcal)': 400, 'Protein (g)': 1}),
        P('Near', 'wheat', categories_tags=cats, nutrition={'Energy (kcal)': 105, 'Protein (g)': 5}),
        P('Unk', '', categories_tags=cats, nutrition={'Energy (kcal)': 100}),
    ]
    s = {'mode': 'vegan', 'allergies_peanuts': True}
    res = find_alternatives(orig, s, n=5, search_fn=lambda cat, cc, diet: [dict(p) for p in pool],
                            lookup_fn=lambda code: None)
    names = [r['name'] for r in res]
    assert names == ['Near', 'Far']
    assert all(r['_verdict']['status'] == 'ok' for r in res)


def test_find_alternatives_error():
    def boom(*a):
        raise RuntimeError('x')
    assert find_alternatives(P('a', 'b', categories_tags=['en:x']), {}, search_fn=boom) == []


def test_alternatives_prefer_most_specific_category_and_pass_filters():
    from src.alternatives import specific_categories
    orig = P('Nutella', 'sugar, palm oil, hazelnuts, skimmed milk powder',
             categories_tags=['en:spreads', 'en:sweet-spreads', 'en:cocoa-and-hazelnuts-spreads'],
             nutrition={'Energy (kcal)': 539, 'Protein (g)': 6})
    assert specific_categories(orig)[0] == 'en:cocoa-and-hazelnuts-spreads'
    calls = []
    by_cat = {
        'en:cocoa-and-hazelnuts-spreads': [P('Vegan hazelnut cream', 'hazelnuts, cocoa, sugar',
                                             categories_tags=orig['categories_tags'],
                                             nutrition={'Energy (kcal)': 530, 'Protein (g)': 7})],
        'en:sweet-spreads': [P('Powdered sugar', 'sugar', categories_tags=['en:sweet-spreads'],
                               nutrition={'Energy (kcal)': 540, 'Protein (g)': 6})],
    }

    def fake(cat, country_tags, diet):
        calls.append((cat, tuple(country_tags), diet))
        return [dict(p) for p in by_cat.get(cat, [])]

    s = {'mode': 'vegan', 'countries': {'tags': ['en:mexico'], 'cc': 'mx'}}
    res = find_alternatives(orig, s, n=3, search_fn=fake)
    # same-category product ranks first even though sugar's macros are closer
    assert res[0]['name'] == 'Vegan hazelnut cream'
    assert calls[0] == ('en:cocoa-and-hazelnuts-spreads', ('en:mexico',), 'en:vegan')


def test_alternatives_one_per_brand_when_possible():
    cats = ['en:biscuits']
    orig = P('Orig', 'wheat flour, sugar', categories_tags=cats)
    pool = [P(f'A{i}', 'wheat flour, sugar', categories_tags=cats, brand='BrandA') for i in range(3)]
    pool.append(P('B1', 'wheat flour, sugar', categories_tags=cats, brand='BrandB'))
    res = find_alternatives(orig, {'mode': 'vegetarian'}, n=2,
                            search_fn=lambda *a: [dict(p) for p in pool])
    assert {r['brand'] for r in res} == {'BrandA', 'BrandB'}


def test_alternatives_load_ingredients_when_allergies_active():
    cats = ['en:biscuits']
    orig = P('Orig', 'wheat flour, milk', categories_tags=cats)
    hit = P('Hit', '', categories_tags=cats)  # search hits carry no ingredients
    hit['id'] = '123'
    full = P('Hit', 'oat flour, sugar, sesame', categories_tags=cats)
    full['id'] = '123'
    res = find_alternatives(orig, {'mode': 'vegetarian', 'allergies_sesame': True}, n=3,
                            search_fn=lambda *a: [dict(hit)], lookup_fn=lambda code: dict(full))
    assert res == []  # enriched ingredients reveal sesame → excluded, not "unknown-but-shown"
    full2 = P('Hit', 'oat flour, sugar', categories_tags=cats)
    full2['id'] = '123'
    res = find_alternatives(orig, {'mode': 'vegetarian', 'allergies_sesame': True}, n=3,
                            search_fn=lambda *a: [dict(hit)], lookup_fn=lambda code: dict(full2))
    assert [r['name'] for r in res] == ['Hit']


def test_fuzzy():
    assert any('frijol' in p['name'].lower() for p in ss.fuzzy_smae('frjol'))
    assert any(p['name'] == 'Plátano' for p in ss.fuzzy_smae('platano'))


def test_parse_query():
    r = ss.parse_query('galletas sin gluten')
    assert r['keywords'] == 'galletas' and r['filters']['gluten_free']
    assert ss.parse_query('high protein yogurt')['filters']['high_protein']


def test_suggest_and_common():
    s = ss.suggest('platano', ['plátano maduro'])
    assert s[0] == 'plátano maduro' and 'Plátano' in s
    assert len(ss.common_foods('es')) == 10


def test_apply_filters_and_single():
    prods = [P('a', 'sugar', nutrition={'Protein (g)': 12, 'Sugars (g)': 0}),
             P('b', 'wheat flour', nutrition={'Protein (g)': 2})]
    assert [p['name'] for p in ss.apply_filters(prods, {'high_protein': True})] == ['a']
    assert [p['name'] for p in ss.apply_filters(prods, {'gluten_free': True})] == ['a']
    assert ss.single_clear_match(prods[:1], 'zzz')['name'] == 'a'
    assert ss.single_clear_match(prods, 'A')['name'] == 'a'


def test_gluten_free_requires_positive_evidence():
    from src.search_smart import apply_filters
    from src.smae_client import search_by_name
    marias = search_by_name('galletas marias')[0]
    platano = search_by_name('platano')[0]
    unknown_off = {'name': 'Cookie X', 'ingredients': '', 'labels': ''}
    labelled = {'name': 'GF Cookie', 'ingredients': '', 'labels': 'en:gluten-free'}
    out = apply_filters([marias, platano, unknown_off, labelled], {'gluten_free': True})
    names = [p['name'] for p in out]
    assert 'Plátano' in names and 'GF Cookie' in names
    assert marias['name'] not in names and 'Cookie X' not in names


def test_fuzzy_smae_is_not_too_loose():
    from src.search_smart import fuzzy_smae
    assert not any('Manzana' in p['name'] for p in fuzzy_smae('banana'))
    assert any(p['name'].startswith('Aguacate') for p in fuzzy_smae('aguacte'))
    assert not any(p['name'] == 'Agua' for p in fuzzy_smae('aguacte'))
    assert any(p['name'].startswith('Tortilla') for p in fuzzy_smae('tortila'))


def test_english_alias_finds_smae_in_mexico(monkeypatch):
    from src import search_smart, api_client
    monkeypatch.setattr(api_client, 'search_by_name', lambda *a, **k: [])
    prods, _ = search_smart.smart_search('banana', {'mode': 'vegetarian', 'countries': {'tags': ['en:mexico'], 'cc': 'mx'}})
    assert prods and prods[0]['name'] == 'Plátano'


def test_localstorage_empty_marker_counts_as_ready():
    from src.storage import _interpret, _EMPTY
    assert _interpret(0) == (False, None)
    assert _interpret(None) == (False, None)
    assert _interpret(_EMPTY) == (True, None)
    assert _interpret({'a': 1}) == (True, {'a': 1})


def test_country_quick_switch_remembers_recent():
    from src.countries import apply_country, ordered_ids, country_cid
    s = {'countries': {'tags': ['en:mexico'], 'cc': 'mx'}, 'recent_countries': ['mx']}
    apply_country(s, 'it')
    assert s['countries']['cc'] == 'it' and country_cid(s['countries']) == 'it'
    assert s['recent_countries'][:2] == ['it', 'mx']
    assert ordered_ids(s['recent_countries'])[:2] == ['it', 'mx']
    apply_country(s, 'nowhere')  # ignored
    assert s['countries']['cc'] == 'it'


def test_generic_flour_is_gluten_risk_but_corn_flour_is_not():
    from src.classifier import ProductClassifier
    c = ProductClassifier()
    g = {'allergies_gluten': True}
    for text in ('harina enriquecida, azúcar', 'flour, sugar', 'wheat flour', 'malt extract'):
        assert any('Gluten' in v for v in c.classify(text, g)['violations']), text
    for text in ('harina de maíz nixtamalizada, sal', 'corn flour, salt', 'rice flour', 'harina de arroz'):
        assert not any('Gluten' in v for v in c.classify(text, g)['violations']), text


def test_search_hit_tags_give_ingredients_and_declared_allergens():
    from src.api_client import _format_search_hit
    hit = {'code': '1', 'product_name': 'Cookie', 'ingredients_tags': ['en:oat-flake', 'en:sugar'],
           'allergens_tags': [], 'traces_tags': ['en:sesame-seeds'],
           'ingredients_analysis_tags': ['en:vegan', 'en:vegetarian']}
    p = _format_search_hit(hit)
    assert p['ingredients'] == 'oat flake, sugar' and p['_needs_full_load'] is True
    v = verdict(p, {'mode': 'vegan', 'allergies_sesame': True})
    assert v['status'] == 'no' and 'traces' in v['reasons'][0]['text']
    assert verdict(p, {'mode': 'vegan'})['status'] == 'ok'


def test_filter_query_excludes_allergens():
    from src.api_client import build_filter_query
    q = build_filter_query('en:biscuits', ['en:mexico'], 'en:vegan', ['en:gluten'])
    assert 'NOT allergens_tags:"en:gluten"' in q and 'NOT traces_tags:"en:gluten"' in q
    assert q.startswith('categories_tags:"en:biscuits" AND (countries_tags:"en:mexico")')


def test_unparsed_ingredients_never_ok_with_allergies():
    garbage = {'id': 'g', 'name': 'Breakfast biscuit', 'ingredients': 'хранителни стойности 450 kcal',
               '_off_tags': {'is_vegan': None, 'is_vegetarian': True},
               '_ingredients_tags_text': '', '_ingr_parsed_n': None}
    v = verdict(garbage, {'mode': 'vegetarian', 'allergies_gluten': True})
    assert v['status'] == 'unknown'
    assert v['reasons'][-1]['reason_key'] == 'verdict_ingredients_unverified'
    # without allergies/restrictions the diet tag alone is enough
    assert verdict(garbage, {'mode': 'vegetarian'})['status'] == 'ok'


def test_tag_text_catches_spelt_when_label_language_unknown():
    p = {'id': 's', 'name': 'Dinkel Doppelkeks', 'ingredients': 'Dinkelmehl, Zucker',
         '_ingredients_tags_text': 'spelt flour, sugar', '_ingr_parsed_n': 2, '_ingr_unknown_n': 0,
         '_off_tags': {'is_vegan': True, 'is_vegetarian': True}}
    assert verdict(p, {'mode': 'vegan', 'allergies_gluten': True})['status'] == 'no'


def test_one_failing_category_level_keeps_the_others():
    cats = ['en:a', 'en:b']
    orig = P('Orig', 'sugar', categories_tags=cats)
    ok = P('Alt', 'sugar', categories_tags=cats)

    def flaky(cat, *a):
        if cat == 'en:b':
            raise TimeoutError('slow')
        return [dict(ok)]
    assert [r['name'] for r in find_alternatives(orig, {'mode': 'vegan'}, search_fn=flaky)] == ['Alt']


def test_alternatives_report_incomplete_on_network_failure():
    from src.alternatives import find_alternatives_ex
    orig = P('Orig', 'sugar', categories_tags=['en:a', 'en:b'])

    def down(*a):
        raise TimeoutError('slow')
    alts, incomplete = find_alternatives_ex(orig, {'mode': 'vegan'}, search_fn=down)
    assert alts == [] and incomplete is True
    alts, incomplete = find_alternatives_ex(orig, {'mode': 'vegan'}, search_fn=lambda *a: [])
    assert alts == [] and incomplete is False
