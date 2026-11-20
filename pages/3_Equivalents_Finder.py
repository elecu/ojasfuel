"""
OjasFuel — Replace a food: "I should eat X but I have Y".
"""

import html as _html
import json
import re

import streamlit as st

from src.i18n import t, init_session, get_lang
from src.theme import inject_theme
from src.ui_helpers import (inject_verdict_css, compute_verdict, open_verdict, tn_short,
                            fmt_value, parse_serving_grams)
from src.replace import MATCH_BASES, equivalent, rank_by_similarity, main_differences
from src.search_smart import smart_search, single_clear_match, common_foods

st.set_page_config(page_title='OjasFuel — Replace', page_icon='🔁', layout='wide')
init_session()
inject_theme()
inject_verdict_css()

settings = st.session_state['settings']
LEVEL_DOT = {'very': '🟢', 'similar': '🟢', 'partial': '🟡', 'low': '🔴'}
SHOW_STEP = 3


def _wk(name: str) -> str:
    """Widget key scoped to the UI language (avoids translated-label state bugs)."""
    return f'rp_{name}_{get_lang()}'


_MACRO_NK = {'protein': 'Protein (g)', 'carbs': 'Carbohydrates (g)', 'fat': 'Fat (g)'}


def _bold(text: str) -> str:
    """HTML-escape and turn **x** into <strong>x</strong>."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', _html.escape(text))


def _signed(d: float, nd: int) -> str:
    return f'{d:+.{nd}f}'.replace('-', '−')


def _pid(p: dict) -> str:
    return str(p.get('id') or p.get('name') or '')


def _settings_sig() -> str:
    skip = {'theme', 'lang', 'onboarded', 'equivalents_threshold'}
    return json.dumps({k: v for k, v in settings.items() if k not in skip},
                      sort_keys=True, default=str)


def _set_orig(p: dict | None) -> None:
    st.session_state['replace_orig'] = p
    st.session_state['replace_alt'] = None
    st.session_state.pop('rp_res_orig', None)
    st.session_state.pop('rp_res_alt', None)


def _run_search(kind: str, query: str) -> None:
    query = (query or '').strip()
    if not query:
        return
    try:
        prods, failed = smart_search(query, settings, None)
    except Exception:
        prods, failed = [], True
    one = single_clear_match(prods, query) if prods else None
    if one is not None:
        if kind == 'orig':
            _set_orig(one)
        else:
            st.session_state['replace_alt'] = one
            st.session_state.pop('rp_res_alt', None)
        st.rerun()
    st.session_state[f'rp_res_{kind}'] = {'q': query, 'items': prods[:8], 'failed': failed}


def _chip_picked() -> None:
    v = st.session_state.get(_wk('chip'))
    if v:
        st.session_state['rp_chip_q'] = v
    st.session_state[_wk('chip')] = None


# ── Header ───────────────────────────────────────────────────────────────────
if st.button(t('back'), key='rp_back'):
    st.switch_page(st.session_state.get('nav_from') or 'app.py')

st.title(f"🔁 {t('replace_title')}")

if 'replace_orig' not in st.session_state:
    st.session_state['replace_orig'] = (st.session_state.get('equiv_original')
                                        or st.session_state.get('selected_product'))
orig = st.session_state.get('replace_orig')

# ── Step 1: what you should eat ──────────────────────────────────────────────
with st.container(border=True):
    st.subheader(t('replace_step1'))
    if not orig:
        with st.form(_wk('orig_form'), border=False):
            q = st.text_input(t('replace_search_orig'), placeholder=t('replace_search_orig_ph'),
                              key=_wk('orig_q'))
            submitted = st.form_submit_button(t('search_button'))
        chips = common_foods(get_lang())[:10]
        if chips:
            st.pills(t('quick_search'), options=chips, selection_mode='single', key=_wk('chip'),
                     on_change=_chip_picked, label_visibility='collapsed')
        if st.session_state.get('rp_chip_q'):
            _run_search('orig', st.session_state.pop('rp_chip_q'))
        elif submitted:
            _run_search('orig', q)
        res = st.session_state.get('rp_res_orig')
        if res:
            if res['items']:
                st.caption(t('replace_pick_one'))
                for i, p in enumerate(res['items']):
                    label = p.get('name') or t('unknown_product')
                    if p.get('brand'):
                        label += f" — {p['brand']}"
                    if st.button(label, key=f'rp_orig_pick_{i}', width='stretch'):
                        _set_orig(p)
                        st.rerun()
            else:
                st.caption(t('no_results'))
        st.stop()

    c1, c2 = st.columns([5, 1.5], vertical_alignment='center')
    with c1:
        st.markdown(f"**{orig.get('name') or t('unknown_product')}**"
                    + (f" — {orig['brand']}" if orig.get('brand') else ''))
    with c2:
        if st.button(t('replace_change'), key='rp_change_orig', width='stretch'):
            _set_orig(None)
            st.rerun()

    oid = _pid(orig)
    srv_g, srv_label = parse_serving_grams(orig)
    if st.session_state.get('rp_qty_oid') != oid:
        st.session_state['rp_qty_oid'] = oid
        st.session_state['replace_grams'] = 100.0
    grams = float(st.session_state.get('replace_grams') or 100.0)
    unit = 'g'
    if srv_g and srv_g > 0:
        unit = st.segmented_control(
            t('replace_qty'), options=['g', 'por'], default='g', selection_mode='single',
            format_func={'g': t('replace_unit_g'), 'por': t('replace_unit_portions')}.get,
            key=_wk('unit'), label_visibility='collapsed') or 'g'
    if unit == 'por' and srv_g:
        n = st.number_input(t('replace_unit_portions'), min_value=0.1, max_value=200.0,
                            value=round(max(grams / srv_g, 0.1), 1), step=0.5,
                            key=_wk(f'qty_por_{oid}'))
        if round(float(n), 1) != round(grams / srv_g, 1):
            grams = float(n) * srv_g
    else:
        grams = float(st.number_input(t('replace_qty') + ' (g)', min_value=1.0, max_value=5000.0,
                                      value=min(max(grams, 1.0), 5000.0), step=10.0,
                                      key=_wk(f'qty_g_{oid}')))
    st.session_state['replace_grams'] = grams
    if srv_g and srv_g > 0:
        st.caption(t('replace_conv', g=fmt_value(grams), n=f'{grams / srv_g:.1f}', label=srv_label))

# ── Step 2: match by ─────────────────────────────────────────────────────────
_bkey = _wk('basis')


def _basis_changed() -> None:
    v = st.session_state.get(_bkey)
    if v in MATCH_BASES:
        st.session_state['replace_basis'] = v
    elif st.session_state.get('replace_basis') in MATCH_BASES:
        st.session_state[_bkey] = st.session_state['replace_basis']  # a choice can't be un-picked


_BASIS_LABELS = {b: t(f'replace_basis_{b}') for b in MATCH_BASES}
with st.container(border=True):
    st.subheader(t('replace_step2'))
    st.pills(t('replace_step2'), options=list(MATCH_BASES), selection_mode='single',
             default=st.session_state.get('replace_basis') if st.session_state.get('replace_basis') in MATCH_BASES else None,
             format_func=_BASIS_LABELS.get, key=_bkey,
             on_change=_basis_changed, label_visibility='collapsed')
basis = st.session_state.get('replace_basis')  # set by the pills callback (authoritative)
if basis not in MATCH_BASES:
    st.info(t('replace_pick_basis'))
    st.stop()

# reset the "show more" counter when the problem changes
_sig = f'{oid}|{basis}'
if st.session_state.get('rp_sig') != _sig:
    st.session_state['rp_sig'] = _sig
    st.session_state['rp_show_n'] = SHOW_STEP

alt = st.session_state.get('replace_alt')
eq = equivalent(orig, alt, grams, basis) if alt else None

# ── Step 3: what you have ────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader(t('replace_step3'))

    if alt and eq:
        # Result card
        esc = _html.escape
        st.markdown('<div class="rp-eat">' + _bold(t('replace_eat', g=fmt_value(eq['alt_grams']),
                    name=alt.get('name') or '')) + '</div>', unsafe_allow_html=True)
        if eq['alt_portions']:
            st.markdown('**' + t('replace_portions_line', n=eq['alt_portions'],
                                 label=eq['portion_label']) + '**')
        st.markdown(f'<span class="rp-badge {eq["level"]}">'
                    f'{_html.escape(t("replace_similar_pct", pct=eq["similarity"]))} · '
                    f'{_html.escape(t("replace_level_" + eq["level"]))}</span>', unsafe_allow_html=True)
        diffs = main_differences(eq)
        if diffs:
            parts = ' · '.join(f"{_signed(d, 0)} g {tn_short(_MACRO_NK[m]).lower()}" for m, d in diffs)
            st.caption(t('replace_diff_line', parts=parts))
        else:
            st.caption(t('replace_same_comp'))

        rows = []
        for key, nk in (('kcal', 'Energy (kcal)'), ('protein', 'Protein (g)'),
                        ('carbs', 'Carbohydrates (g)'), ('fat', 'Fat (g)')):
            o_v, a_v = eq['orig_totals'][key], eq['alt_totals'][key]
            d = eq['diffs'].get(key)
            rows.append({
                t('nutrient'): tn_short(nk),
                t('replace_orig_label', g=fmt_value(grams)): '—' if o_v is None else fmt_value(o_v),
                t('replace_alt_label', g=fmt_value(eq['alt_grams'])): '—' if a_v is None else fmt_value(a_v),
                t('difference'): '—' if d is None else _signed(d, 1),
            })
        st.dataframe(rows, hide_index=True, width='stretch')

        av = alt.get('_verdict') or compute_verdict(alt, settings)
        if av.get('status') == 'no':
            st.error('🚫 ' + t('replace_not_suitable'))
        elif av.get('status') == 'unknown':
            st.warning('⚠️ ' + t('replace_diet_unknown'))

        b1, b2 = st.columns(2)
        with b1:
            if st.button(t('replace_change_alt'), key='rp_change_alt', width='stretch'):
                st.session_state['replace_alt'] = None
                st.rerun()
        with b2:
            if st.button(t('replace_see_verdict'), key='rp_see_verdict', type='primary', width='stretch'):
                open_verdict(alt, 'pages/3_Equivalents_Finder.py')
    else:
        if alt and not eq:
            st.info(t('replace_no_match'))

        # (a) free search
        with st.form(_wk('alt_form'), border=False):
            aq = st.text_input(t('replace_have'), placeholder=t('replace_have_ph'), key=_wk('alt_q'))
            a_sub = st.form_submit_button(t('search_button'))
        if a_sub:
            _run_search('alt', aq)
        res = st.session_state.get('rp_res_alt')
        if res:
            if res['items']:
                st.caption(t('replace_pick_one'))
                for i, p in enumerate(res['items']):
                    e = equivalent(orig, p, grams, basis)
                    g_txt = f"≈ {fmt_value(e['alt_grams'])} g" if e else '—'
                    label = f"{p.get('name') or t('unknown_product')} · {g_txt}"
                    if st.button(label, key=f'rp_alt_pick_{i}', width='stretch'):
                        st.session_state['replace_alt'] = p
                        st.session_state.pop('rp_res_alt', None)
                        st.rerun()
            else:
                st.caption(t('no_results'))

        # (b) suggestions
        st.markdown(f"**{t('replace_suggestions')}**")
        cache = st.session_state.setdefault('_rp_alts', {})
        ck = f'{oid}|{_settings_sig()}'
        alts, incomplete = cache.get(ck, (None, False))
        if alts is None:
            with st.spinner(t('finding_alternatives')):
                try:
                    from src.alternatives import find_alternatives_ex
                    alts, incomplete = find_alternatives_ex(orig, settings, n=12)
                except Exception:
                    alts, incomplete = [], True
            if not incomplete:
                cache[ck] = (alts, False)
        ranked = rank_by_similarity(orig, alts, grams, basis)
        if not ranked and incomplete:
            st.caption('⚠️ ' + t('alternatives_load_failed'))
            st.button(t('retry_search'), key='rp_retry')
        elif not ranked:
            st.caption(t('replace_no_suggestions'))
        shown = int(st.session_state.get('rp_show_n', SHOW_STEP))
        for i, (c, e) in enumerate(ranked[:shown]):
            with st.container(border=True):
                r1, r2 = st.columns([5, 1.3], vertical_alignment='center')
                with r1:
                    esc = _html.escape
                    line = f"<strong>{fmt_value(e['alt_grams'])} g</strong>"
                    if e['alt_portions']:
                        line += f" ({esc(t('replace_portions_line', n=e['alt_portions'], label=e['portion_label']))})"
                    st.markdown(
                        f'<div class="vd-row"><span class="vd-dot">{LEVEL_DOT[e["level"]]}</span><div>'
                        f'<div class="vd-name" style="font-size:1rem">{esc(c.get("name") or "")}</div>'
                        f'<div class="vd-meta">{esc(c.get("brand") or "")}</div>'
                        f'<div>{line} · <span class="rp-badge {e["level"]}" style="padding:1px 8px;font-size:.8rem">'
                        f'{esc(t("replace_similar_pct", pct=e["similarity"]))}</span></div>'
                        f'</div></div>', unsafe_allow_html=True)
                with r2:
                    if st.button(t('replace_choose'), key=f'rp_pick_{i}', width='stretch'):
                        st.session_state['replace_alt'] = c
                        st.rerun()
        if len(ranked) > shown:
            if st.button(t('replace_show_more'), key='rp_more'):
                st.session_state['rp_show_n'] = shown + SHOW_STEP
                st.rerun()
