"""Base definitions for OIE industry vertical packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerticalPackage:
    """A pre-built industry vertical configuration package.

    Contains event types, rule templates, prompt templates, dashboard
    configuration, and suggested document types tailored for a specific
    industry vertical.
    """

    name: str
    display_name: str
    description: str
    event_types: list[dict[str, Any]] = field(default_factory=list)
    rule_templates: list[dict[str, Any]] = field(default_factory=list)
    prompt_templates: list[dict[str, Any]] = field(default_factory=list)
    dashboard_config: dict[str, Any] = field(default_factory=dict)
    document_templates: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, VerticalPackage] = {}


def register_vertical(package: VerticalPackage) -> None:
    """Register a vertical package in the global registry."""
    _REGISTRY[package.name] = package


def get_vertical(name: str) -> VerticalPackage:
    """Retrieve a registered vertical package by name.

    Raises ``KeyError`` if the vertical is not registered.
    """
    # Ensure all built-in verticals are loaded
    _ensure_loaded()
    if name not in _REGISTRY:
        raise KeyError(f"Unknown vertical: {name!r}. Available: {list(_REGISTRY.keys())}")
    return _REGISTRY[name]


def list_verticals() -> list[VerticalPackage]:
    """Return all registered vertical packages."""
    _ensure_loaded()
    return list(_REGISTRY.values())


_loaded = False


def _ensure_loaded() -> None:
    """Lazily import all built-in verticals so they self-register."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    import packages.verticals.logistics  # noqa: F401
    import packages.verticals.healthcare  # noqa: F401
    import packages.verticals.manufacturing  # noqa: F401
    import packages.verticals.cold_chain  # noqa: F401
    import packages.verticals.food_beverage  # noqa: F401
    import packages.verticals.merchandise_supply_chain  # noqa: F401
    import packages.verticals.restaurant_ops  # noqa: F401
