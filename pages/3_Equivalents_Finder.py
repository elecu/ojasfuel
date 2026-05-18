"""
OjasFuel — Equivalents Finder page
"""

import re
import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session
from src.theme import inject_theme
from src.api_client import search_by_name as _off_search
from src.smae_client import search_by_name as _smae_search
from src.classifier import ProductClassifier


def _search(query: str, page_size: int, is_mexico: bool) -> list[dict]:
    """Search SMAE first (Mexico) then OFF, deduplicating by name."""
    results = []
    seen_names = set()
    if is_mexico:
        for p in _smae_search(query, page_size=page_size):
            key = p['name'].lower()
            if key not in seen_names:
                seen_names.add(key)
                results.append(p)
    for p in _off_search(query, page_size=page_size):
        key = p['name'].lower()
        if key not in seen_names:
            seen_names.add(key)
            results.append(p)
    return results[:page_size]

st.set_page_config(page_title='OjasFuel — Equivalents', page_icon='🔄', layout='wide')
init_session()
inject_theme()
classifier = ProductClassifier()

# ── Nutrient label translation map ───────────────────────────────────────────
_NUTRIENT_KEYS = {
    'Energy (kcal)':      'nutrient_energy_kcal',
    'Energy (kJ)':        'nutrient_energy_kj',
    'Protein (g)':        'nutrient_protein',
    'Fat (g)':            'nutrient_fat',
    'Saturated Fat (g)':  'nutrient_saturated_fat',
    'Carbohydrates (g)':  'nutrient_carbohydrates',
    'Sugars (g)':         'nutrient_sugars',
    'Fiber (g)':          'nutrient_fiber',
    'Sodium (mg)':        'nutrient_sodium',
    'Salt (g)':           'nutrient_salt',
}

def _tn(nutrient_key: str) -> str:
    return t(_NUTRIENT_KEYS[nutrient_key]) if nutrient_key in _NUTRIENT_KEYS else nutrient_key


# ── Match priority config ─────────────────────────────────────────────────────
_MATCH_MODES = {
    'cal_only':          ('match_cal_only',          [('Energy (kcal)', 1.0)]),
    'cal_protein':       ('match_cal_protein',        [('Energy (kcal)', 0.5), ('Protein (g)', 0.5)]),
    'cal_protein_carbs': ('match_cal_protein_carbs',  [('Energy (kcal)', 0.4), ('Protein (g)', 0.4), ('Carbohydrates (g)', 0.2)]),
    'protein_priority':  ('match_protein_priority',   [('Protein (g)', 0.7), ('Energy (kcal)', 0.3)]),
}


def _macro_score(orig: dict, cand: dict, weights: list[tuple[str, float]]) -> tuple[float, dict]:
    score = 0.0
    diffs = {}
    for macro, w in weights:
        o = orig.get(macro, 0) or 0
        c = cand.get(macro, 0) or 0
        rel = abs(c - o) / max(o, 1)
        score += w * rel
        diffs[macro] = (c - o) / max(o, 1) * 100
    return score, diffs


def _passes_threshold(orig: dict, cand: dict, macros: list[tuple[str, float]], threshold: float) -> bool:
    for macro, _ in macros:
        o = orig.get(macro, 0) or 0
        c = cand.get(macro, 0) or 0
        if o == 0:
            continue
        if abs(c - o) / o > threshold:
            return False
    return True


def parse_serving_grams(product: dict) -> tuple[float | None, str]:
    """
    Try to get serving size in grams from a product dict.
    Returns (grams, display_label) or (None, '').
    Checks: serving_size string, then _raw.serving_quantity numeric field.
    """
    srv_str = product.get('serving_size', '') or ''
    m = re.search(r'\(?\s*(\d+(?:\.\d+)?)\s*g\s*\)?', srv_str, re.IGNORECASE)
    if m:
        return float(m.group(1)), srv_str

    raw = product.get('_raw', {}) or {}
    qty = raw.get('serving_quantity')
    if qty:
        try:
            g = float(qty)
            label = srv_str or f"{g}g"
            return g, label
        except (TypeError, ValueError):
            pass

    return None, ''


def _equiv_grams_for_macro(orig_nutr: dict, alt_nutr: dict, macro: str, orig_grams: float) -> float | None:
    """How many grams of alt product match `orig_grams` of orig for a single macro."""
    orig_val = orig_nutr.get(macro, 0) or 0
    alt_per_100 = alt_nutr.get(macro, 0) or 0
    if not orig_val or not alt_per_100:
        return None
    target = orig_val * orig_grams / 100
    return round(target / alt_per_100 * 100, 1)


# ── Page ──────────────────────────────────────────────────────────────────────
if st.button(t('back')):
    st.switch_page('pages/1_Detail.py')

st.title(f"🔄 {t('equivalents')}")

original = st.session_state.get('equiv_original') or st.session_state.get('selected_product')

if not original:
    st.warning(t('no_product_selected'))
    st.stop()

orig_nutrition = original.get('nutrition', {})
orig_name = original.get('name') or 'Original'
orig_brand = original.get('brand') or ''

settings = st.session_state['settings']
threshold = settings.get('equivalents_threshold', 0.25)
cs = settings.get('countries', {})
is_mexico = (cs.get('cc') if isinstance(cs, dict) else None) == 'mx'

# ── Original product summary ──────────────────────────────────────────────────
st.subheader(t('original_product'))
with st.container(border=True):
    st.markdown(f"**{orig_name}**  {f'— {orig_brand}' if orig_brand else ''}")

    key_macros = ['Energy (kcal)', 'Protein (g)', 'Fat (g)', 'Carbohydrates (g)']
    cols = st.columns(len(key_macros))
    for col, k in zip(cols, key_macros):
        if k in orig_nutrition:
            label = _tn(k).split(' (')[0]
            unit = k.split('(')[1].rstrip(')')
            col.metric(label, f"{orig_nutrition[k]} {unit}")

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
            alts = _search(alt_query.strip(), page_size=10, is_mexico=is_mexico)
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
            label = _tn(macro).split(' (')[0]
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
        row[0].write(_tn(field))
        row[1].write(f"{o_val}")
        row[2].write(f"{a_val}")
        diff_str = f"+{diff_pct:.1f}%" if diff_pct > 0 else f"{diff_pct:.1f}%"
        if over_threshold:
            row[3].markdown(f"⚠️ **{diff_str}**")
        else:
            row[3].write(diff_str)

    if macro_warnings:
        st.warning(f"**{t('macro_mismatches', pct=int(threshold * 100))}**")
        for field, pct in macro_warnings:
            st.caption(t('macro_warning', nutrient=_tn(field), pct=abs(pct)))
    else:
        st.success(t('good_match'))

st.divider()

# ── Auto-find 5 equivalents ───────────────────────────────────────────────────
st.subheader(t('find_auto'))
st.caption(t('auto_find_caption', name=orig_name, pct=int(threshold * 100)))
st.caption(f"▸ {t('match_priority')}: **{selected_mode_label}**")

if st.button(t('find_auto'), type='secondary'):
    with st.spinner(t('searching')):
        try:
            candidates = _search(orig_name.split(' ')[0], page_size=20, is_mexico=is_mexico)
        except Exception as e:
            st.error(str(e))
            candidates = []

    has_orig_data = any(orig_nutrition.get(m, 0) for m, _ in active_weights)
    if has_orig_data:
        scored = []
        for c in candidates:
            c_nutr = c.get('nutrition', {})
            if not c_nutr.get('Energy (kcal)'):
                continue
            if not _passes_threshold(orig_nutrition, c_nutr, active_weights, threshold):
                continue
            score, diffs = _macro_score(orig_nutrition, c_nutr, active_weights)
            scored.append((score, diffs, c))
        scored.sort(key=lambda x: x[0])
        top5 = scored[:5]

        if top5:
            st.success(t('found_equivalents', n=len(top5), pct=int(threshold * 100)))
            for rank, (score, diffs, c) in enumerate(top5, 1):
                with st.container(border=True):
                    c_nutr = c.get('nutrition', {})
                    c_srv_g, c_srv_label = parse_serving_grams(c)
                    source_badge = " 🇲🇽 SMAE" if c.get('_source') == 'smae' else ""
                    st.markdown(f"**#{rank}** {c.get('name','')} — {c.get('brand','')}{source_badge}")

                    macro_parts = []
                    for macro in active_macro_names:
                        val = c_nutr.get(macro, 0)
                        d = diffs.get(macro, 0)
                        sign = '+' if d > 0 else ''
                        unit = macro.split('(')[1].rstrip(')') if '(' in macro else ''
                        label = _tn(macro).split(' (')[0]
                        macro_parts.append(f"{label}: {val}{unit} ({sign}{d:.1f}%)")
                    st.caption('  ·  '.join(macro_parts))

                    c_kcal_100 = c_nutr.get('Energy (kcal)', 0)
                    if orig_kcal and c_kcal_100:
                        equiv_g = round(orig_kcal / c_kcal_100 * 100, 1)
                        if c_srv_g and c_srv_g > 0:
                            portions = equiv_g / c_srv_g
                            st.caption(f"100g equiv → {equiv_g}g  ·  {t('equiv_servings', n=portions, srv=c_srv_label)}")
                        else:
                            st.caption(f"100g equiv → {equiv_g}g")

                    if st.button(t('use_this'), key=f'use_auto_{rank}'):
                        st.session_state['equiv_alternatives'] = [c]
                        st.rerun()
        else:
            st.warning(t('no_equivalents_found', pct=int(threshold * 100)))
    else:
        st.warning(t('no_macro_data'))
