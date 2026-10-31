"""Handles PostgreSQL connection and """

from dotenv import load_dotenv
import pandas as pd
import psycopg

load_dotenv()

DATASET_PD_URL = r"hf://datasets/datahiveai/recipes-with-nutrition/recipes-with-nutrition.csv"

# def get_connection() -> :