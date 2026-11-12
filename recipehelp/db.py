"""Handles PostgreSQL connections and interactions"""

import pandas as pd
import psycopg
import os
from dotenv import load_dotenv
from pathlib import Path
from typing import LiteralString, cast
from time import sleep

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

        print(f"Executing {filename}")

        raw_sql = sql_file.read_text(encoding="utf-8")
        # SQL should be static and provided by the repo
        sql = cast(LiteralString, raw_sql)
        conn.execute(query=sql)