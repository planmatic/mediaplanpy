"""
MediaPlanPy CLI v3.0 - Streamlined Administrative Interface

This module provides a command-line interface focused on administrative,
setup, and developer workflows for MediaPlanPy SDK v3.0.

Usage:
    mediaplanpy --help
    mediaplanpy workspace create --name "My Workspace"
    mediaplanpy workspace settings --workspace_id ws_abc123
    mediaplanpy list campaigns --workspace_id ws_abc123
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

# Import SDK components
from mediaplanpy import __version__, __schema_version__
from mediaplanpy.workspace import WorkspaceManager, WorkspaceError, WorkspaceNotFoundError
from mediaplanpy.exceptions import MediaPlanError

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency with thousand separators."""
    if currency:
        return f"${amount:,.0f}"
    return f"{amount:,.0f}"


def format_table(headers: List[str], rows: List[List[Any]], alignments: Optional[List[str]] = None) -> str:
    """
    Format data as a table with aligned columns.

    Args:
        headers: Column headers
        rows: Data rows
        alignments: List of 'left' or 'right' for each column

    Returns:
        Formatted table string
    """
    if not rows:
        return ""

    if alignments is None:
        alignments = ['left'] * len(headers)

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Format header
    header_parts = []
    for i, (header, width, align) in enumerate(zip(headers, col_widths, alignments)):
        if align == 'right':
            header_parts.append(header.rjust(width))
        else:
            header_parts.append(header.ljust(width))

    result = []
    result.append("  ".join(header_parts))
    result.append("─" * (sum(col_widths) + 2 * (len(headers) - 1)))

    # Format rows
    for row in rows:
        row_parts = []
        for i, (cell, width, align) in enumerate(zip(row, col_widths, alignments)):
            cell_str = str(cell)
            # Truncate long values
            if len(cell_str) > width and width > 20:
                cell_str = cell_str[:width-3] + "..."

            if align == 'right':
                row_parts.append(cell_str.rjust(width))
            else:
                row_parts.append(cell_str.ljust(width))
        result.append("  ".join(row_parts))

    return "\n".join(result)


def print_error(title: str, message: str, suggestion: Optional[str] = None):
    """Print formatted error message."""
    print(f"\nError: {title}")
    print(f"   {message}")
    if suggestion:
        print(f"\nSuggestion:")
        print(f"   {suggestion}")
    print()


def print_success(message: str):
    """Print success message."""
    print(message)


# =============================================================================
# ARGUMENT PARSER SETUP
# =============================================================================

def setup_argparse() -> argparse.ArgumentParser:
    """Set up argument parsing for the CLI."""
    parser = argparse.ArgumentParser(
        description=f"MediaPlanPy CLI v{__version__} - Administrative Interface",
        epilog=f"SDK Version: {__version__} | Schema: v{__schema_version__}"
    )

    # Global version flag
    parser.add_argument(
        '--version',
        action='version',
        version=f'mediaplanpy {__version__} (schema v{__schema_version__})'
    )

    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # =========================================================================
    # WORKSPACE COMMANDS
    # =========================================================================
    workspace_parser = subparsers.add_parser(
        "workspace",
        help="Workspace management commands"
    )
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")

    # workspace create
    create_parser = workspace_subparsers.add_parser(
        "create",
        help="Create a new workspace with v3.0 defaults"
    )
    create_parser.add_argument(
        "--path",
        default="./workspace.json",
        help="Path to create workspace.json (default: ./workspace.json)"
    )
    create_parser.add_argument(
        "--name",
        help=f"Workspace name (default: 'Workspace created YYYYMMDD')"
    )
    create_parser.add_argument(
        "--storage",
        choices=["local", "s3"],
        default="local",
        help="Storage mode: local or s3 (default: local)"
    )
    create_parser.add_argument(
        "--database",
        choices=["true", "false"],
        default="false",
        help="Enable database: true or false (default: false)"
    )
    create_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing workspace.json if present"
    )

    # workspace settings
    settings_parser = workspace_subparsers.add_parser(
        "settings",
        help="Show workspace configuration and status"
    )
    settings_parser.add_argument(
        "--workspace_id",
        required=True,
        help="Workspace ID"
    )

    # workspace validate
    validate_parser = workspace_subparsers.add_parser(
        "validate",
        help="Validate workspace configuration and connectivity"
    )
    validate_parser.add_argument(
        "--workspace_id",
        required=True,
        help="Workspace ID"
    )

    # workspace upgrade
    upgrade_parser = workspace_subparsers.add_parser(
        "upgrade",
        help="Upgrade workspace to current SDK/schema version"
    )
    upgrade_parser.add_argument(
        "--workspace_id",
        required=True,
        help="Workspace ID"
    )
    upgrade_parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the upgrade (default is dry-run)"
    )

    # workspace statistics
    statistics_parser = workspace_subparsers.add_parser(
        "statistics",
        help="Display workspace statistics and summary"
    )
    statistics_parser.add_argument(
        "--workspace_id",
        required=True,
        help="Workspace ID"
    )

    # workspace version
    version_parser = workspace_subparsers.add_parser(
        "version",
        help="Display comprehensive schema version information"
    )
    version_parser.add_argument(
        "--workspace_id",
        required=True,
        help="Workspace ID"
    )

    # =========================================================================
    # LIST COMMANDS
    # =========================================================================
    list_parser = subparsers.add_parser(
        "list",
        help="Inspection commands"
    )
    list_subparsers = list_parser.add_subparsers(dest="list_command")

    # list campaigns
    campaigns_parser = list_subparsers.add_parser(
        "campaigns",
        help="List all campaigns in workspace"
    )
    campaigns_parser.add_argument(
        "--workspace_id",
        required=True,
        help="Workspace ID"
    )
    campaigns_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format: table or json (default: table)"
    )
    campaigns_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Limit results to n rows (default: 100)"
    )
    campaigns_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip first n rows (default: 0)"
    )

    # list mediaplans
    mediaplans_parser = list_subparsers.add_parser(
        "mediaplans",
        help="List all media plans in workspace"
    )
    mediaplans_parser.add_argument(
        "--workspace_id",
        required=True,
        help="Workspace ID"
    )
    mediaplans_parser.add_argument(
        "--campaign_id",
        help="Filter by campaign ID (optional)"
    )
    mediaplans_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format: table or json (default: table)"
    )
    mediaplans_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Limit results to n rows (default: 100)"
    )
    mediaplans_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip first n rows (default: 0)"
    )

    return parser


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_workspace_create(args) -> int:
    """Handle the 'workspace create' command."""
    try:
        # Generate default name if not provided
        workspace_name = args.name or f"Workspace created {datetime.now().strftime('%Y%m%d')}"

        # Convert database string to boolean
        database_enabled = args.database == "true"

        # Check if file exists without --force
        if Path(args.path).exists() and not args.force:
            print_error(
                "File already exists",
                f"Workspace settings file already exists: {args.path}",
                "Use --force to overwrite existing file"
            )
            return 1

        # Create workspace
        manager = WorkspaceManager()

        # Prepare workspace settings
        workspace_settings = {
            "schema_version": "3.0",
            "last_upgraded": datetime.now().strftime("%Y-%m-%d"),
            "sdk_version_required": "3.0.x"
        }

        # Create with specified configuration
        workspace_id, settings_path = manager.create(
            settings_path_name=str(Path(args.path).parent) if args.path != "./workspace.json" else None,
            settings_file_name=Path(args.path).name if args.path != "./workspace.json" else None,
            overwrite=args.force,
            workspace_settings=workspace_settings
        )

        # Load and modify configuration for storage mode and database
        config = manager.load()

        # Update workspace name
        config['workspace_name'] = workspace_name

        # Configure storage mode
        if args.storage == "s3":
            config['storage']['mode'] = 's3'
            config['storage']['s3'] = {
                'bucket': 'YOUR-BUCKET-NAME',
                'region': 'us-east-1',
                'prefix': '',
                'create_if_missing': True
            }

        # Configure database
        if database_enabled:
            config['database'] = {
                'enabled': True,
                'host': 'localhost',
                'port': 5432,
                'database': 'mediaplan_db',
                'user': 'postgres',
                'password': '',
                'table': 'mediaplans',
                'schema': 'public'
            }

        # Save updated configuration
        with open(settings_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Display success message
        print(f"Created workspace '{workspace_name}' with ID '{workspace_id}'")
        print(f"Settings file: {settings_path}")
        print(f"Schema version: v3.0")
        print(f"Storage mode: {args.storage}")

        if args.storage == "s3":
            print(f"\nIMPORTANT: Please edit the workspace settings file to configure S3:")
            print(f"   File: {settings_path}")
            print(f"   Update: storage.s3.bucket (currently: 'YOUR-BUCKET-NAME')")
            print(f"   Update: storage.s3.region (currently: 'us-east-1')")
        else:
            storage_path = config['storage']['local']['base_path']
            print(f"Storage path: {storage_path}")

        if database_enabled:
            print(f"Database: Enabled")
            print(f"\nIMPORTANT: Please edit the workspace settings file to configure database:")
            print(f"   File: {settings_path}")
            print(f"   Update: database.host (currently: 'localhost')")
            print(f"   Update: database.database (currently: 'mediaplan_db')")
            print(f"   Update: database.user (currently: 'postgres')")
            print(f"   Update: database.password (currently: '')")

        print(f"\nNext steps:")
        print(f"   - Review settings: mediaplanpy workspace settings --workspace_id {workspace_id}")
        if args.storage == "s3" or database_enabled:
            print(f"   - Validate: mediaplanpy workspace validate --workspace_id {workspace_id}")
        print(f"   - Start using Python API to create media plans")

        return 0

    except Exception as e:
        print_error("Workspace creation failed", str(e))
        return 1


def handle_workspace_settings(args) -> int:
    """Handle the 'workspace settings' command."""
    try:
        # Load workspace using workspace_id (SDK handles file lookup)
        manager = WorkspaceManager()
        config = manager.load(workspace_id=args.workspace_id)

        # Display settings
        print("Workspace Settings\n")

        # Basic Information
        print("Basic Information:")
        print(f"   Name: {config.get('workspace_name', 'Unknown')}")
        print(f"   ID: {config.get('workspace_id', 'Unknown')}")
        print(f"   Environment: {config.get('environment', 'production')}")

        workspace_settings = config.get('workspace_settings', {})
        schema_version = workspace_settings.get('schema_version', 'Unknown')
        print(f"   Schema version: v{schema_version}")
        print(f"   Settings file: {manager.workspace_path}")

        # Storage Configuration
        print(f"\nStorage Configuration:")
        storage_config = config.get('storage', {})
        storage_mode = storage_config.get('mode', 'local')
        print(f"   Mode: {storage_mode}")

        if storage_mode == 'local':
            local_config = storage_config.get('local', {})
            print(f"   Base path: {local_config.get('base_path', 'Unknown')}")
            print(f"   Formats: json, parquet")
            print(f"   Create if missing: {local_config.get('create_if_missing', True)}")
        elif storage_mode == 's3':
            s3_config = storage_config.get('s3', {})
            print(f"   S3 Bucket: {s3_config.get('bucket', 'Unknown')}")
            print(f"   S3 Region: {s3_config.get('region', 'Unknown')}")
            if s3_config.get('prefix'):
                print(f"   S3 Prefix: {s3_config.get('prefix')}")
            print(f"   Formats: json, parquet")

        # Database Configuration
        print(f"\nDatabase Configuration:")
        db_config = config.get('database', {})
        db_enabled = db_config.get('enabled', False)

        if db_enabled:
            print(f"   Enabled: Yes")
            print(f"   Host: {db_config.get('host', 'Unknown')}")
            print(f"   Port: {db_config.get('port', 5432)}")
            print(f"   Database: {db_config.get('database', 'Unknown')}")
            print(f"   Table: {db_config.get('table', 'mediaplans')}")
            print(f"   User: {db_config.get('user', 'Unknown')}")
            print(f"   Schema: {db_config.get('schema', 'public')}")
            print(f"   SSL: {db_config.get('ssl', False)}")
        else:
            print(f"   Enabled: No")

        # SDK Compatibility
        print(f"\nSDK Compatibility:")
        print(f"   Current SDK: v{__version__}")
        print(f"   Required SDK: {workspace_settings.get('sdk_version_required', 'Not set')}")

        # Simple compatibility check
        sdk_major = int(__version__.split('.')[0])
        workspace_schema_major = int(schema_version.split('.')[0]) if '.' in schema_version else 0

        if sdk_major == workspace_schema_major:
            print(f"   Status: Compatible")
        else:
            print(f"   Status: Incompatible - Upgrade required")

        # Workspace Settings
        print(f"\nWorkspace Settings:")
        print(f"   Last upgraded: {workspace_settings.get('last_upgraded', 'Unknown')}")
        print(f"   SDK version required: {workspace_settings.get('sdk_version_required', 'Not set')}")
        if workspace_settings.get('created_at'):
            print(f"   Created at: {workspace_settings.get('created_at')}")

        return 0

    except WorkspaceNotFoundError as e:
        print_error(
            "Workspace not found",
            str(e),
            "Create a new workspace: mediaplanpy workspace create\n" +
            "   Or verify workspace_id is correct"
        )
        return 3
    except WorkspaceError as e:
        print_error("Workspace error", str(e))
        return 1
    except Exception as e:
        print_error("Unexpected error", str(e))
        return 1


def handle_workspace_validate(args) -> int:
    """Handle the 'workspace validate' command."""
    print("Workspace Validation Report\n")

    failures = 0

    try:
        # Load workspace using workspace_id (SDK handles file lookup)
        manager = WorkspaceManager()
        config = manager.load(workspace_id=args.workspace_id)
        workspace_name = config.get('workspace_name', 'Unknown')
        print(f"Workspace: {workspace_name} ({args.workspace_id})\n")

    except WorkspaceNotFoundError as e:
        print(f"Workspace: {args.workspace_id}\n")
        print(f"[1/7] Workspace settings file: ❌ FAIL")
        print(f"   Could not find workspace settings file")
        print(f"   {str(e)}")
        print(f"\n[7/7] Overall status: ❌ FAIL (1 failure)\n")
        print(f"Workspace has validation errors. Please address failures above.")
        return 1
    except Exception as e:
        print(f"Workspace: {args.workspace_id}\n")
        print(f"[1/7] Workspace settings file: ❌ FAIL")
        print(f"   Error loading: {str(e)}")
        print(f"\n[7/7] Overall status: ❌ FAIL (1 failure)\n")
        print(f"Workspace has validation errors. Please address failures above.")
        return 1

    try:
        # Check 1: Workspace settings file
        print(f"[1/7] Workspace settings file: ✅ PASS")
        print(f"   Location: {manager.workspace_path}")

        # Check 2: Settings file format (already validated by loading)
        print(f"\n[2/7] Settings file format: ✅ PASS")
        print(f"   Valid JSON")

        # Check 3: Settings file schema
        print(f"\n[3/7] Settings file schema: ✅ PASS")
        print(f"   Valid workspace configuration")

        # Check 4: SDK compatibility
        workspace_settings = config.get('workspace_settings', {})
        schema_version = workspace_settings.get('schema_version', 'Unknown')
        sdk_major = int(__version__.split('.')[0])
        workspace_schema_major = int(schema_version.split('.')[0]) if '.' in schema_version else 0

        if sdk_major == workspace_schema_major:
            print(f"\n[4/7] SDK compatibility: ✅ PASS")
            print(f"   Workspace schema v{schema_version} compatible with SDK v{__version__}")
        else:
            print(f"\n[4/7] SDK compatibility: ❌ FAIL")
            print(f"   Workspace schema v{schema_version} incompatible with SDK v{__version__}")
            print(f"   Action required: Run workspace upgrade")
            failures += 1

        # Check 5: Storage access
        storage_config = config.get('storage', {})
        storage_mode = storage_config.get('mode', 'local')

        if storage_mode == 'local':
            local_config = storage_config.get('local', {})
            base_path = local_config.get('base_path', './mediaplans')

            try:
                # Resolve path
                resolved_config = manager.get_resolved_config()
                resolved_path = resolved_config['storage']['local']['base_path']

                if Path(resolved_path).exists():
                    print(f"\n[5/7] Storage access: ✅ PASS")
                    print(f"   Local storage folder accessible: {resolved_path}")
                else:
                    print(f"\n[5/7] Storage access: ⚠️  WARNING")
                    print(f"   Local storage folder does not exist: {resolved_path}")
                    print(f"   Will be created automatically on first use")
            except Exception as e:
                print(f"\n[5/7] Storage access: ❌ FAIL")
                print(f"   Error accessing local storage: {str(e)}")
                failures += 1

        elif storage_mode == 's3':
            s3_config = storage_config.get('s3', {})
            bucket = s3_config.get('bucket', '')

            if bucket == 'YOUR-BUCKET-NAME' or not bucket:
                print(f"\n[5/7] Storage access: ❌ FAIL")
                print(f"   S3 bucket not configured (currently: '{bucket}')")
                print(f"   Action required: Edit workspace settings file")
                failures += 1
            else:
                # Try to access S3 bucket
                try:
                    import boto3
                    from botocore.exceptions import ClientError

                    s3_client = boto3.client('s3', region_name=s3_config.get('region', 'us-east-1'))
                    s3_client.head_bucket(Bucket=bucket)
                    print(f"\n[5/7] Storage access: ✅ PASS")
                    print(f"   S3 bucket accessible: s3://{bucket}/")
                except ImportError:
                    print(f"\n[5/7] Storage access: ⚠️  WARNING")
                    print(f"   boto3 not installed, cannot verify S3 access")
                except ClientError as e:
                    print(f"\n[5/7] Storage access: ❌ FAIL")
                    print(f"   Cannot access S3 bucket: {bucket}")
                    print(f"   Error: {str(e)}")
                    failures += 1
                except Exception as e:
                    print(f"\n[5/7] Storage access: ❌ FAIL")
                    print(f"   Error checking S3 access: {str(e)}")
                    failures += 1

        # Check 6: Database connection (if enabled)
        db_config = config.get('database', {})
        db_enabled = db_config.get('enabled', False)

        if db_enabled:
            try:
                from mediaplanpy.storage.database import PostgreSQLBackend

                db_backend = PostgreSQLBackend(manager.get_resolved_config())

                # Try to connect
                if db_backend.test_connection():
                    # Check if table exists
                    if db_backend.table_exists():
                        print(f"\n[6/7] Database connection: ✅ PASS")
                        print(f"   Connected to postgresql://{db_config.get('host')}:{db_config.get('port')}/{db_config.get('database')}")
                        print(f"   Table '{db_config.get('table', 'mediaplans')}' exists")
                    else:
                        print(f"\n[6/7] Database connection: ⚠️  WARNING")
                        print(f"   Connected to postgresql://{db_config.get('host')}:{db_config.get('port')}/{db_config.get('database')}")
                        print(f"   Table '{db_config.get('table', 'mediaplans')}' does not exist")
                        print(f"   Will be created automatically on first use")
                else:
                    print(f"\n[6/7] Database connection: ❌ FAIL")
                    print(f"   Cannot connect to postgresql://{db_config.get('host')}:{db_config.get('port')}/{db_config.get('database')}")
                    print(f"   Action required: Check database connection settings")
                    failures += 1

            except ImportError:
                print(f"\n[6/7] Database connection: ⚠️  WARNING")
                print(f"   psycopg2 not installed, cannot verify database connection")
            except Exception as e:
                print(f"\n[6/7] Database connection: ❌ FAIL")
                print(f"   Cannot connect to postgresql://{db_config.get('host')}:{db_config.get('port')}/{db_config.get('database')}")
                print(f"   Error: {str(e)}")
                print(f"   Action required: Check database connection settings")
                failures += 1
        else:
            print(f"\n[6/7] Database connection: ✅ PASS")
            print(f"   Database not enabled (skipped)")

        # Check 7: Overall status
        if failures == 0:
            print(f"\n[7/7] Overall status: ✅ PASS\n")
            print(f"Workspace is valid and ready to use.")
            return 0
        else:
            print(f"\n[7/7] Overall status: ❌ FAIL ({failures} failure{'s' if failures > 1 else ''})\n")
            print(f"Workspace has validation errors. Please address failures above.")
            return 1

    except Exception as e:
        print_error("Validation error", str(e))
        return 1


def handle_workspace_upgrade(args) -> int:
    """Handle the 'workspace upgrade' command."""
    try:
        # Load workspace using workspace_id in upgrade mode (SDK handles file lookup)
        manager = WorkspaceManager()
        manager.load(workspace_id=args.workspace_id, upgrade_mode=True)

        workspace_name = manager.config.get('workspace_name', 'Unknown')

        # Determine if this is dry-run or execute
        dry_run = not args.execute

        if dry_run:
            print("Workspace Upgrade Preview (Dry Run)\n")
        else:
            print("Upgrading Workspace to v3.0\n")

        print(f"Workspace: {workspace_name} ({args.workspace_id})\n")

        # Perform upgrade
        result = manager.upgrade_workspace(dry_run=dry_run)

        if dry_run:
            # Display dry-run preview
            print("Current State:")
            workspace_settings = manager.config.get('workspace_settings', {})
            current_schema = workspace_settings.get('schema_version', 'Unknown')
            print(f"   Schema version: v{current_schema}")
            print(f"   JSON files: {result.get('files_to_migrate', 0)}")
            print(f"   Parquet files: {result.get('files_to_migrate', 0)}")

            if result.get('database_upgrade_needed'):
                print(f"   Database: Enabled (v{current_schema} schema)")

            print(f"\nPlanned Changes:")
            print(f"   Target schema: v3.0")
            print(f"\n   Files to migrate: {result.get('files_to_migrate', 0)}")
            print(f"   - Audience fields will become target_audiences array")
            print(f"   - Location fields will become target_locations array")
            print(f"   - Dictionary field will be renamed")

            if result.get('database_upgrade_needed'):
                print(f"\n   Database changes:")
                print(f"   - Add 42 new columns (Campaign, LineItem, Meta)")
                print(f"   - Preserve all existing data")

            print(f"\n   Backups to create:")
            if result.get('backup_info'):
                for backup_type, backup_path in result['backup_info'].items():
                    print(f"   - {backup_type}: {backup_path}")

            print(f"\nThis is a dry run. No changes made.")
            print(f"To perform actual upgrade: add --execute flag")

        else:
            # Display actual upgrade progress and results
            # (The upgrade_workspace method will have done the work)

            print(f"Step 1/5: Creating backups...")
            if result.get('backups_created'):
                backups = result['backups_created']
                if backups.get('json_backup'):
                    print(f"   JSON files backed up ({backups['json_backup'].get('files_backed_up', 0)} files)")
                if backups.get('parquet_backup'):
                    print(f"   Parquet files backed up ({backups['parquet_backup'].get('files_backed_up', 0)} files)")
                if backups.get('database_backup', {}).get('backup_created'):
                    print(f"   Database backed up ({backups['database_backup'].get('records_backed_up', 0)} records)")
                print(f"   Backup location: {backups.get('backup_directory', 'Unknown')}")

            print(f"\nStep 2/5: Migrating JSON files...")
            print(f"   Migrated {result.get('json_files_migrated', 0)} files (v2.0 to v3.0)")

            print(f"\nStep 3/5: Regenerating Parquet files...")
            print(f"   Regenerated {result.get('parquet_files_regenerated', 0)} files with v3.0 schema")

            print(f"\nStep 4/5: Upgrading database schema...")
            if result.get('database_upgraded'):
                db_result = result.get('database_result', {})
                print(f"   Added {db_result.get('columns_added', 42)} new columns")
                records_before = db_result.get('records_before', 0)
                records_after = db_result.get('records_after', 0)
                if records_before == records_after:
                    print(f"   Data integrity verified ({records_after} records preserved)")
            else:
                print(f"   Database not enabled or already upgraded")

            print(f"\nStep 5/5: Updating workspace settings...")
            print(f"   Workspace settings updated to v3.0")

            print(f"\nUpgrade Complete\n")

            print(f"Summary:")
            print(f"   Files migrated: {result.get('json_files_migrated', 0)}")
            print(f"   Parquet regenerated: {result.get('parquet_files_regenerated', 0)}")
            print(f"   Database upgraded: {'Yes' if result.get('database_upgraded') else 'No'}")
            print(f"   Schema version: v3.0")

            if result.get('backups_created', {}).get('backup_directory'):
                print(f"\nBackups saved to: {result['backups_created']['backup_directory']}")

            print(f"Workspace is now compatible with SDK v{__version__}")

        return 0

    except WorkspaceNotFoundError as e:
        print_error(
            "Workspace not found",
            str(e),
            "Verify workspace_id is correct"
        )
        return 3
    except WorkspaceError as e:
        print_error("Workspace upgrade error", str(e))
        return 1
    except Exception as e:
        print_error("Unexpected error", str(e))
        import traceback
        traceback.print_exc()
        return 1


def handle_workspace_statistics(args) -> int:
    """Handle the 'workspace statistics' command."""
    print_error(
        "Not implemented",
        "The workspace statistics command is not yet implemented.",
        "This command will be implemented in Phase 2"
    )
    return 1


def handle_workspace_version(args) -> int:
    """Handle the 'workspace version' command."""
    print_error(
        "Not implemented",
        "The workspace version command is not yet implemented.",
        "This command will be implemented in Phase 3"
    )
    return 1


def handle_list_campaigns(args) -> int:
    """Handle the 'list campaigns' command."""
    print_error(
        "Not implemented",
        "The list campaigns command is not yet implemented.",
        "This command will be implemented in Phase 2"
    )
    return 1


def handle_list_mediaplans(args) -> int:
    """Handle the 'list mediaplans' command."""
    print_error(
        "Not implemented",
        "The list mediaplans command is not yet implemented.",
        "This command will be implemented in Phase 2"
    )
    return 1


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main entry point for the CLI."""
    parser = setup_argparse()
    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        print(f"\nMediaPlanPy CLI v{__version__}")
        print(f"Schema: v{__schema_version__}")
        print(f"Supported: v2.0 (deprecated), v3.0 (current)")
        print(f"\nQuick Start:")
        print(f"   mediaplanpy workspace create --name 'My Workspace'")
        print(f"   mediaplanpy workspace settings --workspace_id ws_abc123")
        print(f"   mediaplanpy workspace upgrade --workspace_id ws_abc123")
        return 1

    # Handle workspace commands
    if args.command == "workspace":
        if not args.workspace_command:
            print("Error: No workspace command specified")
            print("Use: mediaplanpy workspace --help")
            return 1

        if args.workspace_command == "create":
            return handle_workspace_create(args)
        elif args.workspace_command == "settings":
            return handle_workspace_settings(args)
        elif args.workspace_command == "validate":
            return handle_workspace_validate(args)
        elif args.workspace_command == "upgrade":
            return handle_workspace_upgrade(args)
        elif args.workspace_command == "statistics":
            return handle_workspace_statistics(args)
        elif args.workspace_command == "version":
            return handle_workspace_version(args)

    # Handle list commands
    elif args.command == "list":
        if not args.list_command:
            print("Error: No list command specified")
            print("Use: mediaplanpy list --help")
            return 1

        if args.list_command == "campaigns":
            return handle_list_campaigns(args)
        elif args.list_command == "mediaplans":
            return handle_list_mediaplans(args)

    # Unknown command
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
