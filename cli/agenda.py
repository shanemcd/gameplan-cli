"""Manage daily agenda with configurable sections.

The agenda system provides a living AGENDA.md file that combines:
- Manual sections: User-maintained content
- Command-driven sections: Auto-populated by running shell commands
"""
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml


def init_agenda(base_path: Optional[Path] = None) -> Path:
    """Initialize AGENDA.md from gameplan.yaml configuration.

    Args:
        base_path: Base directory (default: current directory)

    Returns:
        Path to created AGENDA.md

    Raises:
        FileNotFoundError: If gameplan.yaml not found
        FileExistsError: If AGENDA.md already exists
        ValueError: If config missing 'agenda' section
    """
    if base_path is None:
        base_path = Path.cwd()

    # Load config
    config_file = base_path / "gameplan.yaml"
    if not config_file.exists():
        raise FileNotFoundError(
            f"gameplan.yaml not found at {base_path}. "
            "Run 'gameplan init' first."
        )

    with open(config_file) as f:
        config = yaml.safe_load(f)

    if "agenda" not in config:
        raise ValueError(
            "No 'agenda' section in gameplan.yaml. "
            "Add an 'agenda' section with 'sections' list."
        )

    # Check if AGENDA.md already exists
    agenda_file = base_path / "AGENDA.md"
    if agenda_file.exists():
        raise FileExistsError(
            f"AGENDA.md already exists at {base_path}. "
            "Use 'gameplan agenda refresh' to update it."
        )

    # Generate AGENDA.md content
    content = _generate_agenda_content(config["agenda"])

    # Write AGENDA.md
    agenda_file.write_text(content)

    return agenda_file


def view_agenda(base_path: Optional[Path] = None) -> str:
    """View current AGENDA.md content.

    Args:
        base_path: Base directory (default: current directory)

    Returns:
        AGENDA.md content as string

    Raises:
        FileNotFoundError: If AGENDA.md not found
    """
    if base_path is None:
        base_path = Path.cwd()

    agenda_file = base_path / "AGENDA.md"
    if not agenda_file.exists():
        raise FileNotFoundError(
            f"AGENDA.md not found at {base_path}. "
            "Run 'gameplan agenda init' first."
        )

    return agenda_file.read_text()


def refresh_agenda(base_path: Optional[Path] = None) -> Path:
    """Refresh command-driven sections in AGENDA.md.

    Runs configured commands and updates their sections while preserving
    all manual content.

    Args:
        base_path: Base directory (default: current directory)

    Returns:
        Path to updated AGENDA.md

    Raises:
        FileNotFoundError: If gameplan.yaml or AGENDA.md not found
    """
    if base_path is None:
        base_path = Path.cwd()

    # Load config
    config_file = base_path / "gameplan.yaml"
    if not config_file.exists():
        raise FileNotFoundError(
            f"gameplan.yaml not found at {base_path}. "
            "Run 'gameplan init' first."
        )

    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Load current AGENDA.md
    agenda_file = base_path / "AGENDA.md"
    if not agenda_file.exists():
        raise FileNotFoundError(
            f"AGENDA.md not found at {base_path}. "
            "Run 'gameplan agenda init' first."
        )

    content = agenda_file.read_text()

    # Update command-driven sections
    sections = config.get("agenda", {}).get("sections", [])
    for section in sections:
        if "command" in section:
            content = _update_command_section(content, section)

    # Write updated content
    agenda_file.write_text(content)

    return agenda_file


def _generate_agenda_content(agenda_config: Dict[str, Any]) -> str:
    """Generate AGENDA.md content from configuration.

    Args:
        agenda_config: The 'agenda' section from gameplan.yaml

    Returns:
        Formatted AGENDA.md content
    """
    # Start with date header
    today = datetime.now().strftime("%A, %B %d, %Y")
    lines = [f"# Agenda - {today}", ""]

    # Add each section
    sections = agenda_config.get("sections", [])
    for section in sections:
        lines.extend(_generate_section(section))
        lines.append("")  # Blank line between sections

    return "\n".join(lines)


def _generate_section(section: Dict[str, Any]) -> List[str]:
    """Generate markdown for a single section.

    Args:
        section: Section configuration dict

    Returns:
        List of markdown lines for the section
    """
    name = section["name"]
    emoji = section.get("emoji", "")

    # Create section header
    if emoji:
        header = f"## {emoji} {name}"
    else:
        header = f"## {name}"

    lines = [header]

    # Add placeholder content
    if "command" in section:
        # Command-driven section: show command to be run
        lines.append(f"[Run: {section['command']}]")
    else:
        # Manual section: show description
        description = section.get("description", "")
        lines.append(f"[{description}]")

    return lines


def _update_command_section(content: str, section: Dict[str, Any]) -> str:
    """Update a command-driven section with command output.

    Args:
        content: Current AGENDA.md content
        section: Section configuration with 'command' field

    Returns:
        Updated AGENDA.md content
    """
    name = section["name"]
    emoji = section.get("emoji", "")
    command = section["command"]

    # Build section header pattern
    if emoji:
        header_pattern = re.escape(f"## {emoji} {name}")
    else:
        header_pattern = re.escape(f"## {name}")

    # Find the section and replace its content
    # Pattern: ## Header\n[Run: command] OR ## Header\n(existing content)
    # Replace with: ## Header\n(command output)

    # Run the command
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
        else:
            output = "[Error running command: Command failed]"
    except subprocess.TimeoutExpired:
        output = "[Error running command: Timeout]"
    except Exception as e:
        output = f"[Error running command: {str(e)}]"

    # Find section and replace content between this header and next header (or end)
    # Pattern to match: ## Header\n(anything until next ## or end)
    pattern = rf"({header_pattern})\n.*?(?=\n##|\n$|$)"

    replacement = rf"\1\n{output}"

    # Use re.DOTALL to make . match newlines
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)

    return updated


def format_tracked_items(base_path: Optional[Path] = None) -> str:
    """Format tracked items from gameplan.yaml.

    Simple output of tracked Jira items for use in AGENDA.md.

    Args:
        base_path: Base directory (default: current directory)

    Returns:
        Markdown-formatted tracked items
    """
    if base_path is None:
        base_path = Path.cwd()

    config_file = base_path / "gameplan.yaml"
    if not config_file.exists():
        return "_No gameplan.yaml found_"

    with open(config_file) as f:
        config = yaml.safe_load(f)

    areas = config.get("areas", {})
    items_md = []

    # Jira items
    jira_area = areas.get("jira", {})
    jira_items = jira_area.get("items", [])

    for item in jira_items:
        issue_key = item.get("issue")
        if not issue_key:
            continue

        items_md.append(f"- {issue_key}")

    if not items_md:
        return "_No tracked items_"

    return "\n".join(items_md)
