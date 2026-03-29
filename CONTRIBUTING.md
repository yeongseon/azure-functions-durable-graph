# Contributing Guide

We welcome contributions to the `azure-functions-langgraph` project.

## How to Contribute

1. Fork the repository.
2. Create a new branch.
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Write code and tests.
4. Run the local quality gate.
   ```bash
   make check-all
   ```
5. Commit your changes with an English Conventional Commit message.
   ```bash
   git commit -m "feat: describe your feature"
   ```
6. Push and create a pull request.

## Project Commands

```bash
make format      # Format code with ruff
make lint        # Lint with ruff
make typecheck   # Type check with mypy
make test        # Run tests
make cov         # Run tests with coverage
make check-all   # Run the full local gate
```

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Prefix Types

| Type | Description |
| --- | --- |
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes only |
| `style:` | Code formatting, no logic changes |
| `refactor:` | Code refactoring without behavior changes |
| `test:` | Adding or modifying tests |
| `chore:` | Tooling, dependencies, CI/CD, versioning |

### Examples

```bash
git commit -m "feat: add LangGraph StateGraph adapter"
git commit -m "fix: handle empty orchestration input"
git commit -m "docs: improve quickstart"
git commit -m "refactor: extract route normalization"
git commit -m "chore: update dev dependencies"
```

## Version Management

Update the version number in `src/azure_functions_langgraph/__init__.py` when:

1. New features are added -> increment the minor version.
2. Bug fixes are added -> increment the patch version.
3. Breaking changes are added -> increment the major version.

When updating the version, also:

- Update `CHANGELOG.md`.
- Run `make check-all`.
- Ensure CI passes.

## Pre-commit Hook

Install pre-commit hooks with:

```bash
pre-commit install
```

## Code of Conduct

Be respectful and inclusive. See our [Code of Conduct](CODE_OF_CONDUCT.md) for details.
