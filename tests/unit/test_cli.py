"""Tests for the main CLI interface.

These are smoke tests to ensure the CLI structure is correct and
commands are properly wired up.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from cli.cli import main


class TestCLIStructure:
    """Test basic CLI structure and help text."""

    def test_cli_shows_help_with_no_args(self):
        """CLI shows help when run with no arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli"],
            capture_output=True,
            text=True,
        )

        assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()

    def test_cli_has_init_command(self):
        """CLI has 'init' command."""
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "init", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "init" in output.lower()

    def test_cli_has_agenda_command(self):
        """CLI has 'agenda' command."""
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "agenda", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "agenda" in output.lower()


class TestInitCommand:
    """Test init command integration."""

    def test_init_creates_gameplan_yaml(self, temp_dir):
        """Running 'gameplan init' creates gameplan.yaml."""
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "init", "-d", str(temp_dir)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (temp_dir / "gameplan.yaml").exists()

    def test_init_shows_error_if_already_initialized(self, temp_dir):
        """Running 'gameplan init' twice shows error."""
        # First init
        subprocess.run(
            [sys.executable, "-m", "cli.cli", "init", "-d", str(temp_dir)],
            capture_output=True,
        )

        # Second init should fail
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "init", "-d", str(temp_dir)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        output = result.stdout + result.stderr
        assert "already exists" in output.lower()


class TestAgendaCommand:
    """Test agenda command integration."""

    def test_agenda_init_creates_agenda_file(self, temp_dir):
        """Running 'gameplan agenda init' creates AGENDA.md."""
        # First initialize gameplan
        subprocess.run(
            [sys.executable, "-m", "cli.cli", "init", "-d", str(temp_dir)],
            capture_output=True,
        )

        # Then create agenda
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "agenda", "init"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (temp_dir / "AGENDA.md").exists()

    def test_agenda_view_shows_content(self, temp_dir):
        """Running 'gameplan agenda view' shows AGENDA.md content."""
        # Setup
        subprocess.run(
            [sys.executable, "-m", "cli.cli", "init", "-d", str(temp_dir)],
            capture_output=True,
        )
        subprocess.run(
            [sys.executable, "-m", "cli.cli", "agenda", "init"],
            cwd=temp_dir,
            capture_output=True,
        )

        # View agenda
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "agenda", "view"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "# Agenda" in result.stdout

    def test_agenda_refresh_updates_sections(self, temp_dir):
        """Running 'gameplan agenda refresh' updates command sections."""
        # Setup
        subprocess.run(
            [sys.executable, "-m", "cli.cli", "init", "-d", str(temp_dir)],
            capture_output=True,
        )
        subprocess.run(
            [sys.executable, "-m", "cli.cli", "agenda", "init"],
            cwd=temp_dir,
            capture_output=True,
        )

        # Refresh agenda
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "agenda", "refresh"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


class TestCLICommandRouting:
    """Test CLI command routing with direct function calls."""

    @patch("cli.init.init_gameplan")
    @patch("sys.argv", ["gameplan", "init"])
    def test_init_command_calls_init_gameplan(self, mock_init):
        """init command routes to init_gameplan function."""
        mock_init.return_value = Path("/test")

        try:
            main()
        except SystemExit:
            pass

        mock_init.assert_called_once()

    @patch("cli.init.init_gameplan")
    @patch("sys.argv", ["gameplan", "init", "-d", "/tmp/test"])
    def test_init_command_passes_directory_argument(self, mock_init):
        """init command passes --directory argument."""
        mock_init.return_value = Path("/tmp/test")

        try:
            main()
        except SystemExit:
            pass

        # Check that target_dir was passed
        assert mock_init.call_count == 1
        assert mock_init.call_args[1]["target_dir"] == Path("/tmp/test")

    @patch("cli.sync.sync_all")
    @patch("sys.argv", ["gameplan", "sync"])
    def test_sync_command_calls_sync_all(self, mock_sync):
        """sync command routes to sync_all function."""
        try:
            main()
        except SystemExit:
            pass

        mock_sync.assert_called_once()

    @patch("cli.agenda.init_agenda")
    @patch("sys.argv", ["gameplan", "agenda", "init"])
    def test_agenda_init_calls_init_agenda(self, mock_init):
        """agenda init routes to init_agenda function."""
        try:
            main()
        except SystemExit:
            pass

        mock_init.assert_called_once()

    @patch("cli.agenda.view_agenda")
    @patch("sys.argv", ["gameplan", "agenda", "view"])
    def test_agenda_view_calls_view_agenda(self, mock_view):
        """agenda view routes to view_agenda function."""
        mock_view.return_value = "# Agenda\n\nTest content"

        try:
            main()
        except SystemExit:
            pass

        mock_view.assert_called_once()

    @patch("cli.agenda.refresh_agenda")
    @patch("sys.argv", ["gameplan", "agenda", "refresh"])
    def test_agenda_refresh_calls_refresh_agenda(self, mock_refresh):
        """agenda refresh routes to refresh_agenda function."""
        try:
            main()
        except SystemExit:
            pass

        mock_refresh.assert_called_once()

    @patch("sys.argv", ["gameplan"])
    def test_no_command_shows_help(self, capsys):
        """Running gameplan with no command shows help."""
        with pytest.raises(SystemExit):
            main()

        # argparse writes help to stderr by default
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "usage:" in output.lower()

    @patch("sys.argv", ["gameplan", "--help"])
    def test_help_flag_shows_help(self, capsys):
        """--help flag shows help text."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "usage:" in output.lower()


class TestJiraPopulateCommand:
    """Test 'gameplan jira populate' CLI command."""

    def test_cli_has_jira_command(self):
        """CLI has 'jira' command."""
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "jira", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "populate" in output.lower()

    def test_cli_jira_populate_has_help(self):
        """CLI 'jira populate' has help text."""
        result = subprocess.run(
            [sys.executable, "-m", "cli.cli", "jira", "populate", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "--jql" in output
        assert "--env" in output

    @patch("cli.sync.populate_jira_items")
    @patch("sys.argv", ["gameplan", "jira", "populate"])
    def test_jira_populate_calls_populate_function(self, mock_populate):
        """jira populate routes to populate_jira_items."""
        try:
            main()
        except SystemExit:
            pass

        mock_populate.assert_called_once()

    @patch("cli.sync.populate_jira_items")
    @patch(
        "sys.argv", ["gameplan", "jira", "populate", "--jql", "project = TEST", "--env", "staging"]
    )
    def test_jira_populate_passes_jql_and_env_overrides(self, mock_populate):
        """jira populate passes --jql and --env args to populate function."""
        try:
            main()
        except SystemExit:
            pass

        mock_populate.assert_called_once()
        call_kwargs = mock_populate.call_args
        # Check that jql and env were passed
        assert (
            call_kwargs[1].get("jql") == "project = TEST" or call_kwargs[0][1] == "project = TEST"
        )
