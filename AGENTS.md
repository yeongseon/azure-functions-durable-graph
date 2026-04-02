# AGENTS.md

## Purpose
`azure-functions-durable-graph` provides a manifest-first graph runtime for Azure Functions Python v2 applications using Durable Functions orchestration.

## Read First
- `README.md`
- `CONTRIBUTING.md`

## Working Rules
- Runtime code must remain compatible with Python 3.10+.
- Public APIs must be fully typed.
- The orchestrator must remain deterministic — all user logic runs in Durable Functions activities, never inside the orchestrator.
- Keep documentation examples, manifest builder behaviour, and tests synchronized.
- When bumping version, update `tests/test_public_api.py` to match the new version string.

## Validation
- `make test`
- `make lint`
- `make typecheck`
- `make build`
