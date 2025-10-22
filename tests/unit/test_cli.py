"""Tests for the main CLI interface.

These are smoke tests to ensure the CLI structure is correct and
commands are properly wired up.
"""
import subprocess
import sys
from pathlib import Path

import pytest


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
