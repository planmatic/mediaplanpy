#!/usr/bin/env python3
"""
Manual workspace upgrade testing script for SDK v3.0.

This script allows manual step-by-step testing of the workspace upgrade process
from v2.0 to v3.0. Easy to use with IDE debuggers.

Configuration:
    Set WORKSPACE_SETTINGS_PATH below to your workspace settings file path.
"""

import sys
import os
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.exceptions import WorkspaceError


# =============================================================================
# CONFIGURATION - Set your workspace path here
# =============================================================================

WORKSPACE_SETTINGS_PATH = r"C:\mediaplanpy\workspace_35a938d0_settings.json"

# Example paths for common test cases:
# WORKSPACE_SETTINGS_PATH = "/mnt/c/users/laure/mediaplans/workspace_v2_with_db/.mediaplanpy_workspace_settings.json"
# WORKSPACE_SETTINGS_PATH = "/mnt/c/users/laure/mediaplans/workspace_v2_no_db/.mediaplanpy_workspace_settings.json"
# WORKSPACE_SETTINGS_PATH = "/mnt/c/users/laure/mediaplans/workspace_v1/.mediaplanpy_workspace_settings.json"


# =============================================================================
# Helper Functions
# =============================================================================

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


def print_info(label: str, value: any):
    """Print formatted info."""
    print(f"{label}: {value}")


def get_workspace_info(workspace_manager: WorkspaceManager) -> dict:
    """Get current workspace state information."""
    # Get storage path based on storage mode
    storage_config = workspace_manager.config.get("storage", {})
    storage_mode = storage_config.get("mode", "local")
    if storage_mode == "local":
        storage_path = storage_config.get("local", {}).get("base_path", "Unknown")
    elif storage_mode == "s3":
        bucket = storage_config.get("s3", {}).get("bucket", "Unknown")
        prefix = storage_config.get("s3", {}).get("prefix", "")
        storage_path = f"s3://{bucket}/{prefix}" if prefix else f"s3://{bucket}"
    else:
        storage_path = "Unknown"

    info = {
        "workspace_id": workspace_manager.config.get("workspace_id", "Unknown"),
        "workspace_name": workspace_manager.config.get("workspace_name", "Unknown"),
        "settings_path": workspace_manager.workspace_path,
        "storage_mode": storage_mode,
        "storage_path": storage_path,
        "schema_version": "Unknown",
        "database_enabled": False,
        "database_table_version": None,
        "json_files": 0,
        "parquet_files": 0
    }

    # Get schema version from workspace_settings
    workspace_settings = workspace_manager.config.get("workspace_settings", {})
    info["schema_version"] = workspace_settings.get("schema_version", "Unknown")

    # Check database
    db_config = workspace_manager.config.get("database", {})
    if db_config.get("enabled", False):
        info["database_enabled"] = True
        info["database_name"] = db_config.get("database", "Unknown")

        # Try to get database table version
        try:
            from mediaplanpy.storage.database import PostgreSQLBackend
            db_backend = PostgreSQLBackend(workspace_manager.get_resolved_config())
            if db_backend.table_exists():
                info["database_table_version"] = db_backend.get_table_version()
            else:
                info["database_table_version"] = "No table"
        except Exception as e:
            info["database_table_version"] = f"Error: {e}"

    # Count files
    try:
        storage_backend = workspace_manager.get_storage_backend()
        try:
            json_files = storage_backend.list_files("mediaplans", "*.json")
            info["json_files"] = len(json_files)
        except:
            pass
        try:
            parquet_files = storage_backend.list_files("mediaplans", "*.parquet")
            info["parquet_files"] = len(parquet_files)
        except:
            pass
    except Exception as e:
        info["file_count_error"] = str(e)

    return info


def display_workspace_info(info: dict):
    """Display workspace information."""
    print_subsection("Current Workspace State")
    print_info("Workspace ID", info["workspace_id"])
    print_info("Workspace Name", info["workspace_name"])
    print_info("Settings Path", info["settings_path"])
    print_info("Storage Mode", info["storage_mode"])
    print_info("Storage Path", info["storage_path"])
    print_info("Schema Version", info["schema_version"])
    print_info("JSON Files", info["json_files"])
    print_info("Parquet Files", info["parquet_files"])

    print_subsection("Database Configuration")
    if info["database_enabled"]:
        print_info("Database Enabled", "Yes")
        print_info("Database Name", info["database_name"])
        print_info("Database Table Version", info["database_table_version"])
    else:
        print_info("Database Enabled", "No")


def display_upgrade_result(result: dict, dry_run: bool = False):
    """Display upgrade results."""
    mode = "[DRY RUN]" if dry_run else "[ACTUAL]"

    print_subsection(f"Upgrade Results {mode}")

    print_info("Target SDK Version", result["target_sdk_version"])
    print_info("Target Schema Version", result["target_schema_version"])

    print_subsection("Files Processed")
    print_info("JSON Files Migrated", result["json_files_migrated"])
    print_info("Parquet Files Regenerated", result["parquet_files_regenerated"])
    print_info("Files Processed", len(result["files_processed"]))
    print_info("Files Failed", len(result["files_failed"]))

    if result["files_failed"]:
        print("\nFailed Files:")
        for f in result["files_failed"]:
            print(f"  - {f}")

    print_subsection("Database")
    print_info("Database Upgraded", result["database_upgraded"])

    # Display database record counts for data integrity verification
    db_result = result.get("database_result", {})
    if db_result:
        records_before = db_result.get("records_before")
        records_after = db_result.get("records_after")

        if records_before is not None:
            print_info("Records Before Migration", records_before)
        if records_after is not None:
            print_info("Records After Migration", records_after)

        # Data integrity check
        if records_before is not None and records_after is not None:
            if records_before == records_after:
                print("  ✓ Data integrity verified: record count unchanged")
            else:
                print(f"  ⚠️  WARNING: Record count changed ({records_before} → {records_after})")

    if not dry_run and result.get("backups_created"):
        print_subsection("Backups Created")
        backup_dir = result["backups_created"].get("backup_directory")
        if backup_dir:
            print_info("Backup Directory", backup_dir)

        json_backup = result["backups_created"].get("json_backup", {})
        print_info("JSON Files Backed Up", json_backup.get("files_backed_up", 0))

        parquet_backup = result["backups_created"].get("parquet_backup", {})
        print_info("Parquet Files Backed Up", parquet_backup.get("files_backed_up", 0))

        db_backup = result["backups_created"].get("database_backup", {})
        if db_backup.get("backup_created"):
            print_info("Database Backup Table", db_backup.get("backup_table_name", "N/A"))
            print_info("Records Backed Up", db_backup.get("records_backed_up", 0))

    print_subsection("Validation")
    print_info("v1.0 Files Rejected", result.get("v1_files_rejected", 0))

    if result["errors"]:
        print_subsection("Errors")
        for error in result["errors"]:
            print(f"  ❌ {error}")
    else:
        print("\n✅ No errors!")

    print_subsection("Status")
    print_info("Workspace Settings Updated", result["workspace_updated"])


# =============================================================================
# Main Test Execution
# =============================================================================

def main():
    """
    Main test execution.

    Set breakpoints at each step to inspect variables and step through execution.
    """
    print_section("Workspace Upgrade Test - SDK v3.0")

    # Check configuration
    if WORKSPACE_SETTINGS_PATH == "/path/to/your/.mediaplanpy_workspace_settings.json":
        print("❌ ERROR: Please set WORKSPACE_SETTINGS_PATH in the script configuration section.")
        print("\nEdit this file and set WORKSPACE_SETTINGS_PATH to your workspace settings file.")
        return

    if not os.path.exists(WORKSPACE_SETTINGS_PATH):
        print(f"❌ ERROR: Workspace settings file not found:")
        print(f"   {WORKSPACE_SETTINGS_PATH}")
        return

    print(f"Testing workspace: {WORKSPACE_SETTINGS_PATH}\n")

    try:
        # =============================================================================
        # STEP 1: Load Workspace
        # =============================================================================
        # Set breakpoint here to start stepping through

        print_section("STEP 1: Load Workspace")
        workspace_manager = WorkspaceManager()
        # Load in upgrade mode to bypass version compatibility check
        workspace_manager.load(workspace_path=WORKSPACE_SETTINGS_PATH, upgrade_mode=True)

        print("✅ Workspace loaded successfully")

        # Get and display current state
        info_before = get_workspace_info(workspace_manager)
        display_workspace_info(info_before)

        # =============================================================================
        # STEP 2: Dry-Run Upgrade (Preview)
        # =============================================================================
        # Set breakpoint here to inspect workspace state before dry-run

        print_section("STEP 2: Dry-Run Upgrade (Preview)")
        print("Running dry-run to preview changes...")

        try:
            dry_run_result = workspace_manager.upgrade_workspace(dry_run=True)
            display_upgrade_result(dry_run_result, dry_run=True)

        except WorkspaceError as e:
            print(f"\n❌ Dry-run failed: {e}")
            print("\nThis is expected for v1.0 workspaces or if there are validation errors.")

            # If dry-run failed, don't proceed to actual upgrade
            print("\n🛑 Test stopped (dry-run failed as expected).")
            return

        # =============================================================================
        # STEP 3: Actual Upgrade
        # =============================================================================
        # Set breakpoint here to inspect dry-run results before proceeding

        print_section("STEP 3: Actual Upgrade")
        print("⚠️  WARNING: This will modify your workspace!")
        print("\nThe upgrade will:")
        print("  1. Create timestamped backups of all files and database")
        print("  2. Migrate JSON files from v2.0 to v3.0")
        print("  3. Regenerate Parquet files with v3.0 schema")
        print("  4. Upgrade database schema (if enabled and required)")
        print("  5. Update workspace settings to v3.0")

        # Comment out this confirmation to allow automated execution
        response = input("\n⚠️  Proceed with actual upgrade? (yes/no): ")
        if response.lower() != "yes":
            print("\n❌ Upgrade cancelled.")
            return

        print("\nStarting actual upgrade...")

        try:
            upgrade_result = workspace_manager.upgrade_workspace(dry_run=False)
            display_upgrade_result(upgrade_result, dry_run=False)

        except WorkspaceError as e:
            print(f"\n❌ Upgrade failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # =============================================================================
        # STEP 4: Verify Upgrade
        # =============================================================================
        # Set breakpoint here to inspect upgrade results

        print_section("STEP 4: Verify Upgrade")
        print("Reloading workspace to verify changes...")

        # Reload workspace to see changes
        workspace_manager_verify = WorkspaceManager()
        workspace_manager_verify.load(workspace_path=WORKSPACE_SETTINGS_PATH)

        info_after = get_workspace_info(workspace_manager_verify)
        display_workspace_info(info_after)

        # Compare before and after
        print_subsection("Changes Summary")
        print_info("Schema Version Before", info_before["schema_version"])
        print_info("Schema Version After", info_after["schema_version"])

        if info_before["database_enabled"]:
            print_info("Database Table Version Before", info_before["database_table_version"])
            print_info("Database Table Version After", info_after["database_table_version"])

        print("\n✅ Upgrade test complete!")

        if upgrade_result.get("backups_created", {}).get("backup_directory"):
            print(f"\n📁 Backups: {upgrade_result['backups_created']['backup_directory']}")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
