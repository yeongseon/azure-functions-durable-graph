# Azure Functions LangGraph

[![PyPI](https://img.shields.io/pypi/v/azure-functions-langgraph.svg)](https://pypi.org/project/azure-functions-langgraph/)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://pypi.org/project/azure-functions-langgraph/)
[![CI](https://github.com/yeongseon/azure-functions-langgraph/actions/workflows/ci-test.yml/badge.svg)](https://github.com/yeongseon/azure-functions-langgraph/actions/workflows/ci-test.yml)
[![Release](https://github.com/yeongseon/azure-functions-langgraph/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/yeongseon/azure-functions-langgraph/actions/workflows/publish-pypi.yml)
[![Security Scans](https://github.com/yeongseon/azure-functions-langgraph/actions/workflows/security.yml/badge.svg)](https://github.com/yeongseon/azure-functions-langgraph/actions/workflows/security.yml)
[![codecov](https://codecov.io/gh/yeongseon/azure-functions-langgraph/branch/main/graph/badge.svg)](https://codecov.io/gh/yeongseon/azure-functions-langgraph)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://pre-commit.com/)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://yeongseon.github.io/azure-functions-langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

LangGraph runtime for **Azure Functions** with **Durable Functions** orchestration.

---

Part of the **Azure Functions Python DX Toolkit**
→ Bring FastAPI-like developer experience to Azure Functions

## Why this exists

Running LLM-powered graph workflows on Azure Functions is harder than it should be:

- **Orchestrator determinism** — Durable Functions orchestrators must be deterministic; calling LLMs or tools directly inside them breaks replay safety
- **Graph-to-runtime gap** — Translating a LangGraph-style node/edge design into Durable Functions activities requires repetitive plumbing
- **No standard runtime** — Each team builds its own wiring between graph definitions and Durable Functions primitives

## What it does

- **Manifest-first runtime** — compile graph definitions into a stable, versioned manifest that the orchestrator reads without violating determinism
- **Automatic HTTP API** — `POST /api/graphs/{graph_name}/runs`, `GET /api/runs/{instance_id}`, event injection, cancellation, and health endpoints are registered automatically
- **Deterministic orchestrator loop** — all user logic (node execution, routing, event handling) runs in Durable Functions activities, never inside the orchestrator
- **Conditional routing & external events** — support for branching workflows and human-in-the-loop patterns via `RouteDecision`

## Scope

- Azure Functions Python **v2 programming model**
- Durable Functions orchestration via `azure-functions-durable`
- Pydantic v2-based state models
- Graph topologies: sequential, conditional, and event-driven

This package does **not** currently include automatic LangGraph translation. The adapter boundary is reserved for a future release.

## Features

- `ManifestBuilder` API for declaring graph nodes, routes, and event handlers
- Deterministic Durable Functions orchestrator with configurable execution loop
- Typed state management via Pydantic v2 models
- Built-in HTTP endpoints: start run, get status, send event, cancel, health, OpenAPI
- Graph versioning with topology-derived hash for safe deployments

## Installation

```bash
pip install azure-functions-langgraph
```

Your Azure Functions app should also include:

```text
azure-functions
azure-functions-durable
azure-functions-langgraph
```

For local development:

```bash
git clone https://github.com/yeongseon/azure-functions-langgraph.git
cd azure-functions-langgraph
pip install -e .[dev]
```

## Quick Start

```python
from pydantic import BaseModel

from azure_functions_langgraph import DurableGraphApp, ManifestBuilder, RouteDecision


class MyState(BaseModel):
    message: str
    processed: bool = False


def process_message(state: MyState) -> dict:
    return {"processed": True}


def finalize(state: MyState) -> dict:
    return {"message": f"Done: {state.message}"}


builder = ManifestBuilder(graph_name="my_graph", state_model=MyState)
builder.set_entrypoint("process")
builder.add_node("process", process_message, next_node="finalize")
builder.add_node("finalize", finalize, terminal=True)

registration = builder.build()

runtime = DurableGraphApp()
runtime.register_registration(registration)
app = runtime.function_app
```

### What you get

1. `POST /api/graphs/my_graph/runs` — starts a new graph execution
2. `GET /api/runs/{instance_id}` — polls run status
3. `GET /api/health` — lists registered graphs
4. `GET /api/openapi.json` — OpenAPI document

## When to use

- You need graph-shaped LLM workflows on Azure Functions
- You want deterministic Durable Functions orchestration without manual activity wiring
- You need human-in-the-loop approval patterns (external events)
- You want versioned graph deployments with topology hashing

## Documentation

- Project docs live under `docs/`
- Smoke-tested examples live under `examples/`

## Ecosystem

Part of the **Azure Functions Python DX Toolkit**:

| Package | Role |
|---------|------|
| [azure-functions-validation](https://github.com/yeongseon/azure-functions-validation) | Request and response validation |
| [azure-functions-openapi](https://github.com/yeongseon/azure-functions-openapi) | OpenAPI spec and Swagger UI |
| [azure-functions-logging](https://github.com/yeongseon/azure-functions-logging) | Structured logging and observability |
| [azure-functions-doctor](https://github.com/yeongseon/azure-functions-doctor) | Pre-deploy diagnostic CLI |
| [azure-functions-scaffold](https://github.com/yeongseon/azure-functions-scaffold) | Project scaffolding |
| **azure-functions-langgraph** | LangGraph runtime with Durable Functions |
| [azure-functions-python-cookbook](https://github.com/yeongseon/azure-functions-python-cookbook) | Recipes and examples |

## Disclaimer

This project is an independent community project and is not affiliated with,
endorsed by, or maintained by Microsoft.

Azure and Azure Functions are trademarks of Microsoft Corporation.

## License

MIT
