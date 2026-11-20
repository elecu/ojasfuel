import pytest
from src.classifier import ProductClassifier
from src.api_client import extract_nutrition, _nutrition_to_write_fields
from src import smae_client
from src.barcode import barcode_variants, is_barcode, normalize_barcode
from src.filtering import resolve_diet, classify_results, allergy_violations

C = ProductClassifier()


@pytest.mark.parametrize('text', [
    'coconut milk, sugar', 'leche de soya, azúcar', 'cocoa butter, sugar',
    'almond drink', 'manteca de cacao', 'lait de coco', 'Hafermilch', 'cream of tartar',
])
def test_plant_based_vegan(text):
    assert C.classify(text)['is_vegan'] is True


def test_whole_milk_not_vegan():
    r = C.classify('whole milk, sugar')
    assert r['is_vegan'] is False and r['is_vegetarian'] is True


def test_chicken_not_vegetarian():
    assert C.classify('chicken, salt')['is_vegetarian'] is False


def test_dedupe_matches():
    r = C.classify('butter, butter')
    assert r['dairy_or_eggs_found'].count('butter') == 1


def test_violation_kinds():
    r = C.classify('peanut oil, milk', {'mode': 'vegan', 'allergies_peanuts': True})
    assert len(r['violations']) == len(r['violation_kinds'])
    assert allergy_violations(r) and all('allergy' in v.lower() for v in allergy_violations(r))


def test_extract_nutrition():
    n = extract_nutrition({'energy-kcal_100g': 539, 'sodium_100g': 0.4, 'proteins_100g': 6})
    assert n['Energy (kcal)'] == 539
    assert n['Sodium (mg)'] == pytest.approx(400)
    assert n['Protein (g)'] == 6
    assert extract_nutrition({'energy-kj_100g': 418.4})['Energy (kcal)'] == pytest.approx(100, abs=0.1)


def test_write_fields_units():
    f = _nutrition_to_write_fields({'nutriment_sodium_100g': 400, 'nutriment_energy-kcal_100g': 50})
    assert f['nutriment_sodium'] == '400' and f['nutriment_sodium_unit'] == 'mg'
    assert f['nutriment_energy-kcal_unit'] == 'kcal' and f['nutrition_data_per'] == '100g'


def test_smae_normalised_per_100g():
    p = smae_client.search_by_name('Acelga cruda')[0]
    assert p['id'] == 'smae_0001'
    assert p['nutrition']['Energy (kcal)'] == pytest.approx(22.4, abs=0.2)
    assert p['_smae_portion_g'] == 98
    assert '(98 g)' in p['serving_size']
    assert p['_smae_group'] == 'Verduras'


def test_barcode_variants():
    v = barcode_variants('036000291452')
    assert v[0] == '036000291452' and '0036000291452' in v
    assert normalize_barcode('3017-6204 22003') == '3017620422003'
    assert is_barcode('3017620422003') and not is_barcode('abc12345')
    # UPC-E 01234565 -> UPC-A 012345000065
    assert '012345000065' in barcode_variants('01234565')


def test_resolve_diet_priority():
    p = {'ingredients': 'milk', '_off_tags': {'is_vegan': True, 'is_vegetarian': True}}
    d = resolve_diet(p, {})
    assert d['source'] == 'off' and d['is_vegan'] is True
    assert resolve_diet({'ingredients': 'chicken'}, {})['source'] == 'ingredients'
    assert resolve_diet({'ingredients': ''}, {})['source'] == 'none'
    out = classify_results([{'ingredients': 'chicken'}, {'ingredients': 'rice'}], {'mode': 'vegetarian'})
    assert len(out) == 1


def test_smae_corrupt_mixed_dishes_excluded():
    from src.smae_client import search_by_name
    assert search_by_name('frijoles puercos') == []
    assert search_by_name('enfrijoladas') == []


def test_smae_alcohol_group_not_blindly_vegan():
    from src.smae_client import search_by_name
    from src.filtering import resolve_diet
    rompope = search_by_name('rompope')[0]
    assert resolve_diet(rompope, {'mode': 'vegan'})['is_vegan'] is False
    tequila = search_by_name('tequila')[0]
    assert resolve_diet(tequila, {'mode': 'vegan'})['is_vegan'] is True


def test_off_maybe_vegan_never_claimed_vegan():
    from src.api_client import _parse_off_tags
    from src.filtering import resolve_diet
    p = {'ingredients': 'sugar, palm oil',
         '_off_tags': _parse_off_tags(['en:palm-oil', 'en:maybe-vegan', 'en:vegetarian'])}
    d = resolve_diet(p, {'mode': 'vegetarian'})
    assert d['is_vegan'] is None and d['is_vegetarian'] is True


def test_corrupted_stored_settings_are_ignored():
    from src.i18n import _valid_setting
    assert not _valid_setting('mode', 'Vegetarian')
    assert not _valid_setting('theme', 'Dark')
    assert _valid_setting('mode', 'vegan') and _valid_setting('theme', 'light')
