"""Handles common unit conversions for ingredient and nutrition measures"""

MASS_FACTORS = {
    'g': 1,
    "mg": 1_000,
    "mcg": 1_000_000,
    "µg": 1_000_000,
}


def convert_mass(quantity: float, from_unit: str, to_unit: str) -> float:
    """Converts between weight measures (g, mg, mcg/µg)"""
    from_unit = from_unit.strip().lower()
    to_unit = to_unit.strip().lower()
    if from_unit not in MASS_FACTORS:
        raise ValueError(f"{from_unit} is not a supported source unit")
    if to_unit not in MASS_FACTORS:
        raise ValueError(f"{to_unit} is not a supported target unit")

    grams = quantity / MASS_FACTORS[from_unit]
    return grams * MASS_FACTORS[to_unit]