"""Misc adapter for tracking local items without external sync.

This adapter manages miscellaneous tracked items that don't have
an external system (like Jira or GitHub). Items are stored locally
in README.md files with YAML frontmatter.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from cli.adapters.base import Adapter, ItemData, TrackedItem, sanitize_title_for_path


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return {}, content

    frontmatter_str = content[4:end_match.start() + 3]
    body = content[end_match.end() + 3:]

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        return {}, content

    return frontmatter, body


def build_frontmatter(data: Dict[str, Any]) -> str:
    """Build YAML frontmatter string."""
    yaml_str = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=float("inf"),
    )
    return f"---\n{yaml_str}---\n"


class MiscAdapter(Adapter):
    """Adapter for tracking miscellaneous local items."""

    def get_adapter_name(self) -> str:
        """Return adapter name."""
        return "misc"

    def load_config(self, config: Dict[str, Any]) -> List[TrackedItem]:
        """Parse misc configuration and return tracked items.

        Args:
            config: Misc config section with 'items' list

        Returns:
            List of TrackedItem objects
        """
        items = config.get("items", [])
        tracked_items = []

        for item_config in items:
            tracked_item = TrackedItem(
                id=item_config["id"],
                adapter="misc",
                metadata=item_config,
            )
            tracked_items.append(tracked_item)

        return tracked_items

    def fetch_item_data(
        self, item: TrackedItem, since: Optional[str] = None
    ) -> ItemData:
        """Fetch item data from local README.

        Args:
            item: The misc item to fetch
            since: Not used for misc items

        Returns:
            ItemData with title and status from frontmatter
        """
        title = item.metadata.get("title", item.id)
        readme_path = self.get_storage_path(item, title=title)

        if not readme_path.exists():
            # Return data from config for new items
            return ItemData(
                title=title,
                status=item.metadata.get("status", "Active"),
                raw_data=item.metadata,
            )

        # Read existing README
        content = readme_path.read_text()
        frontmatter, _ = parse_frontmatter(content)

        return ItemData(
            title=frontmatter.get("title", title),
            status=frontmatter.get("status", "Active"),
            raw_data=frontmatter,
        )

    def get_storage_path(
        self, item: TrackedItem, title: Optional[str] = None
    ) -> Path:
        """Get README.md path for this misc item.

        Args:
            item: The misc item
            title: Optional title for directory naming

        Returns:
            Path to README.md like tracking/areas/misc/item-slug/README.md
        """
        item_id = item.id

        # Build directory name
        if title:
            sanitized_title = sanitize_title_for_path(title)
            dir_name = f"{item_id}-{sanitized_title}"
        else:
            dir_name = item_id

        return (
            self.base_path
            / "tracking"
            / "areas"
            / "misc"
            / dir_name
            / "README.md"
        )

    def update_readme(
        self, readme_path: Path, data: ItemData, item: TrackedItem
    ) -> None:
        """Update README.md with item data.

        Args:
            readme_path: Path to the README.md file
            data: Item data
            item: The tracked item
        """
        # Create directory if needed
        readme_path.parent.mkdir(parents=True, exist_ok=True)

        if readme_path.exists():
            content = readme_path.read_text()
            content = self._update_existing_readme(content, data, item)
        else:
            content = self._create_new_readme(data, item)

        readme_path.write_text(content)

    def _create_new_readme(self, data: ItemData, item: TrackedItem) -> str:
        """Create new README.md content with YAML frontmatter."""
        frontmatter_data = {
            "id": item.id,
            "title": data.title,
            "status": data.status,
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }
        frontmatter = build_frontmatter(frontmatter_data)

        body = f"""
# {data.title}

## Overview

[Add context about this item here]

## Actions

- [ ] [Add actions here]

## Notes

[Add notes, decisions, and important information here]
"""
        return frontmatter + body

    def _update_existing_readme(
        self, content: str, data: ItemData, item: TrackedItem
    ) -> str:
        """Update existing README.md frontmatter."""
        existing_frontmatter, body = parse_frontmatter(content)

        # Update frontmatter fields
        existing_frontmatter["id"] = item.id
        existing_frontmatter["title"] = data.title
        existing_frontmatter["status"] = data.status
        existing_frontmatter["last_updated"] = datetime.utcnow().isoformat() + "Z"

        return build_frontmatter(existing_frontmatter) + body

    def format_agenda_item(self, item: TrackedItem) -> str:
        """Format a misc item for display in AGENDA.md.

        Args:
            item: The tracked item to format

        Returns:
            Markdown string with title, status, and link to README
        """
        item_id = item.id
        title = item.metadata.get("title", item_id)

        readme_path = self._find_readme_path(item)
        if not readme_path or not readme_path.exists():
            return f"### {title}\n**Status:** Unknown\n"

        content = readme_path.read_text()
        frontmatter, _ = parse_frontmatter(content)

        title = frontmatter.get("title", title)
        status = frontmatter.get("status", "Active")

        relative_path = str(readme_path.relative_to(self.base_path))

        lines = []
        lines.append(f"### {title}")
        lines.append(f"**Status:** {status}")
        lines.append(f"- [Details →]({relative_path})")
        lines.append("")

        return "\n".join(lines)

    def _find_readme_path(self, item: TrackedItem) -> Optional[Path]:
        """Find the README.md path for a tracked item."""
        item_id = item.id
        misc_dir = self.base_path / "tracking" / "areas" / "misc"

        if not misc_dir.exists():
            return None

        for item_dir in misc_dir.iterdir():
            if item_dir.is_dir() and item_dir.name.startswith(f"{item_id}-"):
                readme = item_dir / "README.md"
                if readme.exists():
                    return readme

        # Also check for exact match (no title suffix)
        exact_match = misc_dir / item_id / "README.md"
        if exact_match.exists():
            return exact_match

        return None
