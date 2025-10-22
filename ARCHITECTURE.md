# Gameplan Architecture

**A local-first, test-driven CLI for tracking work items across multiple external systems using markdown.**

---

## Problem Statement

Knowledge workers often track work across multiple systems (GitHub, Jira, Linear, etc.), leading to:

- **Context fragmentation**: Important context scattered across issues, PRs, tickets
- **Manual sync overhead**: Copying status updates between systems
- **Lost decisions**: Why something was done gets buried in comment threads
- **Poor context switching**: Hard to remember "what was I doing on this?" weeks later

**Gameplan solves this** by providing a unified, local-first knowledge base that automatically syncs data from external systems while preserving human-added context.

---

## Core Principles

### 1. Local-First, Markdown-Based
- All tracking data lives in local markdown files
- Human-readable, version-controllable, greppable
- No vendor lock-in, no proprietary formats
- Works offline (sync when connected)

### 2. Automatic Sync, Manual Enrichment
- **Machines handle**: Pulling status, assignees from external systems
- **Humans handle**: Adding context, decisions, meeting notes, analysis
- Clear separation: auto-updated fields vs. manual sections

### 3. Test-Driven Development
- Write tests first (RED)
- Implement minimum code to pass (GREEN)
- Refactor without changing behavior (REFACTOR)
- Maintain 85%+ coverage

### 4. Extensible by Design
- Pluggable adapters for different tracking systems
- Configurable agenda sections
- Adapter ABC enforces consistency

### 5. Zero Lock-In
- External systems remain source of truth
- Gameplan is a view + enrichment layer
- Can stop using it anytime without data loss

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     External Systems                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   Jira   │  │  GitHub  │  │  Linear  │  ...             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼──────────────────────────┘
        │             │             │
        │             │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                      Sync Adapters                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Jira    │  │  GitHub  │  │  Linear  │  ...             │
│  │ Adapter  │  │ Adapter  │  │ Adapter  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼──────────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │   Configuration Layer    │
        │    (gameplan.yaml)       │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │    Storage Layer         │
        │  (tracking/areas/)       │
        │  - README.md per item    │
        │  - Auto + Manual content │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │    Workflow Layer        │
        │  - AGENDA.md             │
        │  - Command-driven        │
        │  - Manual sections       │
        └──────────────────────────┘
```

---

## Component Details

### 1. Configuration Layer (gameplan.yaml)

**Purpose**: Single source of truth for what to track

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
      description: "What's urgent today"
      # Manual section

    - name: "Calendar"
      emoji: "📅"
      command: "date"
      description: "Today's schedule"
      # Command-driven section
```

**Responsibilities**:
- Define all tracked items
- Configure agenda sections
- Provide adapter-specific settings

---

### 2. Adapter Interface

**Purpose**: Standardize how adapters integrate with external systems

All adapters must implement the `Adapter` ABC from `cli/adapters/base.py`:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

class Adapter(ABC):
    """Base adapter interface."""

    @abstractmethod
    def get_adapter_name(self) -> str:
        """Return adapter name (e.g., 'jira')."""
        pass

    @abstractmethod
    def load_config(self, config: Dict[str, Any]) -> List[TrackedItem]:
        """Parse config and return tracked items."""
        pass

    @abstractmethod
    def fetch_item_data(self, item: TrackedItem, since: Optional[str] = None) -> ItemData:
        """Fetch data from external system."""
        pass

    @abstractmethod
    def get_storage_path(self, item: TrackedItem, title: Optional[str] = None) -> Path:
        """Get path to item's README.md."""
        pass

    @abstractmethod
    def update_readme(self, readme_path: Path, data: ItemData, item: TrackedItem):
        """Update README with new data, preserving manual content."""
        pass
```

**Data Classes**:

```python
@dataclass
class TrackedItem:
    id: str              # "PROJ-123", "owner/repo#123"
    adapter: str         # "jira", "github"
    metadata: Dict       # Adapter-specific data

@dataclass
class ItemData:
    title: str           # Item title/summary
    status: str          # Current status
    updates: List[Dict]  # Recent changes
    raw_data: Dict       # Full API response
```

**Design Points**:
- **ABC enforcement**: Python ABC ensures all methods implemented
- **Idempotent**: Running sync multiple times has same effect
- **Non-destructive**: Never removes manual content
- **Section-aware**: Updates specific fields via regex

---

### 3. Jira Adapter (cli/adapters/jira.py)

**Current Implementation**: Phase 4 complete (98% test coverage)

**How it works**:
1. Calls `jirahhh view ISSUE-KEY --env prod --json`
2. Parses JSON response (summary, status, assignee)
3. Creates/updates `tracking/areas/jira/PROJ-123-title/README.md`
4. Updates Status and Assignee fields
5. Preserves all manual content (Overview, Notes sections)

**Directory Naming**:
```
tracking/areas/jira/PROJ-123-fix-api-bug/README.md
                    ^^^^^^^^^-^^^^^^^^^^^
                    issue key  sanitized title
```

**README Structure**:
```markdown
# PROJ-123: Fix API Bug

**Status**: In Progress       ← Auto-updated
**Assignee**: johndoe          ← Auto-updated

## Overview                    ← Manual
User-written context here

## Notes                       ← Manual
- Important decisions
- Meeting notes
```

---

### 4. Storage Layer

**Purpose**: Organize tracked items predictably

**Structure**:
```
tracking/
└── areas/
    └── jira/
        ├── PROJ-123-title/
        │   └── README.md
        └── archive/
            └── (completed items)
```

**README.md Properties**:
- Each tracked item gets its own directory
- README.md is primary file
- Clear markers for auto-updated vs manual
- Archive preserves history

---

### 5. Agenda System

**Purpose**: Daily planning artifact with configurable sections

**Two Section Types**:

1. **Manual Sections** (user-maintained):
   ```yaml
   - name: "Focus & Priorities"
     emoji: "🎯"
     description: "What's urgent today"
   ```

   Rendered as:
   ```markdown
   ## 🎯 Focus & Priorities
   [What's urgent today]
   ```

2. **Command-Driven Sections** (auto-populated):
   ```yaml
   - name: "Calendar"
     emoji: "📅"
     command: "date"
   ```

   Rendered as:
   ```markdown
   ## 📅 Calendar
   Wed Oct 22 15:30:00 UTC 2025
   ```

**Commands**:
- `gameplan agenda init` - Create AGENDA.md from config
- `gameplan agenda view` - Display AGENDA.md
- `gameplan agenda refresh` - Update command sections

**Implementation** (cli/agenda.py):
- Reads gameplan.yaml agenda config
- Generates sections with date header
- Runs shell commands via subprocess
- Preserves manual sections during refresh

---

## Data Flow

### Init Flow

```
User: gameplan init
  │
  ├─▶ Create tracking/areas/jira/
  ├─▶ Generate gameplan.yaml
  └─▶ Print next steps

User: gameplan agenda init
  │
  ├─▶ Read gameplan.yaml
  ├─▶ Generate AGENDA.md with sections
  └─▶ Write to disk
```

### Sync Flow (Phase 5 - planned)

```
User: gameplan sync jira
  │
  ├─▶ Load gameplan.yaml
  │
  ├─▶ For each Jira item:
  │   ├─▶ Call jirahhh CLI
  │   ├─▶ Parse JSON response
  │   ├─▶ Get storage path
  │   └─▶ Update README (preserve manual content)
  │
  └─▶ Done
```

### Agenda Refresh Flow

```
User: gameplan agenda refresh
  │
  ├─▶ Load gameplan.yaml
  ├─▶ Read current AGENDA.md
  │
  ├─▶ For each command-driven section:
  │   ├─▶ Run command (subprocess)
  │   ├─▶ Capture output
  │   └─▶ Replace section content
  │
  ├─▶ Preserve all manual sections
  └─▶ Write updated AGENDA.md
```

---

## Extension Points

### Adding New Adapters

**TDD Approach**:

1. **Write tests first** (`tests/unit/adapters/test_myadapter.py`):
   - Test config parsing
   - Test data fetching (mock API/CLI)
   - Test README updates
   - Test manual content preservation
   - Test idempotency

2. **Implement adapter** (`cli/adapters/myadapter.py`):
   ```python
   from cli.adapters.base import Adapter, TrackedItem, ItemData

   class MyAdapter(Adapter):
       def get_adapter_name(self) -> str:
           return "myadapter"

       # Implement other abstract methods...
   ```

3. **Wire up to sync** (Phase 5):
   - Register in adapter registry
   - Add to sync orchestration

**See CONTRIBUTING.md for detailed guide**

---

## Testing Infrastructure

**Test Coverage**: 76 tests, 89-100% on core modules

**Test Organization**:
```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_adapter_interface.py   (19 tests, 89% coverage)
│   ├── test_init_command.py        (14 tests, 100% coverage)
│   ├── test_agenda_command.py      (17 tests, 94% coverage)
│   ├── test_cli.py                 (8 integration tests)
│   └── adapters/
│       └── test_jira.py            (18 tests, 98% coverage)
└── integration/
    └── (future E2E tests)
```

**Running Tests**:
```bash
# All tests with coverage
uv run pytest --cov=cli --cov-report=term-missing

# Specific module
uv run pytest tests/unit/adapters/test_jira.py -v

# HTML coverage report
uv run pytest --cov=cli --cov-report=html
```

**Coverage Requirements** (pyproject.toml):
```toml
[tool.coverage.report]
fail_under = 85
```

---

## Design Decisions

### Why Markdown?
- **Human-readable**: No special tools needed
- **Version-controllable**: Git tracks all changes
- **Greppable**: Full-text search with standard tools
- **Portable**: No vendor lock-in
- **Future-proof**: Plain text lasts forever

### Why Local-First?
- **Offline work**: No internet required
- **Fast**: No API rate limits or network latency
- **Private**: Sensitive context stays local
- **Control**: You own your data

### Why External Systems as Source of Truth?
- **Collaboration**: Teams use GitHub/Jira for communication
- **Integration**: Established workflows
- **Authority**: Official status changes
- **Gameplan = View Layer**: Enriches, doesn't replace

### Why Python ABC for Adapters?
- **Type safety**: Enforces interface contract
- **IDE support**: Autocomplete and type checking
- **Documentation**: Interface is self-documenting
- **Testability**: Easy to mock and test

### Why Regex for README Updates?
- **Simple**: No AST parsing needed
- **Flexible**: Works with human-edited files
- **Predictable**: Clear field markers (`**Status**:`)
- **Future**: Could upgrade to proper markdown parser if needed

---

## Future Considerations

### Potential Features

1. **Sync Orchestration** (Phase 5)
   - `gameplan sync` command
   - Adapter registry
   - Last-sync timestamps

2. **GitHub Adapter**
   - Track issues and PRs
   - Fetch comments
   - Update status

3. **Advanced Agenda**
   - Action items with checkboxes
   - LOGBOOK.md automatic archival
   - Tracked items integration

4. **Polish**
   - Watch mode for continuous sync
   - Notification system
   - Web UI (optional)

### Challenges to Solve

1. **Merge Conflicts**: Manual edits during sync
   - Current: Last write wins
   - Future: 3-way merge, conflict markers

2. **Large Repos**: Hundreds of tracked items
   - Current: Sync all items
   - Future: Incremental sync, caching, parallel

3. **Schema Evolution**: README structure changes
   - Current: Manual migration
   - Future: Version tracking, auto-migrations

---

## Comparison to Alternatives

### vs. Jira/Linear/Asana
- **Gameplan**: Local, fast, flexible, no vendor lock-in
- **SaaS**: Collaboration features, hosted, structured workflows

### vs. Notion/Obsidian
- **Gameplan**: Automatic sync from external systems
- **Notes**: General-purpose, manual linking

### vs. IDE Extensions
- **Gameplan**: Cross-system, agenda-centric, preserved context
- **IDE**: Editor-specific, view-only

**Gameplan's niche**: Developers/architects tracking work across multiple technical systems who want local-first, markdown-based documentation with automatic sync.

---

## Implementation Status

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed progress.

**Completed (Phase 1-4)**:
- ✅ Base adapter interface
- ✅ Init command
- ✅ Agenda system (simplified)
- ✅ Jira adapter
- ✅ CLI integration

**Next**:
- ⏳ Sync orchestration (Phase 5)
- ⏳ Additional adapters

---

*Last updated: 2025-10-22*
*76 tests passing, 89-100% coverage*
