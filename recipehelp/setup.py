"""
First-time setup script for initialization

This involves:
- Fetching & transforming recipe data
- Initializing and populating the database
- Adding database indexes
"""
from recipehelp import db, ingest


def main() -> None:
    db.execute_sql_script("schema.sql")
    print("[SETUP] Successfully initialized DB tables.")
    df = ingest.fetch_dataset()
    print("[SETUP] Successfully fetched recipe dataset.")
    transformed = ingest.transform_dataset(df)
    print("[SETUP] Successfully transformed recipe dataset.")
    db.insert_bundle(transformed)
    print("[SETUP] Successfully populated DB.")
    db.execute_sql_script("indexes.sql")
    print("[SETUP] Successfully added DB indexes.")
    print("[SETUP] Setup is complete.")



if __name__ == "__main__":
    main()