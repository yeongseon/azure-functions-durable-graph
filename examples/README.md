# Examples

`azure-functions-durable-graph` keeps a growing set of smoke-tested examples:

| Role | Path | Description |
| --- | --- | --- |
| Sequential | `examples/data_pipeline` | Sequential ETL pipeline with `next_node` chaining and state accumulation. |
| Conditional | `examples/content_classifier` | Dynamic routing with `RouteDecision.next()` and fan-in topology. |
| Human-in-the-loop | `examples/support_agent` | External event handling with `RouteDecision.wait_for_event()` and approval flow. |

Each example is a standalone Azure Functions app. See the README in each directory for local setup instructions.
