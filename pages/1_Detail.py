"""
OjasFuel — Verdict page (traffic-light answer + alternatives + quick questions)
"""

import html as _html
import json
import re

import streamlit as st

from src.i18n import t, init_session, get_lang
from src.theme import inject_theme
from src.api_client import NUTRITION_GROUPS, OFFConnectionError
from src import history, smae_client
from src.ui_helpers import (
    tn, nutrient_unit, fmt_value, parse_serving_grams, inject_verdict_css,
    compute_verdict, verdict_card_html, lookup_barcode, open_verdict, reason_text,
    verdict_row,
)

st.set_page_config(page_title='OjasFuel — Verdict', page_icon='🌿', layout='wide')
init_session()
inject_theme()
inject_verdict_css()
history.load_history()

settings = st.session_state['settings']

# ── Back nav ─────────────────────────────────────────────────────────────────
if st.button(t('back'), key='back_btn'):
    st.switch_page('app.py')

product = st.session_state.get('selected_product')

# Fetch full product data if we only have partial data from search API
if product and product.get('_needs_full_load') and product.get('id'):
    with st.spinner(t('loading_full_product')):
        try:
            full = lookup_barcode(product['id'])
        except OFFConnectionError:
            full = None
            st.warning(t('connection_error_partial'))
        if full:
            # Merge: keep search-result fields, overlay full product fields
            full['_off_tags'] = product.get('_off_tags', {}) or full.get('_off_tags', {})
            if product.get('_source') and not full.get('_source'):
                full['_source'] = product['_source']
            full['_needs_full_load'] = False
            st.session_state['selected_product'] = full
            st.session_state['portion_product'] = full
            st.session_state['equiv_original'] = full
            product = full

if not product:
    st.warning(t('no_product_selected'))
    if st.button(t('go_home'), key='home_btn'):
        st.switch_page('app.py')
    st.stop()

is_smae = product.get('_source') == 'smae'
pid = str(product.get('id', ''))
v = compute_verdict(product, settings)
status = v.get('status', 'unknown')

history.add_viewed(product, status)

# ── Verdict card ─────────────────────────────────────────────────────────────
st.markdown(verdict_card_html(product, v), unsafe_allow_html=True)
st.caption('ℹ️ ' + t('auto_classification_disclaimer'))

_seen = st.session_state.get('seen_on')
if _seen and _seen.get('id') == pid:
    c_seen, c_ref = st.columns([3, 1], vertical_alignment='center')
    with c_seen:
        st.caption('🕘 ' + t('seen_on', date=_seen.get('date') or ''))
    with c_ref:
        if not is_smae and st.button(t('refresh'), key='refresh_btn', width='stretch'):
            from src import api_client
            try:
                fresh = api_client.search_by_barcode(pid)
            except OFFConnectionError:
                fresh = None
                st.warning(t('connection_error_partial'))
            if fresh:
                st.session_state.pop('seen_on', None)
                st.session_state['selected_product'] = fresh
                st.session_state['portion_product'] = fresh
                st.session_state['equiv_original'] = fresh
                st.rerun()


# ── Helpers ──────────────────────────────────────────────────────────────────
def _highlight(text: str, terms: list[str]) -> str:
    """HTML-escape `text` and wrap flagged terms in <mark>."""
    esc = _html.escape(text)
    pats = sorted({_html.escape(x) for x in terms if x and len(x.strip()) >= 3},
                  key=len, reverse=True)
    if not pats:
        return esc
    rx = re.compile('|'.join(re.escape(p) for p in pats), re.IGNORECASE)
    return rx.sub(lambda m: f'<mark>{m.group(0)}</mark>', esc)


def _settings_sig() -> str:
    skip = {'theme', 'lang', 'onboarded', 'equivalents_threshold'}
    return json.dumps({k: val for k, val in settings.items() if k not in skip},
                      sort_keys=True, default=str)


def _qq_pick() -> None:
    val = st.session_state.get('qq_pick')
    st.session_state['qq_pick'] = None
    if not val:
        return
    cur = st.session_state.get('qq_active')
    pid_now = str((st.session_state.get('selected_product') or {}).get('id', ''))
    st.session_state['qq_active'] = None if cur == (pid_now, val) else (pid_now, val)


def _toggle(list_name: str) -> None:
    history.toggle_list(st.session_state['selected_product'], list_name,
                        st.session_state.get('_cur_status'))


st.session_state['_cur_status'] = status

# ── Alternatives (when not suitable / unclear, or on request) ────────────────
active = st.session_state.get('qq_active')
active = active[1] if active and active[0] == pid else None

if status in ('no', 'unknown') or active == 'similar':
    st.subheader(t('alternatives_title'))
    cache = st.session_state.setdefault('_alts_cache', {})
    ck = f'{pid}|{_settings_sig()}'
    alts, incomplete = cache.get(ck, (None, False))
    if alts is None:
        with st.spinner(t('finding_alternatives')):
            try:
                from src.alternatives import find_alternatives_ex
                alts, incomplete = find_alternatives_ex(product, settings, n=3)
            except Exception:
                alts, incomplete = [], True
        if not incomplete:  # never remember a network failure for the session
            cache[ck] = (alts, False)
    if not alts and incomplete:
        st.caption('⚠️ ' + t('alternatives_load_failed'))
        st.button(t('retry_search'), key='alts_retry')  # rerun = new attempt
    elif not alts:
        st.caption(t('no_alternatives'))
    for i, alt in enumerate(alts):
        av = alt.get('_verdict') or compute_verdict(alt, settings)
        verdict_row(alt, av, key=f'alt_{i}')

# ── Quick questions (deterministic, no AI) ───────────────────────────────────
cs = settings.get('countries', {})
_is_mx = isinstance(cs, dict) and cs.get('cc') == 'mx'
_qq_opts = ['why', 'portion', 'similar', 'cal'] + (['smae'] if _is_mx else [])
_qq_labels = {
    'why': '❓ ' + t('qq_why'), 'portion': '⚖️ ' + t('qq_portion'),
    'similar': '🔁 ' + t('qq_similar'), 'cal': '🔥 ' + t('qq_calories'),
    'smae': '🇲🇽 ' + t('qq_smae'),
}
st.markdown(f"**{t('quick_questions')}**")
st.pills(t('quick_questions'), options=_qq_opts, selection_mode='single',
         format_func=lambda k: _qq_labels[k], key='qq_pick', on_change=_qq_pick,
         label_visibility='collapsed')

if active == 'portion':
    st.session_state['qq_active'] = None
    st.session_state['portion_product'] = product
    st.session_state['nav_from'] = 'pages/1_Detail.py'
    st.switch_page('pages/2_Portion_Calculator.py')

ingredients = '' if is_smae else (product.get('ingredients', '') or '')
flagged = v.get('flagged_terms') or []

if active == 'why':
    with st.container(border=True):
        st.markdown(f"**{t('qq_why')}**")
        reasons = v.get('reasons') or []
        if reasons:
            for r in reasons:
                txt = _html.escape(reason_text(r))
                icon = '🚨' if r.get('kind') == 'allergy' else '•'
                st.markdown(f"{icon} {txt}", unsafe_allow_html=True)
        else:
            st.caption(t('why_no_issues'))
        if ingredients:
            st.markdown(f"**{t('ingredients')}**")
            st.markdown(f'<div>{_highlight(ingredients, flagged)}</div>', unsafe_allow_html=True)

elif active == 'cal':
    with st.container(border=True):
        nutr = product.get('nutrition', {}) or {}
        kcal = nutr.get('Energy (kcal)')
        grams, label = parse_serving_grams(product)
        if kcal is None:
            st.caption(t('no_nutrition_data'))
        elif grams:
            st.metric(t('calories_per_serving', serving=label or f'{fmt_value(grams)} g'),
                      f"{fmt_value(kcal * grams / 100)} kcal")
            st.caption(f"{fmt_value(kcal)} kcal {t('per_100g').lower()}")
        else:
            st.metric(t('per_100g'), f"{fmt_value(kcal)} kcal")
            st.caption(t('no_serving_info'))

elif active == 'smae':
    with st.container(border=True):
        entry, exact = None, is_smae
        if is_smae:
            entry = product
        else:
            try:
                found = smae_client.search_by_name(product.get('name') or '', page_size=1)
            except Exception:
                found = []
            entry = found[0] if found else None
        if not entry:
            st.caption(t('smae_not_found'))
        else:
            if not exact:
                st.caption(t('smae_closest', name=entry.get('name', '')))
            if entry.get('_smae_group'):
                st.markdown(f"**{t('smae_group')}:** {entry['_smae_group']}")
            if entry.get('_smae_subgroup'):
                st.markdown(f"**{t('smae_subgroup')}:** {entry['_smae_subgroup']}")
            if entry.get('serving_size'):
                st.markdown(f"**{t('smae_portion')}:** {entry['serving_size']}")

# ── Details / nutrition (collapsed) ──────────────────────────────────────────
with st.expander(t('product_details')):
    if product.get('quantity'):
        st.markdown(f"**{t('quantity')}:** {product['quantity']}")
    if product.get('serving_size'):
        st.markdown(f"**{t('serving_size')}:** {product['serving_size']}")
    if product.get('nutriscore'):
        st.markdown(f"**{t('nutriscore')}:** {product['nutriscore']}")
    if is_smae:
        st.markdown(f"**{t('smae_info')}**")
        if product.get('_smae_group'):
            st.markdown(f"**{t('smae_group')}:** {product['_smae_group']}")
        if product.get('_smae_subgroup'):
            st.markdown(f"**{t('smae_subgroup')}:** {product['_smae_subgroup']}")
        st.caption(t('smae_values_per_100g'))
    else:
        st.markdown(f"**{t('ingredients')}**")
        if ingredients:
            st.markdown(f'<div>{_highlight(ingredients, flagged)}</div>', unsafe_allow_html=True)
        else:
            st.caption(t('no_ingredients'))
    if product.get('url'):
        st.markdown(f"[{t('open_off')}]({product['url']})")
    if st.button(t('find_equivalents'), key='equiv_btn'):
        st.session_state['equiv_original'] = product
        st.session_state['nav_from'] = 'pages/1_Detail.py'
        st.switch_page('pages/3_Equivalents_Finder.py')

with st.expander(t('nutrition_facts')):
    st.caption(t('per_100g'))
    nutrition = product.get('nutrition', {}) or {}
    group_labels = {
        'Macronutrients': t('macronutrients'),
        'Minerals': t('minerals'),
        'Vitamins': t('vitamins'),
        'Other': t('other_nutrients'),
    }
    group_rows = {}
    for g, fields in NUTRITION_GROUPS.items():
        rows = [(f, nutrition[f]) for f in fields if nutrition.get(f) is not None]
        if rows:
            group_rows[g] = rows
    if not group_rows:
        st.caption(t('no_nutrition_data'))
    else:
        tabs = st.tabs([group_labels[g] for g in group_rows])
        for tab, (group_name, rows) in zip(tabs, group_rows.items()):
            with tab:
                st.dataframe(
                    [
                        {
                            t('nutrient'): tn(f).split(' (')[0],
                            t('amount_per_100g'): f"{fmt_value(val)} {nutrient_unit(f)}".strip(),
                        }
                        for f, val in rows
                    ],
                    hide_index=True,
                    width='stretch',
                )

# ── Actions ──────────────────────────────────────────────────────────────────
a1, a2, a3, a4 = st.columns(4)
with a1:
    _saved = history.in_list(product, 'safe')
    st.button(('✅ ' + t('saved_safe')) if _saved else ('⭐ ' + t('save_safe')),
              key='safe_btn', on_click=_toggle, args=('safe',), width='stretch')
with a2:
    _avoid = history.in_list(product, 'avoid')
    st.button(('🚫 ' + t('avoiding')) if _avoid else ('🚫 ' + t('avoid')),
              key='avoid_btn', on_click=_toggle, args=('avoid',), width='stretch')
with a3:
    if st.button('📸 ' + t('scan_another'), key='scan_another_btn', type='primary', width='stretch'):
        st.session_state['show_scanner'] = True
        st.session_state['scanner_key'] = st.session_state.get('scanner_key', 0) + 1
        st.switch_page('app.py')
with a4:
    if product.get('url'):
        st.link_button('🚩 ' + t('report_error'), product['url'], width='stretch')
    else:
        if st.button('🚩 ' + t('report_error'), key='report_btn', width='stretch'):
            st.session_state['contribute_prefill_name'] = product.get('name', '')
            st.switch_page('pages/6_Contribute.py')

history.flush()
