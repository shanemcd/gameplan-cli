"""Tests for the init command.

The init command sets up a new gameplan repository with the necessary
directory structure and configuration files.
"""
from pathlib import Path

import pytest
import yaml

from cli.init import init_gameplan


class TestInitGameplan:
    """Test the init_gameplan function."""

    def test_init_creates_tracking_directory(self, temp_dir):
        """Init creates tracking/areas/ directory structure."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        tracking_dir = temp_dir / "tracking" / "areas"
        assert tracking_dir.exists()
        assert tracking_dir.is_dir()

    def test_init_creates_jira_area_directory(self, temp_dir):
        """Init creates tracking/areas/jira/ directory."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        jira_dir = temp_dir / "tracking" / "areas" / "jira"
        assert jira_dir.exists()
        assert jira_dir.is_dir()

    def test_init_creates_jira_archive_directory(self, temp_dir):
        """Init creates tracking/areas/jira/archive/ directory."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        archive_dir = temp_dir / "tracking" / "areas" / "jira" / "archive"
        assert archive_dir.exists()
        assert archive_dir.is_dir()

    def test_init_creates_gameplan_yaml(self, temp_dir):
        """Init creates gameplan.yaml configuration file."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        config_file = temp_dir / "gameplan.yaml"
        assert config_file.exists()
        assert config_file.is_file()

    def test_init_gameplan_yaml_has_valid_structure(self, temp_dir):
        """Init creates gameplan.yaml with valid YAML structure."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        config_file = temp_dir / "gameplan.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert isinstance(config, dict)
        assert "areas" in config
        assert isinstance(config["areas"], dict)

    def test_init_gameplan_yaml_has_jira_section(self, temp_dir):
        """Init creates gameplan.yaml with jira area configuration."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        config_file = temp_dir / "gameplan.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert "jira" in config["areas"]
        assert "items" in config["areas"]["jira"]
        assert isinstance(config["areas"]["jira"]["items"], list)

    def test_init_gameplan_yaml_starts_with_empty_items(self, temp_dir):
        """Init creates gameplan.yaml with empty items list."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        config_file = temp_dir / "gameplan.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert config["areas"]["jira"]["items"] == []

    def test_init_raises_error_if_gameplan_yaml_exists(self, temp_dir):
        """Init raises FileExistsError if gameplan.yaml already exists."""
        # First init succeeds
        init_gameplan(target_dir=temp_dir, interactive=False)

        # Second init should raise error
        with pytest.raises(FileExistsError, match="gameplan.yaml already exists"):
            init_gameplan(target_dir=temp_dir, interactive=False)

    def test_init_uses_current_directory_by_default(self, temp_dir, monkeypatch):
        """Init uses current directory when target_dir is None."""
        # Change to temp directory
        monkeypatch.chdir(temp_dir)

        init_gameplan(target_dir=None, interactive=False)

        config_file = temp_dir / "gameplan.yaml"
        assert config_file.exists()

    def test_init_creates_directories_with_parents(self, temp_dir):
        """Init creates all parent directories if they don't exist."""
        nested_dir = temp_dir / "nested" / "path" / "to" / "gameplan"
        init_gameplan(target_dir=nested_dir, interactive=False)

        assert (nested_dir / "gameplan.yaml").exists()
        assert (nested_dir / "tracking" / "areas" / "jira").exists()

    def test_init_returns_target_directory_path(self, temp_dir):
        """Init returns the Path to the initialized directory."""
        result = init_gameplan(target_dir=temp_dir, interactive=False)

        assert isinstance(result, Path)
        assert result == temp_dir

    def test_init_gameplan_yaml_has_agenda_section(self, temp_dir):
        """Init creates gameplan.yaml with agenda configuration."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        config_file = temp_dir / "gameplan.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert "agenda" in config
        assert "sections" in config["agenda"]
        assert isinstance(config["agenda"]["sections"], list)

    def test_init_gameplan_yaml_has_default_agenda_sections(self, temp_dir):
        """Init creates gameplan.yaml with default agenda sections."""
        init_gameplan(target_dir=temp_dir, interactive=False)

        config_file = temp_dir / "gameplan.yaml"
        with open(config_file) as f:
            config = yaml.safe_load(f)

        sections = config["agenda"]["sections"]
        assert len(sections) > 0

        # Check for Focus & Priorities section
        section_names = [s["name"] for s in sections]
        assert "Focus & Priorities" in section_names

        # Check for Notes section
        assert "Notes" in section_names


class TestInitInteractiveMode:
    """Test interactive mode for init command."""

    def test_init_interactive_mode_not_implemented_yet(self, temp_dir):
        """Interactive mode passes through for now (to be implemented)."""
        # For now, interactive mode should work the same as non-interactive
        result = init_gameplan(target_dir=temp_dir, interactive=True)

        assert result == temp_dir
        assert (temp_dir / "gameplan.yaml").exists()
