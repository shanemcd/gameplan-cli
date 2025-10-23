"""Initialize a new gameplan repository.

This module provides the init command that sets up the directory structure
and configuration files for a new gameplan repository.
"""
from pathlib import Path
from typing import Optional

import yaml


def init_gameplan(target_dir: Optional[Path | str] = None, interactive: bool = False) -> Path:
    """Initialize a new gameplan repository.

    Args:
        target_dir: Directory to initialize (default: current directory)
        interactive: Enable interactive mode with prompts (not yet implemented)

    Returns:
        Path to the initialized directory

    Raises:
        FileExistsError: If gameplan.yaml already exists in target directory

    Example:
        >>> init_gameplan(Path("/path/to/gameplan"))
        Path('/path/to/gameplan')
    """
    # Determine target directory
    if target_dir is None:
        target_path = Path.cwd()
    else:
        target_path = Path(target_dir)

    # Check if already initialized
    config_file = target_path / "gameplan.yaml"
    if config_file.exists():
        raise FileExistsError(
            f"gameplan.yaml already exists at {target_path}. "
            "This directory is already initialized."
        )

    # Create directory structure
    _create_directory_structure(target_path)

    # Create gameplan.yaml
    _create_gameplan_yaml(config_file)

    return target_path


def _create_directory_structure(target_path: Path) -> None:
    """Create the tracking directory structure.

    Args:
        target_path: Base directory for the gameplan repository
    """
    # Create tracking/areas/jira/ and archive
    jira_dir = target_path / "tracking" / "areas" / "jira"
    jira_dir.mkdir(parents=True, exist_ok=True)

    archive_dir = jira_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)


def _create_gameplan_yaml(config_file: Path) -> None:
    """Create the gameplan.yaml configuration file.

    Args:
        config_file: Path to the gameplan.yaml file to create
    """
    template = """\
# Gameplan Configuration
# Track work items and generate daily AGENDA.md

# Areas: Define what you want to track
areas:
  jira:
    # Add Jira issues you're actively working on
    items: []
    # Example:
    # items:
    #   - issue: PROJ-123
    #     env: prod
    #   - issue: PROJ-456
    #     env: staging
    #
    # Optional: Specify custom jirahhh binary path
    # binary_path: /usr/local/bin/jirahhh

# Agenda: Configure your daily AGENDA.md file
agenda:
  sections:
    # Manual sections: You edit the content directly in AGENDA.md
    - name: Focus & Priorities
      emoji: 🎯
      description: What's urgent/important today

    # Command-driven sections: Auto-populated by running a command
    # Uncomment to enable tracked items section:
    # - name: Tracked Items
    #   emoji: 🔄
    #   command: gameplan agenda tracked-items
    #   description: Current status of tracked items

    # You can add custom command-driven sections:
    # - name: Calendar
    #   emoji: 📅
    #   command: your-calendar-command
    #   description: Today's meetings
    #
    # - name: Pull Requests
    #   emoji: 📝
    #   command: your-pr-command
    #   description: PRs awaiting review

    # Manual section for notes
    - name: Notes
      emoji: 📔
      description: Thoughts and observations
"""

    with open(config_file, "w") as f:
        f.write(template)
