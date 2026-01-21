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
from typing import Any, Dict, List, Optional, Tuple

import yaml

from cli.adapters.base import Adapter, ItemData, TrackedItem, sanitize_title_for_path


# Custom YAML representer to force double-quoted strings for multiline content
# This prevents PyYAML from using literal block style which creates odd formatting
def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    """Custom string representer that uses double quotes for multiline strings."""
    if '\n' in data:
        # Force double-quoted style for multiline strings
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


# Create a custom dumper class with our representer
class _FrontmatterDumper(yaml.SafeDumper):
    pass


_FrontmatterDumper.add_representer(str, _str_representer)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown content with optional YAML frontmatter

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
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
    """Build YAML frontmatter string.

    Args:
        data: Dictionary to serialize as YAML

    Returns:
        Frontmatter string with --- delimiters
    """
    # Use custom dumper that forces double-quoted strings for multiline content
    # and width=inf to prevent line wrapping
    yaml_str = yaml.dump(
        data,
        Dumper=_FrontmatterDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=float("inf"),
    )
    return f"---\n{yaml_str}---\n"

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

        Updates Title, Status and Assignee fields while preserving all manual content.

        Args:
            readme_path: Path to the README.md file
            data: New data from Jira
            item: The tracked item
        """
        issue_key = item.id

        # Extract assignee from fields.assignee.displayName
        assignee = "Unassigned"
        if "fields" in data.raw_data:
            assignee_obj = data.raw_data["fields"].get("assignee")
            if assignee_obj and isinstance(assignee_obj, dict):
                assignee = assignee_obj.get("displayName", "Unassigned")

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
        """Create new README.md content with YAML frontmatter.

        Args:
            issue_key: Jira issue key
            data: Item data
            assignee: Assignee name or "Unassigned"

        Returns:
            README.md content with frontmatter
        """
        # Build frontmatter
        frontmatter_data = self._build_frontmatter_data(issue_key, data, assignee)
        frontmatter = build_frontmatter(frontmatter_data)

        # Build body (manual content area)
        body = f"""
# {issue_key}: {data.title}

## Overview

[Add context about this issue here]

## Notes

[Add notes, decisions, and important information here]
"""
        return frontmatter + body

    def _build_frontmatter_data(
        self, issue_key: str, data: ItemData, assignee: str
    ) -> Dict[str, Any]:
        """Build frontmatter data dictionary from Jira data.

        Args:
            issue_key: Jira issue key
            data: Item data from Jira
            assignee: Assignee name

        Returns:
            Dictionary for YAML frontmatter
        """
        # Extract Jira URL from raw data if available
        jira_url = f"https://issues.redhat.com/browse/{issue_key}"

        frontmatter = {
            "issue_key": issue_key,
            "title": data.title,
            "status": data.status,
            "assignee": assignee,
            "jira_url": jira_url,
            "last_synced": datetime.utcnow().isoformat() + "Z",
        }

        # Add comments if present
        comments_data = data.raw_data.get("comments", {})
        all_comments = comments_data.get("comments", [])

        if all_comments:
            frontmatter["comments"] = []
            for comment in all_comments:
                author = comment.get("author", {})
                author_name = author.get("displayName", "Unknown")
                created = comment.get("created", "")
                body = comment.get("body", "").strip()

                # Convert Jira markup to markdown if possible
                body = self._convert_jira_to_markdown(body)

                # Normalize whitespace: strip trailing spaces from lines,
                # remove blank-only lines, and collapse multiple blank lines.
                # This prevents PyYAML from using literal block style which
                # creates odd formatting with random newlines.
                lines = []
                for line in body.split('\n'):
                    stripped = line.rstrip()
                    lines.append(stripped)
                body = '\n'.join(lines)
                # Collapse 2+ consecutive newlines to 2 (one blank line max)
                while '\n\n\n' in body:
                    body = body.replace('\n\n\n', '\n\n')
                body = body.strip()

                frontmatter["comments"].append({
                    "author": author_name,
                    "date": created,
                    "body": body,
                })

        return frontmatter

    def _update_existing_readme(
        self, content: str, data: ItemData, assignee: str
    ) -> str:
        """Update existing README.md content.

        Updates only the YAML frontmatter while preserving all manual content.

        Args:
            content: Current README content
            data: New data
            assignee: Assignee name

        Returns:
            Updated README content
        """
        existing_frontmatter, body = parse_frontmatter(content)

        # Get issue_key from frontmatter, or extract from heading
        issue_key = existing_frontmatter.get("issue_key")
        if not issue_key or issue_key == "UNKNOWN":
            match = re.search(r"^#\s+([A-Z]+-\d+):", body, re.MULTILINE)
            issue_key = match.group(1) if match else "UNKNOWN"

        new_frontmatter_data = self._build_frontmatter_data(issue_key, data, assignee)

        return build_frontmatter(new_frontmatter_data) + body

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
            # --wrap=none prevents pandoc from inserting line breaks in the output
            return pypandoc.convert_text(
                jira_text, "gfm", format="jira", extra_args=["--wrap=none"]
            )
        except Exception:
            # If conversion fails, return original text
            return jira_text

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

    def format_agenda_item(self, item: TrackedItem) -> str:
        """Format a Jira item for AGENDA.md in slim format.

        Args:
            item: The tracked item to format

        Returns:
            Markdown string with title, status, and link to README
        """
        issue_key = item.id

        # Find the README for this item
        readme_path = self._find_readme_path(item)
        if not readme_path or not readme_path.exists():
            return f"### [{issue_key}]\n**Status:** Unknown\n"

        content = readme_path.read_text()
        frontmatter, _ = parse_frontmatter(content)

        title = frontmatter.get("title", "")
        status = frontmatter.get("status", "Unknown")

        # Build relative path from base
        relative_path = str(readme_path.relative_to(self.base_path))

        # Build output
        lines = []
        if title:
            lines.append(f"### [{issue_key}] {title}")
        else:
            lines.append(f"### [{issue_key}]")
        lines.append(f"**Status:** {status}")
        lines.append(f"- [Details →]({relative_path})")
        lines.append("")

        return "\n".join(lines)

    def _find_readme_path(self, item: TrackedItem) -> Optional[Path]:
        """Find the README.md path for a tracked item.

        Args:
            item: The tracked item

        Returns:
            Path to README.md or None if not found
        """
        issue_key = item.id
        jira_dir = self.base_path / "tracking" / "areas" / "jira"

        if not jira_dir.exists():
            return None

        for item_dir in jira_dir.iterdir():
            if item_dir.is_dir() and item_dir.name.startswith(f"{issue_key}-"):
                readme = item_dir / "README.md"
                if readme.exists():
                    return readme

        return None

