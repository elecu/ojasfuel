"""Shared UI helpers for OjasFuel pages."""

import html as _html
import re

import streamlit as st

from src.i18n import t
from src.replace import parse_serving_grams  # noqa: F401  (re-exported)

# Nutrient display keys whose i18n key is not simply nutrient_<slug>.
_SPECIAL_KEYS = {
    'Energy (kcal)': 'nutrient_energy_kcal',
    'Energy (kJ)': 'nutrient_energy_kj',
}


def _slug(nutrient_key: str) -> str:
    base = nutrient_key.split(' (')[0].strip().lower()
    return re.sub(r'[^a-z0-9]+', '_', base).strip('_')


def nutrient_i18n_key(nutrient_key: str) -> str:
    return _SPECIAL_KEYS.get(nutrient_key) or f'nutrient_{_slug(nutrient_key)}'


def tn(nutrient_key: str) -> str:
    """Translated nutrient label (with unit); falls back to the English name."""
    key = nutrient_i18n_key(nutrient_key)
    txt = t(key)
    return nutrient_key if txt == key else txt


def tn_short(nutrient_key: str) -> str:
    """Translated label without the trailing unit."""
    return tn(nutrient_key).split(' (')[0]


def nutrient_unit(nutrient_key: str) -> str:
    return nutrient_key.rsplit('(', 1)[-1].rstrip(')') if '(' in nutrient_key else ''


def fmt_value(value) -> str:
    """Round a nutrient value sensibly for display."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if v == 0:
        return '0'
    a = abs(v)
    if a >= 100:
        return f'{v:.0f}'
    if a >= 10:
        return f'{v:.1f}'.rstrip('0').rstrip('.')
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def diet_source_label(source: str) -> str:
    """Human label for where a diet classification came from."""
    if source == 'off':
        return t('diet_source_off')
    if source == 'smae':
        return t('diet_source_smae')
    if source == 'ingredients':
        return t('diet_source_ingredients')
    return t('diet_source_none')


# ── Verdict helpers (shared by home and verdict page) ────────────────────────
STATUS_EMOJI = {'ok': '🟢', 'no': '🔴', 'unknown': '🟡'}
STATUS_CLASS = {'ok': 'ok', 'no': 'no', 'unknown': 'unk'}
STATUS_KEY = {'ok': 'verdict_ok', 'no': 'verdict_no', 'unknown': 'verdict_unknown'}

VERDICT_CSS = """
<style>
.vd-card { border-radius: var(--radius-lg, 16px); padding: 22px 20px; margin: 4px 0 14px;
  border: 2px solid var(--border); background: var(--bg-surface); }
.vd-card.ok  { border-color: var(--success); background: var(--success-bg); }
.vd-card.no  { border-color: var(--error);   background: var(--error-bg); }
.vd-card.unk { border-color: var(--warning); background: var(--warning-bg); }
.vd-head { display: flex; align-items: center; gap: 14px; }
.vd-light { font-size: 3.2rem; line-height: 1; }
.vd-title { font-size: 2rem; font-weight: 800; line-height: 1.1; color: var(--text-primary); }
.vd-card.ok .vd-title  { color: var(--success); }
.vd-card.no .vd-title  { color: var(--error); }
.vd-card.unk .vd-title { color: var(--warning); }
.vd-body { display: flex; gap: 14px; align-items: center; margin-top: 14px; }
.vd-body img { width: 84px; height: 84px; object-fit: contain; border-radius: 10px;
  background: #fff; flex-shrink: 0; }
.vd-name { font-size: 1.15rem; font-weight: 700; color: var(--text-primary); }
.vd-brand { color: var(--text-secondary); font-size: .9rem; }
.vd-reasons { margin-top: 10px; font-size: 1rem; color: var(--text-primary); }
.vd-reasons .allergy { color: var(--error); font-weight: 700; }
.vd-src { margin-top: 8px; font-size: .82rem; color: var(--text-secondary); }
.vd-row { display: flex; align-items: center; gap: 8px; }
.vd-row .vd-dot { font-size: 1.3rem; }
.vd-row .vd-meta { color: var(--text-secondary); font-size: .85rem; }
/* replace flow */
.rp-badge { display: inline-block; border-radius: 999px; padding: 4px 12px; font-weight: 700;
  font-size: .95rem; border: 1.5px solid var(--border); background: var(--bg-surface); }
.rp-badge.very, .rp-badge.similar { border-color: var(--success); background: var(--success-bg); color: var(--success); }
.rp-badge.partial { border-color: var(--warning); background: var(--warning-bg); color: var(--warning); }
.rp-badge.low { border-color: var(--error); background: var(--error-bg); color: var(--error); }
.rp-eat { font-size: 1.6rem; line-height: 1.25; color: var(--text-primary); margin: 4px 0 6px; }
.rp-eat strong { font-weight: 800; }
mark { background: var(--warning-bg); color: var(--warning); border-radius: 4px;
  padding: 0 3px; font-weight: 700; }
@media (max-width: 640px) { .vd-title { font-size: 1.6rem; } .vd-light { font-size: 2.6rem; } }
</style>
"""


def inject_verdict_css() -> None:
    st.markdown(VERDICT_CSS, unsafe_allow_html=True)


def reason_text(reason: dict) -> str:
    key = reason.get('reason_key')
    if key:
        return t(key)
    return reason.get('text', '')


def reasons_line(v: dict, max_n: int = 3, html: bool = False) -> str:
    """One-line summary of the top reasons (allergies are already first)."""
    parts = []
    for r in (v.get('reasons') or [])[:max_n]:
        txt = reason_text(r)
        if not txt:
            continue
        if html:
            esc = _html.escape(txt)
            parts.append(f'<span class="allergy">{esc}</span>' if r.get('kind') == 'allergy' else esc)
        else:
            parts.append(txt)
    return ' · '.join(parts)


def verdict_card_html(product: dict, v: dict) -> str:
    status = v.get('status', 'unknown')
    esc = _html.escape
    img = product.get('image_url') or ''
    img_html = f'<img src="{esc(img, quote=True)}" alt="">' if img.startswith('http') else ''
    brand = product.get('brand') or ''
    reasons = reasons_line(v, html=True)
    src = diet_source_label(v.get('source', 'none'))
    return (
        f'<div class="vd-card {STATUS_CLASS.get(status, "unk")}">'
        f'<div class="vd-head"><span class="vd-light">{STATUS_EMOJI.get(status, "🟡")}</span>'
        f'<span class="vd-title">{esc(t(STATUS_KEY.get(status, "verdict_unknown")))}</span></div>'
        f'<div class="vd-body">{img_html}<div>'
        f'<div class="vd-name">{esc(product.get("name") or t("unknown_product"))}</div>'
        f'<div class="vd-brand">{esc(brand)}</div></div></div>'
        + (f'<div class="vd-reasons">{reasons}</div>' if reasons else '')
        + f'<div class="vd-src">{esc(src)}</div></div>'
    )


def compute_verdict(product: dict, settings: dict) -> dict:
    """verdict() with a defensive fallback so a logic error never blanks the UI."""
    try:
        from src.verdict import verdict
        return verdict(product, settings)
    except Exception:
        return {'status': 'unknown',
                'reasons': [{'kind': 'no_data', 'text': t('no_ingredients')}],
                'source': 'none', 'flagged_terms': [], 'diet': {}}


def open_verdict(product: dict, from_page: str = 'app.py') -> None:
    """Make `product` the current selection and go to the verdict page."""
    st.session_state['selected_product'] = product
    st.session_state['portion_product'] = product
    st.session_state['equiv_original'] = product
    st.session_state['verdict_from'] = from_page
    st.session_state['nav_from'] = 'pages/1_Detail.py'
    st.switch_page('pages/1_Detail.py')


class _NotFound(Exception):
    pass


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_barcode(code: str) -> dict:
    from src import api_client
    p = api_client.search_by_barcode(code)  # OFFConnectionError propagates (not cached)
    if not p:
        raise _NotFound()  # exceptions are never cached, so misses are retried
    return p


def lookup_barcode(code: str) -> dict | None:
    """Cached barcode lookup. None if not found; raises OFFConnectionError on network failure."""
    try:
        return _cached_barcode(code)
    except _NotFound:
        return None


def verdict_row(product: dict, v: dict, key: str, from_page: str = 'app.py') -> None:
    """Compact list row: status light + name/brand + one-line reason + open button."""
    status = v.get('status', 'unknown')
    esc = _html.escape
    with st.container(border=True):
        c1, c2 = st.columns([5, 1.2], vertical_alignment='center')
        with c1:
            sub = ' · '.join(x for x in (product.get('brand') or '', reasons_line(v, 2)) if x)
            st.markdown(
                f'<div class="vd-row"><span class="vd-dot">{STATUS_EMOJI.get(status, "🟡")}</span>'
                f'<div><div class="vd-name" style="font-size:1rem">{esc(product.get("name") or t("unknown_product"))}</div>'
                f'<div class="vd-meta">{esc(sub)}</div></div></div>',
                unsafe_allow_html=True)
        with c2:
            if st.button(t('open_verdict'), key=key, width='stretch'):
                open_verdict(product, from_page)
