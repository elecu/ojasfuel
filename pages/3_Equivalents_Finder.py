"""
OjasFuel — Equivalents Finder page
"""

import streamlit as st

from src.i18n import t, init_session
from src.theme import inject_theme
from src.api_client import search_by_name as _off_search
from src.smae_client import search_by_name as _smae_search
from src.filtering import classify_results
from src.alternatives import (
    MATCH_MODES as _MATCH_MODES, macro_score as _macro_score,
    passes_threshold as _passes_threshold, equiv_grams_for_macro as _equiv_grams_for_macro,
)
from src.ui_helpers import tn, nutrient_unit, fmt_value, parse_serving_grams


def _search(query: str, page_size: int, is_mexico: bool, cc: str | None, settings: dict) -> list[dict]:
    """Search SMAE first (Mexico) then OFF, dedupe by name, drop products
    that fail the user's diet filter (so meat never shows up)."""
    results = []
    seen_names = set()
    if is_mexico:
        for p in _smae_search(query, page_size=page_size):
            key = p['name'].lower()
            if key not in seen_names:
                seen_names.add(key)
                results.append(p)
    for p in _off_search(query, page_size=page_size, country_code=cc):
        key = p['name'].lower()
        if key not in seen_names:
            seen_names.add(key)
            results.append(p)
    results = classify_results(results, settings)
    return results[:page_size]


def _auto_query(product: dict) -> str:
    """Most specific category (OFF) or SMAE group; fallback first 2 words of name."""
    tags = product.get('categories_tags') or []
    if tags:
        tag = tags[-1]
        tag = tag.split(':', 1)[-1] if ':' in tag else tag
        q = tag.replace('-', ' ').strip()
        if q:
            return q
    if product.get('_smae_group'):
        return str(product['_smae_group'])
    return ' '.join((product.get('name') or '').split()[:2])

st.set_page_config(page_title='OjasFuel — Equivalents', page_icon='🔄', layout='wide')
init_session()
inject_theme()

# ── Page ──────────────────────────────────────────────────────────────────────
if st.button(t('back')):
    st.switch_page('pages/1_Detail.py')

st.title(f"🔄 {t('equivalents')}")

original = st.session_state.get('equiv_original') or st.session_state.get('selected_product')

if not original:
    st.warning(t('no_product_selected'))
    st.stop()

# Reset stale results when the original product changes
_orig_id = original.get('id') or original.get('name')
if st.session_state.get('equiv_orig_id') != _orig_id:
    st.session_state['equiv_orig_id'] = _orig_id
    st.session_state.pop('equiv_alternatives', None)
    st.session_state.pop('equiv_auto_results', None)

orig_nutrition = original.get('nutrition', {})
orig_name = original.get('name') or 'Original'
orig_brand = original.get('brand') or ''

settings = st.session_state['settings']
threshold = settings.get('equivalents_threshold', 0.15)
cs = settings.get('countries', {})
cc = cs.get('cc') if isinstance(cs, dict) else None
is_mexico = cc == 'mx'

# ── Original product summary ──────────────────────────────────────────────────
st.subheader(t('original_product'))
with st.container(border=True):
    st.markdown(f"**{orig_name}**  {f'— {orig_brand}' if orig_brand else ''}")

    key_macros = ['Energy (kcal)', 'Protein (g)', 'Fat (g)', 'Carbohydrates (g)']
    cols = st.columns(len(key_macros))
    for col, k in zip(cols, key_macros):
        if k in orig_nutrition:
            label = tn(k).split(' (')[0]
            col.metric(label, f"{fmt_value(orig_nutrition[k])} {nutrient_unit(k)}")

orig_kcal = orig_nutrition.get('Energy (kcal)', 0)

st.divider()

# ── Match priority — shown at top, applies to both manual and auto-find ───────
st.subheader(t('match_priority'))
mode_keys = list(_MATCH_MODES.keys())
mode_labels = [t(_MATCH_MODES[k][0]) for k in mode_keys]
selected_mode_label = st.radio(
    t('match_priority'),
    options=mode_labels,
    horizontal=True,
    label_visibility='collapsed',
)
selected_mode = mode_keys[mode_labels.index(selected_mode_label)]
_, active_weights = _MATCH_MODES[selected_mode]
active_macro_names = [m for m, _ in active_weights]

st.divider()

# ── Portion to match ──────────────────────────────────────────────────────────
st.subheader(t('qty_to_match'))
orig_grams = st.number_input(
    t('original_qty_g'),
    min_value=1.0,
    max_value=5000.0,
    value=100.0,
    step=10.0,
)

orig_scaled = {k: round(v * orig_grams / 100, 2) for k, v in orig_nutrition.items()}

st.divider()

# ── Alternative product search ────────────────────────────────────────────────
st.subheader(t('alternative_product'))
alt_query = st.text_input(t('search_alternative'), placeholder=orig_name)

if st.button(t('search_button'), key='alt_search') and alt_query.strip():
    with st.spinner(t('searching')):
        try:
            alts = _search(alt_query.strip(), page_size=10, is_mexico=is_mexico, cc=cc, settings=settings)
            st.session_state['equiv_alternatives'] = alts
        except Exception as e:
            st.error(str(e))

alternatives = st.session_state.get('equiv_alternatives', [])

if alternatives:
    alt_names = [
        f"{'🇲🇽 ' if p.get('_source')=='smae' else ''}{p.get('name','?')} — {p.get('brand','')}"
        for p in alternatives
    ]
    chosen_idx = st.selectbox(t('select_alternative'), range(len(alt_names)),
                               format_func=lambda i: alt_names[i])
    alternative = alternatives[chosen_idx]
    alt_nutrition = alternative.get('nutrition', {})
    alt_kcal_100g = alt_nutrition.get('Energy (kcal)', 0)
    alt_name = alternative.get('name') or 'Alternative'
    alt_srv_g, alt_srv_label = parse_serving_grams(alternative)

    st.divider()

    # ── Calculate equivalent quantity using selected match mode ─────────────
    # Compute per-macro equivalents, then weighted average for the chosen mode
    per_macro_equiv = {}
    for macro, _ in active_weights:
        g = _equiv_grams_for_macro(orig_nutrition, alt_nutrition, macro, orig_grams)
        if g is not None:
            per_macro_equiv[macro] = g

    if per_macro_equiv:
        total_w = sum(w for m, w in active_weights if m in per_macro_equiv)
        equiv_grams = round(
            sum(per_macro_equiv[m] * w for m, w in active_weights if m in per_macro_equiv) / total_w, 1
        )

        result_text = f"**{t('you_need', qty=f'{equiv_grams}g', name=alt_name)}**  ≈  {t('equiv_to_match', qty=orig_grams, name=orig_name)}"
        if alt_srv_g and alt_srv_g > 0:
            portions = equiv_grams / alt_srv_g
            result_text += f"  ·  {t('equiv_servings', n=portions, srv=alt_srv_label)}"
        st.success(result_text)

        # Per-macro breakdown (always shown so user sees how each macro matches)
        per_macro_cols = st.columns(len(active_weights))
        for col, (macro, w) in zip(per_macro_cols, active_weights):
            label = tn(macro).split(' (')[0]
            g = per_macro_equiv.get(macro)
            if g is not None:
                srv_note = f" · {per_macro_equiv[macro] / alt_srv_g:.1f}×" if alt_srv_g and alt_srv_g > 0 else ""
                col.metric(f"{t('match_for')} {label}", f"{g}g{srv_note}")
            else:
                col.caption(f"{label}: —")
    else:
        equiv_grams = orig_grams
        st.info(t('no_energy_data'))

    # ── Side-by-side comparison ───────────────────────────────────────────────
    st.subheader(t('comparison'))
    alt_scaled = {k: round(v * equiv_grams / 100, 2) for k, v in alt_nutrition.items()}

    compare_fields = [
        'Energy (kcal)', 'Protein (g)', 'Fat (g)', 'Saturated Fat (g)',
        'Carbohydrates (g)', 'Sugars (g)', 'Fiber (g)', 'Sodium (mg)', 'Salt (g)',
    ]

    header = st.columns([3, 2, 2, 2])
    header[0].markdown(f"**{t('nutrient')}**")
    header[1].markdown(f"**{t('original')}** ({orig_grams}g)")
    header[2].markdown(f"**{t('alternative')}** ({equiv_grams}g)")
    header[3].markdown(f"**{t('difference')}**")

    macro_warnings = []
    for field in compare_fields:
        o_val = orig_scaled.get(field)
        a_val = alt_scaled.get(field)
        if o_val is None and a_val is None:
            continue
        o_val = o_val or 0
        a_val = a_val or 0

        if o_val > 0:
            diff_pct = (a_val - o_val) / o_val * 100
        else:
            diff_pct = 0

        over_threshold = abs(diff_pct) > (threshold * 100)
        if over_threshold and field in ('Protein (g)', 'Fat (g)', 'Carbohydrates (g)', 'Energy (kcal)'):
            macro_warnings.append((field, diff_pct))

        row = st.columns([3, 2, 2, 2])
        row[0].write(tn(field))
        row[1].write(fmt_value(o_val))
        row[2].write(fmt_value(a_val))
        diff_str = f"+{diff_pct:.1f}%" if diff_pct > 0 else f"{diff_pct:.1f}%"
        if over_threshold:
            row[3].markdown(f"⚠️ **{diff_str}**")
        else:
            row[3].write(diff_str)

    if macro_warnings:
        st.warning(f"**{t('macro_mismatches', pct=int(threshold * 100))}**")
        for field, pct in macro_warnings:
            st.caption(t('macro_warning', nutrient=tn(field), pct=abs(pct)))
    else:
        st.success(t('good_match'))

st.divider()

# ── Auto-find 5 equivalents ───────────────────────────────────────────────────
st.subheader(t('find_auto'))
st.caption(t('auto_find_caption', name=orig_name, pct=int(threshold * 100)))
st.caption(f"▸ {t('match_priority')}: **{selected_mode_label}**")

if st.button(t('find_auto'), type='secondary'):
    has_orig_data = any(orig_nutrition.get(m, 0) for m, _ in active_weights)
    if not has_orig_data:
        st.session_state.pop('equiv_auto_results', None)
        st.warning(t('no_macro_data'))
    else:
        with st.spinner(t('searching')):
            try:
                candidates = _search(_auto_query(original), page_size=20,
                                     is_mexico=is_mexico, cc=cc, settings=settings)
            except Exception as e:
                st.error(str(e))
                candidates = []

        scored = []
        for c in candidates:
            if c.get('id') and c.get('id') == original.get('id'):
                continue
            c_nutr = c.get('nutrition', {})
            if not c_nutr.get('Energy (kcal)'):
                continue
            if not _passes_threshold(orig_nutrition, c_nutr, active_weights, threshold):
                continue
            score, diffs = _macro_score(orig_nutrition, c_nutr, active_weights)
            scored.append((score, diffs, c))
        scored.sort(key=lambda x: x[0])
        st.session_state['equiv_auto_results'] = {
            'orig_id': _orig_id,
            'macros': active_macro_names,
            'threshold': threshold,
            'items': scored[:5],
        }

# Rendered outside the button branch so inner buttons survive reruns
_auto = st.session_state.get('equiv_auto_results')
if _auto and _auto.get('orig_id') == _orig_id:
    top5 = _auto['items']
    _pct = int(_auto['threshold'] * 100)
    if top5:
        st.success(t('found_equivalents', n=len(top5), pct=_pct))
        for rank, (score, diffs, c) in enumerate(top5, 1):
            with st.container(border=True):
                c_nutr = c.get('nutrition', {})
                c_srv_g, c_srv_label = parse_serving_grams(c)
                source_badge = " 🇲🇽 SMAE" if c.get('_source') == 'smae' else ""
                st.markdown(f"**#{rank}** {c.get('name','')} — {c.get('brand','')}{source_badge}")

                macro_parts = []
                for macro in _auto['macros']:
                    val = c_nutr.get(macro, 0)
                    d = diffs.get(macro, 0)
                    sign = '+' if d > 0 else ''
                    label = tn(macro).split(' (')[0]
                    macro_parts.append(f"{label}: {fmt_value(val)}{nutrient_unit(macro)} ({sign}{d:.1f}%)")
                st.caption('  ·  '.join(macro_parts))

                c_kcal_100 = c_nutr.get('Energy (kcal)', 0)
                if orig_kcal and c_kcal_100:
                    target_kcal = orig_kcal * orig_grams / 100
                    equiv_g = round(target_kcal / c_kcal_100 * 100, 1)
                    line = f"{orig_grams:g}g → {equiv_g}g"
                    if c_srv_g and c_srv_g > 0:
                        line += f"  ·  {t('equiv_servings', n=equiv_g / c_srv_g, srv=c_srv_label)}"
                    st.caption(line)

                if st.button(t('use_this'), key=f'use_auto_{rank}'):
                    st.session_state['equiv_alternatives'] = [c]
                    st.rerun()
    else:
        st.warning(t('no_equivalents_found', pct=_pct))
