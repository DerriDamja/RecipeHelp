"""Handles CLI interactions"""
import typer
from typing import Optional
from recipehelp import db, setup, users


def _make_id_add_list(map: dict[str, int], add_list: list[str]) -> list[int]:
    id_add_list = []
    for item in add_list:
        try:
            id_add_list.append(map[item])
        except KeyError:
            typer.echo(f"{item} could not be added. Check the list of available options.")
    return id_add_list


def _prompt_input_list(message: str) -> list[str]:
    add_list = typer.prompt(message, default=[])
    add_list = [item.strip() for item in add_list.split(',')]
    return add_list


app = typer.Typer()
recipe_app = typer.Typer(
    help="CLI for the RecipeHelp recipe recommendation system.",
    no_args_is_help=True,
)
user_app = typer.Typer(
    name="recipehelp user",
    help="CLI for managing users in RecipeHelp.",
    no_args_is_help=True,
)
app.add_typer(recipe_app)
app.add_typer(user_app)


@recipe_app.command("setup")
def app_setup(from_dump: bool = True) -> None:
    setup.main(from_dump)


@user_app.command("create")
def add_user() -> None:
    typer.echo("-- Create a new user --\n")
    email: str = typer.prompt("Email Address:")
    display_name: str = typer.prompt("Display Name:")

    if not typer.confirm(
        f"Create user {display_name} ({email})?"
    ):
        raise typer.Abort()

    try:
        user_id = users.add_user(
            email,
            display_name,
        )
        typer.echo(f"Created new user {display_name} ({email})")
    except ValueError as e:
        typer.echo(f"Issue: {e}")


@user_app.command("diet")
def add_user_diet(email: str) -> None:
    typer.echo("-- Add your diets --")
    diets = db.get_property_map("diets", "diet_id", "diet_name")
    typer.echo("Options:")
    for diet in diets:
        typer.echo(diet)

    add_list = _prompt_input_list("Diets to add (comma-separate):")
    diet_ids = _make_id_add_list(diets, add_list)

    try:
        user_id = users.get_id_by_email(email)
        users.add_user_diets(user_id, diet_ids)
    except ValueError as e:
        typer.echo(f"Issue: {e}")


@user_app.command("health")
def add_user_health_label(email: str) -> None:
    typer.echo("-- Add your health labels --")
    health_labels = db.get_property_map(
        "health_labels",
        "health_label_id",
        "health_label_name",
    )
    typer.echo("Options:")
    for label in health_labels:
        typer.echo(label)

    add_list = _prompt_input_list("Health labels to add (comma-separate):")
    label_ids = _make_id_add_list(health_labels, add_list)

    try:
        user_id = users.get_id_by_email(email)
        users.add_user_health_labels(user_id, label_ids)
    except ValueError as e:
        typer.echo(f"Issue: {e}")


@user_app.command("cuisine")
def add_user_cuisine_pref(email: str) -> None:
    typer.echo("-- Add a cuisine preference --")
    cuisines = db.get_property_map(
        "cuisines",
        "cuisine_id",
        "cuisine_name",
    )
    typer.echo("\nCuisine Options:")
    for cuisine in cuisines:
        typer.echo(cuisine)
    cuisine = typer.prompt("Pick a Cuisine:").lower()
    try:
        cuisine_id = cuisines[cuisine]
    except KeyError:
        typer.echo("That cuisine does not exist")
        return

    typer.echo("Preference Options:")
    for pref in users.UserPreference:
        typer.echo(pref)
    preference = typer.prompt("Pick a preference:").upper()

    try:
        user_id = users.get_id_by_email(email)
        users.add_user_cuisine_pref(user_id, cuisine_id, preference)
    except ValueError as e:
        typer.echo(f"Issue: {e}")


@user_app.command("ingredient")
def add_user_ingredient_pref(email: str) -> None:
    typer.echo("-- Add an ingredient preference --")
    ingredients = db.get_property_map(
        "ingredients",
        "ingredient_id",
        "ingredient_name",
    )
    typer.echo("\nIngredient Options:")
    for ingredient in ingredients:
        typer.echo(ingredient)
    ingredient = typer.prompt("Pick an Ingredient:").lower()
    try:
        ingredient_id = ingredients[ingredient]
    except KeyError:
        typer.echo("That ingredient does not exist")
        return

    typer.echo("Preference Options:")
    for pref in users.UserPreference:
        typer.echo(pref)
    preference = typer.prompt("Pick a preference:").upper()

    try:
        user_id = users.get_id_by_email(email)
        users.add_user_ingredient_pref(user_id, ingredient_id, preference)
    except ValueError as e:
        typer.echo(f"Issue: {e}")


@user_app.command("nutrition")
def add_user_nutrition_goal(email: str) -> None:
    typer.echo("-- Add a nutrition goal --")
    nutrients = db.get_property_map(
        "nutrients",
        "nutrient_id",
        "nutrient_name",
    )
    typer.echo("Nutrient Options:")
    for nutrient in nutrients:
        typer.echo(nutrient)
    nutrient = typer.prompt("Pick a Nutrient:").lower()
    try:
        nutrient_id = nutrients[nutrient]
    except KeyError:
        typer.echo("That nutrient does not exist")
        return

    min_quantity = typer.prompt("Enter a minimum quantity bound (leave empty if none):", type=float)
    max_quantity = typer.prompt("Enter a maximum quantity bound (leave empty if none):", type=float)

    try:
        user_id = users.get_id_by_email(email)
        users.add_user_nutrition_goal(
            user_id,
            nutrient_id,
            min_quantity,
            max_quantity
        )
    except ValueError as e:
        typer.echo(f"Issue: {e}")


def main() -> None:
    app()