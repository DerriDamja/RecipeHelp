"""Handles ingestion and processing of the recipe dataset"""

import json
import pandas as pd
from dataclasses import dataclass, field
from math import isnan

DATASET_URL = r"hf://datasets/datahiveai/recipes-with-nutrition/recipes-with-nutrition.csv"
JSON_COLS = [
    "diet_labels",
    "health_labels",
    "cautions",
    "cuisine_type",
    "meal_type",
    "dish_type",
    "ingredients",
    "total_nutrients",
]

@dataclass
class IngestionBundle:
    tables: dict[str, pd.DataFrame] = field(
        default_factory=dict
    )
    source: str = DATASET_URL


def fetch_dataset(dataset_url=DATASET_URL) -> pd.DataFrame:
    """Retrieves the recipe dataset specified by the DATASET_URL"""
    return pd.read_csv(dataset_url)


def _json_parse(val):
    """Safely parses JSON strings, lists, and dicts from CSVs"""
    if pd.isna(val):
        return [] if isinstance(val, list) else {}
    try:
        return json.loads(val) if isinstance(val, str) else val
    except json.JSONDecodeError, TypeError:
        return [] if isinstance(val, str) and val.strip().startswith('[') else {}


def _flatten_json_list(df: pd.DataFrame, col: str, item_key: str = "") -> list[str]:
    """Extracts unique strings from a JSON array"""
    items = []
    for row in df[col]:
        if isinstance(row, list):
            for val in row:
                if item_key:
                    items.append(val.get(item_key, "") if isinstance(val, dict) else val)
                else:
                    items.append(val)
    return items


def _make_recipe_junction(df: pd.DataFrame, col: str, key_col: str) -> pd.DataFrame:
    """
    Creates a basic recipe junction DataFrame.
    Appropriate when no additional attributes are stored.
    """
    if not col in df.columns:
        raise KeyError(f"Column {col} does not exist in the DataFrame")
    
    records = []
    for row in df.itertuples():
        temp_id = row.temp_recipe_id

        for item in getattr(row, col):
            if not isinstance(item, str):
                continue

            records.append({
                "temp_recipe_id": temp_id,
                key_col: item,
            })
    return pd.DataFrame(records)


def transform_dataset(df: pd.DataFrame) -> IngestionBundle:
    """Processes the recipe dataset to ensure existence of necessary information."""

    for col in JSON_COLS:
        df[col] = df[col].apply(_json_parse)

    # Temporary ID for processing purposes, not used in the DB
    df.insert(0, "temp_recipe_id", range(1, len(df) + 1))

    bundle = IngestionBundle()

    # Recipes
    recipe_df = df[[
        "temp_recipe_id",
        "recipe_name",
        "source",
        "url",
        "image_url",
        "calories",
        "servings",
        "total_weight_g",
    ]].copy()
    recipe_df = recipe_df.rename(columns={"source": "source_name"})
    recipe_df = recipe_df.rename(columns={"url": "source_url"})
    recipe_df["servings"] = pd.to_numeric(recipe_df["servings"], errors="coerce")
    recipe_df["total_weight_g"] = pd.to_numeric(recipe_df["total_weight_g"], errors="coerce")
    bundle.tables["recipes"] = recipe_df.dropna(subset=[
        "recipe_name",
        "source_name",
        "source_url",
        "calories",
        "total_weight_g",
    ])

    # Properties
    bundle.tables["diets"] = pd.DataFrame(_flatten_json_list(df, "diet_labels"), columns=["diet_name"]).drop_duplicates()
    bundle.tables["health_labels"] = pd.DataFrame(_flatten_json_list(df, "health_labels"), columns=["health_label_name"]).drop_duplicates()
    bundle.tables["cautions"] = pd.DataFrame(_flatten_json_list(df, "cautions"), columns=["caution_name"]).drop_duplicates()
    bundle.tables["cuisines"] = pd.DataFrame(_flatten_json_list(df, "cuisine_type"), columns=["cuisine_name"]).drop_duplicates()
    bundle.tables["meal_types"] = pd.DataFrame(_flatten_json_list(df, "meal_type"), columns=["meal_type_name"]).drop_duplicates()
    bundle.tables["dish_types"] = pd.DataFrame(_flatten_json_list(df, "dish_type"), columns=["dish_type_name"]).drop_duplicates()

    # Ingredients (and Recipe-Ingredient Junction)
    recipe_ing_records = {}
    for row in df.itertuples():
        ingredients = getattr(row, "ingredients", [])
        if not isinstance(ingredients, list):
            continue

        temp_id = row.temp_recipe_id
        for ing in ingredients:
            if not isinstance(ing, dict) or not {"food", "text", "weight"}.issubset(ing.keys()):
                continue

            ing_name = ing["food"]
            original_text = ing["text"]

            if not ing_name or not original_text or ing.get("weight") is None:
                continue

            ing_key = (temp_id, ing_name)

            if ing_key not in recipe_ing_records:
                measure = ing.get("measure")
                measure = None if measure == "<unit>" else measure
                quantity = float(ing.get("quantity", 0))

                recipe_ing_records[ing_key] = {
                    "temp_recipe_id": temp_id,
                    "ingredient_name": ing["food"].lower(),
                    "original_text": ing["text"],
                    "measure": measure,
                    "quantity": quantity if quantity > 0 else None,
                    "weight_g": float(ing["weight"]),
                }
            else:
                # Aggregates text and weight for duplicate ingredient listings
                recipe_ing_records[ing_key]["original_text"] += f", {original_text}"
                recipe_ing_records[ing_key]["weight_g"] += float(ing["weight"])
                recipe_ing_records[ing_key]["measure"] = None
                recipe_ing_records[ing_key]["quantity"] = None

    bundle.tables["recipe_ingredients"] = pd.DataFrame(recipe_ing_records.values())
    bundle.tables["ingredients"] = bundle.tables["recipe_ingredients"][["ingredient_name"]].drop_duplicates()

    # Nutrients (and Recipe-Nutrients Junction)
    recipe_nutrient_records = []
    for row in df.itertuples():
        nutrients = getattr(row, "total_nutrients", {})
        if not isinstance(nutrients, dict):
            continue

        temp_id = row.temp_recipe_id
        for tag, data in nutrients.items():
            if not isinstance(data, dict) or not {"label", "unit"}.issubset(data.keys()):
                continue

            quantity = float(data.get("quantity", 0))
            recipe_nutrient_records.append({
                "temp_recipe_id": temp_id,
                "nutrient_name": data["label"],
                "nutrient_tag": tag.upper(),
                "unit": data["unit"],
                "quantity": quantity if quantity > 0 else None
            })
    bundle.tables["recipe_nutrients"] = pd.DataFrame(recipe_nutrient_records)
    bundle.tables["nutrients"] = bundle.tables["recipe_nutrients"][["nutrient_tag", "nutrient_name", "unit"]].drop_duplicates()

    # Recipe Properties
    bundle.tables["recipe_diets"] = _make_recipe_junction(df, "diet_labels", "diet_name")
    bundle.tables["recipe_health_labels"] = _make_recipe_junction(df, "health_labels", "health_label_name")
    bundle.tables["recipe_cautions"] = _make_recipe_junction(df, "cautions", "caution_name")
    bundle.tables["recipe_cuisines"] = _make_recipe_junction(df, "cuisine_type", "cuisine_name")
    bundle.tables["recipe_meal_types"] = _make_recipe_junction(df, "meal_type", "meal_type_name")
    bundle.tables["recipe_dish_types"] = _make_recipe_junction(df, "dish_type", "dish_type_name")

    return bundle


def frame_to_rows(df: pd.DataFrame):
    for row in df.itertuples(index=False, name=None):
        cleaned_row = []
        for val in row:
            # Converts NaN values to None so psycopg inserts NULL rather than NaN
            if isinstance(val, float) and isnan(val):
                cleaned_row.append(None)
            else:
                cleaned_row.append(val)
        yield cleaned_row


if __name__ == "__main__":
    print("Fetching...")
    df = fetch_dataset()
    print("Fetched")
    bundle = transform_dataset(df)
    print("transformed")
    pd.set_option("display.max_columns", None)
    for table, frame in bundle.tables.items():
        rows = frame_to_rows(frame)
        print(f"{table}: {frame.head(50)}")
        for i in range(50):
            print(f"{table}: {next(rows)}")
