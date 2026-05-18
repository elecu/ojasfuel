"""
OjasFuel — Equivalents Finder page
"""

import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session
from src.theme import inject_theme
from src.api_client import search_by_name
from src.classifier import ProductClassifier

st.set_page_config(page_title='OjasFuel — Equivalents', page_icon='🔄', layout='wide')
init_session()
inject_theme()
classifier = ProductClassifier()

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
threshold = settings.get('equivalents_threshold', 0.10)

# ── Original product summary ──────────────────────────────────────────────────
st.subheader(t('original_product'))
with st.container(border=True):
    st.markdown(f"**{orig_name}**  {f'— {orig_brand}' if orig_brand else ''}")

    key_macros = ['Energy (kcal)', 'Protein (g)', 'Fat (g)', 'Carbohydrates (g)']
    cols = st.columns(len(key_macros))
    for col, k in zip(cols, key_macros):
        if k in orig_nutrition:
            col.metric(k.split(' (')[0], f"{orig_nutrition[k]} {k.split('(')[1].rstrip(')')}")

orig_kcal = orig_nutrition.get('Energy (kcal)', 0)

st.divider()

# ── Portion to match ──────────────────────────────────────────────────────────
st.subheader('Quantity to match')
orig_grams = st.number_input(
    'Original quantity (g)',
    min_value=1.0,
    max_value=5000.0,
    value=100.0,
    step=10.0,
)

# Macro values for the given original quantity
orig_scaled = {k: round(v * orig_grams / 100, 2) for k, v in orig_nutrition.items()}

st.divider()

# ── Alternative product search ────────────────────────────────────────────────
st.subheader(t('alternative_product'))
alt_query = st.text_input(t('search_alternative'), placeholder=orig_name)

if st.button(t('search_button'), key='alt_search') and alt_query.strip():
    with st.spinner(t('searching')):
        try:
            alts = search_by_name(alt_query.strip(), page_size=10)
            st.session_state['equiv_alternatives'] = alts
        except Exception as e:
            st.error(str(e))

alternatives = st.session_state.get('equiv_alternatives', [])

if alternatives:
    alt_names = [
        f"{p.get('name','?')} — {p.get('brand','')}"
        for p in alternatives
    ]
    chosen_idx = st.selectbox('Select alternative', range(len(alt_names)),
                               format_func=lambda i: alt_names[i])
    alternative = alternatives[chosen_idx]
    alt_nutrition = alternative.get('nutrition', {})
    alt_kcal_100g = alt_nutrition.get('Energy (kcal)', 0)
    alt_name = alternative.get('name') or 'Alternative'

    st.divider()

    # ── Calculate equivalent quantity ────────────────────────────────────────
    if orig_kcal and alt_kcal_100g:
        equiv_grams = round((orig_scaled.get('Energy (kcal)', orig_kcal * orig_grams / 100) / alt_kcal_100g) * 100, 1)
        st.success(f"**{t('you_need', qty=f'{equiv_grams}g', name=alt_name)}**  ≈  to match {orig_grams}g of {orig_name}")
    else:
        equiv_grams = orig_grams
        st.info('Cannot calculate equivalent (missing energy data) — showing same weight.')

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
        row[0].write(field)
        row[1].write(f"{o_val}")
        row[2].write(f"{a_val}")
        diff_str = f"+{diff_pct:.1f}%" if diff_pct > 0 else f"{diff_pct:.1f}%"
        if over_threshold:
            row[3].markdown(f"⚠️ **{diff_str}**")
        else:
            row[3].write(diff_str)

    if macro_warnings:
        st.warning(f"**Macro mismatches (>{int(threshold*100)}%):**")
        for field, pct in macro_warnings:
            st.caption(t('macro_warning', nutrient=field, pct=abs(pct)))
    else:
        st.success(t('good_match'))

st.divider()

# ── Auto-find 5 equivalents ───────────────────────────────────────────────────
st.subheader(f"🔍 {t('find_auto').replace('🔍 ', '')}")
st.caption(f"Searches by name '{orig_name}', ranks by calorie match within ±{int(threshold*100)}%")

if st.button(t('find_auto'), type='secondary'):
    with st.spinner('Searching for equivalents...'):
        try:
            candidates = search_by_name(orig_name.split(' ')[0], page_size=20)
        except Exception as e:
            st.error(str(e))
            candidates = []

    if orig_kcal:
        scored = []
        for c in candidates:
            c_kcal = c.get('nutrition', {}).get('Energy (kcal)', 0)
            if not c_kcal:
                continue
            diff = abs(c_kcal - orig_kcal) / orig_kcal
            if diff <= threshold:
                scored.append((diff, c))
        scored.sort(key=lambda x: x[0])
        top5 = scored[:5]

        if top5:
            st.success(f"Found {len(top5)} equivalents within ±{int(threshold*100)}%:")
            for rank, (diff, c) in enumerate(top5, 1):
                with st.container(border=True):
                    st.markdown(f"**#{rank}** {c.get('name','')} — {c.get('brand','')}")
                    c_kcal = c['nutrition'].get('Energy (kcal)', 0)
                    st.caption(f"{c_kcal} kcal/100g  |  diff: {diff*100:.1f}%")
                    if st.button('Use this', key=f'use_auto_{rank}'):
                        st.session_state['equiv_alternatives'] = [c]
                        st.rerun()
        else:
            st.warning(f"No equivalents found within ±{int(threshold*100)}%. Try increasing the threshold in Settings.")
    else:
        st.warning("Original product has no energy data.")
