"""
OjasFuel — Contribute: submit a missing product to Open Food Facts anonymously.
"""

import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session
from src.theme import inject_theme
from src.api_client import submit_product

st.set_page_config(
    page_title='OjasFuel — Contribute',
    page_icon='🌿',
    layout='wide',
    initial_sidebar_state='collapsed',
)

init_session()
inject_theme()

if st.button(t('back')):
    st.switch_page('app.py')

st.title(t('contribute_title'))
st.caption(t('contribute_subtitle'))
st.info(t('contribute_note'))

st.divider()

# Pre-fill from search context if available
prefill_barcode = st.session_state.pop('contribute_prefill_barcode', '')
prefill_name = st.session_state.pop('contribute_prefill_name', '')

with st.form('contribute_form'):
    barcode = st.text_input(
        t('contribute_barcode'),
        value=prefill_barcode,
        help=t('contribute_barcode_help'),
        placeholder='e.g. 7501234567890',
    )
    name = st.text_input(
        t('contribute_name'),
        value=prefill_name,
        placeholder='e.g. Oat Milk Chocolate',
    )
    brand = st.text_input(t('contribute_brand'), placeholder='e.g. Alpro')
    quantity = st.text_input(t('contribute_quantity'), placeholder='e.g. 500ml')
    ingredients = st.text_area(
        t('contribute_ingredients'),
        placeholder='e.g. Oat base (water, oats 10%), cocoa 2%, salt...',
        height=120,
    )

    st.divider()
    submitted = st.form_submit_button(t('contribute_submit'), type='primary')

if submitted:
    if not barcode.strip() or not name.strip():
        st.error(t('contribute_required'))
    else:
        with st.spinner(t('contribute_submitting')):
            result = submit_product(
                barcode=barcode,
                name=name,
                brand=brand,
                quantity=quantity,
                ingredients=ingredients,
            )
        if result['ok']:
            st.success(t('contribute_success'))
            st.balloons()
        else:
            st.error(t('contribute_failed', err=result['error']))
