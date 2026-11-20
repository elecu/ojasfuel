"""
OjasFuel — Contribute: submit a missing product to Open Food Facts anonymously.
Steps: 1) barcode & name  2) ingredients (OCR optional)  3) nutrition (OCR optional)  4) photo & submit.
"""

import io
import re

import streamlit as st

from src.i18n import t, init_session
from src.theme import inject_theme
from src.api_client import submit_product

st.set_page_config(
    page_title='OjasFuel — Contribute',
    page_icon='🌿',
    layout='wide',
    initial_sidebar_state='collapsed',
)

init_session()
inject_theme()

# ── Optional deps ─────────────────────────────────────────────────────────────
_easyocr_ok = False
try:
    import easyocr as _easyocr
    _easyocr_ok = True
except ImportError:
    pass

try:
    import numpy as _np
    from PIL import Image as _Image
    _img_ok = True
except ImportError:
    _img_ok = False

# ── Country list (OFF tag → i18n key) ─────────────────────────────────────────
_COUNTRY_KEYS = {
    '': 'country_unspecified',
    'en:mexico': 'country_mx',
    'en:united-states': 'country_us',
    'en:canada': 'country_ca',
    'en:france': 'country_fr',
    'en:spain': 'country_es',
    'en:germany': 'country_de',
    'en:brazil': 'country_br',
    'en:argentina': 'country_ar',
    'en:colombia': 'country_co',
    'en:chile': 'country_cl',
    'en:united-kingdom': 'country_gb',
    'en:italy': 'country_it',
    'en:japan': 'country_jp',
    'en:china': 'country_cn',
    'en:india': 'country_in',
}

# ── Full nutrient catalog: OFF POST key → (display label, unit) ───────────────
_ALL_NUTRIENTS: dict[str, tuple[str, str]] = {
    'nutriment_energy-kcal_100g':    ('Energía / Energy (kcal)',           'kcal'),
    'nutriment_energy-kj_100g':      ('Energía / Energy (kJ)',             'kJ'),
    'nutriment_fat_100g':            ('Grasas / Fat (g)',                  'g'),
    'nutriment_saturated-fat_100g':  ('Grasas saturadas / Sat. Fat (g)',   'g'),
    'nutriment_carbohydrates_100g':  ('Carbohidratos / Carbohydrates (g)', 'g'),
    'nutriment_sugars_100g':         ('Azúcares / Sugars (g)',             'g'),
    'nutriment_fiber_100g':          ('Fibra / Fiber (g)',                 'g'),
    'nutriment_proteins_100g':       ('Proteínas / Protein (g)',           'g'),
    'nutriment_salt_100g':           ('Sal / Salt (g)',                    'g'),
    'nutriment_sodium_100g':         ('Sodio / Sodium (mg)',               'mg'),
    'nutriment_cholesterol_100g':    ('Colesterol / Cholesterol (mg)',     'mg'),
    'nutriment_potassium_100g':      ('Potasio / Potassium (mg)',          'mg'),
    'nutriment_calcium_100g':        ('Calcio / Calcium (mg)',             'mg'),
    'nutriment_iron_100g':           ('Hierro / Iron (mg)',                'mg'),
    'nutriment_magnesium_100g':      ('Magnesio / Magnesium (mg)',         'mg'),
    'nutriment_phosphorus_100g':     ('Fósforo / Phosphorus (mg)',         'mg'),
    'nutriment_zinc_100g':           ('Zinc (mg)',                         'mg'),
    'nutriment_manganese_100g':      ('Manganeso / Manganese (mg)',        'mg'),
    'nutriment_copper_100g':         ('Cobre / Copper (mg)',               'mg'),
    'nutriment_selenium_100g':       ('Selenio / Selenium (µg)',           'µg'),
    'nutriment_iodine_100g':         ('Yodo / Iodine (µg)',               'µg'),
    'nutriment_vitamin-a_100g':      ('Vitamina A / Vitamin A (µg)',       'µg'),
    'nutriment_vitamin-b1_100g':     ('Vitamina B1 / Thiamine (mg)',       'mg'),
    'nutriment_vitamin-b2_100g':     ('Vitamina B2 / Riboflavin (mg)',     'mg'),
    'nutriment_vitamin-b3_100g':     ('Vitamina B3 / Niacin (mg)',         'mg'),
    'nutriment_vitamin-b6_100g':     ('Vitamina B6 (mg)',                  'mg'),
    'nutriment_vitamin-b9_100g':     ('Vitamina B9 / Folate (µg)',         'µg'),
    'nutriment_vitamin-b12_100g':    ('Vitamina B12 (µg)',                 'µg'),
    'nutriment_vitamin-c_100g':      ('Vitamina C (mg)',                   'mg'),
    'nutriment_vitamin-d_100g':      ('Vitamina D (µg)',                   'µg'),
    'nutriment_vitamin-e_100g':      ('Vitamina E (mg)',                   'mg'),
    'nutriment_vitamin-k_100g':      ('Vitamina K (µg)',                   'µg'),
    'nutriment_alcohol_100g':        ('Alcohol (g)',                       'g'),
    'nutriment_caffeine_100g':       ('Cafeína / Caffeine (mg)',           'mg'),
}

# ── Keywords for OCR parsing (ES + EN), ordered specific→general ─────────────
_NUTRIENT_KEYWORDS: dict[str, list[str]] = {
    'nutriment_energy-kcal_100g':    ['kcal', 'caloría', 'caloria', 'calorie', 'energía kcal', 'energia kcal'],
    'nutriment_energy-kj_100g':      ['kj', 'kilojoul', 'energía kj', 'energia kj'],
    'nutriment_saturated-fat_100g':  ['saturada', 'saturado', 'saturated', 'sat fat', 'sat. fat'],
    'nutriment_fat_100g':            ['grasa total', 'grasa ', ' fat', 'lipid'],
    'nutriment_sugars_100g':         ['azúcar', 'azucar', 'sugar'],
    'nutriment_carbohydrates_100g':  ['carbohidrato', 'hidratos de carbono', 'carbohydrate', 'total carb'],
    'nutriment_fiber_100g':          ['fibra', 'fiber', 'fibre'],
    'nutriment_proteins_100g':       ['proteína', 'proteina', 'protein'],
    'nutriment_salt_100g':           ['sal ', ' salt'],
    'nutriment_sodium_100g':         ['sodio', 'sodium'],
    'nutriment_cholesterol_100g':    ['colesterol', 'cholesterol'],
    'nutriment_potassium_100g':      ['potasio', 'potassium'],
    'nutriment_calcium_100g':        ['calcio', 'calcium'],
    'nutriment_iron_100g':           ['hierro', ' iron'],
    'nutriment_magnesium_100g':      ['magnesio', 'magnesium'],
    'nutriment_phosphorus_100g':     ['fósforo', 'fosforo', 'phosphorus'],
    'nutriment_zinc_100g':           ['zinc'],
    'nutriment_vitamin-c_100g':      ['vitamina c', 'vitamin c', 'ácido ascórbico', 'ascorbic'],
    'nutriment_vitamin-a_100g':      ['vitamina a', 'vitamin a'],
    'nutriment_vitamin-d_100g':      ['vitamina d', 'vitamin d'],
    'nutriment_vitamin-e_100g':      ['vitamina e', 'vitamin e'],
    'nutriment_vitamin-b1_100g':     ['b1', 'tiamina', 'thiamine'],
    'nutriment_vitamin-b2_100g':     ['b2', 'riboflavina', 'riboflavin'],
    'nutriment_vitamin-b3_100g':     ['b3', 'niacina', 'niacin'],
    'nutriment_vitamin-b6_100g':     ['b6', 'piridoxina', 'pyridoxine'],
    'nutriment_vitamin-b9_100g':     ['b9', 'folato', 'ácido fólico', 'folate', 'folic'],
    'nutriment_vitamin-b12_100g':    ['b12', 'cobalamina', 'cobalamin'],
    'nutriment_caffeine_100g':       ['cafeína', 'cafeine', 'caffeine'],
    'nutriment_alcohol_100g':        ['alcohol'],
}

# ── Flat set of all nutrient keywords (for fast membership check) ─────────────
_ALL_NUTRIENT_KWS: list[str] = [kw for kws in _NUTRIENT_KEYWORDS.values() for kw in kws]


def _parse_nutrition_text(text: str) -> dict:
    """Returns {off_key: value_str} from raw OCR nutrition text."""
    result = {}
    for line in text.lower().split('\n'):
        numbers = re.findall(r'\d+(?:[.,]\d+)?', line)
        if not numbers:
            continue
        val = numbers[0].replace(',', '.')
        for key, keywords in _NUTRIENT_KEYWORDS.items():
            if key in result:
                continue
            if any(kw in line for kw in keywords):
                result[key] = val
                break
    return result


def _classify_lines(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Classify OCR lines into (ingredient_lines, nutrition_lines, other_lines)."""
    ingr, nutr, other = [], [], []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()
        has_number = bool(re.search(r'\d', line_lower))
        has_nutrient_kw = any(kw in line_lower for kw in _ALL_NUTRIENT_KWS)

        if has_nutrient_kw and has_number:
            nutr.append(line_stripped)
        elif not has_nutrient_kw and (len(line_stripped) > 15 or ',' in line_stripped):
            ingr.append(line_stripped)
        else:
            other.append(line_stripped)
    return ingr, nutr, other


def _parse_nutrition_text(text: str) -> dict:
    """Returns {off_key: value_str} from raw OCR nutrition text."""
    result = {}
    for line in text.lower().split('\n'):
        numbers = re.findall(r'\d+(?:[.,]\d+)?', line)
        if not numbers:
            continue
        val = numbers[0].replace(',', '.')
        for key, keywords in _NUTRIENT_KEYWORDS.items():
            if key in result:
                continue
            if any(kw in line for kw in keywords):
                result[key] = val
                break
    return result


@st.cache_resource(show_spinner=False)
def _get_ocr_reader():
    return _easyocr.Reader(['es', 'en'], gpu=False)


def _run_ocr_bytes(img_bytes: bytes) -> str:
    pil_img = _Image.open(io.BytesIO(img_bytes)).convert('RGB')
    return '\n'.join(_get_ocr_reader().readtext(_np.array(pil_img), detail=0))


def _image_capture(key: str) -> bytes | None:
    """Camera/upload chooser. Camera only turns on when the user asks. Returns bytes or None."""
    opt_cam, opt_up = t('contribute_cam_opt'), t('contribute_up_opt')
    method = st.radio(t('contribute_image_source'), [opt_cam, opt_up], horizontal=True,
                      key=f'method_{key}', label_visibility='collapsed')
    if method == opt_cam:
        if st.button(t('contribute_open_camera'), key=f'btn_cam_{key}', width='stretch'):
            st.session_state[f'cam_active_{key}'] = True
        if st.session_state.get(f'cam_active_{key}'):
            img = st.camera_input(t('contribute_camera_label'), key=f'cam_{key}',
                                  label_visibility='collapsed')
            return img.getvalue() if img else None
        return None
    img = st.file_uploader(t('contribute_upload_label'), type=['jpg', 'jpeg', 'png', 'webp'],
                           key=f'up_{key}', label_visibility='collapsed')
    return img.getvalue() if img else None


def _ocr_block(key: str, state_key: str) -> str | None:
    """Image capture + OCR button. Stores raw text in session_state[state_key]."""
    img = _image_capture(key)
    if img and _easyocr_ok and _img_ok:
        if st.button(t('contribute_ocr_run'), key=f'btn_ocr_{key}'):
            with st.spinner(t('contribute_ocr_running')):
                try:
                    st.session_state[state_key] = _run_ocr_bytes(img)
                except Exception as e:
                    st.error(str(e))
    elif img:
        st.info(t('contribute_ocr_missing'))
    return st.session_state.get(state_key)


# ── Callbacks (run before widgets are instantiated, so they may set widget keys) ─
def _apply_ingredients(src_key: str) -> None:
    st.session_state['c_ingredients'] = st.session_state.get(src_key, '')


def _translate_ingredients() -> None:
    st.session_state.pop('c_translated_view', None)
    try:
        from deep_translator import GoogleTranslator
        st.session_state['c_translated'] = GoogleTranslator(
            source='auto', target='en').translate(st.session_state.get('c_ingredients', ''))
        st.session_state.pop('c_translate_err', None)
    except Exception as e:
        st.session_state['c_translate_err'] = str(e)


def _parse_nutrition(src_key: str) -> None:
    parsed = _parse_nutrition_text(st.session_state.get(src_key, ''))
    st.session_state['c_parse_n'] = len(parsed)
    for k, v in parsed.items():
        try:
            st.session_state[f'nutr_{k}'] = float(v)
        except ValueError:
            continue
        if k not in st.session_state['active_nutrition_keys']:
            st.session_state['active_nutrition_keys'].append(k)


def _add_nutrient() -> None:
    k = st.session_state.get('nutrient_to_add')
    if k and k not in st.session_state['active_nutrition_keys']:
        st.session_state['active_nutrition_keys'].append(k)


_FORM_KEYS = ('c_barcode', 'c_name', 'c_brand', 'c_quantity', 'c_ingredients', 'c_country',
              'c_translated', 'c_translate_err', 'c_parse_n', 'ocr_ingredients_text',
              'ocr_nutrition_text', 'ocr_ingr_edit', 'ocr_nutr_edit', 'active_nutrition_keys',
              'contribute_prefill_barcode', 'contribute_prefill_name', '_c_prefill_sig',
              'cam_active_ingr', 'cam_active_nutr', 'cam_active_photo',
              'up_ingr', 'up_nutr', 'up_photo', 'cam_ingr', 'cam_nutr', 'cam_photo')

# Clear everything after a successful submit (must happen before widgets exist).
if st.session_state.pop('_c_clear', False):
    for k in list(st.session_state.keys()):
        if k in _FORM_KEYS or str(k).startswith('nutr_'):
            del st.session_state[k]

# ── Back button / header ──────────────────────────────────────────────────────
if st.button(t('back')):
    st.switch_page('app.py')

st.title(t('contribute_title'))
st.caption(t('contribute_subtitle'))
st.info(t('contribute_note'))

_last = st.session_state.get('_c_last_result')
if _last:
    st.success(t('contribute_success'))
    if _last.get('url'):
        st.markdown(f"[{t('contribute_view_product')}]({_last['url']})")
    if _last.get('photo_ok') is True:
        st.success(t('contribute_photo_ok'))
    elif _last.get('photo_ok') is False:
        st.warning(t('contribute_photo_fail'))
    st.balloons()
    st.session_state.pop('_c_last_result', None)

# ── Initial state (prefill from search context; kept until successful submit) ─
st.session_state.setdefault('active_nutrition_keys', [])
_pb = st.session_state.get('contribute_prefill_barcode', '')
_pn = st.session_state.get('contribute_prefill_name', '')
if (_pb or _pn) and st.session_state.get('_c_prefill_sig') != (_pb, _pn):
    st.session_state['c_barcode'] = _pb
    st.session_state['c_name'] = _pn
    st.session_state['_c_prefill_sig'] = (_pb, _pn)
if 'c_country' not in st.session_state:
    _cc = (st.session_state['settings'].get('countries') or {}).get('cc') \
        if isinstance(st.session_state['settings'].get('countries'), dict) else None
    st.session_state['c_country'] = 'en:mexico' if _cc == 'mx' else ''

# ── Step 1: barcode & name ────────────────────────────────────────────────────
st.header(t('contribute_step1'))
st.text_input(t('contribute_barcode'), key='c_barcode',
              help=t('contribute_barcode_help'), placeholder=t('contribute_barcode_ph'))
st.text_input(t('contribute_name'), key='c_name', placeholder=t('contribute_name_ph'))
col_b, col_q = st.columns(2)
with col_b:
    st.text_input(t('contribute_brand'), key='c_brand', placeholder=t('contribute_brand_ph'))
with col_q:
    st.text_input(t('contribute_quantity'), key='c_quantity', placeholder=t('contribute_quantity_ph'))
st.selectbox(
    t('contribute_country'),
    options=list(_COUNTRY_KEYS.keys()),
    format_func=lambda tag: t(_COUNTRY_KEYS[tag]),
    help=t('contribute_country_help'),
    key='c_country',
)

st.divider()

# ── Step 2: ingredients ───────────────────────────────────────────────────────
st.header(t('contribute_step2'))
with st.expander(t('contribute_ocr_optional')):
    st.caption(t('contribute_ocr_ingredients_caption'))
    _raw = _ocr_block('ingr', 'ocr_ingredients_text')
    if _raw:
        st.text_area(t('contribute_ocr_edit_label'), value=_raw, height=120, key='ocr_ingr_edit')
        st.button(t('contribute_ocr_apply_ingr'), key='btn_apply_ingr',
                  on_click=_apply_ingredients, args=('ocr_ingr_edit',))

st.text_area(t('contribute_ingredients'), key='c_ingredients',
             placeholder=t('contribute_ingredients_ph'), height=120)

if st.session_state.get('c_ingredients', '').strip():
    st.button(t('translate_to_english'), key='btn_translate', on_click=_translate_ingredients,
              help=t('contribute_translate_hint'))
    if st.session_state.get('c_translate_err'):
        st.error(st.session_state['c_translate_err'])
    if st.session_state.get('c_translated'):
        st.info(t('translated_label'))
        st.text_area(t('translated_ingredients_label'), value=st.session_state['c_translated'],
                     height=100, key='c_translated_view')
        st.button(t('contribute_ocr_use_translated'), key='btn_use_translated',
                  on_click=_apply_ingredients, args=('c_translated_view',))

st.divider()

# ── Step 3: nutrition ─────────────────────────────────────────────────────────
st.header(t('contribute_step3'))
with st.expander(t('contribute_ocr_optional')):
    st.caption(t('contribute_ocr_nutrition_caption'))
    _raw = _ocr_block('nutr', 'ocr_nutrition_text')
    if _raw:
        st.text_area(t('contribute_ocr_edit_label'), value=_raw, height=140, key='ocr_nutr_edit')
        st.button(t('contribute_ocr_parse'), key='btn_parse_nutr',
                  on_click=_parse_nutrition, args=('ocr_nutr_edit',))
    _n = st.session_state.get('c_parse_n')
    if _n is not None:
        if _n:
            st.success(t('contribute_ocr_parsed_ok', n=_n))
        else:
            st.warning(t('contribute_ocr_parsed_none'))

_active_keys: list = st.session_state['active_nutrition_keys']
_available_to_add = [k for k in _ALL_NUTRIENTS if k not in _active_keys]
if _available_to_add:
    col_add1, col_add2 = st.columns([3, 1], vertical_alignment='bottom')
    with col_add1:
        st.selectbox(f"➕ {t('contribute_add_nutrient')}", options=_available_to_add,
                     format_func=lambda k: _ALL_NUTRIENTS[k][0], key='nutrient_to_add')
    with col_add2:
        st.button(t('contribute_add_btn'), key='btn_add_nutrient', on_click=_add_nutrient)

nutrition_values = {}
if _active_keys:
    st.caption(t('contribute_nutrition_help'))
    cols = st.columns(2)
    for idx, key in enumerate(_active_keys):
        label, unit = _ALL_NUTRIENTS.get(key, (key, ''))
        with cols[idx % 2]:
            val = st.number_input(label, min_value=0.0, value=None, step=0.1,
                                  format='%.2f', key=f'nutr_{key}', placeholder=unit)
            if val is not None:   # keep legitimate zeros
                nutrition_values[key] = val
else:
    st.caption(f"💡 {t('contribute_nutrient_hint')}")

st.divider()

# ── Step 4: photo & submit ────────────────────────────────────────────────────
st.header(t('contribute_step4'))
st.caption(t('contribute_front_photo'))
_product_photo_bytes = _image_capture('photo')
if _product_photo_bytes:
    st.image(_product_photo_bytes, width=200)

if st.button(t('contribute_submit'), type='primary', key='btn_submit'):
    barcode = st.session_state.get('c_barcode', '').strip()
    name = st.session_state.get('c_name', '').strip()
    if not barcode or not name:
        st.error(t('contribute_required'))
    elif not barcode.isdigit() or not (8 <= len(barcode) <= 14):
        st.error(t('contribute_barcode_invalid'))
    else:
        with st.spinner(t('contribute_submitting')):
            result = submit_product(
                barcode=barcode,
                name=name,
                brand=st.session_state.get('c_brand', ''),
                quantity=st.session_state.get('c_quantity', ''),
                ingredients=st.session_state.get('c_ingredients', ''),
                countries=st.session_state.get('c_country', ''),
                nutrition=nutrition_values or None,
                photo_bytes=_product_photo_bytes,
            )
        if result.get('ok'):
            st.session_state['_c_last_result'] = result
            st.session_state['_c_clear'] = True
            st.rerun()
        else:
            st.error(t('contribute_failed', err=result.get('error') or '?'))
