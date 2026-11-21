"""Country-specific official food tables: UK CoFID, France CIQUAL (+ USDA fallback). No network."""
import json
import re
import sys
from pathlib import Path

import pytest

from src import api_client, food_tables, search_smart as ss, smae_client, usda_client
from src.alternatives import find_alternatives_ex, prep_state
from src.filtering import resolve_diet
from src.history import _SNAPSHOT_KEYS
from src.replace import equivalent, parse_serving_grams
from src.ui_helpers import diet_source_label
from src.verdict import verdict

SRC = Path(food_tables.__file__).parent


def _s(cc, tags=()):
    return {'mode': 'vegetarian', 'countries': {'tags': list(tags), 'cc': cc}}


UK, FR, ES, MX = _s('gb', ['en:united-kingdom']), _s('fr', ['en:france']), _s('es', ['en:spain']), \
    _s('mx', ['en:mexico'])


@pytest.fixture(autouse=True)
def no_off(monkeypatch):
    monkeypatch.setattr(api_client, 'search_by_name', lambda *a, **k: [])


def _first(q, settings):
    res, failed = ss.smart_search(q, settings)
    assert not failed and res, q
    return res[0]


def test_table_for_country():
    assert [food_tables.table_for_country(c) for c in ('mx', 'gb', 'fr', 'us', 'es', 'de', 'it', None)] \
        == ['smae', 'cofid', 'ciqual', 'usda', 'usda', 'usda', 'usda', 'usda']
    assert food_tables.is_reference_only('usda', 'es')
    assert not food_tables.is_reference_only('usda', 'us') and not food_tables.is_reference_only('usda', None)
    assert not food_tables.is_reference_only('cofid', 'gb')


@pytest.mark.parametrize('q', ['cooked rice', 'boiled potatoes', 'banana'])
def test_uk_uses_cofid(q):
    p = _first(q, UK)
    assert p['_source'] == 'cofid' and p['id'].startswith('cofid_') and not p.get('_reference_only')
    assert p['brand'].startswith('UK CoFID')


def test_uk_results_are_sensible():
    rice = _first('cooked rice', UK)
    assert 'rice' in rice['name'].lower() and 'boiled' in rice['name'].lower()
    assert 'banana' in _first('banana', UK)['name'].lower()
    assert 'aubergine' in _first('eggplant', UK)['name'].lower()      # US word -> UK table
    assert _first('arroz cocido', UK)['_source'] == 'cofid'             # Spanish words


@pytest.mark.parametrize('q', ['riz cuit', 'pomme de terre bouillie', 'banane', 'banana', 'plátano'])
def test_france_uses_ciqual(q):
    p = _first(q, FR)
    assert p['_source'] == 'ciqual' and p['id'].startswith('ciqual_') and not p.get('_reference_only')


def test_france_french_and_english_names():
    assert _first('riz cuit', FR)['name'].startswith('Riz')               # French query -> French name
    assert _first('banana', FR)['name'].lower().startswith('banana')      # English query -> English
    assert _first('plátano', FR)['name'].lower().startswith('banana')
    assert _first('lait', FR)['name'].lower().startswith('lait')           # not "laitue"
    p = _first('riz cuit', FR)
    assert p['_raw']['n'] and p['_raw']['nf'] and p['_name_lang'] == 'fr'


def test_other_countries_use_usda_as_reference():
    for st in (ES, _s('de'), _s('it'), _s('pl')):
        p = _first('banana', st)
        assert p['_source'] == 'usda' and p['_reference_only'] is True
    assert not _first('banana', _s('us')).get('_reference_only')
    assert not _first('banana', _s(None)).get('_reference_only')


def test_fallback_to_usda_when_own_table_has_few(monkeypatch):
    # some foods are missing from CIQUAL/CoFID => USDA fills in, flagged
    res, _ = ss.smart_search('tahini paste', UK)
    assert all(p['_source'] in ('cofid', 'usda') for p in res)
    for p in res:
        assert bool(p.get('_reference_only')) == (p['_source'] == 'usda')


def test_mexico_unchanged():
    assert _first('arroz cocido', MX)['_source'] == 'smae'


def test_products_shape():
    for src, q, cc in (('cofid', 'banana', 'gb'), ('ciqual', 'banane', 'fr')):
        p = food_tables.get_table(src).search_by_name(q, cc=cc)[0]
        assert p['_source'] == src and p['nutrition']['Energy (kcal)'] > 0
        assert {'Protein (g)', 'Fat (g)', 'Carbohydrates (g)'} <= set(p['nutrition'])
        assert p['_table_category'] and p['_table_subgroup'] and p['countries_tags'] == []
        assert p['_table_portion_g'] is None and p['serving_size'] == ''   # no portions in these tables
        assert p['_off_tags'] == {'is_vegan': True, 'is_vegetarian': True}
        assert resolve_diet(p, UK)['source'] == src
        assert verdict(p, {'mode': 'vegan'})['status'] == 'ok'


def test_banana_per_table():
    kcal = {}
    for src, cc in (('cofid', 'gb'), ('ciqual', 'fr'), ('usda', 'us')):
        kcal[src] = food_tables.get_table(src).search_by_name('banana', cc=cc)[0]['nutrition']['Energy (kcal)']
    kcal['smae'] = smae_client.search_by_name('plátano')[0]['nutrition']['Energy (kcal)']
    print('banana kcal/100g:', kcal)
    assert all(v > 40 for v in kcal.values())
    assert kcal['cofid'] == 81 and kcal['usda'] == 89  # CoFID and USDA differ: each country sees its own


def test_dairy_and_egg_not_vegan():
    for src, q, cc in (('cofid', 'milk whole', 'gb'), ('cofid', 'eggs', 'gb'), ('ciqual', 'oeuf', 'fr'),
                       ('ciqual', 'lait entier', 'fr'), ('ciqual', 'fromage', 'fr')):
        p = food_tables.get_table(src).search_by_name(q, cc=cc)[0]
        assert p['_off_tags']['is_vegan'] is False and p['_off_tags']['is_vegetarian'] is True, p['name']
        assert verdict(p, {'mode': 'vegan'})['status'] == 'no'
        assert verdict(p, {'mode': 'vegetarian'})['status'] == 'ok'


def test_plant_alternatives_are_vegan():
    p = food_tables.get_table('ciqual').search_by_name('soy drink', cc='fr')
    assert any(x['_off_tags']['is_vegan'] for x in p), [x['name'] for x in p]


def test_uncertain_dishes_not_ok_for_vegan():
    t = food_tables.get_table('ciqual')
    sandwich = [p for p in t.search_by_name('sandwich', 30, 'fr') if 'average' in p['name'].lower()
                or 'moyen' in p['name'].lower()]
    assert sandwich and all(p['_off_tags']['is_vegetarian'] is None for p in sandwich)
    assert verdict(sandwich[0], {'mode': 'vegetarian'})['status'] != 'ok'


# ── database audits ──────────────────────────────────────────────────────────
_SUSPICIOUS = re.compile(
    r"\b(beef|pork|chicken|turkey|bacon|ham|lamb|veal|fish|tuna|salmon|shrimps?|prawns?|crab|lobster|"
    r"clams?|oysters?|mussels?|sausages?|salami|lard|tallow|gelatin\w*|anchov\w*|sardines?|duck|"
    r"liver|suet|meat|jerky|venison|rabbit|caviar|squid|octopus|cod|trout|herring|mackerel|"
    r"boeuf|veau|porc|poulet|dinde|jambon|saucisse|saucisson|lardons?|viande|poisson|thon|saumon|"
    r"crevettes?|moules?|huitres?|gelatine|anchois|volaille|canard|agneau|mouton|foie|rillettes?|"
    r"bouillon de (viande|volaille|boeuf)|fond de veau|surimi|escargots?)\b", re.I)
# vegetarian foods that legitimately contain a flagged word
_AUDIT_OK = re.compile(r"substitut|substitute|vegetari|vegetal|vegan|plant-based|soy|soja|"
                       r"tofu|seitan|quorn|veggie|meat[- ]free|meatless|sans (viande|poisson)|"
                       r"fish-free|pasta|ham ?burger|hambourgeois|"
                       r"eggs?,? (chicken|duck|goose|quail)|(duck|chicken|goose|quail) eggs?|"
                       r"oeufs? (de )?(canard|caille|oie|poule)", re.I)


@pytest.mark.parametrize('fname', ['cofid_db.json', 'ciqual_db.json'])
def test_no_meat_or_fish_in_db(fname):
    db = json.loads((SRC / fname).read_text(encoding='utf-8'))
    bad = []
    for e in db:
        for name in (e['n'], e.get('nf', '')):
            if _SUSPICIOUS.search(name) and not _AUDIT_OK.search(name):
                bad.append(name)
    print(fname, len(db), 'foods; suspicious names:', sorted(set(bad)))
    assert not bad, sorted(set(bad))[:20]


@pytest.mark.parametrize('fname,prefix,lo,hi', [('cofid_db.json', 'cofid_', 1500, 2500),
                                                ('ciqual_db.json', 'ciqual_', 1500, 3200)])
def test_db_shape(fname, prefix, lo, hi):
    db = json.loads((SRC / fname).read_text(encoding='utf-8'))
    assert lo < len(db) < hi
    assert all(e['i'].startswith(prefix) and e['n'] and e['c'] and 'kcal' in e['nu'] for e in db)
    assert len({e['i'] for e in db}) == len(db)
    assert not any(k in e for e in db for k in ('pg', 'pl'))  # no portions published
    if prefix == 'ciqual_':
        assert all(e.get('nf') for e in db)
        groups = {e['c'] for e in db}
        assert 'meat, egg and fish' in groups  # only eggs + meat substitutes remain there
        assert {e['s'] for e in db if e['c'] == 'meat, egg and fish'} == {'eggs', 'meat substitute'}
    else:
        assert not any(e['g'][0] in 'JM' for e in db)


def test_traces_and_missing_values():
    ciq = {e['i']: e for e in json.loads((SRC / 'ciqual_db.json').read_text(encoding='utf-8'))}
    cof = {e['i']: e for e in json.loads((SRC / 'cofid_db.json').read_text(encoding='utf-8'))}
    # CIQUAL: "< 0,5" fat of raw banana -> 0 ; "-" stays missing (no key)
    assert ciq['ciqual_13005']['nu']['f'] == 0.0 and ciq['ciqual_13005']['nu']['kcal'] == 90.5
    # CoFID: "Tr" fibre of easy-cook basmati rice -> 0
    assert cof['cofid_11-860']['nu']['fib'] == 0.0


def test_carbs_are_available_carbs():
    # CIQUAL white rice cooked: Glucides 31.8 g (fibre 0.8 g separate), CoFID long grain boiled 31.1 g
    rice = food_tables.get_table('ciqual').search_by_name('riz cuit', cc='fr')[0]['nutrition']
    assert rice['Carbohydrates (g)'] == 31.8 and rice['Fiber (g)'] == 0.8
    assert food_tables.get_table('cofid').search_by_name('cooked rice', cc='gb')[0]['nutrition']['Carbohydrates (g)'] == 31.1


# ── replace / alternatives ───────────────────────────────────────────────────
def test_equivalent_rice_to_pasta_cofid():
    t = food_tables.get_table('cofid')
    rice = t.search_by_name('cooked rice', cc='gb')[0]
    pasta = t.search_by_name('pasta boiled', cc='gb')[0]
    eq = equivalent(rice, pasta, 200, 'kcal')
    assert eq and 100 < eq['alt_grams'] < 400 and eq['similarity'] > 60
    assert eq['alt_portions'] is None      # no portions in CoFID: the UI hides the portions toggle
    assert parse_serving_grams(pasta) == (None, '')


def test_parse_serving_grams_generic_key():
    assert parse_serving_grams({'_table_portion_g': 158, 'serving_size': '1 cup (158 g)'})[0] == 158
    assert parse_serving_grams({'_usda_portion_g': 30})[0] == 30


@pytest.mark.parametrize('src,q,cc,settings', [('cofid', 'cooked rice', 'gb', UK),
                                               ('ciqual', 'riz cuit', 'fr', FR),
                                               ('ciqual', 'cooked rice', 'fr', FR)])
def test_alternatives_same_state(src, q, cc, settings):
    rice = food_tables.get_table(src).search_by_name(q, cc=cc)[0]

    def boom(*a, **k):
        raise AssertionError('OFF search must not be used for table products')
    alts, incomplete = find_alternatives_ex(rice, settings, n=5, search_fn=boom)
    assert not incomplete and len(alts) >= 3
    assert prep_state(rice['name']) == 'cooked'
    for a in alts:
        assert a['_verdict']['status'] == 'ok'
        assert a['_source'] == src and a['id'] != rice['id']
        assert prep_state(a['name']) == 'cooked', a['name']
        assert a['_name_lang'] == rice['_name_lang']


def test_prep_state_french():
    assert prep_state('Riz blanc, cuit, non salé') == 'cooked'
    assert prep_state('Pomme de terre, bouillie/cuite à l\'eau') == 'cooked'
    assert prep_state('Carotte, crue') == 'raw'
    assert prep_state('Épinard, surgelé, cru') == 'raw' or prep_state('Épinard, surgelé') == 'frozen'
    assert prep_state('Haricots verts, appertisés') == 'canned'
    assert prep_state('Pomme de terre, rôtie/cuite au four') == 'cooked'
    assert prep_state('Lentille, sèche') == 'dry'


# ── plumbing ─────────────────────────────────────────────────────────────────
def test_labels_history_and_gluten():
    assert 'CoFID' in diet_source_label('cofid') and 'CIQUAL' in diet_source_label('ciqual')
    for k in ('_table_category', '_table_subgroup', '_table_portion_g', '_name_lang', '_reference_only'):
        assert k in _SNAPSHOT_KEYS
    banana = food_tables.get_table('cofid').search_by_name('banana', cc='gb')[0]
    assert ss._is_gluten_free(banana)
    bread = food_tables.get_table('cofid').search_by_name('bread white', cc='gb')[0]
    assert not ss._is_gluten_free(bread)


def test_usda_wrapper_still_works():
    p = usda_client.search_by_name('cooked rice')[0]
    assert p['_source'] == 'usda' and p['_usda_category'] and p['_table_category'] == p['_usda_category']
    assert usda_client.usda_by_category('Fruits and Fruit Juices', limit=5)


def test_i18n_parity_and_keys():
    from src import i18n
    en, es = i18n._TRANSLATIONS['en'], i18n._TRANSLATIONS['es']
    assert set(en) == set(es), sorted(set(en) ^ set(es))[:10]
    for k in ('diet_source_cofid', 'diet_source_ciqual', 'cofid_credit', 'ciqual_credit',
              'table_reference_only', 'table_source_cofid', 'table_source_ciqual'):
        assert en[k] and es[k]
    assert 'Open Government Licence v3.0' in en['cofid_credit'] and 'CC-BY 4.0' in en['ciqual_credit']
