"""
Command-line interface for Media Plan OSC.

This module provides a command-line interface for managing workspaces
and media plans.
"""
import os
import sys
import argparse
import logging
from pathlib import Path

# Import the WorkspaceManager
from mediaplanpy.workspace import (
    WorkspaceManager,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mediaplanpy.cli")


def setup_argparse():
    """Set up argument parsing for the CLI."""
    parser = argparse.ArgumentParser(
        description="Media Plan OSC - Open Source Python SDK for Media Plans"
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Workspace commands
    workspace_parser = subparsers.add_parser("workspace", help="Workspace management")
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")

    # workspace init
    init_parser = workspace_subparsers.add_parser("init", help="Initialize a new workspace")
    init_parser.add_argument("--path", help="Path to create workspace.json", default="./workspace.json")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing workspace.json")

    # workspace validate
    validate_parser = workspace_subparsers.add_parser("validate", help="Validate an existing workspace")
    validate_parser.add_argument("--path", help="Path to workspace.json")

    # workspace info
    info_parser = workspace_subparsers.add_parser("info", help="Display information about the workspace")
    info_parser.add_argument("--path", help="Path to workspace.json")

    return parser


def handle_workspace_init(args):
    """Handle the 'workspace init' command."""
    try:
        manager = WorkspaceManager()
        config = manager.create_default_workspace(args.path, overwrite=args.force)
        print(f"✅ Created workspace '{config['workspace_name']}' at {args.path}")
        print(f"Storage mode: {config['storage']['mode']}")
        if config['storage']['mode'] == 'local':
            print(f"Local storage path: {config['storage']['local']['base_path']}")
    except WorkspaceError as e:
        print(f"❌ Error creating workspace: {e}")
        return 1
    return 0


def handle_workspace_validate(args):
    """Handle the 'workspace validate' command."""
    try:
        manager = WorkspaceManager(args.path)
        config = manager.load()
        valid = manager.validate()
        print(f"✅ Workspace '{config['workspace_name']}' is valid")

        # Show some info about the workspace
        print("\nWorkspace Configuration:")
        print(f"  Environment: {config['environment']}")
        print(f"  Storage Mode: {config['storage']['mode']}")

        if config['storage']['mode'] == 'local':
            local_path = manager.get_resolved_config()['storage']['local']['base_path']
            print(f"  Local Storage Path: {local_path}")
        elif config['storage']['mode'] == 's3':
            s3_config = config['storage']['s3']
            print(f"  S3 Bucket: {s3_config['bucket']}")
            if 'prefix' in s3_config:
                print(f"  S3 Prefix: {s3_config['prefix']}")
    except WorkspaceNotFoundError as e:
        print(f"❌ Workspace not found: {e}")
        return 1
    except WorkspaceValidationError as e:
        print(f"❌ Workspace validation failed: {e}")
        return 1
    except WorkspaceError as e:
        print(f"❌ Error validating workspace: {e}")
        return 1
    return 0


def handle_workspace_info(args):
    """Handle the 'workspace info' command."""
    try:
        manager = WorkspaceManager(args.path)
        config = manager.load()

        print(f"Workspace: {config['workspace_name']}")
        print(f"Environment: {config['environment']}")
        print("\nStorage Configuration:")
        print(f"  Mode: {config['storage']['mode']}")

        resolved = manager.get_resolved_config()

        if config['storage']['mode'] == 'local':
            local_config = resolved['storage']['local']
            print(f"  Base Path: {local_config['base_path']}")
            print(f"  Create If Missing: {local_config['create_if_missing']}")
        elif config['storage']['mode'] == 's3':
            s3_config = config['storage']['s3']
            print(f"  Bucket: {s3_config['bucket']}")
            if 'prefix' in s3_config:
                print(f"  Prefix: {s3_config['prefix']}")
            if 'region' in s3_config:
                print(f"  Region: {s3_config['region']}")

        print("\nDatabase Configuration:")
        db_config = config['database']
        if db_config.get('enabled', False):
            print(f"  Enabled: Yes")
            print(f"  Host: {db_config.get('host')}")
            print(f"  Port: {db_config.get('port', 5432)}")
            print(f"  Database: {db_config.get('database')}")
            print(f"  Schema: {db_config.get('schema', 'public')}")
            print(f"  SSL: {db_config.get('ssl', True)}")
        else:
            print("  Enabled: No")

        print("\nGoogle Sheets Configuration:")
        gs_config = config.get('google_sheets', {})
        if gs_config.get('enabled', False):
            print(f"  Enabled: Yes")
            if 'credentials_path' in gs_config:
                creds_path = resolved.get('google_sheets', {}).get('credentials_path', '')
                print(f"  Credentials Path: {creds_path}")
            if 'template_id' in gs_config:
                print(f"  Template ID: {gs_config['template_id']}")
        else:
            print("  Enabled: No")

        print("\nExcel Configuration:")
        excel_config = config.get('excel', {})
        if 'template_path' in excel_config:
            template_path = resolved.get('excel', {}).get('template_path', '')
            print(f"  Template Path: {template_path}")
        if 'default_export_path' in excel_config:
            export_path = resolved.get('excel', {}).get('default_export_path', '')
            print(f"  Default Export Path: {export_path}")

        print("\nLogging Configuration:")
        log_config = config.get('logging', {})
        print(f"  Level: {log_config.get('level', 'INFO')}")
        if 'file' in log_config:
            log_file = resolved.get('logging', {}).get('file', '')
            print(f"  Log File: {log_file}")

    except WorkspaceNotFoundError as e:
        print(f"❌ Workspace not found: {e}")
        return 1
    except WorkspaceValidationError as e:
        print(f"❌ Workspace validation failed: {e}")
        return 1
    except WorkspaceError as e:
        print(f"❌ Error loading workspace: {e}")
        return 1
    return 0


def main():
    """Main entry point for the CLI."""
    parser = setup_argparse()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Handle workspace commands
    if args.command == "workspace":
        if not args.workspace_command:
            # If no workspace subcommand, print workspace help
            for action in parser._actions:
                if action.dest == 'workspace_command':
                    action.choices['init'].print_help()
                    return 1

        if args.workspace_command == "init":
            return handle_workspace_init(args)
        elif args.workspace_command == "validate":
            return handle_workspace_validate(args)
        elif args.workspace_command == "info":
            return handle_workspace_info(args)

    # If we reach here, no command was handled
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())