"""
Enhanced MediaPlan storage integration with comprehensive version support.

This module updates the MediaPlan storage methods to include version validation,
compatibility checking, and migration logic for the new 2-digit versioning strategy.
"""

import os
import logging
import uuid
from typing import Dict, Any, Optional, Union, Type, ClassVar
from datetime import datetime

from mediaplanpy.exceptions import (
    StorageError,
    FileReadError,
    FileWriteError,
    SchemaVersionError,
    SchemaError
)
from mediaplanpy.models.mediaplan import MediaPlan
from mediaplanpy.storage import (
    read_mediaplan as storage_read_mediaplan,
    write_mediaplan as storage_write_mediaplan,
    get_format_handler_instance
)
from mediaplanpy.workspace import WorkspaceManager

logger = logging.getLogger("mediaplanpy.models.mediaplan_storage")

# Define constants
MEDIAPLANS_SUBDIR = "mediaplans"


def _media_plan_file_exists(workspace_config: Dict[str, Any], media_plan_id: str) -> bool:
    """
    Check if a media plan file with the given ID already exists in storage.

    This function checks for JSON files in the standard mediaplans directory structure.

    Args:
        workspace_config: The resolved workspace configuration
        media_plan_id: The media plan ID to check for

    Returns:
        True if a file exists for this media plan ID, False otherwise
    """
    try:
        from mediaplanpy.storage import get_storage_backend
        storage_backend = get_storage_backend(workspace_config)

        # Sanitize media plan ID for use as filename
        safe_id = media_plan_id.replace('/', '_').replace('\\', '_')

        # Check for JSON file in mediaplans directory
        json_path = os.path.join(MEDIAPLANS_SUBDIR, f"{safe_id}.json")

        if storage_backend.exists(json_path):
            return True

        # Also check root directory as fallback (for backward compatibility)
        root_json_path = f"{safe_id}.json"
        if storage_backend.exists(root_json_path):
            return True

        return False

    except Exception as e:
        logger.warning(f"Could not check if media plan file exists for ID {media_plan_id}: {e}")
        # If we can't determine, assume it doesn't exist (safer for first save)
        return False

def save(self, workspace_manager: WorkspaceManager, path: Optional[str] = None,
         format_name: Optional[str] = None, overwrite: bool = False,
         include_parquet: bool = True, include_database: bool = True,
         validate_version: bool = True, set_as_current: bool = False,
         **format_options) -> str:
    """
    Save the media plan to a storage location with comprehensive version validation.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: The path where the media plan should be saved. If None or empty,
              a default path is generated based on the media plan ID.
        format_name: Optional format name to use. If not specified, inferred from path
                    or defaults to "json".
        overwrite: If False (default), saves with a new media plan ID if the current
                  plan already exists as a saved file. If True, preserves the existing
                  media plan ID.
        include_parquet: If True (default), also saves a Parquet file for v1.0+ schemas.
        include_database: If True (default), also saves to database if configured.
        validate_version: If True (default), validate schema version compatibility.
        **format_options: Additional format-specific options.

    Returns:
        The path where the media plan was saved.

    Raises:
        StorageError: If the media plan cannot be saved.
        SchemaVersionError: If version validation fails.
        WorkspaceInactiveError: If the workspace is inactive.
    """
    # Check if workspace is active
    workspace_manager.check_workspace_active("media plan save")

    # Check if workspace is loaded
    if not workspace_manager.is_loaded:
        workspace_manager.load()

    # Set is_current to true of set_as_current is true
    if set_as_current:
        # Set this plan as current - the normal save logic will handle this
        self.meta.is_current = True
        logger.debug(f"set_as_current=True: Will set media plan '{self.meta.id}' as current after save")

    # Get resolved workspace config
    workspace_config = workspace_manager.get_resolved_config()

    # Validate schema version before saving
    if validate_version:
        current_version = self.meta.schema_version
        if current_version:
            try:
                from mediaplanpy.schema.version_utils import (
                    normalize_version,
                    get_compatibility_type,
                    get_migration_recommendation
                )

                # Check version compatibility
                normalized_version = normalize_version(current_version)
                compatibility = get_compatibility_type(normalized_version)

                if compatibility == "unsupported":
                    recommendation = get_migration_recommendation(normalized_version)
                    raise SchemaVersionError(
                        f"Cannot save media plan with unsupported schema version '{current_version}'. "
                        f"{recommendation.get('message', 'Version upgrade required.')}"
                    )
                elif compatibility == "deprecated":
                    logger.warning(
                        f"Saving media plan with deprecated schema version '{current_version}'. "
                        "Consider upgrading to current version."
                    )

                # Ensure version is in correct 2-digit format
                target_version = f"v{normalized_version}"
                if self.meta.schema_version != target_version:
                    logger.info(f"Normalizing schema version from '{current_version}' to '{target_version}'")
                    self.meta.schema_version = target_version

            except ImportError:
                logger.warning("Version utilities not available, skipping advanced version validation")
        else:
            # Set current version if missing
            from mediaplanpy import __schema_version__
            self.meta.schema_version = f"v{__schema_version__}"
            logger.info(f"Set missing schema version to current: v{__schema_version__}")

    # Determine if this is a first save or subsequent save
    current_id = self.meta.id
    is_first_save = not _media_plan_file_exists(workspace_config, current_id)

    # Handle media plan ID and parent_id based on overwrite parameter and existence
    if not overwrite:
        if is_first_save:
            # First save - keep existing ID, no parent_id (nothing to link to)
            logger.info(f"First save of media plan with ID: {current_id}")
            # Keep existing self.meta.id and don't set parent_id
        else:
            # Subsequent save - create new version with lineage
            # Capture current ID before generating new one (for parent_id lineage)
            parent_id = current_id

            # Generate a new media plan ID
            new_id = f"mediaplan_{uuid.uuid4().hex[:8]}"
            self.meta.id = new_id

            # Set parent_id to maintain lineage
            self.meta.parent_id = parent_id
            logger.info(f"Created new version - ID: {new_id}, parent_id: {parent_id}")
    else:
        # When overwrite=True, preserve existing ID and parent_id regardless of first save
        logger.debug(f"Updating existing media plan ID: {self.meta.id}, parent_id: {self.meta.parent_id}")

    # Update created_at timestamp regardless of overwrite value
    self.meta.created_at = datetime.now()

    # Validation: ensure parent_id doesn't equal current ID (defensive programming)
    if self.meta.parent_id == self.meta.id:
        logger.warning(f"parent_id equals current ID ({self.meta.id}), setting parent_id to None")
        self.meta.parent_id = None

    # Generate default path if not provided
    if not path:
        # Default format is json if not specified
        default_format = format_name or "json"
        # Get format extension (remove leading dot if present)
        format_handler = get_format_handler_instance(default_format)
        extension = format_handler.get_file_extension()
        if extension.startswith('.'):
            extension = extension[1:]

        # Use media plan ID as filename
        mediaplan_id = self.meta.id
        # Sanitize media plan ID for use as a filename
        mediaplan_id = mediaplan_id.replace('/', '_').replace('\\', '_')

        # Generate path: mediaplans/mediaplan_id.extension
        path = os.path.join(MEDIAPLANS_SUBDIR, f"{mediaplan_id}.{extension}")

    # If path doesn't already include the mediaplans subdirectory, add it
    if not path.startswith(MEDIAPLANS_SUBDIR):
        path = os.path.join(MEDIAPLANS_SUBDIR, os.path.basename(path))

    # Convert model to dictionary
    data = self.to_dict()

    # Validate data structure if version validation is enabled
    if validate_version:
        try:
            format_handler = get_format_handler_instance(format_name or "json")
            if hasattr(format_handler, 'validate_media_plan_structure'):
                structure_errors = format_handler.validate_media_plan_structure(data)
                if structure_errors:
                    raise StorageError(f"Media plan structure validation failed: {'; '.join(structure_errors)}")
        except Exception as e:
            logger.warning(f"Could not validate media plan structure: {e}")

    # Get storage backend to create subdirectory
    try:
        from mediaplanpy.storage import get_storage_backend
        storage_backend = get_storage_backend(workspace_config)

        # Create mediaplans subdirectory if needed
        if hasattr(storage_backend, 'create_directory'):
            storage_backend.create_directory(MEDIAPLANS_SUBDIR)
    except Exception as e:
        logger.warning(f"Could not ensure mediaplans directory exists: {e}")

    # Write to storage with version validation
    try:
        format_options_copy = format_options.copy()
        if validate_version:
            format_options_copy['validate_version'] = True

        storage_write_mediaplan(workspace_config, data, path, format_name, **format_options_copy)
        logger.info(f"Media plan saved to {path}")
    except SchemaVersionError:
        # Re-raise version errors
        raise
    except Exception as e:
        raise StorageError(f"Failed to save media plan to {path}: {e}")

    # Also save Parquet file for v1.0+ schemas
    if include_parquet and self._should_save_parquet():
        parquet_path = self._get_parquet_path(path)

        # Create separate options for Parquet with version validation
        parquet_options = {k: v for k, v in format_options.items()
                           if k in ['compression']}
        if validate_version:
            parquet_options['validate_version'] = True

        try:
            # Write Parquet file
            storage_write_mediaplan(
                workspace_config, data, parquet_path,
                format_name="parquet", **parquet_options
            )
            logger.info(f"Also saved Parquet file: {parquet_path}")
        except SchemaVersionError as e:
            logger.warning(f"Parquet save failed due to version issue: {e}")
        except Exception as e:
            logger.warning(f"Parquet save failed: {e}")

    # Save to database if configured and enabled
    if include_database:
        try:
            db_saved = self.save_to_database(workspace_manager, overwrite=overwrite)
            if db_saved:
                logger.info(f"Media plan {self.meta.id} synchronized to database")
            else:
                logger.debug(f"Database sync skipped for media plan {self.meta.id}")
        except Exception as e:
            # Database errors should not prevent file save
            logger.warning(f"Database sync failed for media plan {self.meta.id}: {e}")

    # Set other media plans in campaign as non-current if set_as_current is true
    if set_as_current:
        try:
            # Delegate to set_as_current method with update_self=False
            # (this plan is already saved, just coordinate with others)
            result = self.set_as_current(workspace_manager, update_self=False)

            logger.info(f"Coordinated current status after save: {result['total_affected']} plans affected")

        except Exception as e:
            # Don't fail the main save operation, but log the issue
            logger.warning(f"Media plan saved successfully, but could not coordinate current status: {e}")

    # Return the path where the media plan was saved
    return path


def load(cls, workspace_manager: WorkspaceManager, path: Optional[str] = None,
         media_plan_id: Optional[str] = None, campaign_id: Optional[str] = None,
         format_name: Optional[str] = None, validate_version: bool = True,
         auto_migrate: bool = True) -> 'MediaPlan':
    """
    Load a media plan from a storage location with version handling and migration.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: The path to the media plan file.
        media_plan_id: The media plan ID to load.
        campaign_id: The campaign ID to load (deprecated).
        format_name: Optional format name to use.
        validate_version: If True (default), validate and handle version compatibility.
        auto_migrate: If True (default), automatically migrate compatible versions.

    Returns:
        A MediaPlan instance.

    Raises:
        StorageError: If the media plan cannot be loaded.
        SchemaVersionError: If version is incompatible and migration fails.
        ValueError: If no identifier is provided.
    """
    # Check if workspace is loaded
    if not workspace_manager.is_loaded:
        workspace_manager.load()

    # Get resolved workspace config
    workspace_config = workspace_manager.get_resolved_config()

    # Generate default path if not provided but media_plan_id or campaign_id is
    if not path:
        if media_plan_id:
            # Use media plan ID (new preferred approach)
            # Default format is json if not specified
            default_format = format_name or "json"
            # Get format extension
            format_handler = get_format_handler_instance(default_format)
            extension = format_handler.get_file_extension()
            if extension.startswith('.'):
                extension = extension[1:]

            # Sanitize media plan ID for use as a filename
            safe_media_plan_id = media_plan_id.replace('/', '_').replace('\\', '_')

            # Generate path: mediaplans/media_plan_id.extension
            path = os.path.join(MEDIAPLANS_SUBDIR, f"{safe_media_plan_id}.{extension}")

            logger.info(f"Loading media plan by ID: {media_plan_id}")

        elif campaign_id:
            # Use campaign ID (backward compatibility)
            logger.warning("Loading by campaign_id is deprecated. Consider using media_plan_id instead.")

            # Default format is json if not specified
            default_format = format_name or "json"
            # Get format extension
            format_handler = get_format_handler_instance(default_format)
            extension = format_handler.get_file_extension()
            if extension.startswith('.'):
                extension = extension[1:]

            # Sanitize campaign ID for use as a filename
            safe_campaign_id = campaign_id.replace('/', '_').replace('\\', '_')

            # Generate path: mediaplans/campaign_id.extension (old approach)
            path = os.path.join(MEDIAPLANS_SUBDIR, f"{safe_campaign_id}.{extension}")

            logger.info(f"Loading media plan by campaign ID (deprecated): {campaign_id}")

    # Validate we have a path
    if not path:
        raise ValueError("Either path, media_plan_id, or campaign_id must be provided")

    # If path doesn't already include the mediaplans subdirectory, try both locations
    if not path.startswith(MEDIAPLANS_SUBDIR):
        # First try in the mediaplans subdirectory
        mediaplans_path = os.path.join(MEDIAPLANS_SUBDIR, os.path.basename(path))

        try:
            # Get storage backend to check if file exists in new location
            from mediaplanpy.storage import get_storage_backend
            storage_backend = get_storage_backend(workspace_config)

            if storage_backend.exists(mediaplans_path):
                path = mediaplans_path
            # Otherwise, keep the original path (for backward compatibility)
        except Exception as e:
            logger.warning(f"Error checking mediaplans subdirectory: {e}")

    # Read from storage with version handling
    try:
        # Create format options with version validation
        format_options = {}
        if validate_version:
            format_options['validate_version'] = True

        data = storage_read_mediaplan(workspace_config, path, format_name)

        # Extract and validate schema version
        file_version = data.get("meta", {}).get("schema_version")
        logger.debug(f"Loaded media plan with schema version: {file_version}")

        # Handle version compatibility and migration
        if validate_version and file_version:
            try:
                from mediaplanpy.schema.version_utils import (
                    normalize_version,
                    get_compatibility_type,
                    get_migration_recommendation
                )

                # Check compatibility
                normalized_version = normalize_version(file_version)
                compatibility = get_compatibility_type(normalized_version)

                logger.debug(f"Version compatibility: {compatibility}")

                if compatibility == "unsupported":
                    if auto_migrate:
                        # Try to migrate using schema migrator
                        try:
                            from mediaplanpy.schema import SchemaMigrator
                            from mediaplanpy import __schema_version__

                            migrator = SchemaMigrator()
                            current_version = f"v{__schema_version__}"

                            logger.info(f"Attempting migration from {file_version} to {current_version}")
                            migrated_data = migrator.migrate(data, file_version, current_version)
                            data = migrated_data

                            logger.info(f"✅ Successfully migrated media plan from {file_version} to {current_version}")

                        except Exception as migration_error:
                            recommendation = get_migration_recommendation(normalized_version)
                            raise SchemaVersionError(
                                f"Schema version '{file_version}' is not supported and migration failed: {migration_error}. "
                                f"{recommendation.get('message', 'Manual upgrade required.')}"
                            )
                    else:
                        recommendation = get_migration_recommendation(normalized_version)
                        raise SchemaVersionError(
                            f"Schema version '{file_version}' is not supported. "
                            f"{recommendation.get('message', 'Version upgrade required.')}"
                        )

                elif compatibility == "deprecated":
                    logger.warning(
                        f"⚠️ Media plan uses deprecated schema version '{file_version}'. "
                        "Consider upgrading to current version."
                    )
                    if auto_migrate:
                        # Auto-upgrade deprecated versions
                        from mediaplanpy import __schema_version__
                        current_version = f"v{__schema_version__}"

                        if "meta" not in data:
                            data["meta"] = {}
                        data["meta"]["schema_version"] = current_version

                        logger.info(f"Auto-upgraded deprecated version from {file_version} to {current_version}")

                elif compatibility == "forward_minor":
                    from mediaplanpy import __schema_version__
                    current_version = f"v{__schema_version__}"
                    logger.warning(
                        f"⚠️ Media plan uses schema {file_version}. Current SDK supports up to {current_version}. "
                        f"File imported and downgraded to {current_version} - new fields preserved but may be inactive."
                    )
                    if auto_migrate:
                        # Update version to current (Pydantic will preserve unknown fields)
                        if "meta" not in data:
                            data["meta"] = {}
                        data["meta"]["schema_version"] = current_version

                elif compatibility == "backward_compatible":
                    from mediaplanpy import __schema_version__
                    current_version = f"v{__schema_version__}"
                    logger.info(f"ℹ️ Media plan version-bumped from schema {file_version} to {current_version}")
                    if auto_migrate:
                        # Update version to current
                        if "meta" not in data:
                            data["meta"] = {}
                        data["meta"]["schema_version"] = current_version

            except ImportError:
                logger.warning("Version utilities not available, skipping version compatibility checks")

        # Create MediaPlan instance from dictionary
        # The from_dict method will handle any remaining version compatibility
        media_plan = cls.from_dict(data)

        logger.info(f"Media plan loaded from {path}")
        return media_plan

    except FileReadError:
        # Try legacy path as fallback if path was already modified
        if path.startswith(MEDIAPLANS_SUBDIR):
            legacy_path = os.path.basename(path)
            try:
                format_options = {}
                if validate_version:
                    format_options['validate_version'] = True

                data = storage_read_mediaplan(workspace_config, legacy_path, format_name)

                # Apply same version handling as above
                if validate_version:
                    file_version = data.get("meta", {}).get("schema_version")
                    if file_version:
                        try:
                            from mediaplanpy.schema.version_utils import get_compatibility_type
                            compatibility = get_compatibility_type(file_version)

                            if compatibility in ["deprecated", "backward_compatible"] and auto_migrate:
                                from mediaplanpy import __schema_version__
                                current_version = f"v{__schema_version__}"
                                data["meta"]["schema_version"] = current_version
                                logger.info(f"Auto-migrated legacy file from {file_version} to {current_version}")
                        except ImportError:
                            pass

                # Create MediaPlan instance from dictionary
                media_plan = cls.from_dict(data)

                logger.warning(f"Media plan loaded from legacy path {legacy_path}. Future saves will use new path structure.")
                return media_plan
            except Exception:
                # If legacy path also failed, re-raise original error
                pass

        # If all attempts failed, raise appropriate error
        raise StorageError(f"Failed to read media plan from {path}")
    except SchemaVersionError:
        # Re-raise version errors
        raise
    except Exception as e:
        raise StorageError(f"Failed to load media plan from {path}: {e}")


def delete(self, workspace_manager: 'WorkspaceManager',
           dry_run: bool = False, include_database: bool = True) -> Dict[str, Any]:
    """
    Delete the media plan files from workspace storage with version awareness.

    This method removes both JSON and Parquet files associated with this media plan
    from the workspace storage, considering version compatibility for database operations.

    Args:
        workspace_manager: The WorkspaceManager instance.
        dry_run: If True, shows what would be deleted without actually deleting files.
        include_database: If True, also delete from database if configured.

    Returns:
        Dictionary containing deletion results and version information.

    Raises:
        WorkspaceError: If no configuration is loaded.
        WorkspaceInactiveError: If the workspace is inactive.
        StorageError: If deletion fails due to storage backend issues.
    """
    # Check if workspace is active (deletion is a restricted operation)
    workspace_manager.check_workspace_active("media plan deletion")

    # Check if workspace is loaded
    if not workspace_manager.is_loaded:
        workspace_manager.load()

    # Get resolved workspace config and storage backend
    workspace_config = workspace_manager.get_resolved_config()

    try:
        from mediaplanpy.storage import get_storage_backend
        storage_backend = get_storage_backend(workspace_config)
    except Exception as e:
        raise StorageError(f"Failed to get storage backend: {e}")

    # Initialize result dictionary with version information
    result = {
        "deleted_files": [],
        "errors": [],
        "mediaplan_id": self.meta.id,
        "schema_version": self.meta.schema_version,
        "dry_run": dry_run,
        "files_found": 0,
        "files_deleted": 0,
        "database_deleted": False,
        "database_rows_deleted": 0,
        "version_compatible": True,
        "version_warnings": []
    }

    # Check version compatibility for operations
    try:
        from mediaplanpy.schema.version_utils import get_compatibility_type
        compatibility = get_compatibility_type(self.meta.schema_version.lstrip('v'))

        if compatibility == "unsupported":
            result["version_compatible"] = False
            result["version_warnings"].append(
                f"Media plan has unsupported schema version {self.meta.schema_version}"
            )
        elif compatibility == "deprecated":
            result["version_warnings"].append(
                f"Media plan has deprecated schema version {self.meta.schema_version}"
            )
    except Exception as e:
        result["version_warnings"].append(f"Could not determine version compatibility: {e}")

    # Define file extensions to look for
    extensions = ["json", "parquet"]

    # Sanitize media plan ID for use as filename
    safe_mediaplan_id = self.meta.id.replace('/', '_').replace('\\', '_')

    for extension in extensions:
        # Construct the file path in mediaplans subdirectory
        file_path = os.path.join(MEDIAPLANS_SUBDIR, f"{safe_mediaplan_id}.{extension}")

        try:
            # Check if file exists
            if storage_backend.exists(file_path):
                result["files_found"] += 1

                if dry_run:
                    # For dry run, just add to the list without deleting
                    result["deleted_files"].append(file_path)
                    logger.info(f"[DRY RUN] Would delete: {file_path}")
                else:
                    # Actually delete the file
                    storage_backend.delete_file(file_path)
                    result["deleted_files"].append(file_path)
                    result["files_deleted"] += 1
                    logger.info(f"Deleted media plan file: {file_path}")
            else:
                logger.debug(f"File not found (skipping): {file_path}")

        except Exception as e:
            error_msg = f"Failed to delete {file_path}: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)

    # Handle database deletion if enabled and version compatible
    if include_database and result["version_compatible"]:
        try:
            if self._should_save_to_database(workspace_manager):
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete database records for media plan {self.meta.id}")
                    result["database_deleted"] = True  # Would be deleted
                else:
                    # Actually delete from database
                    from mediaplanpy.storage.database import PostgreSQLBackend
                    db_backend = PostgreSQLBackend(workspace_config)

                    workspace_id = workspace_manager.config.get('workspace_id', 'unknown')
                    deleted_rows = db_backend.delete_media_plan(self.meta.id, workspace_id)

                    result["database_deleted"] = True
                    result["database_rows_deleted"] = deleted_rows

                    logger.info(f"Deleted {deleted_rows} database records for media plan {self.meta.id}")
            else:
                logger.debug("Database deletion skipped - not configured or not applicable")

        except Exception as e:
            error_msg = f"Failed to delete database records: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
    elif include_database and not result["version_compatible"]:
        result["version_warnings"].append("Database deletion skipped due to version incompatibility")

    # Log summary with version information
    if dry_run:
        logger.info(f"[DRY RUN] Media plan '{self.meta.id}' (v{self.meta.schema_version}): "
                   f"found {result['files_found']} files that would be deleted")
        if result["database_deleted"]:
            logger.info(f"[DRY RUN] Database records would also be deleted")
    else:
        logger.info(
            f"Media plan '{self.meta.id}' (v{self.meta.schema_version}): "
            f"deleted {result['files_deleted']} of {result['files_found']} files found"
        )
        if result["database_deleted"]:
            logger.info(f"Also deleted {result['database_rows_deleted']} database records")

    # Log version warnings
    for warning in result["version_warnings"]:
        logger.warning(warning)

    # Raise an error if there were any deletion failures (but not if files didn't exist)
    if result["errors"] and not dry_run:
        raise StorageError(
            f"Failed to delete some files for media plan '{self.meta.id}': {'; '.join(result['errors'])}")

    return result


def _should_save_parquet(self) -> bool:
    """
    Check if Parquet should be saved based on schema version compatibility.

    Returns:
        True if the schema version supports Parquet export (v1.0+).
    """
    version = self.meta.schema_version
    if not version:
        return False

    try:
        from mediaplanpy.schema.version_utils import normalize_version, get_compatibility_type

        # Normalize and check compatibility
        normalized_version = normalize_version(version)
        compatibility = get_compatibility_type(normalized_version)

        # Only save Parquet for supported versions
        if compatibility == "unsupported":
            return False

        # Check if major version is 1.0 or higher
        major_version = int(normalized_version.split('.')[0])
        return major_version >= 1

    except Exception as e:
        logger.warning(f"Could not determine Parquet compatibility for version {version}: {e}")
        # Fallback: check if version looks like v1.0+
        if version.startswith('v'):
            try:
                major = int(version.split('.')[0][1:])
                return major >= 1
            except (ValueError, IndexError):
                return False
        return False


def _get_parquet_path(self, json_path: str) -> str:
    """
    Get Parquet path from JSON path.

    Args:
        json_path: The JSON file path.

    Returns:
        The corresponding Parquet file path.
    """
    base, _ = os.path.splitext(json_path)
    return f"{base}.parquet"


def get_version_info(self) -> Dict[str, Any]:
    """
    Get comprehensive version information for this media plan.

    Returns:
        Dictionary with version details and compatibility information
    """
    version_info = {
        "schema_version": self.meta.schema_version,
        "media_plan_id": self.meta.id,
        "created_at": self.meta.created_at,
        "created_by": self.meta.created_by
    }

    # Add compatibility information
    if self.meta.schema_version:
        try:
            from mediaplanpy.schema.version_utils import (
                normalize_version,
                get_compatibility_type,
                get_migration_recommendation
            )
            from mediaplanpy import __version__, __schema_version__

            normalized_version = normalize_version(self.meta.schema_version)
            compatibility = get_compatibility_type(normalized_version)

            version_info.update({
                "normalized_version": normalized_version,
                "compatibility_type": compatibility,
                "current_sdk_version": __version__,
                "current_schema_version": __schema_version__,
                "is_current": normalized_version == __schema_version__,
                "supports_parquet": self._should_save_parquet(),
                "migration_needed": compatibility in ["deprecated", "backward_compatible"]
            })

            if compatibility == "unsupported":
                recommendation = get_migration_recommendation(normalized_version)
                version_info["migration_recommendation"] = recommendation

        except Exception as e:
            version_info["version_check_error"] = str(e)

    return version_info


# Patch methods into MediaPlan class
MediaPlan.save = save
MediaPlan.load = classmethod(load)
MediaPlan.delete = delete
MediaPlan._should_save_parquet = _should_save_parquet
MediaPlan._get_parquet_path = _get_parquet_path
MediaPlan.get_version_info = get_version_info