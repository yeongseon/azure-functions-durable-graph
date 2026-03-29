# FAQ

## What is the relationship between this package and LangGraph?

This package provides a runtime for executing graph-shaped workflows on Azure Functions
with Durable Functions. The manifest-first approach is inspired by LangGraph's
node/edge model, but the runtime is independent. A future LangGraph adapter will
allow automatic translation from LangGraph graph definitions to this runtime's
manifest format.

## Can I use this without Pydantic?

No. State models must be Pydantic v2 `BaseModel` subclasses. The runtime uses
Pydantic for state validation and serialization at every node transition.

## Can I register multiple graphs?

Yes. Call `register_registration()` multiple times:

```python
runtime = DurableGraphApp()
runtime.register_registration(graph_a_registration)
runtime.register_registration(graph_b_registration)
```

Each graph gets its own route: `/api/graphs/{graph_name}/runs`.

!!! warning "Duplicate names"
    Registering two graphs with the same `graph_name` raises `ValueError`.

## How does state merging work?

Node handlers return partial updates that are merged into the current state:

- `dict` return → shallow merge (keys are updated, others preserved)
- `BaseModel` return → full replacement (validated against state model)
- `None` return → state unchanged

```python
def handler(state: MyState) -> dict:
    # Only updates "processed" — all other fields preserved
    return {"processed": True}
```

!!! warning "Shallow merge"
    Dict returns perform shallow merge. Nested dicts are replaced entirely.

## Does it work with async handlers?

Yes. Both `def` and `async def` handlers are supported transparently.

```python
async def my_handler(state: MyState) -> dict:
    result = await some_async_call()
    return {"field": result}
```

## How do external events work?

External events enable human-in-the-loop patterns. A route handler can return
`RouteDecision.wait_for_event(...)` to pause the orchestration until an event
is received via the HTTP endpoint.

```bash
curl -X POST http://localhost:7071/api/runs/{instance_id}/events/approval \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

## What does the graph hash represent?

The `graph_hash` in the manifest is a SHA-256 hash (first 16 chars) of the
canonical JSON representation of the graph topology. It changes when nodes,
edges, or event handlers are added, removed, or renamed.

## Can I customize the HTTP auth level?

Yes. Pass `auth_level` to `DurableGraphApp`:

```python
import azure.functions as func

runtime = DurableGraphApp(auth_level=func.AuthLevel.FUNCTION)
```

## How do I test graph logic without Azure infrastructure?

Use `ManifestBuilder` and `GraphRegistry` directly in unit tests:

```python
from azure_functions_langgraph import ManifestBuilder

builder = ManifestBuilder(graph_name="test", state_model=MyState)
builder.set_entrypoint("step")
builder.add_node("step", handler, terminal=True)
reg = builder.build()

assert reg.manifest.graph_name == "test"
```

For testing handler logic, call handlers directly with state model instances.

## What happens if a node handler raises an exception?

The activity fails and the Durable Functions orchestrator handles it according
to its retry and error handling policies. By default, the orchestration fails
and the error is visible in the run status.

## Where should I go next?

- Setup and first graph: [Quickstart](getting-started.md)
- Builder API deep dive: [Configuration](configuration.md)
- Advanced patterns: [Usage](usage.md)
- Public API details: [API Reference](api.md)
- Common failures: [Troubleshooting](troubleshooting.md)
