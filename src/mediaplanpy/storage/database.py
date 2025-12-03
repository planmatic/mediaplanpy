"""
Enhanced PostgreSQL backend for mediaplanpy with comprehensive v2.0 schema support.

This module provides PostgreSQL database integration with full v2.0 field support,
enhanced version validation, migration logic, and v0.0 rejection for the new
2-digit versioning strategy.

Key Features:
- Full support for all v2.0 schema fields including:
  * New campaign fields (agency, advertiser, campaign type, workflow status)
  * New lineitem fields (currency, dayparts, inventory, 17 new metrics)
  * New meta fields (created_by_id/name, status flags, parent_id)
- Enhanced version validation with 2-digit format support
- Automatic migration from v1.0.0 format to v2.0 format
- Complete rejection of v0.0 schema versions (no longer supported)
- Database constraints to enforce version compatibility
- Performance indexes for v2.0 fields
- Comprehensive validation and statistics methods

Version Compatibility:
- Supports: v1.0, v2.0 (with automatic normalization)
- Rejects: v0.0.x (completely unsupported in SDK v2.0)
- Migrates: v1.0.0 -> 1.0, v2.0.0 -> 2.0 (3-digit to 2-digit format)
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
import pandas as pd

from mediaplanpy.exceptions import StorageError, DatabaseError

logger = logging.getLogger("mediaplanpy.storage.database")

class PostgreSQLBackend:
    """
    PostgreSQL backend for storing flattened media plan data with version support.

    Handles connection management, schema creation, data operations, and version
    migration for media plan database synchronization.
    """

    def __init__(self, workspace_config: Dict[str, Any]):
        """
        Initialize PostgreSQL backend with workspace configuration.

        Args:
            workspace_config: The resolved workspace configuration dictionary.

        Raises:
            DatabaseError: If configuration is invalid or psycopg2 is not available.
        """
        self.config = workspace_config

        # Extract database configuration
        db_config = workspace_config.get('database', {})
        if not db_config.get('enabled', False):
            raise DatabaseError("Database is not enabled in workspace configuration")

        # Validate required configuration
        required_fields = ['host', 'database']
        for field in required_fields:
            if not db_config.get(field):
                raise DatabaseError(f"Missing required database configuration: {field}")

        # Store connection parameters
        self.host = db_config['host']
        self.port = db_config.get('port', 5432)
        self.database = db_config['database']
        self.schema = db_config.get('schema', 'public')
        self.table_name = db_config.get('table_name', 'media_plans')
        self.username = db_config.get('username')
        self.password_env_var = db_config.get('password_env_var')
        self.ssl = db_config.get('ssl', True)
        self.connection_timeout = db_config.get('connection_timeout', 30)
        self.auto_create_table = db_config.get('auto_create_table', True)

        # Get password from environment variable
        self.password = None
        if self.password_env_var:
            self.password = os.environ.get(self.password_env_var)
            if not self.password:
                logger.warning(f"Database password environment variable '{self.password_env_var}' not found")

        # Check if psycopg2 is available
        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.psycopg2_extras = psycopg2.extras
        except ImportError:
            raise DatabaseError(
                "psycopg2-binary is required for database functionality. "
                "Install it with: pip install psycopg2-binary"
            )

        logger.info(f"Initialized PostgreSQL backend for {self.host}:{self.port}/{self.database}")

    def get_connection_params(self) -> Dict[str, Any]:
        """
        Get connection parameters for psycopg2.

        Returns:
            Dictionary of connection parameters.
        """
        params = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'connect_timeout': self.connection_timeout,
        }

        if self.username:
            params['user'] = self.username

        if self.password:
            params['password'] = self.password

        if self.ssl:
            params['sslmode'] = 'require'
        else:
            params['sslmode'] = 'disable'

        return params

    def connect(self):
        """
        Create a database connection.

        Returns:
            psycopg2 connection object.

        Raises:
            DatabaseError: If connection fails.
        """
        try:
            conn_params = self.get_connection_params()
            connection = self.psycopg2.connect(**conn_params)

            # Set autocommit to False for transaction control
            connection.autocommit = False

            logger.debug(f"Connected to PostgreSQL database: {self.host}:{self.port}/{self.database}")
            return connection

        except Exception as e:
            raise DatabaseError(f"Failed to connect to PostgreSQL database: {e}")

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def get_table_schema(self) -> List[Tuple[str, str]]:
        """
        Define the table schema matching Parquet export format plus workspace fields.
        Updated for v3.0 schema support using shared schema definition.

        Returns:
            List of (column_name, column_type) tuples.
        """
        # Use shared schema definition for v3.0 fields
        from mediaplanpy.storage.schema_columns import get_database_schema

        # Get base schema from shared definition (includes workspace fields)
        schema = get_database_schema(include_workspace_fields=True)

        # Add placeholder indicator and version tracking
        schema.append(('is_placeholder', 'BOOLEAN DEFAULT FALSE'))
        schema.append(('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
        schema.append(('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))

        return schema

    def validate_schema_version(self, schema_version: str) -> bool:
        """
        Validate that a schema version follows the 2-digit format and is compatible.

        Args:
            schema_version: Schema version to validate

        Returns:
            True if version is valid and compatible

        Raises:
            DatabaseError: If version is invalid or incompatible
        """
        if not schema_version:
            raise DatabaseError("Schema version cannot be empty")

        # Import version utilities
        try:
            from mediaplanpy.schema.version_utils import (
                validate_version_format,
                normalize_version,
                get_compatibility_type
            )

            # Normalize version to 2-digit format
            try:
                normalized_version = normalize_version(schema_version)
            except Exception as e:
                raise DatabaseError(f"Invalid schema version format '{schema_version}': {e}")

            # Check compatibility
            compatibility = get_compatibility_type(normalized_version)

            if compatibility == "unsupported":
                raise DatabaseError(f"Schema version '{schema_version}' is not supported by current SDK")
            elif compatibility in ["deprecated", "forward_minor"]:
                logger.warning(f"Schema version '{schema_version}' has compatibility issues: {compatibility}")

            return True

        except ImportError:
            # Fallback validation if version utilities not available
            import re
            if not re.match(r'^v?[0-9]+\.[0-9]+$', schema_version.strip()):
                raise DatabaseError(f"Invalid schema version format '{schema_version}'. Expected format: 'X.Y'")
            return True

    def migrate_existing_data(self) -> Dict[str, Any]:
        """
        Migrate existing data to support 2-digit versioning.

        This method:
        1. Finds records with old 3-digit versions (v1.0.0 -> 1.0)
        2. Updates them to 2-digit format
        3. Validates version compatibility
        4. Rejects any v0.0 records (no longer supported)

        Returns:
            Dictionary with migration results
        """
        migration_result = {
            "records_found": 0,
            "records_migrated": 0,
            "v0_records_rejected": 0,
            "errors": []
        }

        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    # Find all distinct schema versions in the table
                    cursor.execute(f"""
                        SELECT DISTINCT meta_schema_version, COUNT(*) as count
                        FROM {self.schema}.{self.table_name}
                        WHERE meta_schema_version IS NOT NULL
                        GROUP BY meta_schema_version
                    """)

                    version_counts = cursor.fetchall()

                    for version, count in version_counts:
                        migration_result["records_found"] += count

                        # Check for v0.0 records - these need to be rejected
                        if version and (version.startswith('0.') or version.startswith('v0.')):
                            # Count and log v0.0 records, but don't migrate them
                            migration_result["v0_records_rejected"] += count
                            error_msg = (
                                f"Found {count} records with unsupported schema version '{version}' (v0.0.x). "
                                f"These records cannot be migrated in SDK v2.0. "
                                f"Use SDK v1.x to migrate v0.0 plans to v1.0 first."
                            )
                            migration_result["errors"].append(error_msg)
                            logger.error(error_msg)
                            continue

                        # Check if this is a 3-digit version that needs migration
                        if version and (version.startswith('v') and version.count('.') >= 2):
                            try:
                                # Convert v1.0.0 -> 1.0
                                from mediaplanpy.schema.version_utils import normalize_version
                                normalized_version = normalize_version(version)

                                # Validate the normalized version
                                self.validate_schema_version(normalized_version)

                                # Update records with this version
                                cursor.execute(f"""
                                    UPDATE {self.schema}.{self.table_name}
                                    SET meta_schema_version = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE meta_schema_version = %s
                                """, (normalized_version, version))

                                updated_count = cursor.rowcount
                                migration_result["records_migrated"] += updated_count

                                logger.info(
                                    f"Migrated {updated_count} records from version '{version}' to '{normalized_version}'")

                            except Exception as e:
                                error_msg = f"Failed to migrate version '{version}': {str(e)}"
                                migration_result["errors"].append(error_msg)
                                logger.error(error_msg)

                        elif version and not version.startswith('v') and version.count('.') == 1:
                            # Already in 2-digit format, validate compatibility
                            try:
                                self.validate_schema_version(version)
                                logger.debug(f"Version '{version}' is already in correct 2-digit format")
                            except Exception as e:
                                error_msg = f"Version '{version}' validation failed: {str(e)}"
                                migration_result["errors"].append(error_msg)

                    # Commit all migrations
                    conn.commit()

        except Exception as e:
            error_msg = f"Database migration failed: {str(e)}"
            migration_result["errors"].append(error_msg)
            logger.error(error_msg)

        return migration_result

    def table_exists(self) -> bool:
        """
        Check if the media plans table exists.

        Returns:
            True if table exists, False otherwise.

        Raises:
            DatabaseError: If query fails.
        """
        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = %s 
                            AND table_name = %s
                        )
                    """, (self.schema, self.table_name))

                    return cursor.fetchone()[0]

        except Exception as e:
            raise DatabaseError(f"Failed to check if table exists: {e}")

    def create_table(self) -> None:
        """
        Create the media plans table if it doesn't exist.
        Updated to include version compatibility triggers and v2.0 field support.

        Raises:
            DatabaseError: If table creation fails.
        """
        if self.table_exists():
            logger.debug(f"Table {self.schema}.{self.table_name} already exists")
            # Run migration for existing table
            migration_result = self.migrate_existing_data()
            if migration_result["errors"]:
                logger.warning(f"Migration completed with errors: {migration_result['errors']}")
            else:
                logger.info(f"Migration completed: {migration_result['records_migrated']} records updated")
            return

        try:
            schema_def = self.get_table_schema()
            column_definitions = [f"{name} {type_def}" for name, type_def in schema_def]

            # Create table with primary key and constraints
            create_sql = f"""
            CREATE TABLE {self.schema}.{self.table_name} (
                {', '.join(column_definitions)},
                PRIMARY KEY (workspace_id, meta_id, lineitem_id),
                CONSTRAINT valid_schema_version CHECK (
                    meta_schema_version IS NULL OR 
                    meta_schema_version ~ '^[0-9]+\\.[0-9]+$'
                ),
                CONSTRAINT no_v0_versions CHECK (
                    meta_schema_version IS NULL OR 
                    NOT (meta_schema_version ~ '^v?0\\.')
                )
            )
            """

            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_sql)

                    # Create index on workspace_id
                    cursor.execute(f"""
                        CREATE INDEX idx_{self.table_name}_workspaces
                            ON {self.schema}.{self.table_name} (workspace_id)
                    """)

                    # Create index on meta_id
                    cursor.execute(f"""
                    CREATE INDEX idx_{self.table_name}_plans 
                        ON {self.schema}.{self.table_name} (workspace_id, meta_id) 
                        INCLUDE (meta_is_current, meta_is_archived, campaign_id, campaign_agency_id, campaign_advertiser_id, campaign_product_id)
                    """)

                    # Create index on schema version for efficient querying
                    # DISCONTINUED 20251010 - Not beneficial
                    # cursor.execute(f"""
                    #     CREATE INDEX IF NOT EXISTS idx_{self.table_name}_schema_version
                    #     ON {self.schema}.{self.table_name} (meta_schema_version)
                    # """)

                    # Create additional indexes for v2.0 fields that might be queried frequently
                    # DISCONTINUED 20251010 - Not beneficial
                    v2_indexes = [
                        # f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_campaign_type ON {self.schema}.{self.table_name} (campaign_campaign_type_id)",
                        # f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_workflow_status ON {self.schema}.{self.table_name} (campaign_workflow_status_id)",
                        # f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_agency ON {self.schema}.{self.table_name} (campaign_agency_id)",
                        # f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_advertiser ON {self.schema}.{self.table_name} (campaign_advertiser_id)",
                        # f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_created_by_id ON {self.schema}.{self.table_name} (meta_created_by_id)",
                        # f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_current_plans ON {self.schema}.{self.table_name} (meta_is_current) WHERE meta_is_current = true",
                        # f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_active_plans ON {self.schema}.{self.table_name} (meta_is_archived) WHERE meta_is_archived = false OR meta_is_archived IS NULL"
                    ]

                    for index_sql in v2_indexes:
                        try:
                            cursor.execute(index_sql)
                        except Exception as e:
                            logger.warning(f"Could not create index: {e}")

                    # Create trigger to update updated_at timestamp
                    cursor.execute(f"""
                        CREATE OR REPLACE FUNCTION update_updated_at_column()
                        RETURNS TRIGGER AS $$
                        BEGIN
                            NEW.updated_at = CURRENT_TIMESTAMP;
                            RETURN NEW;
                        END;
                        $$ language 'plpgsql'
                    """)

                    cursor.execute(f"""
                        CREATE TRIGGER update_{self.table_name}_updated_at 
                        BEFORE UPDATE ON {self.schema}.{self.table_name}
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
                    """)

                    conn.commit()

            logger.info(f"Created table {self.schema}.{self.table_name} with version constraints and v2.0 support")

        except Exception as e:
            raise DatabaseError(f"Failed to create table: {e}")

    def ensure_table_exists(self) -> None:
        """
        Ensure the media plans table exists, creating it if necessary.
        Updated to handle v2.0 schema migration.

        Raises:
            DatabaseError: If auto_create_table is False and table doesn't exist.
        """
        if not self.table_exists():
            if self.auto_create_table:
                self.create_table()
            else:
                raise DatabaseError(
                    f"Table {self.schema}.{self.table_name} does not exist and auto_create_table is disabled"
                )
        else:
            # Table exists, run migration to ensure version compatibility
            migration_result = self.migrate_existing_data()
            if migration_result["records_migrated"] > 0:
                logger.info(f"Migrated {migration_result['records_migrated']} existing records to 2-digit versioning")
            if migration_result["v0_records_rejected"] > 0:
                logger.warning(
                    f"Found {migration_result['v0_records_rejected']} unsupported v0.0 records that could not be migrated")

    def delete_media_plan(self, meta_id: str, workspace_id: str) -> int:
        """
        Delete existing records for a media plan.

        Args:
            meta_id: The media plan ID to delete.
            workspace_id: The workspace ID.

        Returns:
            Number of rows deleted.

        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            delete_sql = f"""
            DELETE FROM {self.schema}.{self.table_name} 
            WHERE workspace_id = %s AND meta_id = %s
            """

            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(delete_sql, (workspace_id, meta_id))
                    rows_deleted = cursor.rowcount
                    conn.commit()

            logger.debug(f"Deleted {rows_deleted} rows for media plan {meta_id}")
            return rows_deleted

        except Exception as e:
            raise DatabaseError(f"Failed to delete media plan {meta_id}: {e}")

    def insert_media_plan(self, flattened_data: pd.DataFrame, workspace_id: str, workspace_name: str) -> int:
        """
        Insert media plan data with enhanced v2.0 version validation and field support.

        Args:
            flattened_data: DataFrame with media plan data
            workspace_id: Workspace ID
            workspace_name: Workspace name

        Returns:
            Number of rows inserted

        Raises:
            DatabaseError: If insertion fails or version validation fails
        """
        if flattened_data.empty:
            logger.warning("No data to insert")
            return 0

        try:
            # Add workspace columns
            df = flattened_data.copy()
            df['workspace_id'] = workspace_id
            df['workspace_name'] = workspace_name

            # Validate schema versions in the data
            if 'meta_schema_version' in df.columns:
                for schema_version in df['meta_schema_version'].dropna().unique():
                    try:
                        # Check for v0.0 versions and reject them
                        version_str = str(schema_version)
                        if version_str.startswith('0.') or version_str.startswith('v0.'):
                            raise DatabaseError(
                                f"Schema version '{version_str}' (v0.0.x) is not supported in SDK v2.0. "
                                f"Use SDK v1.x to migrate v0.0 plans to v1.0 first."
                            )

                        # Validate the version
                        self.validate_schema_version(version_str)
                    except DatabaseError as e:
                        logger.error(f"Schema version validation failed: {e}")
                        raise

            # Get table schema to ensure column order and handle new v2.0 fields
            schema_def = self.get_table_schema()
            expected_columns = [col_name for col_name, _ in schema_def]

            # Ensure all expected columns exist, fill missing with None
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = None

            # Reorder columns to match schema
            df = df[expected_columns]

            # Enhanced data type conversion for v2.0 fields
            def fix_numpy_types(values_list):
                """Convert numpy types to Python types with enhanced v2.0 support."""
                import numpy as np
                import pandas as pd

                fixed_values = []
                for row in values_list:
                    fixed_row = []
                    for val in row:
                        if isinstance(val, (np.integer, np.int32, np.int64)):
                            fixed_row.append(int(val))
                        elif isinstance(val, (np.floating, np.float32, np.float64)):
                            fixed_row.append(float(val))
                        elif isinstance(val, (np.bool_, bool)):
                            fixed_row.append(bool(val))
                        elif pd.isna(val):
                            fixed_row.append(None)
                        else:
                            fixed_row.append(val)
                    fixed_values.append(tuple(fixed_row))
                return fixed_values

            # Convert DataFrame to list of tuples for bulk insert
            values = [tuple(row) for row in df.itertuples(index=False, name=None)]
            values = fix_numpy_types(values)

            # Create INSERT statement for execute_values
            insert_sql = f"""
            INSERT INTO {self.schema}.{self.table_name} 
            ({', '.join(expected_columns)}) 
            VALUES %s
            """

            with self.connect() as conn:
                with conn.cursor() as cursor:
                    # Use execute_values for better performance with multiple rows
                    self.psycopg2_extras.execute_values(
                        cursor, insert_sql, values, page_size=100
                    )
                    rows_inserted = cursor.rowcount
                    conn.commit()

            logger.info(f"Inserted {rows_inserted} rows for media plan with v2.0 schema support")
            return rows_inserted

        except Exception as e:
            raise DatabaseError(f"Failed to insert media plan data: {e}")

    def validate_schema(self) -> List[str]:
        """
        Validate that the database table schema matches expectations for v2.0.

        Returns:
            List of validation error messages, empty if validation succeeds.
        """
        errors = []

        try:
            if not self.table_exists():
                errors.append(f"Table {self.schema}.{self.table_name} does not exist")
                return errors

            # Get actual table columns
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    """, (self.schema, self.table_name))

                    actual_columns = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

            # Get expected schema for v2.0
            expected_schema = self.get_table_schema()
            expected_columns = {col_name for col_name, _ in expected_schema}

            # Check for missing v2.0 columns
            missing_columns = expected_columns - set(actual_columns.keys())
            if missing_columns:
                v2_missing = []
                v1_missing = []

                # Categorize missing columns
                v2_new_fields = [
                    'campaign_budget_currency', 'campaign_agency_id', 'campaign_agency_name',
                    'campaign_advertiser_id', 'campaign_advertiser_name', 'campaign_product_id',
                    'campaign_campaign_type_id', 'campaign_campaign_type_name',
                    'campaign_workflow_status_id', 'campaign_workflow_status_name',
                    'lineitem_cost_currency', 'lineitem_dayparts', 'lineitem_dayparts_custom',
                    'lineitem_inventory', 'lineitem_inventory_custom',
                    'meta_created_by_id', 'meta_created_by_name', 'meta_is_current',
                    'meta_is_archived', 'meta_parent_id',
                    'lineitem_metric_engagements', 'lineitem_metric_followers', 'lineitem_metric_visits',
                    'lineitem_metric_leads', 'lineitem_metric_sales', 'lineitem_metric_add_to_cart',
                    'lineitem_metric_app_install', 'lineitem_metric_application_start',
                    'lineitem_metric_application_complete', 'lineitem_metric_contact_us',
                    'lineitem_metric_download', 'lineitem_metric_signup', 'lineitem_metric_max_daily_spend',
                    'lineitem_metric_max_daily_impressions', 'lineitem_metric_audience_size'
                ]

                for col in missing_columns:
                    if col in v2_new_fields:
                        v2_missing.append(col)
                    else:
                        v1_missing.append(col)

                if v2_missing:
                    errors.append(f"Missing v2.0 columns: {', '.join(v2_missing)}")
                if v1_missing:
                    errors.append(f"Missing v1.0 columns: {', '.join(v1_missing)}")

            # Check for extra columns (informational, not an error)
            extra_columns = set(actual_columns.keys()) - expected_columns
            if extra_columns:
                logger.info(f"Extra columns in table: {', '.join(extra_columns)}")

            # Check version constraints exist
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    # Check for schema version validation constraint
                    cursor.execute("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_schema = %s AND table_name = %s 
                        AND constraint_type = 'CHECK'
                        AND constraint_name = 'valid_schema_version'
                    """, (self.schema, self.table_name))

                    if not cursor.fetchone():
                        errors.append("Missing schema version validation constraint")

                    # Check for v0.0 rejection constraint
                    cursor.execute("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_schema = %s AND table_name = %s 
                        AND constraint_type = 'CHECK'
                        AND constraint_name = 'no_v0_versions'
                    """, (self.schema, self.table_name))

                    if not cursor.fetchone():
                        errors.append("Missing v0.0 version rejection constraint")

        except Exception as e:
            errors.append(f"Schema validation failed: {e}")

        return errors

    def get_full_table_name(self) -> str:
        """
        Get the fully qualified table name.

        Returns:
            The full table name including schema.
        """
        return f"{self.schema}.{self.table_name}"

    def get_version_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about schema versions in the database.

        Returns:
            Dictionary with version statistics and v2.0 compatibility info
        """
        stats = {
            "total_records": 0,
            "version_distribution": {},
            "invalid_versions": [],
            "v0_records_found": 0,
            "migration_needed": False,
            "v2_field_usage": {}
        }

        try:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    # Get total record count
                    cursor.execute(f"SELECT COUNT(*) FROM {self.schema}.{self.table_name}")
                    stats["total_records"] = cursor.fetchone()[0]

                    # Get version distribution
                    cursor.execute(f"""
                        SELECT meta_schema_version, COUNT(*) as count
                        FROM {self.schema}.{self.table_name}
                        GROUP BY meta_schema_version
                        ORDER BY count DESC
                    """)

                    for version, count in cursor.fetchall():
                        if version:
                            stats["version_distribution"][version] = count

                            # Check if this version needs migration (3-digit format)
                            if version.startswith('v') and version.count('.') >= 2:
                                stats["migration_needed"] = True
                                if version not in stats["invalid_versions"]:
                                    stats["invalid_versions"].append(version)

                            # Check for v0.0 versions (should be rejected)
                            if version.startswith('0.') or version.startswith('v0.'):
                                stats["v0_records_found"] += count

                    # Analyze usage of new v2.0 fields
                    v2_fields_to_check = [
                        # New campaign fields
                        'campaign_budget_currency', 'campaign_agency_id', 'campaign_advertiser_id',
                        'campaign_product_id', 'campaign_campaign_type_id', 'campaign_workflow_status_id',
                        # New lineitem fields
                        'lineitem_cost_currency', 'lineitem_dayparts', 'lineitem_inventory',
                        # New meta fields
                        'meta_created_by_id', 'meta_is_current', 'meta_is_archived', 'meta_parent_id',
                        # Sample of new metrics
                        'lineitem_metric_engagements', 'lineitem_metric_leads', 'lineitem_metric_sales'
                    ]

                    for field in v2_fields_to_check:
                        try:
                            cursor.execute(f"""
                                SELECT COUNT(*) 
                                FROM {self.schema}.{self.table_name} 
                                WHERE {field} IS NOT NULL AND {field} != ''
                            """)
                            usage_count = cursor.fetchone()[0]
                            if usage_count > 0:
                                stats["v2_field_usage"][field] = usage_count
                        except Exception:
                            # Field might not exist in older schemas
                            pass

        except Exception as e:
            logger.error(f"Failed to get version statistics: {e}")

        return stats