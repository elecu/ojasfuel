"""Browser-persisted history: recent views, searches, 'safe' and 'avoid' lists.

Stored in localStorage under one key (same st_javascript pattern as
src/storage.py). Loaded once per session; mutations mark the state dirty and
are flushed to the browser on the next load_history()/flush() call.
"""

from datetime import date

import streamlit as st

from src.storage import read_key, write_key

LS_KEY = 'ojasfuel_history_v1'
MAX_RECENT = 50
MAX_SEARCHES = 20
MAX_LIST = 200
_LISTS = ('safe', 'avoid')

_SNAPSHOT_KEYS = (
    'id', 'name', 'brand', 'image_url', 'url', 'ingredients', 'nutrition',
    'labels', 'categories', 'categories_tags', 'quantity', 'serving_size',
    'nutriscore', 'countries_tags', '_off_tags', '_source', '_smae_portion_g',
    '_smae_group', '_smae_subgroup', '_per_portion', '_usda_portion_g', '_usda_category',
    '_table_category', '_table_subgroup', '_table_portion_g', '_name_lang', '_reference_only',
    '_ingredients_tags_text', '_ingr_parsed_n', '_ingr_unknown_n', 'allergens_tags', 'traces_tags',
)


def _empty() -> dict:
    return {'recent': [], 'searches': [], 'safe': [], 'avoid': []}


def _clean(data) -> dict:
    out = _empty()
    if not isinstance(data, dict):
        return out
    for k in out:
        v = data.get(k)
        if isinstance(v, list):
            out[k] = [x for x in v if (isinstance(x, dict) if k != 'searches' else isinstance(x, str))]
    return out


def snapshot(product: dict) -> dict:
    """Minimal copy of a product, enough to re-open its verdict offline."""
    snap = {k: product[k] for k in _SNAPSHOT_KEYS if k in product and product[k] not in (None, '')}
    raw = product.get('_raw') or {}
    if isinstance(raw, dict) and raw.get('serving_quantity'):
        snap['_raw'] = {'serving_quantity': raw['serving_quantity']}
    snap['_needs_full_load'] = False
    return snap


def _entry(product: dict, status: str | None) -> dict:
    return {
        'id': str(product.get('id', '')),
        'name': product.get('name') or '',
        'brand': product.get('brand') or '',
        'status': status or 'unknown',
        'date': date.today().isoformat(),
        'source': product.get('_source') or 'off',
        'product': snapshot(product),
    }


def _state() -> dict:
    h = st.session_state.get('_history')
    if h is None:
        h = _empty()
        st.session_state['_history'] = h
    return h


def _touch() -> None:
    st.session_state['_hist_dirty'] = True


def flush() -> None:
    """Write pending changes to localStorage (renders a hidden JS component)."""
    if st.session_state.get('_hist_loaded') and st.session_state.pop('_hist_dirty', False):
        write_key(LS_KEY, _state())


def load_history() -> dict:
    """Load history from localStorage once per session; flush pending writes."""
    if not st.session_state.get('_hist_loaded'):
        ready, saved = read_key(LS_KEY)
        if not ready:
            return _state()  # never write before the stored copy has been merged
        if saved:
            # Merge: keep anything added this session before the read finished
            cur, disk = _state(), _clean(saved)
            for k in ('recent', 'safe', 'avoid'):
                ids = {e.get('id') for e in cur[k]}
                cur[k] = cur[k] + [e for e in disk[k] if e.get('id') not in ids]
            cur['searches'] = cur['searches'] + [q for q in disk['searches'] if q not in cur['searches']]
            cur['recent'] = cur['recent'][:MAX_RECENT]
            cur['searches'] = cur['searches'][:MAX_SEARCHES]
        st.session_state['_hist_loaded'] = True
    flush()
    return _state()


def add_viewed(product: dict, verdict_status: str | None) -> None:
    pid = str(product.get('id', ''))
    if not pid or pid == 'N/A':
        return
    h = _state()
    first = h['recent'][0] if h['recent'] else None
    entry = _entry(product, verdict_status)
    if first and first.get('id') == pid and first.get('status') == entry['status'] \
            and first.get('date') == entry['date']:
        return  # no-op on reruns: avoids rewriting localStorage every rerun
    h['recent'] = [entry] + [e for e in h['recent'] if e.get('id') != pid]
    h['recent'] = h['recent'][:MAX_RECENT]
    for name in _LISTS:  # keep list snapshots/status fresh
        for e in h[name]:
            if e.get('id') == pid:
                e['status'] = entry['status']
    _touch()


def add_search(q: str) -> None:
    q = (q or '').strip()
    if not q:
        return
    h = _state()
    if h['searches'] and h['searches'][0].lower() == q.lower():
        return
    h['searches'] = [q] + [s for s in h['searches'] if s.lower() != q.lower()]
    h['searches'] = h['searches'][:MAX_SEARCHES]
    _touch()


def get_searches(n: int = 8) -> list[str]:
    return list(_state()['searches'][:n])


def get_recent(n: int = 5) -> list[dict]:
    return list(_state()['recent'][:n])


def get_list(list_name: str) -> list[dict]:
    return list(_state().get(list_name, []))


def in_list(product: dict, list_name: str) -> bool:
    pid = str(product.get('id', ''))
    return any(e.get('id') == pid for e in _state().get(list_name, []))


def toggle_list(product: dict, list_name: str, verdict_status: str | None = None) -> bool:
    """Add/remove product from 'safe' or 'avoid'. Lists are mutually exclusive.
    Returns True if the product is now in the list."""
    if list_name not in _LISTS:
        return False
    pid = str(product.get('id', ''))
    if not pid:
        return False
    h = _state()
    if in_list(product, list_name):
        h[list_name] = [e for e in h[list_name] if e.get('id') != pid]
        _touch()
        return False
    other = 'avoid' if list_name == 'safe' else 'safe'
    h[other] = [e for e in h[other] if e.get('id') != pid]
    h[list_name] = ([_entry(product, verdict_status)]
                    + [e for e in h[list_name] if e.get('id') != pid])[:MAX_LIST]
    _touch()
    return True


def find_recent(product_id: str) -> dict | None:
    """History entry for a product id (recent, safe, then avoid), or None."""
    pid = str(product_id)
    h = _state()
    for k in ('recent', 'safe', 'avoid'):
        for e in h[k]:
            if e.get('id') == pid and e.get('product'):
                return e
    return None


def clear_history() -> None:
    st.session_state['_history'] = _empty()
    _touch()


def status_emoji(status: str | None) -> str:
    return {'ok': '🟢', 'no': '🔴'}.get(status or '', '🟡')
