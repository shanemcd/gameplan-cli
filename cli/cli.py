"""Main CLI entry point for gameplan."""
import argparse
import logging
import os
import sys
from pathlib import Path

from cli import agenda, init, sync


def configure_logging(verbose: bool = False):
    """Configure logging.

    Args:
        verbose: If True, set level to DEBUG. Otherwise INFO.
                 Can also be overridden via GAMEPLAN_LOG_LEVEL env var.
    """
    # Environment variable takes precedence if set
    env_level = os.environ.get("GAMEPLAN_LOG_LEVEL")
    if env_level:
        level = getattr(logging, env_level.upper(), logging.INFO)
    else:
        level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def get_base_path() -> Path:
    """Get the base path for gameplan operations.

    Checks GAMEPLAN_BASE_DIR environment variable first (for wrapper usage),
    falls back to current directory.

    Returns:
        Path to use as base directory
    """
    base_dir = os.environ.get("GAMEPLAN_BASE_DIR")
    if base_dir:
        return Path(base_dir)
    return Path.cwd()


def cmd_init(args):
    """Execute init command."""
    try:
        target_dir = Path(args.directory) if args.directory else get_base_path()
        result = init.init_gameplan(target_dir=target_dir, interactive=args.interactive)
        print(f"✨ Initialized gameplan at {result}")
        print()
        print("📁 Created:")
        print("   - gameplan.yaml (configuration)")
        print("   - tracking/areas/jira/ (tracking files)")
        print()
        print("📋 Next steps:")
        print("   1. Edit gameplan.yaml to add items to track")
        print("   2. Run: gameplan agenda init")
        print("   3. Run: gameplan sync (when adapters configured)")
    except FileExistsError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_agenda(args):
    """Execute agenda subcommands."""
    try:
        base_path = get_base_path()

        if args.agenda_command == "init":
            agenda.init_agenda(base_path=base_path)
            print("✅ Created AGENDA.md")
            print()
            print("📋 Next steps:")
            print("   1. Edit AGENDA.md to add your focus items")
            print("   2. Run: gameplan agenda refresh (to update command sections)")
            print("   3. Run: gameplan agenda view (to display)")
        elif args.agenda_command == "view":
            content = agenda.view_agenda(base_path=base_path)
            print(content)
        elif args.agenda_command == "refresh":
            agenda.refresh_agenda(base_path=base_path)
            print("✅ Refreshed AGENDA.md")
        elif args.agenda_command == "tracked-items":
            output = agenda.format_tracked_items(base_path=base_path)
            print(output)
        else:
            print("Unknown agenda command", file=sys.stderr)
            sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except FileExistsError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_sync(args):
    """Execute sync command."""
    try:
        base_path = get_base_path()
        source = args.source if hasattr(args, 'source') else None

        if source == "jira":
            print("=" * 60)
            print("Jira Activity Sync")
            print("=" * 60)
            print()
            sync.sync_jira(base_path)
        else:
            # Sync all (currently just Jira)
            print("=" * 60)
            print("Syncing All Adapters")
            print("=" * 60)
            print()
            sync.sync_all(base_path)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Gameplan - Local-first work tracking CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new gameplan repository",
    )
    init_parser.add_argument(
        "-d",
        "--directory",
        help="Directory to initialize (default: current directory)",
    )
    init_parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode with prompts",
    )
    init_parser.set_defaults(func=cmd_init)

    # Agenda command
    agenda_parser = subparsers.add_parser(
        "agenda",
        help="Manage daily agenda",
    )
    agenda_subparsers = agenda_parser.add_subparsers(
        dest="agenda_command",
        help="Agenda commands",
    )

    # Set default to show help if no subcommand given
    agenda_parser.set_defaults(
        func=lambda args: (agenda_parser.print_help(), sys.exit(1))
    )

    # agenda init
    init_agenda_parser = agenda_subparsers.add_parser(
        "init",
        help="Create AGENDA.md from gameplan.yaml",
    )
    init_agenda_parser.set_defaults(func=cmd_agenda)

    # agenda view
    view_parser = agenda_subparsers.add_parser(
        "view",
        help="View current AGENDA.md",
    )
    view_parser.set_defaults(func=cmd_agenda)

    # agenda refresh
    refresh_parser = agenda_subparsers.add_parser(
        "refresh",
        help="Refresh command-driven sections in AGENDA.md",
    )
    refresh_parser.set_defaults(func=cmd_agenda)

    # agenda tracked-items
    tracked_items_parser = agenda_subparsers.add_parser(
        "tracked-items",
        help="Format tracked items from gameplan.yaml",
    )
    tracked_items_parser.set_defaults(func=cmd_agenda)

    # Sync command
    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync activity feeds from external systems",
    )
    sync_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    sync_parser.add_argument(
        "source",
        nargs="?",
        choices=["jira"],
        help="Source to sync (default: all)",
    )
    sync_parser.set_defaults(func=cmd_sync)

    args = parser.parse_args()

    # Configure logging based on -v flag
    configure_logging(verbose=args.verbose)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
