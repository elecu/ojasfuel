"""
OjasFuel — Product Detail page
"""

import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session

# Maps OFF nutrient keys to i18n translation keys
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
    """Translate a nutrient key or return it as-is if not mapped."""
    return t(_NUTRIENT_KEYS[nutrient_key]) if nutrient_key in _NUTRIENT_KEYS else nutrient_key
from src.theme import inject_theme
from src.api_client import NUTRITION_GROUPS, search_by_barcode
from src.classifier import ProductClassifier

st.set_page_config(page_title='OjasFuel — Detail', page_icon='🌿', layout='wide')
init_session()
inject_theme()
classifier = ProductClassifier()

# ── Back nav ─────────────────────────────────────────────────────────────────
if st.button(t('back')):
    st.switch_page('app.py')

product = st.session_state.get('selected_product')

# Fetch full product data if we only have partial data from search API
if product and product.get('_needs_full_load') and product.get('id'):
    with st.spinner(t('loading_full_product')):
        full = search_by_barcode(product['id'])
        if full:
            # Merge: keep search-result fields, overlay full product fields
            full['_off_tags'] = product.get('_off_tags', {})
            full['_needs_full_load'] = False
            st.session_state['selected_product'] = full
            st.session_state['portion_product'] = full
            st.session_state['equiv_original'] = full
            product = full

if not product:
    st.warning(t('no_product_selected'))
    st.stop()

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
ingredients = product.get('ingredients', '')
cl = classifier.classify(ingredients, settings)

if cl.get('is_vegan') is None:
    st.warning(t('no_ingredients'))
else:
    c1, c2 = st.columns(2)
    with c1:
        if cl['is_vegan']:
            st.success(t('vegan_tag'))
        elif cl['is_vegetarian']:
            st.info(t('vegetarian_tag'))
        else:
            st.error(t('not_vegetarian_tag'))

        conf = cl.get('confidence', 0)
        st.caption(f"{t('confidence')}: {conf*100:.0f}%")
        st.caption(f"{t('reason')}: {cl.get('reason','')}")

    with c2:
        violations = cl.get('violations', [])
        if violations:
            st.error(t('fails_filter'))
            for v in violations:
                st.caption(f"• {v}")
        else:
            st.success(t('passes_filter'))

        if cl.get('animal_products_found'):
            st.caption(f"🐟 {', '.join(cl['animal_products_found'][:5])}")
        if cl.get('dairy_or_eggs_found'):
            st.caption(f"🥚 {', '.join(cl['dairy_or_eggs_found'][:5])}")

st.divider()

# ── Ingredients ───────────────────────────────────────────────────────────────
st.subheader(t('ingredients'))
if ingredients:
    st.markdown(f"> {ingredients}")
else:
    st.caption(t('no_ingredients'))

st.divider()

# ── Nutrition ─────────────────────────────────────────────────────────────────
st.subheader(t('nutrition_facts'))

nutrition = product.get('nutrition', {})
if not nutrition:
    st.caption(t('no_nutrition_data'))
else:
    group_labels = {
        'Macronutrients': t('macronutrients'),
        'Minerals': t('minerals'),
        'Vitamins': t('vitamins'),
        'Other': t('other_nutrients'),
    }

    tabs = st.tabs([group_labels[g] for g in NUTRITION_GROUPS])
    for tab, (group_name, fields) in zip(tabs, NUTRITION_GROUPS.items()):
        with tab:
            rows = [(f, nutrition[f]) for f in fields if f in nutrition]
            if rows:
                for field, value in rows:
                    col_name, col_val = st.columns([3, 1])
                    col_name.markdown(_tn(field))
                    col_val.markdown(f"**{value}**")
            else:
                st.caption(t('no_group_data'))

st.divider()

# ── Action buttons ────────────────────────────────────────────────────────────
b1, b2 = st.columns(2)
with b1:
    if st.button(t('calc_portion'), use_container_width=True, type='primary'):
        st.session_state['portion_product'] = product
        st.switch_page('pages/2_Portion_Calculator.py')
with b2:
    if st.button(t('find_equivalents'), use_container_width=True):
        st.session_state['equiv_original'] = product
        st.switch_page('pages/3_Equivalents_Finder.py')
