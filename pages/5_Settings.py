"""
SMAEUK — Settings page
"""

import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session, DEFAULT_SETTINGS
from src.theme import inject_theme
from src.storage import save_to_localstorage, clear_localstorage

st.set_page_config(page_title='SMAEUK — Settings', page_icon='⚙️', layout='wide')
init_session()
inject_theme()

if st.button(t('back')):
    st.switch_page('app.py')

st.title(f"⚙️ {t('settings')}")

s = st.session_state['settings']

# ── Appearance / Theme ───────────────────────────────────────────────────────
st.subheader('Appearance')

current_theme = st.session_state.get('theme', 'dark')
theme_col, _ = st.columns([2, 3])
with theme_col:
    st.markdown('<p class="theme-toggle-label">Color Theme</p>', unsafe_allow_html=True)
    theme_choice = st.radio(
        'Color Theme',
        options=['Dark', 'Light'],
        index=0 if current_theme == 'dark' else 1,
        horizontal=True,
        label_visibility='collapsed',
    )
    new_theme = 'dark' if theme_choice == 'Dark' else 'light'
    if new_theme != current_theme:
        st.session_state['theme'] = new_theme
        st.rerun()

st.divider()

# ── Country filter ────────────────────────────────────────────────────────────
st.subheader(t('country_filter'))

# Each entry: display name → {tags: [...], cc: '2-letter-code' | None}
# cc = OFF country code used to query the country-specific subdomain (better coverage)
# tags = used for client-side post-filter on countries_tags metadata
COUNTRIES = {
    'All countries':          {'tags': [],                         'cc': None},
    '🇬🇧 United Kingdom':    {'tags': ['en:united-kingdom'],      'cc': 'gb'},
    '🇪🇸 Spain':             {'tags': ['en:spain'],               'cc': 'es'},
    '🇫🇷 France':            {'tags': ['en:france'],              'cc': 'fr'},
    '🇩🇪 Germany':           {'tags': ['en:germany'],             'cc': 'de'},
    '🇮🇹 Italy':             {'tags': ['en:italy'],               'cc': 'it'},
    '🇺🇸 United States':     {'tags': ['en:united-states'],       'cc': 'us'},
    '🇲🇽 Mexico':            {'tags': ['en:mexico'],              'cc': 'mx'},
    '🇦🇷 Argentina':         {'tags': ['en:argentina'],           'cc': 'ar'},
    '🇨🇴 Colombia':          {'tags': ['en:colombia'],            'cc': 'co'},
    '🇨🇱 Chile':             {'tags': ['en:chile'],               'cc': 'cl'},
    '🇵🇪 Peru':              {'tags': ['en:peru'],                'cc': 'pe'},
    '🇧🇷 Brazil':            {'tags': ['en:brazil'],              'cc': 'br'},
    '🇨🇦 Canada':            {'tags': ['en:canada'],              'cc': 'ca'},
    '🇦🇺 Australia':         {'tags': ['en:australia'],           'cc': 'au'},
    '🇳🇱 Netherlands':       {'tags': ['en:netherlands'],         'cc': 'nl'},
    '🇧🇪 Belgium':           {'tags': ['en:belgium'],             'cc': 'be'},
    '🇨🇭 Switzerland':       {'tags': ['en:switzerland'],         'cc': 'ch'},
    '🇵🇹 Portugal':          {'tags': ['en:portugal'],            'cc': 'pt'},
    '🇵🇱 Poland':            {'tags': ['en:poland'],              'cc': 'pl'},
    # Regional groups use world API (no single cc) but still client-filter by tags
    '🌍 Europe (all)':        {'tags': [
        'en:united-kingdom','en:france','en:germany','en:italy','en:spain',
        'en:netherlands','en:belgium','en:switzerland','en:portugal','en:poland',
        'en:austria','en:sweden','en:denmark','en:norway','en:finland',
    ], 'cc': None},
    '🌎 Latin America (all)': {'tags': [
        'en:mexico','en:argentina','en:colombia','en:chile','en:peru',
        'en:brazil','en:venezuela','en:ecuador','en:bolivia','en:uruguay',
    ], 'cc': None},
}

current_setting = s.get('countries', {'tags': [], 'cc': None})
# backward compat: old format was a plain list
if isinstance(current_setting, list):
    current_setting = {'tags': current_setting, 'cc': None}

current_display = next(
    (name for name, v in COUNTRIES.items() if v['cc'] == current_setting.get('cc') and sorted(v['tags']) == sorted(current_setting.get('tags', []))),
    'All countries'
)

country_choice = st.selectbox(
    t('country_filter'),
    options=list(COUNTRIES.keys()),
    index=list(COUNTRIES.keys()).index(current_display),
    help=t('country_filter_help'),
    label_visibility='collapsed',
)
s['countries'] = COUNTRIES[country_choice]

chosen = COUNTRIES[country_choice]
if chosen['cc']:
    st.caption(f"🌐 Search on **{country_choice.split(' ', 1)[-1]}** OFF database  |  client-filter by country tag")
elif chosen['tags']:
    st.caption(f"Client-side filter only (no single country API for regional groups)")
else:
    st.caption(t('country_all'))

st.divider()

# ── Language ─────────────────────────────────────────────────────────────────
st.subheader(t('language'))
lang_map = {'English (UK)': 'en', 'Español': 'es'}
lang_display = {v: k for k, v in lang_map.items()}
lang_choice = st.radio(
    t('language'),
    options=list(lang_map.keys()),
    index=list(lang_map.values()).index(s.get('lang', 'en')),
    horizontal=True,
    label_visibility='collapsed',
)
s['lang'] = lang_map[lang_choice]

st.divider()

# ── Diet mode ─────────────────────────────────────────────────────────────────
st.subheader(t('diet_mode'))
mode_map = {t('vegetarian'): 'vegetarian', t('vegan'): 'vegan', t('both'): 'both'}
mode_display = {v: k for k, v in mode_map.items()}
mode_choice = st.radio(
    t('diet_mode'),
    options=list(mode_map.keys()),
    index=list(mode_map.values()).index(s.get('mode', 'vegetarian')),
    horizontal=True,
    label_visibility='collapsed',
)
s['mode'] = mode_map[mode_choice]

st.divider()

# ── Dairy & Egg variants ──────────────────────────────────────────────────────
st.subheader(t('dairy_variants'))
col1, col2, col3 = st.columns(3)
with col1:
    s['lacto'] = st.checkbox(t('lacto'), value=s.get('lacto', False),
                              help='Lacto-vegetarian: dairy OK, no eggs')
with col2:
    s['ovo'] = st.checkbox(t('ovo'), value=s.get('ovo', False),
                            help='Ovo-vegetarian: eggs OK, no dairy')
with col3:
    s['ovo_lacto'] = st.checkbox(t('ovo_lacto'), value=s.get('ovo_lacto', False),
                                  help='Both dairy and eggs OK')

s['strict_egg_traces'] = st.checkbox(
    t('strict_egg_traces'),
    value=s.get('strict_egg_traces', False),
    help=t('strict_egg_traces_help'),
)

st.divider()

# ── Additional restrictions ───────────────────────────────────────────────────
st.subheader(t('extra_restrictions'))

col_a, col_b = st.columns(2)
with col_a:
    s['no_garlic'] = st.checkbox(t('no_garlic'), value=s.get('no_garlic', False))
    s['no_onion'] = st.checkbox(t('no_onion'), value=s.get('no_onion', False))
    s['no_caffeine'] = st.checkbox(t('no_caffeine'), value=s.get('no_caffeine', False))
    s['no_alcohol'] = st.checkbox(t('no_alcohol'), value=s.get('no_alcohol', False))
with col_b:
    s['no_mushrooms'] = st.checkbox(t('no_mushrooms'), value=s.get('no_mushrooms', False))
    s['no_gelatin'] = st.checkbox(t('no_gelatin'), value=s.get('no_gelatin', False))
    s['jain'] = st.checkbox(
        t('jain'),
        value=s.get('jain', False),
        help='Jain diet avoids root/underground vegetables + alliums',
    )

st.divider()

# ── Equivalents threshold ─────────────────────────────────────────────────────
st.subheader(t('equivalents_threshold'))
threshold_pct = int(s.get('equivalents_threshold', 0.10) * 100)
threshold_pct = st.select_slider(
    t('threshold_label', pct=threshold_pct),
    options=[5, 10, 15, 20],
    value=threshold_pct,
    label_visibility='collapsed',
)
s['equivalents_threshold'] = threshold_pct / 100
st.caption(t('threshold_label', pct=threshold_pct))

st.divider()

# ── Save / Reset ──────────────────────────────────────────────────────────────
col_save, col_reset = st.columns([2, 1])
with col_save:
    if st.button(t('save_settings'), type='primary', use_container_width=True):
        st.session_state['settings'] = s
        save_to_localstorage(s)   # persist to browser localStorage
        st.success(t('settings_saved'))
with col_reset:
    if st.button(t('reset_settings'), use_container_width=True):
        st.session_state['settings'] = dict(DEFAULT_SETTINGS)
        st.session_state['_ls_loaded'] = False
        clear_localstorage()      # wipe localStorage too
        st.rerun()

st.divider()

# ── About ─────────────────────────────────────────────────────────────────────
st.subheader(t('about'))

col_info, col_logo = st.columns([3, 1])
with col_info:
    st.markdown(f"**{t('version')}:** v0.1.0 Beta")
    st.markdown(f"**{t('creator')}:** Edwin Herrera")
    st.markdown(f"**{t('data_source')}:** {t('data_source_text')}")
    st.caption(t('disclaimer'))
    st.caption(t('off_credit'))

with col_logo:
    theme = st.session_state.get('theme', 'dark')
    off_logo = (
        "https://static.openfoodfacts.org/images/logos/off-logo-horizontal-dark.svg"
        if theme == 'dark'
        else "https://static.openfoodfacts.org/images/logos/off-logo-horizontal-light.svg"
    )
    st.markdown(
        f'<a href="https://world.openfoodfacts.org" target="_blank">'
        f'<img src="{off_logo}" width="140"></a>',
        unsafe_allow_html=True,
    )
