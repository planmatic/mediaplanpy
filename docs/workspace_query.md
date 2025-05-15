# Media Plan Workspace Query Functionality

The Media Plan Python SDK now includes powerful querying capabilities for analyzing media plans across your workspace. These features make it easy to list and filter campaigns, media plans, and line items, with options to include summary statistics and receive the data in a format that best suits your needs.

## New Methods

Three new methods have been added to the `WorkspaceManager` class:

### 1. `list_campaigns(filters=None, include_stats=True, return_dataframe=False)`

Retrieve a list of unique campaigns with metadata and optional statistics.

- **Parameters:**
  - `filters` (dict, optional): Filters to apply to the data
  - `include_stats` (bool): Whether to include summary statistics
  - `return_dataframe` (bool): If True, returns a pandas DataFrame instead of a list of dictionaries

- **Returns:**
  A list of dictionaries or a pandas DataFrame, each representing a unique campaign.

- **Statistics included:**
  - `stat_media_plan_count`: Number of media plans associated with the campaign
  - `stat_lineitem_count`: Total number of line items in the campaign
  - `stat_total_cost`: Sum of all line item costs in the campaign
  - `stat_min_start_date`: Earliest start date among line items
  - `stat_max_end_date`: Latest end date among line items
  - `stat_last_updated`: Most recent update timestamp
  - `stat_distinct_*_count`: Count of distinct values for various dimensions

### 2. `list_mediaplans(filters=None, include_stats=True, return_dataframe=False)`

Retrieve a list of media plans with metadata and optional statistics.

- **Parameters:**
  - `filters` (dict, optional): Filters to apply to the data
  - `include_stats` (bool): Whether to include summary statistics
  - `return_dataframe` (bool): If True, returns a pandas DataFrame instead of a list of dictionaries

- **Returns:**
  A list of dictionaries or a pandas DataFrame, each representing a unique media plan.

- **Statistics included:**
  - `stat_lineitem_count`: Number of line items in the media plan
  - `stat_total_cost`: Sum of all line item costs in the plan
  - `stat_avg_cost_per_item`: Average cost per line item
  - `stat_min_start_date`: Earliest start date among line items
  - `stat_max_end_date`: Latest end date among line items
  - `stat_distinct_*_count`: Count of distinct values for various dimensions
  - `stat_sum_*`: Sum of various metrics across all line items

### 3. `list_lineitems(filters=None, limit=None, return_dataframe=False)`

Retrieve a list of line items across all media plans.

- **Parameters:**
  - `filters` (dict, optional): Filters to apply to the data
  - `limit` (int, optional): Maximum number of line items to return
  - `return_dataframe` (bool): If True, returns a pandas DataFrame instead of a list of dictionaries

- **Returns:**
  A list of dictionaries or a pandas DataFrame, each representing a line item.

## Filtering Options

The `filters` parameter accepts a dictionary where keys are field names and values are filter criteria. Several types of filters are supported:

1. **Exact match:**
   ```python
   {'campaign_id': 'cmp-001'}  # Match exact value
   ```

2. **List of values (IN):**
   ```python
   {'lineitem_channel': ['social', 'video']}  # Match any value in the list
   ```

3. **Range filter:**
   ```python
   {'campaign_budget_total': {'min': 50000, 'max': 100000}}  # Between min and max
   {'meta_created_at': {'min': datetime(2025, 5, 1)}}  # Greater than or equal to min
   ```

4. **Regex match:**
   ```python
   {'lineitem_name': {'regex': '.*Instagram.*'}}  # Match regex pattern
   ```

## Usage Examples

### List campaigns with budget over $50,000

```python
high_budget_campaigns = workspace.list_campaigns(filters={
    'campaign_budget_total': {'min': 50000}
})
```

### List media plans created in May 2025

```python
import datetime
start_date = datetime.datetime(2025, 5, 1)
end_date = datetime.datetime(2025, 5, 31)
may_plans = workspace.list_mediaplans(filters={
    'meta_created_at': {'min': start_date, 'max': end_date}
})
```

### Get line items for a specific campaign as a DataFrame

```python
items_df = workspace.list_lineitems(
    filters={'campaign_id': 'cmp-001'},
    return_dataframe=True
)

# Analyze with pandas
avg_cost_by_channel = items_df.groupby('lineitem_channel')['lineitem_cost_total'].mean()
```

### Find specific partners with regex matching

```python
google_items = workspace.list_lineitems(filters={
    'lineitem_partner': {'regex': '(?i)google.*'}  # Case-insensitive match
})
```

## Technical Details

These methods work by reading Parquet files that are generated when media plans are saved with `include_parquet=True`. The Parquet files store a flattened, denormalized version of the media plan data, which is optimized for analytical queries.

If no Parquet files are found in the workspace, the methods will return empty results. To ensure Parquet files are generated, make sure to set `include_parquet=True` when saving media plans:

```python
media_plan.save(workspace_manager, path="my_plan.json", include_parquet=True)
```

## Performance Considerations

- For large workspaces, consider using filters to reduce the amount of data processed
- When working with large datasets, use `return_dataframe=True` to get a pandas DataFrame for more efficient analysis
- If you only need specific columns, you can select them from the returned data to reduce memory usage
