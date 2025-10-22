"""Tests for the Jira adapter.

The Jira adapter integrates with Jira via the jirahhh CLI tool
(https://github.com/shanemcd/jirahhh).
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.adapters.base import Adapter, ItemData, TrackedItem
from cli.adapters.jira import JiraAdapter


class TestJiraAdapterBasics:
    """Test basic Jira adapter functionality."""

    def test_jira_adapter_name(self, temp_dir):
        """Jira adapter reports correct name."""
        adapter = JiraAdapter({}, temp_dir)
        assert adapter.get_adapter_name() == "jira"

    def test_jira_adapter_is_adapter_subclass(self):
        """JiraAdapter should inherit from Adapter."""
        assert issubclass(JiraAdapter, Adapter)

    def test_jira_adapter_initialization(self, temp_dir):
        """JiraAdapter can be instantiated with config and base_path."""
        config = {"items": []}
        adapter = JiraAdapter(config, temp_dir)

        assert adapter.config == config
        assert adapter.base_path == temp_dir


class TestJiraConfigLoading:
    """Test Jira configuration parsing."""

    def test_load_config_parses_single_item(self, temp_dir):
        """load_config parses single Jira item."""
        config = {
            "items": [
                {"issue": "PROJ-123", "env": "prod"}
            ]
        }
        adapter = JiraAdapter(config, temp_dir)
        items = adapter.load_config(config)

        assert len(items) == 1
        assert items[0].id == "PROJ-123"
        assert items[0].adapter == "jira"
        assert items[0].metadata["issue"] == "PROJ-123"
        assert items[0].metadata["env"] == "prod"

    def test_load_config_parses_multiple_items(self, temp_dir):
        """load_config parses multiple Jira items."""
        config = {
            "items": [
                {"issue": "PROJ-123", "env": "prod"},
                {"issue": "PROJ-456", "env": "stage"},
                {"issue": "PROJ-789", "env": "prod"}
            ]
        }
        adapter = JiraAdapter(config, temp_dir)
        items = adapter.load_config(config)

        assert len(items) == 3
        assert items[0].id == "PROJ-123"
        assert items[1].id == "PROJ-456"
        assert items[2].id == "PROJ-789"

    def test_load_config_handles_empty_items(self, temp_dir):
        """load_config handles empty items list."""
        config = {"items": []}
        adapter = JiraAdapter(config, temp_dir)
        items = adapter.load_config(config)

        assert items == []


class TestJiraFetchItemData:
    """Test fetching data from Jira via jirahhh."""

    @patch("subprocess.run")
    def test_fetch_item_data_calls_jirahhh(self, mock_run, temp_dir):
        """fetch_item_data calls jirahhh view command."""
        # Mock jirahhh response
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "key": "PROJ-123",
                "summary": "Test Issue",
                "status": "In Progress",
                "assignee": "testuser"
            })
        )

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        data = adapter.fetch_item_data(item)

        # Verify jirahhh was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "jirahhh" in call_args[0][0]
        assert "view" in call_args[0][0]
        assert "PROJ-123" in call_args[0][0]

    @patch("subprocess.run")
    def test_fetch_item_data_returns_item_data(self, mock_run, temp_dir):
        """fetch_item_data returns ItemData with parsed info."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "key": "PROJ-123",
                "summary": "Fix API Bug",
                "status": "In Progress",
                "assignee": "johndoe"
            })
        )

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        data = adapter.fetch_item_data(item)

        assert isinstance(data, ItemData)
        assert data.title == "Fix API Bug"
        assert data.status == "In Progress"

    @patch("subprocess.run")
    def test_fetch_item_data_uses_env_from_metadata(self, mock_run, temp_dir):
        """fetch_item_data passes env parameter to jirahhh."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"key": "PROJ-123", "summary": "Test", "status": "Open"})
        )

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "stage"}
        )

        adapter.fetch_item_data(item)

        # Verify --env stage was passed
        call_args = mock_run.call_args[0][0]
        assert "--env" in call_args
        assert "stage" in call_args

    @patch("subprocess.run")
    def test_fetch_item_data_handles_missing_assignee(self, mock_run, temp_dir):
        """fetch_item_data handles Jira issues without assignee."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "key": "PROJ-123",
                "summary": "Unassigned Issue",
                "status": "Open",
                "assignee": None
            })
        )

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        data = adapter.fetch_item_data(item)

        assert data.title == "Unassigned Issue"
        assert data.status == "Open"


class TestJiraStoragePath:
    """Test Jira README.md storage path generation."""

    def test_get_storage_path_uses_issue_key(self, temp_dir):
        """get_storage_path uses issue key in path."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        path = adapter.get_storage_path(item)

        assert "PROJ-123" in str(path)
        assert path.name == "README.md"

    def test_get_storage_path_includes_sanitized_title(self, temp_dir):
        """get_storage_path includes sanitized title in directory name."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        path = adapter.get_storage_path(item, title="Fix: API Bug (Critical!)")

        assert "PROJ-123" in str(path)
        assert "fix-api-bug-critical" in str(path)

    def test_get_storage_path_structure(self, temp_dir):
        """get_storage_path follows tracking/areas/jira/ structure."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        path = adapter.get_storage_path(item, title="Test Issue")

        assert "tracking/areas/jira" in str(path)
        assert path.name == "README.md"


class TestJiraUpdateReadme:
    """Test updating README.md with Jira data."""

    def test_update_readme_creates_new_file(self, temp_dir):
        """update_readme creates README.md if it doesn't exist."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )
        data = ItemData(
            title="Test Issue",
            status="In Progress",
            raw_data={"assignee": "johndoe"}
        )
        readme_path = temp_dir / "README.md"

        adapter.update_readme(readme_path, data, item)

        assert readme_path.exists()
        content = readme_path.read_text()
        assert "PROJ-123" in content
        assert "Test Issue" in content

    def test_update_readme_includes_status(self, temp_dir):
        """update_readme includes status field."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={})
        data = ItemData(
            title="Test Issue",
            status="In Progress",
            raw_data={"assignee": "johndoe"}
        )
        readme_path = temp_dir / "README.md"

        adapter.update_readme(readme_path, data, item)

        content = readme_path.read_text()
        assert "Status" in content or "status" in content
        assert "In Progress" in content

    def test_update_readme_includes_assignee(self, temp_dir):
        """update_readme includes assignee field."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={})
        data = ItemData(
            title="Test Issue",
            status="Open",
            raw_data={"assignee": "johndoe"}
        )
        readme_path = temp_dir / "README.md"

        adapter.update_readme(readme_path, data, item)

        content = readme_path.read_text()
        assert "Assignee" in content or "assignee" in content
        assert "johndoe" in content

    def test_update_readme_is_idempotent(self, temp_dir):
        """update_readme can be run multiple times with same result."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={})
        data = ItemData(
            title="Test Issue",
            status="In Progress",
            raw_data={"assignee": "johndoe"}
        )
        readme_path = temp_dir / "README.md"

        # First update
        adapter.update_readme(readme_path, data, item)
        first_content = readme_path.read_text()

        # Second update with same data
        adapter.update_readme(readme_path, data, item)
        second_content = readme_path.read_text()

        # Should be identical (or at least not duplicate content)
        assert first_content == second_content

    def test_update_readme_preserves_manual_content(self, temp_dir):
        """update_readme preserves manually-added sections."""
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={})
        readme_path = temp_dir / "README.md"

        # Create initial README with manual content
        initial_content = """# PROJ-123: Test Issue

**Status**: Open
**Assignee**: unassigned

## Overview
This is manually written context that should be preserved.

## Notes
- Important note 1
- Important note 2
"""
        readme_path.write_text(initial_content)

        # Update with new data
        data = ItemData(
            title="Test Issue",
            status="In Progress",
            raw_data={"assignee": "johndoe"}
        )
        adapter.update_readme(readme_path, data, item)

        content = readme_path.read_text()
        # Manual content should be preserved
        assert "This is manually written context" in content
        assert "Important note 1" in content
        assert "Important note 2" in content
        # But status/assignee should be updated
        assert "In Progress" in content
        assert "johndoe" in content
