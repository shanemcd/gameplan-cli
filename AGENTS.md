# Claude Code Reference for Gameplan CLI

This is the AI assistant reference guide for the **gameplan-cli** project - a local-first, test-driven CLI for tracking work across multiple systems with markdown.

**See @README.md for project overview and @PROJECT_PLAN.md for implementation roadmap.**

---

## Project Overview

**Gameplan** is a CLI tool that helps users track work items across external systems (Jira, with GitHub and others coming soon) using local markdown files and a pluggable adapter architecture.

### Core Principles

1. **Local-first**: All data in markdown files, version controlled with git
2. **Test-Driven Development**: Write tests first (RED), then implement (GREEN), then refactor (REFACTOR)
3. **Adapter pattern**: Pluggable integrations via ABC interface
4. **Workflow-agnostic**: Users configure their own commands and sections

### Repository Structure

```
gameplan-cli/
├── cli/                      # Main source code
│   ├── __init__.py
│   ├── cli.py                # CLI entry point (argparse)
│   ├── init.py               # Init command
│   ├── agenda.py             # Agenda commands
│   ├── sync.py               # Sync orchestration
│   ├── adapters_cmd.py       # Adapter discovery
│   └── adapters/
│       ├── __init__.py
│       ├── base.py           # ABC interface
│       └── jira.py           # Jira adapter
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── unit/                 # Unit tests (mocked dependencies)
│   │   ├── test_adapter_interface.py
│   │   ├── test_init_command.py
│   │   ├── test_agenda_command.py
│   │   └── adapters/
│   │       └── test_jira.py
│   └── integration/          # Integration tests (real files, mocked APIs)
│       └── test_jira_sync_flow.py
├── pyproject.toml            # Package config
├── PROJECT_PLAN.md           # Implementation roadmap
├── README.md                 # Public README
├── ARCHITECTURE.md           # Architecture documentation
├── CONTRIBUTING.md           # Contributing guide
└── LICENSE                   # Apache 2.0 license
```

---

## Test-Driven Development Workflow

**CRITICAL: Always follow TDD when adding new features.**

### The TDD Cycle

1. **RED Phase**: Write failing tests first
   - Think through the API/interface before implementation
   - Write comprehensive test cases covering happy path and edge cases
   - Run tests to verify they fail: `uv run pytest path/to/test_file.py -v`

2. **GREEN Phase**: Implement minimum code to pass tests
   - Implement just enough to make all tests pass
   - Don't over-engineer or add features not covered by tests
   - Run tests to verify they pass: `uv run pytest path/to/test_file.py -v`

3. **REFACTOR Phase**: Improve code without changing behavior
   - Clean up duplication
   - Improve naming and structure
   - Run tests to verify refactoring didn't break anything

### Coverage Targets

- **Overall**: 85%+
- **Core modules** (base, init, agenda): 95%+
- **Adapters**: 90%+
- **Integration tests**: All major workflows covered

**Run coverage**: `uv run pytest --cov=cli --cov-report=term-missing`

### Example TDD Session

```python
# 1. RED - Write test first (tests/unit/test_new_feature.py)
def test_new_feature_does_something():
    """New feature should do something specific."""
    result = new_feature()
    assert result == "expected"

# Run: uv run pytest tests/unit/test_new_feature.py -v
# Result: ModuleNotFoundError (expected failure)

# 2. GREEN - Implement minimum code (cli/new_feature.py)
def new_feature():
    return "expected"

# Run: uv run pytest tests/unit/test_new_feature.py -v
# Result: 1 passed (success!)

# 3. REFACTOR - Improve if needed
# (In this simple case, no refactoring needed)
```

---

## Git Commit Guidelines

**ALWAYS follow https://cbea.ms/git-commit/ when creating commits.**

### The Seven Rules

1. Separate subject from body with blank line
2. Limit subject line to 50 characters
3. Capitalize the subject line
4. Do not end subject line with a period
5. Use imperative mood ("Add feature" not "Added feature")
6. Wrap body at 72 characters
7. Use body to explain "what" and "why", not "how"

### Commit Message Template

```
Add feature name in imperative mood

Explain what the feature does and why it's needed. Focus on the
problem being solved rather than implementation details.

Key changes:
- Created X to handle Y
- Updated Z to support W
- Added tests with N% coverage

Following TDD approach with comprehensive test suite.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Examples

✅ **Good**:
```
Add Jira adapter with jirahhh integration

Implements the first concrete adapter for syncing Jira issues using
the jirahhh CLI tool. The adapter fetches issue metadata (status,
assignee, summary) and updates README.md files while preserving
all manually-added content.

Following the Adapter ABC interface with 90%+ test coverage.
```

❌ **Bad**:
```
jira stuff

added jira adapter and fixed some bugs
```

---

## Adapter Development

All adapters must implement the `Adapter` ABC from `cli/adapters/base.py`.

### Required Methods

```python
from cli.adapters.base import Adapter, TrackedItem, ItemData

class MyAdapter(Adapter):
    def get_adapter_name(self) -> str:
        """Return adapter name (e.g., 'jira', 'github')."""
        return "myadapter"

    def load_config(self, config: Dict[str, Any]) -> List[TrackedItem]:
        """Parse gameplan.yaml config and return tracked items."""
        pass

    def fetch_item_data(self, item: TrackedItem, since: Optional[str] = None) -> ItemData:
        """Fetch current data from external system."""
        pass

    def get_storage_path(self, item: TrackedItem, title: Optional[str] = None) -> Path:
        """Return path to item's README.md file."""
        pass

    def update_readme(self, readme_path: Path, data: ItemData, item: TrackedItem):
        """Update README.md with new data, preserving manual content."""
        pass
```

### TDD Process for New Adapter

1. **Write tests first**: `tests/unit/adapters/test_myadapter.py`
   - Test config parsing
   - Test data fetching (mock external API/CLI)
   - Test README updates (preserve manual content)
   - Test idempotency
   - Test error handling

2. **Implement adapter**: `cli/adapters/myadapter.py`
   - Inherit from `Adapter`
   - Implement all abstract methods
   - Use subprocess/requests to call external system
   - Parse responses into `ItemData`

3. **Write integration tests**: `tests/integration/test_myadapter_sync_flow.py`
   - End-to-end sync flow
   - README creation and updates
   - Manual content preservation

4. **Register adapter**: Update `cli/adapters_cmd.py` with adapter metadata

### Testing Adapters

```python
# tests/unit/adapters/test_myadapter.py
import pytest
from unittest.mock import patch, MagicMock
from cli.adapters.myadapter import MyAdapter

class TestMyAdapterBasics:
    def test_adapter_name(self, temp_dir):
        """Adapter reports correct name."""
        adapter = MyAdapter({}, temp_dir)
        assert adapter.get_adapter_name() == "myadapter"

class TestMyAdapterConfigLoading:
    def test_load_config_parses_items(self, temp_dir):
        """Adapter parses config correctly."""
        config = {"items": [{"id": "ITEM-1"}]}
        adapter = MyAdapter(config, temp_dir)
        items = adapter.load_config(config)

        assert len(items) == 1
        assert items[0].id == "ITEM-1"

class TestMyAdapterFetchItemData:
    @patch('subprocess.run')
    def test_fetch_calls_external_cli(self, mock_run, temp_dir):
        """fetch_item_data calls external CLI tool."""
        # Mock subprocess response
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"title": "Test", "status": "Open"}'
        )

        adapter = MyAdapter({}, temp_dir)
        item = TrackedItem(id="ITEM-1", adapter="myadapter")
        data = adapter.fetch_item_data(item)

        assert data.title == "Test"
        assert data.status == "Open"
        mock_run.assert_called_once()
```

---

## CLI Command Structure

The CLI uses argparse with subcommands:

```bash
gameplan init                      # Initialize new gameplan
gameplan init -d ~/my-gameplan     # Init in specific directory
gameplan adapters list             # Show enabled adapters
gameplan adapters list --available # Show all available adapters
gameplan sync                      # Sync all adapters
gameplan sync jira                 # Sync Jira only
gameplan agenda init               # Create AGENDA.md
gameplan agenda view               # View AGENDA.md
gameplan agenda refresh            # Update command-driven sections
```

### Adding New Commands

1. **Write tests first**: `tests/unit/test_mycommand.py`
2. **Implement command function**: `cli/mycommand.py`
3. **Wire up in CLI**: Add subparser in `cli/cli.py`
4. **Update help text**: Add clear descriptions and examples

---

## File Management Policy

### NEVER Create Files Unless Absolutely Necessary

- **ALWAYS prefer editing existing files** over creating new ones
- Only create files when:
  - Explicitly requested by user
  - Required by implementation (e.g., new test file for new feature)
  - Part of the core functionality (e.g., init creates gameplan.yaml)

### Editing Guidelines

- Use the `Edit` tool for modifying existing files
- Preserve existing structure and formatting
- When updating documentation, maintain consistency with existing style

---

## Helping Users

### When User Asks About gameplan

1. **Check PROJECT_PLAN.md** first for current implementation status
2. **Check README.md** for quick start and overview
3. **Check ARCHITECTURE.md** (when available) for design details

### Common User Requests

**"Initialize a new gameplan"**:
```bash
gameplan init
# or
gameplan init -d /path/to/directory
```

**"Add a new Jira item to track"**:
Edit `gameplan.yaml`:
```yaml
areas:
  jira:
    items:
      - issue: "PROJ-123"
        env: "prod"
```

**"Sync my tracked items"**:
```bash
gameplan sync
```

**"How do I add a new adapter?"**:
See ARCHITECTURE.md (when created) or PROJECT_PLAN.md Phase 4 for TDD guide.

### When User Reports Issues

1. **Verify setup**: Check if they've run `uv sync` to install dependencies
2. **Check tests**: Run relevant test suite to verify functionality
3. **Review error**: Help debug based on error message
4. **Fix with TDD**: If bug found, write failing test first, then fix

---

## Development Commands

### Setup

```bash
# Clone repository
git clone https://github.com/shanemcd/gameplan-cli.git
cd gameplan-cli

# Install dependencies (including dev)
uv sync --extra dev

# Verify installation
uv run gameplan --help
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_init_command.py -v

# Run with coverage
uv run pytest --cov=cli --cov-report=term-missing

# Run integration tests only
uv run pytest tests/integration/ -v

# View HTML coverage report
uv run pytest --cov=cli --cov-report=html
open htmlcov/index.html
```

### Linting

```bash
# Run ruff
uv run ruff check cli/ tests/

# Auto-fix issues
uv run ruff check --fix cli/ tests/
```

---

## Current Implementation Status

**See PROJECT_PLAN.md for detailed status tracking.**

### Completed (Shipped: ✅)

- **Phase 1: Foundation**
  - Base adapter interface (Adapter ABC, TrackedItem, ItemData)
  - Project structure and configuration
  - Test infrastructure

- **Phase 2: Init Command**
  - `gameplan init` command
  - Directory scaffolding (tracking/areas/)
  - gameplan.yaml generation with helpful comments

- **Phase 3: Agenda System**
  - `gameplan agenda init/view/refresh` commands
  - Command-driven and manual sections
  - Date header updates

- **Phase 4: Jira Adapter**
  - Full Jira integration via jirahhh CLI
  - README.md creation and updates
  - Manual content preservation

- **Phase 5: Sync Orchestration**
  - `gameplan sync` command
  - Change detection with metadata
  - Activity Log for issue updates
  - Rich tracked items formatting

**Test Coverage**: 76 tests, 89-100% coverage on core modules

### In Progress (Current: 🚧)

- Phase 6: Documentation polish for public release

### Upcoming (Planned: ⏳)

- Phase 7: Release prep (CI/CD, PyPI publishing)
- GitHub adapter
- Advanced agenda features

---

## Important Context

### External Dependencies

- **jirahhh**: Public CLI for Jira API access - https://github.com/shanemcd/jirahhh
  - Used by Jira adapter
  - Requires JIRA_* environment variables
  - Installation: `uvx jirahhh`

### Configuration Format

**gameplan.yaml**:
```yaml
areas:
  jira:
    items:
      - issue: "PROJ-123"
        env: "prod"

agenda:
  sections:
    - name: "Focus & Priorities"
      emoji: "🎯"
      description: "What's urgent/important today"
      # Manual section - user edits

    - name: "Calendar"
      emoji: "📅"
      command: "echo 'No meetings today'"
      description: "Today's schedule"
      # Command-driven - auto-populated
```

### Directory Structure After Init

```
my-gameplan/
├── gameplan.yaml             # Configuration
└── tracking/
    └── areas/
        └── jira/
            ├── PROJ-123-title/
            │   └── README.md
            └── archive/
                └── (completed items)
```

---

## Best Practices

### For AI Assistants

1. **Always follow TDD**: Tests first, then implementation
2. **Check PROJECT_PLAN.md**: Know what phase we're in
3. **Maintain coverage**: Aim for 85%+ on all new code
4. **Follow git commit guidelines**: Imperative mood, 50 char subject
5. **Use TodoWrite tool**: Track progress on multi-step tasks
6. **Reference PROJECT_PLAN.md**: When context window fills, this is our source of truth
7. **Don't create unnecessary files**: Prefer editing existing files

### For Code Quality

1. **Type hints**: Use type hints for all function signatures
2. **Docstrings**: Document all public functions and classes
3. **Error handling**: Raise clear exceptions with helpful messages
4. **Testing**: Cover happy path, edge cases, and error conditions
5. **DRY**: Extract common logic into utilities

### For Documentation

1. **Update PROJECT_PLAN.md**: Mark tasks complete, update coverage stats
2. **Update README.md**: Keep examples current
3. **Write clear commit messages**: Follow the 7 rules
4. **Document breaking changes**: Highlight in commit message body

---

## Quick Reference

### Common File Locations

- **Implementation roadmap**: `PROJECT_PLAN.md`
- **Project README**: `README.md`
- **Base adapter interface**: `cli/adapters/base.py`
- **Test fixtures**: `tests/conftest.py`
- **Coverage config**: `pyproject.toml` (tool.coverage section)

### Common Commands

```bash
# Run tests with coverage
uv run pytest --cov=cli --cov-report=term-missing

# Run specific test class
uv run pytest tests/unit/test_init_command.py::TestInitGameplan -v

# Check coverage HTML
uv run pytest --cov=cli --cov-report=html && open htmlcov/index.html

# Verify package installs
uv sync && uv run gameplan --help
```

### Coverage Requirements

From `pyproject.toml`:
```toml
[tool.coverage.report]
fail_under = 85
```

Any PR with <85% coverage will fail CI (when CI is set up).

---

## Maintenance

### Keep This Documentation Updated

Update AGENTS.md when:
- New phases are completed in PROJECT_PLAN.md
- New commands are added to the CLI
- Architecture or design patterns change
- Testing strategies evolve
- New dependencies are added

### Review Regularly

- Check if examples are still accurate
- Verify links and references work
- Update status in "Current Implementation Status"
- Sync with PROJECT_PLAN.md progress

---

*Last updated: 2025-10-22*
*Project status: Phase 1-5 complete, Phase 6 (documentation) in progress*
