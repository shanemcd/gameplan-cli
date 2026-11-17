"""Explicit agenda paths keep workspace configuration separate from page storage."""
import subprocess
import sys
from pathlib import Path

import pytest

from cli.agenda import init_agenda, refresh_agenda, view_agenda


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / "gameplan.yaml").write_text(
        "agenda:\n  sections:\n    - name: Notes\n    - name: Calendar\n"
        "      command: \"printf 'fresh calendar'\"\n"
    )
    return tmp_path


@pytest.mark.parametrize("absolute", [False, True])
def test_init_view_custom_path(workspace, absolute):
    target = workspace / "agenda" / "README.md"
    path = target if absolute else Path("agenda/README.md")
    assert init_agenda(workspace, agenda_path=path) == target
    assert view_agenda(workspace, agenda_path=path) == target.read_text()
    assert not (workspace / "AGENDA.md").exists()
    with pytest.raises(FileExistsError):
        init_agenda(workspace, agenda_path=path)


def test_refresh_preserves_frontmatter_and_uses_custom_logbook_source(workspace):
    target = workspace / "page.md"
    frontmatter = b'---\r\nid: stable-id\r\ntitle: Agenda\r\ncustom: |\r\n  ## Metadata\r\n---\r\n'
    target.write_bytes(frontmatter + (
        "## Notes\nKeep this note\n- [x] Finished task ✅ 2026-10-30\n\n"
        "## Calendar\nstale\n"
    ).encode())
    (workspace / "AGENDA.md").write_text("Unrelated agenda\n")
    assert refresh_agenda(workspace, agenda_path=target) == target
    result = target.read_bytes()
    assert result.startswith(frontmatter)
    assert b"Keep this note" in result
    assert b"fresh calendar" in result
    assert b"Finished task" not in result
    assert b"# Agenda -" not in result
    assert "Finished task" in (workspace / "LOGBOOK.md").read_text()
    assert (workspace / "AGENDA.md").read_text() == "Unrelated agenda\n"


def test_cli_path_for_all_commands(workspace):
    script = "from cli.cli import main; main()"
    root = Path(__file__).resolve().parents[2]
    import os
    env = {**os.environ, "PYTHONPATH": str(root), "GAMEPLAN_BASE_DIR": str(workspace)}
    for command in ["init", "view", "refresh"]:
        result = subprocess.run(
            [sys.executable, "-c", script, "agenda", command, "--path", "custom/README.md"],
            cwd=workspace, env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
    assert not (workspace / "AGENDA.md").exists()


@pytest.mark.parametrize("agenda", ["AGENDA.md", "agenda/README.md", "plans/daily/README.md"])
def test_tracked_item_links_are_relative_to_agenda(workspace, agenda):
    import os
    import yaml
    from cli.agenda import format_tracked_items
    config = {"areas": {"jira": {"items": [{"issue": "TEST-1", "env": "prod"}]}, "misc": {"items": [{"id": "project", "title": "Project"}]}}, "agenda": {"sections": []}}
    (workspace / "gameplan.yaml").write_text(yaml.safe_dump(config))
    targets = ["tracking/areas/jira/TEST-1-example/README.md", "tracking/areas/misc/project-example/README.md"]
    for target in targets:
        path = workspace / target
        path.parent.mkdir(parents=True)
        path.write_text("---\ntitle: Example\nstatus: Active\n---\n")
    output = format_tracked_items(workspace, agenda_path=Path(agenda))
    for target in targets:
        expected = os.path.relpath(workspace / target, (workspace / agenda).parent)
        assert f"[Details →]({expected})" in output


def test_refresh_passes_agenda_location_to_tracked_items(workspace):
    import shlex
    import yaml
    from unittest.mock import patch
    command = f"{shlex.quote(sys.executable)} -m cli.cli agenda tracked-items"
    config = {"areas": {"jira": {"items": [{"issue": "TEST-1", "env": "prod"}]}}, "agenda": {"sections": [{"name": "Tracked Items", "command": command}]}}
    (workspace / "gameplan.yaml").write_text(yaml.safe_dump(config))
    target = workspace / "tracking/areas/jira/TEST-1-example/README.md"
    target.parent.mkdir(parents=True)
    target.write_text("---\ntitle: Example\nstatus: Active\n---\n")
    agenda = workspace / "agenda/README.md"
    agenda.parent.mkdir()
    agenda.write_text("## Tracked Items\nstale\n")
    import os
    root = Path(__file__).resolve().parents[2]
    with patch.dict(os.environ, {"PYTHONPATH": str(root)}):
        refresh_agenda(workspace, agenda_path=agenda)
    assert "[Details →](../tracking/areas/jira/TEST-1-example/README.md)" in agenda.read_text()


def test_missing_custom_path_error_names_target(workspace):
    with pytest.raises(FileNotFoundError, match="missing.md"):
        view_agenda(workspace, agenda_path=Path("missing.md"))
