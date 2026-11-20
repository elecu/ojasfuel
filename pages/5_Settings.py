"""
OjasFuel — Settings page (auto-saving)
"""

import copy
import streamlit as st

from src.countries import COUNTRIES, country_name, country_cid, apply_country, ordered_ids
from src.i18n import _valid_setting, get_lang, t, init_session, DEFAULT_SETTINGS, apply_veg_variant
from src.theme import inject_theme

st.set_page_config(page_title='OjasFuel — Settings', page_icon='⚙️', layout='wide')
init_session()
inject_theme()



def _wk(name: str) -> str:
    """Widget key scoped to the UI language.

    Streamlit sends radio/select values from the browser as their *formatted
    label*; when the language changes the old label ("Dark") no longer maps to
    an option and the raw label leaks into settings. A per-language key makes
    the widgets rebuild from the stored setting instead.
    """
    return f'set_{name}_{get_lang()}'


# ── Callbacks: update session settings, flag persistence, toast ──────────────
def _changed(key: str, widget_key: str, transform=lambda v: v) -> None:
    s = st.session_state['settings']
    value = transform(st.session_state[widget_key])
    if not _valid_setting(key, value):
        return  # never persist a stray label
    s[key] = value
    if key == 'countries':
        apply_country(s, country_cid(value))  # also remembers it as a recent country
    if key == 'veg_variant':
        apply_veg_variant(s)
    if key == 'theme':
        st.session_state['theme'] = s['theme']
    st.session_state['_ls_dirty'] = True
    st.toast(t('settings_saved'))


def _reset() -> None:
    st.session_state['settings'] = copy.deepcopy(DEFAULT_SETTINGS)
    for k in [k for k in st.session_state if str(k).startswith('set_')]:
        del st.session_state[k]
    st.session_state['_pending_ls_clear'] = True
    st.toast(t('settings_reset_done'))


s = st.session_state['settings']

if st.button(t('back')):
    st.switch_page('app.py')

st.title(f"⚙️ {t('settings')}")
st.caption(t('settings_autosave'))

# ── Appearance / Theme ───────────────────────────────────────────────────────
st.subheader(t('appearance'))
theme_col, _ = st.columns([2, 3])
with theme_col:
    st.radio(
        t('color_theme'),
        options=['dark', 'light'],
        format_func=lambda v: t('theme_dark') if v == 'dark' else t('theme_light'),
        index=0 if s.get('theme', 'dark') == 'dark' else 1,
        horizontal=True,
        key=_wk('theme'),
        on_change=_changed, args=('theme', _wk('theme')),
    )

st.divider()

# ── Country filter ────────────────────────────────────────────────────────────
st.subheader(t('country_filter'))
_ids = ordered_ids(s.get('recent_countries'))
st.selectbox(
    t('country_filter'),
    options=_ids,
    format_func=country_name,
    index=_ids.index(country_cid(s.get('countries', {'tags': [], 'cc': None}))),
    help=t('country_filter_help'),
    label_visibility='collapsed',
    key=_wk('country'),
    on_change=_changed, args=('countries', _wk('country'), lambda cid: copy.deepcopy(COUNTRIES[cid])),
)
chosen = s.get('countries') or {'tags': [], 'cc': None}
if chosen.get('cc'):
    st.caption(t('country_search_msg', country=country_name(country_cid(chosen)).split(' ', 1)[-1]))
elif chosen.get('tags'):
    st.caption(t('client_filter_only'))
else:
    st.caption(t('country_all'))

st.divider()

# ── Language ─────────────────────────────────────────────────────────────────
st.subheader(t('language'))
_langs = ['en', 'es']
st.radio(
    t('language'),
    options=_langs,
    format_func=lambda v: {'en': 'English (UK)', 'es': 'Español'}[v],
    index=_langs.index(s.get('lang', 'en')) if s.get('lang', 'en') in _langs else 0,
    horizontal=True,
    label_visibility='collapsed',
    key=_wk('lang'),
    on_change=_changed, args=('lang', _wk('lang')),
)

st.divider()

# ── Diet mode ─────────────────────────────────────────────────────────────────
st.subheader(t('diet_mode'))
_modes = ['vegetarian', 'vegan', 'both']
st.radio(
    t('diet_mode'),
    options=_modes,
    format_func=lambda m: t(m),
    index=_modes.index(s.get('mode', 'vegetarian')) if s.get('mode') in _modes else 0,
    horizontal=True,
    label_visibility='collapsed',
    key=_wk('mode'),
    on_change=_changed, args=('mode', _wk('mode')),
)

# ── Vegetarian variant (only meaningful for vegetarian mode) ─────────────────
if s.get('mode', 'vegetarian') == 'vegetarian':
    st.markdown(f"**{t('dairy_variants')}**")
    _variants = ['lacto_ovo', 'lacto', 'ovo']
    _vlabels = {'lacto_ovo': t('veg_lacto_ovo'), 'lacto': t('lacto'), 'ovo': t('ovo')}
    st.radio(
        t('dairy_variants'),
        options=_variants,
        format_func=lambda v: _vlabels[v],
        index=_variants.index(s.get('veg_variant', 'lacto_ovo')),
        label_visibility='collapsed',
        help=t('veg_variant_help'),
        key=_wk('veg_variant'),
        on_change=_changed, args=('veg_variant', _wk('veg_variant')),
    )

st.checkbox(
    t('strict_egg_traces'),
    value=s.get('strict_egg_traces', False),
    help=t('strict_egg_traces_help'),
    key=_wk('strict_egg_traces'),
    on_change=_changed, args=('strict_egg_traces', _wk('strict_egg_traces')),
)

st.divider()


def _checkbox(key: str, help_key: str | None = None) -> None:
    st.checkbox(
        t(key), value=s.get(key, False),
        help=t(help_key) if help_key else None,
        key=_wk(key),
        on_change=_changed, args=(key, _wk(key)),
    )


# ── Allergies (safety-critical: shown first, expanded when any active) ───────
_allergy_keys = ['allergies_nuts', 'allergies_peanuts', 'allergies_soy',
                 'allergies_mustard', 'allergies_sesame', 'allergies_gluten']
with st.expander(t('allergies'), expanded=any(s.get(k) for k in _allergy_keys)):
    col_a, col_b = st.columns(2)
    with col_a:
        for k in _allergy_keys[:3]:
            _checkbox(k)
    with col_b:
        for k in _allergy_keys[3:]:
            _checkbox(k)

# ── Additional restrictions ───────────────────────────────────────────────────
_extra_keys = ['no_garlic', 'no_onion', 'no_caffeine', 'no_alcohol',
               'no_mushrooms', 'no_gelatin', 'jain']
with st.expander(t('extra_restrictions'), expanded=any(s.get(k) for k in _extra_keys)):
    col_a, col_b = st.columns(2)
    with col_a:
        for k in ('no_garlic', 'no_onion', 'no_caffeine', 'no_alcohol'):
            _checkbox(k)
    with col_b:
        for k in ('no_mushrooms', 'no_gelatin'):
            _checkbox(k)
        _checkbox('jain', 'jain_help')

st.divider()

st.button(t('reset_settings'), on_click=_reset, width='stretch')

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
