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


# Streamlit turns a component value of null into the default (0), which we use
# to mean "JS not evaluated yet". So an empty key must return a distinct marker,
# otherwise first-time users wait forever (no onboarding, history never saved).
_EMPTY = '__ojasfuel_empty__'


def _read_js(ls_key: str) -> str:
    return (f"(() => {{ const v = localStorage.getItem('{ls_key}'); "
            f"return v === null ? '{_EMPTY}' : JSON.parse(v); }})()")


def _interpret(raw):
    """Map an st_javascript result to (ready, data)."""
    if raw is None or (isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw == 0):
        return False, None
    if raw == _EMPTY:
        return True, None
    return True, raw


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
        raw = st_javascript(_read_js(_LS_KEY))
    except Exception:
        return True, None
    ready, data = _interpret(raw)
    return ready, (data if isinstance(data, dict) else None)


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


# ── Generic keyed storage (history etc.) ─────────────────────────────────────
def read_key(ls_key: str):
    """Read a JSON value stored under ls_key. Returns (ready, data)."""
    if not _JS_OK:
        return True, None
    try:
        raw = st_javascript(_read_js(ls_key))
    except Exception:
        return True, None
    return _interpret(raw)


def write_key(ls_key: str, data) -> None:
    """Write a JSON-serialisable value to localStorage under ls_key."""
    if not _JS_OK:
        return
    try:
        payload = json.dumps(data, ensure_ascii=False)
        payload = payload.replace('\\', '\\\\').replace('`', r'\`').replace('${', '\\${').replace('</', '<\\/')
        st_javascript(f"localStorage.setItem('{ls_key}', `{payload}`); 1")
    except Exception:
        pass
