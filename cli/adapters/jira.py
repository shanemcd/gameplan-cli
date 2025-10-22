"""Jira adapter for syncing Jira issues.

This adapter integrates with Jira via the jirahhh CLI tool:
https://github.com/shanemcd/jirahhh

Requires:
- jirahhh CLI installed (uvx jirahhh)
- JIRA_* environment variables configured
"""
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from cli.adapters.base import Adapter, ItemData, TrackedItem, sanitize_title_for_path


class JiraAdapter(Adapter):
    """Adapter for syncing Jira issues via jirahhh CLI."""

    def get_adapter_name(self) -> str:
        """Return adapter name."""
        return "jira"

    def load_config(self, config: Dict[str, Any]) -> List[TrackedItem]:
        """Parse Jira configuration and return tracked items.

        Args:
            config: Jira config section with 'items' list

        Returns:
            List of TrackedItem objects
        """
        items = config.get("items", [])
        tracked_items = []

        for item_config in items:
            tracked_item = TrackedItem(
                id=item_config["issue"],
                adapter="jira",
                metadata=item_config,
            )
            tracked_items.append(tracked_item)

        return tracked_items

    def fetch_item_data(
        self, item: TrackedItem, since: Optional[str] = None
    ) -> ItemData:
        """Fetch Jira issue data via jirahhh CLI.

        Args:
            item: The Jira item to fetch
            since: Optional timestamp (not used for Jira currently)

        Returns:
            ItemData with title, status, and raw Jira data
        """
        issue_key = item.metadata["issue"]
        env = item.metadata.get("env", "prod")

        # Call jirahhh view command
        cmd = ["jirahhh", "view", issue_key, "--env", env, "--json"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to fetch Jira issue {issue_key}: {result.stderr}"
            )

        # Parse JSON response
        jira_data = json.loads(result.stdout)

        return ItemData(
            title=jira_data.get("summary", ""),
            status=jira_data.get("status", "Unknown"),
            raw_data=jira_data,
        )

    def get_storage_path(
        self, item: TrackedItem, title: Optional[str] = None
    ) -> Path:
        """Get README.md path for this Jira issue.

        Args:
            item: The Jira item
            title: Optional title for directory naming

        Returns:
            Path to README.md like tracking/areas/jira/PROJ-123-title/README.md
        """
        issue_key = item.id

        # Build directory name
        if title:
            sanitized_title = sanitize_title_for_path(title)
            dir_name = f"{issue_key}-{sanitized_title}"
        else:
            dir_name = issue_key

        return (
            self.base_path
            / "tracking"
            / "areas"
            / "jira"
            / dir_name
            / "README.md"
        )

    def update_readme(
        self, readme_path: Path, data: ItemData, item: TrackedItem
    ) -> None:
        """Update README.md with Jira data.

        Updates Status and Assignee fields while preserving all manual content.

        Args:
            readme_path: Path to the README.md file
            data: New data from Jira
            item: The tracked item
        """
        issue_key = item.id
        assignee = data.raw_data.get("assignee") or "Unassigned"

        # Create directory if needed
        readme_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if README exists
        if readme_path.exists():
            content = readme_path.read_text()
            # Update existing file
            content = self._update_existing_readme(content, data, assignee)
        else:
            # Create new README
            content = self._create_new_readme(issue_key, data, assignee)

        readme_path.write_text(content)

    def _create_new_readme(
        self, issue_key: str, data: ItemData, assignee: str
    ) -> str:
        """Create new README.md content.

        Args:
            issue_key: Jira issue key
            data: Item data
            assignee: Assignee name or "Unassigned"

        Returns:
            README.md content
        """
        return f"""# {issue_key}: {data.title}

**Status**: {data.status}
**Assignee**: {assignee}

## Overview
[Add context about this issue here]

## Notes
[Add notes, decisions, and important information here]
"""

    def _update_existing_readme(
        self, content: str, data: ItemData, assignee: str
    ) -> str:
        """Update existing README.md content.

        Updates Status and Assignee fields while preserving manual content.

        Args:
            content: Current README content
            data: New data
            assignee: Assignee name

        Returns:
            Updated README content
        """
        # Update Status field
        status_pattern = r"\*\*Status\*\*:\s*.*"
        content = re.sub(
            status_pattern,
            f"**Status**: {data.status}",
            content,
        )

        # Update Assignee field
        assignee_pattern = r"\*\*Assignee\*\*:\s*.*"
        content = re.sub(
            assignee_pattern,
            f"**Assignee**: {assignee}",
            content,
        )

        return content
