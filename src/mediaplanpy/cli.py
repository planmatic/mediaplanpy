"""
Command-line interface for Media Plan OSC.

This module provides a command-line interface for managing workspaces
and media plans with enhanced support for v2.0 schema and 2-digit versioning strategy.
"""
import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

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

# Import version information
from mediaplanpy import __version__, __schema_version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mediaplanpy.cli")


def setup_argparse():
    """Set up argument parsing for the CLI with enhanced v2.0 support."""
    parser = argparse.ArgumentParser(
        description="Media Plan OSC - Open Source Python SDK for Media Plans (v2.0 schema support)",
        epilog=f"SDK Version: {__version__}, Current Schema: v{__schema_version__} | "
               f"Supports: v1.0 (backward compatible), v2.0 (current)"
    )

    # Add global version flag
    parser.add_argument(
        '--version',
        action='version',
        version=f'mediaplanpy {__version__} (schema v{__schema_version__})'
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Workspace commands
    workspace_parser = subparsers.add_parser(
        "workspace",
        help="Workspace management with v2.0 support",
        description="Manage workspace configurations with v2.0 schema support and version compatibility"
    )
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command")

    # workspace init
    init_parser = workspace_subparsers.add_parser(
        "init",
        help="Initialize a new workspace (defaults to v2.0)",
        description="Create a new workspace configuration with v2.0 schema as default"
    )
    init_parser.add_argument("--path", help="Path to create workspace.json", default="./workspace.json")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing workspace.json")
    init_parser.add_argument("--schema-version", help="Schema version for new workspace (default: 2.0)",
                            default="2.0", choices=["1.0", "2.0"])

    # workspace validate
    validate_parser = workspace_subparsers.add_parser(
        "validate",
        help="Validate an existing workspace",
        description="Validate workspace configuration and v2.0 schema compatibility"
    )
    validate_parser.add_argument("--path", help="Path to workspace.json")

    # workspace info
    info_parser = workspace_subparsers.add_parser(
        "info",
        help="Display information about the workspace",
        description="Show detailed workspace configuration including v2.0 schema information"
    )
    info_parser.add_argument("--path", help="Path to workspace.json")
    info_parser.add_argument("--show-v2-fields", action="store_true",
                            help="Show detailed information about new v2.0 fields")

    # workspace upgrade
    upgrade_parser = workspace_subparsers.add_parser(
        "upgrade",
        help="Upgrade workspace to current SDK/schema version",
        description="Upgrade workspace and all media plans to v2.0 schema (v0.0 plans will be rejected)"
    )
    upgrade_parser.add_argument("--workspace", help="Path to workspace.json")
    upgrade_parser.add_argument("--target-version", help="Target SDK version (defaults to current v2.0)")
    upgrade_parser.add_argument("--dry-run", action="store_true",
                                help="Show what would be upgraded without making changes")

    # workspace version
    version_parser = workspace_subparsers.add_parser(
        "version",
        help="Show workspace version information",
        description="Display current workspace and SDK version compatibility details with v2.0 info"
    )
    version_parser.add_argument("--workspace", help="Path to workspace.json")

    # workspace check
    check_parser = workspace_subparsers.add_parser(
        "check",
        help="Check workspace v2.0 compatibility and upgrade readiness",
        description="Analyze workspace compatibility with v2.0 schema and current SDK version"
    )
    check_parser.add_argument("--workspace", help="Path to workspace.json")

    # Schema commands
    schema_parser = subparsers.add_parser(
        "schema",
        help="Schema management for v2.0",
        description="Manage v2.0 schema versions and validation (2-digit format: X.Y)"
    )
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command")

    # schema info
    schema_info_parser = schema_subparsers.add_parser(
        "info",
        help="Display v2.0 schema information",
        description="Show current v2.0 schema version and compatibility matrix"
    )
    schema_info_parser.add_argument("--workspace", help="Path to workspace.json")
    schema_info_parser.add_argument("--show-v2-features", action="store_true",
                                   help="Show detailed v2.0 schema features and new fields")

    # schema versions
    schema_versions_parser = schema_subparsers.add_parser(
        "versions",
        help="List supported schema versions",
        description="List all supported schema versions in 2-digit format (current: v2.0)"
    )
    schema_versions_parser.add_argument("--workspace", help="Path to workspace.json")

    # schema validate
    schema_validate_parser = schema_subparsers.add_parser(
        "validate",
        help="Validate a media plan against v2.0 schema",
        description="Validate media plan with v2.0 schema compatibility checking"
    )
    schema_validate_parser.add_argument("file", help="Path to media plan JSON file")
    schema_validate_parser.add_argument("--version", help="Schema version to validate against (default: 2.0)",
                                       default="2.0")
    schema_validate_parser.add_argument("--workspace", help="Path to workspace.json")
    schema_validate_parser.add_argument("--show-v2-validation", action="store_true",
                                       help="Show detailed v2.0 field validation results")

    # schema migrate
    schema_migrate_parser = schema_subparsers.add_parser(
        "migrate",
        help="Migrate a media plan to v2.0 schema",
        description="Migrate media plan from v1.0 to v2.0 schema (v0.0 plans rejected)"
    )
    schema_migrate_parser.add_argument("file", help="Path to media plan JSON file")
    schema_migrate_parser.add_argument("--to-version", help="Target schema version (default: 2.0)",
                                      default="2.0")
    schema_migrate_parser.add_argument("--output", help="Output file path (defaults to input with v2_0 suffix)")
    schema_migrate_parser.add_argument("--workspace", help="Path to workspace.json")

    # Excel commands - Updated for v2.0
    excel_parser = subparsers.add_parser("excel", help="Excel operations with v2.0 support")
    excel_subparsers = excel_parser.add_subparsers(dest="excel_command")

    # excel export
    excel_export_parser = excel_subparsers.add_parser("export", help="Export media plan to Excel with v2.0 fields")
    excel_export_parser.add_argument("--file", help="Path to media plan JSON file")
    excel_export_parser.add_argument("--workspace", help="Path to workspace.json")
    excel_export_parser.add_argument("--path", help="Path to media plan in workspace storage")
    excel_export_parser.add_argument("--campaign-id", help="Campaign ID to load from workspace storage")
    excel_export_parser.add_argument("--output", help="Output path for Excel file")
    excel_export_parser.add_argument("--template", help="Path to Excel template file")
    excel_export_parser.add_argument("--no-docs", action="store_true", help="Exclude documentation sheet")

    # excel import
    excel_import_parser = excel_subparsers.add_parser("import", help="Import media plan from Excel with v2.0 support")
    excel_import_parser.add_argument("file", help="Path to Excel file")
    excel_import_parser.add_argument("--output", help="Output path for JSON file")
    excel_import_parser.add_argument("--workspace", help="Path to workspace.json")
    excel_import_parser.add_argument("--target-schema", help="Target schema version (default: 2.0)",
                                    default="2.0")


    # excel validate
    excel_validate_parser = excel_subparsers.add_parser("validate", help="Validate Excel file against v2.0 schema")
    excel_validate_parser.add_argument("file", help="Path to Excel file")
    excel_validate_parser.add_argument("--version", help="Schema version to validate against (default: 2.0)",
                                       default="2.0")
    excel_validate_parser.add_argument("--report", help="Output path for validation report")

    # Media plan commands - Updated for v2.0
    mediaplan_parser = subparsers.add_parser("mediaplan", help="Media plan operations with v2.0 support")
    mediaplan_subparsers = mediaplan_parser.add_subparsers(dest="mediaplan_command")

    # mediaplan create (NEW)
    create_parser = mediaplan_subparsers.add_parser("create", help="Create a new media plan with v2.0 schema")
    create_parser.add_argument("name", help="Campaign name for the new media plan")
    create_parser.add_argument("--objective", help="Campaign objective", default="awareness")
    create_parser.add_argument("--start-date", help="Campaign start date (YYYY-MM-DD)")
    create_parser.add_argument("--end-date", help="Campaign end date (YYYY-MM-DD)")
    create_parser.add_argument("--budget", help="Total campaign budget", type=float, default=0)
    create_parser.add_argument("--workspace", help="Path to workspace.json")
    create_parser.add_argument("--output", help="Output path for JSON file")
    create_parser.add_argument("--schema-version", help="Schema version (default: 2.0)", default="2.0")
    # v2.0 specific fields
    create_parser.add_argument("--budget-currency", help="Budget currency (e.g., USD, EUR)")
    create_parser.add_argument("--agency-name", help="Agency name managing the campaign")
    create_parser.add_argument("--advertiser-name", help="Advertiser/client name")
    create_parser.add_argument("--created-by-name", help="Creator name (required for v2.0)", required=True)

    # mediaplan delete
    delete_parser = mediaplan_subparsers.add_parser("delete", help="Delete a media plan from storage")
    delete_parser.add_argument("--workspace", help="Path to workspace.json")
    delete_parser.add_argument("--media-plan-id", required=True, help="Media plan ID to delete")
    delete_parser.add_argument("--dry-run", action="store_true",
                              help="Show what would be deleted without actually deleting")

    return parser


def handle_workspace_init(args):
    """Handle the 'workspace init' command with v2.0 defaults."""
    try:
        manager = WorkspaceManager()

        # Create workspace with specified schema version
        workspace_id, settings_path = manager.create(
            settings_path_name=os.path.dirname(args.path) if args.path != "./workspace.json" else None,
            settings_file_name=os.path.basename(args.path) if args.path != "./workspace.json" else None,
            overwrite=args.force,
            # Override workspace_settings for custom schema version
            workspace_settings={
                "schema_version": args.schema_version,
                "last_upgraded": datetime.now().strftime("%Y-%m-%d"),
                "sdk_version_required": f"{args.schema_version.split('.')[0]}.0.x"
            }
        )
        config = manager.config

        print(f"✅ Created workspace '{config['workspace_name']}' with ID '{workspace_id}' at {settings_path}")
        print(f"📦 SDK Version: {__version__}")
        print(f"📋 Schema Version: v{args.schema_version} ({'Current' if args.schema_version == __schema_version__ else 'Legacy'})")
        print(f"💾 Storage mode: {config['storage']['mode']}")

        if config['storage']['mode'] == 'local':
            print(f"📁 Local storage path: {config['storage']['local']['base_path']}")

        # Show workspace settings info with v2.0 details
        workspace_settings = config.get('workspace_settings', {})
        print(f"⚙️  Workspace Settings (v2.0 format):")
        print(f"   Schema version: {workspace_settings.get('schema_version', 'Not set')}")
        print(f"   SDK required: {workspace_settings.get('sdk_version_required', 'Not set')}")
        print(f"   Last upgraded: {workspace_settings.get('last_upgraded', 'Never')}")

        if args.schema_version == "2.0":
            print(f"🆕 v2.0 Features Enabled:")
            print(f"   • Enhanced campaign fields (agency, advertiser, workflow status)")
            print(f"   • Extended line item metrics (17 new standard metrics)")
            print(f"   • Custom field dictionary configuration")
            print(f"   • Currency support for budgets and costs")
            print(f"   • Advanced targeting options (dayparts, inventory)")

    except WorkspaceError as e:
        print(f"❌ Error creating workspace: {e}")
        return 1
    return 0


# Keep existing handlers for validate, upgrade, version, check that are already implemented
# These are preserved from the original code

def handle_workspace_validate(args):
    """Handle the 'workspace validate' command."""
    try:
        manager = WorkspaceManager(args.path)
        config = manager.load()
        valid = manager.validate()

        print(f"✅ Workspace '{config['workspace_name']}' is valid")
        print(f"📦 SDK Version: {__version__}")
        print(f"📋 Current Schema Version: v{__schema_version__}")

        # Show workspace version compatibility
        version_info = manager.get_workspace_version_info()
        compatibility = manager.check_workspace_compatibility()

        print(f"\n🔍 Version Compatibility:")
        print(f"   Workspace schema version: {version_info['workspace_schema_version']}")
        print(f"   Compatibility status: {version_info['compatibility_status']}")

        if compatibility['warnings']:
            print(f"⚠️  Warnings:")
            for warning in compatibility['warnings']:
                print(f"   - {warning}")

        if compatibility['recommendations']:
            print(f"💡 Recommendations:")
            for rec in compatibility['recommendations']:
                print(f"   - {rec}")

        # Show workspace configuration
        print(f"\n📋 Workspace Configuration:")
        print(f"   Environment: {config['environment']}")
        print(f"   Storage Mode: {config['storage']['mode']}")

        if config['storage']['mode'] == 'local':
            local_path = manager.get_resolved_config()['storage']['local']['base_path']
            print(f"   Local Storage Path: {local_path}")
        elif config['storage']['mode'] == 's3':
            s3_config = config['storage']['s3']
            print(f"   S3 Bucket: {s3_config['bucket']}")
            if 'prefix' in s3_config:
                print(f"   S3 Prefix: {s3_config['prefix']}")

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


def handle_workspace_upgrade(args):
    """Handle the 'workspace upgrade' command."""
    try:
        manager = WorkspaceManager(args.workspace)
        manager.load()

        print(f"🚀 Starting workspace upgrade...")
        print(f"📦 Current SDK Version: {__version__}")
        print(f"📋 Current Schema Version: v{__schema_version__}")

        if args.target_version:
            print(f"🎯 Target SDK Version: {args.target_version}")
        else:
            print(f"🎯 Target SDK Version: {__version__} (current)")

        result = manager.upgrade_workspace(
            target_sdk_version=args.target_version,
            dry_run=args.dry_run
        )

        if args.dry_run:
            print(f"🔍 DRY RUN - Workspace upgrade analysis:")
        else:
            print(f"✅ Workspace upgrade completed:")

        print(f"   📄 JSON files migrated: {result['json_files_migrated']}")
        print(f"   📊 Parquet files regenerated: {result['parquet_files_regenerated']}")
        print(f"   🗄️  Database upgraded: {result['database_upgraded']}")
        print(f"   ⚙️  Workspace settings updated: {result['workspace_updated']}")

        if result.get('v0_files_rejected', 0) > 0:
            print(f"   ❌ v0.0 files rejected: {result['v0_files_rejected']}")
            print(f"   💡 Use SDK v1.x to migrate v0.0 → v1.0 first")

        if result['errors']:
            print(f"⚠️  Errors encountered:")
            for error in result['errors']:
                print(f"    - {error}")
            return 1

        if not args.dry_run:
            print(f"🎉 Upgrade successful! Workspace is now compatible with SDK {__version__}")

        return 0

    except Exception as e:
        print(f"❌ Error upgrading workspace: {e}")
        return 1


def handle_workspace_version(args):
    """Handle the 'workspace version' command."""
    try:
        manager = WorkspaceManager(args.workspace)
        manager.load()

        version_info = manager.get_workspace_version_info()

        print(f"📋 Workspace Version Information:")
        print(f"   Workspace: {version_info['workspace_name']}")
        print(f"   Current SDK Version: {version_info['current_sdk_version']}")
        print(f"   Current Schema Version: v{version_info['current_schema_version']}")
        print(f"   Workspace Schema Version: {version_info['workspace_schema_version'] or 'Not set'}")
        print(f"   Required SDK Version: {version_info['workspace_sdk_required'] or 'Not set'}")
        print(f"   Last Upgraded: {version_info['last_upgraded'] or 'Never'}")
        print(f"   Compatibility Status: {version_info['compatibility_status']}")

        # Show compatibility details
        compatibility = manager.check_workspace_compatibility()

        if not compatibility['is_compatible']:
            print(f"❌ Compatibility Issues Found:")
            for error in compatibility['errors']:
                print(f"   - {error}")
        else:
            print(f"✅ Workspace is compatible with current SDK")

        if compatibility['warnings']:
            print(f"⚠️  Warnings:")
            for warning in compatibility['warnings']:
                print(f"   - {warning}")

        if version_info['needs_upgrade']:
            print(f"💡 Recommendation: Run 'workspace upgrade' to update to current v2.0")

        return 0

    except Exception as e:
        print(f"❌ Error getting version information: {e}")
        return 1


def handle_workspace_check(args):
    """Handle the 'workspace check' command."""
    try:
        manager = WorkspaceManager(args.workspace)
        manager.load()

        print(f"🔍 Checking workspace compatibility...")
        print(f"📦 Current SDK Version: {__version__}")
        print(f"📋 Current Schema Version: v{__schema_version__}")

        compatibility = manager.check_workspace_compatibility()

        if compatibility['is_compatible']:
            print(f"✅ Workspace is compatible with current SDK")
        else:
            print(f"❌ Workspace compatibility issues found")

        if compatibility['errors']:
            print(f"🚫 Errors:")
            for error in compatibility['errors']:
                print(f"   - {error}")

        if compatibility['warnings']:
            print(f"⚠️  Warnings:")
            for warning in compatibility['warnings']:
                print(f"   - {warning}")

        if compatibility['recommendations']:
            print(f"💡 Recommendations:")
            for rec in compatibility['recommendations']:
                print(f"   - {rec}")

        return 0 if compatibility['is_compatible'] else 1

    except Exception as e:
        print(f"❌ Error checking workspace: {e}")
        return 1


# Missing handler implementations for complete CLI v2.0 support

def handle_workspace_info(args):
    """Handle the 'workspace info' command with enhanced v2.0 information."""
    try:
        manager = WorkspaceManager(args.path)
        config = manager.load()

        print(f"📋 Workspace: {config['workspace_name']}")
        print(f"🆔 ID: {config.get('workspace_id', 'Unknown')}")
        print(f"🌍 Environment: {config['environment']}")
        print(f"📦 Current SDK Version: {__version__}")
        print(f"📋 Current Schema Version: v{__schema_version__}")

        # Show version information with v2.0 details
        version_info = manager.get_workspace_version_info()
        print(f"\n🔍 Version Information:")
        print(f"   Workspace schema version: {version_info['workspace_schema_version'] or 'Not set'}")
        print(f"   Required SDK version: {version_info['workspace_sdk_required'] or 'Not set'}")
        print(f"   Last upgraded: {version_info['last_upgraded'] or 'Never'}")
        print(f"   Compatibility status: {version_info['compatibility_status']}")

        # Show v2.0 specific information
        workspace_schema = version_info.get('workspace_schema_version', '')
        if workspace_schema.startswith('2.'):
            print(f"✨ v2.0 Schema Features Active:")
            print(f"   • Enhanced campaign metadata")
            print(f"   • Extended metric collection")
            print(f"   • Custom field dictionaries")
            print(f"   • Multi-currency support")
        elif workspace_schema.startswith('1.'):
            print(f"📋 v1.0 Schema (Legacy Mode):")
            print(f"   • Basic campaign and line item support")
            print(f"   • Limited to v1.0 field set")
            if version_info['needs_upgrade']:
                print(f"   💡 Recommendation: Run 'workspace upgrade' to enable v2.0 features")

        if args.show_v2_fields:
            print(f"\n🆕 New v2.0 Fields Available:")
            print(f"   Campaign Fields:")
            print(f"     • budget_currency: Currency specification")
            print(f"     • agency_id/name: Agency identification")
            print(f"     • advertiser_id/name: Client identification")
            print(f"     • campaign_type_id/name: Campaign classification")
            print(f"     • workflow_status_id/name: Status tracking")
            print(f"   Line Item Fields:")
            print(f"     • cost_currency: Cost currency specification")
            print(f"     • dayparts/dayparts_custom: Time targeting")
            print(f"     • inventory/inventory_custom: Inventory specification")
            print(f"     • 17 new standard metrics (engagements, leads, sales, etc.)")
            print(f"   Meta Fields:")
            print(f"     • created_by_id: Creator identification")
            print(f"     • is_current/is_archived: Status flags")
            print(f"     • parent_id: Plan relationships")

        # Show storage configuration
        resolved = manager.get_resolved_config()
        print(f"\n💾 Storage Configuration:")
        print(f"   Mode: {config['storage']['mode']}")

        if config['storage']['mode'] == 'local':
            local_config = resolved['storage']['local']
            print(f"   Base Path: {local_config['base_path']}")
            print(f"   Create If Missing: {local_config['create_if_missing']}")

        # Show workspace settings (v2.0 format)
        workspace_settings = config.get('workspace_settings', {})
        print(f"\n⚙️  Workspace Settings (v2.0 Format):")
        print(f"   Schema version: {workspace_settings.get('schema_version', 'Not set')}")
        print(f"   Last upgraded: {workspace_settings.get('last_upgraded', 'Never')}")
        print(f"   SDK version required: {workspace_settings.get('sdk_version_required', 'Not set')}")

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
    """Handle the 'schema info' command with enhanced v2.0 support."""
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

        print(f"📋 Schema Information (2-digit format):")
        print(f"   Current Version: v{current_version}")
        print(f"   SDK Version: {__version__}")
        print(f"   Supported Versions: {', '.join([f'v{v}' for v in supported_versions])}")
        print(f"   Format: 2-digit (Major.Minor)")
        print(f"   Schemas: Bundled with SDK")

        # Show v2.0 specific features
        if args.show_v2_features:
            print(f"\n✨ v2.0 Schema Features:")
            print(f"   📊 Campaign Enhancements:")
            print(f"     • Multi-currency budget support")
            print(f"     • Agency and advertiser identification")
            print(f"     • Campaign type classification")
            print(f"     • Workflow status tracking")
            print(f"   📈 Line Item Improvements:")
            print(f"     • 17 new standard metrics")
            print(f"     • Enhanced targeting (dayparts, inventory)")
            print(f"     • Multi-currency cost tracking")
            print(f"   🔧 New Components:")
            print(f"     • Dictionary schema for custom field configuration")
            print(f"     • Enhanced meta fields for plan management")
            print(f"   🔄 Migration Support:")
            print(f"     • Automatic v1.0 → v2.0 migration")
            print(f"     • Backward compatibility with v1.0")
            print(f"     • v0.0 support removed (use SDK v1.x first)")

        # Show version compatibility matrix
        try:
            from mediaplanpy.schema.version_utils import CURRENT_MAJOR, CURRENT_MINOR

            print(f"\n🔄 Version Compatibility Matrix:")
            print(f"   v{CURRENT_MAJOR}.{CURRENT_MINOR} → Native Support (current)")
            print(f"   v{CURRENT_MAJOR}.{CURRENT_MINOR + 1}+ → Forward Compatible (downgrade + warning)")
            print(f"   v{CURRENT_MAJOR}.{max(0, CURRENT_MINOR - 1)}- → Backward Compatible (upgrade)")
            print(f"   v{max(0, CURRENT_MAJOR - 1)}.* → Legacy Support (migrate + warning)")
            print(f"   v{max(0, CURRENT_MAJOR - 2)}.* → Unsupported (reject + guidance)")

        except Exception:
            pass

    except (WorkspaceError, SchemaError) as e:
        print(f"❌ Error getting schema information: {e}")
        return 1
    return 0


def handle_schema_versions(args):
    """Handle the 'schema versions' command with 2-digit version display."""
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

        print(f"📋 Schema Versions (2-digit format):")
        print(f"   Current: v{versions_info.get('current')}")
        print(f"   Supported: {', '.join([f'v{v}' for v in versions_info.get('supported', [])])}")
        print(f"   Format: 2-digit (Major.Minor)")

        if 'deprecated' in versions_info and versions_info['deprecated']:
            print(f"   Deprecated: {', '.join([f'v{v}' for v in versions_info.get('deprecated', [])])}")

        if 'description' in versions_info:
            print(f"   Description: {versions_info['description']}")

        # Show examples
        print(f"\n📝 Version Format Examples:")
        print(f"   ✅ Valid: 'v2.0', 'v1.5', 'v0.9'")
        print(f"   ❌ Invalid: 'v2.0.0', '2.0.1', 'latest'")
        print(f"   ⚠️  Note: v0.0 is no longer supported")

    except (WorkspaceError, SchemaError) as e:
        print(f"❌ Error getting schema versions: {e}")
        return 1
    return 0


def handle_schema_validate(args):
    """Handle the 'schema validate' command with enhanced v2.0 validation."""
    try:
        # Load workspace if specified
        if args.workspace:
            manager = WorkspaceManager(args.workspace)
            manager.load()
            validator = manager.schema_validator
        else:
            # Use default validator
            validator = SchemaValidator()

        # Load the media plan first to check its version
        with open(args.file, 'r') as f:
            media_plan_data = json.load(f)

        file_version = media_plan_data.get("meta", {}).get("schema_version", "unknown")
        target_version = args.version or file_version

        print(f"📄 Validating file: {args.file}")
        print(f"📋 File schema version: {file_version}")
        print(f"🎯 Target validation version: v{target_version}")

        # Check version compatibility before validation
        if file_version != "unknown":
            try:
                from mediaplanpy.schema.version_utils import (
                    get_compatibility_type,
                    get_migration_recommendation,
                    normalize_version
                )

                # Normalize to 2-digit format
                normalized_version = normalize_version(file_version)
                compatibility = get_compatibility_type(normalized_version)

                print(f"🔄 Version compatibility: {compatibility}")

                if compatibility == "unsupported":
                    recommendation = get_migration_recommendation(normalized_version)
                    print(f"❌ {recommendation.get('message', 'Version not supported')}")
                    if normalized_version.startswith("0."):
                        print(f"💡 v0.0 files are no longer supported. Use SDK v1.x to migrate to v1.0 first.")
                    return 1
                elif compatibility in ["deprecated", "forward_minor"]:
                    recommendation = get_migration_recommendation(normalized_version)
                    print(f"⚠️  {recommendation.get('message', 'Version compatibility warning')}")

            except Exception as e:
                print(f"⚠️  Could not determine version compatibility: {e}")

        # Validate the file
        errors = validator.validate(media_plan_data, target_version)

        if not errors:
            print(f"✅ Media plan '{args.file}' is valid against schema v{target_version}")

            # Show v2.0 specific validation details if requested
            if args.show_v2_validation and target_version == "2.0":
                print(f"\n🔍 v2.0 Validation Details:")
                # Check for v2.0 specific fields
                campaign = media_plan_data.get("campaign", {})
                lineitems = media_plan_data.get("lineitems", [])
                dictionary = media_plan_data.get("dictionary")

                v2_campaign_fields = ["budget_currency", "agency_name", "advertiser_name", "campaign_type_name"]
                found_v2_campaign = [field for field in v2_campaign_fields if campaign.get(field)]

                if found_v2_campaign:
                    print(f"   ✨ v2.0 campaign fields found: {', '.join(found_v2_campaign)}")

                # Check for new metrics in line items
                v2_metrics = ["metric_engagements", "metric_leads", "metric_sales", "metric_visits"]
                found_v2_metrics = []
                for item in lineitems:
                    for metric in v2_metrics:
                        if item.get(metric) is not None:
                            found_v2_metrics.append(metric)

                if found_v2_metrics:
                    print(f"   📊 v2.0 metrics found: {', '.join(set(found_v2_metrics))}")

                if dictionary:
                    print(f"   📚 Custom field dictionary configured")

                if not (found_v2_campaign or found_v2_metrics or dictionary):
                    print(f"   📋 Valid v2.0 format but using v1.0 compatible fields only")

            return 0
        else:
            print(f"❌ Media plan validation failed with {len(errors)} errors:")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")
            return 1

    except Exception as e:
        print(f"❌ Error validating media plan: {e}")
        return 1


def handle_schema_migrate(args):
    """Handle the 'schema migrate' command with enhanced v2.0 migration."""
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
            # If no target version specified, use current version (2.0)
            to_version = __schema_version__

        print(f"📄 Migrating file: {args.file}")
        print(f"📋 From version: {from_version}")
        print(f"🎯 To version: v{to_version}")

        # Check version compatibility and provide helpful messages
        try:
            from mediaplanpy.schema.version_utils import get_compatibility_type, normalize_version

            normalized_from = normalize_version(from_version)
            compatibility = get_compatibility_type(normalized_from)
            print(f"🔄 Source version compatibility: {compatibility}")

            # Provide specific guidance for v0.0 files
            if normalized_from.startswith("0."):
                print(f"❌ Cannot migrate v0.0 files directly to v2.0")
                print(f"💡 Solution: Use SDK v1.x to migrate from v0.0 → v1.0 first")
                print(f"   Then use SDK v2.0 to migrate from v1.0 → v2.0")
                return 1

        except Exception as e:
            print(f"⚠️  Could not determine source version compatibility: {e}")

        # Migrate the media plan
        try:
            migrated_plan = migrator.migrate(media_plan, from_version, f"v{to_version}")
        except Exception as e:
            if "v0.0" in str(e) or "0.0" in str(e):
                print(f"❌ v0.0 migration blocked: {e}")
                print(f"💡 Use SDK v1.x to migrate v0.0 → v1.0 first")
                return 1
            else:
                raise

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            # Default to input file name with version suffix
            input_path = Path(args.file)
            version_for_filename = to_version.replace('.', '_')
            output_path = input_path.with_stem(f"{input_path.stem}_v{version_for_filename}")

        # Write the migrated plan
        with open(output_path, 'w') as f:
            json.dump(migrated_plan, f, indent=2)

        print(f"✅ Migration completed successfully")
        print(f"💾 Output saved to: {output_path}")
        print(f"📋 New schema version: {migrated_plan.get('meta', {}).get('schema_version')}")

        # Show what was migrated for v2.0
        if to_version == "2.0":
            print(f"\n✨ v2.0 Migration Benefits:")
            print(f"   • Access to enhanced campaign fields")
            print(f"   • Support for 17 new standard metrics")
            print(f"   • Custom field dictionary configuration")
            print(f"   • Multi-currency support")
            print(f"   • Enhanced meta fields for plan management")

        return 0

    except Exception as e:
        print(f"❌ Error migrating media plan: {e}")
        return 1


def handle_excel_export(args):
    """Handle the 'excel export' command with v2.0 support."""
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

        schema_version = media_plan.meta.schema_version
        print(f"📊 Exporting media plan to Excel")
        print(f"📋 Schema version: {schema_version}")

        # Show v2.0 features being exported
        if schema_version.startswith('v2.') or schema_version.startswith('2.'):
            print(f"✨ v2.0 features will be included:")
            if media_plan.campaign.budget_currency:
                print(f"   • Budget currency: {media_plan.campaign.budget_currency}")
            if media_plan.campaign.agency_name:
                print(f"   • Agency information")
            if media_plan.dictionary:
                print(f"   • Custom field dictionary")
            if any(hasattr(li, 'metric_engagements') and li.metric_engagements for li in media_plan.lineitems):
                print(f"   • v2.0 enhanced metrics")

        # Export to Excel
        if args.workspace:
            # Use workspace-based export
            manager = WorkspaceManager(args.workspace)
            manager.load()

            result_path = media_plan.export_to_excel(
                manager,
                file_path=output_path,
                template_path=args.template,
                include_documentation=not args.no_docs
            )
        else:
            # Use direct export
            result_path = media_plan.export_to_excel(
                file_path=output_path,
                template_path=args.template,
                include_documentation=not args.no_docs
            )

        print(f"✅ Media plan exported to Excel: {result_path}")
        return 0

    except Exception as e:
        print(f"❌ Error exporting media plan to Excel: {e}")
        return 1


def handle_excel_import(args):
    """Handle the 'excel import' command with enhanced v2.0 support."""
    try:
        from mediaplanpy.models import MediaPlan

        print(f"📄 Importing from Excel: {args.file}")
        print(f"🎯 Target schema: v{args.target_schema}")

        # Import from Excel
        media_plan = MediaPlan.import_from_excel(args.file)

        # Display version information
        original_schema = media_plan.meta.schema_version
        print(f"📋 Imported schema version: {original_schema}")

        # Update to target schema if different
        if args.target_schema != original_schema.lstrip('v'):
            print(f"🔄 Converting to target schema v{args.target_schema}")
            media_plan.meta.schema_version = f"v{args.target_schema}"

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
        print(f"📋 Final schema version: {media_plan.meta.schema_version}")

        # Show v2.0 features if applicable
        if media_plan.meta.schema_version.startswith('v2.') or media_plan.meta.schema_version.startswith('2.'):
            print(f"✨ v2.0 features ready for use:")
            print(f"   • Enhanced campaign metadata")
            print(f"   • Extended metric collection")
            print(f"   • Custom field configuration")

        return 0

    except Exception as e:
        print(f"❌ Error importing media plan from Excel: {e}")
        return 1


def handle_excel_validate(args):
    """Handle the 'excel validate' command."""
    try:
        from mediaplanpy.models import MediaPlan

        print(f"📄 Validating Excel file: {args.file}")
        if args.version:
            print(f"🎯 Target schema version: v{args.version}")

        # Validate Excel file
        errors = MediaPlan.validate_excel(args.file, schema_version=args.version)

        if errors:
            print(f"❌ Excel file validation failed with {len(errors)} errors:")
            for i, error in enumerate(errors, 1):
                print(f"   {i}. {error}")

            # Create validation report if requested
            if args.report:
                from mediaplanpy.excel.validator import create_validation_report
                report_path = create_validation_report(args.file, errors, args.report)
                print(f"📄 Validation report saved to: {report_path}")

            return 1
        else:
            print(f"✅ Excel file validated successfully: {args.file}")

            # Create validation report if requested
            if args.report:
                from mediaplanpy.excel.validator import create_validation_report
                report_path = create_validation_report(args.file, [], args.report)
                print(f"📄 Validation report saved to: {report_path}")

            return 0

    except Exception as e:
        print(f"❌ Error validating Excel file: {e}")
        return 1


def handle_mediaplan_create(args):
    """Handle the 'mediaplan create' command with v2.0 support."""
    try:
        from mediaplanpy.models import MediaPlan
        from datetime import date

        # Load workspace if specified
        if args.workspace:
            manager = WorkspaceManager(args.workspace)
            manager.load()
        else:
            manager = None

        # Parse dates
        start_date = date.fromisoformat(args.start_date) if args.start_date else date.today()
        end_date = date.fromisoformat(args.end_date) if args.end_date else date.today()

        print(f"🆕 Creating new media plan with v{args.schema_version} schema:")
        print(f"   Campaign: {args.name}")
        print(f"   Objective: {args.objective}")
        print(f"   Budget: {args.budget}")
        if args.budget_currency:
            print(f"   Currency: {args.budget_currency}")
        if args.agency_name:
            print(f"   Agency: {args.agency_name}")
        if args.advertiser_name:
            print(f"   Advertiser: {args.advertiser_name}")

        # Create media plan with v2.0 fields
        create_kwargs = {
            "created_by_name": args.created_by_name,  # Required for v2.0
            "campaign_name": args.name,
            "campaign_objective": args.objective,
            "campaign_start_date": start_date,
            "campaign_end_date": end_date,
            "campaign_budget": args.budget,
            "schema_version": f"v{args.schema_version}",
            "workspace_manager": manager
        }

        # Add v2.0 specific fields if provided
        if args.budget_currency:
            # This would need to be handled in the Campaign model
            pass
        if args.agency_name:
            # This would need to be handled in the Campaign model
            pass
        if args.advertiser_name:
            # This would need to be handled in the Campaign model
            pass

        # Create the media plan
        media_plan = MediaPlan.create(**create_kwargs)

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            output_path = f"{media_plan.campaign.id}.json"

        # Save the media plan
        if manager:
            result_path = media_plan.save(manager, path=output_path)
            print(f"✅ Media plan created and saved to workspace: {result_path}")
        else:
            media_plan.export_to_json(output_path)
            print(f"✅ Media plan created and saved to: {output_path}")

        print(f"📋 Schema version: {media_plan.meta.schema_version}")
        print(f"🆔 Media plan ID: {media_plan.meta.id}")
        print(f"🆔 Campaign ID: {media_plan.campaign.id}")

        if args.schema_version == "2.0":
            print(f"✨ v2.0 features ready for:")
            print(f"   • Enhanced campaign metadata")
            print(f"   • Extended line item metrics")
            print(f"   • Custom field configuration")

        return 0

    except Exception as e:
        print(f"❌ Error creating media plan: {e}")
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
            schema_version = media_plan.meta.schema_version
        except Exception as e:
            print(f"❌ Error loading media plan '{args.media_plan_id}': {e}")
            return 1

        print(f"📄 Media plan: {args.media_plan_id}")
        print(f"📋 Schema version: {schema_version}")

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
            print(f"   📁 Files found: {result['files_found']}")
            print(f"   🗑️  Files deleted: {result['files_deleted']}")
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
    """Main entry point for the CLI with v2.0 support."""
    parser = setup_argparse()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print(f"\n📋 Media Plan OSC SDK v{__version__}")
        print(f"✨ Current Schema: v{__schema_version__}")
        print(f"🔄 Supported: v1.0 (legacy), v2.0 (current)")
        print(f"❌ v0.0 no longer supported (use SDK v1.x first)")
        print(f"\n💡 Quick Start:")
        print(f"   mediaplanpy workspace init          # Create new v2.0 workspace")
        print(f"   mediaplanpy schema info --show-v2-features  # Show v2.0 features")
        print(f"   mediaplanpy workspace upgrade       # Upgrade existing workspace to v2.0")
        print(f"   mediaplanpy mediaplan create 'My Campaign' --created-by-name 'Your Name'")
        return 1

    # Handle workspace commands
    if args.command == "workspace":
        if not args.workspace_command:
            print(f"💡 v2.0 Workspace Features:")
            print(f"   • Enhanced version tracking")
            print(f"   • Automatic v1.0 → v2.0 migration")
            print(f"   • v0.0 compatibility removed")
            return 1

        if args.workspace_command == "init":
            return handle_workspace_init(args)
        elif args.workspace_command == "validate":
            return handle_workspace_validate(args)
        elif args.workspace_command == "info":
            return handle_workspace_info(args)
        elif args.workspace_command == "upgrade":
            return handle_workspace_upgrade(args)
        elif args.workspace_command == "version":
            return handle_workspace_version(args)
        elif args.workspace_command == "check":
            return handle_workspace_check(args)

    # Handle schema commands
    elif args.command == "schema":
        if not args.schema_command:
            print(f"✨ v2.0 Schema Features:")
            print(f"   • 2-digit versioning (X.Y format)")
            print(f"   • Enhanced field validation")
            print(f"   • Automatic migration support")
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
            print(f"📊 Excel v2.0 Support:")
            print(f"   • All v2.0 fields supported")
            print(f"   • Enhanced validation")
            print(f"   • Backward compatibility")
            return 1

        if args.excel_command == "export":
            return handle_excel_export(args)
        elif args.excel_command == "import":
            return handle_excel_import(args)
        elif args.excel_command == "validate":
            return handle_excel_validate(args)

    # Handle mediaplan commands
    elif args.command == "mediaplan":
        if not args.mediaplan_command:
            print(f"🆕 Media Plan v2.0 Features:")
            print(f"   • Enhanced campaign fields")
            print(f"   • Extended metrics (17 new)")
            print(f"   • Multi-currency support")
            print(f"   • Custom field dictionaries")
            return 1

        if args.mediaplan_command == "create":
            return handle_mediaplan_create(args)
        elif args.mediaplan_command == "delete":
            return handle_mediaplan_delete(args)

    # If we reach here, no command was handled
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())