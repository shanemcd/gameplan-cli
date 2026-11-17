# Gameplan

> **Local-first CLI for tracking work across multiple systems with markdown**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/shanemcd/gameplan-cli/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/shanemcd/gameplan-cli/actions)

**Gameplan** helps you track work items across external systems (Jira, with GitHub and others coming soon) using local markdown files and a pluggable adapter architecture. All data lives locally in human-readable files that you control.

---

## ✨ Features

- 🏠 **Local-first**: All data in markdown files, version controlled with git
- 🔌 **Pluggable adapters**: Easy integration with any tracking system
- 📅 **Smart agenda**: Configurable daily agenda with command-driven sections
- 🧪 **Test-driven**: TDD from the start
- 📝 **Markdown-based**: Human-readable, greppable, no vendor lock-in
- 🤖 **AI-friendly**: Comprehensive documentation for AI assistants

---

## 🚀 Quick Start

### Try It Now (No Installation)

Run gameplan directly from GitHub using `uvx`:

```bash
# Run any gameplan command without cloning
uvx --from git+https://github.com/shanemcd/gameplan-cli gameplan --help

# Initialize a new gameplan
uvx --from git+https://github.com/shanemcd/gameplan-cli gameplan init

# Create and view your agenda
uvx --from git+https://github.com/shanemcd/gameplan-cli gameplan agenda init
uvx --from git+https://github.com/shanemcd/gameplan-cli gameplan agenda view
```

### Installation (For Development)

```bash
# Clone the repository
git clone https://github.com/shanemcd/gameplan-cli.git
cd gameplan-cli

# Install dependencies
uv sync

# Run gameplan
uv run gameplan --help
```

### Initialize Your Gameplan

```bash
# Create a new gameplan repository (use uvx --from or uv run)
gameplan init

# This creates:
# - gameplan.yaml (configuration)
# - tracking/areas/jira/ (tracking directory)
```

### Configure Tracking

Run `gameplan jira populate` to auto-discover your assigned Jira issues, or edit `gameplan.yaml` manually:

```yaml
areas:
  jira:
    env: "prod"
    # Optional: customize the JQL used by `gameplan jira populate`
    # populate:
    #   search: "assignee = currentUser() AND statusCategory != Done"
    items:
      # Manually-added items (never removed by populate)
      - issue: "PROJ-123"
        env: "prod"
      # Items added by `gameplan jira populate` are tagged automatically
      - issue: "PROJ-456"
        env: "prod"
        source: populate

agenda:
  sections:
    - name: "Focus & Priorities"
      emoji: "🎯"
      description: "What's urgent/important today"

    - name: "Calendar"
      emoji: "📅"
      command: "date"
      description: "Today's schedule"

    - name: "Notes"
      emoji: "📔"
      description: "Thoughts and observations"
```

### Create Your Daily Agenda

```bash
# Initialize AGENDA.md
gameplan agenda init

# View your agenda
gameplan agenda view

# Update command-driven sections
gameplan agenda refresh
```

---

## 📖 Usage

### Commands

```bash
# Initialize a new gameplan
gameplan init
gameplan init -d ~/my-gameplan    # Initialize in specific directory

# Manage daily agenda
gameplan agenda init              # Create AGENDA.md
gameplan agenda view              # Display current agenda
gameplan agenda refresh           # Update command-driven sections

# Sync tracked items
gameplan sync                     # Sync all configured adapters
gameplan sync jira                # Sync Jira only

# Populate Jira items from a search
gameplan jira populate            # Uses default or configured JQL
gameplan jira populate --jql "project = MYPROJ" --env staging
```

### Use a custom agenda file (including Rodger pages)

Configuration and tracking remain rooted in the current workspace (or
`GAMEPLAN_BASE_DIR`). Choose the agenda independently with `--path`:

```bash
gameplan agenda init --path "agenda/README.md"
gameplan agenda view --path "agenda/README.md"
gameplan agenda refresh --path "agenda/README.md"
```

Relative paths resolve against the workspace base directory; absolute paths
are also supported. The default remains `AGENDA.md`. Init creates missing
parent directories but refuses to overwrite an existing file. For an existing
Rodger page, use view/refresh rather than init. Refresh preserves leading YAML
frontmatter verbatim and processes completed tasks from the selected agenda,
while keeping `LOGBOOK.md`, configuration, and command working directories at
the workspace root. Generated tracked-item links are relative to the selected
agenda file, not the workspace root. Refresh passes that location to nested
`gameplan agenda tracked-items` commands; standalone formatting also accepts
`gameplan agenda tracked-items --path "agenda/README.md"`. The CLI writes directly to disk: save pending editor
drafts before refreshing and reload the page afterward.

For an editable development installation:

```bash
uv tool install -e ~/github/shanemcd/gameplan-cli/
```

### Example Workflow

```bash
# 1. Initialize your gameplan
cd ~/projects
gameplan init

# 2. Populate tracked items from Jira (auto-discovers your assigned issues)
gameplan jira populate

# 3. Create your daily agenda
gameplan agenda init

# 4. Work throughout the day
#    - Edit AGENDA.md to add focus items, notes
#    - Run `gameplan agenda refresh` to update calendar/commands

# 5. Sync Jira data
gameplan sync jira

# 6. Re-run populate to pick up newly assigned issues
gameplan jira populate
```

---

## 🗂️ Project Structure

After initialization, your gameplan repository looks like:

```
my-gameplan/
├── gameplan.yaml              # Configuration
├── AGENDA.md                  # Daily agenda (after agenda init)
└── tracking/
    └── areas/
        └── jira/
            ├── PROJ-123-fix-api-bug/
            │   └── README.md      # Issue details + your notes
            └── archive/
                └── (completed items)
```

### gameplan.yaml

The configuration file defines what to track and how your agenda works:

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
      # Manual section - you edit this

    - name: "Calendar"
      emoji: "📅"
      command: "gcalcli agenda --tsv"
      description: "Today's meetings"
      # Command-driven - auto-populated
```

### AGENDA.md

Your daily command center, generated from `gameplan.yaml`:

```markdown
# Agenda - Wednesday, October 22, 2025

## 🎯 Focus & Priorities
[What's urgent/important today]

## 📅 Calendar
9:30am - Team Standup
2:00pm - Sprint Planning

## 📔 Notes
[Thoughts and observations]
```

### README.md (per tracked item)

Each tracked item gets its own README:

```markdown
# PROJ-123: Fix API Authentication Bug

**Status**: In Progress
**Assignee**: johndoe

## Overview
API authentication fails when using OAuth tokens due to...

## Notes
- Reproduced locally with test credentials
- Root cause: token expiration not handled
- Fix: Add refresh token logic
```

---

## 🔌 Adapters

Gameplan uses a pluggable adapter architecture. Each adapter integrates with an external tracking system.
- Configurable command path for custom installations

### Available Adapters

**Jira Adapter** (Phase 4 - ✅ Complete)
- Syncs Jira issues via [jirahhh CLI](https://github.com/shanemcd/jirahhh)
- Fetches: status, assignee, summary
- Updates: README.md while preserving your notes
- Supports multiple Jira environments (prod/stage)

**Coming Soon**:
- GitHub adapter (issues, PRs)
- Generic REST API adapter

### Using the Jira Adapter

1. **Install jirahhh**:
   ```bash
   uvx jirahhh --help
   ```

2. **Configure environment variables**:
   ```bash
   export JIRA_URL="https://your-jira.atlassian.net"
   export JIRA_EMAIL="you@example.com"
   export JIRA_API_TOKEN="your-token"
   ```

3. **Populate items from Jira** (recommended):
   ```bash
   # Auto-discover issues assigned to you
   gameplan jira populate

   # Or use a custom JQL query
   gameplan jira populate --jql "project = MYPROJ AND sprint in openSprints()"
   ```

   This searches Jira and updates `gameplan.yaml` automatically. Items added
   by populate are tagged with `source: populate` so they can be refreshed on
   subsequent runs without affecting manually-added items.

   You can also add items manually to `gameplan.yaml`:
   ```yaml
   areas:
     jira:
       items:
         - issue: "PROJ-123"
           env: "prod"
   ```

4. **Sync**:
   ```bash
   gameplan sync jira
   ```

---

## 📚 Documentation

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Implementation roadmap and progress
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture and design decisions
- **[AGENTS.md](AGENTS.md)** - AI assistant reference guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute
- **[LICENSE](LICENSE)** - Apache 2.0 license

---

## 🛠️ Development

### Setup

```bash
# Clone the repository
git clone https://github.com/shanemcd/gameplan-cli.git
cd gameplan-cli

# Install development dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=cli --cov-report=term-missing

# View HTML coverage report
uv run pytest --cov=cli --cov-report=html
open htmlcov/index.html
```

### Project Philosophy

**Test-Driven Development**:
- Write tests first (RED phase)
- Implement minimum code to pass (GREEN phase)
- Refactor without changing behavior (REFACTOR phase)
- Maintain 85%+ overall coverage

**Git Commit Guidelines**:
- Follow [cbea.ms/git-commit](https://cbea.ms/git-commit/)
- Imperative mood: "Add feature" not "Added"
- 50 char subject, 72 char body wrap
- Explain "what" and "why", not "how"

**Code Quality**:
- Type hints on all functions
- Docstrings on all public APIs
- Comprehensive error handling
- Idempotent operations

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for detailed guidelines.

---

## 🗺️ Roadmap

### Completed (Phase 1-6) ✅

- ✅ Base adapter interface with ABC
- ✅ `gameplan init` command
- ✅ Agenda system (init, view, refresh)
- ✅ Jira adapter with change detection and Activity Log
- ✅ `gameplan sync` command
- ✅ Rich tracked items formatting with status emojis
- ✅ CLI integration with full command routing
- ✅ Comprehensive documentation (README, ARCHITECTURE, CONTRIBUTING)
- ✅ Comprehensive test suite

### Next Steps (Phase 7) ⏳

- ✅ **GitHub Actions CI**: Automated testing on push/PR
- ⏳ **v0.1.0 Release**: Tag and prepare for public release
- ⏳ **PyPI Publishing**: Make installable via `pip install gameplan-cli` (optional)

### Future Enhancements

- GitHub adapter for issues and PRs
- Advanced agenda features (checkboxes, logbook, auto-archive)
- Web UI (optional)
- Watch mode for continuous sync
- Export/reporting

See **[PROJECT_PLAN.md](PROJECT_PLAN.md)** for detailed roadmap.

---

## 🤝 Contributing

Contributions are welcome! This project follows strict TDD practices.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Write tests first (RED phase)
4. Implement feature (GREEN phase)
5. Ensure all tests pass: `uv run pytest`
6. Ensure coverage: `uv run pytest --cov=cli`
7. Commit with clear message (see git commit guidelines)
8. Push and create a pull request

### Adding a New Adapter

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for a step-by-step TDD guide for creating adapters.

---

## 📄 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Built with ❤️ following strict TDD practices
- Inspired by the need for local-first work tracking
- Uses [jirahhh](https://github.com/shanemcd/jirahhh) for Jira integration

---

## 📞 Contact

- **Author**: Shane McDonald
- **Email**: me@shanemcd.com
- **Repository**: https://github.com/shanemcd/gameplan-cli
- **Issues**: https://github.com/shanemcd/gameplan-cli/issues

---

**Made with 🤖 and ☕ using [Claude Code](https://claude.com/claude-code)**
