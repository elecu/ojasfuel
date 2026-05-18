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

# ── Live barcode scanner component ────────────────────────────────────────────
SCANNER_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; background: #0d0d1a; font-family: sans-serif; }
  #scanner-container {
    position: relative; width: 100%; max-width: 480px; margin: 0 auto;
  }
  video { width: 100%; border-radius: 12px; display: block; }
  #overlay {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none;
  }
  #status {
    text-align: center; padding: 8px; color: #00d4ff;
    font-size: 14px; min-height: 24px;
  }
  #result {
    text-align: center; padding: 12px; color: #00ff9d;
    font-size: 18px; font-weight: 600; letter-spacing: 0.05em;
    display: none;
  }
  .scan-line {
    position: absolute; left: 10%; width: 80%; height: 2px;
    background: linear-gradient(90deg, transparent, #00d4ff, transparent);
    animation: scanMove 2s linear infinite;
    top: 20%;
  }
  @keyframes scanMove {
    0% { top: 20%; opacity: 1; }
    100% { top: 80%; opacity: 0.3; }
  }
</style>
</head>
<body>
<div id="scanner-container">
  <video id="video" autoplay playsinline muted></video>
  <canvas id="overlay"></canvas>
  <div class="scan-line"></div>
</div>
<div id="status">Initializing camera...</div>
<div id="result"></div>
<script src="https://unpkg.com/@zxing/library@0.19.3/umd/index.min.js"></script>
<script>
(async () => {
  const video = document.getElementById('video');
  const status = document.getElementById('status');
  const result = document.getElementById('result');
  const codeReader = new ZXing.BrowserMultiFormatReader();

  try {
    const devices = await ZXing.BrowserCodeReader.listVideoInputDevices();
    const deviceId = devices.length > 1
      ? devices[devices.length - 1].deviceId  // prefer back camera
      : undefined;

    status.textContent = '🔍 Scanning for barcode...';

    await codeReader.decodeFromVideoDevice(deviceId, 'video', (res, err) => {
      if (res) {
        const code = res.getText();
        status.textContent = '✅ Barcode detected!';
        result.textContent = code;
        result.style.display = 'block';
        codeReader.reset();
        // Pass barcode to Streamlit via query param + reload
        const url = new URL(window.parent.location.href);
        url.searchParams.set('barcode', code);
        window.parent.location.href = url.toString();
      }
    });
  } catch (e) {
    status.textContent = '❌ Camera error: ' + e.message;
  }
})();
</script>
</body>
</html>
"""

# ── Check for barcode from live scanner ───────────────────────────────────────
scanned_from_url = st.query_params.get('barcode', '')
if scanned_from_url:
    st.success(f"📸 Barcode scanned: **{scanned_from_url}**")
    if st.button('Clear scan & scan again'):
        st.query_params.clear()
        st.rerun()

st.divider()

# ── Image source ──────────────────────────────────────────────────────────────
MODE_LIVE = '📡 Live Scan'
MODE_UPLOAD = t('upload_file')
MODE_PHOTO = t('take_photo')

source = st.radio(t('photo_source'), [MODE_LIVE, MODE_UPLOAD, MODE_PHOTO], horizontal=True)

img_data = None
detected_barcode = scanned_from_url or None

if source == MODE_LIVE:
    st.components.v1.html(SCANNER_HTML, height=420, scrolling=False)
    if not scanned_from_url:
        st.info('Point camera at barcode — it will be detected automatically.')
    st.stop()
elif source == MODE_PHOTO:
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

# ── Barcode detection (from image) ────────────────────────────────────────────
st.subheader(t('detected_barcode'))

if not detected_barcode:
    if _pyzbar_ok:
        try:
            def _try_decode(img_pil):
                candidates = []
                for angle in [0, 90, 180, 270]:
                    candidates.append(img_pil.rotate(angle, expand=True))
                if _cv2_ok:
                    arr = _cv2.cvtColor(_np.array(img_pil), _cv2.COLOR_RGB2GRAY)
                    thresh = _cv2.adaptiveThreshold(arr, 255, _cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                    _cv2.THRESH_BINARY, 11, 2)
                    kernel = _np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
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
                detected_barcode = barcodes[0].data.decode('utf-8')
                st.success(t('barcode_found', code=detected_barcode))
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
