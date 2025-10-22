# Gameplan

> Local-first CLI for tracking work across multiple systems with markdown

**Status**: 🚧 Under active development

## Overview

Gameplan is a test-driven CLI tool for tracking work items across multiple external systems (Jira, GitHub, Linear, etc.) using local markdown files and a pluggable adapter architecture.

## Quick Start

```bash
# Initialize a new gameplan repository
gameplan init

# Sync data from configured adapters
gameplan sync

# View your agenda
gameplan agenda view
```

## Core Principles

- **Local-first**: All data lives in markdown files
- **Pluggable adapters**: Easy integration with any tracking system
- **Test-driven**: 85%+ coverage with comprehensive test suite
- **Workflow-agnostic**: Configure your own commands and sections

## Development

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for implementation roadmap.

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=cli --cov-report=term-missing
```

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
