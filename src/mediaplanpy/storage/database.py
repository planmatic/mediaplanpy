"""
Enhanced PostgreSQL backend for mediaplanpy with 2-digit version support.

This module provides PostgreSQL database integration with proper version handling,
migration logic, and compatibility checks for the new 2-digit versioning strategy.
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
        Updated to properly handle 2-digit schema versions.

        Returns:
            List of (column_name, column_type) tuples.
        """
        # Base schema matching ParquetFormatHandler._get_all_columns()
        schema = [
            # Workspace identification (added fields)
            ('workspace_id', 'VARCHAR(255) NOT NULL'),
            ('workspace_name', 'VARCHAR(255) NOT NULL'),

            # Meta fields - updated for 2-digit version support
            ('meta_id', 'VARCHAR(255) NOT NULL'),
            ('meta_schema_version', 'VARCHAR(10)'),  # Reduced size for 2-digit versions (e.g., "1.0")
            ('meta_created_by', 'VARCHAR(255)'),
            ('meta_created_at', 'TIMESTAMP'),
            ('meta_name', 'VARCHAR(255)'),
            ('meta_comments', 'TEXT'),

            # Campaign fields
            ('campaign_id', 'VARCHAR(255) NOT NULL'),
            ('campaign_name', 'VARCHAR(255)'),
            ('campaign_objective', 'TEXT'),
            ('campaign_start_date', 'DATE'),
            ('campaign_end_date', 'DATE'),
            ('campaign_budget_total', 'DECIMAL(15,2)'),
            ('campaign_product_name', 'VARCHAR(255)'),
            ('campaign_product_description', 'TEXT'),
            ('campaign_audience_name', 'VARCHAR(255)'),
            ('campaign_audience_age_start', 'INTEGER'),
            ('campaign_audience_age_end', 'INTEGER'),
            ('campaign_audience_gender', 'VARCHAR(50)'),
            ('campaign_audience_interests', 'TEXT'),  # JSON string
            ('campaign_location_type', 'VARCHAR(50)'),
            ('campaign_locations', 'TEXT'),  # JSON string

            # Line item fields
            ('lineitem_id', 'VARCHAR(255) NOT NULL DEFAULT \'placeholder\''),
            ('lineitem_name', 'VARCHAR(255)'),
            ('lineitem_start_date', 'DATE'),
            ('lineitem_end_date', 'DATE'),
            ('lineitem_cost_total', 'DECIMAL(15,2)'),
            ('lineitem_channel', 'VARCHAR(100)'),
            ('lineitem_channel_custom', 'VARCHAR(255)'),
            ('lineitem_vehicle', 'VARCHAR(255)'),
            ('lineitem_vehicle_custom', 'VARCHAR(255)'),
            ('lineitem_partner', 'VARCHAR(255)'),
            ('lineitem_partner_custom', 'VARCHAR(255)'),
            ('lineitem_media_product', 'VARCHAR(255)'),
            ('lineitem_media_product_custom', 'VARCHAR(255)'),
            ('lineitem_location_type', 'VARCHAR(50)'),
            ('lineitem_location_name', 'VARCHAR(255)'),
            ('lineitem_target_audience', 'VARCHAR(255)'),
            ('lineitem_adformat', 'VARCHAR(100)'),
            ('lineitem_adformat_custom', 'VARCHAR(255)'),
            ('lineitem_kpi', 'VARCHAR(100)'),
            ('lineitem_kpi_custom', 'VARCHAR(255)'),
        ]

        # Add custom dimension fields
        for i in range(1, 11):
            schema.append((f'lineitem_dim_custom{i}', 'VARCHAR(255)'))

        # Add cost fields
        cost_fields = [
            'lineitem_cost_media', 'lineitem_cost_buying', 'lineitem_cost_platform',
            'lineitem_cost_data', 'lineitem_cost_creative'
        ]
        for field in cost_fields:
            schema.append((field, 'DECIMAL(15,2)'))

        # Add custom cost fields
        for i in range(1, 11):
            schema.append((f'lineitem_cost_custom{i}', 'DECIMAL(15,2)'))

        # Add metric fields
        metric_fields = [
            'lineitem_metric_impressions', 'lineitem_metric_clicks', 'lineitem_metric_views'
        ]
        for field in metric_fields:
            schema.append((field, 'DECIMAL(15,2)'))

        # Add custom metric fields
        for i in range(1, 11):
            schema.append((f'lineitem_metric_custom{i}', 'DECIMAL(15,2)'))

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

        Returns:
            Dictionary with migration results
        """
        migration_result = {
            "records_found": 0,
            "records_migrated": 0,
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
                                    SET meta_schema_version = %s
                                    WHERE meta_schema_version = %s
                                """, (normalized_version, version))

                                updated_count = cursor.rowcount
                                migration_result["records_migrated"] += updated_count

                                logger.info(f"Migrated {updated_count} records from version '{version}' to '{normalized_version}'")

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
        Updated to include version compatibility triggers.

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
                )
            )
            """

            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_sql)

                    # Create index on schema version for efficient querying
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_schema_version 
                        ON {self.schema}.{self.table_name} (meta_schema_version)
                    """)

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

            logger.info(f"Created table {self.schema}.{self.table_name} with version constraints")

        except Exception as e:
            raise DatabaseError(f"Failed to create table: {e}")

    def ensure_table_exists(self) -> None:
        """
        Ensure the media plans table exists, creating it if necessary.

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
        Insert media plan data with version validation.

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
                        self.validate_schema_version(str(schema_version))
                    except DatabaseError as e:
                        logger.error(f"Schema version validation failed: {e}")
                        raise

            # Get table schema to ensure column order
            schema_def = self.get_table_schema()
            expected_columns = [col_name for col_name, _ in schema_def]

            # Ensure all expected columns exist, fill missing with None
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = None

            # Reorder columns to match schema
            df = df[expected_columns]

            # Convert numpy types to Python types
            def fix_numpy_types(values_list):
                """Convert numpy types to Python types."""
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

            logger.info(f"Inserted {rows_inserted} rows for media plan")
            return rows_inserted

        except Exception as e:
            raise DatabaseError(f"Failed to insert media plan data: {e}")

    def validate_schema(self) -> List[str]:
        """
        Validate that the database table schema matches expectations.

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

            # Get expected schema
            expected_schema = self.get_table_schema()
            expected_columns = {col_name for col_name, _ in expected_schema}

            # Check for missing columns
            missing_columns = expected_columns - set(actual_columns.keys())
            if missing_columns:
                errors.append(f"Missing columns: {', '.join(missing_columns)}")

            # Check for extra columns (informational, not an error)
            extra_columns = set(actual_columns.keys()) - expected_columns
            if extra_columns:
                logger.info(f"Extra columns in table: {', '.join(extra_columns)}")

            # Check version constraint exists
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_schema = %s AND table_name = %s 
                        AND constraint_type = 'CHECK'
                        AND constraint_name = 'valid_schema_version'
                    """, (self.schema, self.table_name))

                    if not cursor.fetchone():
                        errors.append("Missing schema version validation constraint")

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
            Dictionary with version statistics
        """
        stats = {
            "total_records": 0,
            "version_distribution": {},
            "invalid_versions": [],
            "migration_needed": False
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

        except Exception as e:
            logger.error(f"Failed to get version statistics: {e}")

        return stats