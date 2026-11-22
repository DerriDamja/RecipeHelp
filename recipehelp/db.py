"""Handles PostgreSQL connections and interactions"""

import pandas as pd
import psycopg
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import LiteralString, cast
from time import sleep
from recipehelp.ingest import IngestionBundle

load_dotenv()

PROJECT_PATH = Path(__file__).resolve().parents[1]
SQL_PATH = PROJECT_PATH / "sql"
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")


def get_db_vars() -> dict:
    """Returns PostgreSQL environment variables to be fed into a psycopg connection"""
    vars = {
        "dbname" : POSTGRES_DB,
        "user" : POSTGRES_USER,
        "password" : POSTGRES_PASSWORD,
        "host" : POSTGRES_HOST,
        "port" : POSTGRES_PORT,
    }

    if [key for key, val in vars.items() if not val]:
        raise EnvironmentError(f"Could not read a POSTGRES environment variable. Ensure POSTGRES environment variables are present in a \".env\" file.")

    return vars


def get_connection(retries: int = 10, delay: float = 5.0, **kwargs) -> psycopg.Connection:
    for attempt in range (1, retries + 1):
        try:
            return psycopg.connect(**kwargs)

        except psycopg.Error:
            if attempt >= retries:
                raise

            print(f"PostgreSQL ran into an issue. Retrying ({attempt}/{retries})")
            sleep(delay)

    raise RuntimeError("Could not connect to PostgreSQL.")


def execute_sql_script(filename: str) -> None:
    """Executes a SQL script located under {PROJECT}/sql/ given a file name"""
    with get_connection(**get_db_vars()) as conn:
        sql_file = SQL_PATH / filename

        if not sql_file.exists():
            raise FileNotFoundError(f"Could not find {sql_file}")

        sql = sql_file.read_text(encoding="utf-8")
        # SQL should be static and provided by the repo
        sql = cast(LiteralString, sql)
        conn.execute(query=sql)


def insert_recipes(recipe_df: pd.DataFrame) -> dict:
    """Inserts recipes from a DataFrame. Returns the recipe ID mapping."""
    recipe_id_mapping = {}

    with get_connection(**get_db_vars()) as conn:
        try:
            with conn.cursor() as cur:
                for row in recipe_df.itertuples():
                    cur.execute(
                        """
                        INSERT INTO recipes (
                            recipe_name,
                            source_name,
                            source_url,
                            image_url,
                            servings,
                            calories,
                            total_weight_g
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (source_url) DO NOTHING
                        RETURNING recipe_id;
                        """, (
                        getattr(row, "recipe_name"),
                        getattr(row, "source_name"),
                        getattr(row, "source_url"),
                        getattr(row, "image_url"),
                        getattr(row, "servings"),
                        getattr(row, "calories"),
                        getattr(row, "total_weight_g"),
                    ))

                    res = cur.fetchone()
                    if not res:
                        raise RuntimeError(f"INSERT of recipe {getattr(row, "temp_recipe_id")} did not return a recipe_id")

                    recipe_id = res[0]
                    recipe_id_mapping[getattr(row, "temp_recipe_id")] = recipe_id
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] {e}")
            raise

    return recipe_id_mapping


def _extract_bundle_df(bundle: IngestionBundle, frame_name: str) -> pd.DataFrame:
    if frame_name not in bundle.tables:
        raise KeyError(f"Frame {frame_name} does not exist")

    return bundle.tables.get(frame_name, pd.DataFrame())


def insert_bundle(bundle: IngestionBundle) -> None:
    """Stores a dataset's IngestionBundle into the database."""
    # Extracts desired frames
    recipes = _extract_bundle_df(bundle, "recipes")
    ingredients = _extract_bundle_df(bundle, "ingredients")
    nutrients = _extract_bundle_df(bundle, "nutrients")
    diets = _extract_bundle_df(bundle, "diets")
    health_labels = _extract_bundle_df(bundle, "health_labels")
    cautions = _extract_bundle_df(bundle, "cautions")
    cuisines = _extract_bundle_df(bundle, "cuisines")
    meal_types = _extract_bundle_df(bundle, "meal_types")
    dish_types = _extract_bundle_df(bundle, "dish_types")

    # Maps temp processing IDs to PostgreSQL IDs
    recipe_id_mapping = insert_recipes(recipes)