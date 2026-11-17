"""Handles CLI interactions"""
import typer
from pathlib import Path
from recipehelp import db, setup

app = typer.Typer(
    name="RecipeHelp",
    help="CLI for the RecipeHelp recipe recommendation system.",
    no_args_is_help=True,
)

@app.command("init")
def app_init() -> None:
    setup.main()