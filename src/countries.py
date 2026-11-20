"""
Country options shared by Settings, onboarding and the home quick switcher.

Each id → {tags, cc}. cc = OFF country code (country subdomain, better
coverage); tags = client-side post-filter on countries_tags.
"""

import copy

from src.i18n import t

COUNTRIES = {
    'all': {'tags': [], 'cc': None},
    'mx': {'tags': ['en:mexico'], 'cc': 'mx'},
    'us': {'tags': ['en:united-states'], 'cc': 'us'},
    'gb': {'tags': ['en:united-kingdom'], 'cc': 'gb'},
    'es': {'tags': ['en:spain'], 'cc': 'es'},
    'fr': {'tags': ['en:france'], 'cc': 'fr'},
    'de': {'tags': ['en:germany'], 'cc': 'de'},
    'it': {'tags': ['en:italy'], 'cc': 'it'},
    'nl': {'tags': ['en:netherlands'], 'cc': 'nl'},
    'be': {'tags': ['en:belgium'], 'cc': 'be'},
    'ch': {'tags': ['en:switzerland'], 'cc': 'ch'},
    'pt': {'tags': ['en:portugal'], 'cc': 'pt'},
    'pl': {'tags': ['en:poland'], 'cc': 'pl'},
    'europe': {'tags': [
        'en:united-kingdom', 'en:france', 'en:germany', 'en:italy', 'en:spain',
        'en:netherlands', 'en:belgium', 'en:switzerland', 'en:portugal', 'en:poland',
        'en:austria', 'en:sweden', 'en:denmark', 'en:norway', 'en:finland',
    ], 'cc': None},
}

MAX_RECENT_COUNTRIES = 4


def country_name(cid: str) -> str:
    return t('country_all_opt') if cid == 'all' else t(f'country_{cid}')


def country_cid(setting) -> str:
    """Map a stored countries setting back to its id ('all' if unknown)."""
    if isinstance(setting, list):  # backward compat: old format was a plain list
        setting = {'tags': setting, 'cc': None}
    setting = setting or {}
    for cid, v in COUNTRIES.items():
        if v['cc'] == setting.get('cc') and sorted(v['tags']) == sorted(setting.get('tags', [])):
            return cid
    return 'all'


def ordered_ids(recent: list | None) -> list[str]:
    """Recently used countries first (traveller-friendly), then the rest."""
    recent = [c for c in (recent or []) if c in COUNTRIES]
    return recent + [c for c in COUNTRIES if c not in recent]


def apply_country(settings: dict, cid: str) -> None:
    """Set the active country and remember it in the recent list."""
    if cid not in COUNTRIES:
        return
    settings['countries'] = copy.deepcopy(COUNTRIES[cid])
    recent = [c for c in settings.get('recent_countries', []) if c != cid]
    settings['recent_countries'] = ([cid] + recent)[:MAX_RECENT_COUNTRIES]
