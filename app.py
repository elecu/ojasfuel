"""
OjasFuel — Home / Search page
"""

import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session, get_lang
from src.theme import inject_theme
from src.api_client import search_by_name, search_by_barcode
from src.classifier import ProductClassifier

st.set_page_config(
    page_title='OjasFuel',
    page_icon='🌿',
    layout='wide',
    initial_sidebar_state='collapsed',
)

init_session()
inject_theme()
classifier = ProductClassifier()


def _is_barcode(query: str) -> bool:
    return query.strip().isdigit() and 8 <= len(query.strip()) <= 14


def _diet_tags(product: dict) -> tuple[str, str]:
    """Return (badge, css_class). Uses classifier result if available, else OFF tags."""
    cl = product.get('_classification', {})
    is_vegan = cl.get('is_vegan') if cl else None
    is_vegetarian = cl.get('is_vegetarian') if cl else None

    # Fall back to OFF's own analysis tags when classifier has no ingredients
    if is_vegan is None and is_vegetarian is None:
        off = product.get('_off_tags', {})
        is_vegan = off.get('is_vegan')
        is_vegetarian = off.get('is_vegetarian')

    if is_vegan:
        return t('vegan_tag'), 'tag-vegan'
    if is_vegetarian:
        return t('vegetarian_tag'), 'tag-veg'
    if is_vegan is None and is_vegetarian is None:
        return t('unknown_tag'), 'tag-unknown'
    return t('not_vegetarian_tag'), 'tag-no'


def _filter_tag(product: dict) -> str:
    cl = product.get('_classification', {})
    if not cl:
        return ''
    if cl.get('passes_filters'):
        return t('passes_filter')
    violations = cl.get('violations', [])
    if violations:
        return t('fails_filter') + '\n• ' + '\n• '.join(violations[:3])
    return ''


def _classify_results(products: list) -> list:
    """
    Classify products and filter out those that fail the active diet mode.
    Priority: OFF's own analysis tags > our regex classifier.
    OFF tags are human-verified; classifier runs only when OFF has no data.
    """
    settings = st.session_state['settings']
    mode = settings.get('mode', 'vegetarian')
    filtered = []

    for p in products:
        off = p.get('_off_tags', {})
        off_veg = off.get('is_vegetarian')   # True / False / None
        off_vegan = off.get('is_vegan')       # True / False / None

        p['_classification'] = classifier.classify(p.get('ingredients', ''), settings)
        cl = p['_classification']

        # Country post-filter: client-side check on countries_tags
        # (secondary guard — server-side already scoped by cc subdomain when available)
        cs = settings.get('countries', {})
        country_tags = cs.get('tags', []) if isinstance(cs, dict) else cs  # compat
        if country_tags:
            prod_countries = p.get('countries_tags', [])
            if prod_countries and not any(c in prod_countries for c in country_tags):
                continue
            # no countries_tags on product → pass through (incomplete metadata)

        # Always hide meat/fish/gelatin — regardless of mode
        is_veg = off_veg if off_veg is not None else cl.get('is_vegetarian')
        if is_veg is False:
            continue

        if mode == 'both':
            filtered.append(p)
            continue

        # Vegan mode: also hide dairy/eggs/honey
        is_vegan = off_vegan if off_vegan is not None else cl.get('is_vegan')
        if mode == 'vegan' and is_vegan is False:
            continue

        filtered.append(p)
    return filtered


# ── Header ──────────────────────────────────────────────────────────────────
col_title, col_settings = st.columns([5, 1])
with col_title:
    logo_col, name_col = st.columns([1, 4], vertical_alignment='center')
    with logo_col:
        st.image('logo_icon.png', width=72)
    with name_col:
        st.image('logo_text.png', width=220)
    st.caption(t('app_subtitle'))
with col_settings:
    st.write('')
    if st.button(t('go_to_settings'), use_container_width=True):
        st.switch_page('pages/5_Settings.py')

# Beta banner
settings = st.session_state['settings']
active_filters = [k for k in ('no_garlic','no_onion','no_caffeine','no_alcohol',
                               'no_mushrooms','no_gelatin','jain','lacto','ovo',
                               'ovo_lacto','strict_egg_traces') if settings.get(k)]
mode = settings.get('mode', 'vegetarian')

banner_parts = [f"Mode: **{mode.capitalize()}**"]
if active_filters:
    banner_parts.append(f"{len(active_filters)} restriction(s) active")
st.info('  |  '.join(banner_parts) + '  —  ' + t('beta_banner'))

st.divider()

# ── Search bar ───────────────────────────────────────────────────────────────
# Pre-populate text box with scanned barcode before widget renders
_scanned = st.session_state.pop('scanned_barcode', None)
if _scanned:
    st.session_state['search_query'] = _scanned

col_search, col_scan = st.columns([5, 1])
with col_search:
    query = st.text_input(
        label=t('search'),
        placeholder=t('search_placeholder'),
        label_visibility='collapsed',
        key='search_query',
    )
with col_scan:
    scan_clicked = st.button(t('scan_barcode'), use_container_width=True)

if scan_clicked:
    st.session_state['show_scanner'] = not st.session_state.get('show_scanner', False)

if st.session_state.get('show_scanner'):
    st.markdown(f"**{t('scan_barcode_title')}**")
    st.caption(t('scan_barcode_hint'))
    camera_image = st.camera_input(label='', label_visibility='collapsed')
    if camera_image is not None:
        try:
            from PIL import Image
            from pyzbar.pyzbar import decode as zbar_decode
            img = Image.open(camera_image)
            barcodes = zbar_decode(img)
            if barcodes:
                detected_code = barcodes[0].data.decode('utf-8')
                st.success(t('barcode_detected', code=detected_code))
                st.session_state['show_scanner'] = False
                st.session_state['scanned_barcode'] = detected_code
                st.rerun()
            else:
                st.error(t('barcode_not_detected'))
        except Exception as e:
            st.error(f"{t('error')}: {e}")

search_clicked = st.button(t('search_button'), type='primary', use_container_width=False)

# Auto-search when barcode was just scanned (no button press needed)
auto_search = bool(_scanned)

if (search_clicked and query.strip()) or (auto_search and query.strip()):
    with st.spinner(t('searching')):
        try:
            if _is_barcode(query.strip()):
                product = search_by_barcode(query.strip())
                if product:
                    products = [product]
                else:
                    products = []
                    st.warning(f"Barcode {query.strip()} not found in Open Food Facts.")
                    st.session_state['contribute_prefill_barcode'] = query.strip()
            else:
                cs = settings.get('countries', {})
                cc = cs.get('cc') if isinstance(cs, dict) else None
                products = search_by_name(query.strip(), page_size=20, country_code=cc)
        except Exception as e:
            st.error(f"{t('error')}: {e}")
            products = []

    if products:
        products = _classify_results(products)
        st.session_state['search_results'] = products
        st.success(t('results_count', n=len(products)))
    elif query.strip():
        st.session_state['search_results'] = []
        st.session_state['contribute_prefill_name'] = query.strip()
        st.warning(t('no_results'))

# ── Contribute prompt (shown only after a failed search) ─────────────────────
_no_results_after_search = (
    (search_clicked or auto_search)
    and query.strip()
    and not st.session_state.get('search_results')
)
if _no_results_after_search or st.session_state.get('contribute_prefill_barcode'):
    st.divider()
    st.caption('🔍 ' + ('Not what you were looking for?' if get_lang() == 'en' else '¿No encontraste lo que buscabas?'))
    if st.button(t('contribute_button'), key='btn_contribute'):
        st.switch_page('pages/6_Contribute.py')

# ── Results ──────────────────────────────────────────────────────────────────
results = st.session_state.get('search_results', [])

if results:
    st.subheader(t('results_count', n=len(results)))

    for idx, product in enumerate(results):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 1])

            with c1:
                name = product.get('name') or 'Unknown'
                brand = product.get('brand') or ''
                st.markdown(f"**{name}**")
                if brand:
                    st.caption(brand)

                # Ingredients preview
                ingr = product.get('ingredients', '')
                if ingr:
                    preview = ingr[:120] + ('…' if len(ingr) > 120 else '')
                    st.caption(f"_{preview}_")
                else:
                    st.caption(f"_{t('no_ingredients')}_")

            with c2:
                diet_tag, _ = _diet_tags(product)
                st.markdown(diet_tag)

                cl = product.get('_classification', {})
                if cl.get('confidence'):
                    st.caption(f"{t('confidence')}: {cl['confidence']*100:.0f}%")

                filter_tag = _filter_tag(product)
                if filter_tag:
                    st.caption(filter_tag)

                qty = product.get('quantity', '')
                nutri = product.get('nutriscore', '')
                if qty:
                    st.caption(f"📦 {qty}")
                if nutri:
                    st.caption(f"Nutri-Score: **{nutri}**")

            with c3:
                if st.button(t('view_detail'), key=f'detail_{idx}', use_container_width=True):
                    st.session_state['selected_product'] = product
                    st.session_state['portion_product'] = product
                    st.session_state['equiv_original'] = product
                    st.switch_page('pages/1_Detail.py')
