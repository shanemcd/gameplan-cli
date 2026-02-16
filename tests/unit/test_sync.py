"""Tests for sync command."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml

from cli.adapters.base import TrackedItem, ItemData
from cli.sync import (
    DEFAULT_POPULATE_JQL,
    load_config,
    save_config,
    sync_jira,
    sync_all,
    populate_jira_items,
)


class TestLoadConfig:
    """Tests for loading gameplan.yaml configuration."""

    def test_load_config_reads_yaml_file(self, temp_dir):
        """load_config reads and parses YAML file."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("areas:\n  jira:\n    items: []\n")

        result = load_config(temp_dir)

        assert result == {"areas": {"jira": {"items": []}}}

    def test_load_config_returns_empty_dict_if_file_missing(self, temp_dir, capsys):
        """load_config returns empty dict if gameplan.yaml doesn't exist."""
        result = load_config(temp_dir)

        assert result == {}
        captured = capsys.readouterr()
        assert "Configuration not found" in captured.err

    def test_load_config_handles_complex_yaml(self, temp_dir):
        """load_config parses complex YAML structures."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-123
        env: prod
agenda:
  sections:
    - name: Focus
      emoji: 🎯
""")

        result = load_config(temp_dir)

        assert "areas" in result
        assert "jira" in result["areas"]
        assert "agenda" in result
        assert len(result["areas"]["jira"]["items"]) == 1


class TestSyncJira:
    """Tests for syncing Jira issues."""

    @patch("cli.sync.JiraAdapter")
    def test_sync_jira_loads_config_and_creates_adapter(self, mock_adapter_class, temp_dir):
        """sync_jira loads config and creates JiraAdapter."""
        # Setup config file
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-123
        env: prod
""")

        # Mock adapter instance
        mock_adapter = MagicMock()
        mock_adapter.load_config.return_value = [
            TrackedItem(
                id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"}
            )
        ]
        mock_adapter.fetch_item_data.return_value = ItemData(
            title="Test Issue",
            status="In Progress",
            updates=[],
            raw_data={"fields": {"assignee": {"displayName": "testuser"}}},
        )
        mock_adapter.get_storage_path.return_value = temp_dir / "tracking/areas/jira/PROJ-123"
        mock_adapter.detect_changes.return_value = False
        mock_adapter_class.return_value = mock_adapter

        sync_jira(temp_dir)

        # Verify adapter was created with config
        mock_adapter_class.assert_called_once()
        assert mock_adapter_class.call_args[0][0] == {
            "items": [{"issue": "PROJ-123", "env": "prod"}]
        }

    @patch("cli.sync.JiraAdapter")
    def test_sync_jira_warns_if_no_jira_config(self, mock_adapter_class, temp_dir, capsys):
        """sync_jira warns if no Jira section in config."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("areas: {}\n")

        sync_jira(temp_dir)

        captured = capsys.readouterr()
        assert "No Jira configuration found" in captured.out
        mock_adapter_class.assert_not_called()

    @patch("cli.sync.JiraAdapter")
    def test_sync_jira_warns_if_no_tracked_items(self, mock_adapter_class, temp_dir, capsys):
        """sync_jira warns if no tracked items."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("areas:\n  jira:\n    items: []\n")

        mock_adapter = MagicMock()
        mock_adapter.load_config.return_value = []
        mock_adapter_class.return_value = mock_adapter

        sync_jira(temp_dir)

        captured = capsys.readouterr()
        assert "No tracked Jira issues found" in captured.out

    @patch("cli.sync.JiraAdapter")
    def test_sync_jira_fetches_and_updates_each_item(self, mock_adapter_class, temp_dir):
        """sync_jira fetches data and updates README for each item."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-123
        env: prod
      - issue: PROJ-456
        env: prod
""")

        mock_adapter = MagicMock()
        mock_adapter.load_config.return_value = [
            TrackedItem(
                id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"}
            ),
            TrackedItem(
                id="PROJ-456", adapter="jira", metadata={"issue": "PROJ-456", "env": "prod"}
            ),
        ]
        mock_adapter.fetch_item_data.side_effect = [
            ItemData(
                title="First Issue",
                status="In Progress",
                updates=[],
                raw_data={"fields": {"assignee": {"displayName": "user1"}}},
            ),
            ItemData(
                title="Second Issue",
                status="Done",
                updates=[],
                raw_data={"fields": {"assignee": {"displayName": "user2"}}},
            ),
        ]
        mock_adapter.get_storage_path.side_effect = [
            temp_dir / "tracking/areas/jira/PROJ-123",
            temp_dir / "tracking/areas/jira/PROJ-123-first-issue",
            temp_dir / "tracking/areas/jira/PROJ-456",
            temp_dir / "tracking/areas/jira/PROJ-456-second-issue",
        ]
        mock_adapter.detect_changes.return_value = False
        mock_adapter_class.return_value = mock_adapter

        sync_jira(temp_dir)

        # Verify fetch_item_data called for each item
        assert mock_adapter.fetch_item_data.call_count == 2
        # Verify update_readme called for each item
        assert mock_adapter.update_readme.call_count == 2
        # Verify save_metadata called for each item
        assert mock_adapter.save_metadata.call_count == 2

    @patch("cli.sync.JiraAdapter")
    def test_sync_jira_detects_changes(self, mock_adapter_class, temp_dir, capsys):
        """sync_jira prints notification when changes detected."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-123
        env: prod
""")

        mock_adapter = MagicMock()
        mock_adapter.load_config.return_value = [
            TrackedItem(
                id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"}
            )
        ]
        mock_adapter.fetch_item_data.return_value = ItemData(
            title="Test Issue",
            status="In Progress",
            updates=[],
            raw_data={"fields": {"assignee": {"displayName": "testuser"}}},
        )
        mock_adapter.get_storage_path.return_value = temp_dir / "tracking/areas/jira/PROJ-123"
        mock_adapter.detect_changes.return_value = True  # Changes detected
        mock_adapter_class.return_value = mock_adapter

        sync_jira(temp_dir)

        captured = capsys.readouterr()
        assert "Issue has been updated" in captured.out

    @patch("cli.sync.JiraAdapter")
    def test_sync_jira_skips_item_if_fetch_fails(self, mock_adapter_class, temp_dir, capsys):
        """sync_jira skips item if data fetch fails."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""
areas:
  jira:
    items:
      - issue: PROJ-123
        env: prod
""")

        mock_adapter = MagicMock()
        mock_adapter.load_config.return_value = [
            TrackedItem(
                id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"}
            )
        ]
        mock_adapter.fetch_item_data.return_value = ItemData(
            title="",  # Empty title indicates failure
            status="",
            updates=[],
            raw_data={},
        )
        mock_adapter.get_storage_path.return_value = temp_dir / "tracking/areas/jira/PROJ-123"
        mock_adapter_class.return_value = mock_adapter

        sync_jira(temp_dir)

        captured = capsys.readouterr()
        assert "Could not fetch data" in captured.out
        mock_adapter.update_readme.assert_not_called()


class TestSaveConfig:
    """Tests for saving gameplan.yaml configuration."""

    def test_save_config_updates_items(self, temp_dir):
        """save_config writes items to gameplan.yaml."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("areas:\n  jira:\n    items: []\n")

        items = [{"issue": "PROJ-123", "env": "prod"}]
        save_config(temp_dir, items)

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["areas"]["jira"]["items"] == items

    def test_save_config_preserves_comments(self, temp_dir):
        """save_config preserves YAML comments."""
        config_file = temp_dir / "gameplan.yaml"
        original = """\
# Gameplan Configuration
areas:
  jira:
    # Add Jira issues you're actively working on
    items: []
"""
        config_file.write_text(original)

        save_config(temp_dir, [{"issue": "PROJ-123", "env": "prod"}])

        content = config_file.read_text()
        assert "# Gameplan Configuration" in content
        assert "# Add Jira issues you're actively working on" in content

    def test_save_config_preserves_emoji(self, temp_dir):
        """save_config preserves emoji characters in other sections."""
        config_file = temp_dir / "gameplan.yaml"
        original = """\
areas:
  jira:
    items: []
agenda:
  sections:
    - name: Focus & Priorities
      emoji: "\U0001f3af"
    - name: Notes
      emoji: "\U0001f4d4"
"""
        config_file.write_text(original)

        save_config(temp_dir, [{"issue": "NEW-1", "env": "prod"}])

        content = config_file.read_text()
        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["agenda"]["sections"][0]["emoji"] is not None
        assert saved["agenda"]["sections"][1]["emoji"] is not None
        assert saved["areas"]["jira"]["items"][0]["issue"] == "NEW-1"

    def test_save_config_preserves_other_jira_keys(self, temp_dir):
        """save_config preserves env, command, populate under areas.jira."""
        config_file = temp_dir / "gameplan.yaml"
        original = """\
areas:
  jira:
    env: prod
    command: /usr/local/bin/jirahhh
    populate:
      search: "project = TEST"
    items: []
"""
        config_file.write_text(original)

        save_config(temp_dir, [{"issue": "X-1", "env": "prod"}])

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["areas"]["jira"]["env"] == "prod"
        assert saved["areas"]["jira"]["command"] == "/usr/local/bin/jirahhh"
        assert saved["areas"]["jira"]["populate"]["search"] == "project = TEST"

    def test_save_config_preserves_full_init_template(self, temp_dir):
        """save_config preserves the full init template structure and comments."""
        from cli.init import _create_gameplan_yaml

        config_file = temp_dir / "gameplan.yaml"
        _create_gameplan_yaml(config_file)
        original_content = config_file.read_text()

        save_config(temp_dir, [{"issue": "PROJ-1", "env": "prod", "source": "populate"}])

        updated_content = config_file.read_text()
        # Comments from template should still be present
        assert "# Gameplan Configuration" in updated_content
        assert "# Areas: Define what you want to track" in updated_content
        assert "# Agenda: Configure your daily AGENDA.md file" in updated_content
        # Agenda section should be completely untouched
        for line in original_content.split("\n"):
            if line.startswith("# Agenda") or "agenda:" in line or "sections:" in line:
                assert line in updated_content


class TestPopulateJiraItems:
    """Tests for populating Jira items from search."""

    @patch("cli.sync.JiraAdapter")
    def test_populate_searches_and_updates_config(self, mock_adapter_class, temp_dir):
        """populate_jira_items runs search and saves results to config."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    populate:
      search: "assignee = currentUser() AND statusCategory != Done"
    env: prod
    items: []
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(
                id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"}
            ),
            TrackedItem(
                id="PROJ-456", adapter="jira", metadata={"issue": "PROJ-456", "env": "prod"}
            ),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        # Verify search was called with JQL from config
        mock_adapter.search_issues.assert_called_once_with(
            jql="assignee = currentUser() AND statusCategory != Done",
            env="prod",
        )

        # Verify config was updated with source: populate tag
        with open(config_file) as f:
            saved = yaml.safe_load(f)
        items = saved["areas"]["jira"]["items"]
        assert len(items) == 2
        assert items[0] == {"issue": "PROJ-123", "env": "prod", "source": "populate"}
        assert items[1] == {"issue": "PROJ-456", "env": "prod", "source": "populate"}

    @patch("cli.sync.JiraAdapter")
    def test_populate_with_cli_overrides(self, mock_adapter_class, temp_dir):
        """populate_jira_items accepts JQL and env overrides."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    populate:
      search: "assignee = currentUser()"
    env: prod
    items: []
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(
                id="TEST-1", adapter="jira", metadata={"issue": "TEST-1", "env": "staging"}
            ),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir, jql="project = TEST", env="staging")

        # Should use CLI overrides, not config values
        mock_adapter.search_issues.assert_called_once_with(
            jql="project = TEST",
            env="staging",
        )

    @patch("cli.sync.JiraAdapter")
    def test_populate_removes_stale_populate_items(self, mock_adapter_class, temp_dir):
        """populate_jira_items removes old source: populate items not in search results."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    env: prod
    items:
      - issue: OLD-1
        env: prod
        source: populate
      - issue: OLD-2
        env: prod
        source: populate
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(id="NEW-1", adapter="jira", metadata={"issue": "NEW-1", "env": "prod"}),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        items = saved["areas"]["jira"]["items"]
        assert len(items) == 1
        assert items[0]["issue"] == "NEW-1"
        assert items[0]["source"] == "populate"

    @patch("cli.sync.JiraAdapter")
    def test_populate_preserves_manual_items(self, mock_adapter_class, temp_dir):
        """populate_jira_items preserves items without source: populate."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    env: prod
    items:
      - issue: MANUAL-1
        env: prod
      - issue: STALE-POPULATE
        env: prod
        source: populate
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(id="NEW-1", adapter="jira", metadata={"issue": "NEW-1", "env": "prod"}),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        items = saved["areas"]["jira"]["items"]
        # MANUAL-1 should be kept, STALE-POPULATE removed, NEW-1 added
        issues = [i["issue"] for i in items]
        assert "MANUAL-1" in issues
        assert "NEW-1" in issues
        assert "STALE-POPULATE" not in issues

    @patch("cli.sync.JiraAdapter")
    def test_populate_does_not_duplicate_existing_populate_items(
        self, mock_adapter_class, temp_dir
    ):
        """populate_jira_items does not duplicate items already present from previous populate."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    env: prod
    items:
      - issue: PROJ-123
        env: prod
        source: populate
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(
                id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"}
            ),
            TrackedItem(
                id="PROJ-456", adapter="jira", metadata={"issue": "PROJ-456", "env": "prod"}
            ),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        items = saved["areas"]["jira"]["items"]
        issue_keys = [i["issue"] for i in items]
        assert issue_keys.count("PROJ-123") == 1
        assert "PROJ-456" in issue_keys

    @patch("cli.sync.JiraAdapter")
    def test_populate_does_not_tag_manual_item_matching_search(self, mock_adapter_class, temp_dir):
        """If a manual item matches a search result, it stays manual."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    env: prod
    items:
      - issue: MANUAL-1
        env: prod
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(
                id="MANUAL-1", adapter="jira", metadata={"issue": "MANUAL-1", "env": "prod"}
            ),
            TrackedItem(id="NEW-1", adapter="jira", metadata={"issue": "NEW-1", "env": "prod"}),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        items = saved["areas"]["jira"]["items"]
        manual_item = next(i for i in items if i["issue"] == "MANUAL-1")
        new_item = next(i for i in items if i["issue"] == "NEW-1")
        # Manual item should NOT get source: populate
        assert "source" not in manual_item
        # New item should be tagged
        assert new_item["source"] == "populate"

    @patch("cli.sync.JiraAdapter")
    def test_populate_preserves_other_config_keys(self, mock_adapter_class, temp_dir):
        """populate_jira_items preserves populate.search, env, command, and agenda config."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    populate:
      search: "assignee = currentUser()"
    env: prod
    command: /usr/local/bin/jirahhh
    items: []
agenda:
  sections:
    - name: Focus
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(id="PROJ-1", adapter="jira", metadata={"issue": "PROJ-1", "env": "prod"}),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["areas"]["jira"]["populate"]["search"] == "assignee = currentUser()"
        assert saved["areas"]["jira"]["env"] == "prod"
        assert saved["areas"]["jira"]["command"] == "/usr/local/bin/jirahhh"
        assert saved["agenda"]["sections"][0]["name"] == "Focus"

    def test_populate_warns_if_no_jira_config(self, temp_dir, capsys):
        """populate_jira_items warns if no Jira config exists."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("areas: {}\n")

        populate_jira_items(temp_dir)

        captured = capsys.readouterr()
        assert "No Jira configuration found" in captured.out

    @patch("cli.sync.JiraAdapter")
    def test_populate_uses_default_jql_when_not_configured(self, mock_adapter_class, temp_dir):
        """populate_jira_items uses default JQL when no search in config or args."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    env: prod
    items: []
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = []
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        # Should use the default JQL
        mock_adapter.search_issues.assert_called_once_with(
            jql=DEFAULT_POPULATE_JQL,
            env="prod",
        )

    @patch("cli.sync.JiraAdapter")
    def test_populate_empty_results_removes_only_populate_items(self, mock_adapter_class, temp_dir):
        """Empty search results removes populate items but keeps manual ones."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
areas:
  jira:
    env: prod
    items:
      - issue: MANUAL-1
        env: prod
      - issue: POP-1
        env: prod
        source: populate
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = []
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        items = saved["areas"]["jira"]["items"]
        assert len(items) == 1
        assert items[0]["issue"] == "MANUAL-1"

    @patch("cli.sync.JiraAdapter")
    def test_populate_preserves_yaml_comments(self, mock_adapter_class, temp_dir):
        """populate_jira_items preserves YAML comments in the file."""
        config_file = temp_dir / "gameplan.yaml"
        config_file.write_text("""\
# Gameplan Configuration
areas:
  jira:
    # Jira config
    env: prod
    items: []
# Agenda section
agenda:
  sections:
    - name: Focus
""")

        mock_adapter = MagicMock()
        mock_adapter.search_issues.return_value = [
            TrackedItem(id="PROJ-1", adapter="jira", metadata={"issue": "PROJ-1", "env": "prod"}),
        ]
        mock_adapter_class.return_value = mock_adapter

        populate_jira_items(temp_dir)

        content = config_file.read_text()
        assert "# Gameplan Configuration" in content
        assert "# Jira config" in content
        assert "# Agenda section" in content


class TestSyncAll:
    """Tests for syncing all adapters."""

    @patch("cli.sync.sync_jira")
    def test_sync_all_calls_sync_jira(self, mock_sync_jira, temp_dir):
        """sync_all calls sync_jira."""
        sync_all(temp_dir)

        mock_sync_jira.assert_called_once_with(temp_dir)
