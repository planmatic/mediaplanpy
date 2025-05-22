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
    Apply filters to a DataFrame.

    Args:
        df: pandas DataFrame to filter
        filters: Dictionary of field names and filter values

    Returns:
        Filtered DataFrame
    """
    if not filters:
        return df

    filtered_df = df.copy()
    for field, value in filters.items():
        if field not in filtered_df.columns:
            logger.warning(f"Filter field '{field}' not found in data columns")
            continue

        if isinstance(value, list):
            # List of values (IN operator)
            filtered_df = filtered_df[filtered_df[field].isin(value)]
        elif isinstance(value, dict):
            # Range filter {'min': x, 'max': y} or regex {'regex': pattern}
            if 'min' in value:
                filtered_df = filtered_df[filtered_df[field] >= value['min']]
            if 'max' in value:
                filtered_df = filtered_df[filtered_df[field] <= value['max']]
            if 'regex' in value:
                filtered_df = filtered_df[filtered_df[field].astype(str).str.match(value['regex'])]
        else:
            # Exact match
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
              return_dataframe: bool = True,
              limit: Optional[int] = None) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Execute SQL query against workspace parquet files.

    Use {pattern} syntax to specify which parquet files to query:
    - {*} queries all parquet files in the mediaplans directory
    - {*abc*} queries files containing 'abc' in their name
    - {abc} queries the specific file abc.parquet

    Examples:
        # Query all files
        workspace.sql_query("SELECT DISTINCT campaign_id FROM {*}")

        # Query files matching pattern
        workspace.sql_query("SELECT * FROM {campaign_*} WHERE cost_total > 1000")

        # Query specific file
        workspace.sql_query("SELECT COUNT(*) FROM {my_mediaplan}")

    Args:
        query: SQL query string with {pattern} placeholders for file patterns.
               Only SELECT operations are allowed.
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

    try:
        import duckdb
    except ImportError:
        raise SQLQueryError(
            "DuckDB is required for SQL query functionality. "
            "Install it with: pip install duckdb"
        )

    # Validate SQL query safety
    _validate_sql_safety(query)

    # Resolve file patterns in the query
    resolved_query = _resolve_sql_file_patterns(self, query)

    # Apply limit if specified
    if limit is not None and limit > 0:
        # Check if query already has LIMIT clause
        if not re.search(r'\bLIMIT\s+\d+', resolved_query, re.IGNORECASE):
            resolved_query = f"SELECT * FROM ({resolved_query}) LIMIT {limit}"

    try:
        # Execute the query using DuckDB
        logger.debug(f"Executing SQL query: {resolved_query}")
        result_df = duckdb.query(resolved_query).df()

        # Return in requested format
        if return_dataframe:
            return result_df
        else:
            return result_df.to_dict(orient='records')

    except Exception as e:
        # Wrap DuckDB errors in our custom exception
        raise SQLQueryError(f"SQL query execution failed: {str(e)}")


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
    Replace {pattern} placeholders with actual parquet file paths.

    Args:
        workspace_manager: The WorkspaceManager instance.
        query: SQL query with {pattern} placeholders.

    Returns:
        Query with resolved file paths.

    Raises:
        SQLQueryError: If pattern resolution fails or no matching files found.
    """
    # Get the storage backend to check for files
    storage_backend = workspace_manager.get_storage_backend()

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

            # Convert file paths to full paths for DuckDB
            # Resolve full paths for each matching file
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

            # Join multiple files with UNION ALL if more than one file
            if len(full_paths) == 1:
                resolved_pattern = full_paths[0]
            else:
                # Create a UNION ALL query for multiple files
                # This requires wrapping the original query
                file_list = ', '.join(full_paths)
                resolved_pattern = f"read_parquet([{file_list}])"

            # Replace the pattern in the query
            resolved_query = resolved_query.replace(f'{{{pattern}}}', resolved_pattern)

            logger.debug(f"Resolved pattern '{pattern}' to {len(matching_files)} file(s)")

        except Exception as e:
            if isinstance(e, SQLQueryError):
                raise
            else:
                raise SQLQueryError(f"Failed to resolve file pattern '{pattern}': {str(e)}")

    return resolved_query


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
    """Patch query methods into WorkspaceManager class."""
    from mediaplanpy.workspace import WorkspaceManager
    from mediaplanpy.exceptions import WorkspaceError

    # Add the SQL query exception to the workspace module
    WorkspaceManager.SQLQueryError = SQLQueryError

    # Add existing methods
    WorkspaceManager._get_parquet_files = _get_parquet_files
    WorkspaceManager._load_workspace_data = _load_workspace_data
    WorkspaceManager._apply_filters = _apply_filters
    WorkspaceManager.list_campaigns = list_campaigns
    WorkspaceManager.list_mediaplans = list_mediaplans
    WorkspaceManager.list_lineitems = list_lineitems

    # Add new SQL query method
    WorkspaceManager.sql_query = sql_query
    WorkspaceManager._validate_sql_safety = _validate_sql_safety
    WorkspaceManager._resolve_sql_file_patterns = _resolve_sql_file_patterns
    WorkspaceManager._get_mediaplans_path = _get_mediaplans_path


# Update the patch call at the bottom of the file
patch_workspace_manager()