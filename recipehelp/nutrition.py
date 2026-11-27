"""Handles nutrition logic"""
from typing import Optional


def validate_goal_boundaries(
        min_quantity: float,
        max_quantity: float,
    ) -> None:
    if min_quantity is None and max_quantity is None:
        raise ValueError("At least one boundary needs to be provided")

    if min_quantity is not None and min_quantity < 0:
        raise ValueError("The minimum bound cannot be negative")

    if max_quantity is not None and max_quantity < 0:
        raise ValueError("The maximum bound cannot be negative")

    if (
        min_quantity is not None
        and max_quantity is not None
        and min_quantity > max_quantity
    ):
        raise ValueError("The minimum bound cannot exceed the maximum bound")


class NutritionGoal:
    def __init__(
        self,
        nutrient_id: int,
        min_quantity: Optional[float],
        max_quantity: Optional[float],
    ) -> None:
        self.nutrient_id = nutrient_id
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity
        self._validate_boundaries()

    """def _validate_id(self) -> None:
        if not id_exists(
            "nutrients",
            "nutrient_id",
            self.nutrient_id
        ):
            raise ValueError(f"Nutrient does not exist")"""

    def _validate_boundaries(self) -> None:
        """Ensures boundaries form a valid range"""
        if self.min_quantity is None and self.max_quantity is None:
            raise ValueError("At least one boundary needs to be provided")

        if self.min_quantity is not None and self.min_quantity < 0:
            raise ValueError("The minimum bound cannot be negative")

        if self.max_quantity is not None and self.max_quantity < 0:
            raise ValueError("The maximum bound cannot be negative")

        if (
            self.min_quantity is not None
            and self.max_quantity is not None
            and self.min_quantity > self.max_quantity
        ):
            raise ValueError("The minimum bound cannot exceed the maximum bound")

    def update_min(self, min_quantity: float) -> None:
        self.min_quantity = min_quantity
        self._validate_boundaries()

    def update_max(self, max_quantity: float) -> None:
        self.max_quantity = max_quantity
        self._validate_boundaries()

    def remove_min(self) -> None:
        self.min_quantity = None

    def remove_max(self) -> None:
        self.max_quantity = None