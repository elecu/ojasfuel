#!/usr/bin/env python3
"""
Parse SMAE PDF (Sistema Mexicano de Alimentos Equivalentes, 4ta edición 2014)
into a structured JSON database.

Usage: python scripts/parse_smae.py
Output: src/smae_db.json

Column schemas per group (after gross_weight, net_weight):
  Verduras/Frutas/Cereales/Leguminosas:
    energy, protein, fat, carbs, fiber, vitA, vitC, folate, iron_nohem, potassium, GI, GL

  Alimentos de Origen Animal:
    energy, protein, fat, carbs, cholesterol, vitA, calcium, iron, sodium, [potassium?]

  Leche (all subtypes):
    energy, protein, fat, carbs, cholesterol, vitA, calcium, sodium, [azucar_equiv?]

  Aceites y Grasas sin proteína:
    energy, protein, fat, carbs, AG_sat, AG_mono?, cholesterol?, sodium?

  Aceites y Grasas con proteína:
    energy, protein, fat, carbs, AG_sat, ..., cholesterol, sodium

  Azúcares / Alimentos Libres / Bebidas:
    variable — energy, protein, fat, carbs + extras
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PDF_PATH = ROOT / "src" / "SMAE.pdf"
OUT_PATH = ROOT / "src" / "smae_db.json"

# (regex_pattern, group_name, subgroup_name)
# Order matters: more specific patterns first
GROUP_PATTERNS = [
    (r"ALIMENTOS\s+DE\s+ORIGEN\s+ANIMAL\s+MUY\s+BAJO\s+APORTE\s+DE\s+GRASA",
     "Alimentos de Origen Animal", "Muy bajo aporte de grasa"),
    (r"ALIMENTOS\s+DE\s+ORIGEN\s+ANIMAL\s+BAJO\s+APORTE\s+DE\s+GRASA",
     "Alimentos de Origen Animal", "Bajo aporte de grasa"),
    (r"ALIMENTOS\s+DE\s+ORIGEN\s+ANIMAL\s+MODERADO\s+APORTE\s+DE\s+GRASA",
     "Alimentos de Origen Animal", "Moderado aporte de grasa"),
    (r"ALIMENTOS\s+DE\s+ORIGEN\s+ANIMAL\s+ALTO\s+APORTE\s+DE\s+GRASA",
     "Alimentos de Origen Animal", "Alto aporte de grasa"),
    (r"LECHE\s+SEMI\s*DESCREMADA", "Leche", "Semidescremada"),
    (r"LECHE\s+D[EI]S?C?R?E?M?A?D?A", "Leche", "Descremada"),
    (r"LECHE\s+ENTERA", "Leche", "Entera"),
    (r"LECHE\s+CON\s+AZ", "Leche", "Con azúcar"),
    (r"ACEITES\s+Y\s+GRASAS\s+CON\s+PROTE", "Aceites y Grasas", "Con proteína"),
    (r"ACEITES\s+Y\s+GRASAS", "Aceites y Grasas", "Sin proteína"),
    (r"AZ.CARES\s+SIN\s+GRASA", "Azúcares", "Sin grasa"),
    (r"AZ.CARES\s+CON\s+GRASA", "Azúcares", "Con grasa"),
    (r"A\s*L\s*.\s*M\s*E\s*N\s*T\s*O\s*S\s+LIBRES\s+EN\s+ENERG",
     "Alimentos Libres en Energía", None),
    (r"BEBIDAS\s+ALC", "Bebidas Alcohólicas", None),
    (r"CEREALES\s+(?:Y\s+TUB.RCULOS\s+)?SIN\s+G", "Cereales y Tubérculos", "Sin grasa"),
    (r"CEREALES\s+(?:Y\s+TUB.RCULOS\s+)?CON\s+GRASA", "Cereales y Tubérculos", "Con grasa"),
    (r"LEGUMINOSAS", "Leguminosas", None),
    (r"^VERDURAS$", "Verduras", None),
    (r"^FRUTAS$", "Frutas", None),
]

# Canonical nutrition field names mapped to their column index (0-based, after gross/net)
# Index 0 = gross_weight, 1 = net_weight, 2 = energy_kcal, 3 = protein_g, 4 = fat_g, 5 = carbs_g
# These 6 are consistent across ALL sections

SCHEMA_PLANT = {
    "gross_weight_g": 0,
    "net_weight_g": 1,
    "energy_kcal": 2,
    "protein_g": 3,
    "fat_g": 4,
    "carbs_g": 5,
    "fiber_g": 6,
    "vitamin_a_ug": 7,
    "vitamin_c_mg": 8,
    "folate_ug": 9,
    "iron_mg": 10,
    "potassium_mg": 11,
    "glycemic_index": 12,
    "glycemic_load": 13,
}

SCHEMA_ANIMAL = {
    "gross_weight_g": 0,
    "net_weight_g": 1,
    "energy_kcal": 2,
    "protein_g": 3,
    "fat_g": 4,
    "carbs_g": 5,
    "cholesterol_mg": 6,
    "vitamin_a_ug": 7,
    "calcium_mg": 8,
    "iron_mg": 9,
    "sodium_mg": 10,
    "potassium_mg": 11,
}

SCHEMA_MILK = {
    "gross_weight_g": 0,
    "net_weight_g": 1,
    "energy_kcal": 2,
    "protein_g": 3,
    "fat_g": 4,
    "carbs_g": 5,
    "cholesterol_mg": 6,
    "vitamin_a_ug": 7,
    "calcium_mg": 8,
    "sodium_mg": 9,
}

SCHEMA_FATS = {
    "gross_weight_g": 0,
    "net_weight_g": 1,
    "energy_kcal": 2,
    "protein_g": 3,
    "fat_g": 4,
    "carbs_g": 5,
    "saturated_fat_g": 6,
    "monounsat_fat_g": 7,
    "cholesterol_mg": 8,
    "sodium_mg": 9,
}

SCHEMA_SUGARS = {
    "gross_weight_g": 0,
    "net_weight_g": 1,
    "energy_kcal": 2,
    "protein_g": 3,
    "fat_g": 4,
    "carbs_g": 5,
}

SCHEMA_ALCOHOL = {
    "gross_weight_g": 0,
    "net_weight_g": 1,
    "energy_kcal": 2,
    "carbs_g": 3,
    "alcohol_g": 4,
}

GROUP_SCHEMAS = {
    "Verduras": SCHEMA_PLANT,
    "Frutas": SCHEMA_PLANT,
    "Cereales y Tubérculos": SCHEMA_PLANT,
    "Leguminosas": SCHEMA_PLANT,
    "Alimentos de Origen Animal": SCHEMA_ANIMAL,
    "Leche": SCHEMA_MILK,
    "Aceites y Grasas": SCHEMA_FATS,
    "Azúcares": SCHEMA_SUGARS,
    "Alimentos Libres en Energía": SCHEMA_SUGARS,
    "Bebidas Alcohólicas": SCHEMA_ALCOHOL,
}

# Known units — used to identify the unit token
UNITS = {
    "taza", "tazas", "pieza", "piezas", "g", "ml", "oz",
    "cucharada", "cucharadas", "cucharadita", "cucharaditas",
    "cdas", "cdita", "cditas", "cda",
    "porción", "porciones", "rebanada", "rebanadas",
    "barra", "barras", "sobre", "cajita", "envase", "lata",
    "cápsula", "capsula", "cápsulas", "capsulas",
    "tarro", "copa", "botella",
}

# Compound units that span multiple tokens
COMPOUND_UNITS = [
    "tarro o lata",
    "rebanada delgada",
    "rebanada gruesa",
    "disparo de un segundo",
    "disp. de un segundo",
]


def detect_group(line: str):
    """Return (group, subgroup) if line is a section header, else None."""
    clean = re.sub(r"\s+", " ", line.strip()).upper()
    # Remove OCR artifacts at start (single chars like "O", "NJ", "i", "D")
    clean = re.sub(r"^[A-Z0-9]{1,2}\s+", "", clean)
    for pattern, group, subgroup in GROUP_PATTERNS:
        if re.search(pattern, clean):
            return group, subgroup
    return None


def is_likely_header(line: str) -> bool:
    """Check if line looks like a section header (high caps ratio, reasonable length)."""
    stripped = line.strip()
    if not stripped or len(stripped) > 150:
        return False
    # Remove OCR prefix chars
    clean = re.sub(r"^[A-Za-z0-9]{1,2}\s+", "", stripped)
    upper_ratio = sum(1 for c in clean if c.isupper()) / max(len(clean), 1)
    return upper_ratio > 0.45


def parse_numeric(val: str):
    v = val.strip().replace(" ", "")
    if not v or v.upper() in ("ND", "N.D.", "N.D", "ND."):
        return None
    v = re.sub(r"\bO\b", "0", v)  # OCR: O → 0
    v = re.sub(r"[,/][^.]*$", "", v)  # Remove OCR artifacts like "22/7"
    try:
        return float(v)
    except ValueError:
        return None


def is_data_row(tokens: list[str]) -> bool:
    """Heuristic: row has food name + amount + unit + ≥4 numeric/ND values."""
    if len(tokens) < 4:
        return False
    numeric_count = sum(
        1 for t in tokens[-12:]
        if re.match(r"^[\d.]+$", t.replace("O", "0")) or t.upper() in ("ND", "N.D.", "N.D", "ND.")
    )
    return numeric_count >= 4


def parse_amount_and_unit(tokens: list[str]) -> tuple[str, str, list[str]]:
    """Extract (amount, unit, remaining) from tokens."""
    i = 0
    amount_parts = []

    while i < len(tokens):
        t = tokens[i]
        if re.match(r"^\d+/\d+$", t) or re.match(r"^\d+$", t):
            amount_parts.append(t)
            i += 1
            if i < len(tokens) and re.match(r"^\d+/\d+$", tokens[i]):
                amount_parts.append(tokens[i])
                i += 1
            break
        else:
            break

    if not amount_parts:
        return "", "", tokens

    amount = " ".join(amount_parts)

    # Check for compound units first (look ahead at next 3 tokens)
    remaining_str = " ".join(tokens[i:i+4]).lower()
    unit = ""
    skip = 0
    for cu in COMPOUND_UNITS:
        if remaining_str.startswith(cu):
            unit = cu
            skip = len(cu.split())
            break

    if unit:
        i += skip
    else:
        # Single unit token
        unit_parts = []
        while i < len(tokens):
            t = tokens[i].lower()
            if t in UNITS or (re.match(r"^[a-záéíóúüñ]+\.?$", tokens[i].lower()) and len(tokens[i]) > 1):
                unit_parts.append(tokens[i])
                i += 1
                if i < len(tokens) and tokens[i].lower() in {"delgada", "delgado", "grande", "pequeño", "mediano"}:
                    unit_parts.append(tokens[i])
                    i += 1
                break
            else:
                break
        unit = " ".join(unit_parts) if unit_parts else ""

    return amount, unit, tokens[i:]


def extract_food_and_portion(tokens: list[str]) -> tuple[str, str, str, list[str]] | None:
    """Find split between food name and amount+unit+data.
    Returns (name, amount, unit, numeric_tokens) or None."""
    # Try each token position as start of amount (food name = 1-7 tokens)
    max_split = min(len(tokens) - 4, 8)  # need at least 4 after name (amount, unit, 2 nums)
    for split in range(1, max(max_split, 2)):
        name_tokens = tokens[:split]
        rest = tokens[split:]
        amount, unit, remaining = parse_amount_and_unit(rest)
        if not amount or not unit:
            continue
        # Need at least 4 numeric values remaining (gross, net, energy, carbs min)
        numeric_count = sum(
            1 for t in remaining
            if re.match(r"^[\d.]+$", t.replace("O", "0").split("/")[0])
            or t.upper() in ("ND", "N.D.", "N.D", "ND.")
        )
        if numeric_count >= 4:
            return " ".join(name_tokens), amount, unit, remaining

    return None


def build_entry(name: str, amount: str, unit: str, raw_vals: list,
                group: str, subgroup: str | None, entry_id: int) -> dict:
    schema = GROUP_SCHEMAS.get(group, SCHEMA_SUGARS)

    entry = {
        "id": f"smae_{entry_id:04d}",
        "name": name.strip(),
        "group": group,
        "subgroup": subgroup,
        "portion_amount": amount,
        "portion_unit": unit,
        "edition": "4ta edición 2014",
    }

    for field, idx in schema.items():
        entry[field] = raw_vals[idx] if idx < len(raw_vals) else None

    return entry


def parse_pdf(pdf_path: Path) -> list[dict]:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print(f"pdftotext error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    lines = result.stdout.splitlines()
    entries = []
    entry_id = 1
    current_group = None
    current_subgroup = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect section header
        if is_likely_header(line):
            group_match = detect_group(stripped)
            if group_match:
                g, s = group_match
                current_group = g
                current_subgroup = s
                continue

        if current_group is None:
            continue

        # Skip obvious header rows
        if re.search(r"ALIMENTO|Energía|Proteína|Lípidos|Hidratos|Peso neto|Peso bruto|"
                     r"Vitamina|Calcio|Hierro|Sodio|Fibra|Colesterol|Fólico|Potasio|"
                     r"glicémico|glicémica|sugerida|redondeado|carbono", stripped):
            continue

        # Tokenize: split on 2+ whitespace
        tokens = re.split(r"\s{2,}", stripped)
        tokens = [t.strip() for t in tokens if t.strip()]

        if len(tokens) < 4:
            continue

        if not is_data_row(tokens):
            continue

        parsed = extract_food_and_portion(tokens)
        if not parsed:
            continue

        name, amount, unit, num_tokens = parsed

        # Sanity: name should not start with digit, be at least 2 chars
        if len(name) < 2 or name[0].isdigit():
            continue
        # Sanity: amount should be numeric-like
        if not re.match(r"^\d", amount):
            continue

        # Parse numeric values
        raw_vals = []
        for t in num_tokens:
            t = t.strip()
            if not t:
                continue
            if t.upper() in ("ND", "N.D.", "N.D", "ND."):
                raw_vals.append(None)
            else:
                v = parse_numeric(t)
                if v is not None or re.match(r"^[\dO.]", t):
                    raw_vals.append(v)

        if len(raw_vals) < 4:
            continue

        entry = build_entry(name, amount, unit, raw_vals,
                            current_group, current_subgroup, entry_id)
        entries.append(entry)
        entry_id += 1

    return entries


def main():
    print(f"Parsing {PDF_PATH} ...", file=sys.stderr)
    entries = parse_pdf(PDF_PATH)
    print(f"Parsed {len(entries)} entries", file=sys.stderr)

    from collections import Counter
    groups = Counter(e["group"] for e in entries)
    for g, n in sorted(groups.items()):
        print(f"  {g}: {n}", file=sys.stderr)

    print("\nSamples:", file=sys.stderr)
    for e in entries[:2]:
        print(f"  {e['id']} | {e['group']} | {e['name']} | "
              f"{e['portion_amount']} {e['portion_unit']} | "
              f"{e.get('energy_kcal')} kcal", file=sys.stderr)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"\nWritten {len(entries)} entries to {OUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
