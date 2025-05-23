"""
Database integration for MediaPlan models.

This module enhances the MediaPlan model with methods for automatically
syncing to PostgreSQL database when media plans are saved.
"""

import logging
from typing import Optional
import pandas as pd

from mediaplanpy.exceptions import DatabaseError, StorageError
from mediaplanpy.models.mediaplan import MediaPlan
from mediaplanpy.workspace import WorkspaceManager

logger = logging.getLogger("mediaplanpy.models.mediaplan_database")


def save_to_database(self, workspace_manager: WorkspaceManager, overwrite: bool = False) -> bool:
    """
    Save media plan to configured PostgreSQL database.

    This method is called automatically by MediaPlan.save() when database
    integration is enabled in the workspace configuration.

    Args:
        workspace_manager: The WorkspaceManager instance.
        overwrite: Whether this is an overwrite operation.

    Returns:
        True if database save succeeded, False if it was skipped or failed gracefully.

    Note:
        This method will not raise exceptions - database failures are logged
        as warnings to avoid blocking the file save operation.
    """
    try:
        # Check if we should save to database
        if not self._should_save_to_database(workspace_manager):
            logger.debug("Database save skipped - conditions not met")
            return False

        # Check workspace status (allow warnings for inactive workspaces)
        workspace_manager.check_workspace_active("database save", allow_warnings=True)

        # Get database backend
        from mediaplanpy.storage.database import PostgreSQLBackend
        db_backend = PostgreSQLBackend(workspace_manager.get_resolved_config())

        # Ensure table exists
        db_backend.ensure_table_exists()

        # Get workspace identification
        workspace_id = workspace_manager.config.get('workspace_id', 'unknown')
        workspace_name = workspace_manager.config.get('workspace_name', 'Unknown Workspace')

        # Prepare flattened data
        flattened_data = self._prepare_database_data(workspace_id, workspace_name)

        if flattened_data.empty:
            logger.warning(f"No data to save for media plan {self.meta.id}")
            return False

        # Handle overwrite behavior
        if overwrite:
            # Delete existing records for this media plan
            deleted_count = db_backend.delete_media_plan(self.meta.id, workspace_id)
            logger.info(f"Deleted {deleted_count} existing records for media plan {self.meta.id}")

        # Insert new records
        inserted_count = db_backend.insert_media_plan(flattened_data, workspace_id, workspace_name)

        logger.info(f"Successfully saved media plan {self.meta.id} to database: {inserted_count} records")
        return True

    except ImportError:
        logger.warning("psycopg2-binary not available - database save skipped")
        return False
    except DatabaseError as e:
        logger.warning(f"Database save failed for media plan {self.meta.id}: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error during database save for media plan {self.meta.id}: {e}")
        return False


def _should_save_to_database(self, workspace_manager: WorkspaceManager) -> bool:
    """
    Check if database save should occur based on configuration and schema version.

    Args:
        workspace_manager: The WorkspaceManager instance.

    Returns:
        True if database save should proceed, False otherwise.
    """
    try:
        # Check if workspace is loaded
        if not workspace_manager.is_loaded:
            logger.debug("Workspace not loaded - database save skipped")
            return False

        # Get database configuration
        db_config = workspace_manager.get_resolved_config().get('database', {})

        # Check if database is enabled
        if not db_config.get('enabled', False):
            logger.debug("Database not enabled - save skipped")
            return False

        # Check if we have minimum required configuration
        if not db_config.get('host') or not db_config.get('database'):
            logger.warning("Database enabled but missing required configuration - save skipped")
            return False

        # Only save v1.0.0+ schemas (same logic as Parquet export)
        version = self.meta.schema_version
        if not version or not version.startswith('v'):
            logger.debug(f"Invalid schema version {version} - database save skipped")
            return False

        # Check version number
        try:
            major = int(version.split('.')[0][1:])  # Extract major version number
            if major < 1:
                logger.debug(f"Schema version {version} < v1.0.0 - database save skipped")
                return False
        except (ValueError, IndexError):
            logger.debug(f"Could not parse schema version {version} - database save skipped")
            return False

        return True

    except Exception as e:
        logger.warning(f"Error checking database save conditions: {e}")
        return False


def _prepare_database_data(self, workspace_id: str, workspace_name: str) -> pd.DataFrame:
    """
    Prepare flattened data for database insertion.

    This method reuses the existing Parquet flattening logic to ensure
    consistency between Parquet and database exports.

    Args:
        workspace_id: The workspace ID.
        workspace_name: The workspace name.

    Returns:
        DataFrame with flattened media plan data ready for database insertion.
    """
    try:
        # Import the Parquet format handler to reuse flattening logic
        from mediaplanpy.storage.formats.parquet import ParquetFormatHandler

        # Create format handler instance
        parquet_handler = ParquetFormatHandler()

        # Convert media plan to dictionary
        media_plan_data = self.to_dict()

        # Use the existing flattening method
        flattened_df = parquet_handler._flatten_media_plan(media_plan_data)

        logger.debug(f"Prepared {len(flattened_df)} rows for database insertion")
        return flattened_df

    except Exception as e:
        logger.error(f"Failed to prepare database data: {e}")
        return pd.DataFrame()


def test_database_connection(cls, workspace_manager: WorkspaceManager) -> bool:
    """
    Test database connection for a workspace.

    Args:
        workspace_manager: The WorkspaceManager instance.

    Returns:
        True if connection test succeeds, False otherwise.
    """
    try:
        if not workspace_manager.is_loaded:
            logger.error("Workspace not loaded")
            return False

        db_config = workspace_manager.get_resolved_config().get('database', {})
        if not db_config.get('enabled', False):
            logger.error("Database not enabled")
            return False

        from mediaplanpy.storage.database import PostgreSQLBackend
        db_backend = PostgreSQLBackend(workspace_manager.get_resolved_config())

        return db_backend.test_connection()

    except ImportError:
        logger.error("psycopg2-binary not available")
        return False
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def create_database_table(cls, workspace_manager: WorkspaceManager) -> bool:
    """
    Create the database table for media plans.

    Args:
        workspace_manager: The WorkspaceManager instance.

    Returns:
        True if table creation succeeds, False otherwise.
    """
    try:
        if not workspace_manager.is_loaded:
            logger.error("Workspace not loaded")
            return False

        from mediaplanpy.storage.database import PostgreSQLBackend
        db_backend = PostgreSQLBackend(workspace_manager.get_resolved_config())

        db_backend.create_table()
        logger.info(f"Created database table: {db_backend.get_full_table_name()}")
        return True

    except ImportError:
        logger.error("psycopg2-binary not available")
        return False
    except Exception as e:
        logger.error(f"Database table creation failed: {e}")
        return False


def validate_database_schema(cls, workspace_manager: WorkspaceManager) -> bool:
    """
    Validate database schema against expected structure.

    Args:
        workspace_manager: The WorkspaceManager instance.

    Returns:
        True if schema validation succeeds, False otherwise.
    """
    try:
        if not workspace_manager.is_loaded:
            logger.error("Workspace not loaded")
            return False

        from mediaplanpy.storage.database import PostgreSQLBackend
        db_backend = PostgreSQLBackend(workspace_manager.get_resolved_config())

        errors = db_backend.validate_schema()
        if errors:
            logger.error(f"Database schema validation failed: {'; '.join(errors)}")
            return False

        logger.info("Database schema validation successful")
        return True

    except ImportError:
        logger.error("psycopg2-binary not available")
        return False
    except Exception as e:
        logger.error(f"Database schema validation failed: {e}")
        return False


# Patch methods into MediaPlan class
def patch_mediaplan_database_methods():
    """
    Add the database integration methods to the MediaPlan class.
    """
    MediaPlan.save_to_database = save_to_database
    MediaPlan._should_save_to_database = _should_save_to_database
    MediaPlan._prepare_database_data = _prepare_database_data

    # Add utility methods as class methods
    MediaPlan.test_database_connection = classmethod(test_database_connection)
    MediaPlan.create_database_table = classmethod(create_database_table)
    MediaPlan.validate_database_schema = classmethod(validate_database_schema)

    logger.debug("Added database integration methods to MediaPlan class")


# Apply patches when this module is imported
patch_mediaplan_database_methods()