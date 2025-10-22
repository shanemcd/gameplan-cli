"""Tests for the base adapter interface.

These tests verify that the Adapter ABC enforces the contract that all
concrete adapters must implement.
"""
from abc import ABC
from pathlib import Path

import pytest

from cli.adapters.base import Adapter, ItemData, TrackedItem, sanitize_title_for_path


class TestDataClasses:
    """Test the TrackedItem and ItemData dataclasses."""

    def test_tracked_item_creation(self):
        """TrackedItem can be created with required fields."""
        item = TrackedItem(id="PROJ-123", adapter="jira", metadata={"env": "prod"})

        assert item.id == "PROJ-123"
        assert item.adapter == "jira"
        assert item.metadata == {"env": "prod"}

    def test_tracked_item_default_metadata(self):
        """TrackedItem metadata defaults to empty dict."""
        item = TrackedItem(id="PROJ-123", adapter="jira")

        assert item.metadata == {}

    def test_item_data_creation(self):
        """ItemData can be created with required fields."""
        data = ItemData(
            title="Test Issue",
            status="In Progress",
            updates=[{"type": "comment", "text": "Added comment"}],
            raw_data={"key": "PROJ-123"},
        )

        assert data.title == "Test Issue"
        assert data.status == "In Progress"
        assert len(data.updates) == 1
        assert data.raw_data["key"] == "PROJ-123"

    def test_item_data_default_fields(self):
        """ItemData updates and raw_data default to empty collections."""
        data = ItemData(title="Test", status="Open")

        assert data.updates == []
        assert data.raw_data == {}


class TestSanitizeTitleForPath:
    """Test the title sanitization utility."""

    def test_sanitize_removes_special_characters(self):
        """Sanitize removes special characters and punctuation."""
        result = sanitize_title_for_path("Fix: Bug in API (Critical!)")

        assert result == "fix-bug-in-api-critical"

    def test_sanitize_replaces_spaces_with_hyphens(self):
        """Sanitize replaces spaces with hyphens."""
        result = sanitize_title_for_path("Feature Request API Update")

        assert result == "feature-request-api-update"

    def test_sanitize_converts_to_lowercase(self):
        """Sanitize converts to lowercase."""
        result = sanitize_title_for_path("UPPERCASE Title")

        assert result == "uppercase-title"

    def test_sanitize_truncates_long_titles(self):
        """Sanitize truncates titles longer than max_length."""
        long_title = "This is a very long title that exceeds the maximum length limit"
        result = sanitize_title_for_path(long_title, max_length=20)

        assert len(result) <= 20
        assert not result.endswith("-")  # No trailing hyphen

    def test_sanitize_removes_leading_trailing_hyphens(self):
        """Sanitize removes leading and trailing hyphens."""
        result = sanitize_title_for_path("---Test Title---")

        assert result == "test-title"

    def test_sanitize_handles_multiple_consecutive_spaces(self):
        """Sanitize collapses multiple spaces into single hyphen."""
        result = sanitize_title_for_path("Multiple    Spaces    Here")

        assert result == "multiple-spaces-here"


class TestAdapterInterface:
    """Test the Adapter ABC interface."""

    def test_adapter_is_abstract_base_class(self):
        """Adapter should be an ABC."""
        assert issubclass(Adapter, ABC)

    def test_adapter_cannot_be_instantiated_directly(self):
        """Adapter ABC cannot be instantiated without implementing abstract methods."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Adapter({}, Path("/tmp"))

    def test_adapter_requires_abstract_methods(self):
        """Adapter requires all abstract methods to be implemented."""

        class IncompleteAdapter(Adapter):
            """Adapter missing required methods."""

            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteAdapter({}, Path("/tmp"))

    def test_minimal_concrete_adapter_can_be_instantiated(self, temp_dir):
        """Concrete adapter with all abstract methods can be instantiated."""

        class MinimalAdapter(Adapter):
            def get_adapter_name(self):
                return "minimal"

            def load_config(self, config):
                return []

            def fetch_item_data(self, item, since=None):
                return ItemData(title="Test", status="Open")

            def get_storage_path(self, item, title=None):
                return self.base_path / "test" / "README.md"

            def update_readme(self, readme_path, data, item):
                pass

        adapter = MinimalAdapter({}, temp_dir)
        assert adapter.config == {}
        assert adapter.base_path == temp_dir

    def test_concrete_adapter_implements_get_adapter_name(self, temp_dir):
        """Concrete adapter must implement get_adapter_name()."""

        class TestAdapter(Adapter):
            def get_adapter_name(self):
                return "test"

            def load_config(self, config):
                return []

            def fetch_item_data(self, item, since=None):
                return ItemData(title="Test", status="Open")

            def get_storage_path(self, item, title=None):
                return self.base_path / "README.md"

            def update_readme(self, readme_path, data, item):
                pass

        adapter = TestAdapter({}, temp_dir)
        assert adapter.get_adapter_name() == "test"

    def test_concrete_adapter_implements_load_config(self, temp_dir):
        """Concrete adapter must implement load_config()."""

        class TestAdapter(Adapter):
            def get_adapter_name(self):
                return "test"

            def load_config(self, config):
                items = config.get("items", [])
                return [
                    TrackedItem(id=item["id"], adapter="test", metadata=item)
                    for item in items
                ]

            def fetch_item_data(self, item, since=None):
                return ItemData(title="Test", status="Open")

            def get_storage_path(self, item, title=None):
                return self.base_path / "README.md"

            def update_readme(self, readme_path, data, item):
                pass

        adapter = TestAdapter({}, temp_dir)
        config = {"items": [{"id": "TEST-1"}, {"id": "TEST-2"}]}
        items = adapter.load_config(config)

        assert len(items) == 2
        assert items[0].id == "TEST-1"
        assert items[1].id == "TEST-2"

    def test_concrete_adapter_implements_fetch_item_data(self, temp_dir):
        """Concrete adapter must implement fetch_item_data()."""

        class TestAdapter(Adapter):
            def get_adapter_name(self):
                return "test"

            def load_config(self, config):
                return []

            def fetch_item_data(self, item, since=None):
                return ItemData(
                    title=f"Title for {item.id}",
                    status="In Progress",
                    raw_data={"since": since},
                )

            def get_storage_path(self, item, title=None):
                return self.base_path / "README.md"

            def update_readme(self, readme_path, data, item):
                pass

        adapter = TestAdapter({}, temp_dir)
        item = TrackedItem(id="TEST-123", adapter="test")
        data = adapter.fetch_item_data(item, since="2025-10-01")

        assert data.title == "Title for TEST-123"
        assert data.status == "In Progress"
        assert data.raw_data["since"] == "2025-10-01"

    def test_concrete_adapter_implements_get_storage_path(self, temp_dir):
        """Concrete adapter must implement get_storage_path()."""

        class TestAdapter(Adapter):
            def get_adapter_name(self):
                return "test"

            def load_config(self, config):
                return []

            def fetch_item_data(self, item, since=None):
                return ItemData(title="Test", status="Open")

            def get_storage_path(self, item, title=None):
                return self.base_path / "tracking" / item.id / "README.md"

            def update_readme(self, readme_path, data, item):
                pass

        adapter = TestAdapter({}, temp_dir)
        item = TrackedItem(id="TEST-456", adapter="test")
        path = adapter.get_storage_path(item)

        assert path == temp_dir / "tracking" / "TEST-456" / "README.md"

    def test_concrete_adapter_implements_update_readme(self, temp_dir):
        """Concrete adapter must implement update_readme()."""

        class TestAdapter(Adapter):
            def get_adapter_name(self):
                return "test"

            def load_config(self, config):
                return []

            def fetch_item_data(self, item, since=None):
                return ItemData(title="Test", status="Open")

            def get_storage_path(self, item, title=None):
                return self.base_path / "README.md"

            def update_readme(self, readme_path, data, item):
                readme_path.parent.mkdir(parents=True, exist_ok=True)
                readme_path.write_text(f"# {data.title}\nStatus: {data.status}")

        adapter = TestAdapter({}, temp_dir)
        item = TrackedItem(id="TEST-789", adapter="test")
        data = ItemData(title="Test Issue", status="In Progress")
        readme_path = temp_dir / "README.md"

        adapter.update_readme(readme_path, data, item)

        assert readme_path.exists()
        content = readme_path.read_text()
        assert "# Test Issue" in content
        assert "Status: In Progress" in content
