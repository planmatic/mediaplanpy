"""
Workspace upgrader for migrating workspaces from v2.0 to v3.0.

This module provides the WorkspaceUpgrader class which handles all aspects
of upgrading a workspace to v3.0, including:
- File backups (JSON and Parquet)
- Database table backups
- Schema migration (v2.0 → v3.0)
- Database schema upgrades (ALTER TABLE)
- Workspace settings updates
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mediaplanpy.workspace.loader import WorkspaceManager

from mediaplanpy.exceptions import WorkspaceError, SchemaVersionError, ValidationError

logger = logging.getLogger("mediaplanpy.workspace.upgrader")


class WorkspaceUpgrader:
    """
    Handles workspace upgrades from v2.0 to v3.0.

    This class orchestrates the complete upgrade process including:
    1. Pre-upgrade validation
    2. Backup creation (files and database)
    3. JSON migration with audience/location transformation
    4. Parquet regeneration with v3.0 schema
    5. Database schema upgrade with ALTER TABLE
    6. Workspace settings update

    Example:
        >>> from mediaplanpy.workspace import WorkspaceManager
        >>> workspace_manager = WorkspaceManager()
        >>> workspace_manager.load()
        >>> upgrader = WorkspaceUpgrader(workspace_manager)
        >>> result = upgrader.upgrade(dry_run=True)  # Preview changes
        >>> result = upgrader.upgrade(dry_run=False)  # Actually upgrade
    """

    def __init__(self, workspace_manager: 'WorkspaceManager'):
        """
        Initialize the workspace upgrader.

        Args:
            workspace_manager: The WorkspaceManager instance for the workspace to upgrade
        """
        self.workspace_manager = workspace_manager

    def upgrade(self, target_sdk_version: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Upgrade entire workspace from v2.0 to v3.0.

        This method implements the complete workspace upgrade process:
        1. Validate workspace is v2.0 (reject v1.0 and below)
        2. Create timestamped backups (JSON, Parquet, Database)
        3. Upgrade database schema (ALTER TABLE to add v3.0 columns) - BEFORE data migration
        4. Migrate JSON files (v2.0 → v3.0) - save() automatically updates Parquet & Database
        5. Update workspace settings to v3.0

        Args:
            target_sdk_version: Target SDK version (defaults to current SDK version)
            dry_run: If True, shows what would be upgraded without making changes

        Returns:
            UpgradeResult dictionary with files processed, errors, database changes, backup locations

        Raises:
            WorkspaceError: If no configuration is loaded or upgrade fails
            WorkspaceInactiveError: If workspace is inactive
        """
        # Check if workspace is active
        self.workspace_manager.check_workspace_active("workspace upgrade")

        # Ensure workspace is loaded
        if not self.workspace_manager.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        # Get current SDK and schema versions
        from mediaplanpy import __version__, __schema_version__

        if target_sdk_version is None:
            target_sdk_version = __version__

        target_schema_version = __schema_version__  # This will be "3.0"

        logger.info(f"Starting workspace upgrade to SDK {target_sdk_version}, Schema {target_schema_version}")

        # Initialize result dictionary
        result = {
            "dry_run": dry_run,
            "target_sdk_version": target_sdk_version,
            "target_schema_version": target_schema_version,
            "files_processed": [],
            "files_failed": [],
            "errors": [],
            "database_upgraded": False,
            "workspace_updated": False,
            "parquet_files_regenerated": 0,
            "json_files_migrated": 0,
            "backups_created": {},
            "v1_files_rejected": 0,  # Track v1.0 and below rejections
            "version_validation_errors": []
        }

        try:
            # STEP 0: Pre-upgrade validation - reject v1.0 and validate compatibility
            validation_result = self._validate_upgrade_compatibility(target_schema_version, dry_run)
            result["v1_files_rejected"] = validation_result["v1_files_rejected"]
            result["version_validation_errors"].extend(validation_result["errors"])
            result["errors"].extend(validation_result["errors"])

            # If we found v1.0 or below files, this is a blocking error
            if validation_result["v1_files_rejected"] > 0:
                error_msg = (
                    f"Found {validation_result['v1_files_rejected']} media plan files with v1.0 or older schema. "
                    f"v1.0 support has been removed in SDK v3.0. Please use SDK v2.x to migrate "
                    f"v1.0 plans to v2.0 first, then upgrade to SDK v3.0."
                )
                result["errors"].append(error_msg)
                logger.error(error_msg)

                if not dry_run:
                    raise WorkspaceError(error_msg)

            # STEP 1: Create backups (unless dry run)
            if not dry_run:
                backup_dir = self._create_backup_directory()
                result["backups_created"]["backup_directory"] = backup_dir

                # Backup JSON files
                json_backup = self._backup_files(backup_dir)
                result["backups_created"]["json_backup"] = json_backup
                if json_backup["errors"]:
                    result["errors"].extend(json_backup["errors"])

                # Backup Parquet files
                parquet_backup = self._backup_files(backup_dir, file_pattern="*.parquet")
                result["backups_created"]["parquet_backup"] = parquet_backup
                if parquet_backup["errors"]:
                    result["errors"].extend(parquet_backup["errors"])

                # Backup database table if enabled
                if self._should_upgrade_database():
                    db_backup = self._backup_database_table(backup_dir)
                    result["backups_created"]["database_backup"] = db_backup
                    if db_backup["errors"]:
                        result["errors"].extend(db_backup["errors"])

                logger.info(f"Backups created in: {backup_dir}")

            # Get initial database record count (before any changes)
            initial_record_count = None
            if self._should_upgrade_database():
                try:
                    from mediaplanpy.storage.database import PostgreSQLBackend
                    db_backend = PostgreSQLBackend(self.workspace_manager.get_resolved_config())
                    if db_backend.table_exists():
                        initial_record_count = self._get_workspace_record_count(db_backend)
                        logger.info(f"Database records before upgrade: {initial_record_count}")
                except Exception as e:
                    logger.warning(f"Could not get initial record count: {e}")

            # STEP 2: Upgrade database schema FIRST (before saving v3.0 data)
            if self._should_upgrade_database():
                db_result = self._upgrade_database_schema(dry_run)
                result["database_upgraded"] = db_result["upgraded"]
                result["errors"].extend(db_result["errors"])
                # Store database result for record count display
                result["database_result"] = db_result

            # STEP 3: Upgrade all JSON media plans (v2.0 → v3.0)
            # Note: save() will automatically regenerate Parquet AND update database with v3.0 data
            json_result = self._upgrade_json_mediaplans(target_schema_version, dry_run)
            result["json_files_migrated"] = json_result["migrated_count"]
            result["files_processed"].extend(json_result["processed_files"])
            result["files_failed"].extend(json_result["failed_files"])
            result["errors"].extend(json_result["errors"])
            # Parquet files are automatically regenerated during save() above
            result["parquet_files_regenerated"] = json_result["migrated_count"]

            # Get final database record count (after all changes)
            if self._should_upgrade_database() and initial_record_count is not None:
                try:
                    from mediaplanpy.storage.database import PostgreSQLBackend
                    db_backend = PostgreSQLBackend(self.workspace_manager.get_resolved_config())
                    if db_backend.table_exists():
                        final_record_count = self._get_workspace_record_count(db_backend)
                        logger.info(f"Database records after upgrade: {final_record_count}")

                        # Add to database_result or create if doesn't exist
                        if "database_result" not in result:
                            result["database_result"] = {}
                        result["database_result"]["records_before"] = initial_record_count
                        result["database_result"]["records_after"] = final_record_count

                        # Data integrity check
                        if initial_record_count != final_record_count:
                            warning_msg = f"⚠️  WARNING: Record count changed during upgrade (before: {initial_record_count}, after: {final_record_count})"
                            logger.warning(warning_msg)
                            result["errors"].append(warning_msg)
                        else:
                            logger.info(f"✓ Data integrity verified: {final_record_count} records preserved")
                except Exception as e:
                    logger.warning(f"Could not get final record count: {e}")

            # STEP 4: Update workspace settings for v3.0
            workspace_result = self._update_workspace_settings(target_sdk_version, target_schema_version, dry_run)
            result["workspace_updated"] = workspace_result["updated"]
            result["errors"].extend(workspace_result["errors"])

            # Log comprehensive summary
            if dry_run:
                logger.info(f"[DRY RUN] Workspace upgrade would process {len(result['files_processed'])} files")
                if result["v1_files_rejected"] > 0:
                    logger.warning(f"[DRY RUN] Would reject {result['v1_files_rejected']} v1.0 or older files")
            else:
                logger.info(f"Workspace upgrade completed: {result['json_files_migrated']} JSON files migrated, "
                           f"{result['parquet_files_regenerated']} Parquet files regenerated")
                if result["v1_files_rejected"] > 0:
                    logger.warning(f"Rejected {result['v1_files_rejected']} v1.0 or older files (no longer supported)")
                if result["backups_created"]:
                    logger.info(f"Backups stored in: {result['backups_created'].get('backup_directory', 'N/A')}")

            return result

        except Exception as e:
            error_msg = f"Workspace upgrade failed: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
            raise WorkspaceError(error_msg)

    # =========================================================================
    # Backup Methods
    # =========================================================================

    def _create_backup_directory(self) -> str:
        """
        Create timestamped backup directory inside the workspace's storage path.

        For local storage: Creates a physical directory
        For S3 storage: Returns a backup prefix path

        Returns:
            Path/prefix for backup directory
        """
        # Get workspace storage configuration
        storage_config = self.workspace_manager.config.get("storage", {})
        storage_mode = storage_config.get("mode", "local")

        # Generate timestamp for backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder_name = f"{timestamp}_upgrade_v3.0"

        if storage_mode == "local":
            # Use the storage base_path from config
            workspace_dir = storage_config.get("local", {}).get("base_path")
            if not workspace_dir:
                raise WorkspaceError("Local storage base_path not configured")

            # Create physical directory for local storage
            backup_dir = os.path.join(workspace_dir, "backups", backup_folder_name)
            os.makedirs(backup_dir, exist_ok=True)
            logger.info(f"Created local backup directory: {backup_dir}")

        elif storage_mode == "s3":
            # For S3, construct backup prefix (virtual directory)
            # NOTE: Don't include workspace prefix here - storage backend adds it automatically
            s3_config = storage_config.get("s3", {})
            prefix = s3_config.get("prefix", "")

            # Build backup path without prefix (storage backend will add it)
            backup_dir = f"backups/{backup_folder_name}"

            # Log full S3 path for user visibility
            if prefix:
                full_path = f"{prefix}/{backup_dir}"
            else:
                full_path = backup_dir
            logger.info(f"S3 backup prefix: s3://{s3_config.get('bucket')}/{full_path}")

        else:
            raise WorkspaceError(f"Backup not supported for storage mode: {storage_mode}")

        return backup_dir

    def _backup_files(self, backup_dir: str, file_pattern: str = "*.json") -> Dict[str, Any]:
        """
        Backup media plan files (JSON or Parquet) to backup directory.

        Args:
            backup_dir: Directory where backups should be stored
            file_pattern: File pattern to match (*.json or *.parquet)

        Returns:
            Dictionary with backup results
        """
        result = {
            "backup_created": False,
            "backup_directory": backup_dir,
            "files_backed_up": 0,
            "errors": []
        }

        try:
            # Get storage backend
            storage_backend = self.workspace_manager.get_storage_backend()

            # Find all files matching pattern in mediaplans directory
            files = []
            try:
                files = storage_backend.list_files("mediaplans", file_pattern)
            except Exception:
                # Try root directory as fallback
                try:
                    files = storage_backend.list_files("", file_pattern)
                except Exception:
                    logger.info(f"No files found matching {file_pattern}")
                    return result

            if not files:
                logger.info(f"No files to backup matching {file_pattern}")
                return result

            # Get storage mode to determine backup method
            storage_config = self.workspace_manager.config.get("storage", {})
            storage_mode = storage_config.get("mode", "local")

            # Determine if binary mode based on file pattern
            binary_mode = file_pattern.endswith(".parquet")

            # Copy each file using appropriate method
            for file_path in files:
                try:
                    # Read file content from source
                    content = storage_backend.read_file(file_path, binary=binary_mode)

                    # Construct backup file path
                    filename = os.path.basename(file_path)

                    if storage_mode == "local":
                        # Local: Write to physical directory
                        files_backup_dir = os.path.join(backup_dir, "mediaplans")
                        os.makedirs(files_backup_dir, exist_ok=True)
                        backup_file_path = os.path.join(files_backup_dir, filename)

                        mode = 'wb' if binary_mode else 'w'
                        with open(backup_file_path, mode) as f:
                            f.write(content)

                    elif storage_mode == "s3":
                        # S3: Write using storage backend to backup prefix
                        backup_file_path = f"{backup_dir}/mediaplans/{filename}"
                        # S3 write_file() auto-detects string vs bytes, no binary parameter needed
                        storage_backend.write_file(backup_file_path, content)

                    result["files_backed_up"] += 1
                    logger.debug(f"Backed up {file_path} to {backup_file_path}")

                except Exception as e:
                    result["errors"].append(f"Failed to backup {file_path}: {str(e)}")
                    logger.error(f"Failed to backup {file_path}: {str(e)}")

            result["backup_created"] = result["files_backed_up"] > 0
            backup_location = f"{backup_dir}/mediaplans" if storage_mode == "s3" else os.path.join(backup_dir, "mediaplans")
            logger.info(f"File backup complete: {result['files_backed_up']} {file_pattern} files backed up to {backup_location}")

        except Exception as e:
            result["errors"].append(f"File backup failed: {str(e)}")
            logger.error(f"File backup failed: {str(e)}")

        return result

    def _backup_database_table(self, backup_dir: str) -> Dict[str, Any]:
        """
        Backup database table by creating a timestamped backup table.

        Uses PostgreSQL CREATE TABLE AS SELECT for atomic backup.

        Args:
            backup_dir: Directory where backup metadata is stored

        Returns:
            Dictionary with backup results
        """
        result = {
            "backup_created": False,
            "backup_table_name": None,
            "records_backed_up": 0,
            "errors": []
        }

        try:
            from mediaplanpy.storage.database import PostgreSQLBackend

            # Get database backend
            db_backend = PostgreSQLBackend(self.workspace_manager.get_resolved_config())

            # Check if table exists
            if not db_backend.table_exists():
                logger.info("Database table does not exist, no backup needed")
                return result

            # Check if table is already v3.0 - no backup needed
            current_version = db_backend.get_table_version()
            if current_version == "3.0":
                logger.info("Database table is already v3.0, no backup needed")
                return result

            # Generate backup table name with timestamp at start
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_table_name = f"{timestamp}_backup_{db_backend.table_name}"

            # Create backup table using CREATE TABLE AS SELECT
            try:
                with db_backend.connect() as conn:
                    with conn.cursor() as cursor:
                        # Create backup table (quote table names for PostgreSQL compatibility)
                        backup_sql = f"""
                            CREATE TABLE {db_backend.schema}."{backup_table_name}" AS
                            SELECT * FROM {db_backend.schema}.{db_backend.table_name}
                        """
                        cursor.execute(backup_sql)

                        # Get count of backed up records
                        count_sql = f'SELECT COUNT(*) FROM {db_backend.schema}."{backup_table_name}"'
                        cursor.execute(count_sql)
                        result["records_backed_up"] = cursor.fetchone()[0]

                    conn.commit()

                result["backup_created"] = True
                result["backup_table_name"] = backup_table_name

                # Write backup metadata to file
                metadata_path = os.path.join(backup_dir, "database_backup_info.txt")
                with open(metadata_path, 'w') as f:
                    f.write(f"Backup Table: {backup_table_name}\n")
                    f.write(f"Records Backed Up: {result['records_backed_up']}\n")
                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Database: {db_backend.database}\n")

                logger.info(f"Database backup complete: {result['records_backed_up']} records backed up to table '{backup_table_name}'")

            except Exception as e:
                result["errors"].append(f"Failed to create backup table: {str(e)}")
                logger.error(f"Failed to create backup table: {str(e)}")

        except ImportError:
            logger.info("Database features not available (psycopg2 not installed)")
        except Exception as e:
            result["errors"].append(f"Database backup failed: {str(e)}")
            logger.error(f"Database backup failed: {str(e)}")

        return result

    # =========================================================================
    # Validation Methods
    # =========================================================================

    def _validate_upgrade_compatibility(self, target_schema_version: str, dry_run: bool) -> Dict[str, Any]:
        """
        Validate that workspace can be upgraded to v3.0.

        Checks:
        - Rejects v1.0 and below (no longer supported in v3.0)
        - Counts v2.0 files that will be migrated
        - Validates current workspace schema version

        Args:
            target_schema_version: Target schema version (should be "3.0")
            dry_run: If True, just validate without blocking

        Returns:
            Dictionary with validation results
        """
        result = {
            "v1_files_rejected": 0,
            "v2_files_found": 0,
            "errors": []
        }

        try:
            # Get storage backend
            storage_backend = self.workspace_manager.get_storage_backend()

            # Find all JSON files
            json_files = []
            try:
                json_files = storage_backend.list_files("mediaplans", "*.json")
            except Exception:
                try:
                    json_files = storage_backend.list_files("", "*.json")
                except Exception:
                    pass

            # Check each file's schema version
            for file_path in json_files:
                try:
                    content = storage_backend.read_file(file_path, binary=False)
                    import json
                    data = json.loads(content)

                    current_version = data.get("meta", {}).get("schema_version")

                    if not current_version:
                        result["errors"].append(f"File {file_path} has no schema version")
                        continue

                    # Check for v1.0 and below files
                    from mediaplanpy.schema.version_utils import normalize_version
                    normalized = normalize_version(current_version)
                    major_version = int(normalized.split('.')[0])

                    if major_version < 2:
                        result["v1_files_rejected"] += 1
                        logger.warning(f"Found unsupported version {current_version} in {file_path}")
                    elif major_version == 2:
                        result["v2_files_found"] += 1

                except Exception as e:
                    result["errors"].append(f"Error checking {file_path}: {str(e)}")

            # Log summary
            if result["v1_files_rejected"] > 0:
                logger.error(f"Validation failed: {result['v1_files_rejected']} files with v1.0 or older schema")
            else:
                logger.info(f"Validation passed: {result['v2_files_found']} v2.0 files ready for upgrade")

        except Exception as e:
            result["errors"].append(f"Validation failed: {str(e)}")

        return result

    # =========================================================================
    # Migration Methods
    # =========================================================================

    def _upgrade_json_mediaplans(self, target_schema_version: str, dry_run: bool) -> Dict[str, Any]:
        """
        Upgrade all JSON media plan files from v2.0 to v3.0.

        Performs v2.0 → v3.0 migration including:
        - Audience fields → target_audiences array transformation
        - Location fields → target_locations array transformation
        - Dictionary custom_dimensions → lineitem_custom_dimensions rename
        - Schema version update to 3.0

        Args:
            target_schema_version: Target schema version (should be "3.0")
            dry_run: If True, don't actually modify files

        Returns:
            Dictionary with migration results
        """
        from mediaplanpy.models import MediaPlan

        result = {
            "migrated_count": 0,
            "already_current_count": 0,
            "v1_rejected_count": 0,
            "processed_files": [],
            "failed_files": [],
            "errors": []
        }

        try:
            # Get storage backend
            storage_backend = self.workspace_manager.get_storage_backend()

            # Find all JSON files in mediaplans directory
            json_files = []
            try:
                json_files = storage_backend.list_files("mediaplans", "*.json")
            except Exception:
                # Try root directory as fallback
                json_files = storage_backend.list_files("", "*.json")

            total_files = len(json_files)
            logger.info(f"Found {total_files} JSON files to process for v3.0 upgrade")

            for index, file_path in enumerate(json_files, start=1):
                try:
                    result["processed_files"].append(file_path)

                    # Extract plan name from file path for progress message
                    plan_name = os.path.basename(file_path).replace('.json', '')

                    if dry_run:
                        # For dry run, just check what would be migrated
                        try:
                            content = storage_backend.read_file(file_path, binary=False)
                            import json
                            data = json.loads(content)

                            current_version = data.get("meta", {}).get("schema_version")

                            if not current_version:
                                result["errors"].append(f"File {file_path} has no schema version")
                                continue

                            # Check for v1.0 and below files
                            from mediaplanpy.schema.version_utils import normalize_version
                            normalized = normalize_version(current_version)
                            major_version = int(normalized.split('.')[0])

                            if major_version < 2:
                                result["v1_rejected_count"] += 1
                                logger.warning(f"[DRY RUN] Would reject v1.0 or older file: {file_path}")
                                continue

                            target_normalized = normalize_version(f"v{target_schema_version}")

                            if normalized != target_normalized:
                                result["migrated_count"] += 1
                                logger.info(f"[DRY RUN] Would migrate {file_path} from {current_version} to v{target_schema_version}")
                            else:
                                result["already_current_count"] += 1
                                logger.debug(f"[DRY RUN] File {file_path} already at target version")

                        except Exception as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Failed to check {file_path}: {str(e)}")
                    else:
                        # Actually perform migration
                        try:
                            # Pre-check for v1.0 and below files
                            content = storage_backend.read_file(file_path, binary=False)
                            import json
                            data = json.loads(content)

                            current_version = data.get("meta", {}).get("schema_version")

                            # CRITICAL: Reject v1.0 and below files
                            if current_version:
                                from mediaplanpy.schema.version_utils import normalize_version
                                normalized = normalize_version(current_version)
                                major_version = int(normalized.split('.')[0])

                                if major_version < 2:
                                    result["v1_rejected_count"] += 1
                                    result["failed_files"].append(file_path)
                                    error_msg = (
                                        f"Cannot migrate {file_path}: schema version {current_version} "
                                        f"is no longer supported in SDK v3.0. Use SDK v2.x to migrate to v2.0 first."
                                    )
                                    result["errors"].append(error_msg)
                                    logger.error(error_msg)
                                    continue

                            # Temporarily suppress expected migration warnings during upgrade
                            import logging
                            mediaplan_logger = logging.getLogger('mediaplanpy')
                            old_level = mediaplan_logger.level
                            mediaplan_logger.setLevel(logging.ERROR)  # Suppress WARNING level during upgrade

                            try:
                                # Load media plan (will trigger v2.0 → v3.0 migration via schema migrator)
                                # Note: validate_version=False suppresses expected v2.0 deprecation warnings during upgrade
                                media_plan = MediaPlan.load(self.workspace_manager, path=file_path, validate_version=False, auto_migrate=True)

                                # Save with v3.0 schema (will auto-regenerate Parquet and update Database)
                                # Note: validate_version=False suppresses warnings during upgrade
                                media_plan.save(self.workspace_manager, path=file_path, overwrite=True, validate_version=False)
                            finally:
                                # Restore original log level
                                mediaplan_logger.setLevel(old_level)

                            # Check if migration actually occurred
                            from mediaplanpy.schema.version_utils import normalize_version
                            normalized = normalize_version(current_version) if current_version else ""
                            target_normalized = normalize_version(f"v{target_schema_version}")

                            if normalized != target_normalized:
                                result["migrated_count"] += 1
                                # Use print() for user-visible progress (not suppressed by logger)
                                print(f"✓ Successfully migrated media plan '{plan_name}' ({index}/{total_files})")
                            else:
                                result["already_current_count"] += 1
                                print(f"✓ Media plan '{plan_name}' already at v{target_schema_version} ({index}/{total_files})")

                        except SchemaVersionError as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Schema version error for {file_path}: {str(e)}")
                            logger.error(f"Schema version error for {file_path}: {str(e)}")
                        except ValidationError as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Validation failed for {file_path}: {str(e)}")
                            logger.error(f"Validation failed for {file_path}: {str(e)}")
                        except Exception as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Unexpected error with {file_path}: {str(e)}")
                            logger.error(f"Unexpected error with {file_path}: {str(e)}")

                except Exception as e:
                    result["failed_files"].append(file_path)
                    result["errors"].append(f"Error processing {file_path}: {str(e)}")

            # Log summary
            logger.info(f"JSON migration complete: {result['migrated_count']} migrated, "
                       f"{result['already_current_count']} already current, "
                       f"{result['v1_rejected_count']} v1.0 or older files rejected")

        except Exception as e:
            result["errors"].append(f"Error finding JSON files: {str(e)}")

        return result

    def _regenerate_parquet_files(self, dry_run: bool) -> Dict[str, Any]:
        """
        Regenerate all Parquet files with v3.0 schema.

        Args:
            dry_run: If True, don't actually regenerate files

        Returns:
            Dictionary with regeneration results
        """
        from mediaplanpy.models import MediaPlan

        result = {
            "regenerated_count": 0,
            "skipped_count": 0,
            "processed_files": [],
            "failed_files": [],
            "errors": []
        }

        try:
            # Get storage backend
            storage_backend = self.workspace_manager.get_storage_backend()

            # Find all JSON files (source of truth)
            json_files = []
            try:
                json_files = storage_backend.list_files("mediaplans", "*.json")
            except Exception:
                json_files = storage_backend.list_files("", "*.json")

            logger.info(f"Regenerating Parquet files for {len(json_files)} media plans")

            for json_path in json_files:
                try:
                    # Construct Parquet path from JSON path
                    parquet_path = json_path.rsplit('.', 1)[0] + '.parquet'
                    result["processed_files"].append(parquet_path)

                    if dry_run:
                        logger.info(f"[DRY RUN] Would regenerate Parquet for {json_path}")
                        result["regenerated_count"] += 1
                    else:
                        try:
                            # Load media plan from JSON (already migrated to v3.0 in previous step)
                            # Note: validate_version=False suppresses expected v2.0 deprecation warnings
                            media_plan = MediaPlan.load(self.workspace_manager, path=json_path, validate_version=False)

                            # Save will automatically regenerate Parquet with v3.0 schema
                            media_plan.save(
                                self.workspace_manager,
                                path=json_path,
                                overwrite=True,
                                include_parquet=True,
                                include_database=False,  # Database handled separately
                                validate_version=True
                            )

                            result["regenerated_count"] += 1
                            logger.info(f"Regenerated Parquet for {json_path}")

                        except Exception as e:
                            result["failed_files"].append(parquet_path)
                            result["errors"].append(f"Failed to regenerate Parquet for {parquet_path} (from {json_path}): {str(e)}")
                            logger.error(f"Failed to regenerate Parquet for {parquet_path} (from {json_path}): {str(e)}")

                except Exception as e:
                    result["failed_files"].append(parquet_path)
                    result["errors"].append(f"Error processing Parquet for {parquet_path} (from {json_path}): {str(e)}")

            logger.info(f"Parquet regeneration complete: {result['regenerated_count']} files regenerated")

        except Exception as e:
            result["errors"].append(f"Error regenerating Parquet files: {str(e)}")

        return result

    def _get_workspace_record_count(self, db_backend) -> int:
        """
        Get the count of records in the database for this workspace.

        Args:
            db_backend: PostgreSQL backend instance

        Returns:
            Number of records for this workspace_id
        """
        try:
            workspace_id = self.workspace_manager.config.get("workspace_id")
            with db_backend.connect() as conn:
                with conn.cursor() as cursor:
                    query = f"""
                        SELECT COUNT(*)
                        FROM {db_backend.schema}.{db_backend.table_name}
                        WHERE workspace_id = %s
                    """
                    cursor.execute(query, (workspace_id,))
                    count = cursor.fetchone()[0]
                    return count
        except Exception as e:
            logger.warning(f"Failed to get record count: {e}")
            return -1  # Return -1 to indicate count failed

    def _upgrade_database_schema(self, dry_run: bool) -> Dict[str, Any]:
        """
        Upgrade database schema from v2.0 to v3.0.

        Performs:
        1. Detects current database schema version
        2. Adds v3.0 columns using ALTER TABLE
        3. Keeps deprecated v2.0 columns for backward compatibility

        Note: Record count tracking is handled at the upgrade() level to cover
        the entire upgrade process, not just schema changes.

        Args:
            dry_run: If True, don't actually modify database

        Returns:
            Dictionary with upgrade results (schema versions, columns added, errors)
        """
        result = {
            "upgraded": False,
            "schema_version_before": None,
            "schema_version_after": None,
            "columns_added": 0,
            "errors": []
        }

        try:
            from mediaplanpy.storage.database import PostgreSQLBackend
            from mediaplanpy.models import MediaPlan

            # Get database backend
            db_backend = PostgreSQLBackend(self.workspace_manager.get_resolved_config())

            # Check if table exists
            if not db_backend.table_exists():
                logger.info("Database table does not exist, creating with v3.0 schema")
                if not dry_run:
                    # Table will be created with v3.0 schema automatically on first save
                    result["upgraded"] = True
                    result["schema_version_after"] = "3.0"
                return result

            # Detect current schema version
            current_version = db_backend.get_table_version()
            result["schema_version_before"] = current_version

            if current_version == "3.0":
                logger.info("Database schema is already v3.0 - no upgrade needed")
                result["upgraded"] = False  # Already at target version
                result["schema_version_after"] = "3.0"
                return result

            if dry_run:
                logger.info(f"[DRY RUN] Would upgrade database from v{current_version} to v3.0")
                result["upgraded"] = True  # Would be upgraded
                result["schema_version_after"] = "3.0"
                return result

            # Actually upgrade database schema
            logger.info(f"Upgrading database schema from v{current_version} to v3.0")

            # Call migrate_schema_v2_to_v3 method in database backend
            migration_result = db_backend.migrate_schema_v2_to_v3()

            result["columns_added"] = migration_result.get("columns_added", 0)
            result["errors"].extend(migration_result.get("errors", []))

            if migration_result.get("success", False):
                result["upgraded"] = True
                result["schema_version_after"] = "3.0"
                logger.info(f"Database schema upgraded: {result['columns_added']} columns added")
            else:
                result["errors"].append("Database schema migration failed")
                logger.error("Database schema migration failed")

        except ImportError:
            logger.info("Database features not available (psycopg2 not installed)")
        except Exception as e:
            result["errors"].append(f"Database upgrade failed: {str(e)}")
            logger.error(f"Database upgrade failed: {str(e)}")

        return result

    def _update_workspace_settings(self, sdk_version: str, schema_version: str, dry_run: bool) -> Dict[str, Any]:
        """
        Update workspace settings to v3.0.

        Args:
            sdk_version: New SDK version
            schema_version: New schema version
            dry_run: If True, don't actually update settings

        Returns:
            Dictionary with update results
        """
        result = {
            "updated": False,
            "errors": []
        }

        try:
            # Load current settings to check if already at target version
            import json
            with open(self.workspace_manager.workspace_path, 'r') as f:
                settings = json.load(f)

            # Check if already at target version
            current_schema = settings.get('workspace_settings', {}).get('schema_version')
            if current_schema == schema_version:
                logger.info(f"Workspace settings already at target version {schema_version} - no update needed")
                result["updated"] = False
                return result

            if dry_run:
                logger.info(f"[DRY RUN] Would update workspace settings from {current_schema} to SDK {sdk_version}, Schema {schema_version}")
                result["updated"] = True
                return result

            # Update version information in workspace_settings (settings already loaded above)
            if 'workspace_settings' not in settings:
                settings['workspace_settings'] = {}

            settings['workspace_settings']['schema_version'] = schema_version
            settings['workspace_settings']['sdk_version_required'] = sdk_version
            settings['workspace_settings']['last_upgraded'] = datetime.now().strftime('%Y-%m-%d')

            # Add upgrade metadata
            if 'upgrade_history' not in settings:
                settings['upgrade_history'] = []

            settings['upgrade_history'].append({
                'timestamp': datetime.now().isoformat(),
                'from_version': '2.0',
                'to_version': schema_version,
                'sdk_version': sdk_version
            })

            # Write updated settings
            with open(self.workspace_manager.workspace_path, 'w') as f:
                json.dump(settings, f, indent=2)

            result["updated"] = True
            logger.info(f"Workspace settings updated to v{schema_version}")

        except Exception as e:
            result["errors"].append(f"Failed to update workspace settings: {str(e)}")
            logger.error(f"Failed to update workspace settings: {str(e)}")

        return result

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _should_upgrade_database(self) -> bool:
        """
        Check if database upgrade should be performed.

        Returns:
            True if database is configured and should be upgraded
        """
        try:
            config = self.workspace_manager.get_resolved_config()
            return 'database' in config and config['database'] is not None
        except Exception:
            return False
