"""Manage daily agenda with configurable sections.

The agenda system provides a living AGENDA.md file that combines:
- Manual sections: User-maintained content
- Command-driven sections: Auto-populated by running shell commands
- Logbook: Automatic archival of completed tasks to LOGBOOK.md files
"""
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

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
    all manual content. Also processes the logbook by moving completed
    tasks (marked with ✅ YYYY-MM-DD) to each item's LOGBOOK.md file.

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

    # Process logbook FIRST (before other updates)
    # This extracts completed tasks, logs them, and removes from agenda
    process_logbook(base_path)

    # Re-read content after logbook processing
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


# =============================================================================
# Logbook Functions - Automatic archival of completed tasks
# =============================================================================


def extract_completed_tasks(content: str) -> Dict[str, Dict[str, List[str]]]:
    """Extract ALL completed tasks from AGENDA.md content with any date.

    Scans the Actions subsections of tracked items for completed tasks
    (lines starting with '- [x]') that have a completion date (✅ YYYY-MM-DD).
    Also extracts completed tasks from outside tracked items into "Other".

    Args:
        content: AGENDA.md content

    Returns:
        Dict mapping item titles (or "Other") to dict of dates to tasks:
        {
            "[ANSTRAT-1567] Title": {
                "2025-10-13": ["- [x] Task 1 ✅ 2025-10-13"],
            },
            "Other": {
                "2025-10-13": ["- [x] Misc task ✅ 2025-10-13"],
            }
        }
    """
    completed_tasks: Dict[str, Dict[str, List[str]]] = {}
    current_item_title: Optional[str] = None
    in_actions_section = False
    in_tracked_items_section = False

    # Pattern to match completion date: ✅ YYYY-MM-DD
    date_pattern = re.compile(r'✅ (\d{4}-\d{2}-\d{2})')

    for line in content.split('\n'):
        # Check for Tracked Items section (## 🔄 Tracked Items or ## Tracked Items)
        if line.startswith('## ') and 'Tracked Items' in line:
            in_tracked_items_section = True
            current_item_title = None
            in_actions_section = False

        # Check for other h2 sections (end of Tracked Items)
        elif line.startswith('## ') and 'Tracked Items' not in line:
            in_tracked_items_section = False
            current_item_title = None
            in_actions_section = False

        # Check for item heading (### [...]) within Tracked Items
        elif in_tracked_items_section and line.startswith('### ['):
            current_item_title = line.replace('### ', '')
            in_actions_section = False

        # Check for Actions subsection
        elif line.strip() == '#### Actions':
            in_actions_section = True

        # Check for any other h4 subsection (end of Actions)
        elif line.startswith('#### ') and line.strip() != '#### Actions':
            in_actions_section = False

        # Check for completed tasks
        elif line.startswith('- [x]'):
            match = date_pattern.search(line)
            if match:
                task_date = match.group(1)

                # Determine which category this task belongs to
                if in_tracked_items_section and current_item_title and in_actions_section:
                    category = current_item_title
                else:
                    category = "Other"

                if category not in completed_tasks:
                    completed_tasks[category] = {}

                if task_date not in completed_tasks[category]:
                    completed_tasks[category][task_date] = []

                completed_tasks[category][task_date].append(line)

    return completed_tasks


def _extract_issue_key_from_title(item_title: str) -> Optional[str]:
    """Extract issue key from item title like '[ANSTRAT-1567] Title'.

    Args:
        item_title: Item title from AGENDA.md

    Returns:
        Issue key (e.g., 'ANSTRAT-1567') or None if not found
    """
    match = re.match(r'\[([A-Z]+-\d+)\]', item_title)
    return match.group(1) if match else None


def _get_week_start(date_str: str) -> str:
    """Get the Monday of the week containing the given date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Monday's date in YYYY-MM-DD format
    """
    from datetime import datetime as dt, timedelta
    date = dt.strptime(date_str, "%Y-%m-%d")
    # Monday is weekday 0
    monday = date - timedelta(days=date.weekday())
    return monday.strftime("%Y-%m-%d")


def _format_issue_heading(item_title: str) -> str:
    """Format item title as a logbook heading.

    Args:
        item_title: Item title like '[ANSTRAT-1567] Some Title'

    Returns:
        Formatted heading like 'ANSTRAT-1567 (Some Title)'
    """
    if item_title == "Other":
        return "Other"

    issue_key = _extract_issue_key_from_title(item_title)
    if issue_key:
        # Extract title part after the key (handle with or without trailing space)
        title_part = item_title.replace(f"[{issue_key}]", "").strip()
        if title_part:
            return f"{issue_key} ({title_part})"
        return issue_key
    return item_title


def append_to_logbook(
    completed_tasks: Dict[str, Dict[str, List[str]]],
    base_path: Path
) -> Tuple[int, int]:
    """Append completed tasks to top-level LOGBOOK.md.

    Creates or updates LOGBOOK.md at the repository root with weekly sections
    and initiative sub-headings. Tasks are organized by week (newest first),
    then by initiative.

    Structure:
        # Logbook

        ## Week of 2026-01-06

        ### ANSTRAT-598 (MRBC)

        - [x] Task 1 ✅ 2026-01-08

        ### Other

        - [x] Misc task ✅ 2026-01-07

    Args:
        completed_tasks: Dict mapping item titles to dict of dates to tasks
        base_path: Base directory

    Returns:
        Tuple of (total_tasks_logged, initiatives_logged)
    """
    if not completed_tasks:
        return (0, 0)

    logbook_file = base_path / "LOGBOOK.md"

    # Read existing logbook if it exists
    if logbook_file.exists():
        existing_content = logbook_file.read_text()
    else:
        existing_content = "# Logbook\n"

    # Parse existing logbook structure
    existing_entries = _parse_logbook(existing_content)

    # Merge new tasks into existing structure
    logged_count = 0
    initiatives_logged = set()

    for item_title, date_tasks in completed_tasks.items():
        issue_heading = _format_issue_heading(item_title)

        for task_date, tasks in date_tasks.items():
            week_start = _get_week_start(task_date)

            if week_start not in existing_entries:
                existing_entries[week_start] = {}

            if issue_heading not in existing_entries[week_start]:
                existing_entries[week_start][issue_heading] = []

            # Add tasks (avoiding duplicates)
            for task in tasks:
                if task not in existing_entries[week_start][issue_heading]:
                    existing_entries[week_start][issue_heading].append(task)
                    logged_count += 1

            initiatives_logged.add(issue_heading)

    # Rebuild logbook content
    new_content = _build_logbook_content(existing_entries)

    # Write back
    logbook_file.write_text(new_content)

    return (logged_count, len(initiatives_logged))


def _parse_logbook(content: str) -> Dict[str, Dict[str, List[str]]]:
    """Parse existing LOGBOOK.md into structured data.

    Args:
        content: LOGBOOK.md content

    Returns:
        Dict mapping week_start -> initiative -> list of tasks
    """
    entries: Dict[str, Dict[str, List[str]]] = {}
    current_week: Optional[str] = None
    current_initiative: Optional[str] = None

    for line in content.split('\n'):
        # Week heading: ## Week of YYYY-MM-DD
        if line.startswith('## Week of '):
            week_date = line.replace('## Week of ', '').strip()
            current_week = week_date
            current_initiative = None
            if current_week not in entries:
                entries[current_week] = {}

        # Initiative heading: ### ISSUE-KEY (Title) or ### Other
        elif line.startswith('### ') and current_week:
            current_initiative = line.replace('### ', '').strip()
            if current_initiative not in entries[current_week]:
                entries[current_week][current_initiative] = []

        # Task line
        elif line.startswith('- [x]') and current_week and current_initiative:
            entries[current_week][current_initiative].append(line)

    return entries


def _build_logbook_content(entries: Dict[str, Dict[str, List[str]]]) -> str:
    """Build LOGBOOK.md content from structured data.

    Args:
        entries: Dict mapping week_start -> initiative -> list of tasks

    Returns:
        Formatted LOGBOOK.md content
    """
    lines = ["# Logbook", ""]

    # Sort weeks in reverse chronological order
    for week_start in sorted(entries.keys(), reverse=True):
        initiatives = entries[week_start]
        if not initiatives:
            continue

        lines.append(f"## Week of {week_start}")
        lines.append("")

        # Sort initiatives: tracked items first (alphabetically), "Other" last
        sorted_initiatives = sorted(
            initiatives.keys(),
            key=lambda x: (x == "Other", x)
        )

        for initiative in sorted_initiatives:
            tasks = initiatives[initiative]
            if not tasks:
                continue

            lines.append(f"### {initiative}")
            lines.append("")

            # Sort tasks by date (newest first within the week)
            date_pattern = re.compile(r'✅ (\d{4}-\d{2}-\d{2})')
            sorted_tasks = sorted(
                tasks,
                key=lambda t: date_pattern.search(t).group(1) if date_pattern.search(t) else "",
                reverse=True
            )

            for task in sorted_tasks:
                lines.append(task)

            lines.append("")

    return '\n'.join(lines)


def remove_completed_tasks_from_content(
    content: str,
    completed_tasks: Dict[str, Dict[str, List[str]]]
) -> str:
    """Remove completed tasks from AGENDA.md content after they've been logged.

    Args:
        content: Current AGENDA.md content
        completed_tasks: Dict mapping item titles to dict of dates to tasks

    Returns:
        Updated content with completed tasks removed
    """
    if not completed_tasks:
        return content

    # Build set of task lines to remove (for efficient lookup)
    tasks_to_remove = set()
    for date_tasks in completed_tasks.values():
        for tasks in date_tasks.values():
            for task in tasks:
                tasks_to_remove.add(task)

    # Filter out completed tasks
    lines = content.split('\n')
    filtered_lines = []

    for line in lines:
        # Keep line if it's not a completed task to remove
        if not (line.startswith('- [x]') and line in tasks_to_remove):
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def process_logbook(base_path: Path) -> Tuple[int, int]:
    """Process completed tasks: extract, log to LOGBOOK.md, remove from AGENDA.md.

    This is the main entry point for logbook functionality. It:
    1. Reads AGENDA.md
    2. Extracts completed tasks with dates (from tracked items + other sections)
    3. Appends them to top-level LOGBOOK.md organized by week and initiative
    4. Removes them from AGENDA.md

    Args:
        base_path: Base directory

    Returns:
        Tuple of (total_tasks_logged, initiatives_logged)
    """
    agenda_file = base_path / "AGENDA.md"
    if not agenda_file.exists():
        return (0, 0)

    content = agenda_file.read_text()

    # Extract completed tasks
    completed_tasks = extract_completed_tasks(content)
    if not completed_tasks:
        return (0, 0)

    # Append to logbook
    logged_count, initiatives_logged = append_to_logbook(completed_tasks, base_path)

    if logged_count > 0:
        # Remove from agenda
        updated_content = remove_completed_tasks_from_content(content, completed_tasks)
        agenda_file.write_text(updated_content)
        print(f"📓 Logged {logged_count} completed task(s) to LOGBOOK.md")
        print(f"🧹 Removed {logged_count} completed task(s) from AGENDA.md")

    return (logged_count, initiatives_logged)
