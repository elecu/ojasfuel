import pytest
from src.verdict import verdict
from src.alternatives import find_alternatives
from src import search_smart as ss
from src import smae_client


def P(name, ing, **kw):
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
    orig = P('Orig', 'oats', categories_tags=['en:cereals'], nutrition={'Energy (kcal)': 100, 'Protein (g)': 5})
    pool = [
        orig,
        P('Meat', 'chicken', nutrition={'Energy (kcal)': 100, 'Protein (g)': 5}),
        P('Milk', 'whole milk', nutrition={'Energy (kcal)': 100, 'Protein (g)': 5}),
        P('Peanut', 'peanuts', nutrition={'Energy (kcal)': 100, 'Protein (g)': 5}),
        P('Far', 'rice', nutrition={'Energy (kcal)': 400, 'Protein (g)': 1}),
        P('Near', 'wheat', nutrition={'Energy (kcal)': 105, 'Protein (g)': 5}),
        P('Unk', '', nutrition={'Energy (kcal)': 100}),
    ]
    s = {'mode': 'vegan', 'allergies_peanuts': True}
    res = find_alternatives(orig, s, n=5, search_fn=lambda q, cc: [dict(p) for p in pool])
    names = [r['name'] for r in res]
    assert names == ['Near', 'Far']
    assert all(r['_verdict']['status'] == 'ok' for r in res)


def test_find_alternatives_error():
    def boom(q, cc):
        raise RuntimeError('x')
    assert find_alternatives(P('a', 'b'), {}, search_fn=boom) == []


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
