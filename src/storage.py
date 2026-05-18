"""
localStorage persistence for user settings.
Uses streamlit-javascript to read/write browser localStorage.
Each user's browser stores their own settings — no server-side storage needed.
"""

import json
import streamlit as st

try:
    from streamlit_javascript import st_javascript
    _JS_OK = True
except ImportError:
    _JS_OK = False

_LS_KEY = 'smaeuk_settings_v1'


def load_from_localstorage() -> dict | None:
    """
    Read settings dict from localStorage.
    Returns None on first render (JS not yet evaluated) or if nothing stored.
    Caller should overlay on top of defaults, not replace them.
    """
    if not _JS_OK:
        return None
    try:
        raw = st_javascript(f"JSON.parse(localStorage.getItem('{_LS_KEY}') || 'null')")
        if raw and isinstance(raw, dict):
            return raw
    except Exception:
        pass
    return None


def save_to_localstorage(settings: dict) -> None:
    """Write settings dict to localStorage. Call when user clicks Save Settings."""
    if not _JS_OK:
        return
    try:
        payload = json.dumps(settings, ensure_ascii=False)
        # Escape backticks so the template literal is safe
        payload = payload.replace('`', r'\`')
        st_javascript(f"localStorage.setItem('{_LS_KEY}', JSON.stringify({payload})); 1")
    except Exception:
        pass


def clear_localstorage() -> None:
    """Remove saved settings from localStorage (used by Reset button)."""
    if not _JS_OK:
        return
    try:
        st_javascript(f"localStorage.removeItem('{_LS_KEY}'); 1")
    except Exception:
        pass
