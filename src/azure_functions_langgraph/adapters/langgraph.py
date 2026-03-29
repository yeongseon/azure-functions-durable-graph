from __future__ import annotations

from typing import Any

from ..manifest import GraphRegistration


def bridge_stategraph(
    *,
    graph_name: str,
    graph: Any,
    registration: GraphRegistration[Any],
) -> GraphRegistration[Any]:
    """Temporary bridge boundary for LangGraph integration.

    The runtime consumes a versioned manifest + handlers bundle. This helper exists
    to make the intended public integration point explicit while automatic
    extraction from a LangGraph graph object is still under development.

    Current expectation:
    - the caller owns the actual LangGraph graph object
    - the caller also provides the matching GraphRegistration bundle
    - future work will introspect public LangGraph APIs and build the bundle

    This function currently returns the supplied registration unchanged.
    """
    _ = graph_name
    _ = graph
    return registration
