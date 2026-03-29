# API Reference

This page documents the public API exported from `azure_functions_langgraph`.

```python
from azure_functions_langgraph import (
    DurableGraphApp,
    GraphManifest,
    GraphRegistration,
    ManifestBuilder,
    RouteAction,
    RouteDecision,
)
```

!!! note "Public surface"
    The package exports `DurableGraphApp`, `GraphManifest`, `GraphRegistration`,
    `ManifestBuilder`, `RouteAction`, and `RouteDecision`.
    Registry and contract internals are not public contracts.

## `ManifestBuilder`

::: azure_functions_langgraph.ManifestBuilder

### Usage example: building a graph

```python
from pydantic import BaseModel

from azure_functions_langgraph import ManifestBuilder, RouteDecision


class AgentState(BaseModel):
    query: str
    classified: bool = False
    response: str | None = None


def classify(state: AgentState) -> dict:
    return {"classified": True}


def route(state: AgentState) -> RouteDecision:
    return RouteDecision.next("respond")


def respond(state: AgentState) -> dict:
    return {"response": f"Answer to: {state.query}"}


builder = ManifestBuilder(graph_name="agent", state_model=AgentState)
builder.set_entrypoint("classify")
builder.add_node("classify", classify, route=route)
builder.add_node("respond", respond, terminal=True)
registration = builder.build()
```

## `GraphManifest`

::: azure_functions_langgraph.GraphManifest

The manifest is a Pydantic model containing:

- `graph_name` — unique graph identifier
- `version` — semantic version string
- `graph_hash` — SHA-256 hash of canonical topology JSON (first 16 chars)
- `state_model_name` — name of the Pydantic state model class
- `entrypoint` — starting node name
- `nodes` — dict of `NodeDefinition` objects
- `event_handler_names` — sorted list of registered event handler names
- `metadata` — arbitrary metadata dict

## `GraphRegistration`

::: azure_functions_langgraph.GraphRegistration

A dataclass containing:

- `manifest` — the compiled `GraphManifest`
- `state_model` — the Pydantic state model type
- `node_handlers` — dict mapping handler names to callables
- `route_handlers` — dict mapping route handler names to callables
- `event_handlers` — dict mapping event names to callables

## `RouteDecision`

::: azure_functions_langgraph.RouteDecision

### Factory methods

```python
# Continue to next node
RouteDecision.next("step_two")

# Complete the graph
RouteDecision.complete(note="all done")

# Wait for an external event
RouteDecision.wait_for_event(
    event_name="approval",
    resume_node="process",
    event_handler_name="merge_approval",
)
```

## `RouteAction`

::: azure_functions_langgraph.RouteAction

An enum with values:

- `RouteAction.NEXT` — continue to next node
- `RouteAction.COMPLETE` — finish the graph
- `RouteAction.WAIT_FOR_EVENT` — pause for external event

## `DurableGraphApp`

::: azure_functions_langgraph.DurableGraphApp

!!! note "Import safety"
    `DurableGraphApp` requires `azure-functions` and `azure-functions-durable`
    at import time. In pure unit test environments without these packages,
    `DurableGraphApp` is set to `None` in `__init__.py`.

### Usage example: wiring a Function App

```python
from azure_functions_langgraph import DurableGraphApp

runtime = DurableGraphApp()
runtime.register_registration(registration)
app = runtime.function_app
```

## HTTP API endpoints

`DurableGraphApp` registers the following endpoints:

| Method | Route | Description |
| --- | --- | --- |
| POST | `/api/graphs/{graph_name}/runs` | Start a new graph run |
| GET | `/api/runs/{instance_id}` | Get run status |
| POST | `/api/runs/{instance_id}/events/{event_name}` | Send an external event |
| POST | `/api/runs/{instance_id}/cancel` | Cancel a run |
| GET | `/api/openapi.json` | OpenAPI document |
| GET | `/api/health` | Health check with registered graphs |

## Internal references

These modules are useful for advanced extension work but are internal APIs:

- `registry.py`: `GraphRegistry`, `execute_node`, `resolve_route`, `apply_event`
- `contracts.py`: `OrchestrationInput`, `NodeExecutionRequest`, `RouteResolutionRequest`, `EventApplyRequest`, `RunStatusEnvelope`

For full implementation patterns, see [Usage](usage.md) and
[Architecture](architecture.md).
