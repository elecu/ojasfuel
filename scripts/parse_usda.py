"""Build src/usda_db.json from the USDA FoodData Central "SR Legacy" CSV export.

Usage:  python3 -I scripts/parse_usda.py <input_dir> <output_json>

SR Legacy (2018) is U.S. government data, public domain.
Only vegetarian-relevant categories are kept, and any food whose description
names an animal (meat, fish, gelatin, lard...) is dropped. Nutrients are per
100 g, stored under short keys (mapped back to display names by usda_client).
"""

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Category name -> kept? (names as in food_category.csv)
KEEP = {
    'Cereal Grains and Pasta', 'Legumes and Legume Products', 'Fruits and Fruit Juices',
    'Vegetables and Vegetable Products', 'Nut and Seed Products', 'Dairy and Egg Products',
    'Fats and Oils', 'Baked Products', 'Breakfast Cereals', 'Snacks', 'Sweets',
    'Beverages', 'Soups, Sauces, and Gravies', 'Spices and Herbs',
}

# USDA nutrient id -> short key (units already g / mg / ug per 100 g)
NUTRIENTS = {
    '1008': 'kcal', '1003': 'p', '1004': 'f', '1005': 'c', '1079': 'fib', '2000': 'sug',
    '1258': 'sat', '1093': 'na', '1092': 'k', '1087': 'ca', '1089': 'fe', '1090': 'mg',
    '1095': 'zn', '1162': 'vc', '1106': 'va', '1177': 'b9', '1178': 'b12', '1114': 'vd',
    '1253': 'chol', '1018': 'alc', '1057': 'caf',
}
EXPECTED_UNITS = {'1008': 'KCAL', '1003': 'G', '1004': 'G', '1005': 'G', '1079': 'G',
                  '2000': 'G', '1258': 'G', '1093': 'MG', '1092': 'MG', '1087': 'MG',
                  '1089': 'MG', '1090': 'MG', '1095': 'MG', '1162': 'MG', '1106': 'UG',
                  '1177': 'UG', '1178': 'UG', '1114': 'UG', '1253': 'MG', '1018': 'G',
                  '1057': 'MG'}

# Animal-derived words anywhere in the description -> drop the food
_ANIMAL = re.compile(
    r'\b(beef|pork|chicken|turkey|bacon|ham|lamb|veal|fish|tuna|salmon|shrimp|crab|lobster|'
    r'clams?|oysters?|sausages?|pepperoni|salami|bologna|lard|tallow|gelatins?|anchov\w*|'
    r'sardines?|duck|goose|liver|suet|meat|frankfurters?|hot dog|jerky|venison|rabbit|'
    r'caviar|roe|escargot|squab|bison|elk|game|oxtail|bouillon|broth|stock|mollusks?|'
    r'crayfish|cod|trout|herring|mackerel|bass|catfish|haddock|shark|squid|octopus|'
    r'whale|seal|tripe|giblets?|gizzards?|kidney|brain|tongue|marrow|spleen|lungs?|'
    r'heart|gumdrops?|gummi\w*|marshmallows?|chitterlings|capon|cornish|emu|ostrich|pheasant|quail|goat|horse|moose)\b',
    re.I)
_MEATLESS = re.compile(r'meatless|meat substitute|meat analog|meat extender|imitation meat|'
                       r'imitation (bacon|sausage)|vegetarian (bacon|sausage|meat)', re.I)
_FISH_NOT = re.compile(r'(fish|egg|sea) ?(substitute)|heart of palm|hearts of palm|artichoke heart|'
                       r'bass? ?\bbeans|ham ?burger', re.I)

_FRAC = {0.25: '1/4', 0.33: '1/3', 0.5: '1/2', 0.67: '2/3', 0.75: '3/4', 0.125: '1/8',
         0.13: '1/8', 0.12: '1/8', 0.38: '3/8', 0.62: '5/8', 0.88: '7/8', 0.17: '1/6',
         0.2: '1/5', 0.1: '1/10'}


def _fmt_amount(a: float) -> str:
    if a == int(a):
        return str(int(a))
    whole, frac = int(a), round(a - int(a), 2)
    f = _FRAC.get(frac)
    if f:
        return f'{whole} {f}' if whole else f
    return f'{a:g}'


# Animal-derived even though the name has no animal word:
# gravies (meat stock), au jus, Worcestershire & Caesar (anchovies), wonton soup (pork)
_HIDDEN_ANIMAL = re.compile(r'\bgravy\b|\bau jus\b|worcestershire|\bcaesar\b|soup, wonton', re.I)


def is_animal(desc: str) -> bool:
    if _HIDDEN_ANIMAL.search(desc):
        return True
    if _MEATLESS.search(desc) or _FISH_NOT.search(desc):
        # allow, but still drop if another animal word remains
        stripped = _MEATLESS.sub(' ', _FISH_NOT.sub(' ', desc))
        return bool(_ANIMAL.search(stripped))
    return bool(_ANIMAL.search(desc))


def _clean(s: str) -> str:
    s = re.sub(r'\([^)]*\)', '', s or '')
    return re.sub(r'\s+', ' ', s).strip(' ,')


def _portion_candidates(rows, units, category):
    out = []
    for r in rows:
        try:
            g = float(r['gram_weight'])
            amt = float(r['amount'] or 1)
        except ValueError:
            continue
        if g <= 0 or amt <= 0:
            continue
        unit = units.get(r['measure_unit_id'], '')
        unit = '' if unit == 'undetermined' else unit
        desc = _clean(r['portion_description'])
        mod = _clean(r['modifier'])
        text = ' '.join(x for x in (unit, desc, mod) if x).lower()
        if re.match(r'^(oz|ounces?|fl oz|lb|pounds?|quart|pint|gallon|liter|ml|tsp|teaspoon|g)\b', text) \
                and not re.search(r'\b(cup|slice|piece|medium)\b', text):
            continue
        tbsp_first = category in ('Spices and Herbs', 'Fats and Oils')
        if re.search(r'\bcup\b', text):
            tier = 1 if tbsp_first else 0
        elif re.search(r'\b(tbsp|tablespoon)\b', text):
            tier = 0 if tbsp_first else 3
        elif re.search(r'\b(medium|piece|slice|patty|fruit|each|small|large|cookie|roll|bar)\b', text):
            tier = 1 if not tbsp_first else 2
        elif re.search(r'\bserving\b', text):
            tier = 4
        else:
            tier = 5
        if g > 500:
            tier += 10
        label_unit = ' '.join(x for x in (unit, desc) if x)
        if mod and len(mod) <= 30:
            label_unit = f'{label_unit}, {mod}' if label_unit else mod
        if not label_unit:
            continue
        out.append((tier, int(r['seq_num'] or 99), amt, label_unit, g))
    return sorted(out)


def build(indir: Path) -> list[dict]:
    cats = {}
    with open(indir / 'food_category.csv', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            cats[r['id']] = r['description']

    foods = {}
    with open(indir / 'food.csv', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            cat = cats.get(r['food_category_id'])
            if cat in KEEP and not is_animal(r['description']):
                foods[r['fdc_id']] = {'i': 'usda_' + r['fdc_id'], 'n': re.sub(r"\s*\(Includes foods for USDA's Food Distribution Program\)", '', r['description']).strip(),
                                      'c': cat, 'nu': {}}

    units = {}
    with open(indir / 'measure_unit.csv', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            units[r['id']] = r['name']

    nut_units = {}
    with open(indir / 'nutrient.csv', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['id'] in NUTRIENTS:
                nut_units[r['id']] = r['unit_name'].upper()
    for nid, u in EXPECTED_UNITS.items():
        if nut_units.get(nid) != u:
            sys.exit(f'unexpected unit for nutrient {nid}: {nut_units.get(nid)} != {u}')

    with open(indir / 'food_nutrient.csv', newline='', encoding='utf-8') as f:
        rd = csv.reader(f)
        head = next(rd)
        i_fdc, i_nut, i_amt = head.index('fdc_id'), head.index('nutrient_id'), head.index('amount')
        for row in rd:
            fd = foods.get(row[i_fdc])
            key = NUTRIENTS.get(row[i_nut])
            if fd is None or key is None:
                continue
            try:
                val = float(row[i_amt])
            except ValueError:
                continue
            if val < 0:
                continue
            fd['nu'][key] = round(val, 2)

    # Carbohydrates: USDA 1005 is "carbohydrate, by difference" and INCLUDES fiber,
    # while UK/EU/Mexico labels (Open Food Facts, SMAE) report carbs EXCLUDING fiber.
    # Store available carbs (1005 - fiber) so "match by carbohydrates" compares
    # like with like. Fiber stays its own field; energy is left as USDA reports it.
    for fd in foods.values():
        nu = fd['nu']
        if 'c' in nu and 'fib' in nu:
            nu['c'] = round(max(0.0, nu['c'] - nu['fib']), 2)

    portions = {}
    with open(indir / 'food_portion.csv', newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['fdc_id'] in foods:
                portions.setdefault(r['fdc_id'], []).append(r)

    out = []
    for fid, fd in foods.items():
        if 'kcal' not in fd['nu']:
            continue  # unusable for equivalence
        cands = _portion_candidates(portions.get(fid, []), units, fd['c'])
        if cands:
            _, _, amt, unit, g = cands[0]
            g = round(g, 1)
            gs = f'{g:g}'
            fd['pl'] = f'{_fmt_amount(amt)} {unit} ({gs} g)'
            fd['pg'] = g
        else:
            fd['pl'], fd['pg'] = '100 g', 100.0
        out.append(fd)
    out.sort(key=lambda x: int(x['i'].split('_')[1]))
    return out


def main(argv):
    if len(argv) != 3:
        sys.exit('usage: parse_usda.py <input_dir> <output_json>')
    data = build(Path(argv[1]))
    Path(argv[2]).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                             encoding='utf-8')
    counts = Counter(d['c'] for d in data)
    for c, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f'{n:5d}  {c}')
    print(f'{len(data)} foods, {Path(argv[2]).stat().st_size / 1e6:.2f} MB')


if __name__ == '__main__':
    main(sys.argv)
