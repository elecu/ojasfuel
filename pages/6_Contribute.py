"""
OjasFuel — Contribute: submit a missing product to Open Food Facts anonymously.
"""

import streamlit as st
import sys
import io
import re
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

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

# ── Country list (OFF tag → display label) ────────────────────────────────────
_COUNTRIES = {
    '': '— Sin especificar / Not specified —',
    'en:mexico': '🇲🇽 México',
    'en:united-states': '🇺🇸 United States',
    'en:canada': '🇨🇦 Canada',
    'en:france': '🇫🇷 France',
    'en:spain': '🇪🇸 Spain',
    'en:germany': '🇩🇪 Germany',
    'en:brazil': '🇧🇷 Brazil',
    'en:argentina': '🇦🇷 Argentina',
    'en:colombia': '🇨🇴 Colombia',
    'en:chile': '🇨🇱 Chile',
    'en:united-kingdom': '🇬🇧 United Kingdom',
    'en:italy': '🇮🇹 Italy',
    'en:japan': '🇯🇵 Japan',
    'en:china': '🇨🇳 China',
    'en:india': '🇮🇳 India',
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


def _run_ocr_bytes(img_bytes: bytes) -> str:
    pil_img = _Image.open(io.BytesIO(img_bytes)).convert('RGB')
    reader = _easyocr.Reader(['es', 'en'], gpu=False)
    return '\n'.join(reader.readtext(_np.array(pil_img), detail=0))


def _image_capture(key: str) -> bytes | None:
    """Radio toggle: camera activates ONLY when user explicitly selects it.
    Returns image bytes or None."""
    _is_es = st.session_state.get('lang', 'es') == 'es'
    opt_cam = '📷 Cámara' if _is_es else '📷 Camera'
    opt_up  = '📁 Subir imagen' if _is_es else '📁 Upload image'
    method = st.radio('', [opt_cam, opt_up], horizontal=True, key=f'method_{key}',
                      label_visibility='collapsed')
    if method == opt_cam:
        img = st.camera_input('', key=f'cam_{key}', label_visibility='collapsed')
        return img.getvalue() if img else None
    else:
        img = st.file_uploader('', type=['jpg', 'jpeg', 'png', 'webp'],
                               key=f'up_{key}', label_visibility='collapsed')
        return img.read() if img else None


# ── Back button ───────────────────────────────────────────────────────────────
if st.button(t('back')):
    st.switch_page('app.py')

st.title(t('contribute_title'))
st.caption(t('contribute_subtitle'))
st.info(t('contribute_note'))

st.divider()

# ── Pre-fill from search context ──────────────────────────────────────────────
prefill_barcode = st.session_state.pop('contribute_prefill_barcode', '')
prefill_name = st.session_state.pop('contribute_prefill_name', '')

_cs = st.session_state.get('country_selection', {})
_cc = _cs.get('cc') if isinstance(_cs, dict) else None
_default_country = 'en:mexico' if _cc == 'mx' else ''

if 'active_nutrition_keys' not in st.session_state:
    st.session_state['active_nutrition_keys'] = []

# ── Foto del producto ─────────────────────────────────────────────────────────
st.subheader(t('contribute_photo_title'))
_product_photo_bytes = _image_capture('product')
if _product_photo_bytes:
    st.image(_product_photo_bytes, width=200)

st.divider()

# ── OCR section — tabs ────────────────────────────────────────────────────────
_ocr_miss_msg = 'EasyOCR no disponible. Instala con: pip install easyocr pillow numpy'

tab_single, tab_ingr, tab_nutr = st.tabs([
    t('contribute_ocr_single_title'),
    t('contribute_ocr_ingredients_title'),
    t('contribute_ocr_nutrition_title'),
])

# ───────────────────────── TAB 1: Foto única ─────────────────────────────────
with tab_single:
    st.caption(t('contribute_ocr_single_caption'))
    _single_img = _image_capture('single')

    if _single_img and _easyocr_ok and _img_ok:
        if st.button(t('contribute_ocr_run'), key='btn_ocr_single'):
            with st.spinner(t('contribute_ocr_running')):
                try:
                    raw = _run_ocr_bytes(_single_img)
                    st.session_state['single_ocr_raw'] = raw
                    # Clear previous split results
                    st.session_state.pop('single_ocr_ingr', None)
                    st.session_state.pop('single_ocr_nutr', None)
                    st.session_state.pop('single_ocr_other', None)
                except Exception as e:
                    st.error(str(e))
    elif _single_img and not (_easyocr_ok and _img_ok):
        st.info(_ocr_miss_msg)

    if st.session_state.get('single_ocr_raw'):
        raw_text = st.text_area(
            t('contribute_ocr_edit_label'),
            value=st.session_state['single_ocr_raw'],
            height=140,
            key='single_raw_edit',
        )
        if st.button(t('contribute_ocr_autosplit'), key='btn_autosplit'):
            ingr_lines, nutr_lines, other_lines = _classify_lines(raw_text.split('\n'))
            st.session_state['single_ocr_ingr'] = '\n'.join(ingr_lines)
            st.session_state['single_ocr_nutr'] = '\n'.join(nutr_lines)
            st.session_state['single_ocr_other'] = '\n'.join(other_lines)
            st.rerun()

    if st.session_state.get('single_ocr_ingr') is not None or st.session_state.get('single_ocr_nutr') is not None:
        st.divider()
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown(f"**{t('contribute_ocr_detected_ingr')}**")
            edited_single_ingr = st.text_area(
                t('contribute_ocr_detected_ingr'),
                value=st.session_state.get('single_ocr_ingr', ''),
                height=160,
                label_visibility='collapsed',
                key='single_ingr_edit',
            )
            if st.button(t('contribute_ocr_apply_ingr'), key='btn_apply_single_ingr'):
                st.session_state['prefill_ingredients'] = edited_single_ingr
                st.rerun()

        with col_right:
            st.markdown(f"**{t('contribute_ocr_detected_nutr')}**")
            edited_single_nutr = st.text_area(
                t('contribute_ocr_detected_nutr'),
                value=st.session_state.get('single_ocr_nutr', ''),
                height=160,
                label_visibility='collapsed',
                key='single_nutr_edit',
            )
            if st.button(t('contribute_ocr_parse'), key='btn_parse_single_nutr'):
                parsed = _parse_nutrition_text(edited_single_nutr)
                if parsed:
                    st.session_state['ocr_nutrition_values'] = parsed
                    existing = set(st.session_state['active_nutrition_keys'])
                    for k in parsed:
                        if k not in existing:
                            st.session_state['active_nutrition_keys'].append(k)
                    st.success(t('contribute_ocr_parsed_ok', n=len(parsed)))
                else:
                    st.warning(t('contribute_ocr_parsed_none'))
                st.rerun()

        _other = st.session_state.get('single_ocr_other', '')
        if _other.strip():
            with st.expander(t('contribute_ocr_unclassified')):
                st.text(_other)

# ───────────────────────── TAB 2: Solo ingredientes ──────────────────────────
with tab_ingr:
    st.caption(t('contribute_ocr_ingredients_caption'))
    _ingr_img = _image_capture('ingr')

    if _ingr_img and _easyocr_ok and _img_ok:
        if st.button(t('contribute_ocr_run'), key='btn_ocr_ingr'):
            with st.spinner(t('contribute_ocr_running')):
                try:
                    raw = _run_ocr_bytes(_ingr_img)
                    st.session_state['ocr_ingredients_text'] = raw
                except Exception as e:
                    st.error(str(e))
    elif _ingr_img and not (_easyocr_ok and _img_ok):
        st.info(_ocr_miss_msg)

    if st.session_state.get('ocr_ingredients_text'):
        edited_ingr = st.text_area(
            t('contribute_ocr_edit_label'),
            value=st.session_state['ocr_ingredients_text'],
            height=120,
            key='ocr_ingr_edit',
        )
        if st.button(t('contribute_ocr_apply_ingr'), key='btn_apply_ingr'):
            st.session_state['prefill_ingredients'] = edited_ingr
            st.rerun()

# ───────────────────────── TAB 3: Solo nutrición ─────────────────────────────
with tab_nutr:
    st.caption(t('contribute_ocr_nutrition_caption'))
    _nutr_img = _image_capture('nutr')

    if _nutr_img and _easyocr_ok and _img_ok:
        if st.button(t('contribute_ocr_run'), key='btn_ocr_nutr'):
            with st.spinner(t('contribute_ocr_running')):
                try:
                    raw = _run_ocr_bytes(_nutr_img)
                    st.session_state['ocr_nutrition_text'] = raw
                except Exception as e:
                    st.error(str(e))
    elif _nutr_img and not (_easyocr_ok and _img_ok):
        st.info(_ocr_miss_msg)

    if st.session_state.get('ocr_nutrition_text'):
        edited_nutr = st.text_area(
            t('contribute_ocr_edit_label'),
            value=st.session_state['ocr_nutrition_text'],
            height=140,
            key='ocr_nutr_edit',
        )
        if st.button(t('contribute_ocr_parse'), key='btn_parse_nutr'):
            parsed = _parse_nutrition_text(edited_nutr)
            if parsed:
                st.session_state['ocr_nutrition_values'] = parsed
                existing = set(st.session_state['active_nutrition_keys'])
                for k in parsed:
                    if k not in existing:
                        st.session_state['active_nutrition_keys'].append(k)
                st.success(t('contribute_ocr_parsed_ok', n=len(parsed)))
            else:
                st.warning(t('contribute_ocr_parsed_none'))
            st.rerun()

st.divider()

# ── "Add nutrient" button (outside form) ──────────────────────────────────────
_ocr_nutrition = st.session_state.get('ocr_nutrition_values', {})
_active_keys: list = st.session_state['active_nutrition_keys']
_available_to_add = [k for k in _ALL_NUTRIENTS if k not in _active_keys]

if _available_to_add:
    col_add1, col_add2 = st.columns([3, 1])
    with col_add1:
        _add_label = 'Agregar nutriente' if st.session_state.get('lang', 'es') == 'es' else 'Add nutrient'
        _to_add = st.selectbox(
            f'➕ {_add_label}',
            options=_available_to_add,
            format_func=lambda k: _ALL_NUTRIENTS[k][0],
            key='nutrient_to_add',
        )
    with col_add2:
        st.write('')
        st.write('')
        if st.button('Agregar / Add', key='btn_add_nutrient'):
            if _to_add and _to_add not in _active_keys:
                st.session_state['active_nutrition_keys'].append(_to_add)
            st.rerun()

# ── Main form ─────────────────────────────────────────────────────────────────
_prefill_ingr = st.session_state.get('prefill_ingredients', '')

with st.form('contribute_form'):
    barcode = st.text_input(
        t('contribute_barcode'),
        value=prefill_barcode,
        help=t('contribute_barcode_help'),
        placeholder='e.g. 7501234567890',
    )
    name = st.text_input(
        t('contribute_name'),
        value=prefill_name,
        placeholder='e.g. Oat Milk Chocolate',
    )
    brand = st.text_input(t('contribute_brand'), placeholder='e.g. Alpro')
    quantity = st.text_input(t('contribute_quantity'), placeholder='e.g. 500ml')

    ingredients = st.text_area(
        t('contribute_ingredients'),
        value=_prefill_ingr,
        placeholder='e.g. Oat base (water, oats 10%), cocoa 2%, salt...',
        height=120,
    )

    _country_options = list(_COUNTRIES.keys())
    _country_labels = list(_COUNTRIES.values())
    _default_idx = _country_options.index(_default_country) if _default_country in _country_options else 0
    country_idx = st.selectbox(
        t('contribute_country'),
        options=range(len(_country_options)),
        format_func=lambda i: _country_labels[i],
        index=_default_idx,
        help=t('contribute_country_help'),
    )
    country_tag = _country_options[country_idx]

    nutrition_values = {}
    if _active_keys:
        with st.expander(t('contribute_nutrition_expander'), expanded=True):
            st.caption(t('contribute_nutrition_help'))
            cols = st.columns(2)
            for idx, key in enumerate(_active_keys):
                label, unit = _ALL_NUTRIENTS.get(key, (key, ''))
                prefill_val = float(_ocr_nutrition[key]) if key in _ocr_nutrition else None
                with cols[idx % 2]:
                    val = st.number_input(
                        label,
                        min_value=0.0,
                        value=prefill_val,
                        step=0.1,
                        format='%.2f',
                        key=f'nutr_{key}',
                        placeholder=unit,
                    )
                    if val is not None and val > 0:
                        nutrition_values[key] = val
    else:
        _hint = ('Usa los botones de OCR arriba o el selector "Agregar nutriente" para añadir campos.'
                 if st.session_state.get('lang', 'es') == 'es'
                 else 'Use the OCR buttons above or the "Add nutrient" selector to add fields.')
        st.caption(f'💡 {_hint}')

    st.divider()
    submitted = st.form_submit_button(t('contribute_submit'), type='primary')

if submitted:
    if not barcode.strip() or not name.strip():
        st.error(t('contribute_required'))
    elif not barcode.strip().isdigit() or not (8 <= len(barcode.strip()) <= 14):
        st.error('❌ Barcode must be 8-14 digits (EAN/UPC format)')
    else:
        with st.spinner(t('contribute_submitting')):
            result = submit_product(
                barcode=barcode,
                name=name,
                brand=brand,
                quantity=quantity,
                ingredients=ingredients,
                countries=country_tag,
                nutrition=nutrition_values if nutrition_values else None,
                photo_bytes=_product_photo_bytes,
            )
        if result['ok']:
            st.success(t('contribute_success'))
            st.balloons()
            for k in ('ocr_ingredients_text', 'ocr_nutrition_text', 'ocr_nutrition_values',
                      'prefill_ingredients', 'active_nutrition_keys',
                      'single_ocr_raw', 'single_ocr_ingr', 'single_ocr_nutr', 'single_ocr_other'):
                st.session_state.pop(k, None)
        else:
            st.error(t('contribute_failed', err=result['error']))
