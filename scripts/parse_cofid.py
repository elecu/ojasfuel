"""Build src/cofid_db.json from the UK CoFID 2021 workbook.

Usage:  python3 -I scripts/parse_cofid.py <cofid_2021.xlsx> <output_json>

McCance and Widdowson's The Composition of Foods Integrated Dataset 2021
(Public Health England; Open Government Licence v3.0).  Needs openpyxl.

Choices:
 * 'Tr' (trace) -> 0; 'N' (present but not quantified) and blanks -> missing.
 * Carbohydrate in CoFID is already AVAILABLE carbohydrate (fibre excluded):
   stored as is. Energy = published kcal. Fibre = AOAC fibre.
 * Fish, meat and poultry groups (J*, M*) and any food whose name names an animal
   (or gelatin) are dropped; eggs and dairy are kept.
 * "weighed with skin/shell/bones" rows (edible-portion adjusted) are dropped:
   per 100 g of the food as bought they are not comparable with other foods.
 * Alcoholic beverages (group Q) are published per 100 ml: converted to per 100 g
   with the table's specific gravity.
 * CoFID has no household portions: no 'pl'/'pg' fields.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import food_filters  # noqa: E402

TOP = {
    'A': 'Cereals and cereal products', 'B': 'Milk and milk products', 'C': 'Eggs and egg dishes',
    'D': 'Vegetables, potatoes and pulses', 'F': 'Fruit', 'G': 'Nuts and seeds',
    'H': 'Herbs and spices', 'O': 'Fats and oils', 'P': 'Non-alcoholic beverages',
    'Q': 'Alcoholic beverages', 'S': 'Sugars, preserves and confectionery',
    'W': 'Soups, sauces and miscellaneous',
}
SUB = {
    'A': 'Cereal dishes', 'AA': 'Rice, pasta and grains', 'AB': 'Sandwiches', 'AC': 'Rice, pasta and grains',
    'AD': 'Rice, pasta and grains', 'AE': 'Pizza', 'AF': 'Bread', 'AG': 'Bread',
    'AI': 'Breakfast cereals', 'AK': 'Rusks', 'AM': 'Biscuits', 'AN': 'Cakes', 'AO': 'Pastry',
    'AP': 'Buns and scones', 'AS': 'Cereal puddings', 'AT': 'Other cereal products',
    'BA': 'Milk', 'BAB': 'Milk', 'BAE': 'Milk', 'BAH': 'Milk', 'BAK': 'Milk', 'BAR': 'Milk',
    'BC': 'Milk', 'BH': 'Milk drinks', 'BJC': 'Cream', 'BJP': 'Cream', 'BJS': 'Cream',
    'BL': 'Cheese', 'BN': 'Yogurt and fromage frais', 'BNE': 'Yogurt and fromage frais',
    'BNH': 'Yogurt and fromage frais', 'BNS': 'Yogurt and fromage frais',
    'BP': 'Ice cream and frozen desserts', 'BR': 'Milk puddings and desserts',
    'BTM': 'Baking fats and margarine', 'BV': 'Cheese dishes',
    'CA': 'Eggs', 'CD': 'Egg dishes', 'CDE': 'Egg dishes', 'CDH': 'Egg dishes',
    'D': 'Vegetables', 'DA': 'Potato products', 'DAE': 'Potatoes', 'DAM': 'Potatoes',
    'DAP': 'Potato chips', 'DAR': 'Potato chips', 'DB': 'Pulses', 'DF': 'Peas',
    'DG': 'Vegetables', 'DI': 'Dried vegetables', 'DR': 'Vegetable dishes',
    'F': 'Fruit', 'FA': 'Fruit', 'FC': 'Fruit juices', 'G': 'Nuts and seeds', 'GA': 'Nuts and seeds',
    'H': 'Herbs and spices', 'OA': 'Butter and spreads', 'OB': 'Butter and spreads',
    'OC': 'Vegetable oils', 'OE': 'Vegetable fats', 'OF': 'Other fats',
    'P': 'Hot drinks', 'PA': 'Hot drinks', 'PAA': 'Hot drinks', 'PAC': 'Hot drinks',
    'PCA': 'Soft drinks', 'PCC': 'Soft drinks', 'PE': 'Fruit juice drinks',
    'Q': 'Spirits and mixers', 'QA': 'Beer', 'QC': 'Cider', 'QE': 'Wine', 'QF': 'Fortified wine',
    'QG': 'Fortified wine', 'QI': 'Liqueurs', 'QK': 'Spirits',
    'S': 'Icing and curds', 'SC': 'Sugars and spreads', 'SEA': 'Chocolate confectionery',
    'SEC': 'Sweets', 'SN': 'Snacks', 'SNA': 'Crisps', 'SNC': 'Snacks',
    'WA': 'Soups', 'WAA': 'Soups', 'WAC': 'Soups', 'WAE': 'Soups', 'WC': 'Sauces',
    'WCD': 'Sauces', 'WCG': 'Sauces', 'WCN': 'Sauces', 'WE': 'Chutneys', 'WY': 'Miscellaneous',
}
DROP_TOP = {'J', 'M'}          # fish and meat/poultry groups
DROP_SUB = {'OF'}              # animal fats (lard, dripping, ghee: names checked anyway)
SPECIAL_KEEP = {('OF', 'ghee')}  # butter ghee is dairy

# short key -> (sheet, header text)
NUTRIENTS = {
    'kcal': ('1.3 Proximates', 'Energy (kcal) (kcal)'),
    'p': ('1.3 Proximates', 'Protein (g)'), 'f': ('1.3 Proximates', 'Fat (g)'),
    'c': ('1.3 Proximates', 'Carbohydrate (g)'), 'fib': ('1.3 Proximates', 'AOAC fibre (g)'),
    'sug': ('1.3 Proximates', 'Total sugars (g)'),
    'sat': ('1.3 Proximates', 'Satd FA /100g fd (g)'),
    'chol': ('1.3 Proximates', 'Cholesterol (mg)'), 'alc': ('1.3 Proximates', 'Alcohol (g)'),
    'na': ('1.4 Inorganics', 'Sodium (mg)'), 'k': ('1.4 Inorganics', 'Potassium (mg)'),
    'ca': ('1.4 Inorganics', 'Calcium (mg)'), 'mg': ('1.4 Inorganics', 'Magnesium (mg)'),
    'fe': ('1.4 Inorganics', 'Iron (mg)'), 'zn': ('1.4 Inorganics', 'Zinc (mg)'),
    'va': ('1.5 Vitamins', 'Retinol Equivalent (µg)'), 'vd': ('1.5 Vitamins', 'Vitamin D (µg)'),
    'b9': ('1.5 Vitamins', 'Folate (µg)'), 'b12': ('1.5 Vitamins', 'Vitamin B12 (µg)'),
    'vc': ('1.5 Vitamins', 'Vitamin C (mg)'),
}
_CODE = re.compile(r'^\d+-\d+$')


def _num(v):
    """'Tr' -> 0.0 (trace); 'N', '', None, other text -> None (missing)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == 'Tr':
        return 0.0
    try:
        return float(s.strip('[]() '))
    except ValueError:
        return None


def _read(wb, sheet):
    rows = wb[sheet].iter_rows(values_only=True)
    head = [str(h).strip() if h is not None else '' for h in next(rows)]
    out = {}
    for r in rows:
        code = str(r[0]).strip() if r[0] is not None else ''
        if _CODE.match(code) and code not in out:
            out[code] = r
    return head, out


def build(path: Path) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = {}
    for sheet in {s for s, _ in NUTRIENTS.values()}:
        head, rows = _read(wb, sheet)
        sheets[sheet] = (head, rows)
    fhead, frows = _read(wb, '1.2 Factors')
    sg_i = fhead.index('Specific gravity')
    idx = {}
    for key, (sheet, col) in NUTRIENTS.items():
        head = sheets[sheet][0]
        if col not in head:
            sys.exit(f'column not found: {sheet!r} / {col!r}')
        idx[key] = head.index(col)

    prox_head, prox = sheets['1.3 Proximates']
    out, dropped = [], Counter()
    for code, row in prox.items():
        name = str(row[1] or '').strip()
        group = str(row[3] or '').strip()
        if not name or not group:
            dropped['no name/group'] += 1
            continue
        if group[0] in DROP_TOP or group in DROP_SUB and not re.search(r'ghee, butter', name, re.I):
            dropped['meat/fish/animal-fat group'] += 1
            continue
        if re.search(r'weighed (with|as)', name, re.I):
            dropped['weighed with skin/shell'] += 1
            continue
        if food_filters.is_animal_en(name):
            dropped['animal name'] += 1
            continue
        nu = {}
        for key, (sheet, _) in NUTRIENTS.items():
            r = sheets[sheet][1].get(code)
            if r is not None:
                v = _num(r[idx[key]])
                if v is not None and v >= 0:
                    nu[key] = v
        if 'kcal' not in nu:
            dropped['no energy'] += 1
            continue
        if group[0] == 'Q':  # per 100 ml -> per 100 g
            try:
                sg = float(frows[code][sg_i])
            except (KeyError, TypeError, ValueError):
                sg = 1.0
            if sg > 0:
                nu = {k: v / sg for k, v in nu.items()}
        nu = {k: round(v, 2) for k, v in nu.items()}
        sub = SUB.get(group) or SUB.get(group[:2]) or SUB.get(group[:1]) or TOP[group[0]]
        out.append({'i': 'cofid_' + code, 'n': name, 'c': TOP[group[0]], 's': sub,
                    'g': group, 'nu': nu})
    out.sort(key=lambda e: e['i'])
    for why, n in dropped.items():
        print(f'dropped {n:5d}  {why}')
    return out


def main(argv):
    if len(argv) != 3:
        sys.exit('usage: parse_cofid.py <cofid_2021.xlsx> <output_json>')
    data = build(Path(argv[1]))
    Path(argv[2]).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                             encoding='utf-8')
    for c, n in sorted(Counter(d['c'] for d in data).items(), key=lambda x: -x[1]):
        print(f'{n:5d}  {c}')
    print(f'{len(data)} foods, {Path(argv[2]).stat().st_size / 1e6:.2f} MB')


if __name__ == '__main__':
    main(sys.argv)
