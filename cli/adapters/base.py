"""Base adapter interface for tracking systems.

This module defines the contract that all tracking system adapters must implement.
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def sanitize_title_for_path(title: str, max_length: int = 50) -> str:
    """Sanitize a title for use in filesystem paths.

    Args:
        title: The title to sanitize
        max_length: Maximum length for the sanitized title

    Returns:
        Sanitized title safe for use in filesystem paths

    Example:
        >>> sanitize_title_for_path("Fix: Bug in API (Critical!)")
        "fix-bug-in-api-critical"
    """
    # Convert to lowercase
    title = title.lower()

    # Replace spaces and special chars with hyphens
    title = re.sub(r"[^\w\s-]", "", title)  # Remove special chars
    title = re.sub(r"[-\s]+", "-", title)  # Replace spaces/multiple hyphens with single hyphen

    # Remove leading/trailing hyphens
    title = title.strip("-")

    # Truncate to max length at word boundary if possible
    if len(title) > max_length:
        title = title[:max_length]
        # Try to break at last hyphen
        if "-" in title:
            title = title.rsplit("-", 1)[0]
        title = title.rstrip("-")

    return title


@dataclass
class TrackedItem:
    """Represents a tracked work item from any system.

    Attributes:
        id: Unique identifier for the item (e.g., "PROJ-123", "owner/repo#123")
        adapter: Name of the adapter that manages this item
        metadata: Adapter-specific metadata (owner, repo, env, etc.)
    """

    id: str
    adapter: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ItemData:
    """Data fetched from a tracking system for an item.

    Attributes:
        title: Item title/summary
        status: Current status (Open, In Progress, Done, etc.)
        updates: List of updates (comments, status changes, etc.)
        raw_data: Full raw response from the API for adapter-specific processing
    """

    title: str
    status: str
    updates: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)


class Adapter(ABC):
    """Abstract base class for tracking system adapters.

    All adapters must implement this interface to work with the gameplan CLI.

    Example:
        class JiraAdapter(Adapter):
            def get_adapter_name(self) -> str:
                return "jira"

            def load_config(self, config: Dict[str, Any]) -> List[TrackedItem]:
                # Parse Jira-specific config
                pass

            # ... implement other abstract methods
    """

    def __init__(self, config: Dict[str, Any], base_path: Path):
        """Initialize the adapter.

        Args:
            config: Adapter-specific configuration from gameplan.yaml
            base_path: Base path for storing work files
        """
        self.config = config
        self.base_path = base_path

    def _get_binary_path(self, binary_name: str) -> str:
        """Get the binary path from config or default.

        Args:
            binary_name: Default binary name to use if no custom path configured

        Returns:
            Path to binary, either from config or the default binary name

        Example:
            For an adapter that uses "gh" CLI:
            - If config has binary_path: "/usr/local/bin/gh", returns that
            - Otherwise returns "gh" (relies on PATH lookup)

        AIA: Primarily AI, Stylistic edits, Content edits, New content, Human-initiated, Reviewed, Claude Code [Sonnet 4] v1.0
        Vibe-Coder: Andrew Potozniak <tyraziel@gmail.com>
        """
        return self.config.get("binary_path", binary_name)

    @abstractmethod
    def get_adapter_name(self) -> str:
        """Return the adapter name (e.g., 'jira', 'github').

        Returns:
            Lowercase adapter name
        """
        pass

    @abstractmethod
    def load_config(self, config: Dict[str, Any]) -> List[TrackedItem]:
        """Parse configuration and return list of tracked items.

        Args:
            config: Adapter-specific configuration section

        Returns:
            List of TrackedItem objects to track

        Example:
            Jira config:
            {
                'items': [
                    {'issue': 'PROJ-123', 'env': 'prod'}
                ]
            }

            Returns:
            [
                TrackedItem(
                    id='PROJ-123',
                    adapter='jira',
                    metadata={'issue': 'PROJ-123', 'env': 'prod'}
                )
            ]
        """
        pass

    @abstractmethod
    def fetch_item_data(self, item: TrackedItem, since: Optional[str] = None) -> ItemData:
        """Fetch current data for a tracked item.

        Args:
            item: The item to fetch data for
            since: Optional ISO timestamp - only fetch updates after this time

        Returns:
            ItemData with current state and updates

        Example:
            For Jira issue, fetch:
            - Current title and status
            - Assignee information
            - Recent comments or updates
        """
        pass

    @abstractmethod
    def get_storage_path(self, item: TrackedItem, title: Optional[str] = None) -> Path:
        """Get the README.md path for storing this item's data.

        Args:
            item: The item to get path for
            title: Optional title for the item (used for directory naming)

        Returns:
            Absolute path to the item's README.md file

        Notes:
            If title is provided, the directory name should include a sanitized
            version of the title for human readability.

        Example:
            For PROJ-123 with title "Fix API Bug":
            Path('/path/to/gameplan/tracking/areas/jira/PROJ-123-fix-api-bug/README.md')
        """
        pass

    @abstractmethod
    def update_readme(self, readme_path: Path, data: ItemData, item: TrackedItem):
        """Update the README file with new data.

        This should update auto-managed sections while preserving manual content.

        Args:
            readme_path: Path to the README.md file
            data: New data to write
            item: The tracked item

        Example:
            Update status and assignee fields
            Preserve all manual content (Overview, Notes, etc.)
        """
        pass
