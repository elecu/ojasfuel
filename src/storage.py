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


def read_localstorage() -> tuple[bool, dict | None]:
    """
    Read settings from localStorage.
    Returns (ready, data). st_javascript returns 0 until the JS has been
    evaluated in the browser; any other value (including None = nothing stored)
    means the read completed.
    """
    if not _JS_OK:
        return True, None
    try:
        raw = st_javascript(f"JSON.parse(localStorage.getItem('{_LS_KEY}') || 'null')")
    except Exception:
        return True, None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw == 0:
        return False, None
    return True, (raw if isinstance(raw, dict) else None)


def load_from_localstorage() -> dict | None:
    """Backward-compatible wrapper: returns stored dict or None."""
    return read_localstorage()[1]


def save_to_localstorage(settings: dict) -> None:
    """Write settings dict to localStorage. Called automatically when a setting changes."""
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
