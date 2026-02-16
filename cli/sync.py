"""Sync command for pulling data from external systems."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from ruamel.yaml import YAML

from cli.adapters.jira import JiraAdapter


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


def save_config(base_path: Path, items: List[Dict[str, Any]]) -> None:
    """Update areas.jira.items in gameplan.yaml while preserving all other content.

    Uses ruamel.yaml to perform a round-trip edit that preserves comments,
    formatting, emoji, and all non-items sections.

    Args:
        base_path: Base directory containing gameplan.yaml
        items: List of item dicts to write to areas.jira.items
    """
    config_file = base_path / "gameplan.yaml"

    ryaml = YAML()
    ryaml.preserve_quotes = True

    with open(config_file) as f:
        data = ryaml.load(f)

    data["areas"]["jira"]["items"] = items

    with open(config_file, "w") as f:
        ryaml.dump(data, f)


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


def sync_all(base_path: Path) -> None:
    """Sync all configured adapters.

    Args:
        base_path: Base directory for gameplan repository
    """
    # For now, only Jira is implemented
    sync_jira(base_path)


DEFAULT_POPULATE_JQL = "assignee = currentUser() AND statusCategory != Done"


def populate_jira_items(
    base_path: Path,
    jql: Optional[str] = None,
    env: Optional[str] = None,
) -> None:
    """Populate gameplan.yaml Jira items from a JQL search.

    Runs a JQL search via jirahhh, then merges results into
    areas.jira.items. Items tagged with source: populate that are no
    longer in the search results are removed. Manual items (without
    source: populate) are always preserved.

    Args:
        base_path: Base directory for gameplan repository
        jql: JQL query override (defaults to areas.jira.populate.search in config,
             then DEFAULT_POPULATE_JQL)
        env: Environment override (defaults to areas.jira.env in config)
    """
    config = load_config(base_path)

    jira_config = config.get("areas", {}).get("jira", {})
    if not jira_config:
        print("⚠️  No Jira configuration found in gameplan.yaml!")
        return

    populate_config = jira_config.get("populate", {})

    # Resolve JQL: CLI override > config > default
    search_jql = jql or populate_config.get("search") or DEFAULT_POPULATE_JQL

    # Resolve env: CLI override > config > default
    search_env = env or jira_config.get("env", "prod")

    # Create adapter and search
    adapter = JiraAdapter(jira_config, base_path)

    print(f"Searching Jira: {search_jql}")
    tracked_items = adapter.search_issues(jql=search_jql, env=search_env)
    print(f"Found {len(tracked_items)} issue(s)")

    # Build set of issue keys from search results
    search_keys = {item.id for item in tracked_items}

    # Separate existing items into manual and populate buckets
    existing_items = jira_config.get("items", []) or []
    manual_items = []
    for item in existing_items:
        if item.get("source") != "populate":
            manual_items.append(item)

    # Build set of manual issue keys so we don't duplicate them
    manual_keys = {item["issue"] for item in manual_items}

    # Build new populate items from search results (skip any that exist as manual)
    new_populate_items = []
    for item in tracked_items:
        if item.id not in manual_keys:
            new_populate_items.append(
                {
                    "issue": item.id,
                    "env": item.metadata.get("env", search_env),
                    "source": "populate",
                }
            )

    # Final items list: manual items first, then populate items
    final_items = manual_items + new_populate_items

    save_config(base_path, final_items)

    added = [i["issue"] for i in new_populate_items]
    if added:
        print("\nUpdated gameplan.yaml with:")
        for key in added:
            print(f"  - {key}")
    else:
        print("\nNo new items to add")

    print("\n✓ Populate complete!")
