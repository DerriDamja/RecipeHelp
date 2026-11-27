"""Handles PostgreSQL connections and interactions"""

import pandas as pd
import psycopg
import os
from dotenv import load_dotenv
from psycopg.sql import SQL, Identifier
from pathlib import Path
from typing import LiteralString, cast
from time import sleep
from recipehelp.ingest import IngestionBundle
from recipehelp.users import UserPreference

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
            if kwargs:
                return psycopg.connect(**kwargs)
            return psycopg.connect(**get_db_vars())

        except psycopg.Error:
            if attempt >= retries:
                raise

            print(f"PostgreSQL ran into an issue. Retrying ({attempt}/{retries})")
            sleep(delay)

    raise RuntimeError("Could not connect to PostgreSQL.")


def execute_sql_script(filename: str) -> None:
    """Executes a SQL script located under {PROJECT}/sql/ given a file name"""
    with get_connection() as conn:
        sql_file = SQL_PATH / filename

        if not sql_file.exists():
            raise FileNotFoundError(f"Could not find {sql_file}")

        sql = sql_file.read_text(encoding="utf-8")
        # SQL should be static and provided by the repo
        sql = cast(LiteralString, sql)
        conn.execute(query=sql)


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prepares DataFrames for DB insertion by replacing NaNs with None (NULL)"""
    return df.astype(object).where(pd.notna(df), None)


def insert_recipes(df: pd.DataFrame) -> dict[int, int]:
    """Inserts recipes from a DataFrame. Returns the recipe ID map."""
    recipe_map = {}
    df = _prepare_df(df)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in df.itertuples():
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
                    ON CONFLICT DO NOTHING
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
                recipe_map[getattr(row, "temp_recipe_id")] = recipe_id

    return recipe_map


def insert_nutrients(df: pd.DataFrame) -> dict[str, int]:
    nutrient_map = {}
    df = _prepare_df(df)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in df.itertuples():
                cur.execute(
                    """
                    INSERT INTO nutrients (
                        nutrient_name,
                        nutrient_tag,
                        unit
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING nutrient_id;
                    """, (
                    getattr(row, "nutrient_name"),
                    getattr(row, "nutrient_tag"),
                    getattr(row, "unit"),
                ))

                res = cur.fetchone()
                if not res:
                    raise RuntimeError(f"INSERT of nutrient {getattr(row, "nutrient_tag")} did not return a nutrient_id")

                nutrient_id = res[0]
                nutrient_map[getattr(row, "nutrient_tag")] = nutrient_id

    return nutrient_map


def insert_one_val_table(
        df: pd.DataFrame,
        table: str,
        id_col: str,
        val_name: str,
        ) -> dict[str, int]:
    """
    Inserts a simple table containing only one UNIQUE attribute.
    The DataFrame's val_name must match the DB's attribute name.
    Returns an ID map.
    """
    id_map = {}
    df = _prepare_df(df)

    with get_connection() as conn:
        with conn.cursor() as cur:
            query = SQL(
                """
                INSERT INTO {} ({})
                VALUES (%s)
                ON CONFLICT DO NOTHING
                RETURNING {};
                """).format(
                Identifier(table),
                Identifier(val_name),
                Identifier(id_col),
            )

            for row in df.itertuples():
                cur.execute(query, (getattr(row, val_name),))

                res = cur.fetchone()
                if not res:
                    raise RuntimeError(f"INSERT of {val_name} did not return a {id_col}")

                id = res[0]
                id_map[getattr(row, val_name)] = id

    return id_map


def insert_recipe_junction(
        df: pd.DataFrame,
        table: str,
        other_id_col: str,
        other_col: str,
        recipe_map: dict,
        other_map: dict,
        ) -> None:
    """Inserts basic recipe junctions."""
    df = _prepare_df(df)

    with get_connection() as conn:
        with conn.cursor() as cur:
            query = SQL(
                """
                INSERT INTO {} (recipe_id, {})
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """).format(
                Identifier(table),
                Identifier(other_id_col),
            )
            for row in df.itertuples():
                cur.execute(query, (recipe_map[getattr(row, "temp_recipe_id")], other_map[getattr(row, other_col)]))


def insert_recipe_ingredients(df: pd.DataFrame, recipe_map: dict, ingredient_map: dict) -> None:
    df = _prepare_df(df)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in df.itertuples():
                cur.execute(
                    """
                    INSERT INTO recipe_ingredients (
                        recipe_id,
                        ingredient_id,
                        original_text,
                        measure,
                        quantity,
                        weight_g
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """, (
                    recipe_map[getattr(row, "temp_recipe_id")],
                    ingredient_map[getattr(row, "ingredient_name")],
                    getattr(row, "original_text"),
                    getattr(row, "measure"),
                    getattr(row, "quantity"),
                    getattr(row, "weight_g"),
                ))


def insert_recipe_nutrients(df: pd.DataFrame, recipe_map: dict, nutrient_map: dict) -> None:
    df = _prepare_df(df)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for row in df.itertuples():
                cur.execute(
                    """
                    INSERT INTO recipe_nutrients (
                        recipe_id,
                        nutrient_id,
                        quantity
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """, (
                    recipe_map[getattr(row, "temp_recipe_id")],
                    nutrient_map[getattr(row, "nutrient_tag")],
                    getattr(row, "quantity"),
                ))


def insert_bundle(bundle: IngestionBundle) -> None:
    """Stores a dataset's IngestionBundle into the database."""
    # Insertions

    # Maps temp processing IDs to PostgreSQL IDs
    recipe_map = insert_recipes(bundle.tables["recipes"])

    # Maps UNIQUE nutrient tags to PostgreSQL IDs
    nutrient_map = insert_nutrients(bundle.tables["nutrients"])

    # Maps UNIQUE names to PostgreSQL IDs
    ingredient_map = insert_one_val_table(
        bundle.tables["ingredients"],
        "ingredients",
        "ingredient_id",
        "ingredient_name",
    )
    diet_map = insert_one_val_table(
        bundle.tables["diets"],
        "diets",
        "diet_id",
        "diet_name",
    )
    health_label_map = insert_one_val_table(
        bundle.tables["health_labels"],
        "health_labels",
        "health_label_id",
        "health_label_name",
    )
    caution_map = insert_one_val_table(
        bundle.tables["cautions"],
        "cautions",
        "caution_id",
        "caution_name",
    )
    cuisine_map = insert_one_val_table(
        bundle.tables["cuisines"],
        "cuisines",
        "cuisine_id",
        "cuisine_name",
    )
    meal_type_map = insert_one_val_table(
        bundle.tables["meal_types"],
        "meal_types",
        "meal_type_id",
        "meal_type_name",
    )
    dish_type_map = insert_one_val_table(
        bundle.tables["dish_types"],
        "dish_types",
        "dish_type_id",
        "dish_type_name",
    )

    # Junction insertions
    insert_recipe_ingredients(bundle.tables["recipe_ingredients"], recipe_map, ingredient_map)
    insert_recipe_nutrients(bundle.tables["recipe_nutrients"], recipe_map, nutrient_map)
    insert_recipe_junction(
        bundle.tables["recipe_diets"],
        "recipe_diets",
        "diet_id",
        "diet_name",
        recipe_map,
        diet_map,
    )
    insert_recipe_junction(
        bundle.tables["recipe_health_labels"],
        "recipe_health_labels",
        "health_label_id",
        "health_label_name",
        recipe_map,
        health_label_map,
    )
    insert_recipe_junction(
        bundle.tables["recipe_cautions"],
        "recipe_cautions",
        "caution_id",
        "caution_name",
        recipe_map,
        caution_map,
    )
    insert_recipe_junction(
        bundle.tables["recipe_cuisines"],
        "recipe_cuisines",
        "cuisine_id",
        "cuisine_name",
        recipe_map,
        cuisine_map,
    )
    insert_recipe_junction(
        bundle.tables["recipe_meal_types"],
        "recipe_meal_types",
        "meal_type_id",
        "meal_type_name",
        recipe_map,
        meal_type_map,
    )
    insert_recipe_junction(
        bundle.tables["recipe_dish_types"],
        "recipe_dish_types",
        "dish_type_id",
        "dish_type_name",
        recipe_map,
        dish_type_map,
    )


def insert_user(email: str, display_name: str) -> int:
    """Adds a new user to the database and returns their user ID"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    email,
                    display_name
                )
                VALUES (%s, %s)
                ON CONFLICT (email)
                DO NOTHING
                RETURNING user_id;
                """, (
                    email,
                    display_name,
                ))

            res = cur.fetchone()
            if res is None:
                raise ValueError("An account with this email already exists")

            return res[0]


def insert_user_diet(user_id: int, diet_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
            """
            INSERT INTO user_diets (
                user_id,
                diet_id
            )
            VALUES (%s, %s)
            ON CONFLICT (user_id, diet_id)
            DO NOTHING;
            """, (
                user_id,
                diet_id,
            ))


def insert_user_health_label(user_id: int, health_label_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO  user_health_labels (
                    user_id,
                    health_label_id
                )
                VALUES (%s, %s)
                ON CONFLICT (user_id, health_label_id)
                DO NOTHING;
                """, (
                    user_id,
                    health_label_id,
                ))


def insert_user_cuisine_pref(
        user_id: int,
        cuisine_id: int,
        preference: UserPreference,
    ) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_cuisine_preferences (
                    user_id,
                    cuisine_id,
                    preference
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, cuisine_id)
                DO UPDATE SET
                    preference = EXCLUDED.preference;
                """, (
                    user_id,
                    cuisine_id,
                    preference,
                ))


def insert_user_ingredient_pref(
        user_id: int,
        ingredient_id: int,
        preference: UserPreference,
    ) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_ingredient_preferences (
                    user_id,
                    ingredient_id,
                    preference
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, ingredient_id)
                DO UPDATE SET
                    preference = EXCLUDED.preference;
                """, (
                    user_id,
                    ingredient_id,
                    preference,
                ))


def insert_user_nutrition(
        user_id: int,
        nutrient_id: int,
        min_quantity: float,
        max_quantity: float,
    ) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_nutrition_goals (
                    user_id,
                    nutrient_id,
                    min_quantity,
                    max_quantity
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, nutrient_id)
                DO UPDATE SET
                    min_quantity = EXCLUDED.min_quantity
                    max_quantity = EXCLUDED.max_quantity;
                """, (
                    user_id,
                    nutrient_id,
                    min_quantity,
                    max_quantity,
                ))


def update_user_name(user_id: int, new_name: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET display_name = %s
                WHERE id = %s;
                """, (
                    new_name,
                    user_id,
                ))


def id_exists(table: str, id_col: str, id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = SQL(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM {}
                    WHERE {} = %s
                );
                """).format(
                Identifier(table),
                Identifier(id_col),
            )
            res = cur.execute(query, (id,)).fetchone()
            if res is None:
                raise KeyError(f"Error searching for the {id_col} ID in {table}")

            return res[0]


def get_id_by_name(table: str, id_col: str, name_col: str, name: str) -> int:
    """Selects an ID from a table given a name. Intended for use where names are UNIQUE"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = SQL(
                """
                SELECT {}
                FROM {}
                WHERE {} = %s;
                """
            ).format(
                Identifier(id_col),
                Identifier(table),
                Identifier(name_col),
            )
            res = cur.execute(query, (name,)).fetchone()
            if res is None:
                raise KeyError(f"Error retrieving ID for {name} in {table}")

            return res[0]


def get_property_map(
        table: str,
        id_col: str,
        name_col: str
    ) -> dict[str, int]:
    """
    Returns a map of UNIQUE property names and their associated ID.
    Example properties: diets, health_labels, cuisines, etc.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = SQL(
                """
                SELECT {}, {}
                FROM {}
                ORDER BY {};
                """
            ).format(
                Identifier(id_col),
                Identifier(name_col),
                Identifier(table),
                Identifier(name_col),
            )
            cur.execute(query)
            return {name: id for id, name in cur.fetchall()}
