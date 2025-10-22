"""Main CLI entry point for gameplan."""
import argparse
import sys
from pathlib import Path

from cli import agenda, init


def cmd_init(args):
    """Execute init command."""
    try:
        target_dir = Path(args.directory) if args.directory else None
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
        if args.agenda_command == "init":
            agenda.init_agenda()
            print("✅ Created AGENDA.md")
            print()
            print("📋 Next steps:")
            print("   1. Edit AGENDA.md to add your focus items")
            print("   2. Run: gameplan agenda refresh (to update command sections)")
            print("   3. Run: gameplan agenda view (to display)")
        elif args.agenda_command == "view":
            content = agenda.view_agenda()
            print(content)
        elif args.agenda_command == "refresh":
            agenda.refresh_agenda()
            print("✅ Refreshed AGENDA.md")
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Gameplan - Local-first work tracking CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
