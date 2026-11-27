"""Manages user logic, such as creation, modification, and deletion"""
from re import match
from enum import Enum
from recipehelp import db, nutrition

class UserPreference(str, Enum):
    """Represents user preferences towards recipe and nutrition properties"""
    LIKE = "LIKE"
    EXCLUDE = "EXCLUDE"


def _make_preference(preference: str) -> UserPreference:
    try:
        return UserPreference(preference.upper())
    except ValueError:
        raise ValueError("Invalid preference type")


def validate_user_email(email: str) -> None:
    """Ensures a user email is in a valid email format"""
    pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
    if not bool(match(pattern, email)):
        raise ValueError(f"{email} uses an invalid email format")


def clean_user_email(email: str) -> str:
    clean_email = email.strip().lower()
    validate_user_email(clean_email)
    return clean_email


def get_id_by_email(email: str) -> int:
    clean_email = clean_user_email(email)
    user_id = db.get_id_by_name(
        "users",
        "user_id",
        "email",
        clean_email
    )
    return user_id


def add_user(email: str, display_name: str) -> int:
    """Adds a new user to the database"""
    clean_email = clean_user_email(email)
    
    user_id = db.insert_user(clean_email, display_name)
    return user_id
    


def add_user_diets(user_id: int, diet_ids: list[int]) -> None:
    """Adds diets to a user's diet list"""
    for diet_id in diet_ids:
        db.insert_user_diet(user_id, diet_id)


def add_user_health_labels(user_id: int, label_ids: list[int]) -> None:
    for label_id in label_ids:
        db.insert_user_health_label(user_id, label_id)


def add_user_cuisine_pref(
        user_id: int,
        cuisine_id: int,
        preference: str
    ) -> None:
    pref = _make_preference(preference)
    db.insert_user_cuisine_pref(user_id, cuisine_id, pref)


def add_user_ingredient_pref(
        user_id: int,
        ingredient_id: int,
        preference: str
    ) -> None:
    pref = _make_preference(preference)
    db.insert_user_ingredient_pref(user_id, ingredient_id, pref)


def add_user_nutrition_goal(
        user_id: int,
        nutrient_id: int,
        min_quantity: float,
        max_quantity: float,
    ) -> None:
    nutrition.validate_goal_boundaries(
        min_quantity,
        max_quantity,
    )
    db.insert_user_nutrition(
        user_id,
        nutrient_id,
        min_quantity,
        max_quantity,
    )
