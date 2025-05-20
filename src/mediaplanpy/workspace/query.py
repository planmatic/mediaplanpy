"""
Updated workspace query module to support mediaplans subdirectory and handle placeholder records.

This module updates the query methods to look for Parquet files
in the mediaplans subdirectory of the workspace storage and properly handle
placeholder records for empty media plans.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Union

import pandas as pd
import io

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

    Examples:
        # List all campaigns
        campaigns = workspace.list_campaigns()

        # List campaigns with budget over $50,000
        campaigns = workspace.list_campaigns(filters={
            'campaign_budget_total': {'min': 50000}
        })

        # Get campaigns as DataFrame for analysis
        campaigns_df = workspace.list_campaigns(return_dataframe=True)
    """
    # Ensure workspace is loaded
    if not self.is_loaded:
        self.load()

    # Load all data
    all_data = self._load_workspace_data(filters)
    if all_data.empty:
        return [] if not return_dataframe else all_data

    # Get unique campaigns
    campaign_cols = [col for col in all_data.columns if col.startswith('campaign_')]
    # Use meta_id to deduplicate records (one record per media plan)
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

    # Drop meta_id column if it was added
    if 'meta_id' in campaigns_df.columns:
        campaigns_df = campaigns_df.drop(columns=['meta_id'])

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

    Examples:
        # List all media plans
        plans = workspace.list_mediaplans()

        # List media plans created in May 2025
        import datetime
        start_date = datetime.datetime(2025, 5, 1)
        end_date = datetime.datetime(2025, 5, 31)
        plans = workspace.list_mediaplans(filters={
            'meta_created_at': {'min': start_date, 'max': end_date}
        })
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

    Examples:
        # Get line items for a specific campaign
        items = workspace.list_lineitems(filters={'campaign_id': 'cmp-001'})

        # Get line items in social media channels with regex match on name
        items = workspace.list_lineitems(filters={
            'lineitem_channel': 'social',
            'lineitem_name': {'regex': '.*Instagram.*'}
        })

        # Get first 100 line items as DataFrame
        items_df = workspace.list_lineitems(limit=100, return_dataframe=True)
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


def patch_workspace_manager():
    """Patch query methods into WorkspaceManager class."""
    from mediaplanpy.workspace import WorkspaceManager

    # Add each method to the WorkspaceManager class
    WorkspaceManager._get_parquet_files = _get_parquet_files
    WorkspaceManager._load_workspace_data = _load_workspace_data
    WorkspaceManager._apply_filters = _apply_filters
    WorkspaceManager.list_campaigns = list_campaigns
    WorkspaceManager.list_mediaplans = list_mediaplans
    WorkspaceManager.list_lineitems = list_lineitems


# Apply the patches when this module is imported
patch_workspace_manager()