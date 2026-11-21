"""
OjasFuel — Home / Search page
"""

import streamlit as st
import os as _os, tempfile as _tempfile

from src.i18n import t, init_session, get_lang
from src.theme import inject_theme
from src.api_client import OFFConnectionError
from src.barcode import is_barcode, normalize_barcode, decode_image
from src.ui_helpers import (inject_verdict_css, compute_verdict, open_verdict,
                            lookup_barcode, verdict_row, STATUS_EMOJI)
from src import history
from src.search_smart import smart_search, single_clear_match, common_foods
from src.smae_client import _normalize
from src.countries import COUNTRIES, apply_country, country_cid, country_name, ordered_ids

st.set_page_config(
    page_title='OjasFuel',
    page_icon='🌿',
    layout='wide',
    initial_sidebar_state='collapsed',
)

init_session()
inject_theme()
inject_verdict_css()
history.load_history()

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


_ONB_COUNTRIES = COUNTRIES
_ALLERGY_KEYS = ['allergies_nuts', 'allergies_peanuts', 'allergies_soy',
                 'allergies_mustard', 'allergies_sesame', 'allergies_gluten']

st.markdown("""
<style>
.st-key-scan_btn button { min-height: 4.4rem; font-size: 1.35rem; font-weight: 800; }
.st-key-search_form button { min-height: 2.6rem; }
</style>
""", unsafe_allow_html=True)


def _wk(name: str) -> str:
    """Per-language widget key so radios/selects rebuild when the language changes."""
    return f'onb_{name}_{get_lang()}'


def _onb_save() -> None:
    st.session_state['_ls_dirty'] = True


def _onb_lang() -> None:
    v = st.session_state[_wk('lang')]
    if v in ('en', 'es'):
        st.session_state['settings']['lang'] = v
        _onb_save()


def _onb_country() -> None:
    cid = st.session_state[_wk('country')]
    if cid in _ONB_COUNTRIES:
        apply_country(st.session_state['settings'], cid)
        _onb_save()


def _onb_mode() -> None:
    v = st.session_state[_wk('mode')]
    if v in ('vegetarian', 'vegan', 'both'):
        st.session_state['settings']['mode'] = v
        _onb_save()


def _onb_allergies() -> None:
    chosen = set(st.session_state[_wk('allergies')])
    for k in _ALLERGY_KEYS:
        st.session_state['settings'][k] = k in chosen
    _onb_save()


def _onb_finish() -> None:
    st.session_state['settings']['onboarded'] = True
    st.session_state.pop('onb_step', None)
    _onb_save()


def _onb_next() -> None:
    st.session_state['onb_step'] = st.session_state.get('onb_step', 0) + 1


def _onb_prev() -> None:
    st.session_state['onb_step'] = max(0, st.session_state.get('onb_step', 0) - 1)


def _render_onboarding(s: dict) -> None:
    step = st.session_state.get('onb_step', 0)
    if step > 3:
        _onb_finish()
        step = 0
    with st.container(border=True):
        st.subheader(t('onb_title'))
        st.progress((step + 1) / 4, text=t('onb_step', n=step + 1, total=4))
        if step == 0:
            st.markdown(f"**{t('language')}**")
            st.radio(t('language'), options=['en', 'es'],
                     format_func=lambda v: {'en': 'English (UK)', 'es': 'Español'}[v],
                     index=0 if s.get('lang', 'en') == 'en' else 1, horizontal=True,
                     label_visibility='collapsed', key=_wk('lang'), on_change=_onb_lang)
        elif step == 1:
            st.markdown(f"**{t('country_filter')}**")
            ids = list(_ONB_COUNTRIES)
            cur = s.get('countries', {})
            cur_cc = cur.get('cc') if isinstance(cur, dict) else None
            idx = next((i for i, c in enumerate(ids) if _ONB_COUNTRIES[c]['cc'] == cur_cc), 0)
            st.selectbox(t('country_filter'), options=ids,
                         format_func=lambda c: t('country_all_opt') if c == 'all' else t(f'country_{c}'),
                         index=idx, label_visibility='collapsed',
                         key=_wk('country'), on_change=_onb_country)
        elif step == 2:
            st.markdown(f"**{t('diet_mode')}**")
            modes = ['vegetarian', 'vegan', 'both']
            st.radio(t('diet_mode'), options=modes, format_func=lambda m: t(m),
                     index=modes.index(s.get('mode', 'vegetarian')) if s.get('mode') in modes else 0,
                     horizontal=True, label_visibility='collapsed',
                     key=_wk('mode'), on_change=_onb_mode)
        else:
            st.markdown(f"**{t('allergies')}**")
            st.multiselect(t('allergies'), options=_ALLERGY_KEYS, format_func=lambda k: t(k),
                           default=[k for k in _ALLERGY_KEYS if s.get(k)],
                           placeholder=t('onb_allergies_none'), label_visibility='collapsed',
                           key=_wk('allergies'), on_change=_onb_allergies)
        c_back, c_next, c_skip = st.columns([1, 1, 1])
        with c_back:
            if step > 0:
                st.button(t('back'), key='onb_back', on_click=_onb_prev, width='stretch')
        with c_next:
            if step < 3:
                st.button(t('onb_next'), key='onb_next', type='primary', on_click=_onb_next, width='stretch')
            else:
                st.button(t('onb_done'), key='onb_done', type='primary', on_click=_onb_finish, width='stretch')
        with c_skip:
            st.button(t('onb_skip'), key='onb_skip', on_click=_onb_finish, width='stretch')


# ── Header ──────────────────────────────────────────────────────────────────
_, col_logo, _ = st.columns([2, 1, 2])
with col_logo:
    st.image('logo_text2.png', width="stretch")
    st.caption(t('app_subtitle'))

settings = st.session_state['settings']

# First visit: quick onboarding (only once localStorage has been read)
if st.session_state.get('_ls_loaded') and not settings.get('onboarded'):
    _render_onboarding(settings)
    st.stop()

active_filters = [k for k in ('no_garlic','no_onion','no_caffeine','no_alcohol',
                               'no_mushrooms','no_gelatin','jain','lacto','ovo',
                               'ovo_lacto','strict_egg_traces') if settings.get(k)]
mode = settings.get('mode', 'vegetarian')

diet_label = f"{t('diet_mode')}: **{t(mode)}**"
if active_filters:
    diet_label += f"  |  {t('restrictions_active', n=len(active_filters))}"

def _quick_country() -> None:
    cid = st.session_state.get(_wk('quick_country'))
    s = st.session_state['settings']
    if cid in COUNTRIES and cid != country_cid(s.get('countries')):
        apply_country(s, cid)
        st.session_state['_ls_dirty'] = True
        st.session_state['search_results'] = []  # results were for the old country
        st.toast(t('country_changed', country=country_name(cid)))


col1, col_country, col2 = st.columns([1, 0.32, 0.2], gap='small')
with col1:
    st.markdown(diet_label)
with col_country:
    # Travellers: switch country in one tap, recent countries first
    _cur_cid = country_cid(settings.get('countries'))
    with st.popover(f"📍 {country_name(_cur_cid)}", width='stretch', help=t('country_switch_help')):
        _ids = ordered_ids(settings.get('recent_countries'))
        st.radio(t('change_country'), options=_ids, index=_ids.index(_cur_cid),
                 format_func=country_name, key=_wk('quick_country'), on_change=_quick_country)
with col2:
    if st.button(f"⚙️ {t('settings')}", key='settings_btn', help=t('go_to_settings'), width='stretch'):
        st.switch_page('pages/5_Settings.py')

# ── Two equal paths: scan / search by name ───────────────────────────────────
def _chip_picked() -> None:
    v = st.session_state.get('chip_pick')
    if v:
        st.session_state['pending_query'] = v
    st.session_state['chip_pick'] = None


col_scan, col_search = st.columns(2, gap='medium')
with col_scan:
    st.caption(t('path_scan_hint'))
    _label = ('✖ ' + t('close_scanner')) if st.session_state.get('show_scanner') else t('scan_big')
    scan_clicked = st.button(_label, key='scan_btn', type='primary', width='stretch')
with col_search:
    st.caption(t('path_search_hint'))
    with st.form('search_form', border=False):
        query = st.text_input(
            label=t('search'),
            placeholder=t('search_placeholder'),
            label_visibility='collapsed',
            key='search_query',
        )
        search_clicked = st.form_submit_button(t('search_button'), width='stretch')

# Quick chips: recent searches first, then common foods
_chips: list[str] = []
for _q in history.get_searches(4) + common_foods(get_lang(), ((lambda c: c.get('cc') if isinstance(c, dict) else None)(st.session_state['settings'].get('countries')))):
    if _q and _normalize(_q) not in {_normalize(c) for c in _chips}:
        _chips.append(_q)
    if len(_chips) >= 10:
        break
if _chips:
    st.pills(t('quick_search'), options=_chips, selection_mode='single', key='chip_pick',
             on_change=_chip_picked, label_visibility='collapsed')

if st.button(t('replace_link'), key='replace_link_btn', type='tertiary'):
    st.session_state['replace_orig'] = None
    st.session_state['replace_alt'] = None
    st.session_state['nav_from'] = 'app.py'
    st.switch_page('pages/3_Equivalents_Finder.py')

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
                st.session_state['pending_query'] = _decoded
            elif _decoded:
                st.session_state['scan_invalid_code'] = _decoded
            else:
                st.session_state['photo_retry'] = True
            st.rerun()
        elif is_barcode(_result_str):
            st.session_state['show_scanner'] = False
            st.session_state['pending_query'] = _result_str
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

# Decide whether to run a lookup this run
run_query = None
if search_clicked and query.strip():
    run_query = query.strip()
else:
    run_query = st.session_state.pop('pending_query', None)


def _retry_search(code: str):
    st.session_state['pending_query'] = code


def _open_from_history(entry: dict) -> None:
    st.session_state['seen_on'] = {'id': entry.get('id'), 'date': entry.get('date')}
    open_verdict(dict(entry['product']))


if run_query:
    st.session_state.pop('conn_error_code', None)
    st.session_state['last_search_empty'] = False
    cs = settings.get('countries', {})
    cc = cs.get('cc') if isinstance(cs, dict) else None
    is_mexico = cc == 'mx'

    if is_barcode(run_query):
        code = normalize_barcode(run_query)
        st.session_state['search_results'] = []
        st.session_state['last_search_kind'] = 'barcode'
        cached = history.find_recent(code)
        if cached:
            _open_from_history(cached)  # instant: no network
        product, conn_error = None, False
        with st.spinner(t('searching')):
            try:
                product = lookup_barcode(code)
            except OFFConnectionError:
                conn_error = True
        if product:
            open_verdict(product)
        elif conn_error:
            st.session_state['conn_error_code'] = run_query
        else:
            st.session_state['last_search_empty'] = True
            st.session_state['contribute_prefill_barcode'] = code
            st.warning(t('smae_no_barcode') if is_mexico else t('barcode_not_found_off', code=run_query))
    else:
        history.add_search(run_query)
        products, off_failed = [], False
        with st.spinner(t('searching')):
            try:
                products, off_failed = smart_search(run_query, settings, history.get_searches(20))
            except Exception as e:
                st.error(f"{t('error')}: {e}")
        st.session_state['search_results'] = products
        st.session_state['search_off_failed'] = off_failed
        st.session_state['search_q'] = run_query
        st.session_state['last_search_kind'] = 'name'
        if not products:
            st.session_state['last_search_empty'] = True
            st.session_state['contribute_prefill_name'] = run_query
        else:
            match = single_clear_match(products, run_query)
            if match:
                open_verdict(match)  # one clear match: straight to the verdict

# ── Connection error (not the same as "not found") ───────────────────────────
_conn_code = st.session_state.get('conn_error_code')
if _conn_code:
    st.error(t('connection_error'))
    st.button(t('retry_search'), key='retry_search_btn', on_click=_retry_search, args=(_conn_code,))

# ── Results (compact list with traffic lights) ───────────────────────────────
results = st.session_state.get('search_results', [])

if st.session_state.get('search_off_failed'):
    st.warning(t('off_unavailable'))

if st.session_state.get('last_search_empty') and not results and not _conn_code:
    if st.session_state.get('last_search_kind') == 'name':
        st.warning(t('no_results'))
    st.caption('🔍 ' + t('not_found_prompt'))
    st.page_link('pages/6_Contribute.py', label=t('contribute_button'), icon='➕')

if results:
    st.subheader(t('results_count', n=len(results)))
    for idx, product in enumerate(results):
        v = product.get('_verdict') or compute_verdict(product, settings)
        verdict_row(product, v, key=f'res_{idx}')
else:
    # ── Recent + my lists (only when not showing results) ───────────────────
    _recent = history.get_recent(5)
    if _recent:
        st.markdown(f"**{t('recent')}**")
        _cols = st.columns(len(_recent))
        for _i, (_c, _e) in enumerate(zip(_cols, _recent)):
            with _c:
                _lbl = f"{STATUS_EMOJI.get(_e.get('status'), '🟡')} {(_e.get('name') or '?')[:22]}"
                if st.button(_lbl, key=f'recent_{_i}', width='stretch', help=_e.get('name')):
                    _open_from_history(_e)
    _safe, _avoid = history.get_list('safe'), history.get_list('avoid')
    if _safe or _avoid:
        with st.expander(t('my_lists')):
            for _name, _items, _title in (('safe', _safe, t('my_safe')), ('avoid', _avoid, t('my_avoid'))):
                if _items:
                    st.markdown(f"**{_title}**")
                    for _i, _e in enumerate(_items[:20]):
                        if st.button(f"{STATUS_EMOJI.get(_e.get('status'), '🟡')} {_e.get('name') or '?'}"
                                     + (f" — {_e['brand']}" if _e.get('brand') else ''),
                                     key=f'list_{_name}_{_i}', width='stretch'):
                            _open_from_history(_e)

history.flush()
