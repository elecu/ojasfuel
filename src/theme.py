"""
OjasFuel — Shared theme/CSS injection utility.

Call inject_theme() at the top of every page (after init_session).
It reads st.session_state['theme'] ('dark' | 'light') and injects the
appropriate CSS variables + component overrides via st.markdown.

No business logic lives here — pure presentation.
"""

import streamlit as st

# ── CSS template ─────────────────────────────────────────────────────────────
# Variables are defined on :root for the chosen theme then used throughout.
# Every override targets Streamlit's generated class names via attribute or
# element selectors so we never rely on undocumented internal class names.

_CSS_DARK = """
:root {
    --bg-primary:      #0a0a0f;
    --bg-secondary:    #111118;
    --bg-surface:      #16161f;
    --bg-elevated:     #1c1c28;
    --accent:          #00d4ff;
    --accent-dim:      rgba(0, 212, 255, 0.12);
    --accent-glow:     rgba(0, 212, 255, 0.25);
    --text-primary:    #f0f0f5;
    --text-secondary:  #9898b0;
    --text-muted:      #55556a;
    --border:          rgba(255, 255, 255, 0.06);
    --border-accent:   rgba(0, 212, 255, 0.30);
    --success:         #00ff9d;
    --success-bg:      rgba(0, 255, 157, 0.08);
    --warning:         #ffb830;
    --warning-bg:      rgba(255, 184, 48, 0.08);
    --error:           #ff4d6d;
    --error-bg:        rgba(255, 77, 109, 0.08);
    --info:            #7b8cff;
    --info-bg:         rgba(123, 140, 255, 0.08);
    --radius-sm:       8px;
    --radius-md:       12px;
    --radius-lg:       16px;
    --shadow:          0 4px 24px rgba(0,0,0,0.4);
    --shadow-accent:   0 0 20px rgba(0, 212, 255, 0.15);
    --transition:      0.25s ease;
}
"""

_CSS_LIGHT = """
:root {
    --bg-primary:      #f8f8fc;
    --bg-secondary:    #f2f2f8;
    --bg-surface:      #ebebf5;
    --bg-elevated:     #ffffff;
    --accent:          #0099cc;
    --accent-dim:      rgba(0, 153, 204, 0.10);
    --accent-glow:     rgba(0, 153, 204, 0.20);
    --text-primary:    #1a1a2e;
    --text-secondary:  #4a4a6a;
    --text-muted:      #8888a8;
    --border:          rgba(0, 0, 0, 0.08);
    --border-accent:   rgba(0, 153, 204, 0.30);
    --success:         #008060;
    --success-bg:      rgba(0, 128, 96, 0.08);
    --warning:         #b86000;
    --warning-bg:      rgba(184, 96, 0, 0.08);
    --error:           #cc1a3a;
    --error-bg:        rgba(204, 26, 58, 0.08);
    --info:            #3344cc;
    --info-bg:         rgba(51, 68, 204, 0.08);
    --radius-sm:       8px;
    --radius-md:       12px;
    --radius-lg:       16px;
    --shadow:          0 4px 16px rgba(0,0,0,0.08);
    --shadow-accent:   0 0 16px rgba(0, 153, 204, 0.12);
    --transition:      0.25s ease;
}
"""

_CSS_SHARED = """
/* ── Font import ──────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

/* ── Global resets & base ─────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    -webkit-font-smoothing: antialiased;
}

/* Main content area */
[data-testid="stMain"] > div,
.main .block-container {
    background-color: var(--bg-primary) !important;
    padding-top: 2rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Typography ───────────────────────────────────────────────────────── */
h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    color: var(--text-primary) !important;
}
h1 { font-size: 2rem !important; line-height: 1.2; }
h2 { font-size: 1.4rem !important; }
h3 { font-size: 1.15rem !important; }

/* Streamlit heading widgets */
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3 {
    color: var(--text-primary) !important;
}

p, li, span, label, div {
    color: var(--text-primary);
}

/* Caption / helper text */
[data-testid="stCaptionContainer"] p,
small, .stCaption {
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
}

/* ── Divider ──────────────────────────────────────────────────────────── */
hr, [data-testid="stDivider"] hr {
    border-color: var(--border) !important;
    margin: 1.5rem 0 !important;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.03em !important;
    border-radius: var(--radius-md) !important;
    transition: all var(--transition) !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    padding: 0.45rem 1.1rem !important;
    box-shadow: none !important;
}
[data-testid="stButton"] > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--accent-dim) !important;
    box-shadow: var(--shadow-accent) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button[kind="primary"],
[data-testid="stButton"] > button[data-baseweb="button"][kind="primary"] {
    background: var(--accent) !important;
    color: var(--bg-primary) !important;
    border-color: var(--accent) !important;
    font-weight: 700 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: var(--bg-primary) !important;
    color: var(--accent) !important;
    box-shadow: var(--shadow-accent) !important;
    transform: translateY(-1px) !important;
}

/* ── Text inputs ──────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    transition: border-color var(--transition), box-shadow var(--transition) !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 0.75rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
    outline: none !important;
}

/* Label above inputs */
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label {
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    color: var(--text-secondary) !important;
}

/* ── Selectbox ────────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background-color: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    transition: border-color var(--transition) !important;
}
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
}

/* ── Radio buttons ────────────────────────────────────────────────────── */
[data-testid="stRadio"] > div {
    gap: 0.5rem !important;
}
[data-testid="stRadio"] label {
    font-size: 0.9rem !important;
    font-weight: 400 !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    color: var(--text-primary) !important;
}
[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
    color: var(--text-primary) !important;
}

/* ── Checkboxes ───────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] label {
    font-size: 0.9rem !important;
    font-weight: 400 !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    color: var(--text-primary) !important;
}
[data-testid="stCheckbox"] span[data-baseweb="checkbox"] > div {
    border-color: var(--border-accent) !important;
    border-radius: 4px !important;
    transition: background var(--transition) !important;
}

/* ── Slider ───────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background-color: var(--accent) !important;
    box-shadow: 0 0 8px var(--accent-glow) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stSliderTrackFill"] {
    background-color: var(--accent) !important;
}

/* ── Cards / containers ───────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1.25rem 1.5rem !important;
    box-shadow: var(--shadow) !important;
    transition: border-color var(--transition), box-shadow var(--transition) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
    border-color: var(--border-accent) !important;
    box-shadow: var(--shadow-accent), var(--shadow) !important;
}

/* ── Expander ─────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    background: var(--bg-surface) !important;
    overflow: hidden;
    transition: border-color var(--transition) !important;
}
[data-testid="stExpander"]:hover {
    border-color: var(--border-accent) !important;
}
[data-testid="stExpander"] summary {
    background: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: var(--bg-elevated) !important;
    border-top: 1px solid var(--border) !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.03em !important;
    color: var(--text-secondary) !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.6rem 1rem !important;
    transition: all var(--transition) !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: var(--text-primary) !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* ── Metric widgets ───────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 0.9rem 1rem !important;
    transition: border-color var(--transition) !important;
}
[data-testid="stMetric"]:hover {
    border-color: var(--border-accent) !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: var(--text-secondary) !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--accent) !important;
}

/* ── Alerts: success / warning / error / info ─────────────────────────── */
[data-testid="stAlert"][data-baseweb="notification"][kind="positive"],
.stSuccess {
    background-color: var(--success-bg) !important;
    border: 1px solid var(--success) !important;
    border-radius: var(--radius-md) !important;
    color: var(--success) !important;
}
[data-testid="stAlert"][kind="warning"],
.stWarning {
    background-color: var(--warning-bg) !important;
    border: 1px solid var(--warning) !important;
    border-radius: var(--radius-md) !important;
    color: var(--warning) !important;
}
[data-testid="stAlert"][kind="error"],
.stError {
    background-color: var(--error-bg) !important;
    border: 1px solid var(--error) !important;
    border-radius: var(--radius-md) !important;
    color: var(--error) !important;
}
[data-testid="stAlert"][kind="info"],
.stInfo {
    background-color: var(--info-bg) !important;
    border: 1px solid var(--info) !important;
    border-radius: var(--radius-md) !important;
    color: var(--info) !important;
}

/* Text inside alerts */
[data-testid="stAlert"] p,
[data-testid="stAlert"] span {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
}

/* ── Spinner ──────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] p {
    color: var(--accent) !important;
    font-size: 0.88rem !important;
}

/* ── File uploader ────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] > div {
    background-color: var(--bg-surface) !important;
    border: 2px dashed var(--border-accent) !important;
    border-radius: var(--radius-md) !important;
    transition: border-color var(--transition) !important;
}
[data-testid="stFileUploader"] > div:hover {
    border-color: var(--accent) !important;
    background-color: var(--accent-dim) !important;
}

/* ── Info banner (st.info top of search) ──────────────────────────────── */
[data-testid="stNotification"] {
    border-radius: var(--radius-md) !important;
}

/* ── Scrollbar ────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb {
    background: var(--text-muted);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ── Accent header line ───────────────────────────────────────────────── */
.smaeuk-page-header {
    border-left: 3px solid var(--accent);
    padding-left: 0.75rem;
    margin-bottom: 1.5rem;
}

/* ── Theme toggle pill ────────────────────────────────────────────────── */
.theme-toggle-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin-bottom: 0.25rem;
}
"""


def inject_theme() -> None:
    """
    Inject theme CSS into the current Streamlit page.
    Must be called after init_session() so session_state['theme'] exists.
    """
    theme = st.session_state.get('theme', 'dark')
    vars_css = _CSS_DARK if theme == 'dark' else _CSS_LIGHT
    full_css = f"<style>{vars_css}{_CSS_SHARED}</style>"
    st.markdown(full_css, unsafe_allow_html=True)
