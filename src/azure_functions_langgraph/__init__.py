"""azure-functions-langgraph package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .contracts import RouteAction, RouteDecision
from .manifest import GraphManifest, GraphRegistration, ManifestBuilder

if TYPE_CHECKING:
    from .app import DurableGraphApp

__all__ = [
    "__version__",
    "DurableGraphApp",
    "GraphManifest",
    "GraphRegistration",
    "ManifestBuilder",
    "RouteAction",
    "RouteDecision",
]

__version__ = "0.1.0a0"


def __getattr__(name: str) -> object:
    if name == "DurableGraphApp":
        try:
            from .app import DurableGraphApp as _cls

            return _cls
        except (ImportError, ModuleNotFoundError):  # pragma: no cover
            return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
