#!/usr/bin/env python3
"""OCR benchmark for ingredient labels. Usage: python scripts/ocr_benchmark.py <dir>

<dir> holds images plus same-name .txt ground-truth ingredient lists.
Not wired into the app.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageOps  # noqa: E402

from src import blocklists as B  # noqa: E402
from src.classifier import _find_matches  # noqa: E402
from src.verdict import verdict  # noqa: E402

IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
CRIT = [B.MEAT_FISH, B.DAIRY, B.EGGS, B.GELATIN, B.HONEY, B.ALLERGIES_NUTS, B.ALLERGIES_PEANUTS,
        B.ALLERGIES_SOY, B.ALLERGIES_MUSTARD, B.ALLERGIES_SESAME, B.ALLERGIES_GLUTEN]
ALL_ALLERGIES = {'allergies_nuts': True, 'allergies_peanuts': True, 'allergies_soy': True,
                 'allergies_mustard': True, 'allergies_sesame': True, 'allergies_gluten': True}
SETTINGS = [{'mode': 'vegetarian'}, {'mode': 'vegan', **ALL_ALLERGIES}]


def norm_tokens(text: str) -> list[str]:
    t = unicodedata.normalize('NFKD', text.lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.findall(r'[a-z0-9]+', t)


def preprocess(path: str, out_dir: str) -> str:
    im = Image.open(path).convert('L')
    im = ImageOps.autocontrast(im)
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    out = os.path.join(out_dir, 'pp_' + os.path.basename(path) + '.png')
    im.save(out)
    return out


def tesseract_cli(path: str) -> str:
    langs = subprocess.run(['tesseract', '--list-langs'], capture_output=True, text=True).stdout.split()
    lang = '+'.join(l for l in ('spa', 'eng') if l in langs) or 'eng'
    r = subprocess.run(['tesseract', path, 'stdout', '-l', lang], capture_output=True, text=True, timeout=120)
    return r.stdout


_easy = None


def easyocr_run(path: str) -> str:
    global _easy
    if _easy is None:
        import easyocr
        _easy = easyocr.Reader(['es', 'en'], gpu=False, verbose=False)
    return ' '.join(_easy.readtext(path, detail=0))


def tesseractjs_available() -> bool:
    if not shutil.which('node'):
        return False
    r = subprocess.run(['node', '-e', "require('tesseract.js')"], capture_output=True)
    return r.returncode == 0


def tesseractjs_run(path: str) -> str:
    js = ("const T=require('tesseract.js');T.recognize(process.argv[1],'spa+eng')"
          ".then(r=>{process.stdout.write(r.data.text)}).catch(e=>{console.error(e);process.exit(1)})")
    r = subprocess.run(['node', '-e', js, path], capture_output=True, text=True, timeout=180)
    return r.stdout


def engines() -> dict:
    eng = {}
    if shutil.which('tesseract'):
        eng['tesseract'] = tesseract_cli
    else:
        print('note: tesseract CLI not found, skipped')
    try:
        import easyocr  # noqa: F401
        eng['easyocr'] = easyocr_run
    except Exception:
        print('note: easyocr not importable, skipped')
    if tesseractjs_available():
        eng['tesseract.js'] = tesseractjs_run
    else:
        print("note: tesseract.js not installed (npm install tesseract.js locally and set NODE_PATH), skipped")
    return eng


def crit_terms(text: str) -> set[str]:
    low = text.lower()
    return {m.lower() for pats in CRIT for m in _find_matches(low, pats)}


def verdicts(text: str) -> list[str]:
    return [verdict({'name': '', 'ingredients': text}, s)['status'] for s in SETTINGS]


def main(d: str) -> int:
    samples = []
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(IMG_EXT):
            gt = os.path.splitext(os.path.join(d, f))[0] + '.txt'
            if os.path.exists(gt):
                samples.append((os.path.join(d, f), open(gt, encoding='utf-8').read()))
    if not samples:
        print('no image + .txt pairs found in', d)
        return 1
    eng = engines()
    tmp = tempfile.mkdtemp()
    rows = []
    for ename, fn in eng.items():
        for variant in ('raw', 'pre'):
            recalls, crit_miss, agree, agree_n, times = [], 0, 0, 0, []
            for img, gt in samples:
                src = preprocess(img, tmp) if variant == 'pre' else img
                t0 = time.time()
                try:
                    text = fn(src)
                except Exception as e:
                    print(f'  {ename}/{variant} failed on {os.path.basename(img)}: {e}')
                    text = ''
                times.append(time.time() - t0)
                gt_tok, ocr_tok = set(norm_tokens(gt)), set(norm_tokens(text))
                recalls.append(len(gt_tok & ocr_tok) / len(gt_tok) if gt_tok else 1.0)
                gt_crit, ocr_crit = crit_terms(gt), crit_terms(text)
                crit_miss += len(gt_crit - ocr_crit)
                for a, b in zip(verdicts(gt), verdicts(text)):
                    agree_n += 1
                    agree += a == b
            rows.append((f'{ename}/{variant}', sum(recalls) / len(recalls), crit_miss,
                         agree / agree_n, sum(times) / len(times)))
    print(f"\n{'engine':<20}{'recall':>8}{'crit_miss':>11}{'verdict%':>10}{'avg_s':>8}  decision")
    for name, rec, cm, ag, avg in rows:
        go = cm == 0 and ag >= 0.9 and avg <= 5
        print(f'{name:<20}{rec:>8.2f}{cm:>11}{ag * 100:>9.0f}%{avg:>8.2f}  {"GO" if go else "NO-GO"}')
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
