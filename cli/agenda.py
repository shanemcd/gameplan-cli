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

    # Update date header to today
    content = _update_date_header(content)

    # Get configured sections
    sections = config.get("agenda", {}).get("sections", [])

    # Reorder sections to match config order (preserving content)
    content = _reorder_sections(content, sections)

    # Update command-driven sections
    for section in sections:
        if "command" in section:
            content = _update_command_section(content, section, base_path)

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


def _update_date_header(content: str) -> str:
    """Update the date header in AGENDA.md to today's date.

    Args:
        content: Current AGENDA.md content

    Returns:
        Updated content with today's date
    """
    today = datetime.now().strftime("%A, %B %d, %Y")
    new_header = f"# Agenda - {today}"

    # Pattern to match: # Agenda - [any date]
    pattern = r"^# Agenda - .*$"

    updated = re.sub(pattern, new_header, content, count=1, flags=re.MULTILINE)

    return updated


def _reorder_sections(content: str, sections: List[Dict[str, Any]]) -> str:
    """Reorder sections to match config order, preserving all content.

    Extracts all sections from AGENDA.md, then reassembles them in the
    order specified in gameplan.yaml. Missing sections are created with
    placeholder content.

    Args:
        content: Current AGENDA.md content
        sections: List of section configurations from gameplan.yaml

    Returns:
        Updated content with sections in config order
    """
    # Extract header (everything before first ## section)
    first_section_match = re.search(r"^## ", content, re.MULTILINE)
    if not first_section_match:
        # No sections found, just return content as-is
        return content

    header = content[:first_section_match.start()]

    # Extract all existing sections with their content
    # Pattern: ## header\n(content until next ## or end)
    section_pattern = r"(## [^\n]+)\n(.*?)(?=\n## |\Z)"
    existing_sections = {}

    for match in re.finditer(section_pattern, content, re.DOTALL):
        section_header = match.group(1)
        section_content = match.group(2).rstrip()
        existing_sections[section_header] = section_content

    # Build new content in config order
    new_sections = []

    for section in sections:
        name = section["name"]
        emoji = section.get("emoji", "")

        if emoji:
            expected_header = f"## {emoji} {name}"
        else:
            expected_header = f"## {name}"

        if expected_header in existing_sections:
            # Use existing content
            new_sections.append(f"{expected_header}\n{existing_sections[expected_header]}")
        else:
            # Create new section with placeholder
            section_lines = _generate_section(section)
            new_sections.append("\n".join(section_lines))

    # Reassemble: header + sections
    result = header + "\n".join(new_sections)

    # Ensure trailing newline
    if not result.endswith("\n"):
        result += "\n"

    return result


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


def _update_command_section(content: str, section: Dict[str, Any], base_path: Path) -> str:
    """Update a command-driven section with command output.

    Args:
        content: Current AGENDA.md content
        section: Section configuration with 'command' field
        base_path: Base directory to run command from

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

    # Run the command from the base directory
    try:
        import os
        env = os.environ.copy()
        env["GAMEPLAN_BASE_DIR"] = str(base_path)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(base_path),
            env=env,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
        else:
            # Include stderr in error for debugging
            stderr = result.stderr.strip() if result.stderr else ""
            if stderr:
                output = f"[Error running command: Command failed]\n{stderr}"
            else:
                output = "[Error running command: Command failed]"
    except subprocess.TimeoutExpired:
        output = "[Error running command: Timeout]"
    except Exception as e:
        output = f"[Error running command: {str(e)}]"

    # Find section and replace content between this header and next header (or end)
    # Pattern to match: ## Header\n(anything until next ## or end)
    # Note: Use '\n## ' (with space) to match only h2 headers, not h3/h4/etc (###, ####)
    pattern = rf"({header_pattern})\n.*?(?=\n## |\n$|$)"

    replacement = rf"\1\n{output}"

    # Use re.DOTALL to make . match newlines
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)

    return updated


def format_tracked_items(base_path: Optional[Path] = None) -> str:
    """Format tracked items with current status and preserved Actions/Notes.

    Reads status/title from tracking files created by sync, and preserves
    Actions/Notes subsections from existing AGENDA.md.

    Args:
        base_path: Base directory (default: current directory)

    Returns:
        Markdown-formatted tracked items with status, Actions, and Notes
    """
    if base_path is None:
        base_path = Path.cwd()

    config_file = base_path / "gameplan.yaml"
    if not config_file.exists():
        return "_No gameplan.yaml found_"

    with open(config_file) as f:
        config = yaml.safe_load(f)

    # Read current AGENDA.md to extract existing Actions/Notes
    agenda_file = base_path / "AGENDA.md"
    existing_subsections = {}
    if agenda_file.exists():
        existing_subsections = _extract_tracked_item_subsections(agenda_file.read_text())

    areas = config.get("areas", {})
    items_md = []

    # Jira items
    jira_area = areas.get("jira", {})
    jira_items = jira_area.get("items", [])

    for item in jira_items:
        issue_key = item.get("issue")
        if not issue_key:
            continue

        # Read status from tracking file
        status_info = _read_jira_status(base_path, issue_key)

        # Generate item markdown
        item_md = _format_single_tracked_item(
            issue_key,
            status_info,
            existing_subsections.get(issue_key, {})
        )
        items_md.append(item_md)

    if not items_md:
        return "_No tracked items_"

    return "\n".join(items_md)


def _extract_tracked_item_subsections(content: str) -> Dict[str, Dict[str, str]]:
    """Extract Actions and Notes subsections for each tracked item from AGENDA.md.

    Args:
        content: Current AGENDA.md content

    Returns:
        Dict mapping issue keys to their Actions/Notes content
    """
    result = {}

    # Pattern to match tracked items: ### [ISSUE-KEY] Title
    item_pattern = r"###\s+\[([A-Z]+-\d+)\][^\n]*\n"

    # Find all tracked items
    matches = list(re.finditer(item_pattern, content))

    for i, match in enumerate(matches):
        issue_key = match.group(1)

        # Extract content from this heading to the next ### or ## heading (or end)
        start = match.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # Look for next ## heading
            next_section = re.search(r"\n##\s", content[start:])
            end = start + next_section.start() if next_section else len(content)

        item_content = content[start:end]

        # Extract Actions subsection
        actions_match = re.search(
            r"####\s+Actions\s*\n(.*?)(?=####\s+Notes|###\s+\[|##\s+|$)",
            item_content,
            re.DOTALL
        )
        actions = actions_match.group(1).strip() if actions_match else ""

        # Extract Notes subsection
        notes_match = re.search(
            r"####\s+Notes\s*\n(.*?)(?=###\s+\[|##\s+|$)",
            item_content,
            re.DOTALL
        )
        notes = notes_match.group(1).strip() if notes_match else ""

        result[issue_key] = {
            "actions": actions,
            "notes": notes
        }

    return result


def _read_jira_status(base_path: Path, issue_key: str) -> Dict[str, str]:
    """Read status information for a Jira issue from tracking files.

    Args:
        base_path: Base directory
        issue_key: Jira issue key

    Returns:
        Dict with 'status', 'title', 'assignee' keys
    """
    # Find the tracking directory for this issue
    jira_dir = base_path / "tracking" / "areas" / "jira"
    if not jira_dir.exists():
        return {"status": "Unknown", "title": "", "assignee": ""}

    # Find directory matching this issue key
    for item_dir in jira_dir.iterdir():
        if item_dir.is_dir() and item_dir.name.startswith(f"{issue_key}-"):
            readme = item_dir / "README.md"
            if readme.exists():
                content = readme.read_text()

                # Extract title from # heading
                title_match = re.search(r"^#\s+[A-Z]+-\d+:\s+(.+)$", content, re.MULTILINE)
                title = title_match.group(1) if title_match else ""

                # Extract status
                status_match = re.search(r"\*\*Status\*\*:\s+(.+)$", content, re.MULTILINE)
                status = status_match.group(1) if status_match else "Unknown"

                # Extract assignee
                assignee_match = re.search(r"\*\*Assignee\*\*:\s+(.+)$", content, re.MULTILINE)
                assignee = assignee_match.group(1) if assignee_match else ""

                return {"status": status, "title": title, "assignee": assignee}

    return {"status": "Unknown", "title": "", "assignee": ""}


def _format_single_tracked_item(
    issue_key: str,
    status_info: Dict[str, str],
    subsections: Dict[str, str]
) -> str:
    """Format a single tracked item with status and subsections.

    Args:
        issue_key: Jira issue key
        status_info: Dict with status, title, assignee
        subsections: Dict with actions and notes content

    Returns:
        Markdown for the tracked item
    """
    status = status_info.get("status", "Unknown")
    title = status_info.get("title", "")

    # Map status to emoji
    status_emoji = {
        "In Progress": "🟢",
        "Refinement": "❓",
        "To Do": "⚪",
        "Done": "✅",
        "Blocked": "🔴",
    }.get(status, "⚪")

    lines = []

    # Heading
    if title:
        lines.append(f"### [{issue_key}] {title}")
    else:
        lines.append(f"### [{issue_key}]")

    lines.append("")

    # Status line (no URL since we don't know the Jira base URL)
    lines.append(f"**{issue_key}** {status_emoji} {status}")
    lines.append("")

    # Actions subsection
    lines.append("#### Actions")
    lines.append("")
    if subsections.get("actions"):
        lines.append(subsections["actions"])
    else:
        lines.append("- Add your next actions here")
    lines.append("")

    # Notes subsection
    lines.append("#### Notes")
    lines.append("")
    if subsections.get("notes"):
        lines.append(subsections["notes"])
    else:
        lines.append("[Add context, observations, or reminders here]")
    lines.append("")

    return "\n".join(lines)
