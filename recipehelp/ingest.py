"""Handles ingestion and processing of the recipe dataset"""

import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

DATASET_URL = r"hf://datasets/datahiveai/recipes-with-nutrition/recipes-with-nutrition.csv"
JSON_COLS = [
    "diet_labels",
    "health_labels",
    "cautions",
    "cuisine_type",
    "meal_type",
    "dish_type",
    "ingredients",
    "total_nutritients",
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
    """Creates a junction DataFrame between two relation frames"""
    records = []
    for _, row in df.iterrows():
        recipe_name, source = row["recipe_name"], row["source"]
        for item in row.get(col, []):
            if isinstance(item, str):
                records.append({
                    "recipe_name": recipe_name,
                    "source": source,
                    key_col: item
                })
    return pd.DataFrame(records)


def transform_dataset() -> IngestionBundle:
    """Processes the recipe dataset to ensure existence of necessary information."""
    df: pd.DataFrame = fetch_dataset()

    for col in JSON_COLS:
        df[col] = df[col].apply(_json_parse)

    bundle = IngestionBundle()

    # Recipe Sources
    source_df = df[["source", "url"]].rename(columns={"source": "source_name", "url": "source_url"})
    bundle.tables["recipe_sources"] = source_df.dropna(subset=["source_name"])

    # Recipes
    recipe_df = df[["recipe_name", "source", "image_url", "servings", "total_weight_g"]].copy()
    recipe_df.rename(columns={"source": "source_name"}, inplace=True)
    recipe_df["servings"] = pd.to_numeric(recipe_df["servings"], errors="coerce")
    recipe_df["total_weight_g"] = pd.to_numeric(recipe_df["total_weight_g"], errors="coerce")
    bundle.tables["recipes"] = recipe_df

    # Recipe Properties
    bundle.tables["diets"] = pd.DataFrame(_flatten_json_list(df, "diet_labels"), columns=["diet_name"]).drop_duplicates()
    bundle.tables["health_labels"] = pd.DataFrame(_flatten_json_list(df, "health_labels"), columns=["health_label_name"]).drop_duplicates()
    bundle.tables["cautions"] = pd.DataFrame(_flatten_json_list(df, "cautions"), columns=["caution_name"]).drop_duplicates()
    bundle.tables["cuisines"] = pd.DataFrame(_flatten_json_list(df, "cuisine_type"), columns=["cuisine_name"]).drop_duplicates()
    bundle.tables["meal_types"] = pd.DataFrame(_flatten_json_list(df, "meal_type"), columns=["meal_type_name"]).drop_duplicates()
    bundle.tables["dish_types"] = pd.DataFrame(_flatten_json_list(df, "dish_type"), columns=["dish_type_name"]).drop_duplicates()

    # Ingredients (and Recipe-Ingredient Junction)
    ing_records = []
    for _, row in df.iterrows():
        recipe_name, source = row["recipe_name"], row["source"]
        for ing in row.get("ingredients", []):
            if isinstance(ing, dict):
                ing_records.append({
                    "recipe_name": recipe_name,
                    "source": source,
                    "ingredient_name": ing.get("food", ""),
                    "original_text": ing.get("text", ""),
                    "measure": ing.get("measure"),
                    "quantity": float(ing["quantity"]) if "quantity" in ing else None,
                    "weight_g": float(ing["weight"]) if "weight" in ing else None,
                })
    bundle.tables["recipe_ingredients"] = pd.DataFrame(ing_records)
    bundle.tables["ingredients"] = bundle.tables["recipe_ingredients"]["ingredient_name"].drop_duplicates().to_frame()

    # Nutrients (and Recipe-Nutrients Junction)
    nutrient_records = []
    for _, row in df.iterrows():
        recipe_name, source = row["recipe_name"], row["source"]
        for tag, data in row.get("total_nutrients", {}).items():
            if isinstance(data, dict):
                quantity = float(data.get("quantity", 0))
                nutrient_records.append({
                    "recipe_name": recipe_name,
                    "source": source,
                    "nutrient_tag": tag,
                    "nutrient_name": data.get("label", ""),
                    "unit": data.get("unit", ""),
                    "quantity": quantity if quantity > 0 else None
                })
    bundle.tables["recipe_nutrients"] = pd.DataFrame(nutrient_records)
    bundle.tables["nutrients"] = bundle.tables["recipe_nutrients"][["nutrient_tag", "nutrient_name", "unit"]].drop_duplicates()

    bundle.tables["recipe_diets"] = _make_recipe_junction(df, "diet_labels", "diet_name")
    bundle.tables["recipe_health_labels"] = _make_recipe_junction(df, "health_labels", "health_label_name")
    bundle.tables["recipe_cautions"] = _make_recipe_junction(df, "cautions", "caution_name")
    bundle.tables["recipe_cuisines"] = _make_recipe_junction(df, "cuisine_type", "cuisine_name")
    bundle.tables["recipe_meal_types"] = _make_recipe_junction(df, "meal_type", "meal_type_name")
    bundle.tables["recipe_dish_types"] = _make_recipe_junction(df, "dish_type", "dish_type_name")

    return bundle


def frame_to_rows(df: pd.DataFrame):
    """Converts DataFrames to a list of tuples, replacing any NaN with None for psycopg compat"""
    cleaned = df.where(pd.notnull(df), None).astype(object)
    return [tuple(x) for x in cleaned.to_numpy()]