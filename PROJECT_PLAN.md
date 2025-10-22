# Gameplan CLI - Public Release Implementation Plan

**Project Goal**: Generalize the gameplan CLI for public release as an open-source work tracking tool.

**Key Decisions**:
- License: Apache 2.0
- First adapter: Jira (using public jirahhh CLI)
- Agenda system: Phased approach (simple first, features later)
- Development: Test-Driven Development (TDD)
- Git commits: Follow https://cbea.ms/git-commit/ (imperative mood, 50 char subject, 72 char body)

---

## Architecture Overview

**Core Principles**:
1. **Local-first**: All data in markdown files, version controlled
2. **Adapter pattern**: Pluggable integrations via ABC interface
3. **Test-driven**: Write tests first, aim for 85%+ coverage
4. **Workflow-agnostic**: Configurable via gameplan.yaml

**Key Components**:
```
gameplan-cli/
├── cli/
│   ├── __init__.py
│   ├── cli.py              # Main entry point
│   ├── init.py             # Init command
│   ├── agenda.py           # Agenda commands
│   ├── sync.py             # Sync orchestration
│   ├── adapters_cmd.py     # Adapter discovery
│   └── adapters/
│       ├── __init__.py
│       ├── base.py         # ABC interface
│       └── jira.py         # Jira adapter
├── tests/
│   ├── conftest.py         # Shared fixtures
│   ├── test_smoke.py       # Smoke tests
│   ├── unit/
│   │   ├── test_adapter_interface.py
│   │   ├── test_init_command.py
│   │   ├── test_agenda_command.py
│   │   ├── test_adapters_command.py
│   │   └── adapters/
│   │       └── test_jira.py
│   └── integration/
│       └── test_jira_sync_flow.py
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md
├── AGENTS.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## Implementation Phases

### Phase 1: Foundation (CURRENT)
**Goal**: Set up project infrastructure and base adapter interface

#### Tasks:
- [x] Create PROJECT_PLAN.md
- [x] Initialize git repository
- [x] Create pyproject.toml with dependencies
- [x] Set up directory structure (cli/, tests/)
- [x] Add .gitignore for Python
- [x] Write tests for base adapter interface (19 tests)
- [x] Implement cli/adapters/base.py (Adapter ABC, TrackedItem, ItemData)
- [ ] Add Apache 2.0 LICENSE file

**Git Commits**:
1. ✅ `Initialize gameplan-cli project with basic structure`
2. ✅ `Add Python project structure with pyproject.toml`
3. ✅ `Add base adapter interface with comprehensive tests`

**Coverage Achieved**: 89% on base.py (exceeds 85% target)

---

### Phase 2: Init Command
**Goal**: Enable users to bootstrap new gameplan repositories

#### Tasks:
- [ ] Write tests: tests/unit/test_init_command.py
  - Test directory creation (tracking/areas/)
  - Test gameplan.yaml generation
  - Test error handling (already exists)
  - Test --directory and --interactive flags
- [ ] Implement cli/init.py
  - Create directory structure
  - Generate minimal gameplan.yaml
  - Interactive prompts (optional)
- [ ] Write integration test for full init flow
- [ ] Add smoke test for `gameplan init --help`

**Git Commits**:
1. `Add init command with directory scaffolding`
2. `Add interactive mode for init command`

**Coverage Target**: 95%+

**Example Usage**:
```bash
gameplan init
gameplan init -d ~/my-gameplan
gameplan init -i  # Interactive mode
```

---

### Phase 3: Agenda System (Simplified)
**Goal**: Implement basic agenda with command-driven sections

#### Scope (Phase 3a - Simple):
- AGENDA.md initialization from config
- Manual sections (user edits)
- Command-driven sections (run commands, populate output)
- Basic refresh (update command sections only)

#### Deferred to Later (Phase 3b - Advanced):
- Action items with checkboxes
- LOGBOOK.md automatic archival
- Completion tracking with dates
- Tracked items integration

#### Tasks:
- [ ] Write tests: tests/unit/test_agenda_command.py
  - Test template generation from config
  - Test section types (manual vs command-driven)
  - Test refresh preserves manual content
  - Test view command
- [ ] Implement cli/agenda.py
  - `init_agenda()` - create AGENDA.md from gameplan.yaml
  - `view_agenda()` - display AGENDA.md
  - `refresh_agenda()` - update command sections
- [ ] Add example agenda config to gameplan.yaml template

**Git Commits**:
1. `Add agenda init command with configurable sections`
2. `Add agenda refresh to update command-driven sections`
3. `Add agenda view command`

**Coverage Target**: 90%+

**Example gameplan.yaml**:
```yaml
agenda:
  sections:
    - name: "Focus & Priorities"
      emoji: "🎯"
      description: "What's urgent/important today"
      # Manual section - no command

    - name: "Calendar"
      emoji: "📅"
      command: "echo 'No meetings today'"
      description: "Today's schedule"
```

---

### Phase 4: Jira Adapter
**Goal**: Implement first real adapter for Jira issue tracking

#### Prerequisites:
- jirahhh CLI installed and documented
- Base adapter interface complete

#### Tasks:
- [ ] Document jirahhh installation in README
- [ ] Write tests: tests/unit/adapters/test_jira.py
  - Test config parsing (issue, env)
  - Test fetch_item_data (mock jirahhh calls)
  - Test get_storage_path (ISSUE-KEY directory naming)
  - Test update_readme (status/assignee updates, preserve manual content)
  - Test idempotency
- [ ] Implement cli/adapters/jira.py
  - Inherit from Adapter ABC
  - Use subprocess to call jirahhh
  - Parse JSON output
  - Update README sections (Status, Assignee)
- [ ] Write integration test: tests/integration/test_jira_sync_flow.py
  - End-to-end: config → fetch → update README
  - Verify manual content preservation
- [ ] Add JIRA_* environment variable docs

**Git Commits**:
1. `Add Jira adapter with jirahhh integration`
2. `Add integration tests for Jira sync flow`

**Coverage Target**: 90%+

**Example gameplan.yaml**:
```yaml
areas:
  jira:
    items:
      - issue: "PROJ-123"
        env: "prod"
      - issue: "PROJ-456"
        env: "stage"
```

---

### Phase 5: Sync Orchestration
**Goal**: Implement sync command that runs adapters

#### Tasks:
- [ ] Write tests: tests/unit/test_sync_command.py
  - Test adapter loading from config
  - Test sync with last-sync timestamp
  - Test error handling (missing config, API errors)
- [ ] Implement cli/sync.py
  - Load gameplan.yaml
  - Instantiate enabled adapters
  - Run sync for each adapter
  - Track .last-sync timestamps
- [ ] Write tests: tests/unit/test_adapters_command.py
  - Test adapter registry
  - Test list enabled vs available
- [ ] Implement cli/adapters_cmd.py
  - AVAILABLE_ADAPTERS registry
  - list_adapters() with filtering
- [ ] Update cli/cli.py with sync and adapters commands

**Git Commits**:
1. `Add sync command with adapter orchestration`
2. `Add adapters list command for discovery`
3. `Add main CLI with argparse command structure`

**Coverage Target**: 85%+

**Example Usage**:
```bash
gameplan sync              # Sync all adapters
gameplan sync jira         # Sync Jira only
gameplan adapters list     # Show enabled adapters
gameplan adapters list --available  # Show all available
```

---

### Phase 6: Documentation
**Goal**: Create comprehensive public documentation

#### Tasks:
- [ ] Write README.md
  - Quick start (install, init, sync)
  - Core concepts (local-first, adapters, agenda)
  - Example workflows
  - Contributing section
  - Link to ARCHITECTURE.md
- [ ] Write ARCHITECTURE.md
  - Problem statement (generalized)
  - Core principles
  - Adapter interface documentation
  - Data flow diagrams
  - Extension points
  - How to add new adapters (TDD guide)
- [ ] Write AGENTS.md
  - Guidelines for AI assistants
  - How to help users configure gameplan
  - Common workflows and patterns
  - Example interactions
- [ ] Write CONTRIBUTING.md
  - Development setup
  - Running tests
  - Adding adapters (step-by-step TDD)
  - Code style and coverage requirements
  - PR process
- [ ] Add examples/
  - example-gameplan.yaml
  - example-jira-workflow.md

**Git Commits**:
1. `Add comprehensive README with quick start guide`
2. `Add ARCHITECTURE.md with adapter development guide`
3. `Add AGENTS.md for AI assistant integration`
4. `Add CONTRIBUTING.md and example configurations`

---

### Phase 7: Polish & Release Prep
**Goal**: Prepare for initial public release

#### Tasks:
- [ ] Add CI/CD (GitHub Actions)
  - Run tests on push
  - Check coverage requirements
  - Lint with ruff/black
- [ ] Add version management
  - Follow semantic versioning
  - Tag v0.1.0 for initial release
- [ ] Create GitHub repository
  - Add description and topics
  - Set up issue templates
  - Add PR template
- [ ] Write release notes
- [ ] Publish to PyPI (optional)

**Git Commits**:
1. `Add GitHub Actions CI workflow`
2. `Add pre-commit hooks and linting config`
3. `Prepare v0.1.0 release`

---

## Future Enhancements (Post-Release)

### Phase 8: Advanced Agenda Features
- Action items with checkbox syntax
- LOGBOOK.md automatic archival
- Completion tracking with dates
- Tracked items section integration
- Notes and Focus & Priorities management

### Phase 9: Additional Adapters
- GitHub adapter (gh CLI)
- Linear adapter
- Generic REST API adapter

### Phase 10: Power Features
- Watch mode (`gameplan sync --watch`)
- Selective sync by item
- Export/reporting
- Web UI (optional)

---

## Testing Strategy

**Coverage Targets**:
- Overall: 85%+
- Core modules (base, init, agenda): 95%+
- Adapters: 90%+
- Integration tests: All major workflows

**Test Categories**:
1. **Smoke tests**: Basic imports, help text
2. **Unit tests**: Individual functions/classes (mocked dependencies)
3. **Integration tests**: Full flows (real files, mocked external APIs)

**Running Tests**:
```bash
# All tests with coverage
uv run pytest --cov=cli --cov-report=term-missing

# Specific module
uv run pytest tests/unit/test_init_command.py -v

# Integration tests only
uv run pytest tests/integration/ -v

# HTML coverage report
uv run pytest --cov=cli --cov-report=html
```

---

## Git Commit Guidelines

Following https://cbea.ms/git-commit/:

**The Seven Rules**:
1. Separate subject from body with blank line
2. Limit subject line to 50 characters
3. Capitalize the subject line
4. Do not end subject line with a period
5. Use imperative mood ("Add feature" not "Added feature")
6. Wrap body at 72 characters
7. Use body to explain "what" and "why", not "how"

**Example**:
```
Add Jira adapter with jirahhh integration

Implements the first concrete adapter for syncing Jira issues using
the jirahhh CLI tool. The adapter fetches issue metadata (status,
assignee, summary) and updates README.md files while preserving
all manually-added content.

Following the Adapter ABC interface with 90%+ test coverage.
```

---

## Dependencies

**Runtime**:
- Python 3.11+
- pyyaml (config parsing)
- marko (markdown parsing)
- pypandoc (markdown conversion)

**Development**:
- pytest (testing framework)
- pytest-cov (coverage reporting)
- pytest-mock (mocking)

**External Tools** (optional, per adapter):
- jirahhh (Jira adapter) - https://github.com/shanemcd/jirahhh
- gh (GitHub adapter, future)

---

## Progress Tracking

**Status Legend**:
- ⏳ Not started
- 🚧 In progress
- ✅ Complete
- 🚀 Shipped

| Phase | Status | Coverage | Notes |
|-------|--------|----------|-------|
| Phase 1: Foundation | ✅ | 89% | Complete! 19 tests passing |
| Phase 2: Init Command | ⏳ | - | Next up |
| Phase 3: Agenda (Simple) | ⏳ | - | Phased approach |
| Phase 4: Jira Adapter | ⏳ | - | - |
| Phase 5: Sync Orchestration | ⏳ | - | - |
| Phase 6: Documentation | ⏳ | - | - |
| Phase 7: Release Prep | ⏳ | - | - |

---

## Key Reference Links

- **Git commit style**: https://cbea.ms/git-commit/
- **jirahhh CLI**: https://github.com/shanemcd/jirahhh

---

*Last updated: 2025-10-22*
*This plan will be updated as we progress through implementation.*
