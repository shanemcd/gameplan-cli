"""Tests for sync command."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from cli.adapters.base import TrackedItem, ItemData
from cli.sync import load_config, sync_jira, sync_all


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
            TrackedItem(id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"})
        ]
        mock_adapter.fetch_item_data.return_value = ItemData(
            title="Test Issue",
            status="In Progress",
            updates=[],
            raw_data={"fields": {"assignee": {"displayName": "testuser"}}}
        )
        mock_adapter.get_storage_path.return_value = temp_dir / "tracking/areas/jira/PROJ-123"
        mock_adapter.detect_changes.return_value = False
        mock_adapter_class.return_value = mock_adapter

        sync_jira(temp_dir)

        # Verify adapter was created with config
        mock_adapter_class.assert_called_once()
        assert mock_adapter_class.call_args[0][0] == {"items": [{"issue": "PROJ-123", "env": "prod"}]}

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
            TrackedItem(id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"}),
            TrackedItem(id="PROJ-456", adapter="jira", metadata={"issue": "PROJ-456", "env": "prod"}),
        ]
        mock_adapter.fetch_item_data.side_effect = [
            ItemData(
                title="First Issue",
                status="In Progress",
                updates=[],
                raw_data={"fields": {"assignee": {"displayName": "user1"}}}
            ),
            ItemData(
                title="Second Issue",
                status="Done",
                updates=[],
                raw_data={"fields": {"assignee": {"displayName": "user2"}}}
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
            TrackedItem(id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"})
        ]
        mock_adapter.fetch_item_data.return_value = ItemData(
            title="Test Issue",
            status="In Progress",
            updates=[],
            raw_data={"fields": {"assignee": {"displayName": "testuser"}}}
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
            TrackedItem(id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"})
        ]
        mock_adapter.fetch_item_data.return_value = ItemData(
            title="",  # Empty title indicates failure
            status="",
            updates=[],
            raw_data={}
        )
        mock_adapter.get_storage_path.return_value = temp_dir / "tracking/areas/jira/PROJ-123"
        mock_adapter_class.return_value = mock_adapter

        sync_jira(temp_dir)

        captured = capsys.readouterr()
        assert "Could not fetch data" in captured.out
        mock_adapter.update_readme.assert_not_called()


class TestSyncAll:
    """Tests for syncing all adapters."""

    @patch("cli.sync.sync_jira")
    def test_sync_all_calls_sync_jira(self, mock_sync_jira, temp_dir):
        """sync_all calls sync_jira."""
        sync_all(temp_dir)

        mock_sync_jira.assert_called_once_with(temp_dir)
