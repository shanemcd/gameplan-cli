"""Jira adapter for syncing Jira issues via jirahhh CLI.

This adapter integrates with Jira systems by using the jirahhh CLI tool
(https://github.com/shanemcd/jirahhh) rather than direct API calls.

Requirements:
- jirahhh CLI tool installed (install with: uvx jirahhh)
- JIRA_* environment variables configured for jirahhh
  (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)
- jirahhh binary must be in PATH or configured via binary_path
"""
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cli.adapters.base import Adapter, ItemData, TrackedItem, sanitize_title_for_path

try:
    import pypandoc
    PANDOC_AVAILABLE = True
except ImportError:
    PANDOC_AVAILABLE = False


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
            ItemData with title, status, and raw Jira data including comments
        """
        issue_key = item.metadata.get("issue") or item.id
        env = item.metadata.get("env", "prod")

        # Call jirahhh API to get full issue data
        jirahhh_command = self._get_command("jirahhh")
        cmd = [jirahhh_command, "api", "GET", f"/rest/api/2/issue/{issue_key}", "--env", env]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            # Return empty data on error
            return ItemData(
                title="",
                status="",
                raw_data={}
            )

        # Parse JSON response
        try:
            jira_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ItemData(
                title="",
                status="",
                raw_data={}
            )

        # Extract fields
        title = ""
        status = ""

        if "fields" in jira_data:
            # JSON format from Jira API
            fields = jira_data["fields"]
            title = fields.get("summary", "")
            status_obj = fields.get("status", {})
            status = status_obj.get("name", "") if isinstance(status_obj, dict) else str(status_obj)
        else:
            # Fallback
            title = jira_data.get("summary", "")
            status = jira_data.get("status", "")

        # Fetch comments
        comments_cmd = [jirahhh_command, "api", "GET", f"/rest/api/2/issue/{issue_key}/comment", "--env", env]

        comments_result = subprocess.run(
            comments_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        comments_data = {}
        if comments_result.returncode == 0:
            try:
                comments_data = json.loads(comments_result.stdout)
            except json.JSONDecodeError:
                pass

        # Add comments to raw data
        jira_data["comments"] = comments_data

        return ItemData(
            title=title,
            status=status,
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

        # Extract assignee from raw data (same logic as sync.py)
        assignee = "Unassigned"
        if "fields" in data.raw_data:
            assignee_obj = data.raw_data["fields"].get("assignee")
            if assignee_obj and isinstance(assignee_obj, dict):
                assignee = assignee_obj.get("displayName", "Unassigned")
        else:
            assignee = data.raw_data.get("assignee", "Unassigned")

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

        Updates Status, Assignee, and Activity Log while preserving manual content.

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

        # Update Activity Log section with comments
        content = self._update_activity_log(content, data)

        return content

    def _convert_jira_to_markdown(self, jira_text: str) -> str:
        """Convert Jira wiki markup to markdown.

        Args:
            jira_text: Text in Jira wiki markup format

        Returns:
            Text converted to markdown format
        """
        if not PANDOC_AVAILABLE or not jira_text:
            return jira_text

        try:
            # Use pypandoc to convert from jira to gfm (GitHub-flavored markdown)
            return pypandoc.convert_text(jira_text, "gfm", format="jira")
        except Exception:
            # If conversion fails, return original text
            return jira_text

    def _update_activity_log(self, content: str, data: ItemData) -> str:
        """Update the Activity Log section with comments from Jira.

        Args:
            content: Current README content
            data: ItemData with comments

        Returns:
            Updated content with Activity Log populated
        """
        # Find Activity Log section
        activity_log_pattern = re.compile(
            r"^## Activity Log\s*\n.*?(?=\n## |\Z)",
            re.MULTILINE | re.DOTALL
        )

        match = activity_log_pattern.search(content)
        if not match:
            # No Activity Log section found
            return content

        # Extract comments
        comments_data = data.raw_data.get("comments", {})
        all_comments = comments_data.get("comments", [])

        if not all_comments:
            # No comments, use placeholder
            activity_log = "## Activity Log\n\n*(Auto-synced from Jira)*\n"
        else:
            # Build activity log with comments
            activity_log = "## Activity Log\n\n*(Auto-synced from Jira)*\n\n"

            # Reverse to show most recent first
            for comment in reversed(all_comments):
                author = comment.get("author", {})
                author_name = author.get("displayName", "Unknown")
                created = comment.get("created", "")
                body = comment.get("body", "").strip()

                # Convert Jira markup to markdown
                body = self._convert_jira_to_markdown(body)

                # Format timestamp
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        created = dt.strftime("%Y-%m-%d %H:%M UTC")
                    except Exception:
                        pass

                # Add comment entry
                activity_log += f"### {author_name} - {created}\n\n"
                activity_log += f"{body}\n\n"
                activity_log += "---\n\n"

        # Replace the Activity Log section
        return activity_log_pattern.sub(activity_log.rstrip() + "\n", content)

    def _get_metadata_path(self, readme_path: Path) -> Path:
        """Get the metadata file path for a given README path."""
        return readme_path.parent / ".metadata.json"

    def load_metadata(self, readme_path: Path) -> Dict[str, Any]:
        """Load previous metadata for an issue.

        Args:
            readme_path: Path to the README file

        Returns:
            Dictionary with previous metadata, empty dict if none exists
        """
        metadata_path = self._get_metadata_path(readme_path)
        if not metadata_path.exists():
            return {}

        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save_metadata(self, readme_path: Path, data: ItemData) -> None:
        """Save current metadata for an issue.

        Args:
            readme_path: Path to the README file
            data: ItemData containing current state
        """
        metadata_path = self._get_metadata_path(readme_path)

        metadata = {
            "last_sync": datetime.utcnow().isoformat(),
        }

        # Extract updated timestamp from raw data
        if "fields" in data.raw_data:
            fields = data.raw_data["fields"]
            metadata["updated"] = fields.get("updated")

        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except IOError:
            pass

    def detect_changes(self, readme_path: Path, data: ItemData) -> bool:
        """Detect if issue has been updated since last sync.

        Args:
            readme_path: Path to the README file
            data: ItemData with current state

        Returns:
            True if issue was updated, False otherwise
        """
        prev_metadata = self.load_metadata(readme_path)

        if not prev_metadata:
            # First sync, no previous data
            return False

        # Check if updated timestamp changed
        prev_updated = prev_metadata.get("updated")
        current_updated = None
        if "fields" in data.raw_data:
            current_updated = data.raw_data["fields"].get("updated")

        # Return True if timestamps differ
        return (
            prev_updated is not None
            and current_updated is not None
            and prev_updated != current_updated
        )
