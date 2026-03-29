# Changelog

This page documents the version history and migration paths for the `azure-functions-langgraph` package.

## Versioning Scheme

This project follows Semantic Versioning (semver.org). Given a version number MAJOR.MINOR.PATCH, increment the:

- MAJOR version when you make incompatible API changes
- MINOR version when you add functionality in a backward compatible manner
- PATCH version when you make backward compatible bug fixes

The changelog is generated from Conventional Commits using git-cliff. Breaking changes are explicitly listed under the "Breaking Changes" section for each release.

## Full Version History

### v0.1.0a0 (2026-03-29)

#### Added

- Manifest-first runtime with `ManifestBuilder` fluent API
- `DurableGraphApp` for automatic Azure Functions + Durable Functions wiring
- Sequential node execution with Pydantic v2 state management
- Conditional routing via `RouteDecision`
- External event injection and resume (`wait_for_event`)
- Graph cancellation via HTTP endpoint
- Minimal OpenAPI document generation
- Health endpoint with registered graph listing
- Graph versioning with topology-derived SHA-256 hash
- Support agent example with human-in-the-loop approval pattern
- Unit tests for manifest building and registry operations
- Full project infrastructure (CI, docs, security scanning, release workflow)
