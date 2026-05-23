"""
OjasFuel — Home / Search page
"""

import streamlit as st
import sys
import os as _os, tempfile as _tempfile
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session, get_lang
from src.theme import inject_theme
from src.api_client import search_by_name, search_by_barcode
from src import smae_client
from src.classifier import ProductClassifier

st.set_page_config(
    page_title='OjasFuel',
    page_icon='🌿',
    layout='wide',
    initial_sidebar_state='collapsed',
)

init_session()
inject_theme()
classifier = ProductClassifier()

# ── Live barcode scanner component (ZXing) ────────────────────────────────────
_SCANNER_COMPONENT_DIR = _os.path.join(_tempfile.gettempdir(), 'ojsfuel_barcode_scanner_home')
_os.makedirs(_SCANNER_COMPONENT_DIR, exist_ok=True)

_SCANNER_HTML_TEMPLATE = """
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

  #vignette {
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at center,
      transparent 50%,
      rgba(0,0,0,0.55) 100%);
    pointer-events: none;
    border-radius: 16px;
  }

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
  <div id="status">{js_init_camera}</div>
</div>

<div id="result">
  <div id="result-label">{js_barcode_detected_label}</div>
  <div id="result-code"></div>
</div>

<script src="https://unpkg.com/@zxing/library@0.19.3/umd/index.min.js"></script>
<script>
window.parent.postMessage({
  isStreamlitMessage: true,
  type: 'streamlit:componentReady',
  apiVersion: 1,
}, '*');

window.parent.postMessage({
  isStreamlitMessage: true,
  type: 'streamlit:setFrameHeight',
  height: 420,
}, '*');

(async () => {
  const video    = document.getElementById('video');
  const status   = document.getElementById('status');
  const dot      = document.getElementById('status-dot');
  const resultEl = document.getElementById('result');
  const code     = document.getElementById('result-code');

  const hints = new Map();
  hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
  hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
    ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8,
    ZXing.BarcodeFormat.UPC_A,  ZXing.BarcodeFormat.UPC_E,
    ZXing.BarcodeFormat.CODE_128, ZXing.BarcodeFormat.CODE_39,
  ]);
  const reader = new ZXing.BrowserMultiFormatReader(hints);

  const setStatus = (text, cls) => {
    status.textContent = text;
    status.className = cls || '';
    dot.style.background = cls === 'success' ? '#00e676'
                         : cls === 'error'   ? '#ff4d6d' : '#00d4ff';
    dot.style.boxShadow  = cls === 'success' ? '0 0 6px #00e676'
                         : cls === 'error'   ? '0 0 6px #ff4d6d' : '0 0 6px #00d4ff';
  };

  function capturePhoto() {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0);
    return canvas.toDataURL('image/jpeg', 0.92);
  }

  try {
    setStatus('{js_scanning}', 'active');

    const autoPhotoTimer = setTimeout(() => {
      reader.reset();
      const dataUrl = capturePhoto();
      setStatus('{js_analyzing_photo}', 'active');
      dot.style.animation = 'none';
      window.parent.postMessage({
        isStreamlitMessage: true,
        type: 'streamlit:setComponentValue',
        value: 'PHOTO:' + dataUrl,
        dataType: 'json',
      }, '*');
    }, 5000);

    await reader.decodeFromConstraints(
      { video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } } },
      'video',
      (res, err) => {
        if (res) {
          clearTimeout(autoPhotoTimer);
          const barcode = res.getText();
          setStatus('{js_detected}', 'success');
          code.textContent = barcode;
          resultEl.style.display = 'block';
          dot.style.animation = 'none';
          reader.reset();
          window.parent.postMessage({
            isStreamlitMessage: true,
            type: 'streamlit:setComponentValue',
            value: barcode,
            dataType: 'json',
          }, '*');
        }
      }
    );
  } catch (e) {
    setStatus('{js_camera_error}' + e.message, 'error');
    dot.style.animation = 'none';
  }
})();
</script>
</body>
</html>
"""

def _build_scanner_html() -> str:
    from src.i18n import t
    html = _SCANNER_HTML_TEMPLATE
    html = html.replace('{js_init_camera}', t('init_camera'))
    html = html.replace('{js_scanning}', t('scanning_barcode_js'))
    html = html.replace('{js_detected}', t('barcode_detected_js'))
    html = html.replace('{js_camera_error}', t('camera_error_js'))
    html = html.replace('{js_barcode_detected_label}', t('detected_barcode'))
    html = html.replace('{js_analyzing_photo}', t('js_analyzing_photo'))
    return html

with open(_os.path.join(_SCANNER_COMPONENT_DIR, 'index.html'), 'w') as _f:
    _f.write(_build_scanner_html())

_barcode_scanner_component = st.components.v1.declare_component(
    'barcode_scanner_home',
    path=_SCANNER_COMPONENT_DIR,
)


def _is_barcode(query: str) -> bool:
    return query.strip().isdigit() and 8 <= len(query.strip()) <= 14


def _try_decode_pyzbar(img_pil):
    try:
        import pyzbar.pyzbar as _pyzbar
        import cv2 as _cv2
        import numpy as _np
        from PIL import Image as _PILImage
    except ImportError:
        return []
    candidates = [img_pil]
    try:
        arr = _cv2.cvtColor(_np.array(img_pil), _cv2.COLOR_RGB2GRAY)
        kernel = _np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharp = _cv2.filter2D(arr, -1, kernel)
        candidates.append(_PILImage.fromarray(sharp))
    except Exception:
        pass
    for img in candidates:
        result = _pyzbar.decode(img)
        if result:
            return result
    return []


def _diet_tags(product: dict) -> tuple[str, str]:
    """Return (badge, css_class). Uses classifier result if available, else OFF tags."""
    cl = product.get('_classification', {})
    is_vegan = cl.get('is_vegan') if cl else None
    is_vegetarian = cl.get('is_vegetarian') if cl else None

    # Fall back to OFF's own analysis tags when classifier has no ingredients
    if is_vegan is None and is_vegetarian is None:
        off = product.get('_off_tags', {})
        is_vegan = off.get('is_vegan')
        is_vegetarian = off.get('is_vegetarian')

    if is_vegan:
        return t('vegan_tag'), 'tag-vegan'
    if is_vegetarian:
        return t('vegetarian_tag'), 'tag-veg'
    if is_vegan is None and is_vegetarian is None:
        return t('unknown_tag'), 'tag-unknown'
    return t('not_vegetarian_tag'), 'tag-no'


def _filter_tag(product: dict) -> str:
    cl = product.get('_classification', {})
    if not cl:
        return ''
    if cl.get('passes_filters'):
        return t('passes_filter')
    violations = cl.get('violations', [])
    if violations:
        return t('fails_filter') + '\n• ' + '\n• '.join(violations[:3])
    return ''


def _classify_results(products: list) -> list:
    """
    Classify products and filter out those that fail the active diet mode.
    Priority: OFF's own analysis tags > our regex classifier.
    OFF tags are human-verified; classifier runs only when OFF has no data.
    """
    settings = st.session_state['settings']
    mode = settings.get('mode', 'vegetarian')
    filtered = []

    for p in products:
        off = p.get('_off_tags', {})
        off_veg = off.get('is_vegetarian')   # True / False / None
        off_vegan = off.get('is_vegan')       # True / False / None

        p['_classification'] = classifier.classify(p.get('ingredients', ''), settings, product_name=p.get('name', ''))
        cl = p['_classification']

        # Country post-filter: client-side check on countries_tags
        # (secondary guard — server-side already scoped by cc subdomain when available)
        cs = settings.get('countries', {})
        country_tags = cs.get('tags', []) if isinstance(cs, dict) else cs  # compat
        if country_tags:
            prod_countries = p.get('countries_tags', [])
            if prod_countries and not any(c in prod_countries for c in country_tags):
                continue
            # no countries_tags on product → pass through (incomplete metadata)

        # Always hide meat/fish/gelatin — regardless of mode
        is_veg = off_veg if off_veg is not None else cl.get('is_vegetarian')
        if is_veg is False:
            continue

        if mode == 'both':
            filtered.append(p)
            continue

        # Vegan mode: also hide dairy/eggs/honey
        is_vegan = off_vegan if off_vegan is not None else cl.get('is_vegan')
        if mode == 'vegan' and is_vegan is False:
            continue

        filtered.append(p)
    return filtered


# ── Header ──────────────────────────────────────────────────────────────────
_, col_logo, _ = st.columns([2, 1, 2])
with col_logo:
    st.image('logo_text2.png', use_column_width=True)
    st.caption(t('app_subtitle'))

st.divider()

# Beta banner
settings = st.session_state['settings']
active_filters = [k for k in ('no_garlic','no_onion','no_caffeine','no_alcohol',
                               'no_mushrooms','no_gelatin','jain','lacto','ovo',
                               'ovo_lacto','strict_egg_traces') if settings.get(k)]
mode = settings.get('mode', 'vegetarian')

diet_label = f"{t('diet_mode')}: <strong>{t(mode)}</strong>"
if active_filters:
    diet_label += f" &nbsp;|&nbsp; {t('restrictions_active', n=len(active_filters))}"

# Diet mode compact banner + Settings
col_diet, col_settings = st.columns([6, 1], gap='small')
with col_diet:
    st.markdown(
        f"<div style='border:1px solid rgba(255,255,255,0.08); border-radius:6px; "
        f"padding:5px 10px; font-size:0.75rem; color:var(--text-muted); display:inline-block; width:100%;'>"
        f"{diet_label}</div>",
        unsafe_allow_html=True
    )
with col_settings:
    st.markdown("<div style='font-size:0.75rem'>", unsafe_allow_html=True)
    if st.button(t('go_to_settings'), use_container_width=True, key='settings_btn'):
        st.switch_page('pages/5_Settings.py')
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ── Search bar ───────────────────────────────────────────────────────────────
# Pre-populate text box with scanned barcode before widget renders
_scanned = st.session_state.pop('scanned_barcode', None)
if _scanned:
    st.session_state['search_query'] = _scanned

col_search, col_scan = st.columns([5, 1])
with col_search:
    query = st.text_input(
        label=t('search'),
        placeholder=t('search_placeholder'),
        label_visibility='collapsed',
        key='search_query',
    )
with col_scan:
    scan_clicked = st.button(t('scan_barcode'), use_container_width=True)

if scan_clicked:
    st.session_state['show_scanner'] = not st.session_state.get('show_scanner', False)

if st.session_state.get('show_scanner'):
    _scanner_key = st.session_state.get('scanner_key', 0)
    _live_result = _barcode_scanner_component(key=f'home_live_barcode_{_scanner_key}', default=None, height=420)
    if _live_result:
        _result_str = str(_live_result)
        if _result_str.startswith('PHOTO:'):
            import base64 as _b64, re as _re, io as _io
            from PIL import Image as _PILImg
            _data_url = _result_str[6:]
            _b64_data = _re.sub(r'^data:image/\w+;base64,', '', _data_url)
            _img_bytes = _b64.b64decode(_b64_data)
            _pil_img = _PILImg.open(_io.BytesIO(_img_bytes)).convert('RGB')
            _barcodes = _try_decode_pyzbar(_pil_img)
            if _barcodes:
                st.session_state['show_scanner'] = False
                st.session_state['scanned_barcode'] = _barcodes[0].data.decode('utf-8')
                st.rerun()
            else:
                st.session_state['show_scanner'] = False
                st.session_state['photo_retry'] = True
                st.rerun()
        elif _is_barcode(_result_str):
            st.session_state['show_scanner'] = False
            st.session_state['scanned_barcode'] = _result_str
            st.rerun()

if st.session_state.pop('photo_retry', False):
    st.warning(t('barcode_not_detected'))
    if st.button(t('retry_scan')):
        st.session_state['show_scanner'] = True
        st.session_state['scanner_key'] = st.session_state.get('scanner_key', 0) + 1
        st.rerun()

search_clicked = st.button(t('search_button'), type='primary', use_container_width=False)

# Auto-search when barcode was just scanned (no button press needed)
auto_search = bool(_scanned)

if (search_clicked and query.strip()) or (auto_search and query.strip()):
    with st.spinner(t('searching')):
        try:
            cs = settings.get('countries', {})
            cc = cs.get('cc') if isinstance(cs, dict) else None
            is_mexico = cc == 'mx'

            if _is_barcode(query.strip()):
                # For Mexico: try OFF first (some products may have barcodes), then show hint
                product = search_by_barcode(query.strip())
                if product:
                    products = [product]
                else:
                    products = []
                    if is_mexico:
                        st.warning(t('smae_no_barcode'))
                    else:
                        st.warning(t('barcode_not_found_off', code=query.strip()))
                    st.session_state['contribute_prefill_barcode'] = query.strip()
            elif is_mexico:
                # Hybrid: SMAE first, then OFF Mexico
                smae_results = smae_client.search_by_name(query.strip(), page_size=20)
                try:
                    off_results = search_by_name(query.strip(), page_size=10, country_code='mx')
                except Exception:
                    off_results = []
                seen_names = {r['name'].lower() for r in smae_results}
                products = smae_results + [
                    p for p in off_results if p['name'].lower() not in seen_names
                ]
            else:
                products = search_by_name(query.strip(), page_size=20, country_code=cc)
        except Exception as e:
            st.error(f"{t('error')}: {e}")
            products = []

    if products:
        products = _classify_results(products)
        st.session_state['search_results'] = products
        st.success(t('results_count', n=len(products)))
    elif query.strip() and not _is_barcode(query.strip()):
        st.session_state['search_results'] = []
        st.session_state['contribute_prefill_name'] = query.strip()
        st.warning(t('no_results'))

# ── Contribute prompt (shown only after a failed search) ─────────────────────
_no_results_after_search = (
    (search_clicked or auto_search)
    and query.strip()
    and not st.session_state.get('search_results')
)
if _no_results_after_search or st.session_state.get('contribute_prefill_barcode'):
    st.divider()
    st.caption('🔍 ' + t('not_found_prompt'))
    st.page_link('pages/6_Contribute.py', label=t('contribute_button'), icon='➕')

# ── Results ──────────────────────────────────────────────────────────────────
results = st.session_state.get('search_results', [])

if results:
    st.subheader(t('results_count', n=len(results)))

    for idx, product in enumerate(results):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])

            with c1:
                name = product.get('name') or 'Unknown'
                brand = product.get('brand') or ''
                source = product.get('_source', '')
                st.markdown(f"**{name}**")
                if source == 'smae':
                    st.caption(f"🇲🇽 {t('smae_source_label')}")
                elif brand:
                    st.caption(brand)

                # Ingredients preview (skip for SMAE entries — no real ingredient list)
                if source != 'smae':
                    ingr = product.get('ingredients', '')
                    if ingr:
                        preview = ingr[:120] + ('…' if len(ingr) > 120 else '')
                        st.caption(f"_{preview}_")
                    else:
                        st.caption(f"_{t('no_ingredients')}_")

            with c2:
                diet_tag, _ = _diet_tags(product)
                st.markdown(diet_tag)

                cl = product.get('_classification', {})
                if cl.get('confidence'):
                    st.caption(f"{t('confidence')}: {cl['confidence']*100:.0f}%")

                filter_tag = _filter_tag(product)
                if filter_tag:
                    st.caption(filter_tag)

                qty = product.get('quantity', '')
                nutri = product.get('nutriscore', '')
                if qty:
                    st.caption(f"📦 {qty}")
                if nutri:
                    st.caption(f"{t('nutriscore')}: **{nutri}**")

            with c3:
                if st.button(t('view_detail'), key=f'detail_{idx}', use_container_width=True):
                    st.session_state['selected_product'] = product
                    st.session_state['portion_product'] = product
                    st.session_state['equiv_original'] = product
                    st.switch_page('pages/1_Detail.py')
