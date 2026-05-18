"""
OjasFuel — Photo Upload page
Barcode detection (pyzbar) + OCR (easyocr) + upload to Open Food Facts
"""

import streamlit as st
import sys
import io
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session
from src.theme import inject_theme
from src.api_client import search_by_barcode

st.set_page_config(page_title='OjasFuel — Photo Upload', page_icon='📷', layout='wide')
init_session()
inject_theme()

# ── Optional dependency checks ────────────────────────────────────────────────
_pyzbar_ok = False
_easyocr_ok = False
_cv2_ok = False

try:
    from PIL import Image
    import numpy as np
    _np = np
    _Image = Image
except ImportError:
    st.error('Pillow / numpy not installed. Run: pip install Pillow numpy')
    st.stop()

try:
    from pyzbar import pyzbar as _pyzbar
    _pyzbar_ok = True
except ImportError:
    pass
except Exception:
    pass

try:
    import cv2 as _cv2
    _cv2_ok = True
except ImportError:
    pass

try:
    import easyocr as _easyocr
    _easyocr_ok = True
except ImportError:
    pass


if st.button(t('back')):
    st.switch_page('app.py')

st.title(f"📷 {t('photo_upload')}")

# Capability badges
cap_col1, cap_col2, cap_col3 = st.columns(3)
cap_col1.markdown('**Barcode:** ' + ('✅ pyzbar' if _pyzbar_ok else '❌ pyzbar missing'))
cap_col2.markdown('**OCR:** ' + ('✅ easyocr' if _easyocr_ok else '❌ easyocr missing'))
cap_col3.markdown('**OpenCV:** ' + ('✅ cv2' if _cv2_ok else '⚠️ cv2 missing'))

if not _pyzbar_ok:
    st.info(t('pyzbar_missing'))
if not _easyocr_ok:
    st.info(t('easyocr_missing'))

st.divider()

# ── Image source ──────────────────────────────────────────────────────────────
source = st.radio(t('photo_source'), [t('upload_file'), t('take_photo')], horizontal=True)

img_data = None
if source == t('take_photo'):
    cam = st.camera_input(t('take_photo'))
    if cam:
        img_data = cam.read()
else:
    uploaded = st.file_uploader(t('upload_file'), type=['jpg', 'jpeg', 'png', 'webp'])
    if uploaded:
        img_data = uploaded.read()

if not img_data:
    st.stop()

pil_img = _Image.open(io.BytesIO(img_data)).convert('RGB')
st.image(pil_img, caption='Uploaded image', use_column_width=False, width=400)
img_array = _np.array(pil_img)

st.divider()

# ── Barcode detection ─────────────────────────────────────────────────────────
st.subheader(t('detected_barcode'))

detected_barcode = None

if _pyzbar_ok:
    try:
        def _try_decode(img_pil):
            """Try pyzbar on multiple preprocessed versions of the image."""
            import numpy as np
            candidates = []

            # Original + rotations
            for angle in [0, 90, 180, 270]:
                candidates.append(img_pil.rotate(angle, expand=True))

            # If cv2 available: add grayscale + threshold + sharpened variants
            if _cv2_ok:
                arr = _cv2.cvtColor(np.array(img_pil), _cv2.COLOR_RGB2GRAY)
                # Adaptive threshold
                thresh = _cv2.adaptiveThreshold(arr, 255, _cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                _cv2.THRESH_BINARY, 11, 2)
                # Sharpen
                kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
                sharp = _cv2.filter2D(arr, -1, kernel)
                for variant in [thresh, sharp]:
                    pil_v = _Image.fromarray(variant)
                    for angle in [0, 90, 180, 270]:
                        candidates.append(pil_v.rotate(angle, expand=True))

            for img in candidates:
                result = _pyzbar.decode(img)
                if result:
                    return result
            return []

        barcodes = _try_decode(pil_img)
        if barcodes:
            code = barcodes[0].data.decode('utf-8')
            detected_barcode = code
            st.success(t('barcode_found', code=code))
        else:
            st.info(t('barcode_not_found'))
    except Exception as e:
        st.warning(f"Barcode detection error: {e}")
        st.info(t('libzbar_missing'))
else:
    st.info(t('pyzbar_missing'))
    manual_barcode = st.text_input('Enter barcode manually')
    if manual_barcode.strip():
        detected_barcode = manual_barcode.strip()

# Auto-search if barcode found
if detected_barcode:
    with st.spinner(t('searching')):
        found = search_by_barcode(detected_barcode)
    if found:
        st.success(f"Found: **{found.get('name','')}** — {found.get('brand','')}")
        if st.button('Go to product detail'):
            st.session_state['selected_product'] = found
            st.session_state['portion_product'] = found
            st.switch_page('pages/1_Detail.py')
    else:
        st.warning(f"Barcode {detected_barcode} not found in Open Food Facts — you can upload it below.")

st.divider()

# ── OCR ───────────────────────────────────────────────────────────────────────
ocr_ingredients = ''
ocr_nutrients = ''

if _easyocr_ok:
    with st.expander('🔍 Run OCR (slow on first run — downloads models ~1GB)'):
        if st.button('Run OCR on this image'):
            with st.spinner('Running OCR... (first run may take several minutes)'):
                try:
                    reader = _easyocr.Reader(['en'], gpu=False)
                    ocr_results = reader.readtext(img_array, detail=0)
                    full_text = '\n'.join(ocr_results)

                    # Heuristic split: lines with numbers → nutrients, rest → ingredients
                    lines = full_text.split('\n')
                    ingr_lines = [l for l in lines if not any(c.isdigit() for c in l[:20])]
                    nutr_lines = [l for l in lines if any(c.isdigit() for c in l[:20])]

                    ocr_ingredients = '\n'.join(ingr_lines)
                    ocr_nutrients = '\n'.join(nutr_lines)
                    st.session_state['ocr_ingredients'] = ocr_ingredients
                    st.session_state['ocr_nutrients'] = ocr_nutrients
                    st.success('OCR complete')
                except Exception as e:
                    st.error(f"OCR error: {e}")

    ocr_ingredients = st.session_state.get('ocr_ingredients', '')
    ocr_nutrients = st.session_state.get('ocr_nutrients', '')
else:
    st.info(t('easyocr_missing'))

st.divider()

# ── Edit fields before upload ─────────────────────────────────────────────────
st.subheader(t('edit_before_upload'))

product_name_input = st.text_input(
    'Product name',
    value='' if not detected_barcode else (
        st.session_state.get('selected_product', {}) or {}
    ).get('name', ''),
)
brand_input = st.text_input('Brand')
barcode_input = st.text_input('Barcode / EAN', value=detected_barcode or '')

ingredients_input = st.text_area(
    t('ocr_ingredients'),
    value=ocr_ingredients,
    height=120,
    help='Edit detected ingredients or paste them manually',
)

nutrients_input = st.text_area(
    t('ocr_nutrients'),
    value=ocr_nutrients,
    height=120,
    help='Edit detected nutrition table text',
)

# ── Translate ─────────────────────────────────────────────────────────────────
if ingredients_input.strip():
    if st.button(t('translate_to_english')):
        with st.spinner(t('translating')):
            try:
                from deep_translator import GoogleTranslator
                translated = GoogleTranslator(source='auto', target='en').translate(ingredients_input)
                st.session_state['translated_ingredients'] = translated
                st.rerun()
            except Exception as e:
                st.error(f"Translation error: {e}")

    if st.session_state.get('translated_ingredients'):
        st.info('Translated:')
        translated_text = st.text_area(
            'Translated ingredients',
            value=st.session_state['translated_ingredients'],
            height=100,
        )
        if st.button('Use translated version'):
            ingredients_input = translated_text

st.divider()

# ── Upload to Open Food Facts ─────────────────────────────────────────────────
st.subheader(t('upload_to_off'))
st.info(t('off_login_required'))

with st.expander('Login & Upload'):
    off_user = st.text_input(t('off_username'))
    off_pass = st.text_input(t('off_password'), type='password')

    if st.button(t('upload_to_off'), type='primary'):
        if not off_user or not off_pass:
            st.error('Please enter your Open Food Facts username and password.')
        elif not barcode_input.strip():
            st.error('Barcode is required to upload.')
        else:
            with st.spinner('Uploading...'):
                try:
                    import requests
                    payload = {
                        'code': barcode_input.strip(),
                        'product_name': product_name_input,
                        'brands': brand_input,
                        'ingredients_text': ingredients_input,
                        'user_id': off_user,
                        'password': off_pass,
                    }
                    resp = requests.post(
                        'https://world.openfoodfacts.org/cgi/product_jqm2.pl',
                        data=payload,
                        headers={'User-Agent': 'OjasFuel/1.0'},
                        timeout=15,
                    )
                    data = resp.json()
                    if data.get('status') == 1:
                        st.success(t('upload_success'))
                        st.markdown(f"[View product](https://world.openfoodfacts.org/product/{barcode_input.strip()})")
                    else:
                        st.error(t('upload_failed', err=data.get('status_verbose', 'Unknown error')))
                except Exception as e:
                    st.error(t('upload_failed', err=str(e)))
