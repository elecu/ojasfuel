"""
OjasFuel — Home / Search page
"""

import streamlit as st
import os as _os, tempfile as _tempfile

from src.i18n import t, init_session, get_lang
from src.theme import inject_theme
from src.api_client import search_by_name, search_by_barcode, OFFConnectionError
from src import smae_client
from src.filtering import classify_results, allergy_violations, resolve_diet
from src.barcode import is_barcode, normalize_barcode, decode_image
from src.ui_helpers import diet_source_label

st.set_page_config(
    page_title='OjasFuel',
    page_icon='🌿',
    layout='wide',
    initial_sidebar_state='collapsed',
)

init_session()
inject_theme()

# ── Live barcode scanner component (ZXing) ────────────────────────────────────
_LANG = get_lang()
_SCANNER_COMPONENT_DIR = _os.path.join(_tempfile.gettempdir(), f'ojsfuel_barcode_scanner_home_{_LANG}')
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

  #capture-btn {
    margin-top: 12px;
    background: #00e676;
    color: #04210f;
    border: 0;
    border-radius: 999px;
    padding: 10px 26px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }
  #capture-btn:disabled { opacity: 0.5; cursor: default; }

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

<button id="capture-btn" type="button">{js_capture}</button>

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
  height: 480,
}, '*');

(async () => {
  const video    = document.getElementById('video');
  const status   = document.getElementById('status');
  const dot      = document.getElementById('status-dot');
  const resultEl = document.getElementById('result');
  const code     = document.getElementById('result-code');
  const captureBtn = document.getElementById('capture-btn');

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

    let sent = false;
    const sendPhoto = () => {
      if (sent) return;
      sent = true;
      clearTimeout(autoPhotoTimer);
      const dataUrl = capturePhoto();
      reader.reset();
      captureBtn.disabled = true;
      setStatus('{js_analyzing_photo}', 'active');
      dot.style.animation = 'none';
      window.parent.postMessage({
        isStreamlitMessage: true,
        type: 'streamlit:setComponentValue',
        value: 'PHOTO:' + dataUrl,
        dataType: 'json',
      }, '*');
    };
    const autoPhotoTimer = setTimeout(sendPhoto, 10000);
    captureBtn.addEventListener('click', sendPhoto);

    await reader.decodeFromConstraints(
      { video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } } },
      'video',
      (res, err) => {
        if (res && !sent) {
          sent = true;
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
    html = html.replace('{js_capture}', t('capture_photo'))
    return html


def _write_if_changed(path: str, content: str) -> None:
    try:
        with open(path, 'r') as f:
            if f.read() == content:
                return
    except OSError:
        pass
    tmp = f'{path}.{_os.getpid()}.tmp'
    with open(tmp, 'w') as f:
        f.write(content)
    _os.replace(tmp, path)  # atomic: no half-written file for other users


_write_if_changed(_os.path.join(_SCANNER_COMPONENT_DIR, 'index.html'), _build_scanner_html())

_barcode_scanner_component = st.components.v1.declare_component(
    f'barcode_scanner_home_{_LANG}',
    path=_SCANNER_COMPONENT_DIR,
)


def _diet_tags(product: dict) -> tuple[str, str]:
    """Return (badge, css_class) from the shared resolve_diet result."""
    d = product.get('_diet') or {}
    is_vegan = d.get('is_vegan')
    is_vegetarian = d.get('is_vegetarian')
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


# ── Header ──────────────────────────────────────────────────────────────────
_, col_logo, _ = st.columns([2, 1, 2])
with col_logo:
    st.image('logo_text2.png', width="stretch")
    st.caption(t('app_subtitle'))

st.divider()

settings = st.session_state['settings']
active_filters = [k for k in ('no_garlic','no_onion','no_caffeine','no_alcohol',
                               'no_mushrooms','no_gelatin','jain','lacto','ovo',
                               'ovo_lacto','strict_egg_traces') if settings.get(k)]
mode = settings.get('mode', 'vegetarian')

diet_label = f"{t('diet_mode')}: **{t(mode)}**"
if active_filters:
    diet_label += f"  |  {t('restrictions_active', n=len(active_filters))}"

# Diet mode compact banner + Settings
col1, col2 = st.columns([1, 0.2], gap='small')
with col1:
    st.markdown(diet_label)
with col2:
    if st.button(f"⚙️ {t('settings')}", key='settings_btn', help=t('go_to_settings'), width='stretch'):
        st.switch_page('pages/5_Settings.py')

st.divider()

# ── Search bar ───────────────────────────────────────────────────────────────
# Pre-populate text box with scanned barcode before widget renders
_scanned = st.session_state.pop('scanned_barcode', None)
if _scanned:
    st.session_state['search_query'] = _scanned

col_search, col_scan = st.columns([5, 1])
with col_search:
    with st.form('search_form', border=False):
        query = st.text_input(
            label=t('search'),
            placeholder=t('search_placeholder'),
            label_visibility='collapsed',
            key='search_query',
        )
        search_clicked = st.form_submit_button(t('search_button'), type='primary')
with col_scan:
    scan_clicked = st.button(t('scan_barcode'), width='stretch')

if scan_clicked:
    _opening = not st.session_state.get('show_scanner', False)
    st.session_state['show_scanner'] = _opening
    if _opening:
        # New component key each time so the old value is never replayed
        st.session_state['scanner_key'] = st.session_state.get('scanner_key', 0) + 1

if st.session_state.get('show_scanner'):
    _scanner_key = st.session_state.get('scanner_key', 0)
    _live_result = _barcode_scanner_component(key=f'home_live_barcode_{_scanner_key}', default=None, height=480)
    if _live_result:
        _result_str = str(_live_result)
        if _result_str.startswith('PHOTO:'):
            import base64 as _b64, re as _re, io as _io
            from PIL import Image as _PILImg
            _data_url = _result_str[6:]
            _b64_data = _re.sub(r'^data:image/\w+;base64,', '', _data_url)
            _img_bytes = _b64.b64decode(_b64_data)
            _pil_img = _PILImg.open(_io.BytesIO(_img_bytes)).convert('RGB')
            _decoded = decode_image(_pil_img)
            st.session_state['show_scanner'] = False
            if _decoded and is_barcode(_decoded):
                st.session_state['scanned_barcode'] = _decoded
            elif _decoded:
                st.session_state['scan_invalid_code'] = _decoded
            else:
                st.session_state['photo_retry'] = True
            st.rerun()
        elif is_barcode(_result_str):
            st.session_state['show_scanner'] = False
            st.session_state['scanned_barcode'] = _result_str
            st.rerun()
        else:
            # Non-numeric symbology (CODE_128 / CODE_39): tell the user instead of hanging
            st.session_state['show_scanner'] = False
            st.session_state['scan_invalid_code'] = _result_str
            st.rerun()

st.caption('⌨️ ' + t('manual_barcode_hint'))

_invalid_code = st.session_state.pop('scan_invalid_code', None)
if _invalid_code:
    st.warning(t('barcode_non_numeric', code=_invalid_code))

if st.session_state.pop('photo_retry', False):
    st.warning(t('barcode_not_detected'))
    if st.button(t('retry_scan')):
        st.session_state['show_scanner'] = True
        st.session_state['scanner_key'] = st.session_state.get('scanner_key', 0) + 1
        st.rerun()

# Decide whether to run a search this run
run_query = None
if search_clicked and query.strip():
    run_query = query.strip()
elif _scanned and query.strip():
    run_query = query.strip()
else:
    _retry = st.session_state.pop('retry_query', None)
    if _retry:
        run_query = _retry


def _retry_search(code: str):
    st.session_state['retry_query'] = code


if run_query:
    st.session_state.pop('conn_error_code', None)
    products = []
    conn_error = False
    with st.spinner(t('searching')):
        try:
            cs = settings.get('countries', {})
            cc = cs.get('cc') if isinstance(cs, dict) else None
            is_mexico = cc == 'mx'

            if is_barcode(run_query):
                try:
                    product = search_by_barcode(normalize_barcode(run_query))
                except OFFConnectionError:
                    product = None
                    conn_error = True
                    st.session_state['conn_error_code'] = run_query
                products = [product] if product else []
                if not product and not conn_error:
                    if is_mexico:
                        st.warning(t('smae_no_barcode'))
                    else:
                        st.warning(t('barcode_not_found_off', code=run_query))
            elif is_mexico:
                # Hybrid: SMAE first, then OFF Mexico
                smae_results = smae_client.search_by_name(run_query, page_size=20)
                try:
                    off_results = search_by_name(run_query, page_size=10, country_code='mx')
                except Exception:
                    off_results = []
                seen_names = {r['name'].lower() for r in smae_results}
                products = smae_results + [
                    p for p in off_results if p['name'].lower() not in seen_names
                ]
            else:
                products = search_by_name(run_query, page_size=20, country_code=cc)
        except Exception as e:
            st.error(f"{t('error')}: {e}")
            products = []

    if products and is_barcode(run_query):
        # Exact barcode lookup: never hide the product, just label it
        for _p in products:
            _p['_diet'] = resolve_diet(_p, settings)
            _p['_classification'] = _p['_diet']['classification']
    elif products:
        products = classify_results(products, settings)

    if products:
        st.session_state['search_results'] = products
        st.session_state['last_search_empty'] = False
    else:
        st.session_state['search_results'] = []
        if conn_error:
            st.session_state['last_search_empty'] = False
        else:
            st.session_state['last_search_empty'] = True
            if is_barcode(run_query):
                st.session_state['contribute_prefill_barcode'] = normalize_barcode(run_query)
            else:
                st.session_state['contribute_prefill_name'] = run_query
                st.warning(t('no_results'))

# ── Connection error (not the same as "not found") ───────────────────────────
_conn_code = st.session_state.get('conn_error_code')
if _conn_code:
    st.error(t('connection_error'))
    st.button(t('retry_search'), key='retry_search_btn', on_click=_retry_search, args=(_conn_code,))

# ── Contribute prompt (shown only after a genuinely empty search) ────────────
if st.session_state.get('last_search_empty'):
    st.divider()
    st.caption('🔍 ' + t('not_found_prompt'))
    st.page_link('pages/6_Contribute.py', label=t('contribute_button'), icon='➕')

# ── Results ──────────────────────────────────────────────────────────────────
results = st.session_state.get('search_results', [])

if results:
    st.subheader(t('results_count', n=len(results)))

    for idx, product in enumerate(results):
        with st.container(border=True):
            c0, c1, c2, c3 = st.columns([0.6, 3, 2, 1])

            with c0:
                if product.get('image_url'):
                    st.image(product['image_url'], width=64)

            with c1:
                name = product.get('name') or 'Unknown'
                brand = product.get('brand') or ''
                source = product.get('_source', '')

                cl = product.get('_classification', {}) or {}
                allergy_hits = allergy_violations(cl) if cl else []
                if allergy_hits:
                    st.error('🚨 ' + t('allergy_warning', items=', '.join(allergy_hits[:3])))

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
                        st.caption('⚠️ ' + t('check_allergies_detail'))

            with c2:
                diet_tag, _ = _diet_tags(product)
                st.markdown(diet_tag)

                _src = (product.get('_diet') or {}).get('source', 'none')
                st.caption(diet_source_label(_src))

                filter_tag = _filter_tag(product)
                if filter_tag:
                    st.caption(filter_tag)

                qty = product.get('quantity', '')
                nutri = product.get('nutriscore', '')
                if qty:
                    st.caption(f"📦 {qty}")
                if nutri and nutri in ('A', 'B', 'C', 'D', 'E'):
                    st.caption(f"{t('nutriscore')}: **{nutri}**")

            with c3:
                if st.button(t('view_detail'), key=f'detail_{idx}', width='stretch'):
                    st.session_state['selected_product'] = product
                    st.session_state['portion_product'] = product
                    st.session_state['equiv_original'] = product
                    st.session_state['nav_from'] = 'pages/1_Detail.py'
                    st.switch_page('pages/1_Detail.py')
