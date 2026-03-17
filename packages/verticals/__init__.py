"""OIE Industry Vertical Packages — pre-built configurations for specific industries."""

from packages.verticals.base import VerticalPackage, get_vertical

# Import verticals so they self-register on package import
import packages.verticals.food_beverage  # noqa: F401
import packages.verticals.merchandise_supply_chain  # noqa: F401
import packages.verticals.restaurant_ops  # noqa: F401

__all__ = ["VerticalPackage", "get_vertical"]
