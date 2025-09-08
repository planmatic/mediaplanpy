"""
Updated workspace query module to support mediaplans subdirectory and handle placeholder records.

This module updates the query methods to look for Parquet files
in the mediaplans subdirectory of the workspace storage and properly handle
placeholder records for empty media plans.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Union
from mediaplanpy.exceptions import SQLQueryError
import pandas as pd
import io
import re

logger = logging.getLogger("mediaplanpy.workspace.query")

# Define constants
MEDIAPLANS_SUBDIR = "mediaplans"


def _get_parquet_files(self):
    """
    Find all Parquet files in the workspace storage.

    Returns:
        List of paths to Parquet files in the workspace.
    """
    storage_backend = self.get_storage_backend()

    # First look in the mediaplans subdirectory
    mediaplans_files = []
    try:
        mediaplans_files = storage_backend.list_files(MEDIAPLANS_SUBDIR, "*.parquet")
        # Prepend the subdirectory path if needed
        mediaplans_files = [
            f if f.startswith(MEDIAPLANS_SUBDIR) else os.path.join(MEDIAPLANS_SUBDIR, f)
            for f in mediaplans_files
        ]
    except Exception as e:
        logger.warning(f"Error listing files in mediaplans subdirectory: {e}")

    # Also look in the root directory for backward compatibility
    root_files = []
    try:
        root_files = storage_backend.list_files("", "*.parquet")
        # Filter out any files in the mediaplans subdirectory (already counted)
        root_files = [f for f in root_files if not f.startswith(MEDIAPLANS_SUBDIR)]
    except Exception as e:
        logger.warning(f"Error listing files in root directory: {e}")

    # Combine both lists
    all_files = mediaplans_files + root_files

    return all_files


def _load_workspace_data(self, filters=None):
    """
    Load and combine all Parquet files in the workspace.

    Args:
        filters: Optional pre-filtering to apply while loading

    Returns:
        Combined pandas DataFrame of all media plan data
    """
    storage_backend = self.get_storage_backend()
    parquet_files = self._get_parquet_files()

    if not parquet_files:
        logger.warning("No Parquet files found in workspace")
        return pd.DataFrame()

    dataframes = []
    for file_path in parquet_files:
        try:
            # Read the file into a DataFrame
            content = storage_backend.read_file(file_path, binary=True)
            buffer = io.BytesIO(content)
            df = pd.read_parquet(buffer)

            # Apply pre-filtering if provided (optimization)
            if filters:
                df = self._apply_filters(df, filters)

            if not df.empty:
                dataframes.append(df)

        except Exception as e:
            logger.error(f"Error loading Parquet file {file_path}: {e}")

    if not dataframes:
        return pd.DataFrame()

    return pd.concat(dataframes, ignore_index=True)


def _apply_filters(self, df, filters):
    """
    Apply filters to a DataFrame with enhanced date field support.

    Args:
        df: pandas DataFrame to filter
        filters: Dictionary of field names and filter values

    Returns:
        Filtered DataFrame
    """
    if not filters:
        return df

    filtered_df = df.copy()

    # Define date field patterns for smart detection
    date_field_patterns = [
        'start_date', 'end_date', 'created_at', 'updated_at',
        'last_updated', 'min_start_date', 'max_end_date'
    ]

    for field, value in filters.items():
        if field not in filtered_df.columns:
            logger.warning(f"Filter field '{field}' not found in data columns")
            continue

        # Detect if this is likely a date field
        is_date_field = any(pattern in field.lower() for pattern in date_field_patterns)

        if isinstance(value, list):
            # List of values (IN operator)
            if is_date_field:
                # Convert both sides to datetime for proper comparison
                try:
                    # Convert filter values to datetime
                    date_values = [pd.to_datetime(v) for v in value]
                    # Convert DataFrame column to datetime
                    df_dates = pd.to_datetime(filtered_df[field], errors='coerce')
                    filtered_df = filtered_df[df_dates.isin(date_values)]
                except Exception as e:
                    logger.warning(f"Failed to apply date list filter for {field}: {e}")
                    # Fallback to string comparison
                    filtered_df = filtered_df[filtered_df[field].isin(value)]
            else:
                filtered_df = filtered_df[filtered_df[field].isin(value)]

        elif isinstance(value, dict):
            # Range filter {'min': x, 'max': y} or regex {'regex': pattern}
            if 'min' in value or 'max' in value:
                if is_date_field:
                    # Handle date range filtering
                    try:
                        # Convert DataFrame column to datetime
                        df_dates = pd.to_datetime(filtered_df[field], errors='coerce')

                        if 'min' in value:
                            min_date = pd.to_datetime(value['min'])
                            filtered_df = filtered_df[df_dates >= min_date]

                        if 'max' in value:
                            max_date = pd.to_datetime(value['max'])
                            filtered_df = filtered_df[df_dates <= max_date]

                    except Exception as e:
                        logger.warning(f"Failed to apply date range filter for {field}: {e}")
                        # Fallback to string comparison (may not work correctly for dates)
                        try:
                            if 'min' in value:
                                filtered_df = filtered_df[filtered_df[field] >= value['min']]
                            if 'max' in value:
                                filtered_df = filtered_df[filtered_df[field] <= value['max']]
                        except Exception as fallback_error:
                            logger.error(f"Date filter failed completely for {field}: {fallback_error}")
                            continue
                else:
                    # Numeric range filtering
                    try:
                        if 'min' in value:
                            filtered_df = filtered_df[filtered_df[field] >= value['min']]
                        if 'max' in value:
                            filtered_df = filtered_df[filtered_df[field] <= value['max']]
                    except Exception as e:
                        logger.warning(f"Failed to apply numeric range filter for {field}: {e}")
                        continue

            if 'regex' in value:
                try:
                    filtered_df = filtered_df[filtered_df[field].astype(str).str.match(value['regex'])]
                except Exception as e:
                    logger.warning(f"Failed to apply regex filter for {field}: {e}")
                    continue

        else:
            # Exact match
            if is_date_field:
                # Handle date exact matching
                try:
                    target_date = pd.to_datetime(value)
                    df_dates = pd.to_datetime(filtered_df[field], errors='coerce')
                    filtered_df = filtered_df[df_dates == target_date]
                except Exception as e:
                    logger.warning(f"Failed to apply date exact filter for {field}: {e}")
                    # Fallback to string comparison
                    filtered_df = filtered_df[filtered_df[field] == value]
            else:
                filtered_df = filtered_df[filtered_df[field] == value]

    return filtered_df


def list_campaigns(self, filters=None, include_stats=True, return_dataframe=False):
    """
    Retrieve a list of unique campaigns with metadata and statistics.

    Args:
        filters (dict, optional): Filters to apply. Keys are field names, values are
                                 filter values or lists of values.
        include_stats (bool): Whether to include summary statistics.
        return_dataframe (bool): If True, return pandas DataFrame instead of list of dicts.

    Returns:
        List of dictionaries or DataFrame, each row representing a unique campaign.
    """
    # Ensure workspace is loaded
    if not self.is_loaded:
        self.load()

    # Load all data
    all_data = self._load_workspace_data(filters)
    if all_data.empty:
        return [] if not return_dataframe else all_data

    # Get unique campaigns - ONLY using campaign_id for deduplication
    campaign_cols = [col for col in all_data.columns if col.startswith('campaign_')]
    campaigns_df = all_data[campaign_cols].drop_duplicates(subset=['campaign_id'])

    # Add statistics if requested
    if include_stats:
        stats_list = []
        for idx, row in campaigns_df.iterrows():
            campaign_id = row['campaign_id']
            campaign_data = all_data[all_data['campaign_id'] == campaign_id]

            # Count line items (exclude placeholder records)
            if 'is_placeholder' in campaign_data.columns:
                actual_lineitems = campaign_data[~campaign_data['is_placeholder']]
                stats = {
                    'stat_media_plan_count': campaign_data['meta_id'].nunique(),
                    'stat_lineitem_count': len(actual_lineitems),  # Exclude placeholders
                    'stat_total_cost': actual_lineitems['lineitem_cost_total'].sum(),
                    'stat_last_updated': campaign_data['meta_created_at'].max(),
                }
            else:
                stats = {
                    'stat_media_plan_count': campaign_data['meta_id'].nunique(),
                    'stat_lineitem_count': len(campaign_data),
                    'stat_total_cost': campaign_data['lineitem_cost_total'].sum(),
                    'stat_last_updated': campaign_data['meta_created_at'].max(),
                }

            # Add date stats if available
            if 'lineitem_start_date' in campaign_data.columns:
                non_null_start_dates = campaign_data['lineitem_start_date'].dropna()
                if not non_null_start_dates.empty:
                    stats['stat_min_start_date'] = non_null_start_dates.min()

            if 'lineitem_end_date' in campaign_data.columns:
                non_null_end_dates = campaign_data['lineitem_end_date'].dropna()
                if not non_null_end_dates.empty:
                    stats['stat_max_end_date'] = non_null_end_dates.max()

            # Calculate dimension counts (only for actual line items)
            lineitem_data = campaign_data
            if 'is_placeholder' in lineitem_data.columns:
                lineitem_data = lineitem_data[~lineitem_data['is_placeholder']]

            for dim in ['channel', 'vehicle', 'partner', 'media_product',
                        'adformat', 'kpi', 'location_name']:
                col = f'lineitem_{dim}'
                if col in lineitem_data.columns:
                    # Count distinct non-empty values
                    non_empty_values = lineitem_data[col].dropna().astype(str)
                    non_empty_values = non_empty_values[non_empty_values != '']
                    stats[f'stat_distinct_{dim}_count'] = len(non_empty_values.unique())

            stats_list.append(stats)

        # Add stats to campaigns DataFrame
        stats_df = pd.DataFrame(stats_list)
        campaigns_df.reset_index(drop=True, inplace=True)
        stats_df.reset_index(drop=True, inplace=True)
        campaigns_df = pd.concat([campaigns_df, stats_df], axis=1)

    # Return as requested format
    if return_dataframe:
        return campaigns_df
    else:
        return campaigns_df.to_dict(orient='records')


def list_mediaplans(self, filters=None, include_stats=True, return_dataframe=False):
    """
    Retrieve a list of media plans with metadata and statistics.

    Args:
        filters (dict, optional): Filters to apply. Keys are field names, values are
                                 filter values or lists of values.
        include_stats (bool): Whether to include summary statistics.
        return_dataframe (bool): If True, return pandas DataFrame instead of list of dicts.

    Returns:
        List of dictionaries or DataFrame, each row representing a unique media plan.
    """
    # Ensure workspace is loaded
    if not self.is_loaded:
        self.load()

    # Load all data
    all_data = self._load_workspace_data(filters)
    if all_data.empty:
        return [] if not return_dataframe else all_data

    # Get unique media plans (combine meta and campaign fields)
    meta_cols = [col for col in all_data.columns if col.startswith('meta_')]
    campaign_cols = [col for col in all_data.columns if col.startswith('campaign_')]
    plan_cols = meta_cols + campaign_cols
    plans_df = all_data[plan_cols].drop_duplicates(subset=['meta_id'])

    # Add statistics if requested
    if include_stats:
        stats_list = []
        for plan_id in plans_df['meta_id']:
            plan_data = all_data[all_data['meta_id'] == plan_id]

            # Filter out placeholder records for statistics
            lineitem_data = plan_data
            if 'is_placeholder' in lineitem_data.columns:
                lineitem_data = lineitem_data[~lineitem_data['is_placeholder']]

            # Count of actual line items (0 if all are placeholders)
            lineitem_count = len(lineitem_data)

            # Calculate basic statistics
            stats = {
                'stat_lineitem_count': lineitem_count,
                'stat_total_cost': lineitem_data['lineitem_cost_total'].sum() if lineitem_count > 0 else 0,
                'stat_avg_cost_per_item': lineitem_data['lineitem_cost_total'].mean() if lineitem_count > 0 else 0,
            }

            # Add date stats if available and there are actual line items
            if lineitem_count > 0:
                if 'lineitem_start_date' in lineitem_data.columns:
                    non_null_start_dates = lineitem_data['lineitem_start_date'].dropna()
                    if not non_null_start_dates.empty:
                        stats['stat_min_start_date'] = non_null_start_dates.min()

                if 'lineitem_end_date' in lineitem_data.columns:
                    non_null_end_dates = lineitem_data['lineitem_end_date'].dropna()
                    if not non_null_end_dates.empty:
                        stats['stat_max_end_date'] = non_null_end_dates.max()

                # Calculate dimension counts
                for dim in ['channel', 'vehicle', 'partner', 'media_product',
                            'adformat', 'kpi', 'location_name']:
                    col = f'lineitem_{dim}'
                    if col in lineitem_data.columns:
                        # Count distinct non-empty values
                        non_empty_values = lineitem_data[col].dropna().astype(str)
                        non_empty_values = non_empty_values[non_empty_values != '']
                        stats[f'stat_distinct_{dim}_count'] = len(non_empty_values.unique())

                # Calculate metric sums
                for metric in ['cost_media', 'cost_platform', 'cost_creative',
                            'metric_impressions', 'metric_clicks', 'metric_views']:
                    col = f'lineitem_{metric}'
                    if col in lineitem_data.columns and not lineitem_data[col].isna().all():
                        stats[f'stat_sum_{metric}'] = lineitem_data[col].sum()
            else:
                # For empty media plans with no line items, set dimension counts to 0
                for dim in ['channel', 'vehicle', 'partner', 'media_product',
                            'adformat', 'kpi', 'location_name']:
                    stats[f'stat_distinct_{dim}_count'] = 0

                # Set metric sums to 0
                for metric in ['cost_media', 'cost_platform', 'cost_creative',
                            'metric_impressions', 'metric_clicks', 'metric_views']:
                    stats[f'stat_sum_{metric}'] = 0

            stats_list.append(stats)

        # Add stats to plans DataFrame
        stats_df = pd.DataFrame(stats_list)
        plans_df.reset_index(drop=True, inplace=True)
        stats_df.reset_index(drop=True, inplace=True)
        plans_df = pd.concat([plans_df, stats_df], axis=1)

    # Return as requested format
    if return_dataframe:
        return plans_df
    else:
        return plans_df.to_dict(orient='records')


def list_lineitems(self, filters=None, limit=None, return_dataframe=False):
    """
    Retrieve a list of line items across all media plans.

    Args:
        filters (dict, optional): Filters to apply. Keys are field names, values are
                                 filter values or lists of values.
        limit (int, optional): Maximum number of line items to return.
        return_dataframe (bool): If True, return pandas DataFrame instead of list of dicts.

    Returns:
        List of dictionaries or DataFrame, each row representing a line item.
    """
    # Ensure workspace is loaded
    if not self.is_loaded:
        self.load()

    # Load all data with filters applied
    all_data = self._load_workspace_data(filters)
    if all_data.empty:
        return [] if not return_dataframe else all_data

    # Filter out placeholder records (these represent media plans with no line items)
    if 'is_placeholder' in all_data.columns:
        all_data = all_data[all_data['is_placeholder'] == False]
        # Drop the is_placeholder column as it's no longer needed
        all_data = all_data.drop(columns=['is_placeholder'])

    # Apply limit if specified
    if limit is not None and limit > 0:
        all_data = all_data.head(limit)

    # Return as requested format
    if return_dataframe:
        return all_data
    else:
        return all_data.to_dict(orient='records')


def sql_query(self,
              query: str,
              engine: str = "auto",
              return_dataframe: bool = True,
              limit: Optional[int] = None) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Execute SQL query against workspace data with intelligent routing.

    Enhanced with intelligent routing:
    - {*} queries with database enabled → PostgreSQL (server-side processing)
    - All other queries → DuckDB + Parquet (existing fast path)

    Use {pattern} syntax to specify which parquet files to query:
    - {*} queries all parquet files in the mediaplans directory
    - {*abc*} queries files containing 'abc' in their name
    - {abc} queries the specific file abc.parquet

    Examples:
        # Query all data (auto-routes to database if enabled)
        workspace.sql_query("SELECT DISTINCT campaign_id FROM {*}")

        # Force database engine
        workspace.sql_query("SELECT * FROM {*}", engine="database")

        # Force DuckDB engine
        workspace.sql_query("SELECT * FROM {*}", engine="duckdb")

        # Pattern queries (always use DuckDB)
        workspace.sql_query("SELECT SUM(cost_total) FROM {campaign_*}")

    Args:
        query: SQL query string with {pattern} placeholders for file patterns.
               Only SELECT operations are allowed.
        engine: Query engine ("auto", "database", "duckdb"). Default "auto".
        return_dataframe: If True, return pandas DataFrame; if False, return list of dicts.
        limit: Optional maximum number of rows to return.

    Returns:
        Query results as DataFrame or list of dictionaries.

    Raises:
        WorkspaceError: If workspace is not loaded.
        SQLQueryError: If query is invalid, unsafe, or execution fails.
    """
    # Ensure workspace is loaded
    if not self.is_loaded:
        raise WorkspaceError("No workspace configuration loaded. Call load() first.")

    # Validate SQL query safety (existing logic)
    _validate_sql_safety(query)

    # Intelligent routing decision
    if self._should_route_to_database(query, engine):
        return self._sql_query_postgres(query, return_dataframe, limit)
    else:
        return self._sql_query_duckdb(query, return_dataframe, limit)


def _should_route_to_database(self, query: str, engine_override: str) -> bool:
    """
    Determine whether to route query to database or DuckDB using EXISTING methods.

    Routing Logic:
    - engine="database" → Always database (with validation using existing PostgreSQLBackend)
    - engine="duckdb" → Always DuckDB
    - engine="auto" → Database if enabled AND {*} pattern detected (lightweight check)

    Args:
        query: SQL query string
        engine_override: Engine preference ("auto", "database", "duckdb")

    Returns:
        True if should route to database, False for DuckDB

    Raises:
        SQLQueryError: If database requested but not available
    """
    if engine_override == "database":
        # Explicit database request - use existing methods for validation
        db_config = self.get_database_config()  # Existing WorkspaceManager method

        if not db_config.get('enabled', False):
            raise SQLQueryError(
                "Database engine requested but database is not enabled in workspace configuration"
            )

        # Use existing PostgreSQLBackend for validation
        try:
            from mediaplanpy.storage.database import PostgreSQLBackend
            backend = PostgreSQLBackend(self.get_resolved_config())  # Existing validation in constructor

            # Use existing test_connection method
            if not backend.test_connection():
                raise SQLQueryError(
                    "Database engine requested but database connection failed"
                )
        except Exception as e:
            if isinstance(e, SQLQueryError):
                raise  # Re-raise our custom errors
            else:
                raise SQLQueryError(f"Database engine requested but unavailable: {e}")

        return True

    elif engine_override == "duckdb":
        # Explicit DuckDB request
        return False

    elif engine_override == "auto":
        # Auto routing: lightweight check for performance
        db_config = self.get_database_config()  # Existing method

        # Quick checks first (no expensive operations for auto mode)
        if not db_config.get('enabled', False):
            return False

        if '{*}' not in query:
            return False

        # For auto mode, assume database is available if enabled
        # The actual connection will be tested in _sql_query_postgres()
        # where we can provide better error handling
        return True

    else:
        raise SQLQueryError(
            f"Invalid engine parameter: {engine_override}. "
            "Must be 'auto', 'database', or 'duckdb'"
        )


def _sql_query_duckdb(self, query: str, return_dataframe: bool = True,
                      limit: Optional[int] = None) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Execute query using DuckDB against Parquet files (existing logic).

    This is the existing sql_query implementation renamed for routing.
    """
    # This is the existing implementation from the original sql_query method
    # (all the DuckDB + S3 logic that was already working)

    try:
        import duckdb
    except ImportError:
        raise SQLQueryError(
            "DuckDB is required for SQL query functionality. "
            "Install it with: pip install duckdb"
        )

    # Resolve file patterns in the query (handles S3 URLs)
    resolved_query = _resolve_sql_file_patterns(self, query)

    # Apply limit if specified
    if limit is not None and limit > 0:
        # Check if query already has LIMIT clause
        if not re.search(r'\bLIMIT\s+\d+', resolved_query, re.IGNORECASE):
            resolved_query = f"SELECT * FROM ({resolved_query}) LIMIT {limit}"

    try:
        # Get storage backend info for logging
        storage_backend = self.get_storage_backend()
        storage_type = type(storage_backend).__name__

        logger.debug(f"Executing SQL query with DuckDB using {storage_type}")
        logger.debug(f"Resolved query: {resolved_query}")

        # Create DuckDB connection
        conn = duckdb.connect()

        # Configure S3 access if using S3 storage
        if storage_type == "S3StorageBackend":
            try:
                # Install and load httpfs extension for S3 support
                conn.execute("INSTALL httpfs;")
                conn.execute("LOAD httpfs;")

                # Configure S3 settings
                conn.execute(f"SET s3_region='{storage_backend.region}';")

                if storage_backend.endpoint_url:
                    conn.execute(f"SET s3_endpoint='{storage_backend.endpoint_url}';")

                conn.execute(f"SET s3_use_ssl={'true' if storage_backend.use_ssl else 'false'};")

                # Configure credentials
                _configure_duckdb_credentials(conn, storage_backend)

                logger.debug("DuckDB configured for S3 access")

            except Exception as e:
                conn.close()
                raise SQLQueryError(f"Failed to configure DuckDB for S3 access: {e}")

        # Execute the query
        result_df = conn.execute(resolved_query).df()
        conn.close()

        logger.debug(f"DuckDB query executed successfully, returned {len(result_df)} rows")

        # Return in requested format
        if return_dataframe:
            return result_df
        else:
            return result_df.to_dict(orient='records')

    except Exception as e:
        # Provide helpful error messages for common S3 issues
        error_msg = str(e).lower()

        if "s3" in error_msg and ("credentials" in error_msg or "access" in error_msg):
            raise SQLQueryError(
                f"S3 access failed - check AWS credentials and bucket permissions. "
                f"DuckDB needs the same AWS credentials as your S3StorageBackend. "
                f"Original error: {str(e)}"
            )
        elif "s3" in error_msg and "region" in error_msg:
            raise SQLQueryError(
                f"S3 region configuration error. Verify bucket region matches workspace config. "
                f"Original error: {str(e)}"
            )
        elif "httpfs" in error_msg or "extension" in error_msg:
            raise SQLQueryError(
                f"DuckDB S3 extension error. Make sure DuckDB can install/load the httpfs extension. "
                f"Original error: {str(e)}"
            )
        else:
            # Wrap other DuckDB errors in our custom exception
            raise SQLQueryError(f"DuckDB query execution failed: {str(e)}")


def _sql_query_postgres(self, query: str, return_dataframe: bool = True,
                        limit: Optional[int] = None) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Execute query against PostgreSQL database with workspace isolation.

    Args:
        query: SQL query with {*} pattern
        return_dataframe: Return format preference
        limit: Optional row limit

    Returns:
        Query results as DataFrame or list of dictionaries

    Raises:
        SQLQueryError: If database execution fails
    """
    try:
        from mediaplanpy.storage.database import PostgreSQLBackend
        import pandas as pd
    except ImportError as e:
        raise SQLQueryError(f"Required dependencies not available: {e}")

    try:
        # Get database configuration and table name
        database_config = self.get_database_config()
        table_name = database_config.get('table_name', 'media_plans')

        # Get current workspace ID for isolation
        workspace_config = self.get_resolved_config()
        workspace_id = workspace_config.get('workspace_id')

        if not workspace_id:
            raise SQLQueryError("No workspace_id found in configuration - required for database queries")

        # Create database backend
        db_backend = PostgreSQLBackend(database_config)

        # Pattern replacement: {*} → table_name
        resolved_query = query.replace('{*}', table_name)

        # Add workspace isolation (CRITICAL for multi-tenant safety)
        resolved_query = self._add_workspace_filter(resolved_query, workspace_id)

        # Apply limit if specified
        if limit and not re.search(r'\bLIMIT\b', resolved_query, re.IGNORECASE):
            resolved_query = f"SELECT * FROM ({resolved_query}) AS limited LIMIT {limit}"

        logger.debug(f"Executing PostgreSQL query: {resolved_query}")

        # Execute query using database backend
        with db_backend.get_connection() as conn:
            if return_dataframe:
                result_df = pd.read_sql(resolved_query, conn)
                logger.debug(f"PostgreSQL query executed successfully, returned {len(result_df)} rows")
                return result_df
            else:
                # Return list of dicts
                cursor = conn.cursor()
                cursor.execute(resolved_query)

                # Get column names
                columns = [desc[0] for desc in cursor.description]

                # Fetch all rows and convert to list of dicts
                rows = cursor.fetchall()
                result = [dict(zip(columns, row)) for row in rows]

                cursor.close()
                logger.debug(f"PostgreSQL query executed successfully, returned {len(result)} rows")
                return result

    except Exception as e:
        # Provide specific error context for database issues
        error_msg = str(e).lower()

        if "connection" in error_msg or "connect" in error_msg:
            raise SQLQueryError(
                f"Database connection failed. Check database configuration and ensure "
                f"PostgreSQL is running. Original error: {str(e)}"
            )
        elif "table" in error_msg and "does not exist" in error_msg:
            raise SQLQueryError(
                f"Database table '{table_name}' does not exist. "
                f"Enable auto_create_table or create table manually. Original error: {str(e)}"
            )
        elif "workspace_id" in error_msg:
            raise SQLQueryError(
                f"Workspace isolation error - invalid workspace_id filter. "
                f"Original error: {str(e)}"
            )
        else:
            # Generic database error
            raise SQLQueryError(f"PostgreSQL query execution failed: {str(e)}")


def _add_workspace_filter(self, query: str, workspace_id: str) -> str:
    """
    Add workspace isolation filter to SQL query for multi-tenant safety.

    This is CRITICAL - every database query must be filtered by workspace_id
    to prevent data leakage between workspaces in multi-tenant deployments.

    Args:
        query: Original SQL query
        workspace_id: Current workspace identifier

    Returns:
        Query with workspace filter added

    Raises:
        SQLQueryError: If workspace filter cannot be added safely
    """
    if not workspace_id:
        raise SQLQueryError("workspace_id is required for database query isolation")

    # Normalize query for parsing
    query_upper = query.upper().strip()

    # Escape single quotes in workspace_id for SQL safety
    safe_workspace_id = workspace_id.replace("'", "''")
    workspace_filter = f"workspace_id = '{safe_workspace_id}'"

    try:
        # Case 1: Query already has WHERE clause
        if ' WHERE ' in query_upper:
            # Find the WHERE clause and add our filter with AND
            where_pattern = re.compile(r'\bWHERE\b', re.IGNORECASE)
            match = where_pattern.search(query)

            if match:
                # Insert our filter right after WHERE
                where_pos = match.end()
                filtered_query = (
                        query[:where_pos] +
                        f" {workspace_filter} AND (" +
                        query[where_pos:] +
                        ")"
                )
                return filtered_query

        # Case 2: Query has no WHERE clause - add one
        # We need to add WHERE before ORDER BY, GROUP BY, HAVING, LIMIT

        # Find the position to insert WHERE clause
        # Look for these clauses in order of precedence
        clause_patterns = [
            (r'\bGROUP\s+BY\b', re.IGNORECASE),
            (r'\bHAVING\b', re.IGNORECASE),
            (r'\bORDER\s+BY\b', re.IGNORECASE),
            (r'\bLIMIT\b', re.IGNORECASE)
        ]

        insert_pos = len(query)  # Default to end of query

        for pattern, flags in clause_patterns:
            match = re.search(pattern, query, flags)
            if match:
                insert_pos = min(insert_pos, match.start())

        # Insert WHERE clause
        filtered_query = (
                query[:insert_pos].rstrip() +
                f" WHERE {workspace_filter} " +
                query[insert_pos:]
        )

        return filtered_query

    except Exception as e:
        raise SQLQueryError(
            f"Failed to add workspace isolation filter to query. "
            f"This is required for multi-tenant safety. Original error: {str(e)}"
        )


# Also update the SQLQueryError definition if not already present
class SQLQueryError(Exception):
    """Exception raised when SQL query execution fails."""
    pass


def _validate_sql_safety(query: str) -> None:
    """
    Validate that the SQL query is safe (SELECT operations only).

    Args:
        query: The SQL query to validate.

    Raises:
        SQLQueryError: If query contains unsafe operations.
    """
    # Convert to uppercase for checking, but preserve original for error messages
    query_upper = query.upper().strip()

    # Remove comments and extra whitespace
    query_clean = re.sub(r'--.*$', '', query_upper, flags=re.MULTILINE)
    query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
    query_clean = ' '.join(query_clean.split())

    # Check if query starts with allowed read-only operations
    allowed_starts = ['SELECT', 'WITH', 'DESCRIBE', 'SHOW', 'EXPLAIN', 'PRAGMA']
    query_starts_with_allowed = any(query_clean.startswith(keyword) for keyword in allowed_starts)

    if not query_starts_with_allowed:
        raise SQLQueryError(
            "Only read-only queries are allowed (SELECT, DESCRIBE, SHOW, EXPLAIN, PRAGMA, WITH). "
            f"Query starts with: {query_clean.split()[0] if query_clean else 'empty'}"
        )

    # List of forbidden SQL keywords/operations
    forbidden_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'UPSERT',
        'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK',
        'PRAGMA', 'ATTACH', 'DETACH'
    ]

    # Check for forbidden operations
    for keyword in forbidden_keywords:
        # Use word boundaries to avoid false positives
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, query_clean):
            raise SQLQueryError(f"Forbidden SQL operation detected: {keyword}")

    # Check for potential file system operations
    filesystem_patterns = [
        r'COPY\s+',
        r'EXPORT\s+',
        r'IMPORT\s+',
        r'LOAD\s+',
        r'INSTALL\s+'
    ]

    for pattern in filesystem_patterns:
        if re.search(pattern, query_clean):
            raise SQLQueryError("File system operations are not allowed in queries")


def _resolve_sql_file_patterns(workspace_manager, query: str) -> str:
    """
    Replace {pattern} placeholders with actual file paths or S3 URLs.

    Enhanced for S3 storage support - generates S3 URLs when using S3 storage backend.

    Args:
        workspace_manager: The WorkspaceManager instance.
        query: SQL query with {pattern} placeholders.

    Returns:
        Query with resolved file paths or S3 URLs.

    Raises:
        SQLQueryError: If pattern resolution fails or no matching files found.
    """
    # Get the storage backend to check for files and determine storage type
    storage_backend = workspace_manager.get_storage_backend()
    storage_backend_type = type(storage_backend).__name__

    # Find all {pattern} occurrences in the query
    pattern_matches = re.findall(r'\{([^}]+)\}', query)

    if not pattern_matches:
        raise SQLQueryError(
            "No file patterns found in query. Use {pattern} syntax to specify files, "
            "e.g., {*} for all files, {abc} for abc.parquet"
        )

    resolved_query = query

    for pattern in pattern_matches:
        try:
            # Get matching files based on pattern
            if pattern == '*':
                # All parquet files
                matching_files = storage_backend.list_files(MEDIAPLANS_SUBDIR, "*.parquet")
            else:
                # Specific pattern - add .parquet extension if not present
                search_pattern = pattern if pattern.endswith('.parquet') else f"{pattern}.parquet"
                matching_files = storage_backend.list_files(MEDIAPLANS_SUBDIR, search_pattern)

            if not matching_files:
                raise SQLQueryError(
                    f"No parquet files found matching pattern '{pattern}' "
                    f"in {MEDIAPLANS_SUBDIR} directory"
                )

            # Convert file paths to appropriate format based on storage backend type
            if storage_backend_type == "S3StorageBackend":
                # For S3: generate S3 URLs that DuckDB can read directly
                file_urls = []
                for file_path in matching_files:
                    # Ensure the file path includes the mediaplans subdirectory
                    if not file_path.startswith(MEDIAPLANS_SUBDIR):
                        full_file_path = f"{MEDIAPLANS_SUBDIR}/{file_path}"
                    else:
                        full_file_path = file_path

                    # Generate S3 URL
                    s3_key = storage_backend.resolve_s3_key(full_file_path)
                    s3_url = f"s3://{storage_backend.bucket}/{s3_key}"
                    file_urls.append(f"'{s3_url}'")

                logger.debug(f"Generated {len(file_urls)} S3 URLs for pattern '{pattern}'")

                # Configure DuckDB for S3 access using the same credentials as storage backend
                resolved_pattern = _prepare_duckdb_s3_access(storage_backend, file_urls)

            else:
                # For local storage: use local file paths (existing logic)
                full_paths = []
                for file_path in matching_files:
                    # Ensure the file path includes the mediaplans subdirectory
                    if not file_path.startswith(MEDIAPLANS_SUBDIR):
                        full_file_path = f"{MEDIAPLANS_SUBDIR}/{file_path}"
                    else:
                        full_file_path = file_path

                    # Get the absolute path from storage backend
                    if hasattr(storage_backend, 'resolve_path'):
                        resolved_path = storage_backend.resolve_path(full_file_path)
                        full_paths.append(f"'{resolved_path}'")
                    else:
                        # Fallback for storage backends without resolve_path
                        full_paths.append(f"'{full_file_path}'")

                # Handle multiple files with UNION ALL or read_parquet array
                if len(full_paths) == 1:
                    resolved_pattern = full_paths[0]
                else:
                    # Create a list for read_parquet function
                    file_list = ', '.join(full_paths)
                    resolved_pattern = f"read_parquet([{file_list}])"

            # Replace the pattern in the query
            resolved_query = resolved_query.replace(f'{{{pattern}}}', resolved_pattern)

            logger.debug(f"Resolved pattern '{pattern}' to {len(matching_files)} file(s) for {storage_backend_type}")

        except Exception as e:
            if isinstance(e, SQLQueryError):
                raise
            else:
                raise SQLQueryError(f"Failed to resolve file pattern '{pattern}': {str(e)}")

    return resolved_query


def _prepare_duckdb_s3_access(s3_storage_backend, file_urls: List[str]) -> str:
    """
    Prepare DuckDB S3 access configuration and return the file pattern for the query.

    This function configures DuckDB to use the same AWS credentials as the S3StorageBackend
    and returns the appropriate file pattern for the SQL query.

    Args:
        s3_storage_backend: The S3StorageBackend instance
        file_urls: List of S3 URLs to access

    Returns:
        String representing the file pattern for DuckDB (single file or read_parquet array)
    """
    try:
        import duckdb
    except ImportError:
        raise SQLQueryError(
            "DuckDB is required for SQL query functionality. "
            "Install it with: pip install duckdb"
        )

    # Configure DuckDB for S3 access using the same credentials as storage backend
    conn = duckdb.connect()

    try:
        # Install and load the httpfs extension for S3 support
        conn.execute("INSTALL httpfs;")
        conn.execute("LOAD httpfs;")

        # Configure S3 settings to match the storage backend
        conn.execute(f"SET s3_region='{s3_storage_backend.region}';")

        if s3_storage_backend.endpoint_url:
            conn.execute(f"SET s3_endpoint='{s3_storage_backend.endpoint_url}';")

        conn.execute(f"SET s3_use_ssl={'true' if s3_storage_backend.use_ssl else 'false'};")

        # Configure AWS credentials - use the same authentication as S3StorageBackend
        _configure_duckdb_credentials(conn, s3_storage_backend)

        logger.debug("DuckDB S3 configuration completed successfully")

    except Exception as e:
        logger.error(f"Failed to configure DuckDB for S3 access: {e}")
        raise SQLQueryError(f"Failed to configure DuckDB for S3: {e}")
    finally:
        conn.close()

    # Return the appropriate file pattern for the query
    if len(file_urls) == 1:
        return file_urls[0]
    else:
        # Multiple files - use read_parquet with array
        file_list = ', '.join(file_urls)
        return f"read_parquet([{file_list}])"


def _configure_duckdb_credentials(duckdb_conn, s3_storage_backend):
    """
    Configure DuckDB S3 credentials to match the S3StorageBackend authentication.

    Args:
        duckdb_conn: DuckDB connection object
        s3_storage_backend: S3StorageBackend instance
    """
    try:
        # Get AWS credentials from the same session/client as S3StorageBackend
        # This ensures DuckDB uses exactly the same authentication

        if s3_storage_backend.profile:
            # If using a specific AWS profile, set it for DuckDB
            duckdb_conn.execute(f"SET s3_aws_profile='{s3_storage_backend.profile}';")
            logger.debug(f"DuckDB configured to use AWS profile: {s3_storage_backend.profile}")

        else:
            # Use credential chain (environment variables, IAM roles, etc.)
            # Try to get credentials from the boto3 session
            try:
                # Get credentials from the S3 client's session
                credentials = s3_storage_backend.s3_client._request_signer._credentials

                if hasattr(credentials, 'access_key') and credentials.access_key:
                    duckdb_conn.execute(f"SET s3_access_key_id='{credentials.access_key}';")
                    logger.debug("DuckDB configured with access key from S3 client")

                if hasattr(credentials, 'secret_key') and credentials.secret_key:
                    duckdb_conn.execute(f"SET s3_secret_access_key='{credentials.secret_key}';")
                    logger.debug("DuckDB configured with secret key from S3 client")

                if hasattr(credentials, 'session_token') and credentials.session_token:
                    duckdb_conn.execute(f"SET s3_session_token='{credentials.session_token}';")
                    logger.debug("DuckDB configured with session token from S3 client")

            except Exception as e:
                logger.warning(f"Could not extract credentials from S3 client: {e}")
                logger.info("DuckDB will use default AWS credential chain")

                # Fallback: let DuckDB use its own credential chain
                # This should work if environment variables or IAM roles are configured
                pass

    except Exception as e:
        logger.warning(f"DuckDB credential configuration failed: {e}")
        logger.info("DuckDB will attempt to use default AWS credential chain")


def _get_mediaplans_path(workspace_manager) -> str:
    """
    Get the full path to the mediaplans subdirectory.

    Args:
        workspace_manager: The WorkspaceManager instance.

    Returns:
        Full path to the mediaplans directory.
    """
    storage_backend = workspace_manager.get_storage_backend()
    if hasattr(storage_backend, 'resolve_path'):
        return storage_backend.resolve_path(MEDIAPLANS_SUBDIR)
    else:
        # Fallback
        return MEDIAPLANS_SUBDIR


# Add the new exception and method to the patch function
def patch_workspace_manager():
    """
    Patch enhanced query methods into WorkspaceManager class.

    This replaces the existing patch_workspace_manager() function to include:
    - Enhanced sql_query with intelligent routing (Steps 1.1 & 1.2)
    - PostgreSQL query execution with workspace isolation
    - All existing methods (preserved unchanged)
    """
    from mediaplanpy.workspace import WorkspaceManager
    from mediaplanpy.exceptions import WorkspaceError

    # Add the SQL query exception to the workspace module
    WorkspaceManager.SQLQueryError = SQLQueryError

    # =========================================================================
    # EXISTING METHODS (preserved unchanged)
    # =========================================================================
    WorkspaceManager._get_parquet_files = _get_parquet_files
    WorkspaceManager._load_workspace_data = _load_workspace_data
    WorkspaceManager._apply_filters = _apply_filters
    WorkspaceManager.list_campaigns = list_campaigns
    WorkspaceManager.list_mediaplans = list_mediaplans
    WorkspaceManager.list_lineitems = list_lineitems

    # =========================================================================
    # ENHANCED SQL QUERY METHODS (Steps 1.1 & 1.2)
    # =========================================================================

    # Core routing method (Step 1.1 - revised to use existing methods)
    WorkspaceManager._should_route_to_database = _should_route_to_database

    # PostgreSQL execution methods (Step 1.2)
    WorkspaceManager._sql_query_postgres = _sql_query_postgres
    WorkspaceManager._add_workspace_filter = _add_workspace_filter

    # Enhanced main sql_query method (Step 1.1)
    WorkspaceManager.sql_query = sql_query

    # Keep existing DuckDB logic as fallback (Step 1.1)
    WorkspaceManager._sql_query_duckdb = _sql_query_duckdb

    # =========================================================================
    # EXISTING HELPER METHODS (preserved unchanged)
    # =========================================================================
    WorkspaceManager._validate_sql_safety = _validate_sql_safety
    WorkspaceManager._resolve_sql_file_patterns = _resolve_sql_file_patterns
    WorkspaceManager._get_mediaplans_path = _get_mediaplans_path
    WorkspaceManager._prepare_duckdb_s3_access = _prepare_duckdb_s3_access
    WorkspaceManager._configure_duckdb_credentials = _configure_duckdb_credentials

# Update the patch call at the bottom of the file
patch_workspace_manager()