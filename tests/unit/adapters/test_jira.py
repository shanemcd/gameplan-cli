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
        """fetch_item_data calls jirahhh API commands."""
        # Mock jirahhh responses (issue data and comments)
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "fields": {
                        "summary": "Test Issue",
                        "status": {"name": "In Progress"},
                        "assignee": {"displayName": "testuser"},
                        "updated": "2025-01-01T00:00:00.000+0000"
                    }
                })
            ),
            MagicMock(
                returncode=0,
                stdout=json.dumps({"comments": []})
            )
        ]

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        data = adapter.fetch_item_data(item)

        # Verify jirahhh was called twice (issue + comments)
        assert mock_run.call_count == 2
        # Check first call is for issue data
        assert "jirahhh" in mock_run.call_args_list[0][0][0]
        assert "/rest/api/2/issue/PROJ-123" in mock_run.call_args_list[0][0][0]
        # Check second call is for comments
        assert "/rest/api/2/issue/PROJ-123/comment" in mock_run.call_args_list[1][0][0]

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


class TestJiraErrorHandling:
    """Test error handling in Jira adapter."""

    @patch("subprocess.run")
    def test_fetch_item_data_handles_command_failure(self, mock_run, temp_dir):
        """fetch_item_data returns empty ItemData if jirahhh command fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"})

        data = adapter.fetch_item_data(item)

        assert data.title == ""
        assert data.status == ""
        assert data.raw_data == {}

    @patch("subprocess.run")
    def test_fetch_item_data_handles_json_decode_error(self, mock_run, temp_dir):
        """fetch_item_data handles invalid JSON response."""
        mock_run.return_value = MagicMock(returncode=0, stdout="not valid json")

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"})

        data = adapter.fetch_item_data(item)

        assert data.title == ""
        assert data.status == ""
        assert data.raw_data == {}

    @patch("subprocess.run")
    def test_fetch_item_data_handles_comments_json_error(self, mock_run, temp_dir):
        """fetch_item_data handles invalid JSON from comments endpoint."""
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "fields": {
                        "summary": "Test Issue",
                        "status": {"name": "Open"}
                    }
                })
            ),
            MagicMock(returncode=0, stdout="invalid json")
        ]

        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={"issue": "PROJ-123", "env": "prod"})

        data = adapter.fetch_item_data(item)

        assert data.title == "Test Issue"
        assert data.status == "Open"
        # Comments should be empty dict due to JSON error
        assert data.raw_data.get("comments") == {}


class TestJiraMetadata:
    """Test metadata handling for change detection."""

    def test_get_metadata_path(self, temp_dir):
        """_get_metadata_path returns correct path."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"

        metadata_path = adapter._get_metadata_path(readme_path)

        assert metadata_path == temp_dir / "tracking/areas/jira/PROJ-123/.metadata.json"

    def test_save_metadata_creates_file(self, temp_dir):
        """save_metadata creates .metadata.json file."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"
        readme_path.parent.mkdir(parents=True)

        data = ItemData(
            title="Test Issue",
            status="Open",
            raw_data={"fields": {"updated": "2025-01-15T10:00:00.000+0000"}}
        )

        adapter.save_metadata(readme_path, data)

        metadata_path = readme_path.parent / ".metadata.json"
        assert metadata_path.exists()

    def test_save_metadata_includes_timestamps(self, temp_dir):
        """save_metadata includes last_sync and updated timestamps."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"
        readme_path.parent.mkdir(parents=True)

        data = ItemData(
            title="Test Issue",
            status="Open",
            raw_data={"fields": {"updated": "2025-01-15T10:00:00.000+0000"}}
        )

        adapter.save_metadata(readme_path, data)

        metadata_path = readme_path.parent / ".metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        assert "last_sync" in metadata
        assert metadata["updated"] == "2025-01-15T10:00:00.000+0000"

    def test_save_metadata_handles_io_error(self, temp_dir):
        """save_metadata handles IOError gracefully."""
        adapter = JiraAdapter({}, temp_dir)
        # Path that doesn't exist and can't be created
        readme_path = temp_dir / "nonexistent/dir/README.md"

        data = ItemData(title="Test", status="Open", raw_data={})

        # Should not raise exception
        adapter.save_metadata(readme_path, data)

    def test_load_metadata_returns_dict(self, temp_dir):
        """load_metadata returns metadata dict."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"
        readme_path.parent.mkdir(parents=True)

        # Save metadata first
        metadata_path = readme_path.parent / ".metadata.json"
        with open(metadata_path, "w") as f:
            json.dump({"last_sync": "2025-01-15", "updated": "2025-01-14"}, f)

        result = adapter.load_metadata(readme_path)

        assert result["last_sync"] == "2025-01-15"
        assert result["updated"] == "2025-01-14"

    def test_load_metadata_returns_empty_if_missing(self, temp_dir):
        """load_metadata returns empty dict if file doesn't exist."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"

        result = adapter.load_metadata(readme_path)

        assert result == {}

    def test_load_metadata_handles_corrupt_json(self, temp_dir):
        """load_metadata returns empty dict if JSON is corrupt."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"
        readme_path.parent.mkdir(parents=True)

        # Create corrupt metadata file
        metadata_path = readme_path.parent / ".metadata.json"
        metadata_path.write_text("not valid json")

        result = adapter.load_metadata(readme_path)

        assert result == {}


class TestJiraChangeDetection:
    """Test change detection logic."""

    def test_detect_changes_returns_false_on_first_sync(self, temp_dir):
        """detect_changes returns False if no previous metadata."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"

        data = ItemData(
            title="Test",
            status="Open",
            raw_data={"fields": {"updated": "2025-01-15T10:00:00.000+0000"}}
        )

        has_changes = adapter.detect_changes(readme_path, data)

        assert has_changes is False

    def test_detect_changes_returns_false_if_no_change(self, temp_dir):
        """detect_changes returns False if updated timestamp unchanged."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"
        readme_path.parent.mkdir(parents=True)

        # Save previous metadata
        metadata_path = readme_path.parent / ".metadata.json"
        with open(metadata_path, "w") as f:
            json.dump({"updated": "2025-01-15T10:00:00.000+0000"}, f)

        # Check with same timestamp
        data = ItemData(
            title="Test",
            status="Open",
            raw_data={"fields": {"updated": "2025-01-15T10:00:00.000+0000"}}
        )

        has_changes = adapter.detect_changes(readme_path, data)

        assert has_changes is False

    def test_detect_changes_returns_true_if_timestamp_changed(self, temp_dir):
        """detect_changes returns True if updated timestamp changed."""
        adapter = JiraAdapter({}, temp_dir)
        readme_path = temp_dir / "tracking/areas/jira/PROJ-123/README.md"
        readme_path.parent.mkdir(parents=True)

        # Save previous metadata
        metadata_path = readme_path.parent / ".metadata.json"
        with open(metadata_path, "w") as f:
            json.dump({"updated": "2025-01-15T10:00:00.000+0000"}, f)

        # Check with different timestamp
        data = ItemData(
            title="Test",
            status="In Progress",
            raw_data={"fields": {"updated": "2025-01-16T10:00:00.000+0000"}}
        )

        has_changes = adapter.detect_changes(readme_path, data)

        assert has_changes is True


class TestJirahhhCustomBinaryPath:
    """Test custom binary path configuration."""

    @patch("subprocess.run")
    def test_uses_default_jirahhh_binary_when_no_config(self, mock_run, temp_dir):
        """Uses 'jirahhh' binary when no custom binary_path configured."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "Open"}
                }
            })
        )

        # No binary_path in config
        adapter = JiraAdapter({}, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        adapter.fetch_item_data(item)

        # Should use default "jirahhh" command
        call_args = mock_run.call_args_list[0][0][0]
        assert call_args[0] == "jirahhh"

    @patch("subprocess.run")
    def test_uses_custom_binary_path_when_configured(self, mock_run, temp_dir):
        """Uses custom binary path when binary_path configured."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "Open"}
                }
            })
        )

        # Custom binary path in config
        config = {"binary_path": "/custom/path/to/jirahhh"}
        adapter = JiraAdapter(config, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        adapter.fetch_item_data(item)

        # Should use custom path
        call_args = mock_run.call_args_list[0][0][0]
        assert call_args[0] == "/custom/path/to/jirahhh"

    @patch("subprocess.run")
    def test_custom_binary_path_used_for_both_calls(self, mock_run, temp_dir):
        """Custom binary path used for both issue and comments API calls."""
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout=json.dumps({
                    "fields": {
                        "summary": "Test Issue",
                        "status": {"name": "Open"}
                    }
                })
            ),
            MagicMock(
                returncode=0,
                stdout=json.dumps({"comments": []})
            )
        ]

        config = {"binary_path": "/usr/local/bin/jirahhh"}
        adapter = JiraAdapter(config, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        adapter.fetch_item_data(item)

        # Both calls should use custom path
        assert mock_run.call_count == 2
        first_call_args = mock_run.call_args_list[0][0][0]
        second_call_args = mock_run.call_args_list[1][0][0]
        assert first_call_args[0] == "/usr/local/bin/jirahhh"
        assert second_call_args[0] == "/usr/local/bin/jirahhh"

    @patch("subprocess.run")
    def test_relative_binary_path_supported(self, mock_run, temp_dir):
        """Supports relative paths for binary_path."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "Open"}
                }
            })
        )

        config = {"binary_path": "./bin/jirahhh"}
        adapter = JiraAdapter(config, temp_dir)
        item = TrackedItem(
            id="PROJ-123",
            adapter="jira",
            metadata={"issue": "PROJ-123", "env": "prod"}
        )

        adapter.fetch_item_data(item)

        call_args = mock_run.call_args_list[0][0][0]
        assert call_args[0] == "./bin/jirahhh"


class TestJiraActivityLog:
    """Test Activity Log updates."""

    def test_update_activity_log_with_no_comments(self, temp_dir):
        """_update_activity_log shows placeholder if no comments."""
        adapter = JiraAdapter({}, temp_dir)

        content = """# PROJ-123: Test Issue

**Status**: Open
**Assignee**: unassigned

## Overview
Test

## Activity Log

Old activity here

## Notes
Notes here
"""
        data = ItemData(
            title="Test",
            status="Open",
            raw_data={"comments": {"comments": []}}
        )

        result = adapter._update_activity_log(content, data)

        assert "## Activity Log" in result
        assert "*(Auto-synced from Jira)*" in result
        assert "Old activity here" not in result

    def test_update_activity_log_with_comments(self, temp_dir):
        """_update_activity_log populates with Jira comments."""
        adapter = JiraAdapter({}, temp_dir)

        content = """# PROJ-123: Test Issue

**Status**: Open

## Activity Log

Placeholder

## Notes
Notes
"""
        data = ItemData(
            title="Test",
            status="Open",
            raw_data={
                "comments": {
                    "comments": [
                        {
                            "author": {"displayName": "John Doe"},
                            "created": "2025-01-15T10:00:00.000Z",
                            "body": "This is a test comment"
                        }
                    ]
                }
            }
        )

        result = adapter._update_activity_log(content, data)

        assert "John Doe" in result
        assert "2025-01-15 10:00 UTC" in result
        assert "This is a test comment" in result

    def test_update_activity_log_returns_unchanged_if_no_section(self, temp_dir):
        """_update_activity_log returns content unchanged if no Activity Log section."""
        adapter = JiraAdapter({}, temp_dir)

        content = """# PROJ-123: Test Issue

**Status**: Open

## Overview
No activity log section
"""
        data = ItemData(title="Test", status="Open", raw_data={})

        result = adapter._update_activity_log(content, data)

        assert result == content

    def test_convert_jira_to_markdown_without_pandoc(self, temp_dir, monkeypatch):
        """_convert_jira_to_markdown returns original text if pandoc unavailable."""
        # Simulate PANDOC_AVAILABLE = False
        import cli.adapters.jira as jira_module
        monkeypatch.setattr(jira_module, "PANDOC_AVAILABLE", False)

        adapter = JiraAdapter({}, temp_dir)
        jira_text = "h1. Header\n\nSome text"

        result = adapter._convert_jira_to_markdown(jira_text)

        # Should return unchanged
        assert result == jira_text

    def test_convert_jira_to_markdown_with_empty_text(self, temp_dir):
        """_convert_jira_to_markdown handles empty text."""
        adapter = JiraAdapter({}, temp_dir)

        result = adapter._convert_jira_to_markdown("")

        assert result == ""

    @patch("cli.adapters.jira.pypandoc")
    def test_convert_jira_to_markdown_handles_exception(self, mock_pypandoc, temp_dir):
        """_convert_jira_to_markdown returns original text on conversion error."""
        # Simulate pypandoc available but conversion fails
        import cli.adapters.jira as jira_module
        jira_module.PANDOC_AVAILABLE = True

        mock_pypandoc.convert_text.side_effect = Exception("Conversion failed")

        adapter = JiraAdapter({}, temp_dir)
        jira_text = "h1. Header"

        result = adapter._convert_jira_to_markdown(jira_text)

        assert result == jira_text
