"""Tests for the agenda command.

The agenda command manages a daily AGENDA.md file with configurable sections.
Some sections are manual (user-maintained), others are command-driven
(auto-populated by running shell commands).

Also includes tests for logbook functionality - automatic archival of
completed tasks to LOGBOOK.md files.
"""
from pathlib import Path
from datetime import datetime

import pytest
import yaml

from cli.agenda import (
    init_agenda,
    view_agenda,
    refresh_agenda,
    extract_completed_tasks,
    append_to_logbook,
    remove_completed_tasks_from_content,
    process_logbook,
    _extract_issue_key_from_title,
    _get_week_start,
    _format_issue_heading,
    _parse_logbook,
    _build_logbook_content,
)


class TestInitAgenda:
    """Test agenda initialization."""

    def test_init_creates_agenda_file(self, temp_dir, monkeypatch):
        """Init creates AGENDA.md file."""
        monkeypatch.chdir(temp_dir)

        # Create minimal config
        config = {
            "agenda": {
                "sections": [
                    {"name": "Focus", "description": "Today's focus"}
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        init_agenda()

        agenda_file = temp_dir / "AGENDA.md"
        assert agenda_file.exists()
        assert agenda_file.is_file()

    def test_init_agenda_has_date_header(self, temp_dir, monkeypatch):
        """Init creates AGENDA.md with date header."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {"name": "Focus", "description": "Today's focus"}
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        init_agenda()

        content = (temp_dir / "AGENDA.md").read_text()
        today = datetime.now().strftime("%A, %B %d, %Y")
        assert f"# Agenda - {today}" in content

    def test_init_creates_manual_section(self, temp_dir, monkeypatch):
        """Init creates manual section with description."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {
                        "name": "Focus & Priorities",
                        "emoji": "🎯",
                        "description": "What's urgent today"
                    }
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        init_agenda()

        content = (temp_dir / "AGENDA.md").read_text()
        assert "## 🎯 Focus & Priorities" in content
        assert "[What's urgent today]" in content

    def test_init_creates_command_driven_section(self, temp_dir, monkeypatch):
        """Init creates command-driven section with command marker."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {
                        "name": "Calendar",
                        "emoji": "📅",
                        "command": "echo 'No meetings'",
                        "description": "Today's meetings"
                    }
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        init_agenda()

        content = (temp_dir / "AGENDA.md").read_text()
        assert "## 📅 Calendar" in content
        assert "[Run: echo 'No meetings']" in content

    def test_init_creates_section_without_emoji(self, temp_dir, monkeypatch):
        """Init creates section without emoji if not specified."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {"name": "Notes", "description": "Observations"}
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        init_agenda()

        content = (temp_dir / "AGENDA.md").read_text()
        assert "## Notes" in content
        assert "[Observations]" in content

    def test_init_creates_multiple_sections(self, temp_dir, monkeypatch):
        """Init creates multiple sections in order."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {"name": "Focus", "description": "Focus items"},
                    {"name": "Calendar", "command": "date"},
                    {"name": "Notes", "description": "Notes"}
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        init_agenda()

        content = (temp_dir / "AGENDA.md").read_text()
        # Check all sections present
        assert "## Focus" in content
        assert "## Calendar" in content
        assert "## Notes" in content

        # Check order
        focus_pos = content.find("## Focus")
        calendar_pos = content.find("## Calendar")
        notes_pos = content.find("## Notes")
        assert focus_pos < calendar_pos < notes_pos

    def test_init_raises_error_if_agenda_exists(self, temp_dir, monkeypatch):
        """Init raises FileExistsError if AGENDA.md already exists."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [{"name": "Focus", "description": "Focus"}]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # First init succeeds
        init_agenda()

        # Second init should raise error
        with pytest.raises(FileExistsError, match="AGENDA.md already exists"):
            init_agenda()

    def test_init_raises_error_if_no_config(self, temp_dir, monkeypatch):
        """Init raises FileNotFoundError if gameplan.yaml missing."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(FileNotFoundError, match="gameplan.yaml not found"):
            init_agenda()

    def test_init_raises_error_if_no_agenda_section(self, temp_dir, monkeypatch):
        """Init raises ValueError if config missing agenda section."""
        monkeypatch.chdir(temp_dir)

        config = {"areas": {"jira": {"items": []}}}
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(ValueError, match="No 'agenda' section"):
            init_agenda()


class TestViewAgenda:
    """Test viewing agenda."""

    def test_view_returns_agenda_content(self, temp_dir, monkeypatch):
        """View returns AGENDA.md content."""
        monkeypatch.chdir(temp_dir)

        agenda_content = "# Agenda\n\n## Focus\nTest content"
        (temp_dir / "AGENDA.md").write_text(agenda_content)

        result = view_agenda()

        assert result == agenda_content

    def test_view_raises_error_if_no_agenda(self, temp_dir, monkeypatch):
        """View raises FileNotFoundError if AGENDA.md missing."""
        monkeypatch.chdir(temp_dir)

        with pytest.raises(FileNotFoundError, match="AGENDA.md not found"):
            view_agenda()


class TestRefreshAgenda:
    """Test refreshing command-driven sections."""

    def test_refresh_updates_command_section(self, temp_dir, monkeypatch):
        """Refresh updates command-driven section with command output."""
        monkeypatch.chdir(temp_dir)

        # Create config with command
        config = {
            "agenda": {
                "sections": [
                    {
                        "name": "Time",
                        "command": "echo 'Current time'"
                    }
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Create AGENDA.md with placeholder
        agenda_content = """# Agenda

## Time
[Run: echo 'Current time']
"""
        (temp_dir / "AGENDA.md").write_text(agenda_content)

        refresh_agenda()

        # Check that command output replaced placeholder
        updated_content = (temp_dir / "AGENDA.md").read_text()
        assert "Current time" in updated_content
        assert "[Run: echo 'Current time']" not in updated_content

    def test_refresh_preserves_manual_sections(self, temp_dir, monkeypatch):
        """Refresh preserves manual section content."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {"name": "Focus", "description": "Focus items"},
                    {"name": "Time", "command": "echo 'Now'"}
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Create AGENDA.md with manual content
        agenda_content = """# Agenda

## Focus
- Complete important task
- Review PR

## Time
[Run: echo 'Now']
"""
        (temp_dir / "AGENDA.md").write_text(agenda_content)

        refresh_agenda()

        updated_content = (temp_dir / "AGENDA.md").read_text()
        # Manual content should be preserved
        assert "- Complete important task" in updated_content
        assert "- Review PR" in updated_content
        # Command output should be added
        assert "Now" in updated_content

    def test_refresh_handles_multiple_command_sections(self, temp_dir, monkeypatch):
        """Refresh updates multiple command-driven sections."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {"name": "Date", "command": "echo 'Monday'"},
                    {"name": "Notes", "description": "Manual notes"},
                    {"name": "Time", "command": "echo '10:00'"}
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        agenda_content = """# Agenda

## Date
[Run: echo 'Monday']

## Notes
Manual content here

## Time
[Run: echo '10:00']
"""
        (temp_dir / "AGENDA.md").write_text(agenda_content)

        refresh_agenda()

        updated_content = (temp_dir / "AGENDA.md").read_text()
        assert "Monday" in updated_content
        assert "10:00" in updated_content
        assert "Manual content here" in updated_content

    def test_refresh_raises_error_if_no_agenda(self, temp_dir, monkeypatch):
        """Refresh raises FileNotFoundError if AGENDA.md missing."""
        monkeypatch.chdir(temp_dir)

        # Create config
        config = {
            "agenda": {
                "sections": [{"name": "Test", "command": "echo 'test'"}]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(FileNotFoundError, match="AGENDA.md not found"):
            refresh_agenda()

    def test_refresh_raises_error_if_no_config(self, temp_dir, monkeypatch):
        """Refresh raises FileNotFoundError if gameplan.yaml missing."""
        monkeypatch.chdir(temp_dir)

        (temp_dir / "AGENDA.md").write_text("# Agenda")

        with pytest.raises(FileNotFoundError, match="gameplan.yaml not found"):
            refresh_agenda()

    def test_refresh_handles_command_failure_gracefully(self, temp_dir, monkeypatch):
        """Refresh shows error message if command fails."""
        monkeypatch.chdir(temp_dir)

        config = {
            "agenda": {
                "sections": [
                    {"name": "Test", "command": "false"}  # Command that fails
                ]
            }
        }
        config_file = temp_dir / "gameplan.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        agenda_content = """# Agenda

## Test
[Run: false]
"""
        (temp_dir / "AGENDA.md").write_text(agenda_content)

        refresh_agenda()

        updated_content = (temp_dir / "AGENDA.md").read_text()
        assert "[Error running command]" in updated_content or "Command failed" in updated_content


class TestFormatTrackedItems:
    """Test format_tracked_items function."""

    def test_format_tracked_items_returns_message_if_no_config(self, temp_dir):
        """format_tracked_items returns message if gameplan.yaml missing."""
        from cli.agenda import format_tracked_items

        result = format_tracked_items(temp_dir)

        assert result == "_No gameplan.yaml found_"

    def test_format_tracked_items_returns_message_if_no_items(self, temp_dir):
        """format_tracked_items returns message if no tracked items."""
        from cli.agenda import format_tracked_items

        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items: []
""")

        result = format_tracked_items(temp_dir)

        assert result == "_No tracked items_"

    def test_format_tracked_items_reads_from_tracking_files(self, temp_dir):
        """format_tracked_items reads status from tracking README files."""
        from cli.agenda import format_tracked_items

        # Create config
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-123
        env: prod
""")

        # Create tracking file with frontmatter
        tracking_dir = temp_dir / "tracking/areas/jira/PROJ-123-test-issue"
        tracking_dir.mkdir(parents=True)
        readme = tracking_dir / "README.md"
        readme.write_text("""---
issue_key: PROJ-123
title: Test Issue
status: In Progress
assignee: testuser
---
# PROJ-123: Test Issue
""")

        result = format_tracked_items(temp_dir)

        assert "[PROJ-123] Test Issue" in result
        assert "**Status:** In Progress" in result
        assert "Details →" in result

    def test_format_tracked_items_uses_slim_format(self, temp_dir):
        """format_tracked_items outputs slim format with links to README."""
        from cli.agenda import format_tracked_items

        # Create config
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-123
        env: prod
""")

        # Create tracking file with frontmatter
        tracking_dir = temp_dir / "tracking/areas/jira/PROJ-123-test-issue"
        tracking_dir.mkdir(parents=True)
        readme = tracking_dir / "README.md"
        readme.write_text("""---
issue_key: PROJ-123
title: Test Issue
status: In Progress
assignee: testuser
---
# PROJ-123: Test Issue
""")

        result = format_tracked_items(temp_dir)

        # Slim format should NOT have Actions/Notes subsections
        assert "#### Actions" not in result
        assert "#### Notes" not in result
        assert "Add your next actions here" not in result
        # Should have link to README
        assert "tracking/areas/jira/PROJ-123-test-issue/README.md" in result

    def test_format_tracked_items_handles_multiple_statuses(self, temp_dir):
        """format_tracked_items shows correct status for each item."""
        from cli.agenda import format_tracked_items

        # Create config with multiple items
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-1
      - issue: PROJ-2
      - issue: PROJ-3
      - issue: PROJ-4
      - issue: PROJ-5
""")

        # Create tracking files with frontmatter and different statuses
        for issue_num, status in [
            ("1", "In Progress"),
            ("2", "Refinement"),
            ("3", "To Do"),
            ("4", "Done"),
            ("5", "Blocked"),
        ]:
            tracking_dir = temp_dir / f"tracking/areas/jira/PROJ-{issue_num}-issue"
            tracking_dir.mkdir(parents=True)
            readme = tracking_dir / "README.md"
            readme.write_text(f"""---
issue_key: PROJ-{issue_num}
title: Issue {issue_num}
status: {status}
---
# PROJ-{issue_num}: Issue {issue_num}
""")

        result = format_tracked_items(temp_dir)

        assert "In Progress" in result
        assert "Refinement" in result
        assert "To Do" in result
        assert "Done" in result
        assert "Blocked" in result


class TestExtractTrackedItemSubsections:
    """Test _extract_tracked_item_subsections helper."""

    def test_extract_subsections_from_agenda(self, temp_dir):
        """_extract_tracked_item_subsections extracts Actions and Notes."""
        from cli.agenda import _extract_tracked_item_subsections

        content = """# Agenda

## Tracked Items

### [PROJ-123] Test Issue

**PROJ-123** 🟢 In Progress

#### Actions

- [ ] Task 1
- [ ] Task 2

#### Notes

Some important notes

### [PROJ-456] Another Issue

**PROJ-456** ❓ Refinement

#### Actions

- Different actions

#### Notes

Different notes
"""

        result = _extract_tracked_item_subsections(content)

        assert "PROJ-123" in result
        assert "Task 1" in result["PROJ-123"]["actions"]
        assert "Task 2" in result["PROJ-123"]["actions"]
        assert "important notes" in result["PROJ-123"]["notes"]

        assert "PROJ-456" in result
        assert "Different actions" in result["PROJ-456"]["actions"]
        assert "Different notes" in result["PROJ-456"]["notes"]

    def test_extract_subsections_handles_missing_sections(self):
        """_extract_tracked_item_subsections handles missing Actions/Notes."""
        from cli.agenda import _extract_tracked_item_subsections

        content = """# Agenda

### [PROJ-123] Test

**PROJ-123** 🟢 In Progress

Some content but no subsections
"""

        result = _extract_tracked_item_subsections(content)

        assert result["PROJ-123"]["actions"] == ""
        assert result["PROJ-123"]["notes"] == ""


class TestReadJiraStatus:
    """Test _read_jira_status helper."""

    def test_read_jira_status_from_readme(self, temp_dir):
        """_read_jira_status reads status from tracking README."""
        from cli.agenda import _read_jira_status

        tracking_dir = temp_dir / "tracking/areas/jira/PROJ-123-test-issue"
        tracking_dir.mkdir(parents=True)
        readme = tracking_dir / "README.md"
        readme.write_text("""# PROJ-123: Test Issue

**Status**: In Progress
**Assignee**: John Doe
""")

        result = _read_jira_status(temp_dir, "PROJ-123")

        assert result["status"] == "In Progress"
        assert result["title"] == "Test Issue"
        assert result["assignee"] == "John Doe"

    def test_read_jira_status_returns_unknown_if_not_found(self, temp_dir):
        """_read_jira_status returns Unknown if tracking file not found."""
        from cli.agenda import _read_jira_status

        result = _read_jira_status(temp_dir, "NONEXISTENT-1")

        assert result["status"] == "Unknown"
        assert result["title"] == ""


class TestFormatSingleTrackedItem:
    """Test _format_single_tracked_item helper."""

    def test_format_single_item_with_status_emoji(self):
        """_format_single_tracked_item includes status emoji."""
        from cli.agenda import _format_single_tracked_item

        status_info = {"status": "In Progress", "title": "Test Issue", "assignee": ""}
        subsections = {"actions": "", "notes": ""}

        result = _format_single_tracked_item("PROJ-123", status_info, subsections)

        assert "### [PROJ-123] Test Issue" in result
        assert "🟢 In Progress" in result

    def test_format_single_item_preserves_actions(self):
        """_format_single_tracked_item preserves Actions subsection."""
        from cli.agenda import _format_single_tracked_item

        status_info = {"status": "In Progress", "title": "Test", "assignee": ""}
        subsections = {"actions": "- [ ] Task 1\n- [ ] Task 2", "notes": ""}

        result = _format_single_tracked_item("PROJ-1", status_info, subsections)

        assert "- [ ] Task 1" in result
        assert "- [ ] Task 2" in result

    def test_format_single_item_preserves_notes(self):
        """_format_single_tracked_item preserves Notes subsection."""
        from cli.agenda import _format_single_tracked_item

        status_info = {"status": "Done", "title": "Test", "assignee": ""}
        subsections = {"actions": "", "notes": "Important context here"}

        result = _format_single_tracked_item("PROJ-1", status_info, subsections)

        assert "Important context here" in result

    def test_format_single_item_uses_default_placeholders(self):
        """_format_single_tracked_item uses defaults if subsections empty."""
        from cli.agenda import _format_single_tracked_item

        status_info = {"status": "To Do", "title": "Test", "assignee": ""}
        subsections = {"actions": "", "notes": ""}

        result = _format_single_tracked_item("PROJ-1", status_info, subsections)

        assert "Add your next actions here" in result
        assert "[Add context, observations, or reminders here]" in result


# =============================================================================
# Logbook Tests - Automatic archival of completed tasks
# =============================================================================


class TestExtractCompletedTasks:
    """Test extract_completed_tasks function."""

    def test_extracts_completed_task_with_date(self):
        """Extracts completed tasks marked with checkbox and date."""
        content = """# Agenda

## 🔄 Tracked Items

### [PROJ-123] Test Issue

**PROJ-123** 🟢 In Progress

#### Actions

- [x] Completed task ✅ 2025-10-13
- [ ] Pending task

#### Notes

Some notes
"""
        result = extract_completed_tasks(content)

        assert "[PROJ-123] Test Issue" in result
        assert "2025-10-13" in result["[PROJ-123] Test Issue"]
        assert "- [x] Completed task ✅ 2025-10-13" in result["[PROJ-123] Test Issue"]["2025-10-13"]

    def test_ignores_completed_without_date(self):
        """Ignores completed tasks without a date emoji."""
        content = """# Agenda

## 🔄 Tracked Items

### [PROJ-123] Test Issue

#### Actions

- [x] Completed but no date
- [ ] Pending task
"""
        result = extract_completed_tasks(content)

        assert result == {}

    def test_extracts_multiple_dates(self):
        """Extracts tasks with different dates."""
        content = """# Agenda

## 🔄 Tracked Items

### [PROJ-123] Test Issue

#### Actions

- [x] Task from yesterday ✅ 2025-10-12
- [x] Task from today ✅ 2025-10-13
- [ ] Pending task
"""
        result = extract_completed_tasks(content)

        assert "2025-10-12" in result["[PROJ-123] Test Issue"]
        assert "2025-10-13" in result["[PROJ-123] Test Issue"]

    def test_extracts_from_multiple_items(self):
        """Extracts tasks from multiple tracked items."""
        content = """# Agenda

## 🔄 Tracked Items

### [PROJ-123] First Issue

#### Actions

- [x] Task A ✅ 2025-10-13

#### Notes

Notes for first

### [PROJ-456] Second Issue

#### Actions

- [x] Task B ✅ 2025-10-13

#### Notes

Notes for second
"""
        result = extract_completed_tasks(content)

        assert "[PROJ-123] First Issue" in result
        assert "[PROJ-456] Second Issue" in result
        assert "- [x] Task A ✅ 2025-10-13" in result["[PROJ-123] First Issue"]["2025-10-13"]
        assert "- [x] Task B ✅ 2025-10-13" in result["[PROJ-456] Second Issue"]["2025-10-13"]

    def test_only_extracts_from_actions_section(self):
        """Only extracts completed tasks from Actions section, not Notes."""
        content = """# Agenda

## 🔄 Tracked Items

### [PROJ-123] Test Issue

#### Actions

- [ ] Pending task

#### Notes

- [x] This is a note with checkbox ✅ 2025-10-13
"""
        result = extract_completed_tasks(content)

        # Notes with checkboxes inside tracked items are NOT extracted
        assert "[PROJ-123] Test Issue" not in result

    def test_extracts_other_tasks_outside_tracked_items(self):
        """Extracts non-tracked tasks into 'Other' category."""
        content = """# Agenda

## 🎯 Focus

- [x] Random task ✅ 2025-10-13

## 🔄 Tracked Items

### [PROJ-123] Test Issue

#### Actions

- [x] Tracked task ✅ 2025-10-13
"""
        result = extract_completed_tasks(content)

        assert "Other" in result
        assert "- [x] Random task ✅ 2025-10-13" in result["Other"]["2025-10-13"]
        assert "[PROJ-123] Test Issue" in result
        assert "- [x] Tracked task ✅ 2025-10-13" in result["[PROJ-123] Test Issue"]["2025-10-13"]


class TestExtractIssueKeyFromTitle:
    """Test _extract_issue_key_from_title helper."""

    def test_extracts_issue_key(self):
        """Extracts issue key from standard title format."""
        result = _extract_issue_key_from_title("[ANSTRAT-1567] Test Title")
        assert result == "ANSTRAT-1567"

    def test_extracts_issue_key_simple(self):
        """Extracts issue key from simple format."""
        result = _extract_issue_key_from_title("[PROJ-123] Issue")
        assert result == "PROJ-123"

    def test_returns_none_for_invalid_format(self):
        """Returns None if no issue key found."""
        result = _extract_issue_key_from_title("No brackets here")
        assert result is None

    def test_returns_none_for_empty_brackets(self):
        """Returns None for empty brackets."""
        result = _extract_issue_key_from_title("[] Empty")
        assert result is None


class TestGetWeekStart:
    """Test _get_week_start helper."""

    def test_monday_returns_same_date(self):
        """Monday returns the same date."""
        result = _get_week_start("2025-10-13")  # Monday
        assert result == "2025-10-13"

    def test_wednesday_returns_monday(self):
        """Wednesday returns previous Monday."""
        result = _get_week_start("2025-10-15")  # Wednesday
        assert result == "2025-10-13"

    def test_sunday_returns_monday(self):
        """Sunday returns previous Monday."""
        result = _get_week_start("2025-10-19")  # Sunday
        assert result == "2025-10-13"


class TestFormatIssueHeading:
    """Test _format_issue_heading helper."""

    def test_formats_issue_with_title(self):
        """Formats issue key with title."""
        result = _format_issue_heading("[ANSTRAT-1567] MCP Server MVP")
        assert result == "ANSTRAT-1567 (MCP Server MVP)"

    def test_formats_issue_without_title(self):
        """Formats issue key without title."""
        result = _format_issue_heading("[PROJ-123]")
        assert result == "PROJ-123"

    def test_other_passthrough(self):
        """'Other' passes through unchanged."""
        result = _format_issue_heading("Other")
        assert result == "Other"


class TestAppendToLogbook:
    """Test append_to_logbook function."""

    def test_creates_new_logbook(self, temp_dir):
        """Creates LOGBOOK.md at repo root if it doesn't exist."""
        completed_tasks = {
            "[PROJ-123] Test": {
                "2025-10-13": ["- [x] Task 1 ✅ 2025-10-13"]
            }
        }

        logged, initiatives = append_to_logbook(completed_tasks, temp_dir)

        logbook = temp_dir / "LOGBOOK.md"
        assert logbook.exists()
        content = logbook.read_text()
        assert "# Logbook" in content
        assert "## Week of 2025-10-13" in content
        assert "### PROJ-123 (Test)" in content
        assert "- [x] Task 1 ✅ 2025-10-13" in content
        assert logged == 1
        assert initiatives == 1

    def test_appends_to_existing_logbook(self, temp_dir):
        """Appends to existing LOGBOOK.md preserving old entries."""
        # Create existing logbook
        logbook = temp_dir / "LOGBOOK.md"
        logbook.write_text("""# Logbook

## Week of 2025-10-06

### PROJ-123 (Test)

- [x] Old task ✅ 2025-10-07
""")

        completed_tasks = {
            "[PROJ-123] Test": {
                "2025-10-13": ["- [x] New task ✅ 2025-10-13"]
            }
        }

        append_to_logbook(completed_tasks, temp_dir)

        content = logbook.read_text()
        # Both weeks should be present
        assert "## Week of 2025-10-06" in content
        assert "- [x] Old task ✅ 2025-10-07" in content
        assert "## Week of 2025-10-13" in content
        assert "- [x] New task ✅ 2025-10-13" in content

    def test_handles_multiple_initiatives(self, temp_dir):
        """Handles multiple initiatives in same week."""
        completed_tasks = {
            "[PROJ-123] First": {
                "2025-10-13": ["- [x] Task A ✅ 2025-10-13"]
            },
            "[PROJ-456] Second": {
                "2025-10-14": ["- [x] Task B ✅ 2025-10-14"]
            }
        }

        logged, initiatives = append_to_logbook(completed_tasks, temp_dir)

        logbook = temp_dir / "LOGBOOK.md"
        content = logbook.read_text()
        assert "### PROJ-123 (First)" in content
        assert "### PROJ-456 (Second)" in content
        assert logged == 2
        assert initiatives == 2

    def test_handles_other_category(self, temp_dir):
        """Handles 'Other' category for non-tracked tasks."""
        completed_tasks = {
            "Other": {
                "2025-10-13": ["- [x] Random task ✅ 2025-10-13"]
            }
        }

        append_to_logbook(completed_tasks, temp_dir)

        logbook = temp_dir / "LOGBOOK.md"
        content = logbook.read_text()
        assert "### Other" in content
        assert "- [x] Random task ✅ 2025-10-13" in content

    def test_avoids_duplicates(self, temp_dir):
        """Doesn't add duplicate tasks."""
        # Create existing logbook with task
        logbook = temp_dir / "LOGBOOK.md"
        logbook.write_text("""# Logbook

## Week of 2025-10-13

### PROJ-123 (Test)

- [x] Existing task ✅ 2025-10-13
""")

        completed_tasks = {
            "[PROJ-123] Test": {
                "2025-10-13": ["- [x] Existing task ✅ 2025-10-13"]  # Same task
            }
        }

        logged, initiatives = append_to_logbook(completed_tasks, temp_dir)

        content = logbook.read_text()
        # Task should only appear once
        assert content.count("- [x] Existing task ✅ 2025-10-13") == 1
        assert logged == 0  # No new tasks logged

    def test_returns_zero_if_no_tasks(self, temp_dir):
        """Returns (0, 0) if no completed tasks."""
        logged, initiatives = append_to_logbook({}, temp_dir)

        assert logged == 0
        assert initiatives == 0


class TestParseLogbook:
    """Test _parse_logbook helper."""

    def test_parses_logbook_structure(self):
        """Parses logbook into structured data."""
        content = """# Logbook

## Week of 2025-10-13

### PROJ-123 (Test)

- [x] Task 1 ✅ 2025-10-13

### Other

- [x] Random ✅ 2025-10-14

## Week of 2025-10-06

### PROJ-456 (Another)

- [x] Old task ✅ 2025-10-07
"""
        result = _parse_logbook(content)

        assert "2025-10-13" in result
        assert "PROJ-123 (Test)" in result["2025-10-13"]
        assert "- [x] Task 1 ✅ 2025-10-13" in result["2025-10-13"]["PROJ-123 (Test)"]
        assert "Other" in result["2025-10-13"]
        assert "2025-10-06" in result
        assert "PROJ-456 (Another)" in result["2025-10-06"]


class TestBuildLogbookContent:
    """Test _build_logbook_content helper."""

    def test_builds_logbook_content(self):
        """Builds logbook content from structured data."""
        entries = {
            "2025-10-13": {
                "PROJ-123 (Test)": ["- [x] Task 1 ✅ 2025-10-13"],
                "Other": ["- [x] Random ✅ 2025-10-14"],
            },
            "2025-10-06": {
                "PROJ-456 (Another)": ["- [x] Old task ✅ 2025-10-07"],
            }
        }

        result = _build_logbook_content(entries)

        # Newest week first
        assert result.index("Week of 2025-10-13") < result.index("Week of 2025-10-06")
        # Other comes after tracked items
        assert result.index("### PROJ-123") < result.index("### Other")


class TestRemoveCompletedTasksFromContent:
    """Test remove_completed_tasks_from_content function."""

    def test_removes_completed_tasks(self):
        """Removes completed tasks from content."""
        content = """# Agenda

## 🔄 Tracked Items

### [PROJ-123] Test

#### Actions

- [x] Task to remove ✅ 2025-10-13
- [ ] Keep this pending task

#### Notes

Keep these notes
"""
        completed_tasks = {
            "[PROJ-123] Test": {
                "2025-10-13": ["- [x] Task to remove ✅ 2025-10-13"]
            }
        }

        result = remove_completed_tasks_from_content(content, completed_tasks)

        assert "- [x] Task to remove ✅ 2025-10-13" not in result
        assert "- [ ] Keep this pending task" in result
        assert "Keep these notes" in result

    def test_removes_multiple_tasks(self):
        """Removes multiple completed tasks."""
        content = """## 🔄 Tracked Items

### [PROJ-123] Test

#### Actions

- [x] Task 1 ✅ 2025-10-13
- [ ] Pending
- [x] Task 2 ✅ 2025-10-13
"""
        completed_tasks = {
            "[PROJ-123] Test": {
                "2025-10-13": [
                    "- [x] Task 1 ✅ 2025-10-13",
                    "- [x] Task 2 ✅ 2025-10-13",
                ]
            }
        }

        result = remove_completed_tasks_from_content(content, completed_tasks)

        assert "- [x] Task 1 ✅ 2025-10-13" not in result
        assert "- [x] Task 2 ✅ 2025-10-13" not in result
        assert "- [ ] Pending" in result

    def test_returns_unchanged_if_no_tasks(self):
        """Returns unchanged content if no tasks to remove."""
        content = "# Agenda\n\nSome content"
        result = remove_completed_tasks_from_content(content, {})
        assert result == content


class TestProcessLogbook:
    """Test process_logbook integration function."""

    def test_full_logbook_workflow(self, temp_dir):
        """Tests complete workflow: extract, log to root LOGBOOK.md, remove."""
        # Create AGENDA.md with completed task
        agenda = temp_dir / "AGENDA.md"
        agenda.write_text("""# Agenda

## 🔄 Tracked Items

### [PROJ-123] Test Issue

**PROJ-123** 🟢 In Progress

#### Actions

- [x] Completed task ✅ 2025-10-13
- [ ] Pending task

#### Notes

Notes here
""")

        logged, initiatives = process_logbook(temp_dir)

        # Check task was logged
        assert logged == 1
        assert initiatives == 1

        # Check LOGBOOK.md was created at root
        logbook = temp_dir / "LOGBOOK.md"
        assert logbook.exists()
        logbook_content = logbook.read_text()
        assert "## Week of 2025-10-13" in logbook_content
        assert "### PROJ-123 (Test Issue)" in logbook_content
        assert "- [x] Completed task ✅ 2025-10-13" in logbook_content

        # Check task was removed from AGENDA.md
        agenda_content = agenda.read_text()
        assert "- [x] Completed task ✅ 2025-10-13" not in agenda_content
        assert "- [ ] Pending task" in agenda_content
        assert "Notes here" in agenda_content

    def test_returns_zero_if_no_completed_tasks(self, temp_dir):
        """Returns (0, 0) if no completed tasks."""
        agenda = temp_dir / "AGENDA.md"
        agenda.write_text("""# Agenda

## 🔄 Tracked Items

### [PROJ-123] Test

#### Actions

- [ ] Only pending tasks
""")

        logged, initiatives = process_logbook(temp_dir)

        assert logged == 0
        assert initiatives == 0

    def test_returns_zero_if_no_agenda(self, temp_dir):
        """Returns (0, 0) if AGENDA.md doesn't exist."""
        logged, initiatives = process_logbook(temp_dir)

        assert logged == 0
        assert initiatives == 0


class TestRefreshAgendaWithLogbook:
    """Test that refresh_agenda integrates logbook processing."""

    def test_refresh_processes_logbook(self, temp_dir, monkeypatch):
        """Refresh processes completed tasks into logbook."""
        monkeypatch.chdir(temp_dir)

        # Create config
        config = {
            "agenda": {
                "sections": [
                    {"name": "Tracked Items", "emoji": "🔄", "description": "Tracked items"}
                ]
            }
        }
        (temp_dir / "gameplan.yaml").write_text(yaml.dump(config))

        # Create AGENDA.md with completed task
        (temp_dir / "AGENDA.md").write_text("""# Agenda - Monday, October 13, 2025

## 🔄 Tracked Items

### [PROJ-123] Test Issue

#### Actions

- [x] Done task ✅ 2025-10-13
- [ ] Pending task

#### Notes

Some notes
""")

        refresh_agenda()

        # Check logbook was created at root
        logbook = temp_dir / "LOGBOOK.md"
        assert logbook.exists()
        logbook_content = logbook.read_text()
        assert "## Week of 2025-10-13" in logbook_content
        assert "- [x] Done task ✅ 2025-10-13" in logbook_content

        # Check task was removed from agenda
        agenda_content = (temp_dir / "AGENDA.md").read_text()
        assert "- [x] Done task ✅ 2025-10-13" not in agenda_content
        assert "- [ ] Pending task" in agenda_content
