"""
PostgreSQL backend for mediaplanpy.

This module provides PostgreSQL database integration for automatically
syncing media plan data when plans are saved.
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
    PostgreSQL backend for storing flattened media plan data.

    Handles connection management, schema creation, and data operations
    for media plan database synchronization.
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

        Returns:
            List of (column_name, column_type) tuples.
        """
        # Base schema matching ParquetFormatHandler._get_all_columns()
        schema = [
            # Workspace identification (added fields)
            ('workspace_id', 'VARCHAR(255) NOT NULL'),
            ('workspace_name', 'VARCHAR(255) NOT NULL'),

            # Meta fields
            ('meta_id', 'VARCHAR(255) NOT NULL'),
            ('meta_schema_version', 'VARCHAR(50)'),
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
            ('lineitem_id', 'VARCHAR(255)'),
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

        # Add placeholder indicator
        schema.append(('is_placeholder', 'BOOLEAN DEFAULT FALSE'))

        return schema

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

        Raises:
            DatabaseError: If table creation fails.
        """
        if self.table_exists():
            logger.debug(f"Table {self.schema}.{self.table_name} already exists")
            return

        try:
            schema_def = self.get_table_schema()
            column_definitions = [f"{name} {type_def}" for name, type_def in schema_def]

            # Create table with primary key
            create_sql = f"""
            CREATE TABLE {self.schema}.{self.table_name} (
                {', '.join(column_definitions)},
                PRIMARY KEY (workspace_id, meta_id, COALESCE(lineitem_id, 'placeholder'))
            )
            """

            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_sql)
                    conn.commit()

            logger.info(f"Created table {self.schema}.{self.table_name}")

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
        Insert media plan data into the database.

        Args:
            flattened_data: DataFrame with flattened media plan data.
            workspace_id: The workspace ID.
            workspace_name: The workspace name.

        Returns:
            Number of rows inserted.

        Raises:
            DatabaseError: If insertion fails.
        """
        if flattened_data.empty:
            logger.warning("No data to insert")
            return 0

        try:
            # Add workspace columns
            df = flattened_data.copy()
            df['workspace_id'] = workspace_id
            df['workspace_name'] = workspace_name

            # Get table schema to ensure column order
            schema_def = self.get_table_schema()
            expected_columns = [col_name for col_name, _ in schema_def]

            # Ensure all expected columns exist, fill missing with None
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = None

            # Reorder columns to match schema
            df = df[expected_columns]

            # Convert DataFrame to list of tuples for bulk insert
            values = [tuple(row) for row in df.itertuples(index=False, name=None)]

            # Create INSERT statement
            placeholders = ', '.join(['%s'] * len(expected_columns))
            insert_sql = f"""
            INSERT INTO {self.schema}.{self.table_name} 
            ({', '.join(expected_columns)}) 
            VALUES ({placeholders})
            """

            with self.connect() as conn:
                with conn.cursor() as cursor:
                    # Use execute_values for better performance with multiple rows
                    self.psycopg2_extras.execute_values(
                        cursor, insert_sql, values, template=None, page_size=100
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