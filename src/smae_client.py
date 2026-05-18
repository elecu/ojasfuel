"""
SMAE (Sistema Mexicano de Alimentos Equivalentes) local database client.
Used as the primary data source when the user selects Mexico.
"""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

_DB_PATH = Path(__file__).parent / "smae_db.json"

# Groups that are fully vegan (no animal products whatsoever)
_VEGAN_GROUPS = {
    "Verduras",
    "Frutas",
    "Leguminosas",
    "Alimentos Libres en Energía",
    "Bebidas Alcohólicas",
}

# Groups that depend on the subgroup for vegan classification
_VEGAN_SUBGROUP_RULES = {
    # Cereales: sin grasa = vegan; con grasa = unknown (fat may be animal)
    ("Cereales y Tubérculos", "Sin grasa"): (True, True),
    ("Cereales y Tubérculos", "Con grasa"): (None, None),
    # Aceites: sin proteína = vegan; con proteína = unknown (may have dairy/egg)
    ("Aceites y Grasas", "Sin proteína"): (True, True),
    ("Aceites y Grasas", "Con proteína"): (None, None),
    # Azúcares: sin grasa = vegan; con grasa = unknown
    ("Azúcares", "Sin grasa"): (True, True),
    ("Azúcares", "Con grasa"): (None, None),
    # Leche: all dairy → not vegan, vegetarian
    ("Leche", None): (False, True),
    ("Leche", "Descremada"): (False, True),
    ("Leche", "Semidescremada"): (False, True),
    ("Leche", "Entera"): (False, True),
    ("Leche", "Con azúcar"): (False, True),
    # Animal origin → not vegan, not vegetarian
    ("Alimentos de Origen Animal", None): (False, False),
    ("Alimentos de Origen Animal", "Muy bajo aporte de grasa"): (False, False),
    ("Alimentos de Origen Animal", "Bajo aporte de grasa"): (False, False),
    ("Alimentos de Origen Animal", "Moderado aporte de grasa"): (False, False),
    ("Alimentos de Origen Animal", "Alto aporte de grasa"): (False, False),
}


def _normalize(text: str) -> str:
    """Lowercase + strip accents for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _classify_by_group(group: str, subgroup: str | None) -> tuple[bool | None, bool | None]:
    """Return (is_vegan, is_vegetarian) based on food group."""
    if group in _VEGAN_GROUPS:
        return True, True
    key = (group, subgroup)
    if key in _VEGAN_SUBGROUP_RULES:
        return _VEGAN_SUBGROUP_RULES[key]
    # Try with None subgroup as fallback
    key2 = (group, None)
    if key2 in _VEGAN_SUBGROUP_RULES:
        return _VEGAN_SUBGROUP_RULES[key2]
    return None, None


@lru_cache(maxsize=1)
def _load_db() -> list[dict]:
    with open(_DB_PATH, encoding="utf-8") as f:
        return json.load(f)


def _smae_to_product(entry: dict) -> dict:
    """Convert SMAE entry to the same shape as api_client.format_product()."""
    group = entry.get("group", "")
    subgroup = entry.get("subgroup")
    is_vegan, is_vegetarian = _classify_by_group(group, subgroup)

    # Build nutrition dict using the same display keys as NUTRITION_FIELDS in api_client.py
    nutrition = {}
    _add = lambda key, val: nutrition.update({key: val}) if val is not None else None

    _add("Energy (kcal)", entry.get("energy_kcal"))
    _add("Protein (g)", entry.get("protein_g"))
    _add("Fat (g)", entry.get("fat_g"))
    _add("Saturated Fat (g)", entry.get("saturated_fat_g"))
    _add("Carbohydrates (g)", entry.get("carbs_g"))
    _add("Fiber (g)", entry.get("fiber_g"))
    _add("Vitamin A (µg)", entry.get("vitamin_a_ug"))
    _add("Vitamin C (mg)", entry.get("vitamin_c_mg"))
    _add("Vitamin B9 (µg)", entry.get("folate_ug"))
    _add("Iron (mg)", entry.get("iron_mg"))
    _add("Potassium (mg)", entry.get("potassium_mg"))
    _add("Calcium (mg)", entry.get("calcium_mg"))
    _add("Sodium (mg)", entry.get("sodium_mg"))
    _add("Cholesterol (mg)", entry.get("cholesterol_mg"))
    _add("Alcohol (g)", entry.get("alcohol_g"))

    portion = f"{entry.get('portion_amount', '')} {entry.get('portion_unit', '')}".strip()
    net_w = entry.get("net_weight_g")
    serving = f"{net_w}g" if net_w else ""

    # Use food name + group as ingredients hint so classifier.py blocklists work
    # e.g. "Alón de pollo" → classifier matches "pollo" → not vegan
    # "Leche entera" → classifier matches "leche" → not vegan
    ingredients_hint = f"{entry['name']} {group}"
    if subgroup:
        ingredients_hint += f" {subgroup}"

    label_parts = [f"Grupo SMAE: {group}"]
    if subgroup:
        label_parts.append(subgroup)
    if entry.get("glycemic_index") is not None:
        label_parts.append(f"IG: {entry['glycemic_index']}")

    return {
        "id": entry["id"],
        "name": entry["name"],
        "brand": "SMAE 4ta ed.",
        "ingredients": ingredients_hint,
        "image_url": None,
        "url": None,
        "nutrition": nutrition,
        "labels": ", ".join(label_parts),
        "categories": group,
        "quantity": portion,
        "serving_size": serving,
        "nutriscore": None,
        "countries_tags": ["en:mexico"],
        "_off_tags": {"is_vegan": is_vegan, "is_vegetarian": is_vegetarian},
        "_classification": None,
        "_needs_full_load": False,
        "_raw": entry,
        "_source": "smae",
    }


def search_by_name(query: str, page_size: int = 20) -> list[dict]:
    """Search SMAE database by food name. Returns formatted product dicts."""
    if not query or not query.strip():
        return []

    db = _load_db()
    q_norm = _normalize(query.strip())
    words = q_norm.split()

    results = []
    for entry in db:
        name_norm = _normalize(entry["name"])
        # All query words must appear in the food name
        if all(w in name_norm for w in words):
            results.append(entry)

    # Sort: exact matches first, then alphabetical
    def score(e):
        n = _normalize(e["name"])
        return (0 if n == q_norm else 1, n)

    results.sort(key=score)
    return [_smae_to_product(e) for e in results[:page_size]]


def search_by_barcode(_barcode: str) -> dict | None:
    """SMAE has no barcodes — always returns None."""
    return None
