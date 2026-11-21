"""USDA SR Legacy generic-food database: parse output, search, alternatives (no network)."""
import json
from pathlib import Path

import pytest

from src import usda_client, search_smart as ss, api_client
from src.alternatives import find_alternatives_ex, prep_state
from src.replace import equivalent
from src.ui_helpers import diet_source_label

UK = {'mode': 'vegetarian', 'countries': {'tags': ['en:united-states'], 'cc': 'us'}}  # USDA is the US table
UK_WORDS = 'gb'  # query translation for UK English words
ES = {'mode': 'vegetarian', 'countries': {'tags': ['en:spain'], 'cc': 'es'}}


@pytest.fixture(autouse=True)
def no_off(monkeypatch):
    monkeypatch.setattr(api_client, 'search_by_name', lambda *a, **k: [])


def _names(res):
    return [p['name'] for p in res]


def test_db_loads_and_shape():
    db = json.loads((Path(usda_client.__file__).parent / 'usda_db.json').read_text(encoding='utf-8'))
    assert 3000 < len(db) < 8000
    assert all(e['i'].startswith('usda_') and e['n'] and 'kcal' in e['nu'] for e in db)
    cats = {e['c'] for e in db}
    assert not cats & {'Beef Products', 'Poultry Products', 'Finfish and Shellfish Products',
                       'Baby Foods', 'Fast Foods'}
    # animal-named foods are dropped
    assert not any('chicken' in e['n'].lower() or 'bacon' in e['n'].lower() for e in db)


def test_product_shape():
    p = usda_client.search_by_name('cooked rice')[0]
    assert p['_source'] == 'usda' and p['id'].startswith('usda_')
    assert p['nutrition']['Energy (kcal)'] == 130 and 'Protein (g)' in p['nutrition']
    assert p['serving_size'] == '1 cup (158 g)' and p['_usda_portion_g'] == 158
    assert p['_off_tags'] == {'is_vegan': True, 'is_vegetarian': True}
    assert p['countries_tags'] == []


@pytest.mark.parametrize('q,settings', [('cooked rice', UK), ('arroz cocido', ES)])
def test_cooked_rice_first(q, settings):
    res, failed = ss.smart_search(q, settings)
    assert not failed
    assert 'rice' in res[0]['name'].lower() and 'cooked' in res[0]['name'].lower()
    assert 'white' in ' '.join(_names(res[:3])).lower()


def test_uk_and_spanish_words():
    res = usda_client.search_by_name('aubergine', cc=UK_WORDS)
    assert res and all('eggplant' in n.lower() for n in _names(res[:2]))
    res, _ = ss.smart_search('patata hervida', ES)
    assert 'potatoes, boiled' in res[0]['name'].lower()
    res = usda_client.search_by_name('courgette', cc=UK_WORDS)
    assert 'squash, summer, zucchini' in res[0]['name'].lower() or 'zucchini' in res[0]['name'].lower()


def test_typo_and_plural():
    assert 'banana' in usda_client.fuzzy_usda('bananna')[0]['name'].lower()
    assert usda_client.search_by_name('potatoes')


def test_mexico_keeps_smae_first(monkeypatch):
    mx = {'mode': 'vegetarian', 'countries': {'tags': ['en:mexico'], 'cc': 'mx'}}
    res, _ = ss.smart_search('arroz cocido', mx)
    assert res[0]['_source'] == 'smae'


def test_dairy_not_vegan():
    milk = usda_client.search_by_name('milk whole')[0]
    assert milk['_off_tags'] == {'is_vegan': False, 'is_vegetarian': True}
    from src.verdict import verdict
    assert verdict(milk, {'mode': 'vegan'})['status'] == 'no'
    assert verdict(milk, {'mode': 'vegetarian'})['status'] == 'ok'


def test_diet_source_label_and_i18n():
    from src.filtering import resolve_diet
    rice = usda_client.search_by_name('cooked rice')[0]
    assert resolve_diet(rice, UK)['source'] == 'usda'
    assert 'USDA' in diet_source_label('usda')


def test_equivalent_rice_to_pasta():
    rice = usda_client.search_by_name('cooked rice')[0]
    pasta = usda_client.search_by_name('spaghetti cooked')[0]
    eq = equivalent(rice, pasta, 300, 'kcal')
    assert 200 < eq['alt_grams'] < 450 and eq['alt_portions'] and eq['similarity'] > 70


def test_prep_state():
    assert prep_state('Rice, white, cooked') == 'cooked'
    assert prep_state('Pasta, dry, enriched') == 'dry'
    assert prep_state('Arroz cocido') == 'cooked' and prep_state('Apple') is None
    assert prep_state('Potatoes, french fried, frozen, unprepared') == 'frozen'


def test_alternatives_same_state_first():
    rice = usda_client.search_by_name('cooked rice')[0]
    def boom(*a, **k):
        raise AssertionError('OFF search must not be used for USDA products')
    alts, incomplete = find_alternatives_ex(rice, UK, n=5, search_fn=boom)
    assert not incomplete and len(alts) == 5
    for a in alts:
        assert a['_verdict']['status'] == 'ok'
        assert prep_state(a['name']) == 'cooked', a['name']
        assert a['id'] != rice['id']


def test_carbs_are_available_carbs():
    # USDA lentils (cooked): carbs by difference 20.13 g, fiber 7.9 g -> 12.23 g
    p = usda_client.search_by_name('lentils boiled')[0]
    n = p['nutrition']
    assert n['Fiber (g)'] == 7.9
    assert n['Carbohydrates (g)'] == pytest.approx(20.13 - 7.9, abs=0.02)
