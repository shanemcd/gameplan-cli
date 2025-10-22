"""Tests for the agenda command.

The agenda command manages a daily AGENDA.md file with configurable sections.
Some sections are manual (user-maintained), others are command-driven
(auto-populated by running shell commands).
"""
from pathlib import Path
from datetime import datetime

import pytest
import yaml

from cli.agenda import init_agenda, view_agenda, refresh_agenda


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
