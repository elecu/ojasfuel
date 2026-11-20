import pytest

from src import smae_client
from src.replace import (MATCH_BASES, equivalent, main_differences, rank_by_similarity,
                         totals, level_for, parse_serving_grams)


def _p(q):
    return smae_client.search_by_name(q)[0]


@pytest.fixture(scope='module')
def foods():
    return _p('arroz cocido'), _p('pasta cocida'), _p('papa cocida')


def test_rice_to_pasta_kcal(foods):
    rice, pasta, _ = foods
    eq = equivalent(rice, pasta, 300, 'kcal')
    assert eq['alt_grams'] == pytest.approx(295, abs=3)
    assert 55 <= eq['similarity'] <= 70 and eq['level'] == 'partial'
    assert eq['alt_portions'] == pytest.approx(4.9, abs=0.1)
    assert eq['portion_grams'] == 60
    assert main_differences(eq)[0][0] == 'carbs'


def test_rice_to_potato_kcal(foods):
    rice, _, potato = foods
    eq = equivalent(rice, potato, 300, 'kcal')
    assert eq['alt_grams'] == pytest.approx(441, abs=5)
    assert eq['similarity'] >= 90 and eq['level'] == 'very'


def test_basis_changes_grams(foods):
    rice, pasta, _ = foods
    k = equivalent(rice, pasta, 300, 'kcal')['alt_grams']
    c = equivalent(rice, pasta, 300, 'carbs')['alt_grams']
    p = equivalent(rice, pasta, 300, 'protein')['alt_grams']
    assert len({k, c, p}) == 3


def test_missing_basis_none(foods):
    rice, pasta, _ = foods
    no_fat = {**pasta, 'nutrition': {k: v for k, v in pasta['nutrition'].items() if k != 'Fat (g)'}}
    assert equivalent(rice, no_fat, 300, 'fat') is None
    assert equivalent(rice, pasta, 300, 'bogus') is None


def test_portions_from_serving_text():
    p = {'serving_size': '1/2 taza (60 g)', 'nutrition': {'Energy (kcal)': 100}}
    assert parse_serving_grams(p) == (60.0, '1/2 taza (60 g)')
    rice = {'nutrition': {'Energy (kcal)': 100, 'Protein (g)': 1, 'Carbohydrates (g)': 20, 'Fat (g)': 0.5}}
    alt = {**p, 'nutrition': {'Energy (kcal)': 100, 'Protein (g)': 2, 'Carbohydrates (g)': 20, 'Fat (g)': 0.5}}
    eq = equivalent(rice, alt, 120, 'kcal')
    assert eq['alt_grams'] == 120 and eq['alt_portions'] == 2.0


def test_levels():
    assert [level_for(x) for x in (100, 85, 84, 70, 69, 50, 49, 0)] == \
        ['very', 'very', 'similar', 'similar', 'partial', 'partial', 'low', 'low']


def test_totals_missing(foods):
    rice = foods[0]
    t = totals({'nutrition': {'Energy (kcal)': 200}}, 50)
    assert t == {'kcal': 100.0, 'protein': None, 'carbs': None, 'fat': None}
    assert totals(rice, 100)['kcal'] == pytest.approx(127.66)


def test_rank(foods):
    rice, pasta, potato = foods
    r = rank_by_similarity(rice, [pasta, {'name': 'x', 'nutrition': {}}, potato], 300, 'kcal')
    assert [c['name'] for c, _ in r] == [potato['name'], pasta['name']]
