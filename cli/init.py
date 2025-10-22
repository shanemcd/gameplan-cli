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
    config = {
        "areas": {
            "jira": {
                "items": [],
            },
        },
        "agenda": {
            "sections": [
                {
                    "name": "Focus & Priorities",
                    "emoji": "🎯",
                    "description": "What's urgent/important today",
                },
                {
                    "name": "Notes",
                    "emoji": "📔",
                    "description": "Thoughts and observations",
                },
            ],
        },
    }

    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
