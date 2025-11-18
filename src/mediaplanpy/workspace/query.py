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

    Returns one row per campaign_id with current settings and statistics from the
    current/latest media plan.

    Args:
        filters (dict, optional): Filters to apply. Keys are field names, values are
                                 filter values or lists of values.
        include_stats (bool): Whether to include summary statistics.
        return_dataframe (bool): If True, return pandas DataFrame instead of list of dicts.

    Returns:
        List of dictionaries or DataFrame, each row representing a unique campaign.
    """
    import pandas as pd

    # Ensure workspace is loaded
    if not self.is_loaded:
        from mediaplanpy.exceptions import WorkspaceError
        raise WorkspaceError("No workspace configuration loaded. Call load() first.")

    # Step 1: Build simple SQL query to get all campaign data with line item aggregations
    # The workspace_id filter will be automatically injected by sql_query
    # Filter out archived plans at SQL level
    if include_stats:
        query = """
        SELECT
            campaign_id,
            campaign_name,
            campaign_objective,
            campaign_start_date,
            campaign_end_date,
            campaign_budget_total,
            campaign_product_name,
            campaign_product_description,
            campaign_audience_name,
            campaign_audience_age_start,
            campaign_audience_age_end,
            campaign_audience_gender,
            campaign_audience_interests,
            campaign_location_type,
            campaign_locations,
            campaign_budget_currency,
            campaign_agency_id,
            campaign_agency_name,
            campaign_advertiser_id,
            campaign_advertiser_name,
            campaign_product_id,
            campaign_campaign_type_id,
            campaign_campaign_type_name,
            campaign_workflow_status_id,
            campaign_workflow_status_name,
            meta_id,
            meta_is_current,
            meta_created_at,
            -- Line item statistics per media plan
            COUNT(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN 1 END) as stat_lineitem_count,
            SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_total ELSE 0 END) as stat_total_cost,
            MIN(CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_start_date IS NOT NULL THEN lineitem_start_date END) as stat_min_start_date,
            MAX(CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_end_date IS NOT NULL THEN lineitem_end_date END) as stat_max_end_date,
            COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_channel IS NOT NULL AND lineitem_channel != '' THEN lineitem_channel END) as stat_distinct_channel_count,
            COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_vehicle IS NOT NULL AND lineitem_vehicle != '' THEN lineitem_vehicle END) as stat_distinct_vehicle_count,
            COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_partner IS NOT NULL AND lineitem_partner != '' THEN lineitem_partner END) as stat_distinct_partner_count,
            COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_media_product IS NOT NULL AND lineitem_media_product != '' THEN lineitem_media_product END) as stat_distinct_media_product_count,
            COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_adformat IS NOT NULL AND lineitem_adformat != '' THEN lineitem_adformat END) as stat_distinct_adformat_count,
            COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_kpi IS NOT NULL AND lineitem_kpi != '' THEN lineitem_kpi END) as stat_distinct_kpi_count,
            COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_location_name IS NOT NULL AND lineitem_location_name != '' THEN lineitem_location_name END) as stat_distinct_location_name_count
        FROM {*}
        WHERE meta_is_archived = FALSE OR meta_is_archived IS NULL
        GROUP BY campaign_id, campaign_name, campaign_objective,
                 campaign_start_date, campaign_end_date, campaign_budget_total,
                 campaign_product_name, campaign_product_description,
                 campaign_audience_name, campaign_audience_age_start, campaign_audience_age_end,
                 campaign_audience_gender, campaign_audience_interests, campaign_location_type, campaign_locations,
                 campaign_budget_currency, campaign_agency_id, campaign_agency_name,
                 campaign_advertiser_id, campaign_advertiser_name, campaign_product_id,
                 campaign_campaign_type_id, campaign_campaign_type_name,
                 campaign_workflow_status_id, campaign_workflow_status_name,
                 meta_id, meta_is_current, meta_created_at
        ORDER BY campaign_id,
                 CASE WHEN meta_is_current = TRUE THEN 0 ELSE 1 END,
                 meta_created_at DESC
        """
    else:
        query = """
        SELECT DISTINCT
            campaign_id,
            campaign_name,
            campaign_objective,
            campaign_start_date,
            campaign_end_date,
            campaign_budget_total,
            campaign_product_name,
            campaign_product_description,
            campaign_audience_name,
            campaign_audience_age_start,
            campaign_audience_age_end,
            campaign_audience_gender,
            campaign_audience_interests,
            campaign_location_type,
            campaign_locations,
            campaign_budget_currency,
            campaign_agency_id,
            campaign_agency_name,
            campaign_advertiser_id,
            campaign_advertiser_name,
            campaign_product_id,
            campaign_campaign_type_id,
            campaign_campaign_type_name,
            campaign_workflow_status_id,
            campaign_workflow_status_name,
            meta_id,
            meta_is_current,
            meta_created_at
        FROM {*}
        WHERE meta_is_archived = FALSE OR meta_is_archived IS NULL
        ORDER BY campaign_id,
                 CASE WHEN meta_is_current = TRUE THEN 0 ELSE 1 END,
                 meta_created_at DESC
        """

    # Add user filters if provided
    if filters:
        query = self._add_sql_filters(query, filters)

    # Step 2: Execute query - workspace_id filter is automatically injected
    df = self.sql_query(query, return_dataframe=True)

    if df.empty:
        return df if return_dataframe else []

    # Step 3: Count non-archived plans per campaign (before filtering to first row)
    if include_stats:
        plan_counts = df.groupby('campaign_id')['meta_id'].nunique().reset_index()
        plan_counts.columns = ['campaign_id', 'stat_media_plan_count']

    # Step 4: Keep only the first row per campaign_id (current or most recent)
    # The ORDER BY in the SQL already sorted by is_current and created_at DESC
    result_df = df.groupby('campaign_id', as_index=False).first()

    # Step 5: Add plan counts back to the filtered dataframe
    if include_stats:
        result_df = result_df.merge(plan_counts, on='campaign_id', how='left')
        result_df['stat_media_plan_count'] = result_df['stat_media_plan_count'].fillna(0).astype(int)
        # Add stat_last_updated as meta_created_at
        result_df['stat_last_updated'] = result_df['meta_created_at']

    # Step 6: Sort by campaign name
    result_df = result_df.sort_values('campaign_name').reset_index(drop=True)

    # Step 7: Return in requested format (keep meta fields for future use)
    if return_dataframe:
        return result_df
    else:
        return result_df.to_dict(orient='records')


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
        from mediaplanpy.exceptions import WorkspaceError
        raise WorkspaceError("No workspace configuration loaded. Call load() first.")

    # Build SQL query with all meta and campaign fields (using correct database column names)
    query = """
    SELECT 
        meta_id,
        meta_schema_version,
        meta_created_at,
        meta_name,
        meta_comments,
        meta_created_by_id,
        meta_created_by_name,
        meta_is_current,
        meta_is_archived,
        meta_parent_id,
        campaign_id,
        campaign_name,
        campaign_objective,
        campaign_start_date,
        campaign_end_date,
        campaign_budget_total,
        campaign_product_name,
        campaign_budget_currency,
        campaign_agency_id,
        campaign_agency_name,
        campaign_advertiser_id,
        campaign_advertiser_name,
        campaign_product_id,
        campaign_campaign_type_id,
        campaign_campaign_type_name,
        campaign_workflow_status_id,
        campaign_workflow_status_name"""

    if include_stats:
        query += """,
        COUNT(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN 1 END) as stat_lineitem_count,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_total ELSE 0 END) as stat_total_cost,
        AVG(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_total END) as stat_avg_cost_per_item,
        MIN(CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_start_date IS NOT NULL THEN lineitem_start_date END) as stat_min_start_date,
        MAX(CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_end_date IS NOT NULL THEN lineitem_end_date END) as stat_max_end_date,
        COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_channel IS NOT NULL AND lineitem_channel != '' THEN lineitem_channel END) as stat_distinct_channel_count,
        COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_vehicle IS NOT NULL AND lineitem_vehicle != '' THEN lineitem_vehicle END) as stat_distinct_vehicle_count,
        COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_partner IS NOT NULL AND lineitem_partner != '' THEN lineitem_partner END) as stat_distinct_partner_count,
        COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_media_product IS NOT NULL AND lineitem_media_product != '' THEN lineitem_media_product END) as stat_distinct_media_product_count,
        COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_adformat IS NOT NULL AND lineitem_adformat != '' THEN lineitem_adformat END) as stat_distinct_adformat_count,
        COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_kpi IS NOT NULL AND lineitem_kpi != '' THEN lineitem_kpi END) as stat_distinct_kpi_count,
        COUNT(DISTINCT CASE WHEN (is_placeholder = FALSE OR is_placeholder IS NULL) AND lineitem_location_name IS NOT NULL AND lineitem_location_name != '' THEN lineitem_location_name END) as stat_distinct_location_name_count,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_media ELSE 0 END) as stat_sum_cost_media,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_buying ELSE 0 END) as stat_sum_cost_buying,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_platform ELSE 0 END) as stat_sum_cost_platform,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_data ELSE 0 END) as stat_sum_cost_data,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_cost_creative ELSE 0 END) as stat_sum_cost_creative,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_metric_impressions ELSE 0 END) as stat_sum_metric_impressions,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_metric_clicks ELSE 0 END) as stat_sum_metric_clicks,
        SUM(CASE WHEN is_placeholder = FALSE OR is_placeholder IS NULL THEN lineitem_metric_views ELSE 0 END) as stat_sum_metric_views"""

    query += """
    FROM {*}
    GROUP BY meta_id, meta_schema_version, meta_created_at, meta_name, meta_comments,
             meta_created_by_id, meta_created_by_name, meta_is_current, meta_is_archived, meta_parent_id,
             campaign_id, campaign_name, campaign_objective, 
             campaign_start_date, campaign_end_date, campaign_budget_total, campaign_product_name,
             campaign_budget_currency, campaign_agency_id, campaign_agency_name,
             campaign_advertiser_id, campaign_advertiser_name, campaign_product_id,
             campaign_campaign_type_id, campaign_campaign_type_name,
             campaign_workflow_status_id, campaign_workflow_status_name
    ORDER BY meta_created_at DESC"""

    # Add filters if provided
    if filters:
        query = self._add_sql_filters(query, filters)

    # Use routing logic - automatically chooses database vs Parquet!
    return self.sql_query(query, return_dataframe=return_dataframe)


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
        from mediaplanpy.exceptions import WorkspaceError
        raise WorkspaceError("No workspace configuration loaded. Call load() first.")

    # Build SQL query - select all columns, filter out placeholders
    query = """
    SELECT * FROM {*}
    WHERE is_placeholder = FALSE OR is_placeholder IS NULL"""

    # Add filters if provided
    if filters:
        # For line items, we need to add filters as additional WHERE conditions
        filter_conditions = self._build_sql_filter_conditions(filters)
        if filter_conditions:
            query += f" AND ({filter_conditions})"

    query += " ORDER BY lineitem_start_date DESC, lineitem_name"

    # Use routing logic with limit - automatically chooses database vs Parquet!
    return self.sql_query(query, return_dataframe=return_dataframe, limit=limit)


def _add_sql_filters(self, base_query, filters):
    """
    Convert filter dict to SQL WHERE clauses and add to base query.

    Handles the GROUP BY case by inserting WHERE clause before GROUP BY.

    Args:
        base_query: SQL query string
        filters: Dictionary of filter criteria

    Returns:
        Query with WHERE clause added

    Raises:
        SQLQueryError: If filter cannot be converted safely
    """
    if not filters:
        return base_query

    try:
        filter_conditions = self._build_sql_filter_conditions(filters)
        if not filter_conditions:
            return base_query

        # Find the position to insert WHERE clause
        # Look for GROUP BY, ORDER BY, or end of query
        base_query_upper = base_query.upper()

        insert_positions = []
        for clause in ['GROUP BY', 'ORDER BY', 'LIMIT']:
            pos = base_query_upper.find(clause)
            if pos != -1:
                insert_positions.append(pos)

        if insert_positions:
            insert_pos = min(insert_positions)
            # Insert WHERE clause before the first found clause
            filtered_query = (
                    base_query[:insert_pos].rstrip() +
                    f"\nWHERE {filter_conditions}\n" +
                    base_query[insert_pos:]
            )
        else:
            # No special clauses found, add WHERE at the end
            filtered_query = f"{base_query.rstrip()}\nWHERE {filter_conditions}"

        return filtered_query

    except Exception as e:
        from mediaplanpy.exceptions import SQLQueryError
        raise SQLQueryError(f"Failed to add SQL filters: {str(e)}")


def _build_sql_filter_conditions(self, filters):
    """
    Convert filter dictionary to SQL WHERE conditions.

    Handles:
    - List values (IN operator)
    - Range filters {'min': x, 'max': y}
    - Exact matches
    - Date field detection and conversion
    - SQL injection prevention through proper escaping

    Args:
        filters: Dictionary of field names and filter values

    Returns:
        String of SQL WHERE conditions joined with AND

    Raises:
        SQLQueryError: If filter cannot be converted safely
    """
    if not filters:
        return ""

    conditions = []

    # Define date field patterns for smart detection
    date_field_patterns = [
        'start_date', 'end_date', 'created_at', 'updated_at',
        'last_updated', 'min_start_date', 'max_end_date'
    ]

    for field, value in filters.items():
        try:
            # Detect if this is likely a date field
            is_date_field = any(pattern in field.lower() for pattern in date_field_patterns)

            if isinstance(value, list):
                # List of values (IN operator)
                if not value:  # Empty list
                    continue

                if is_date_field:
                    # Date list - convert to proper date format
                    escaped_values = []
                    for v in value:
                        escaped_values.append(f"'{self._escape_sql_value(str(v))}'")
                    conditions.append(f"{field} IN ({', '.join(escaped_values)})")
                else:
                    # Regular list
                    escaped_values = [f"'{self._escape_sql_value(str(v))}'" for v in value]
                    conditions.append(f"{field} IN ({', '.join(escaped_values)})")

            elif isinstance(value, dict):
                # Range filter {'min': x, 'max': y} or regex
                if 'min' in value or 'max' in value:
                    range_conditions = []

                    if 'min' in value:
                        min_val = self._escape_sql_value(str(value['min']))
                        if is_date_field:
                            range_conditions.append(f"{field} >= '{min_val}'")
                        else:
                            # Try numeric first, fall back to string
                            try:
                                float(value['min'])
                                range_conditions.append(f"{field} >= {min_val}")
                            except (ValueError, TypeError):
                                range_conditions.append(f"{field} >= '{min_val}'")

                    if 'max' in value:
                        max_val = self._escape_sql_value(str(value['max']))
                        if is_date_field:
                            range_conditions.append(f"{field} <= '{max_val}'")
                        else:
                            # Try numeric first, fall back to string
                            try:
                                float(value['max'])
                                range_conditions.append(f"{field} <= {max_val}")
                            except (ValueError, TypeError):
                                range_conditions.append(f"{field} <= '{max_val}'")

                    if range_conditions:
                        conditions.append(f"({' AND '.join(range_conditions)})")

                if 'regex' in value:
                    # Regex filter - convert to SQL LIKE or similar
                    # Note: Full regex support varies by database, using LIKE for compatibility
                    regex_pattern = self._escape_sql_value(value['regex'])
                    # Convert basic regex patterns to SQL LIKE
                    if regex_pattern.startswith('^') and regex_pattern.endswith('$'):
                        # Exact match pattern
                        pattern = regex_pattern[1:-1].replace('.*', '%').replace('.', '_')
                        conditions.append(f"{field} LIKE '{pattern}'")
                    else:
                        # Contains pattern
                        pattern = regex_pattern.replace('.*', '%').replace('.', '_')
                        conditions.append(f"{field} LIKE '%{pattern}%'")

            else:
                # Exact match
                escaped_value = self._escape_sql_value(str(value))
                if is_date_field:
                    conditions.append(f"{field} = '{escaped_value}'")
                else:
                    # Try numeric first, fall back to string
                    try:
                        float(value)
                        conditions.append(f"{field} = {escaped_value}")
                    except (ValueError, TypeError):
                        conditions.append(f"{field} = '{escaped_value}'")

        except Exception as e:
            from mediaplanpy.exceptions import SQLQueryError
            raise SQLQueryError(f"Failed to process filter for field '{field}': {str(e)}")

    return ' AND '.join(conditions)


def _escape_sql_value(self, value):
    """
    Escape SQL value to prevent injection attacks.

    Args:
        value: String value to escape

    Returns:
        Escaped string safe for SQL
    """
    if value is None:
        return 'NULL'

    # Convert to string and escape single quotes
    str_value = str(value)
    # Escape single quotes by doubling them
    escaped = str_value.replace("'", "''")
    # Remove other potentially dangerous characters
    # Keep alphanumeric, spaces, hyphens, underscores, periods, colons
    import re
    escaped = re.sub(r"[^\w\s\-\.:@]", "", escaped)

    return escaped


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
    - engine="auto" → Database if enabled (performance optimization for all queries)

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
        # Auto routing: use database whenever enabled for optimal performance
        db_config = self.get_database_config()  # Existing method

        # Route to database if enabled, regardless of query pattern
        if db_config.get('enabled', False):
            return True
        else:
            return False

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

    Enhanced to support both {*} and {plan_id} patterns with automatic
    plan_id filtering for optimal performance.

    Args:
        query: SQL query with {*} or {plan_id} pattern
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
        db_backend = PostgreSQLBackend(workspace_config)

        # Resolve patterns: {*} → table_name, {plan_id} → table_name + WHERE filter
        resolved_query = self._resolve_database_patterns(query, table_name)

        # Add workspace isolation (CRITICAL for multi-tenant safety)
        resolved_query = self._add_workspace_filter(resolved_query, workspace_id)

        # Apply limit if specified
        if limit and not re.search(r'\bLIMIT\b', resolved_query, re.IGNORECASE):
            resolved_query = f"SELECT * FROM ({resolved_query}) AS limited LIMIT {limit}"

        logger.debug(f"Executing PostgreSQL query: {resolved_query}")

        # Execute query using database backend
        with db_backend.connect() as conn:
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


def _resolve_database_patterns(self, query: str, table_name: str) -> str:
    """
    Resolve database query patterns for {*} and {plan_id} cases.

    Handles:
    - {*} → table_name (query all plans)
    - {plan_id} → table_name + WHERE media_plan_id = 'plan_id' (query specific plan)

    Uses only the first pattern found if multiple exist.

    Args:
        query: SQL query with {pattern} placeholder
        table_name: Database table name to substitute

    Returns:
        Query with pattern resolved and plan_id filter added if applicable

    Raises:
        SQLQueryError: If pattern resolution fails
    """
    try:
        # Extract all patterns from the query
        pattern_matches = re.findall(r'\{([^}]+)\}', query)

        if not pattern_matches:
            raise SQLQueryError(
                "No file patterns found in query. Use {*} for all plans or {plan_id} for specific plan."
            )

        # Use only the first pattern (as per requirements)
        pattern = pattern_matches[0].strip()

        if pattern == '*':
            # {*} case: replace with table name, no additional filtering
            resolved_query = query.replace('{*}', table_name)
            logger.debug(f"Resolved {{*}} pattern to table: {table_name}")

        else:
            # {plan_id} case: replace with table name and add plan_id filter
            resolved_query = query.replace(f'{{{pattern}}}', table_name)
            resolved_query = self._add_plan_id_filter(resolved_query, pattern)
            logger.debug(f"Resolved {{{{}}}} pattern to table with plan_id filter: {pattern}")

        return resolved_query

    except Exception as e:
        if isinstance(e, SQLQueryError):
            raise
        else:
            raise SQLQueryError(f"Failed to resolve database pattern: {str(e)}")

def _add_plan_id_filter(self, query: str, plan_id: str) -> str:
    """
    Add plan_id filter to SQL query using the same logic as workspace filter.

    Properly handles existing WHERE clauses by combining filters with AND.
    This follows the same pattern as _add_workspace_filter() for consistency.

    Args:
        query: Original SQL query (may already contain WHERE clause)
        plan_id: Media plan identifier to filter by

    Returns:
        Query with plan_id filter added (combined with existing WHERE if present)

    Raises:
        SQLQueryError: If plan_id filter cannot be added safely
    """
    if not plan_id:
        raise SQLQueryError("plan_id is required for plan-specific database queries")

    # Escape single quotes in plan_id for SQL safety
    safe_plan_id = self._escape_sql_value(plan_id)
    plan_filter = f"meta_id = '{safe_plan_id}'"

    try:
        # Normalize query for parsing - but preserve original formatting
        query_upper = query.upper()

        # Case 1: Query already has WHERE clause
        where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
        if where_match:
            # Find the WHERE keyword position
            where_pos = where_match.start()
            where_end = where_match.end()

            # Find what comes after WHERE to inject our filter properly
            remaining_query = query[where_end:]
            remaining_upper = query_upper[where_end:]

            # Find positions of major clauses that could come after WHERE
            clause_patterns = [
                (r'\bGROUP\s+BY\b', 'GROUP BY'),
                (r'\bHAVING\b', 'HAVING'),
                (r'\bORDER\s+BY\b', 'ORDER BY'),
                (r'\bLIMIT\b', 'LIMIT')
            ]

            # Find the first major clause after WHERE
            next_clause_pos = len(remaining_query)  # Default to end if no clause found

            for pattern, clause_name in clause_patterns:
                match = re.search(pattern, remaining_query, re.IGNORECASE)
                if match:
                    next_clause_pos = min(next_clause_pos, match.start())

            # Extract the existing WHERE conditions
            existing_conditions = remaining_query[:next_clause_pos].strip()
            rest_of_query = remaining_query[next_clause_pos:]

            # Combine plan_id filter with existing conditions using AND
            combined_conditions = f"({plan_filter}) AND ({existing_conditions})"

            # Reconstruct the query
            filtered_query = (
                    query[:where_end] +  # Everything up to and including WHERE
                    f" {combined_conditions}" +  # Combined conditions
                    rest_of_query  # Rest of query (GROUP BY, ORDER BY, etc.)
            )

            return filtered_query

        # Case 2: Query has no WHERE clause - add one
        # Find the position to insert WHERE clause
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
                f" WHERE {plan_filter} " +
                query[insert_pos:]
        )

        return filtered_query

    except Exception as e:
        raise SQLQueryError(
            f"Failed to add plan_id filter to query. "
            f"Original error: {str(e)}"
        )


def _add_workspace_filter(self, query: str, workspace_id: str) -> str:
    """
    Add workspace isolation filter to SQL query for multi-tenant safety.

    ENHANCED to properly handle existing WHERE clauses from user filters.

    This is CRITICAL - every database query must be filtered by workspace_id
    to prevent data leakage between workspaces in multi-tenant deployments.

    Args:
        query: Original SQL query (may already contain WHERE clause from user filters)
        workspace_id: Current workspace identifier

    Returns:
        Query with workspace filter added (combined with existing WHERE if present)

    Raises:
        SQLQueryError: If workspace filter cannot be added safely
    """
    if not workspace_id:
        raise SQLQueryError("workspace_id is required for database query isolation")

    # Escape single quotes in workspace_id for SQL safety
    safe_workspace_id = workspace_id.replace("'", "''")
    workspace_filter = f"workspace_id = '{safe_workspace_id}'"

    try:
        # Normalize query for parsing - but preserve original formatting
        query_upper = query.upper()

        # Case 1: Query already has WHERE clause (from user filters)
        where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
        if where_match:
            # Find the WHERE keyword position
            where_pos = where_match.start()
            where_end = where_match.end()

            # We need to add our workspace filter with AND
            # Find what comes after WHERE to inject our filter properly

            # Look for the next major SQL clause after WHERE
            remaining_query = query[where_end:]
            remaining_upper = query_upper[where_end:]

            # Find positions of major clauses that could come after WHERE
            clause_patterns = [
                (r'\bGROUP\s+BY\b', 'GROUP BY'),
                (r'\bHAVING\b', 'HAVING'),
                (r'\bORDER\s+BY\b', 'ORDER BY'),
                (r'\bLIMIT\b', 'LIMIT')
            ]

            # Find the first major clause after WHERE
            next_clause_pos = len(remaining_query)  # Default to end if no clause found

            for pattern, clause_name in clause_patterns:
                match = re.search(pattern, remaining_query, re.IGNORECASE)
                if match:
                    next_clause_pos = min(next_clause_pos, match.start())

            # Extract the existing WHERE conditions
            existing_conditions = remaining_query[:next_clause_pos].strip()
            rest_of_query = remaining_query[next_clause_pos:]

            # Combine workspace filter with existing conditions using AND
            combined_conditions = f"({workspace_filter}) AND ({existing_conditions})"

            # Reconstruct the query
            filtered_query = (
                    query[:where_end] +  # Everything up to and including WHERE
                    f" {combined_conditions}" +  # Combined conditions
                    rest_of_query  # Rest of query (GROUP BY, ORDER BY, etc.)
            )

            return filtered_query

        # Case 2: Query has no WHERE clause - add one
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
    # EXISTING METHODS
    # =========================================================================
    WorkspaceManager._get_parquet_files = _get_parquet_files
    WorkspaceManager._load_workspace_data = _load_workspace_data
    WorkspaceManager._apply_filters = _apply_filters
    WorkspaceManager.list_campaigns = list_campaigns
    WorkspaceManager.list_mediaplans = list_mediaplans
    WorkspaceManager.list_lineitems = list_lineitems

    # =========================================================================
    # SQL QUERY METHODS
    # =========================================================================
    WorkspaceManager._should_route_to_database = _should_route_to_database
    WorkspaceManager._sql_query_postgres = _sql_query_postgres
    WorkspaceManager._add_workspace_filter = _add_workspace_filter
    WorkspaceManager.sql_query = sql_query
    WorkspaceManager._sql_query_duckdb = _sql_query_duckdb
    WorkspaceManager._resolve_database_patterns = _resolve_database_patterns
    WorkspaceManager._add_plan_id_filter = _add_plan_id_filter

    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    WorkspaceManager._validate_sql_safety = _validate_sql_safety
    WorkspaceManager._resolve_sql_file_patterns = _resolve_sql_file_patterns
    WorkspaceManager._get_mediaplans_path = _get_mediaplans_path
    WorkspaceManager._prepare_duckdb_s3_access = _prepare_duckdb_s3_access
    WorkspaceManager._configure_duckdb_credentials = _configure_duckdb_credentials

    WorkspaceManager._add_sql_filters = _add_sql_filters
    WorkspaceManager._build_sql_filter_conditions = _build_sql_filter_conditions
    WorkspaceManager._escape_sql_value = _escape_sql_value

# Update the patch call at the bottom of the file
patch_workspace_manager()