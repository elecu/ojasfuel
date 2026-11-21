"""Build src/ciqual_db.json from the ANSES-CIQUAL 2020 tables (French + English .xls).

Usage:  python3 -I scripts/parse_ciqual.py <ciqual_2020_fr.xls> <ciqual_2020_eng.xls> <output_json>

Anses (2020). Ciqual French food composition table (ciqual.anses.fr, Licence Ouverte / CC-BY 4.0).
Needs xlrd (legacy .xls). The two files are joined on alim_code.

Choices:
 * "traces" -> 0 and "< x" (below the detection limit) -> 0; "-" and blanks -> missing.
 * Comma decimals ("4,63") are converted.
 * Energy = Regulation EU 1169/2011 kcal; where that is missing, the "N x Jones factor,
   with fibres" kcal; where both are missing (about 800 foods) it is computed from protein,
   fat, carbohydrate, fibre and alcohol with the EU 1169/2011 factors (4/9/4/2/7 kcal per g)
   and the entry gets "ke": 1. Foods without the macronutrients are dropped.
 * Glucides (carbohydrates) in CIQUAL are available carbohydrates (fibre excluded):
   stored as is. Fibre is its own field.
 * Protein = N x Jones factor (falls back to N x 6.25). Vitamin A = retinol +
   beta-carotene / 12 (ug RAE). Sodium falls back to salt x 400.
 * Dropped: meat, fish, seafood, cooked-meat groups (04, except eggs 0410 and meat
   substitutes 0411), fish oils, baby foods (11), and any food whose French or English
   name names an animal (or gelatin). Eggs and dairy are kept.
 * Both French ('nf') and English ('n') names are kept.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import food_filters  # noqa: E402

# short key -> French column header prefix
NUTRIENTS = {
    'kcal': 'Energie, Règlement UE N° 1169/2011 (kcal',
    'kcalj': 'Energie, N x facteur Jones, avec fibres  (kcal',
    'p': 'Protéines, N x facteur de Jones', 'p625': 'Protéines, N x 6.25',
    'c': 'Glucides', 'f': 'Lipides', 'sug': 'Sucres (g', 'fib': 'Fibres alimentaires',
    'sat': 'AG saturés', 'alc': 'Alcool', 'chol': 'Cholestérol', 'salt': 'Sel chlorure de sodium',
    'ca': 'Calcium', 'fe': 'Fer', 'mg': 'Magnésium', 'k': 'Potassium', 'na': 'Sodium',
    'zn': 'Zinc', 'ret': 'Rétinol', 'bc': 'Beta-Carotène', 'vd': 'Vitamine D',
    'vc': 'Vitamine C', 'b9': 'Vitamine B9', 'b12': 'Vitamine B12',
}
DROP_SUBGROUPS = {'0401', '0402', '0403', '0404', '0405', '0406', '0407', '0408', '0409', '0904'}
DROP_GROUPS = {'00', '11'}


def _num(v):
    """'traces' and '< x' -> 0.0; '-' / '' / other text -> None (missing)."""
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in ('-', ''):
        return None
    if s == 'traces' or s.startswith('<'):
        return 0.0
    try:
        return float(s.replace(',', '.'))
    except ValueError:
        return None


def _sheet(path):
    import xlrd
    ws = xlrd.open_workbook(path).sheet_by_index(0)
    head = [str(h) for h in ws.row_values(0)]
    return head, [ws.row_values(r) for r in range(1, ws.nrows)]


def _col(head, prefix):
    for i, h in enumerate(head):
        if h.startswith(prefix):
            return i
    sys.exit(f'CIQUAL column not found: {prefix!r}')


def _txt(v):
    s = str(v or '').strip()
    return '' if s in ('-', '') else s


def build(fr_path: Path, en_path: Path) -> list[dict]:
    fhead, frows = _sheet(fr_path)
    ehead, erows = _sheet(en_path)
    idx = {k: _col(fhead, p) for k, p in NUTRIENTS.items()}
    en_by_code = {int(r[6]): r for r in erows}
    out, dropped = [], Counter()
    for r in frows:
        code = int(r[6])
        er = en_by_code.get(code)
        grp, sub = _txt(r[0]), _txt(r[1])
        name_fr = _txt(r[7])
        name_en = _txt(er[7]) if er else ''
        if not name_fr and not name_en:
            continue
        if grp in DROP_GROUPS or not _txt(r[3]):
            dropped['no group / baby food'] += 1
            continue
        if sub in DROP_SUBGROUPS:
            dropped['meat/fish/seafood group'] += 1
            continue
        if sub != '0411':  # meat substitutes may legitimately say "steak"/"nuggets"
            if (name_fr and food_filters.is_animal_fr(name_fr)) or \
                    (name_en and food_filters.is_animal_en(name_en)):
                dropped['animal name'] += 1
                continue
        nu = {}
        for key, i in idx.items():
            v = _num(r[i])
            if v is not None and v >= 0:
                nu[key] = v
        kcal = nu.pop('kcal', None)
        kcalj = nu.pop('kcalj', None)
        if kcal is None:
            kcal = kcalj
        p625 = nu.pop('p625', None)
        if 'p' not in nu and p625 is not None:
            nu['p'] = p625
        computed = False
        if kcal is None and all(k in nu for k in ('p', 'f', 'c')):
            # EU 1169/2011 factors: 4 kcal/g protein and carbohydrate, 9 fat, 2 fibre, 7 alcohol
            kcal = (4 * nu['p'] + 4 * nu['c'] + 9 * nu['f'] + 2 * nu.get('fib', 0)
                    + 7 * nu.get('alc', 0))
            computed = True
        if kcal is None:
            dropped['no energy and no macros'] += 1
            continue
        nu['kcal'] = kcal
        salt = nu.pop('salt', None)
        if 'na' not in nu and salt is not None:
            nu['na'] = salt * 400
        ret, bc = nu.pop('ret', None), nu.pop('bc', None)
        if ret is not None or bc is not None:
            nu['va'] = (ret or 0) + (bc or 0) / 12
        nu = {k: round(v, 2) for k, v in nu.items()}
        entry = {'i': f'ciqual_{code}', 'n': name_en or name_fr, 'nf': name_fr or name_en,
                 'c': _txt(er[3]) if er else _txt(r[3]), 's': _txt(er[4]) if er else _txt(r[4])}
        ss = _txt(er[5]) if er else _txt(r[5])
        if ss:
            entry['ss'] = ss
        if computed:
            entry['ke'] = 1  # energy computed from macronutrients, not published
        entry['nu'] = nu
        out.append(entry)
    out.sort(key=lambda e: int(e['i'].split('_')[1]))
    for why, n in dropped.items():
        print(f'dropped {n:5d}  {why}')
    return out


def main(argv):
    if len(argv) != 4:
        sys.exit('usage: parse_ciqual.py <ciqual_fr.xls> <ciqual_eng.xls> <output_json>')
    data = build(Path(argv[1]), Path(argv[2]))
    Path(argv[3]).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                             encoding='utf-8')
    for c, n in sorted(Counter(d['c'] for d in data).items(), key=lambda x: -x[1]):
        print(f'{n:5d}  {c}')
    print(f'{len(data)} foods, {Path(argv[3]).stat().st_size / 1e6:.2f} MB')


if __name__ == '__main__':
    main(sys.argv)
