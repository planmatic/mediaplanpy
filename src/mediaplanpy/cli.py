"""
Command-line interface for Media Plan OSC.

This module provides a command-line interface for managing workspaces
and media plans.
"""
import os
import sys
import json
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

# Import schema module
from mediaplanpy.schema import (
    SchemaRegistry,
    SchemaValidator,
    SchemaMigrator
)

# Import exceptions
from mediaplanpy.exceptions import (
    SchemaError,
    SchemaVersionError,
    SchemaRegistryError,
    SchemaMigrationError,
    ValidationError
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

    # Schema commands
    schema_parser = subparsers.add_parser("schema", help="Schema management")
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command")

    # schema info
    schema_info_parser = schema_subparsers.add_parser("info", help="Display schema information")
    schema_info_parser.add_argument("--workspace", help="Path to workspace.json")

    # schema versions
    schema_versions_parser = schema_subparsers.add_parser("versions", help="List supported schema versions")
    schema_versions_parser.add_argument("--workspace", help="Path to workspace.json")

    # schema validate
    schema_validate_parser = schema_subparsers.add_parser("validate", help="Validate a media plan against schema")
    schema_validate_parser.add_argument("file", help="Path to media plan JSON file")
    schema_validate_parser.add_argument("--version", help="Schema version to validate against")
    schema_validate_parser.add_argument("--workspace", help="Path to workspace.json")

    # schema migrate
    schema_migrate_parser = schema_subparsers.add_parser("migrate", help="Migrate a media plan to a new schema version")
    schema_migrate_parser.add_argument("file", help="Path to media plan JSON file")
    schema_migrate_parser.add_argument("--to-version", help="Target schema version")
    schema_migrate_parser.add_argument("--output", help="Output file path (defaults to input with version suffix)")
    schema_migrate_parser.add_argument("--workspace", help="Path to workspace.json")

    # Excel commands
    excel_parser = subparsers.add_parser("excel", help="Excel operations")
    excel_subparsers = excel_parser.add_subparsers(dest="excel_command")

    # excel export
    excel_export_parser = excel_subparsers.add_parser("export", help="Export media plan to Excel")
    excel_export_parser.add_argument("--file", help="Path to media plan JSON file")
    excel_export_parser.add_argument("--workspace", help="Path to workspace.json")
    excel_export_parser.add_argument("--path", help="Path to media plan in workspace storage")
    excel_export_parser.add_argument("--campaign-id", help="Campaign ID to load from workspace storage")
    excel_export_parser.add_argument("--output", help="Output path for Excel file")
    excel_export_parser.add_argument("--template", help="Path to Excel template file")
    excel_export_parser.add_argument("--no-docs", action="store_true", help="Exclude documentation sheet")

    # excel import
    excel_import_parser = excel_subparsers.add_parser("import", help="Import media plan from Excel")
    excel_import_parser.add_argument("file", help="Path to Excel file")
    excel_import_parser.add_argument("--output", help="Output path for JSON file")
    excel_import_parser.add_argument("--workspace", help="Path to workspace.json")

    # excel update
    excel_update_parser = excel_subparsers.add_parser("update", help="Update media plan from Excel")
    excel_update_parser.add_argument("file", help="Path to Excel file with updates")
    excel_update_parser.add_argument("--target", help="Path to media plan JSON file to update")
    excel_update_parser.add_argument("--workspace", help="Path to workspace.json")
    excel_update_parser.add_argument("--path", help="Path to media plan in workspace storage")
    excel_update_parser.add_argument("--campaign-id", help="Campaign ID to load from workspace storage")
    excel_update_parser.add_argument("--output", help="Output path for updated JSON file")

    # excel validate
    excel_validate_parser = excel_subparsers.add_parser("validate", help="Validate Excel file against schema")
    excel_validate_parser.add_argument("file", help="Path to Excel file")
    excel_validate_parser.add_argument("--version", help="Schema version to validate against")
    excel_validate_parser.add_argument("--report", help="Output path for validation report")

    # Media plan commands (add this new section after excel commands)
    mediaplan_parser = subparsers.add_parser("mediaplan", help="Media plan operations")
    mediaplan_subparsers = mediaplan_parser.add_subparsers(dest="mediaplan_command")

    # mediaplan delete
    delete_parser = mediaplan_subparsers.add_parser("delete", help="Delete a media plan from storage")
    delete_parser.add_argument("--workspace", help="Path to workspace.json")
    delete_parser.add_argument("--media-plan-id", required=True, help="Media plan ID to delete")
    delete_parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")

    return parser

def handle_workspace_init(args):
    """Handle the 'workspace init' command."""
    try:
        manager = WorkspaceManager()
        workspace_id, settings_path = manager.create(
            settings_path_name=os.path.dirname(args.path) if args.path != "./workspace.json" else None,
            settings_file_name=os.path.basename(args.path) if args.path != "./workspace.json" else None,
            overwrite=args.force
        )
        config = manager.config
        print(f"✅ Created workspace '{config['workspace_name']}' with ID '{workspace_id}' at {settings_path}")
        print(f"Storage mode: {config['storage']['mode']}")
        if config['storage']['mode'] == 'local':
            print(f"Local storage path: {config['storage']['local']['base_path']}")
        print(f"Schema settings:")
        print(f"  Preferred version: {config['schema_settings']['preferred_version']}")
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

        print("\nSchema Settings:")
        schema_settings = resolved.get('schema_settings', {})
        print(f"  Preferred Version: {schema_settings.get('preferred_version', 'v1.0.0')}")
        print(f"  Auto Migrate: {schema_settings.get('auto_migrate', False)}")

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


def handle_schema_info(args):
    """Handle the 'schema info' command."""
    try:
        # Load workspace if specified
        if args.workspace:
            manager = WorkspaceManager(args.workspace)
            manager.load()
            registry = manager.schema_registry
        else:
            # Use default registry
            registry = SchemaRegistry()

        # Get schema information
        current_version = registry.get_current_version()
        supported_versions = registry.get_supported_versions()

        print(f"Schema Information:")
        print(f"  Current Version: {current_version}")
        print(f"  Supported Versions: {', '.join(supported_versions)}")
        print(f"  Schemas: Bundled with SDK")

    except (WorkspaceError, SchemaError) as e:
        print(f"❌ Error getting schema information: {e}")
        return 1
    return 0


def handle_schema_versions(args):
    """Handle the 'schema versions' command."""
    try:
        # Load workspace if specified
        if args.workspace:
            manager = WorkspaceManager(args.workspace)
            manager.load()
            registry = manager.schema_registry
        else:
            # Use default registry
            registry = SchemaRegistry()

        # Get versions
        versions_info = registry.load_versions_info()

        print(f"Schema Versions:")
        print(f"  Current: {versions_info.get('current')}")
        print(f"  Supported: {', '.join(versions_info.get('supported', []))}")
        if 'deprecated' in versions_info and versions_info['deprecated']:
            print(f"  Deprecated: {', '.join(versions_info.get('deprecated', []))}")
        if 'description' in versions_info:
            print(f"  Description: {versions_info['description']}")

    except (WorkspaceError, SchemaError) as e:
        print(f"❌ Error getting schema versions: {e}")
        return 1
    return 0


def handle_schema_validate(args):
    """Handle the 'schema validate' command."""
    try:
        # Load workspace if specified
        if args.workspace:
            manager = WorkspaceManager(args.workspace)
            manager.load()
            validator = manager.schema_validator
        else:
            # Use default validator
            validator = SchemaValidator()

        # Validate the file
        errors = validator.validate_file(args.file, args.version)

        if not errors:
            print(f"✅ Media plan '{args.file}' is valid")
        else:
            print(f"❌ Media plan validation failed with {len(errors)} errors:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
            return 1

    except (WorkspaceError, SchemaError, ValidationError) as e:
        print(f"❌ Error validating media plan: {e}")
        return 1
    return 0


def handle_schema_migrate(args):
    """Handle the 'schema migrate' command."""
    try:
        # Load workspace if specified
        if args.workspace:
            manager = WorkspaceManager(args.workspace)
            manager.load()
            migrator = manager.schema_migrator
        else:
            # Use default migrator
            migrator = SchemaMigrator()

        # Load the media plan
        with open(args.file, 'r') as f:
            media_plan = json.load(f)

        # Get source version
        from_version = media_plan.get("meta", {}).get("schema_version")
        if not from_version:
            print(f"❌ Media plan does not specify a schema version")
            return 1

        # Get target version
        to_version = args.to_version
        if not to_version:
            # If no target version specified, use current version
            to_version = migrator.registry.get_current_version()

        # Migrate the media plan
        migrated_plan = migrator.migrate(media_plan, from_version, to_version)

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            # Default to input file name with version suffix
            input_path = Path(args.file)
            output_path = input_path.with_stem(f"{input_path.stem}_{to_version}")

        # Write the migrated plan
        with open(output_path, 'w') as f:
            json.dump(migrated_plan, f, indent=2)

        print(f"✅ Migrated media plan from {from_version} to {to_version}")
        print(f"  Output saved to: {output_path}")

    except (WorkspaceError, SchemaError, ValidationError) as e:
        print(f"❌ Error migrating media plan: {e}")
        return 1
    return 0


def handle_excel_export(args):
    """Handle the 'excel export' command."""
    try:
        from mediaplanpy.models import MediaPlan

        # Load the media plan from file
        if args.file:
            media_plan = MediaPlan.import_from_json(args.file)
        elif args.path and args.workspace:
            # Load workspace
            manager = WorkspaceManager(args.workspace)
            manager.load()

            # Load from storage
            media_plan = MediaPlan.load(manager, path=args.path)
        elif args.campaign_id and args.workspace:
            # Load workspace
            manager = WorkspaceManager(args.workspace)
            manager.load()

            # Load by campaign ID
            media_plan = MediaPlan.load(manager, campaign_id=args.campaign_id)
        else:
            print("❌ Error: You must specify either --file, or both --workspace and (--path or --campaign-id)")
            return 1

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            # Default to campaign ID
            output_path = f"{media_plan.campaign.id}.xlsx"

        # Export to Excel
        if args.workspace:
            # Use workspace-based export
            manager = WorkspaceManager(args.workspace)
            manager.load()

            result_path = media_plan.export_to_excel(
                manager,
                path=output_path,
                template_path=args.template,
                include_documentation=not args.no_docs
            )
        else:
            # Use direct export
            result_path = media_plan.export_to_excel_path(
                path=output_path,
                template_path=args.template,
                include_documentation=not args.no_docs
            )

        print(f"✅ Media plan exported to Excel: {result_path}")
        return 0

    except Exception as e:
        print(f"❌ Error exporting media plan to Excel: {e}")
        return 1


def handle_excel_import(args):
    """Handle the 'excel import' command."""
    try:
        from mediaplanpy.models import MediaPlan

        # Import from Excel
        media_plan = MediaPlan.import_from_excel_path(args.file)

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            # Default to campaign ID
            output_path = f"{media_plan.campaign.id}.json"

        # Save the media plan
        if args.workspace:
            # Use workspace-based save
            manager = WorkspaceManager(args.workspace)
            manager.load()

            result_path = media_plan.save(manager, path=output_path)
        else:
            # Use direct save
            media_plan.export_to_json(output_path)
            result_path = output_path

        print(f"✅ Media plan imported from Excel and saved to: {result_path}")
        return 0

    except Exception as e:
        print(f"❌ Error importing media plan from Excel: {e}")
        return 1


def handle_excel_update(args):
    """Handle the 'excel update' command."""
    try:
        from mediaplanpy.models import MediaPlan

        # Load the media plan from file
        if args.target:
            media_plan = MediaPlan.import_from_json(args.target)
        elif args.path and args.workspace:
            # Load workspace
            manager = WorkspaceManager(args.workspace)
            manager.load()

            # Load from storage
            media_plan = MediaPlan.load(manager, path=args.path)
        elif args.campaign_id and args.workspace:
            # Load workspace
            manager = WorkspaceManager(args.workspace)
            manager.load()

            # Load by campaign ID
            media_plan = MediaPlan.load(manager, campaign_id=args.campaign_id)
        else:
            print("❌ Error: You must specify either --target, or both --workspace and (--path or --campaign-id)")
            return 1

        # Update from Excel
        media_plan.update_from_excel(args.file)

        # Determine output path
        if args.output:
            output_path = args.output
        elif args.target:
            # Use the same file
            output_path = args.target
        else:
            # Default to campaign ID
            output_path = f"{media_plan.campaign.id}.json"

        # Save the updated media plan
        if args.workspace:
            # Use workspace-based save
            manager = WorkspaceManager(args.workspace)
            manager.load()

            result_path = media_plan.save(manager, path=output_path)
        else:
            # Use direct save
            media_plan.export_to_json(output_path)
            result_path = output_path

        print(f"✅ Media plan updated from Excel and saved to: {result_path}")
        return 0

    except Exception as e:
        print(f"❌ Error updating media plan from Excel: {e}")
        return 1


def handle_excel_validate(args):
    """Handle the 'excel validate' command."""
    try:
        from mediaplanpy.models import MediaPlan
        from mediaplanpy.excel.validator import create_validation_report

        # Validate Excel file
        errors = MediaPlan.validate_excel(args.file, schema_version=args.version)

        if errors:
            print(f"❌ Excel file validation failed with {len(errors)} errors:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")

            # Create validation report if requested
            if args.report:
                report_path = create_validation_report(args.file, errors, args.report)
                print(f"Validation report saved to: {report_path}")

            return 1
        else:
            print(f"✅ Excel file validated successfully: {args.file}")

            # Create validation report if requested
            if args.report:
                report_path = create_validation_report(args.file, [], args.report)
                print(f"Validation report saved to: {report_path}")

            return 0

    except Exception as e:
        print(f"❌ Error validating Excel file: {e}")
        return 1


def handle_mediaplan_delete(args):
    """Handle the 'mediaplan delete' command."""
    try:
        from mediaplanpy.models import MediaPlan

        # Load workspace
        if args.workspace:
            manager = WorkspaceManager(args.workspace)
            manager.load()
        else:
            manager = WorkspaceManager()
            manager.load()

        # Load the media plan
        try:
            media_plan = MediaPlan.load(manager, media_plan_id=args.media_plan_id)
        except Exception as e:
            print(f"❌ Error loading media plan '{args.media_plan_id}': {e}")
            return 1

        # Perform deletion
        result = media_plan.delete(manager, dry_run=args.dry_run)

        # Display results
        if args.dry_run:
            print(f"🔍 DRY RUN - Media plan '{result['mediaplan_id']}':")
            if result['deleted_files']:
                print(f"   Would delete {len(result['deleted_files'])} file(s):")
                for file_path in result['deleted_files']:
                    print(f"     - {file_path}")
            else:
                print("   No files found to delete")
        else:
            print(f"✅ Media plan '{result['mediaplan_id']}' deletion completed:")
            print(f"   Files found: {result['files_found']}")
            print(f"   Files deleted: {result['files_deleted']}")
            if result['deleted_files']:
                print("   Deleted files:")
                for file_path in result['deleted_files']:
                    print(f"     - {file_path}")

        if result['errors']:
            print(f"⚠️  Errors encountered:")
            for error in result['errors']:
                print(f"     - {error}")
            return 1

        return 0

    except Exception as e:
        print(f"❌ Error deleting media plan: {e}")
        return 1


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

    # Handle schema commands
    elif args.command == "schema":
        if not args.schema_command:
            # If no schema subcommand, print schema help
            for action in parser._actions:
                if action.dest == 'schema_command':
                    action.choices['info'].print_help()
                    return 1

        if args.schema_command == "info":
            return handle_schema_info(args)
        elif args.schema_command == "versions":
            return handle_schema_versions(args)
        elif args.schema_command == "validate":
            return handle_schema_validate(args)
        elif args.schema_command == "migrate":
            return handle_schema_migrate(args)

    # Handle excel commands
    elif args.command == "excel":
        if not args.excel_command:
            # If no excel subcommand, print excel help
            for action in parser._actions:
                if action.dest == 'excel_command':
                    action.choices['export'].print_help()
                    return 1

        if args.excel_command == "export":
            return handle_excel_export(args)
        elif args.excel_command == "import":
            return handle_excel_import(args)
        elif args.excel_command == "update":
            return handle_excel_update(args)
        elif args.excel_command == "validate":
            return handle_excel_validate(args)

    # Handle mediaplan commands (add this after excel commands)
    elif args.command == "mediaplan":
        if not args.mediaplan_command:
            # If no mediaplan subcommand, print mediaplan help
            for action in parser._actions:
                if action.dest == 'mediaplan_command':
                    action.choices['delete'].print_help()
                    return 1

        if args.mediaplan_command == "delete":
            return handle_mediaplan_delete(args)

    # If we reach here, no command was handled
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())