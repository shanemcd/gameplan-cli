"""Tests for the Misc adapter."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cli.adapters.base import ItemData, TrackedItem
from cli.adapters.misc import MiscAdapter, build_frontmatter, parse_frontmatter


class TestMiscParseFrontmatter:
    """Test frontmatter parsing utilities."""

    def test_parse_valid_frontmatter(self):
        content = "---\ntitle: Test\nstatus: Active\n---\n# Body"
        fm, body = parse_frontmatter(content)
        assert fm["title"] == "Test"
        assert fm["status"] == "Active"
        assert body == "# Body"

    def test_parse_no_frontmatter(self):
        content = "# Just a heading"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_no_closing_delimiter(self):
        content = "---\ntitle: Test\n# No closing"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_invalid_yaml(self):
        content = "---\n: [invalid\n---\n# Body"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_build_frontmatter(self):
        data = {"id": "test", "title": "Test Item"}
        result = build_frontmatter(data)
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert "id: test" in result
        assert "title: Test Item" in result


class TestMiscAdapterConfig:
    """Test MiscAdapter configuration."""

    def test_get_adapter_name(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        assert adapter.get_adapter_name() == "misc"

    def test_load_config(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        config = {
            "items": [
                {"id": "item-1", "title": "First Item"},
                {"id": "item-2", "title": "Second Item"},
            ]
        }
        items = adapter.load_config(config)
        assert len(items) == 2
        assert items[0].id == "item-1"
        assert items[1].id == "item-2"
        assert items[0].adapter == "misc"

    def test_load_config_empty(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        items = adapter.load_config({})
        assert items == []


class TestMiscAdapterStorage:
    """Test MiscAdapter storage paths."""

    def test_get_storage_path_with_title(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="my-item", adapter="misc")
        path = adapter.get_storage_path(item, title="My Item Title")
        assert path == temp_dir / "tracking" / "areas" / "misc" / "my-item-my-item-title" / "README.md"

    def test_get_storage_path_without_title(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="my-item", adapter="misc")
        path = adapter.get_storage_path(item)
        assert path == temp_dir / "tracking" / "areas" / "misc" / "my-item" / "README.md"


class TestMiscFetchItemData:
    """Test MiscAdapter.fetch_item_data."""

    def test_fetch_new_item_returns_config_data(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(
            id="new-item", adapter="misc",
            metadata={"id": "new-item", "title": "New Item"}
        )
        data = adapter.fetch_item_data(item)
        assert data.title == "New Item"
        assert data.status == "Active"

    def test_fetch_existing_item_reads_frontmatter(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(
            id="existing", adapter="misc",
            metadata={"id": "existing", "title": "Existing Item"}
        )
        # Create the README with frontmatter
        readme_path = adapter.get_storage_path(item, title="Existing Item")
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text("---\ntitle: Updated Title\nstatus: Done\n---\n# Body")

        data = adapter.fetch_item_data(item)
        assert data.title == "Updated Title"
        assert data.status == "Done"


class TestMiscUpdateReadme:
    """Test MiscAdapter.update_readme."""

    @patch("cli.adapters.misc.datetime")
    def test_creates_new_readme(self, mock_dt, temp_dir):
        mock_dt.utcnow.return_value = datetime(2026, 1, 15, 12, 0, 0)
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="test-item", adapter="misc")
        data = ItemData(title="Test Item", status="Active")
        readme_path = temp_dir / "test" / "README.md"

        adapter.update_readme(readme_path, data, item)

        content = readme_path.read_text()
        assert "---" in content
        assert "id: test-item" in content
        assert "title: Test Item" in content
        assert "status: Active" in content
        assert "# Test Item" in content
        assert "## Overview" in content

    @patch("cli.adapters.misc.datetime")
    def test_updates_existing_readme(self, mock_dt, temp_dir):
        mock_dt.utcnow.return_value = datetime(2026, 1, 15, 12, 0, 0)
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="test-item", adapter="misc")
        readme_path = temp_dir / "test" / "README.md"
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(
            "---\nid: test-item\ntitle: Old Title\nstatus: Active\n---\n"
            "# Old Title\n\nManual content here\n"
        )

        data = ItemData(title="New Title", status="Done")
        adapter.update_readme(readme_path, data, item)

        content = readme_path.read_text()
        assert "title: New Title" in content
        assert "status: Done" in content
        assert "Manual content here" in content

    @patch("cli.adapters.misc.datetime")
    def test_update_readme_is_idempotent(self, mock_dt, temp_dir):
        mock_dt.utcnow.return_value = datetime(2026, 1, 15, 12, 0, 0)
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="test-item", adapter="misc")
        data = ItemData(title="Test Item", status="Active")
        readme_path = temp_dir / "test" / "README.md"

        adapter.update_readme(readme_path, data, item)
        first = readme_path.read_text()

        adapter.update_readme(readme_path, data, item)
        second = readme_path.read_text()

        assert first == second


class TestMiscFormatAgendaItem:
    """Test MiscAdapter.format_agenda_item."""

    def test_format_with_existing_readme(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(
            id="my-item", adapter="misc",
            metadata={"id": "my-item", "title": "My Item"}
        )
        # Create readme
        readme_dir = temp_dir / "tracking" / "areas" / "misc" / "my-item-my-item"
        readme_dir.mkdir(parents=True)
        (readme_dir / "README.md").write_text(
            "---\ntitle: My Item\nstatus: Active\n---\n# My Item\n"
        )

        result = adapter.format_agenda_item(item)
        assert "### My Item" in result
        assert "**Status:** Active" in result
        assert "[Details →](" in result

    def test_format_without_readme(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(
            id="missing", adapter="misc",
            metadata={"id": "missing", "title": "Missing Item"}
        )

        result = adapter.format_agenda_item(item)
        assert "### Missing Item" in result
        assert "**Status:** Unknown" in result


class TestMiscFindReadmePath:
    """Test MiscAdapter._find_readme_path."""

    def test_find_by_prefix(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="my-item", adapter="misc")
        readme_dir = temp_dir / "tracking" / "areas" / "misc" / "my-item-some-title"
        readme_dir.mkdir(parents=True)
        (readme_dir / "README.md").write_text("# Content")

        result = adapter._find_readme_path(item)
        assert result == readme_dir / "README.md"

    def test_find_exact_match(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="my-item", adapter="misc")
        readme_dir = temp_dir / "tracking" / "areas" / "misc" / "my-item"
        readme_dir.mkdir(parents=True)
        (readme_dir / "README.md").write_text("# Content")

        result = adapter._find_readme_path(item)
        assert result == readme_dir / "README.md"

    def test_find_returns_none_when_missing(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="nonexistent", adapter="misc")
        (temp_dir / "tracking" / "areas" / "misc").mkdir(parents=True)

        result = adapter._find_readme_path(item)
        assert result is None

    def test_find_returns_none_when_dir_missing(self, temp_dir):
        adapter = MiscAdapter({}, temp_dir)
        item = TrackedItem(id="anything", adapter="misc")

        result = adapter._find_readme_path(item)
        assert result is None
