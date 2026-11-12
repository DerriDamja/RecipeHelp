"""
First-time setup script for initialization

This involves:
- Initializing and populating the database
- Adding database indexes
"""
from recipehelp import db
from recipehelp import ingest


def main() -> None:
    db.execute_sql_script("schema.sql")
    print("[SETUP] Successfully initialized DB tables.")


if __name__ == "__main__":
    main()