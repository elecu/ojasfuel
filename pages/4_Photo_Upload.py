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

# ── Page-level style overrides ────────────────────────────────────────────────
st.markdown("""
<style>
/* Radio group — pill-style selector */
[data-testid="stRadio"] > div {
    display: flex !important;
    flex-direction: row !important;
    gap: 0.5rem !important;
    flex-wrap: wrap !important;
}
[data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    gap: 0.4rem !important;
    padding: 0.35rem 0.9rem !important;
    border-radius: 999px !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-surface) !important;
    cursor: pointer !important;
    transition: all 0.22s ease !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
}
[data-testid="stRadio"] label:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--accent-dim) !important;
}
/* Active radio — glow pill */
[data-testid="stRadio"] label:has(input:checked) {
    border-color: var(--accent) !important;
    background: var(--accent-dim) !important;
    color: var(--accent) !important;
    box-shadow: 0 0 10px var(--accent-glow), 0 0 0 1px var(--border-accent) !important;
    font-weight: 600 !important;
}
[data-testid="stRadio"] label input[type="radio"] {
    accent-color: var(--accent) !important;
}

/* Alert boxes — sharper dark-theme look */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    font-family: 'Inter', sans-serif !important;
    backdrop-filter: blur(4px) !important;
}
[data-testid="stAlert"] svg {
    color: inherit !important;
    flex-shrink: 0 !important;
}

/* Title accent */
[data-testid="stHeading"] h1 {
    letter-spacing: 0.03em !important;
    background: linear-gradient(135deg, var(--text-primary) 60%, var(--accent));
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* Divider spacing */
[data-testid="stDivider"] { margin: 1.75rem 0 !important; }

/* iframe (scanner) container */
[data-testid="stComponents"] iframe,
iframe {
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border) !important;
}
</style>
""", unsafe_allow_html=True)

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
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #0a0a0f;
    font-family: 'Inter', system-ui, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
    padding: 12px 8px 16px;
    color: #f0f0f5;
  }

  /* ── Viewfinder wrapper ── */
  #scanner-container {
    position: relative;
    width: 100%;
    max-width: 460px;
    aspect-ratio: 4 / 3;
    border-radius: 16px;
    overflow: hidden;
    background: #0d0d1a;
    box-shadow: 0 0 40px rgba(0, 230, 118, 0.08), 0 8px 32px rgba(0,0,0,0.5);
  }

  video {
    width: 100%; height: 100%;
    object-fit: cover;
    display: block;
    border-radius: 16px;
  }

  #overlay {
    position: absolute; top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    border-radius: 16px;
  }

  /* ── Dark vignette around edges ── */
  #vignette {
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at center,
      transparent 50%,
      rgba(0,0,0,0.55) 100%);
    pointer-events: none;
    border-radius: 16px;
  }

  /* ── Viewfinder reticle: corner brackets ── */
  #reticle {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 56%; height: 56%;
    pointer-events: none;
  }
  .corner {
    position: absolute;
    width: 22px; height: 22px;
    border-color: #00e676;
    border-style: solid;
    border-width: 0;
    border-radius: 3px;
    transition: opacity 0.3s ease;
  }
  .corner.tl { top: 0; left: 0;  border-top-width: 3px; border-left-width: 3px;
    box-shadow: -2px -2px 8px rgba(0,230,118,0.35); }
  .corner.tr { top: 0; right: 0; border-top-width: 3px; border-right-width: 3px;
    box-shadow: 2px -2px 8px rgba(0,230,118,0.35); }
  .corner.bl { bottom: 0; left: 0;  border-bottom-width: 3px; border-left-width: 3px;
    box-shadow: -2px 2px 8px rgba(0,230,118,0.35); }
  .corner.br { bottom: 0; right: 0; border-bottom-width: 3px; border-right-width: 3px;
    box-shadow: 2px 2px 8px rgba(0,230,118,0.35); }

  /* ── Scan line ── */
  .scan-line {
    position: absolute;
    left: 22%; width: 56%;
    height: 2px;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(0,212,255,0.5) 20%,
      #00d4ff 50%,
      rgba(0,212,255,0.5) 80%,
      transparent 100%);
    border-radius: 2px;
    filter: blur(0.5px);
    animation: scanMove 2.2s cubic-bezier(0.4,0,0.6,1) infinite;
    box-shadow: 0 0 8px #00d4ff, 0 0 16px rgba(0,212,255,0.4);
    pointer-events: none;
  }
  @keyframes scanMove {
    0%   { top: 22%; opacity: 0; }
    8%   { opacity: 1; }
    92%  { opacity: 1; }
    100% { top: 78%; opacity: 0; }
  }

  /* ── Status bar ── */
  #status-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-top: 14px;
    width: 100%;
    max-width: 460px;
  }
  #status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00d4ff;
    box-shadow: 0 0 6px #00d4ff;
    flex-shrink: 0;
    animation: pulse 1.6s ease-in-out infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.45; transform: scale(0.75); }
  }
  #status {
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.03em;
    color: #a0a0c0;
    transition: color 0.3s ease;
  }
  #status.active  { color: #00d4ff; }
  #status.success { color: #00e676; }
  #status.error   { color: #ff4d6d; }

  /* ── Result card ── */
  #result {
    display: none;
    margin-top: 16px;
    width: 100%;
    max-width: 460px;
    background: rgba(0, 230, 118, 0.06);
    border: 1px solid rgba(0, 230, 118, 0.35);
    border-radius: 14px;
    padding: 16px 20px;
    text-align: center;
    box-shadow: 0 0 24px rgba(0, 230, 118, 0.12), 0 0 48px rgba(0,230,118,0.06);
    animation: resultIn 0.35s cubic-bezier(0.22,1,0.36,1) forwards;
  }
  @keyframes resultIn {
    from { opacity: 0; transform: translateY(10px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }
  #result-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #00e676;
    margin-bottom: 6px;
    opacity: 0.75;
  }
  #result-code {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #00e676;
    text-shadow: 0 0 12px rgba(0,230,118,0.5);
    word-break: break-all;
  }
</style>
</head>
<body>

<div id="scanner-container">
  <video id="video" autoplay playsinline muted></video>
  <canvas id="overlay"></canvas>
  <div id="vignette"></div>
  <div id="reticle">
    <div class="corner tl"></div>
    <div class="corner tr"></div>
    <div class="corner bl"></div>
    <div class="corner br"></div>
  </div>
  <div class="scan-line"></div>
</div>

<div id="status-bar">
  <div id="status-dot"></div>
  <div id="status">Initializing camera...</div>
</div>

<div id="result">
  <div id="result-label">Barcode Detected</div>
  <div id="result-code"></div>
</div>

<script src="https://unpkg.com/@zxing/library@0.19.3/umd/index.min.js"></script>
<script>
(async () => {
  const video  = document.getElementById('video');
  const status = document.getElementById('status');
  const dot    = document.getElementById('status-dot');
  const result = document.getElementById('result');
  const code   = document.getElementById('result-code');
  const codeReader = new ZXing.BrowserMultiFormatReader();

  const setStatus = (text, cls) => {
    status.textContent = text;
    status.className = cls || '';
    dot.style.background = cls === 'success' ? '#00e676'
                         : cls === 'error'   ? '#ff4d6d' : '#00d4ff';
    dot.style.boxShadow  = cls === 'success' ? '0 0 6px #00e676'
                         : cls === 'error'   ? '0 0 6px #ff4d6d' : '0 0 6px #00d4ff';
  };

  try {
    const devices  = await ZXing.BrowserCodeReader.listVideoInputDevices();
    const deviceId = devices.length > 1
      ? devices[devices.length - 1].deviceId
      : undefined;

    setStatus('Scanning for barcode...', 'active');

    await codeReader.decodeFromVideoDevice(deviceId, 'video', (res, err) => {
      if (res) {
        const barcode = res.getText();
        setStatus('Barcode detected!', 'success');
        code.textContent = barcode;
        result.style.display = 'block';
        dot.style.animation = 'none';
        codeReader.reset();
        const url = new URL(window.parent.location.href);
        url.searchParams.set('barcode', barcode);
        setTimeout(() => { window.parent.location.href = url.toString(); }, 600);
      }
    });
  } catch (e) {
    setStatus('Camera error: ' + e.message, 'error');
    dot.style.animation = 'none';
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
