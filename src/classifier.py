"""
ProductClassifier — regex-based vegan/vegetarian classification.
Supports additional dietary filters via the `filters` dict from Settings.
"""

import re
from src.blocklists import (
    MEAT_FISH, DAIRY, EGGS, EGGS_TRACES, GELATIN, HONEY,
    ALCOHOL, CAFFEINE, MUSHROOMS, ONION, GARLIC, JAIN_EXTRAS,
)


def _find_matches(text: str, patterns: list[str]) -> list[str]:
    """Return actual matched substrings from text for each pattern that hits."""
    found = []
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            found.append(m.group(0))
    return found


class ProductClassifier:
    def classify(self, ingredients_text: str, filters: dict = None, **_kwargs) -> dict:
        """
        Classify a product by its ingredients text (and optionally product name).

        Returns:
            is_vegan (bool)
            is_vegetarian (bool)
            passes_filters (bool) — True if product passes user's active filters
            violations (list[str]) — filter violations (human-readable)
            confidence (float) — 0.0-1.0
            reason (str) — short explanation
            animal_products_found (list[str])
            dairy_or_eggs_found (list[str])
        """
        if filters is None:
            filters = {}

        no_ingredients = not ingredients_text or ingredients_text.strip() in ('', 'N/A', 'n/a')

        if no_ingredients:
            return {
                'is_vegan': None,
                'is_vegetarian': None,
                'passes_filters': None,
                'violations': [],
                'confidence': 0.0,
                'reason': 'No ingredients data available',
                'animal_products_found': [],
                'dairy_or_eggs_found': [],
            }

        name_scan = False

        text = ingredients_text.lower()

        meat_found = _find_matches(text, MEAT_FISH)
        dairy_found = _find_matches(text, DAIRY)
        eggs_found = _find_matches(text, EGGS)
        gelatin_found = _find_matches(text, GELATIN)
        honey_found = _find_matches(text, HONEY)

        animal_products_found = meat_found + gelatin_found
        dairy_or_eggs_found = dairy_found + eggs_found

        # --- Core classification ---
        is_vegetarian = not bool(meat_found or gelatin_found)
        is_vegan = is_vegetarian and not bool(dairy_found or eggs_found or honey_found)

        if meat_found:
            reason = f"Contains meat/fish: {', '.join(meat_found[:3])}"
            confidence = 0.98
        elif gelatin_found:
            reason = f"Contains animal-derived gelatin/additive: {', '.join(gelatin_found[:3])}"
            confidence = 0.95
        elif dairy_found or eggs_found:
            items = (dairy_found + eggs_found)[:3]
            reason = f"Vegetarian (contains dairy/eggs): {', '.join(items)}"
            confidence = 0.95
        elif honey_found:
            reason = f"Not vegan (contains honey): {', '.join(honey_found[:3])}"
            confidence = 0.90
        else:
            reason = "No animal products detected"
            confidence = 0.88

        # --- Apply user filters ---
        violations = []
        mode = filters.get('mode', 'vegetarian')

        if mode == 'vegan' and not is_vegan:
            if not is_vegetarian:
                violations.append("Contains meat/fish")
            if dairy_found:
                violations.append(f"Contains dairy: {', '.join(dairy_found[:2])}")
            if eggs_found:
                violations.append(f"Contains eggs: {', '.join(eggs_found[:2])}")
            if honey_found:
                violations.append(f"Contains honey")
        elif mode == 'vegetarian' and not is_vegetarian:
            violations.append(f"Contains meat/fish: {', '.join(meat_found[:2])}")

        # Lacto/Ovo variants
        if filters.get('ovo') and dairy_found:
            violations.append(f"Ovo-vegetarian: contains dairy: {', '.join(dairy_found[:2])}")
        if filters.get('lacto') and eggs_found:
            violations.append(f"Lacto-vegetarian: contains eggs: {', '.join(eggs_found[:2])}")

        # Strict egg traces
        if filters.get('strict_egg_traces'):
            traces = _find_matches(text, EGGS_TRACES)
            if traces:
                violations.append("Contains egg traces (strict mode active)")

        # Additional restrictions
        if filters.get('no_alcohol'):
            matches = _find_matches(text, ALCOHOL)
            if matches:
                violations.append(f"Contains alcohol: {', '.join(matches[:2])}")

        if filters.get('no_caffeine'):
            matches = _find_matches(text, CAFFEINE)
            if matches:
                violations.append(f"Contains caffeine: {', '.join(matches[:2])}")

        if filters.get('no_mushrooms'):
            matches = _find_matches(text, MUSHROOMS)
            if matches:
                violations.append(f"Contains mushrooms: {', '.join(matches[:2])}")

        if filters.get('no_onion'):
            matches = _find_matches(text, ONION)
            if matches:
                violations.append(f"Contains onion: {', '.join(matches[:2])}")

        if filters.get('no_garlic'):
            matches = _find_matches(text, GARLIC)
            if matches:
                violations.append(f"Contains garlic: {', '.join(matches[:2])}")

        if filters.get('no_gelatin') and gelatin_found:
            violations.append(f"Contains gelatin: {', '.join(gelatin_found[:2])}")

        if filters.get('jain'):
            extras = _find_matches(text, JAIN_EXTRAS)
            if extras:
                violations.append(f"Jain diet: contains root vegetables: {', '.join(extras[:3])}")
            garlic_m = _find_matches(text, GARLIC)
            onion_m = _find_matches(text, ONION)
            if garlic_m:
                violations.append(f"Jain diet: contains garlic")
            if onion_m:
                violations.append(f"Jain diet: contains onion")

        passes_filters = len(violations) == 0

        return {
            'is_vegan': is_vegan,
            'is_vegetarian': is_vegetarian,
            'passes_filters': passes_filters,
            'violations': violations,
            'confidence': confidence,
            'reason': reason,
            'animal_products_found': animal_products_found,
            'dairy_or_eggs_found': dairy_or_eggs_found,
        }
