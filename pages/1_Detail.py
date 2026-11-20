"""
OjasFuel — Product Detail page
"""

import streamlit as st

from src.i18n import t, init_session
from src.theme import inject_theme
from src.api_client import NUTRITION_GROUPS, search_by_barcode, OFFConnectionError
from src.filtering import resolve_diet, allergy_violations
from src.ui_helpers import tn, nutrient_unit, fmt_value, diet_source_label

st.set_page_config(page_title='OjasFuel — Detail', page_icon='🌿', layout='wide')
init_session()
inject_theme()

# ── Back nav ─────────────────────────────────────────────────────────────────
if st.button(t('back')):
    st.switch_page('app.py')

product = st.session_state.get('selected_product')

# Fetch full product data if we only have partial data from search API
if product and product.get('_needs_full_load') and product.get('id'):
    with st.spinner(t('loading_full_product')):
        try:
            full = search_by_barcode(product['id'])
        except OFFConnectionError:
            full = None
            st.warning(t('connection_error_partial'))
        if full:
            # Merge: keep search-result fields, overlay full product fields
            full['_off_tags'] = product.get('_off_tags', {})
            if product.get('_source') and not full.get('_source'):
                full['_source'] = product['_source']
            full['_needs_full_load'] = False
            st.session_state['selected_product'] = full
            st.session_state['portion_product'] = full
            st.session_state['equiv_original'] = full
            product = full

if not product:
    st.warning(t('no_product_selected'))
    st.stop()

is_smae = product.get('_source') == 'smae'

# ── Header ────────────────────────────────────────────────────────────────────
st.title(product.get('name') or t('unknown_product'))

col_meta, col_img = st.columns([3, 1])
with col_meta:
    if product.get('brand'):
        st.markdown(f"**{t('brand')}:** {product['brand']}")
    if product.get('quantity'):
        st.markdown(f"**{t('quantity')}:** {product['quantity']}")
    if product.get('serving_size'):
        st.markdown(f"**{t('serving_size')}:** {product['serving_size']}")
    if product.get('nutriscore'):
        st.markdown(f"**{t('nutriscore')}:** {product['nutriscore']}")
    if product.get('url'):
        st.markdown(f"[{t('open_off')}]({product['url']})")

with col_img:
    img = product.get('image_url', '')
    if img:
        st.image(img, width=160)

st.divider()

# ── Classification ────────────────────────────────────────────────────────────
st.subheader(t('classification'))

settings = st.session_state['settings']
ingredients = '' if is_smae else (product.get('ingredients', '') or '')
diet = resolve_diet(product, settings)
cl = diet.get('classification') or {}
source = diet.get('source', 'none')

allergy_hits = allergy_violations(cl) if cl else []
if allergy_hits:
    st.error('🚨 ' + t('allergy_warning', items=', '.join(allergy_hits)))

if diet.get('is_vegan') is None and diet.get('is_vegetarian') is None:
    st.warning(t('no_ingredients'))
    st.caption('⚠️ ' + t('check_allergies_detail'))
else:
    c1, c2 = st.columns(2)
    with c1:
        if diet.get('is_vegan'):
            st.success(t('vegan_tag'))
        elif diet.get('is_vegetarian'):
            st.info(t('vegetarian_tag'))
        else:
            st.error(t('not_vegetarian_tag'))

        st.caption(diet_source_label(source))
        if cl.get('reason'):
            st.caption(f"{t('reason')}: {cl['reason']}")

    with c2:
        violations = cl.get('violations', [])
        if violations:
            st.error(t('fails_filter'))
            for v in violations:
                st.caption(f"• {v}")
        elif cl:
            st.success(t('passes_filter'))

        if cl.get('animal_products_found'):
            st.caption(f"🐟 {', '.join(cl['animal_products_found'][:5])}")
        if cl.get('dairy_or_eggs_found'):
            st.caption(f"🥚 {', '.join(cl['dairy_or_eggs_found'][:5])}")

st.caption('ℹ️ ' + t('auto_classification_disclaimer'))

st.divider()

# ── Ingredients / SMAE info ───────────────────────────────────────────────────
if is_smae:
    st.subheader(t('smae_info'))
    if product.get('_smae_group'):
        st.markdown(f"**{t('smae_group')}:** {product['_smae_group']}")
    if product.get('_smae_subgroup'):
        st.markdown(f"**{t('smae_subgroup')}:** {product['_smae_subgroup']}")
    if product.get('serving_size'):
        st.markdown(f"**{t('smae_portion')}:** {product['serving_size']}")
    st.caption(t('smae_values_per_100g'))
else:
    st.subheader(t('ingredients'))
    if ingredients:
        st.markdown(f"> {ingredients}")
    else:
        st.caption(t('no_ingredients'))

st.divider()

# ── Nutrition ─────────────────────────────────────────────────────────────────
st.subheader(t('nutrition_facts'))
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
                        t('amount_per_100g'): f"{fmt_value(v)} {nutrient_unit(f)}".strip(),
                    }
                    for f, v in rows
                ],
                hide_index=True,
                width='stretch',
            )

st.divider()

# ── Action buttons ────────────────────────────────────────────────────────────
b1, b2 = st.columns(2)
with b1:
    if st.button(t('calc_portion'), width='stretch', type='primary'):
        st.session_state['portion_product'] = product
        st.session_state['nav_from'] = 'pages/1_Detail.py'
        st.switch_page('pages/2_Portion_Calculator.py')
with b2:
    if st.button(t('find_equivalents'), width='stretch'):
        st.session_state['equiv_original'] = product
        st.session_state['nav_from'] = 'pages/1_Detail.py'
        st.switch_page('pages/3_Equivalents_Finder.py')
