# Configuration

This page documents the `ManifestBuilder` API, `DurableGraphApp` options, and how
to configure graph definitions.

## ManifestBuilder

`ManifestBuilder` is the primary API for declaring graph topologies.

```python
from azure_functions_durable_graph import ManifestBuilder

builder = ManifestBuilder(
    graph_name="my_graph",
    state_model=MyState,
    version="0.1.0",
    metadata={"team": "platform"},
)
```

### Constructor parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `graph_name` | `str` | required | Unique name for the graph (used in API routes). |
| `state_model` | `type[BaseModel]` | required | Pydantic v2 model representing graph state. |
| `version` | `str` | `"0.1.0"` | Semantic version string for the graph. |
| `metadata` | `dict` | `None` | Arbitrary metadata included in the manifest. |

### `set_entrypoint(node_name)`

Sets the starting node for graph execution. Must reference a node added via `add_node`.

```python
builder.set_entrypoint("classify")
```

!!! warning "Required"
    `build()` raises `ValueError` if no entrypoint is set.

### `add_node(name, handler, *, next_node=None, route=None, terminal=False)`

Registers a node in the graph.

| Parameter | Type | Description |
| --- | --- | --- |
| `name` | `str` | Unique node name. |
| `handler` | `Callable` | Function that receives state and returns updates. |
| `next_node` | `str \| None` | Static next node (simple linear flow). |
| `route` | `Callable \| None` | Route handler for conditional branching. |
| `terminal` | `bool` | If `True`, the graph completes after this node. |

```python
# Linear flow
builder.add_node("step_a", handler_a, next_node="step_b")

# Conditional routing
builder.add_node("step_a", handler_a, route=my_route_handler)

# Terminal node
builder.add_node("final", handler_final, terminal=True)
```

!!! note "Mutual exclusivity"
    Terminal nodes cannot define `next_node` or `route`.

### `add_event_handler(event_name, handler)`

Registers an event handler for external event injection.

```python
builder.add_event_handler("approval", merge_approval)
```

Event handlers receive `(state, event_payload)` and return state updates.

### `build()`

Compiles the manifest and returns a `GraphRegistration`.

```python
registration = builder.build()
```

The build step:

1. Validates that an entrypoint is set and references a registered node.
2. Computes a manifest-derived hash from the canonical JSON of the graph structure.
3. Returns a `GraphRegistration` containing the manifest and all handler references.

## DurableGraphApp

`DurableGraphApp` wires graph registrations into Azure Functions.

```python
from azure_functions_durable_graph import DurableGraphApp

runtime = DurableGraphApp(auth_level=func.AuthLevel.ANONYMOUS)
runtime.register_registration(registration)
app = runtime.function_app
```

### Constructor parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `auth_level` | `func.AuthLevel` | `ANONYMOUS` | Auth level for all HTTP endpoints. |

### `register_registration(registration)`

Adds a graph registration to the runtime. Multiple graphs can be registered.

```python
runtime.register_registration(support_agent_registration)
runtime.register_registration(data_pipeline_registration)
```

## Node handlers

Node handlers are functions that receive the current state model and return updates.

```python
def my_handler(state: MyState) -> dict:
    return {"field": "new_value"}
```

Supported return types:

- `dict[str, Any]` — merged into current state
- `BaseModel` — replaces state (validated against state model)
- `None` — state unchanged

Both sync and async handlers are supported:

```python
async def async_handler(state: MyState) -> dict:
    result = await some_async_call()
    return {"field": result}
```

## Route handlers

Route handlers determine the next node after execution.

```python
def my_route(state: MyState) -> RouteDecision:
    if state.needs_review:
        return RouteDecision.wait_for_event(
            event_name="approval",
            resume_node="process",
        )
    return RouteDecision.next("process")
```

Supported return types:

- `RouteDecision` — explicit routing decision
- `str` — shorthand for `RouteDecision.next(node_name)` (use `"__complete__"` to end)
- `dict` — validated as `RouteDecision`
- `None` — falls back to `next_node` if defined, otherwise completes

## Event handlers

Event handlers process external events and return state updates.

```python
def merge_approval(state: MyState, event_payload: Any) -> dict:
    return {"approved": event_payload.get("approved", False)}
```

## Related references

- [Usage](usage.md)
- [API Reference](api.md)
- [Architecture](architecture.md)
- [Troubleshooting](troubleshooting.md)
