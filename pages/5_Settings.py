"""
OjasFuel — Settings page
"""

import streamlit as st
import sys
sys.path.insert(0, '/home/eherrera-chacon/Documents/smaeuk')

from src.i18n import t, init_session, DEFAULT_SETTINGS
from src.theme import inject_theme
from src.storage import save_to_localstorage, clear_localstorage

st.set_page_config(page_title='OjasFuel — Settings', page_icon='⚙️', layout='wide')
init_session()
inject_theme()

if st.button(t('back')):
    st.switch_page('app.py')

st.title(f"⚙️ {t('settings')}")

s = st.session_state['settings']

# ── Appearance / Theme ───────────────────────────────────────────────────────
st.subheader(t('appearance'))

current_theme = st.session_state.get('theme', 'dark')
theme_col, _ = st.columns([2, 3])
with theme_col:
    st.markdown(f'<p class="theme-toggle-label">{t("color_theme")}</p>', unsafe_allow_html=True)
    theme_choice = st.radio(
        t('color_theme'),
        options=[t('theme_dark'), t('theme_light')],
        index=0 if current_theme == 'dark' else 1,
        horizontal=True,
        label_visibility='collapsed',
    )
    new_theme = 'dark' if theme_choice == t('theme_dark') else 'light'
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
    '🇲🇽 Mexico':            {'tags': ['en:mexico'],              'cc': 'mx'},
    '🇺🇸 United States':     {'tags': ['en:united-states'],       'cc': 'us'},
    '🇬🇧 United Kingdom':    {'tags': ['en:united-kingdom'],      'cc': 'gb'},
    '🇪🇸 Spain':             {'tags': ['en:spain'],               'cc': 'es'},
    '🇫🇷 France':            {'tags': ['en:france'],              'cc': 'fr'},
    '🇩🇪 Germany':           {'tags': ['en:germany'],             'cc': 'de'},
    '🇮🇹 Italy':             {'tags': ['en:italy'],               'cc': 'it'},
    '🇳🇱 Netherlands':       {'tags': ['en:netherlands'],         'cc': 'nl'},
    '🇧🇪 Belgium':           {'tags': ['en:belgium'],             'cc': 'be'},
    '🇨🇭 Switzerland':       {'tags': ['en:switzerland'],         'cc': 'ch'},
    '🇵🇹 Portugal':          {'tags': ['en:portugal'],            'cc': 'pt'},
    '🇵🇱 Poland':            {'tags': ['en:poland'],              'cc': 'pl'},
    # Regional group
    '🌍 Europe (all)':        {'tags': [
        'en:united-kingdom','en:france','en:germany','en:italy','en:spain',
        'en:netherlands','en:belgium','en:switzerland','en:portugal','en:poland',
        'en:austria','en:sweden','en:denmark','en:norway','en:finland',
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
    st.caption(t('country_search_msg', country=country_choice.split(' ', 1)[-1]))
elif chosen['tags']:
    st.caption(t('client_filter_only'))
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
                              help=t('lacto_help'))
with col2:
    s['ovo'] = st.checkbox(t('ovo'), value=s.get('ovo', False),
                            help=t('ovo_help'))
with col3:
    s['ovo_lacto'] = st.checkbox(t('ovo_lacto'), value=s.get('ovo_lacto', False),
                                  help=t('ovo_lacto_help'))

s['strict_egg_traces'] = st.checkbox(
    t('strict_egg_traces'),
    value=s.get('strict_egg_traces', False),
    help=t('strict_egg_traces_help'),
)

st.divider()

# ── Additional restrictions ───────────────────────────────────────────────────
with st.expander(t('extra_restrictions'), expanded=False):
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
            help=t('jain_help'),
        )

st.divider()

# ── Allergies ──────────────────────────────────────────────────────────────────
with st.expander(t('allergies'), expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        s['allergies_nuts'] = st.checkbox(t('allergies_nuts'), value=s.get('allergies_nuts', False))
        s['allergies_peanuts'] = st.checkbox(t('allergies_peanuts'), value=s.get('allergies_peanuts', False))
        s['allergies_soy'] = st.checkbox(t('allergies_soy'), value=s.get('allergies_soy', False))
    with col_b:
        s['allergies_mustard'] = st.checkbox(t('allergies_mustard'), value=s.get('allergies_mustard', False))
        s['allergies_sesame'] = st.checkbox(t('allergies_sesame'), value=s.get('allergies_sesame', False))
        s['allergies_gluten'] = st.checkbox(t('allergies_gluten'), value=s.get('allergies_gluten', False))

st.divider()

# ── Equivalents threshold ─────────────────────────────────────────────────────
st.subheader(t('equivalents_threshold'))
threshold_pct = round(s.get('equivalents_threshold', 0.10) * 100)
if threshold_pct not in [5, 10, 15, 20]:
    threshold_pct = 10
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

st.write('')
col_info, col_logo = st.columns([3, 1])
with col_info:
    st.markdown(f"**{t('version')}:** v0.1.1 Beta")
    st.markdown(f"**{t('creator')}:** Edwin Herrera")
    is_mexico_info = s.get('countries', {}).get('cc') == 'mx'
    if is_mexico_info:
        st.markdown(f"**{t('data_source')}:** {t('data_source_text_mx')}")
        st.caption(t('disclaimer_mx'))
        st.caption(t('smae_credit'))
        st.caption(t('off_credit'))
    else:
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
    is_mexico = s.get('countries', {}).get('cc') == 'mx'
    if is_mexico:
        import base64 as _b64
        _smae_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 160">
  <text x="10" y="138" font-family="Arial Rounded MT Bold,Arial Black,Helvetica Neue,sans-serif"
        font-weight="900" font-size="152" fill="#6aaa1e" letter-spacing="-4">smae</text>
  <text x="448" y="58" font-family="Arial,sans-serif" font-weight="700" font-size="26" fill="#6aaa1e">MR</text>
  <circle cx="490" cy="44" r="24" fill="none" stroke="#6aaa1e" stroke-width="3"/>
</svg>"""
        _smae_b64 = _b64.b64encode(_smae_svg).decode()
        st.markdown(
            f'<div style="display:flex;flex-direction:column;gap:10px;align-items:flex-start;">'
            f'<a href="https://midietasmae.com.mx/" target="_blank">'
            f'<img src="data:image/svg+xml;base64,{_smae_b64}" style="width:130px;height:auto;"></a>'
            f'<a href="https://world.openfoodfacts.org" target="_blank">'
            f'<img src="{off_logo}" style="width:130px;height:auto;"></a>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<a href="https://world.openfoodfacts.org" target="_blank">'
            f'<img src="{off_logo}" width="140"></a>',
            unsafe_allow_html=True,
        )

st.write('')
st.markdown(
    f"""
    <div style="margin-top:0.5rem;">
        <p style="margin-bottom:0.75rem;color:var(--text-secondary);font-size:0.95rem;">
            {t('support_text')}
        </p>
        <a href="https://buymeacoffee.com/cowboyedwin" target="_blank"
           style="display:inline-block;
                  background:#FFDD00;
                  color:#000000;
                  font-weight:700;
                  font-size:0.95rem;
                  padding:0.55rem 1.4rem;
                  border-radius:12px;
                  text-decoration:none;
                  letter-spacing:0.02em;">
            {t('support_btn')}
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
