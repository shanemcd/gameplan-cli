"""Sync command for pulling data from external systems."""
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from cli.adapters.jira import JiraAdapter
from cli.adapters.misc import MiscAdapter


def load_config(base_path: Path) -> Dict[str, Any]:
    """Load gameplan.yaml configuration.

    Args:
        base_path: Base directory containing gameplan.yaml

    Returns:
        Configuration dictionary
    """
    config_file = base_path / "gameplan.yaml"

    if not config_file.exists():
        print(f"⚠️  Configuration not found: {config_file}", file=sys.stderr)
        return {}

    with open(config_file) as f:
        return yaml.safe_load(f)


def sync_jira(base_path: Path) -> None:
    """Sync Jira issues and update README files.

    Args:
        base_path: Base directory for gameplan repository
    """
    print("Loading tracked Jira issues from gameplan.yaml...")
    config = load_config(base_path)

    # Check if Jira section exists
    jira_config = config.get("areas", {}).get("jira", {})
    if not jira_config:
        print("⚠️  No Jira configuration found in gameplan.yaml!")
        return

    # Create adapter
    adapter = JiraAdapter(jira_config, base_path)

    # Load tracked items
    tracked_items = adapter.load_config(jira_config)

    if not tracked_items:
        print("⚠️  No tracked Jira issues found in gameplan.yaml!")
        return

    print(f"Found {len(tracked_items)} tracked Jira issue(s)")
    print("\nChecking Jira issues...")

    for item in tracked_items:
        print(f"  Checking {item.id}...")

        # Get the readme path first to load previous metadata
        readme_path = adapter.get_storage_path(item, title=None)

        # Fetch data from Jira
        data = adapter.fetch_item_data(item)

        if not data.title:
            print("    ⚠️  Could not fetch data")
            continue

        # Extract assignee from raw data
        assignee = "Unassigned"
        if "fields" in data.raw_data:
            assignee_obj = data.raw_data["fields"].get("assignee")
            if assignee_obj and isinstance(assignee_obj, dict):
                assignee = assignee_obj.get("displayName", "Unassigned")
        else:
            assignee = data.raw_data.get("assignee", "Unassigned")

        # Detect if issue has been updated
        has_changes = adapter.detect_changes(readme_path, data)

        # Print status
        if has_changes:
            print(f"    ✓ Status: {data.status} | Assignee: {assignee}")
            print("    🔔 Issue has been updated - review README.md for details")
        else:
            print(f"    ✓ Status: {data.status} | Assignee: {assignee}")

        # Update the README.md with new status (pass title for directory naming)
        readme_path = adapter.get_storage_path(item, title=data.title)
        adapter.update_readme(readme_path, data, item)

        # Save metadata for next sync
        adapter.save_metadata(readme_path, data)

    print("\n✓ Jira sync complete!")


def sync_misc(base_path: Path) -> None:
    """Sync misc items and ensure README files exist.

    Args:
        base_path: Base directory for gameplan repository
    """
    config = load_config(base_path)

    misc_config = config.get("areas", {}).get("misc", {})
    if not misc_config:
        return

    adapter = MiscAdapter(misc_config, base_path)
    tracked_items = adapter.load_config(misc_config)

    if not tracked_items:
        return

    print(f"\nFound {len(tracked_items)} misc item(s)")
    print("Checking misc items...")

    for item in tracked_items:
        print(f"  Checking {item.id}...")

        data = adapter.fetch_item_data(item)
        readme_path = adapter.get_storage_path(item, title=data.title)

        if readme_path.exists():
            print(f"    ✓ {data.title}")
        else:
            print(f"    + Creating {data.title}")
            adapter.update_readme(readme_path, data, item)

    print("\n✓ Misc sync complete!")


def sync_all(base_path: Path) -> None:
    """Sync all configured adapters.

    Args:
        base_path: Base directory for gameplan repository
    """
    sync_jira(base_path)
    sync_misc(base_path)
