"""
OjasFuel — Portion Calculator page
"""

import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session
from src.theme import inject_theme

st.set_page_config(page_title='OjasFuel — Portions', page_icon='⚖️', layout='wide')
init_session()
inject_theme()

if st.button(t('back')):
    st.switch_page('pages/1_Detail.py')

st.title(f"⚖️ {t('portion_calc')}")

product = st.session_state.get('portion_product') or st.session_state.get('selected_product')

if not product:
    st.warning(t('no_product_selected'))
    st.stop()

name = product.get('name') or 'Unknown'
nutrition = product.get('nutrition', {})

st.markdown(f"**{name}**")
if product.get('brand'):
    st.caption(product['brand'])

st.divider()

# ── Input: how much to eat ────────────────────────────────────────────────────
st.subheader(t('how_much_eating'))

input_method = st.radio(
    'Input method',
    options=['By weight (g)', 'By percentage (%)', 'By portions'],
    horizontal=True,
    label_visibility='collapsed',
)

portion_grams = None

if input_method == 'By weight (g)':
    portion_grams = st.number_input(
        t('enter_weight_g'),
        min_value=1.0,
        max_value=5000.0,
        value=100.0,
        step=5.0,
    )

elif input_method == 'By percentage (%)':
    total_weight = st.number_input(
        t('total_weight_g'),
        min_value=1.0,
        max_value=10000.0,
        value=200.0,
        step=10.0,
    )
    pct = st.slider(t('enter_percentage'), min_value=1, max_value=100, value=50)
    portion_grams = total_weight * pct / 100
    st.caption(t('portion_grams', g=f'{portion_grams:.1f}'))

else:  # By portions
    total_weight = st.number_input(
        t('total_weight_g'),
        min_value=1.0,
        max_value=10000.0,
        value=200.0,
        step=10.0,
    )
    num_portions = st.number_input(t('number_of_portions'), min_value=1, max_value=50, value=4)
    weight_per = total_weight / num_portions
    st.caption(t('weight_per_portion') + f': {weight_per:.1f}g')
    portions_to_eat = st.number_input('Portions to eat', min_value=0.25, max_value=float(num_portions * 4),
                                       value=1.0, step=0.25)
    portion_grams = weight_per * portions_to_eat
    st.caption(t('portion_grams', g=f'{portion_grams:.1f}'))

st.divider()

# ── Output: nutrients for portion ─────────────────────────────────────────────
if portion_grams and portion_grams > 0 and nutrition:
    st.subheader(t('nutrients_for_portion') + f' ({portion_grams:.1f}g)')

    factor = portion_grams / 100.0

    computed = {field: round(val * factor, 2) for field, val in nutrition.items()}

    # Show macros prominently
    macro_keys = ['Energy (kcal)', 'Protein (g)', 'Fat (g)', 'Carbohydrates (g)', 'Sugars (g)', 'Fiber (g)']
    macro_cols = st.columns(len([k for k in macro_keys if k in computed]))
    macro_shown = [k for k in macro_keys if k in computed]
    for col, key in zip(macro_cols, macro_shown):
        with col:
            val = computed[key]
            unit = key.split('(')[1].rstrip(')')
            label = key.split(' (')[0]
            st.metric(label, f"{val} {unit}")

    # Warnings
    warnings = []
    if 'Sodium (mg)' in computed and computed['Sodium (mg)'] > 600:
        warnings.append(t('warning_sodium', v=f"{computed['Sodium (mg)']:.0f}"))
    # OFF stores sodium in grams, convert
    if 'Salt (g)' in computed and computed['Salt (g)'] * 1000 > 600:
        warnings.append(t('warning_sodium', v=f"{computed['Salt (g)']*1000:.0f}"))
    if 'Sugars (g)' in computed and computed['Sugars (g)'] > 15:
        warnings.append(t('warning_sugar', v=f"{computed['Sugars (g)']:.1f}"))
    if 'Protein (g)' in computed and computed['Protein (g)'] < 5:
        warnings.append(t('warning_protein', v=f"{computed['Protein (g)']:.1f}"))

    if warnings:
        for w in warnings:
            st.warning(w)

    # Full table
    with st.expander('All nutrients for this portion'):
        for field, val in computed.items():
            c_name, c_val = st.columns([3, 1])
            c_name.write(field)
            c_val.write(f"**{val}**")

    st.divider()

    # ── Save portion ─────────────────────────────────────────────────────────
    st.subheader(t('save_portion'))
    portion_label = st.text_input('Label for this portion', value=f"{name} – {portion_grams:.0f}g")

    if st.button(t('save_portion'), type='primary'):
        entry = {
            'label': portion_label,
            'product_name': name,
            'grams': portion_grams,
            'nutrients': computed,
        }
        st.session_state['saved_portions'].append(entry)
        st.success(t('portion_saved'))

elif not nutrition:
    st.info('No nutrition data available for this product.')

# ── Saved portions sidebar ────────────────────────────────────────────────────
saved = st.session_state.get('saved_portions', [])
if saved:
    st.divider()
    st.subheader(t('saved_portions'))
    for i, p in enumerate(saved):
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{p['label']}**  — {p['grams']:.0f}g")
            kcal = p['nutrients'].get('Energy (kcal)', '')
            prot = p['nutrients'].get('Protein (g)', '')
            if kcal:
                col1.caption(f"🔥 {kcal} kcal  |  💪 {prot}g protein" if prot else f"🔥 {kcal} kcal")
            if col2.button('🗑', key=f'del_portion_{i}'):
                st.session_state['saved_portions'].pop(i)
                st.rerun()
