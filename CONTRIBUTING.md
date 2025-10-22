# Contributing to Gameplan

Thank you for your interest in contributing to Gameplan! This document provides guidelines and instructions for contributors.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Test-Driven Development (TDD)](#test-driven-development-tdd)
- [Adding a New Adapter](#adding-a-new-adapter)
- [Code Quality Standards](#code-quality-standards)
- [Git Commit Guidelines](#git-commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)

---

## Code of Conduct

This project follows a simple principle: **Be respectful and professional**. We're all here to build useful software together.

---

## Development Setup

### Prerequisites

- **Python 3.11+** (required)
- **uv** (recommended) or pip for dependency management
- **Git** for version control

### Installation

```bash
# Clone the repository
git clone https://github.com/shanemcd/gameplan-cli.git
cd gameplan-cli

# Install dependencies (using uv)
uv sync

# Or with pip
pip install -e ".[dev]"

# Verify installation
uv run pytest
```

### Project Structure

```
gameplan-cli/
├── cli/                    # Source code
│   ├── __init__.py
│   ├── cli.py             # Main CLI entry point
│   ├── init.py            # Init command
│   ├── agenda.py          # Agenda commands
│   └── adapters/          # Adapter implementations
│       ├── base.py        # ABC interface
│       └── jira.py        # Jira adapter
├── tests/                 # Test suite
│   ├── conftest.py        # Shared fixtures
│   └── unit/              # Unit tests
│       ├── test_*.py
│       └── adapters/
├── pyproject.toml         # Package configuration
├── README.md              # Public documentation
├── ARCHITECTURE.md        # Architecture guide
└── CONTRIBUTING.md        # This file
```

---

## Development Workflow

Gameplan follows **strict Test-Driven Development (TDD)**. All new features and bug fixes must follow this workflow:

### The TDD Cycle

```
┌─────────────────────────────────────────┐
│  1. RED: Write failing tests first      │
│     - Test what the feature SHOULD do   │
│     - Run tests (they should fail)      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. GREEN: Implement minimum code       │
│     - Write code to pass tests          │
│     - Run tests (they should pass)      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. REFACTOR: Clean up code             │
│     - Improve without changing behavior │
│     - Run tests (still passing)         │
└─────────────────────────────────────────┘
```

### Example Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/my-new-feature

# 2. Write tests first (RED phase)
# Edit tests/unit/test_my_feature.py
uv run pytest tests/unit/test_my_feature.py
# Tests should FAIL

# 3. Implement feature (GREEN phase)
# Edit cli/my_feature.py
uv run pytest tests/unit/test_my_feature.py
# Tests should PASS

# 4. Refactor (REFACTOR phase)
# Clean up code, improve readability
uv run pytest  # All tests still pass

# 5. Check coverage
uv run pytest --cov=cli --cov-report=term-missing
# Ensure 85%+ coverage

# 6. Commit with clear message
git add tests/unit/test_my_feature.py cli/my_feature.py
git commit -m "Add my new feature with comprehensive tests"

# 7. Push and create PR
git push origin feature/my-new-feature
```

---

## Test-Driven Development (TDD)

### Core Principles

1. **Tests come FIRST**: Write tests before implementation
2. **One test at a time**: Focus on making one test pass, then move to next
3. **Minimal implementation**: Write only enough code to pass the test
4. **Refactor fearlessly**: Tests protect you from breaking things

### Writing Good Tests

**DO**:
- Test behavior, not implementation
- Use descriptive test names: `test_load_config_parses_single_item`
- Arrange-Act-Assert structure
- Mock external dependencies (subprocess, file I/O, APIs)
- Test edge cases (empty lists, missing fields, errors)

**DON'T**:
- Test private methods directly
- Duplicate implementation logic in tests
- Write tests that depend on each other
- Hardcode absolute paths

### Example Test Structure

```python
def test_feature_does_something(temp_dir, sample_config):
    """Feature should do X when Y happens."""
    # ARRANGE: Set up test data
    adapter = MyAdapter(sample_config, temp_dir)
    item = TrackedItem(id="TEST-123", adapter="my", metadata={})

    # ACT: Execute the behavior
    result = adapter.some_method(item)

    # ASSERT: Verify the outcome
    assert result.status == "expected_value"
    assert result.title == "Expected Title"
```

---

## Adding a New Adapter

This is a complete TDD guide for creating a new adapter (e.g., GitHub, Linear, etc.).

### Step 1: Write Tests First (RED Phase)

Create `tests/unit/adapters/test_myadapter.py`:

```python
"""Tests for MyAdapter.

MyAdapter integrates with [External System] via [CLI/API].
"""
import pytest
from cli.adapters.base import Adapter, ItemData, TrackedItem
from cli.adapters.myadapter import MyAdapter


class TestMyAdapterBasics:
    """Test basic adapter functionality."""

    def test_adapter_name(self, temp_dir):
        """MyAdapter reports correct name."""
        adapter = MyAdapter({}, temp_dir)
        assert adapter.get_adapter_name() == "myadapter"

    def test_adapter_is_subclass(self):
        """MyAdapter inherits from Adapter ABC."""
        assert issubclass(MyAdapter, Adapter)


class TestMyAdapterConfigLoading:
    """Test configuration parsing."""

    def test_load_config_parses_single_item(self, temp_dir):
        """load_config parses single item."""
        config = {
            "items": [
                {"id": "item-123", "repo": "owner/repo"}
            ]
        }
        adapter = MyAdapter(config, temp_dir)
        items = adapter.load_config(config)

        assert len(items) == 1
        assert items[0].id == "item-123"
        assert items[0].adapter == "myadapter"

    # Add more config tests...


class TestMyAdapterFetchData:
    """Test fetching data from external system."""

    @patch("subprocess.run")  # Or mock API calls
    def test_fetch_item_data_calls_external_system(self, mock_run, temp_dir):
        """fetch_item_data calls external CLI/API."""
        # Mock external response
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"title": "Test", "status": "Open"}'
        )

        adapter = MyAdapter({}, temp_dir)
        item = TrackedItem(
            id="item-123",
            adapter="myadapter",
            metadata={"id": "item-123"}
        )

        data = adapter.fetch_item_data(item)

        assert isinstance(data, ItemData)
        assert data.title == "Test"
        assert data.status == "Open"

    # Add more fetch tests...


class TestMyAdapterStorage:
    """Test storage path generation."""

    def test_get_storage_path_structure(self, temp_dir):
        """get_storage_path follows tracking/areas/myadapter/ structure."""
        adapter = MyAdapter({}, temp_dir)
        item = TrackedItem(
            id="item-123",
            adapter="myadapter",
            metadata={"id": "item-123"}
        )

        path = adapter.get_storage_path(item, title="Test Item")

        assert "tracking/areas/myadapter" in str(path)
        assert path.name == "README.md"

    # Add more storage tests...


class TestMyAdapterUpdateReadme:
    """Test README.md updates."""

    def test_update_readme_creates_new_file(self, temp_dir):
        """update_readme creates README.md if missing."""
        adapter = MyAdapter({}, temp_dir)
        item = TrackedItem(id="item-123", adapter="myadapter", metadata={})
        data = ItemData(
            title="Test Item",
            status="Open",
            raw_data={}
        )
        readme_path = temp_dir / "README.md"

        adapter.update_readme(readme_path, data, item)

        assert readme_path.exists()
        content = readme_path.read_text()
        assert "Test Item" in content

    def test_update_readme_preserves_manual_content(self, temp_dir):
        """update_readme preserves manually-added sections."""
        # Create README with manual content
        readme_path = temp_dir / "README.md"
        initial_content = """# item-123: Test

**Status**: Open

## Overview
Manual content here

## Notes
- Important note
"""
        readme_path.write_text(initial_content)

        # Update with new status
        adapter = MyAdapter({}, temp_dir)
        item = TrackedItem(id="item-123", adapter="myadapter", metadata={})
        data = ItemData(title="Test", status="Closed", raw_data={})

        adapter.update_readme(readme_path, data, item)

        content = readme_path.read_text()
        assert "Manual content here" in content
        assert "Important note" in content
        assert "Closed" in content  # Status updated

    # Add more update tests...
```

**Run tests (should FAIL)**:
```bash
uv run pytest tests/unit/adapters/test_myadapter.py
```

### Step 2: Implement Adapter (GREEN Phase)

Create `cli/adapters/myadapter.py`:

```python
"""MyAdapter for syncing items from [External System].

Integrates with [External System] via [CLI tool/API].
Requires:
- [CLI tool] installed (if applicable)
- [Environment variables] configured (if applicable)
"""
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from cli.adapters.base import Adapter, ItemData, TrackedItem, sanitize_title_for_path


class MyAdapter(Adapter):
    """Adapter for syncing items from [External System]."""

    def get_adapter_name(self) -> str:
        """Return adapter name."""
        return "myadapter"

    def load_config(self, config: Dict[str, Any]) -> List[TrackedItem]:
        """Parse configuration and return tracked items.

        Args:
            config: Adapter config section with 'items' list

        Returns:
            List of TrackedItem objects
        """
        items = config.get("items", [])
        tracked_items = []

        for item_config in items:
            tracked_item = TrackedItem(
                id=item_config["id"],
                adapter="myadapter",
                metadata=item_config,
            )
            tracked_items.append(tracked_item)

        return tracked_items

    def fetch_item_data(
        self, item: TrackedItem, since: Optional[str] = None
    ) -> ItemData:
        """Fetch item data from external system.

        Args:
            item: The item to fetch
            since: Optional timestamp for incremental sync

        Returns:
            ItemData with title, status, and raw data
        """
        item_id = item.metadata["id"]

        # Call external CLI/API
        # Example for CLI:
        cmd = ["mycli", "view", item_id, "--json"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to fetch item {item_id}: {result.stderr}"
            )

        # Parse response
        data = json.loads(result.stdout)

        return ItemData(
            title=data.get("title", ""),
            status=data.get("status", "Unknown"),
            raw_data=data,
        )

    def get_storage_path(
        self, item: TrackedItem, title: Optional[str] = None
    ) -> Path:
        """Get README.md path for this item.

        Args:
            item: The tracked item
            title: Optional title for directory naming

        Returns:
            Path to README.md like tracking/areas/myadapter/item-123-title/README.md
        """
        item_id = item.id

        # Build directory name
        if title:
            sanitized_title = sanitize_title_for_path(title)
            dir_name = f"{item_id}-{sanitized_title}"
        else:
            dir_name = item_id

        return (
            self.base_path
            / "tracking"
            / "areas"
            / "myadapter"
            / dir_name
            / "README.md"
        )

    def update_readme(
        self, readme_path: Path, data: ItemData, item: TrackedItem
    ) -> None:
        """Update README.md with item data.

        Updates Status field while preserving all manual content.

        Args:
            readme_path: Path to the README.md file
            data: New data from external system
            item: The tracked item
        """
        item_id = item.id

        # Create directory if needed
        readme_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if README exists
        if readme_path.exists():
            content = readme_path.read_text()
            content = self._update_existing_readme(content, data)
        else:
            content = self._create_new_readme(item_id, data)

        readme_path.write_text(content)

    def _create_new_readme(self, item_id: str, data: ItemData) -> str:
        """Create new README.md content."""
        return f"""# {item_id}: {data.title}

**Status**: {data.status}

## Overview
[Add context about this item here]

## Notes
[Add notes, decisions, and important information here]
"""

    def _update_existing_readme(self, content: str, data: ItemData) -> str:
        """Update existing README.md content.

        Updates Status field while preserving manual content.
        """
        # Update Status field
        status_pattern = r"\*\*Status\*\*:\s*.*"
        content = re.sub(
            status_pattern,
            f"**Status**: {data.status}",
            content,
        )

        return content
```

**Run tests (should PASS)**:
```bash
uv run pytest tests/unit/adapters/test_myadapter.py -v
```

### Step 3: Check Coverage

```bash
uv run pytest tests/unit/adapters/test_myadapter.py --cov=cli.adapters.myadapter --cov-report=term-missing
```

**Target**: 90%+ coverage for adapters.

### Step 4: Integration (Phase 5)

Once sync orchestration is implemented, register your adapter:

```python
# In cli/adapters/__init__.py or sync.py
from cli.adapters.myadapter import MyAdapter

AVAILABLE_ADAPTERS = {
    "jira": JiraAdapter,
    "myadapter": MyAdapter,
}
```

### Step 5: Document Adapter

Add documentation to README.md:

```markdown
### MyAdapter

**Status**: ✅ Complete

- Syncs items from [External System] via [CLI/API]
- Fetches: [list fields]
- Updates: README.md while preserving your notes
- Requires: [dependencies/environment variables]
```

---

## Code Quality Standards

### Type Hints

All functions must have type hints:

```python
def my_function(item: TrackedItem, path: Path) -> ItemData:
    """Function with type hints."""
    pass
```

### Docstrings

All public functions and classes must have docstrings:

```python
def my_function(item: TrackedItem) -> str:
    """Brief description of what this does.

    Args:
        item: Description of parameter

    Returns:
        Description of return value

    Raises:
        RuntimeError: When something goes wrong
    """
    pass
```

### Code Style

- **Formatter**: ruff (configured in pyproject.toml)
- **Line length**: 88 characters (Black default)
- **Imports**: Sorted with isort standards
- **Naming**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`

### Error Handling

- Use descriptive error messages
- Raise appropriate exceptions (ValueError, RuntimeError, FileNotFoundError)
- Include context in error messages

```python
# Good
raise ValueError(f"Invalid config: missing 'items' key in {config_path}")

# Bad
raise ValueError("Invalid config")
```

---

## Git Commit Guidelines

We follow https://cbea.ms/git-commit/

### The Seven Rules

1. **Separate subject from body with blank line**
2. **Limit subject line to 50 characters**
3. **Capitalize the subject line**
4. **Do not end subject line with a period**
5. **Use imperative mood** ("Add feature" not "Added feature")
6. **Wrap body at 72 characters**
7. **Use body to explain what and why, not how**

### Commit Message Template

```
Add brief description of change in imperative mood

Longer explanation of the change, explaining WHAT changed and WHY
it was necessary. Wrap at 72 characters.

The implementation details (HOW) are in the code - the commit message
should explain the reasoning and context.

Related to #123
```

### Examples

**Good**:
```
Add Jira adapter with jirahhh integration

Implements the first concrete adapter for syncing Jira issues using
the jirahhh CLI tool. The adapter fetches issue metadata (status,
assignee, summary) and updates README.md files while preserving
all manually-added content.

Following the Adapter ABC interface with 90%+ test coverage.
```

**Bad**:
```
fixed bug

updated the code to fix the bug
```

### Commit Frequency

- Commit **logical units** of work
- One feature/fix per commit
- Don't commit broken code
- Don't commit untested code

---

## Pull Request Process

### Before Creating PR

1. **Ensure all tests pass**:
   ```bash
   uv run pytest
   ```

2. **Check coverage meets requirements**:
   ```bash
   uv run pytest --cov=cli --cov-report=term-missing
   ```
   - Overall: 85%+
   - Adapters: 90%+
   - Core modules: 95%+

3. **Format code**:
   ```bash
   uv run ruff format .
   uv run ruff check .
   ```

4. **Update documentation** if needed:
   - README.md for user-facing features
   - ARCHITECTURE.md for design changes
   - Docstrings for new APIs

### Creating the PR

1. **Clear title**: Use imperative mood, be descriptive
   - Good: "Add GitHub adapter with PR tracking"
   - Bad: "update code"

2. **Description template**:
   ```markdown
   ## Summary
   Brief description of what this PR does.

   ## Changes
   - Added X
   - Modified Y
   - Fixed Z

   ## Testing
   - Added N new tests
   - All tests passing
   - Coverage: X%

   ## Documentation
   - Updated README.md
   - Added docstrings

   ## Related Issues
   Fixes #123
   ```

3. **Link related issues**: Use "Fixes #123" or "Related to #456"

### PR Review Process

1. Maintainer reviews code
2. Address feedback with new commits
3. Once approved, maintainer will merge

---

## Testing Requirements

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Overall | 85%+ | 94% |
| Core modules (base, init, agenda) | 95%+ | 94-100% |
| Adapters | 90%+ | 98% |

### Running Tests

```bash
# All tests
uv run pytest

# Specific module
uv run pytest tests/unit/test_init_command.py

# With coverage
uv run pytest --cov=cli --cov-report=term-missing

# HTML coverage report
uv run pytest --cov=cli --cov-report=html
open htmlcov/index.html

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (mocked dependencies)
│   ├── test_adapter_interface.py
│   ├── test_init_command.py
│   ├── test_agenda_command.py
│   ├── test_cli.py
│   └── adapters/
│       ├── test_jira.py
│       └── test_myadapter.py
└── integration/             # Integration tests (real files)
    └── test_jira_sync_flow.py
```

### Test Fixtures

Common fixtures in `tests/conftest.py`:

- `temp_dir`: Temporary directory for file operations
- `sample_config`: Example gameplan.yaml content
- `config_file`: Pre-created gameplan.yaml in temp_dir

Use these in your tests:

```python
def test_something(temp_dir, sample_config):
    """Test using shared fixtures."""
    adapter = MyAdapter(sample_config, temp_dir)
    # ... test code
```

---

## Documentation Standards

### README.md

- Keep user-focused
- Include quick start guide
- Show example usage
- Link to detailed docs (ARCHITECTURE.md, CONTRIBUTING.md)

### ARCHITECTURE.md

- Explain design decisions
- Document data flows
- Describe component interactions
- Include diagrams where helpful

### Code Comments

**DO** comment:
- Complex algorithms
- Non-obvious behavior
- Workarounds for bugs
- Important business logic

**DON'T** comment:
- Obvious code (`i += 1  # increment i`)
- Redundant docstrings
- Commented-out code (delete it)

### Inline Documentation

```python
# Good: Explains WHY
# Use regex instead of markdown parser for performance
# and to handle human-edited files gracefully
content = re.sub(pattern, replacement, content)

# Bad: Explains WHAT (code already shows this)
# Replace pattern with replacement
content = re.sub(pattern, replacement, content)
```

---

## Questions?

- **Issues**: https://github.com/shanemcd/gameplan-cli/issues
- **Email**: me@shanemcd.com
- **Discussions**: https://github.com/shanemcd/gameplan-cli/discussions

---

## License

By contributing to Gameplan, you agree that your contributions will be licensed under the Apache 2.0 License.

---

**Thank you for contributing to Gameplan!**
