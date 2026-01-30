# MediaPlanPy SDK - API Reference

This document provides a comprehensive reference for all external methods available in the MediaPlanPy SDK v3.0, organized by entity type. This reference is intended for developers and agents building with the MediaPlanPy SDK.

## Table of Contents

1. [CLI Commands](#cli-commands)
2. [Workspace Management](#workspace-management)
3. [MediaPlan Operations](#mediaplan-operations)
4. [LineItem Operations](#lineitem-operations)
5. [Campaign Operations](#campaign-operations)
6. [Target Audience Model (v3.0)](#target-audience-model-v30)
7. [Target Location Model (v3.0)](#target-location-model-v30)
8. [Metric Formula Model (v3.0)](#metric-formula-model-v30)
9. [Dictionary Model (v3.0)](#dictionary-model-v30)
10. [Storage Functions](#storage-functions)
11. [Schema Management](#schema-management)
12. [Excel Integration](#excel-integration)
13. [Utility Functions](#utility-functions)

---

## CLI Commands

MediaPlanPy v3.0 includes a comprehensive CLI for workspace management and migration workflows.

### Global Commands

**`mediaplanpy --version`**
- Displays SDK version and schema version information

**`mediaplanpy --help`**
- Shows comprehensive help for all commands and subcommands

### Workspace Commands

**`mediaplanpy workspace create`**
- **Description**: Creates a new workspace with v3.0 defaults
- **Key Use Cases**: Initial setup, creating isolated environments
- **Parameters**:
  - `--path`: Path to create workspace.json (default: ./workspace.json)
  - `--name`: Workspace name (default: auto-generated)
  - `--storage`: Storage mode: local or s3 (default: local)
  - `--database`: Enable database: true or false (default: false)
  - `--force`: Overwrite existing workspace.json if present
- **Example**:
```bash
mediaplanpy workspace create \
  --name "Production Workspace" \
  --storage s3 \
  --database true
```

**`mediaplanpy workspace settings --workspace_id <id>`**
- **Description**: Shows workspace configuration and status
- **Key Use Cases**: Configuration inspection, troubleshooting
- **Example**:
```bash
mediaplanpy workspace settings --workspace_id workspace_abc123
```

**`mediaplanpy workspace validate --workspace_id <id>`**
- **Description**: Validates workspace configuration and connectivity
- **Key Use Cases**: Pre-operation validation, troubleshooting
- **Checks**: Schema version, SDK compatibility, storage access, database connection, file integrity
- **Example**:
```bash
mediaplanpy workspace validate --workspace_id workspace_abc123
```

**`mediaplanpy workspace upgrade --workspace_id <id> [--execute]`**
- **Description**: Upgrades workspace from v2.0 to v3.0
- **Key Use Cases**: Schema migration, version upgrades
- **Default Behavior**: Dry-run (preview changes without executing)
- **Parameters**:
  - `--execute`: Execute the upgrade (omit for dry-run)
- **Upgrade Process**:
  1. Creates automatic backups (JSON files, database tables)
  2. Migrates all media plan JSON files (v2.0 → v3.0)
  3. Regenerates Parquet files for analytics
  4. Upgrades database schema (if PostgreSQL enabled)
  5. Updates workspace settings to v3.0
- **Example**:
```bash
# Dry-run (preview changes)
mediaplanpy workspace upgrade --workspace_id workspace_abc123

# Execute upgrade
mediaplanpy workspace upgrade --workspace_id workspace_abc123 --execute
```

**`mediaplanpy workspace statistics --workspace_id <id>`**
- **Description**: Displays workspace statistics and summary
- **Key Use Cases**: Workspace analysis, capacity planning
- **Example**:
```bash
mediaplanpy workspace statistics --workspace_id workspace_abc123
```

**`mediaplanpy workspace version --workspace_id <id>`**
- **Description**: Displays comprehensive schema version information
- **Key Use Cases**: Version compatibility checks, upgrade planning
- **Example**:
```bash
mediaplanpy workspace version --workspace_id workspace_abc123
```

### List Commands

**`mediaplanpy list campaigns --workspace_id <id>`**
- **Description**: Lists all campaigns in workspace
- **Key Use Cases**: Campaign inspection, reporting
- **Parameters**:
  - `--format`: Output format: table or json (default: table)
  - `--limit`: Limit results to n rows (default: 100)
  - `--offset`: Skip first n rows (default: 0)
- **Example**:
```bash
# Table output
mediaplanpy list campaigns --workspace_id workspace_abc123

# JSON output
mediaplanpy list campaigns --workspace_id workspace_abc123 --format json
```

**`mediaplanpy list mediaplans --workspace_id <id>`**
- **Description**: Lists all media plans in workspace
- **Key Use Cases**: Media plan inspection, versioning
- **Parameters**:
  - `--campaign_id`: Filter by campaign ID (optional)
  - `--format`: Output format: table or json (default: table)
  - `--limit`: Limit results to n rows (default: 100)
  - `--offset`: Skip first n rows (default: 0)
- **Example**:
```bash
# List all media plans
mediaplanpy list mediaplans --workspace_id workspace_abc123

# Filter by campaign
mediaplanpy list mediaplans --workspace_id workspace_abc123 --campaign_id camp_001
```

---

## Workspace Management

The `WorkspaceManager` class provides multi-environment configuration and querying capabilities.

### WorkspaceManager Instance Methods

#### Configuration Management

**`create(settings_path_name=None, settings_file_name=None, storage_path_name=None, workspace_name="Default", overwrite=False, **kwargs) -> Tuple[str, str]`**
- **Location**: `src/mediaplanpy/workspace/loader.py:301`
- **Description**: Creates a new workspace configuration file
- **Key Use Cases**: Initial setup, creating isolated environments
- **Parameters**:
  - `workspace_name`: Name for the workspace
  - `overwrite`: Whether to overwrite existing configuration
- **Returns**: Tuple of (workspace_id, settings_file_path)
- **Example**:
```python
from mediaplanpy import WorkspaceManager

workspace = WorkspaceManager()
workspace_id, config_path = workspace.create(
    workspace_name="My_Project",
    storage_path_name="/path/to/data"
)
```

**`load(workspace_path=None, workspace_id=None, config_dict=None) -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/workspace/loader.py:429`
- **Description**: Loads workspace configuration with automatic migration
- **Key Use Cases**: Initializing workspace, loading existing configurations
- **Parameters**:
  - `workspace_path`: Path to workspace file
  - `workspace_id`: ID to locate workspace file
  - `config_dict`: Configuration dictionary to use directly
- **Returns**: Loaded workspace configuration
- **Example**:
```python
# Load by workspace ID
config = workspace.load(workspace_id="workspace_abc123")

# Load from specific path
config = workspace.load(workspace_path="/path/to/workspace.json")
```

**`get_resolved_config() -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/workspace/loader.py:587`
- **Description**: Gets configuration with all variables resolved
- **Key Use Cases**: Getting runtime configuration values
- **Returns**: Configuration with resolved paths and variables

**`upgrade_workspace(target_sdk_version=None, dry_run=False) -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/workspace/loader.py:809`
- **Description**: Upgrades workspace to new SDK/Schema version with v2.0 support
- **Key Use Cases**: Migrating workspaces between SDK versions
- **Parameters**:
  - `target_sdk_version`: Target SDK version
  - `dry_run`: Show changes without executing
- **Returns**: Upgrade results dictionary
- **Example**:
```python
# Check what would be upgraded
result = workspace.upgrade_workspace(dry_run=True)
print(f"Would migrate {result['json_files_migrated']} files")

# Perform actual upgrade
result = workspace.upgrade_workspace()
```

#### Data Querying

**`list_campaigns(filters=None, include_stats=True, return_dataframe=False) -> Union[List[Dict], DataFrame]`**
- **Location**: `src/mediaplanpy/workspace/query.py:211`
- **Description**: Retrieves campaigns with metadata and statistics. Returns one row per campaign_id with current settings and statistics from the current/latest media plan.
- **Key Use Cases**: Campaign reporting, dashboard data
- **Behavior**:
  - Returns one row per `campaign_id` (no duplicates)
  - Campaign settings from current plan (`meta_is_current = TRUE`) or most recent plan
  - Statistics calculated from current/latest media plan only (except `stat_media_plan_count`)
- **Parameters**:
  - `filters`: Dictionary of filter criteria
  - `include_stats`: Include summary statistics
  - `return_dataframe`: Return pandas DataFrame instead of list
- **Example**:
```python
# Get all campaigns with stats (one row per campaign)
campaigns = workspace.list_campaigns(include_stats=True)

# Filter by date range
campaigns = workspace.list_campaigns(
    filters={"stat_min_start_date": {"min": "2023-01-01"}}
)
```

**`list_mediaplans(filters=None, include_stats=True, return_dataframe=False) -> Union[List[Dict], DataFrame]`**
- **Location**: `src/mediaplanpy/workspace/query.py:301`
- **Description**: Retrieves media plans with metadata and statistics
- **Key Use Cases**: Media plan reporting, portfolio analysis
- **Example**:
```python
# Get all media plans
plans = workspace.list_mediaplans()

# Filter by campaign
plans = workspace.list_mediaplans(
    filters={"campaign_id": ["camp_123", "camp_456"]}
)
```

**`list_lineitems(filters=None, limit=None, return_dataframe=False) -> Union[List[Dict], DataFrame]`**
- **Location**: `src/mediaplanpy/workspace/query.py:404`
- **Description**: Retrieves line items across all media plans
- **Key Use Cases**: Line item analysis, performance reporting
- **Parameters**:
  - `filters`: Filter criteria
  - `limit`: Maximum number of items to return
- **Example**:
```python
# Get recent line items
lineitems = workspace.list_lineitems(
    filters={"lineitem_start_date": {"min": "2023-01-01"}},
    limit=100
)
```

**`sql_query(query, return_dataframe=True, limit=None) -> Union[DataFrame, List[Dict]]`**
- **Location**: `src/mediaplanpy/workspace/query.py:443`
- **Description**: Execute SQL queries against workspace Parquet files with S3 support
- **Key Use Cases**: Complex analytics, custom reporting, data exploration
- **Parameters**:
  - `query`: SQL query string with {pattern} placeholders
  - `return_dataframe`: Return format
  - `limit`: Row limit
- **Example**:
```python
# Query all data
result = workspace.sql_query("SELECT DISTINCT campaign_id FROM {*}")

# Query with pattern matching
result = workspace.sql_query(
    "SELECT SUM(cost_total) as total_spend FROM {campaign_*} WHERE channel='Digital'"
)
```

#### Storage and Database

**`get_storage_backend() -> StorageBackend`**
- **Location**: `src/mediaplanpy/workspace/loader.py:780`
- **Description**: Gets storage backend configured for this workspace
- **Key Use Cases**: Direct storage operations
- **Returns**: Storage backend instance (Local, S3, etc.)

**`get_database_config() -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/workspace/loader.py:683`
- **Description**: Gets resolved database configuration
- **Key Use Cases**: Database connectivity, configuration validation

#### Version and Compatibility

**`get_workspace_version_info() -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/workspace/loader.py:1580`
- **Description**: Gets version information about current workspace
- **Key Use Cases**: Version compatibility checks, upgrade planning
- **Returns**: Dictionary with version details and compatibility status

**`check_workspace_compatibility() -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/workspace/loader.py:1648`
- **Description**: Checks compatibility between workspace and SDK versions
- **Key Use Cases**: Pre-operation validation, troubleshooting
- **Returns**: Compatibility analysis results

---

## MediaPlan Operations

The `MediaPlan` class represents a complete media plan with comprehensive lifecycle management.

### MediaPlan Creation

**`@classmethod create(cls, created_by, campaign_name, campaign_objective, campaign_start_date, campaign_end_date, campaign_budget, schema_version=None, workspace_manager=None, **kwargs) -> MediaPlan`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:280`
- **Description**: Creates new media plan with required fields
- **Key Use Cases**: New media plan creation, template generation
- **v3.0 Enhancements**: Supports target_audiences, target_locations, custom_properties
- **Parameters**:
  - `created_by`: Creator name/email
  - `campaign_name`: Campaign name
  - `campaign_objective`: Campaign objective
  - `campaign_start_date`: Start date
  - `campaign_end_date`: End date
  - `campaign_budget`: Total budget
  - `target_audiences`: List of TargetAudience objects (v3.0)
  - `target_locations`: List of TargetLocation objects (v3.0)
- **Example**:
```python
from mediaplanpy import MediaPlan, TargetAudience, TargetLocation
from datetime import date
from decimal import Decimal

media_plan = MediaPlan.create(
    created_by="john.doe@company.com",
    campaign_name="Q4 Brand Campaign",
    campaign_objective="awareness",
    campaign_start_date=date(2024, 10, 1),
    campaign_end_date=date(2024, 12, 31),
    campaign_budget=Decimal("100000"),
    target_audiences=[
        TargetAudience(
            name="Tech Executives",
            demo_age_start=35,
            demo_age_end=55,
            demo_gender="Any"
        )
    ],
    target_locations=[
        TargetLocation(
            name="North America",
            location_type="Country",
            location_list=["United States", "Canada"]
        )
    ]
)
```

**`@classmethod from_dict(cls, data: Dict[str, Any]) -> MediaPlan`**
- **Location**: `src/mediaplanpy/models/base.py`
- **Description**: Creates MediaPlan from dictionary with version handling
- **Key Use Cases**: Data import, API integration
- **Example**:
```python
data = {"meta": {...}, "campaign": {...}, "lineitems": [...]}
media_plan = MediaPlan.from_dict(data)
```

### Storage Operations

**`save(workspace_manager, path=None, format_name=None, overwrite=False, include_parquet=True, include_database=True, validate_version=True, set_as_current=None, **format_options) -> str`**
- **Location**: `src/mediaplanpy/models/mediaplan_storage.py:73`
- **Description**: Saves media plan with comprehensive version validation
- **Key Use Cases**: Persisting changes, creating backups, versioning
- **Parameters**:
  - `workspace_manager`: WorkspaceManager instance
  - `overwrite`: Preserve existing ID vs create new version
  - `include_parquet`: Also save Parquet format
  - `set_as_current`: Set as current plan (None/True/False)
- **Example**:
```python
# Save new version (default behavior)
path = media_plan.save(workspace_manager)

# Update existing version
path = media_plan.save(workspace_manager, overwrite=True)

# Set as current plan
path = media_plan.save(workspace_manager, set_as_current=True)
```

**`@classmethod load(cls, workspace_manager, path=None, media_plan_id=None, campaign_id=None, format_name=None, validate_version=True, auto_migrate=True) -> MediaPlan`**
- **Location**: `src/mediaplanpy/models/mediaplan_storage.py:200`
- **Description**: Loads media plan with version handling
- **Key Use Cases**: Opening existing plans, data recovery
- **Parameters**:
  - `path`: File path or None for ID lookup
  - `media_plan_id`: Media plan ID to load
  - `auto_migrate`: Automatically migrate compatible versions
- **Example**:
```python
# Load by ID
media_plan = MediaPlan.load(workspace_manager, media_plan_id="plan_123")

# Load from specific path
media_plan = MediaPlan.load(workspace_manager, path="mediaplans/plan_123.json")
```

**`delete(workspace_manager, dry_run=False, include_database=True) -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/models/mediaplan_storage.py:350`
- **Description**: Deletes media plan files with version awareness
- **Key Use Cases**: Cleanup, removing obsolete plans
- **Parameters**:
  - `dry_run`: Preview deletion without executing
  - `include_database`: Also delete from database
- **Example**:
```python
# Preview deletion
result = media_plan.delete(workspace_manager, dry_run=True)
print(f"Would delete {result['files_to_delete']}")

# Perform deletion
result = media_plan.delete(workspace_manager)
```

### Line Item Management

**`create_lineitem(line_items, validate=True, **kwargs) -> Union[LineItem, List[LineItem]]`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:450`
- **Description**: Creates one or more line items
- **Key Use Cases**: Adding placements, bulk line item creation
- **v3.0 Enhancements**: Supports metric_formulas, custom_properties
- **Parameters**:
  - `line_items`: Single item or list of LineItem/dict objects
  - `validate`: Validate before creation
  - `**kwargs`: Common properties applied to all items
- **Example**:
```python
# Create single line item
lineitem = media_plan.create_lineitem({
    "name": "Display Campaign",
    "channel": "Digital",
    "cost_total": Decimal("5000")
})

# Create multiple line items
lineitems = media_plan.create_lineitem([
    {"name": "Facebook Ads", "channel": "Social", "cost_total": Decimal("3000")},
    {"name": "Google Ads", "channel": "Search", "cost_total": Decimal("2000")}
])
```

**`load_lineitem(line_item_id: str) -> Optional[LineItem]`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:550`
- **Description**: Loads line item by ID
- **Key Use Cases**: Retrieving specific line items for editing

**`update_lineitem(line_item: LineItem, validate: bool = True) -> LineItem`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:560`
- **Description**: Updates existing line item
- **Key Use Cases**: Modifying line item properties
- **Example**:
```python
lineitem = media_plan.load_lineitem("li_123")
lineitem.cost_total = Decimal("6000")
media_plan.update_lineitem(lineitem)
```

**`delete_lineitem(line_item_id: str, validate: bool = False) -> bool`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:580`
- **Description**: Removes line item by ID
- **Key Use Cases**: Cleaning up unwanted line items

### Formula Management (v3.0)

**`set_standard_metric_formula(metric_name: str, formula_type: str, base_metric: str) -> None`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:1186`
- **Description**: Configure a formula for a standard metric in the dictionary
- **Key Use Cases**: Setting workspace-wide formula defaults
- **NEW in v3.0**: Allows standard metrics to use formulas for calculation
- **Parameters**:
  - `metric_name`: Standard metric name (e.g., 'metric_impressions', 'metric_clicks')
  - `formula_type`: Type of formula ('cost_per_unit', 'conversion_rate', 'constant', 'power_function')
  - `base_metric`: Base metric for calculation (e.g., 'cost_total', 'metric_impressions')
- **Example**:
```python
# Configure impressions to calculate from cost and CPM
media_plan.set_standard_metric_formula(
    "metric_impressions",
    formula_type="cost_per_unit",
    base_metric="cost_total"
)

# Configure clicks to calculate from impressions and CTR
media_plan.set_standard_metric_formula(
    "metric_clicks",
    formula_type="conversion_rate",
    base_metric="metric_impressions"
)
```

**`get_standard_metric_formula(metric_name: str) -> Optional[Dict[str, Any]]`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:1243`
- **Description**: Get formula configuration for a standard metric
- **Returns**: Dictionary with 'formula_type' and 'base_metric' keys, or None
- **Example**:
```python
config = media_plan.get_standard_metric_formula("metric_impressions")
# Returns: {'formula_type': 'cost_per_unit', 'base_metric': 'cost_total'}
```

**`remove_standard_metric_formula(metric_name: str) -> bool`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:1268`
- **Description**: Remove formula configuration for a standard metric
- **Returns**: True if removed, False if not configured

### Status Management

**`set_as_current(workspace_manager: WorkspaceManager, update_self: bool = True) -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:600`
- **Description**: Sets this plan as current, unsetting others in campaign
- **Key Use Cases**: Version management, activating plans
- **Returns**: Results with affected plan counts
- **Example**:
```python
result = media_plan.set_as_current(workspace_manager)
print(f"Unset {result['plans_unset_count']} other current plans")
```

**`archive(workspace_manager: WorkspaceManager) -> None`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:650`
- **Description**: Archives the media plan
- **Key Use Cases**: Deactivating old plans while preserving data

**`restore(workspace_manager: WorkspaceManager) -> None`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:670`
- **Description**: Restores archived media plan
- **Key Use Cases**: Reactivating archived plans

### Export/Import Operations

**`export_to_json(workspace_manager=None, file_path=None, file_name=None, overwrite=False, **format_options) -> str`**
- **Location**: `src/mediaplanpy/models/mediaplan_json.py:23`
- **Description**: Exports media plan to JSON format
- **Key Use Cases**: Data export, backup, API integration
- **Example**:
```python
# Export to workspace storage
json_path = media_plan.export_to_json(workspace_manager, file_name="backup.json")

# Export to local file
json_path = media_plan.export_to_json(file_path="/path/to/export.json")
```

**`@classmethod import_from_json(cls, file_name, workspace_manager=None, file_path=None, **format_options) -> MediaPlan`**
- **Location**: `src/mediaplanpy/models/mediaplan_json.py:150`
- **Description**: Imports media plan from JSON with version handling
- **Key Use Cases**: Data import, migration, recovery
- **Example**:
```python
# Import from workspace
media_plan = MediaPlan.import_from_json("imported_plan.json", workspace_manager)

# Import from local file
media_plan = MediaPlan.import_from_json("plan.json", file_path="/path/to/file")
```

**`export_to_excel(workspace_manager=None, file_path=None, file_name=None, template_path=None, include_documentation=True, overwrite=False, **format_options) -> str`**
- **Location**: `src/mediaplanpy/models/mediaplan_excel.py:25`
- **Description**: Exports media plan to Excel format with formula-aware column generation
- **Key Use Cases**: Client reporting, offline editing, presentation
- **v3.0 Enhancements**: Formula-aware export with coefficient columns based on dictionary configuration
- **Example**:
```python
excel_path = media_plan.export_to_excel(
    workspace_manager,
    template_path="custom_template.xlsx",
    include_documentation=True
)
```

### Validation and Migration

**`validate_against_schema(validator=None, version=None) -> List[str]`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:720`
- **Description**: Validates against JSON schema
- **Key Use Cases**: Data quality validation, compliance checking
- **Returns**: List of error messages (empty if valid)

**`migrate_to_version(migrator=None, to_version=None) -> MediaPlan`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:750`
- **Description**: Migrates to new schema version
- **Key Use Cases**: Schema upgrades, compatibility maintenance
- **Example**:
```python
# Migrate to current version
migrated_plan = media_plan.migrate_to_version()

# Migrate to specific version
migrated_plan = media_plan.migrate_to_version(to_version="3.0")
```

### Custom Fields

**`get_custom_field_config(field_name: str) -> Optional[Dict[str, Any]]`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:800`
- **Description**: Gets custom field configuration
- **Key Use Cases**: Custom field management, UI generation
- **Example**:
```python
config = media_plan.get_custom_field_config("dim_custom1")
if config and config.get("enabled"):
    print(f"Field caption: {config.get('caption')}")
```

**`set_custom_field_config(field_name: str, enabled: bool, caption: str = None)`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:820`
- **Description**: Configures custom field
- **Key Use Cases**: Customizing field labels, enabling/disabling fields
- **Example**:
```python
media_plan.set_custom_field_config("dim_custom1", True, "Market Segment")
```

### Utility Methods

**`calculate_total_cost() -> Decimal`**
- **Location**: `src/mediaplanpy/models/mediaplan.py:690`
- **Description**: Calculates total cost from all line items
- **Key Use Cases**: Budget validation, reporting
- **Returns**: Sum of all line item costs

---

## LineItem Operations

The `LineItem` class represents individual line items within media plans with comprehensive formula support (v3.0).

### LineItem Data Model

**Core Fields**:
- `id`: Unique identifier
- `name`: Line item name
- `start_date`, `end_date`: Date range
- `cost_total`: Total cost

**Channel Fields**:
- `channel`: Primary channel (Digital, TV, Radio, etc.)
- `vehicle`: Platform/publication
- `partner`: Partner/publisher
- `media_product`: Specific product offering

**v3.0 Enhancements**:
- `metric_formulas`: Dictionary of MetricFormula objects for calculated metrics
- `custom_properties`: Extensible object for custom data
- New metrics: `metric_view_starts`, `metric_view_completions`, `metric_reach`, `metric_units`, `metric_impression_share`, `metric_page_views`, `metric_likes`, `metric_shares`, `metric_comments`, `metric_conversions`
- `kpi_value`: Line item level KPI value
- `buy_type`, `buy_commitment`: Buy information fields
- `is_aggregate`, `aggregation_level`: Aggregation support
- `cost_currency_exchange_rate`: Multi-currency support
- `cost_minimum`, `cost_maximum`: Budget constraints

### Formula Methods (v3.0)

**`get_metric_formula_definition(metric_name: str) -> Optional[Dict[str, Any]]`**
- **Location**: `src/mediaplanpy/models/lineitem.py:530`
- **Description**: Get formula definition for this metric on this lineitem
- **NEW in v3.0**: Implements 3-tier hierarchy (lineitem override → dictionary → defaults)
- **Key Use Cases**: Understanding formula configuration, UI generation
- **Parameters**:
  - `metric_name`: Name of the metric (e.g., "metric_clicks")
- **Returns**: Dict with "formula_type" and "base_metric" keys, or None
- **Hierarchy**:
  1. Check this lineitem's metric_formulas for override (highest priority)
  2. Delegate to dictionary for plan-level definition (fallback)
  3. Dictionary returns defaults (ultimate fallback)
- **Example**:
```python
# Get formula definition (checks hierarchy)
formula_def = lineitem.get_metric_formula_definition("metric_clicks")
# Returns: {"formula_type": "conversion_rate", "base_metric": "metric_impressions"}
```

**`configure_metric_formula(metric_name, coefficient=None, parameter1=None, parameter2=None, comments=None, formula_type=None, base_metric=None, recalculate_value=True, recalculate_dependents=True) -> Dict[str, Decimal]`**
- **Location**: `src/mediaplanpy/models/lineitem.py:1247`
- **Description**: Configure formula parameters for a metric, optionally creating a lineitem-level override
- **NEW in v3.0**: Create lineitem-level formula overrides that differ from dictionary defaults
- **Key Use Cases**: Custom formula configuration, lineitem-specific overrides
- **Parameters**:
  - `metric_name`: Name of the metric to configure
  - `coefficient`: New coefficient value (None = no change)
  - `parameter1`: New parameter1 value for power functions (None = no change)
  - `parameter2`: New parameter2 value for power functions (None = no change)
  - `comments`: New comments (None = no change)
  - `formula_type`: Optional formula type to override dictionary (must provide both formula_type and base_metric together)
  - `base_metric`: Optional base metric to override dictionary (must provide both formula_type and base_metric together)
  - `recalculate_value`: If True (default), recalculate this metric's value
  - `recalculate_dependents`: If True (default), recalculate dependent metrics
- **Returns**: Dictionary mapping metric names to their new calculated values
- **Example**:
```python
# Create lineitem-level override with custom formula
lineitem.configure_metric_formula(
    "metric_clicks",
    coefficient=Decimal("0.02"),
    formula_type="conversion_rate",
    base_metric="metric_impressions"
)

# Configure CPM coefficient (uses dictionary formula)
lineitem.configure_metric_formula(
    "metric_impressions",
    coefficient=Decimal("0.010")  # $10 CPM
)

# Configure power function parameters
lineitem.configure_metric_formula(
    "metric_leads",
    coefficient=Decimal("1.5"),
    parameter1=Decimal("0.8"),  # Exponent
    formula_type="power_function",
    base_metric="metric_impressions"
)
```

**`set_metric_value(metric_name: str, value: Decimal, recalculate_dependents=True, update_coefficient=True) -> Dict[str, Decimal]`**
- **Location**: `src/mediaplanpy/models/lineitem.py:1137`
- **Description**: Set a metric value with optional automatic recalculation
- **NEW in v3.0**: Automatically recalculates dependent metrics and updates coefficients
- **Key Use Cases**: Setting metric values, triggering recalculation chains
- **Parameters**:
  - `metric_name`: Name of the metric to set (e.g., "metric_impressions")
  - `value`: The value to set (must be Decimal)
  - `recalculate_dependents`: If True (default), recalculate dependent metrics
  - `update_coefficient`: If True (default), reverse-calculate coefficient
- **Returns**: Dictionary mapping metric names to their new calculated values
- **Example**:
```python
# Set cost_total and recalculate all dependents
lineitem.set_metric_value("cost_total", Decimal("15000"))
# Returns: {"metric_impressions": Decimal("1875000"), "metric_clicks": Decimal("46875")}

# Set impressions and update its coefficient
lineitem.set_metric_value("metric_impressions", Decimal("2000000"))
# Returns: {"metric_conversions": Decimal("2000")}  # If conversions depends on impressions
```

### Inherited Methods from BaseModel

**`to_dict(exclude_none: bool = True) -> Dict[str, Any]`**
- **Description**: Converts line item to dictionary
- **Key Use Cases**: Data export, API integration

**`validate_model() -> List[str]`**
- **Description**: Validates line item data
- **Key Use Cases**: Data quality validation

**`deep_copy() -> LineItem`**
- **Description**: Creates deep copy
- **Key Use Cases**: Duplicating line items with modifications

---

## Campaign Operations

The `Campaign` class represents campaign information within media plans.

### Campaign Data Model (v3.0)

**Core Fields**:
- `id`: Unique identifier
- `name`: Campaign name
- `objective`: Campaign objective (awareness, conversion, etc.)
- `start_date`, `end_date`: Campaign duration
- `budget_total`: Total campaign budget
- `budget_currency`: Currency code

**Organization Fields**:
- `agency_id`, `agency_name`: Agency information
- `advertiser_id`, `advertiser_name`: Advertiser information
- `product_id`, `product_name`, `product_description`: Product information
- `campaign_type_id`, `campaign_type_name`: Campaign classification
- `workflow_status_id`, `workflow_status_name`: Status tracking

**v3.0 Enhancements**:
- `target_audiences`: Array of TargetAudience objects (replaces flat audience fields)
- `target_locations`: Array of TargetLocation objects (replaces flat location fields)
- `kpi_name1-5`, `kpi_value1-5`: Campaign KPI tracking (5 pairs)
- `dim_custom1-5`: Custom dimension fields at campaign level
- `custom_properties`: Extensible object for custom data

### Validation Methods

**`validate_dates() -> Campaign`**
- **Location**: `src/mediaplanpy/models/campaign.py:131`
- **Description**: Validates start_date <= end_date
- **Key Use Cases**: Date consistency validation

### Inherited Methods from BaseModel

Campaigns inherit standard model methods like `to_dict()`, `validate_model()`, etc.

---

## Target Audience Model (v3.0)

The `TargetAudience` class represents a target audience segment for a campaign.

### TargetAudience Data Model

**Required Fields**:
- `name`: Name of the target audience

**Optional Fields**:
- `description`: Detailed description
- `demo_age_start`: Minimum age (inclusive)
- `demo_age_end`: Maximum age (inclusive)
- `demo_gender`: Target gender ("Male", "Female", "Any")
- `demo_attributes`: Additional demographic attributes (e.g., income, education)
- `interest_attributes`: Interest-based attributes and behaviors
- `intent_attributes`: Purchase intent signals
- `purchase_attributes`: Purchase behavior and transaction history
- `content_attributes`: Content consumption and engagement
- `exclusion_list`: Segments or attributes to exclude
- `extension_approach`: Audience extension approach (e.g., lookalike)
- `population_size`: Estimated size of target audience

### Creation Example

```python
from mediaplanpy.models import TargetAudience

audience = TargetAudience(
    name="Tech Executives",
    description="C-level and VP-level technology decision makers",
    demo_age_start=35,
    demo_age_end=55,
    demo_gender="Any",
    demo_attributes="Income: $150K+, Education: Bachelor's or higher",
    interest_attributes="Enterprise software, Cloud computing, AI/ML",
    intent_attributes="Active evaluation of enterprise solutions",
    population_size=500000
)
```

### Validation Methods

**`validate_age_range() -> None`**
- **Description**: Validates demo_age_start <= demo_age_end
- **Raises**: ValidationError if age range is invalid

---

## Target Location Model (v3.0)

The `TargetLocation` class represents a geographic target location for a campaign.

### TargetLocation Data Model

**Required Fields**:
- `name`: Name of the target location

**Optional Fields**:
- `description`: Detailed description
- `location_type`: Type of geographic targeting ("Country", "State", "DMA", "County", "Postcode", "Radius", "POI")
- `location_list`: List of specific locations to target
- `exclusion_type`: Type of geographic exclusion
- `exclusion_list`: List of specific locations to exclude
- `population_percent`: Percentage of target population (0-1 decimal, e.g., 0.452 = 45.2%)

### Creation Example

```python
from mediaplanpy.models import TargetLocation

location = TargetLocation(
    name="Major US Metro Areas",
    description="Top 10 DMAs by population",
    location_type="DMA",
    location_list=["New York", "Los Angeles", "Chicago", "Dallas-Ft. Worth", "Houston"],
    population_percent=0.35
)
```

---

## Metric Formula Model (v3.0)

The `MetricFormula` class represents a custom calculation formula for a metric.

### MetricFormula Data Model

**Required Fields**:
- `formula_type`: Type of formula function ("cost_per_unit", "conversion_rate", "constant", "power_function")

**Optional Fields**:
- `base_metric`: The metric or cost field used as input (e.g., "cost_total", "metric_impressions")
- `coefficient`: Coefficient value for the formula
- `parameter1`: First parameter for the formula function
- `parameter2`: Second parameter for the formula function
- `parameter3`: Third parameter for the formula function
- `comments`: Additional notes about the formula configuration

### Creation Example

```python
from mediaplanpy.models import MetricFormula
from decimal import Decimal

# Cost per unit formula (e.g., CPM for impressions)
formula = MetricFormula(
    formula_type="cost_per_unit",
    base_metric="cost_total",
    coefficient=Decimal("0.008"),  # $8 CPM
    comments="Standard CPM rate for programmatic display"
)

# Conversion rate formula (e.g., CTR for clicks)
ctr_formula = MetricFormula(
    formula_type="conversion_rate",
    base_metric="metric_impressions",
    coefficient=Decimal("0.025"),  # 2.5% CTR
    comments="Expected CTR based on historical performance"
)

# Power function formula (e.g., diminishing returns)
power_formula = MetricFormula(
    formula_type="power_function",
    base_metric="metric_impressions",
    coefficient=Decimal("1.5"),
    parameter1=Decimal("0.8"),  # Exponent
    comments="Diminishing returns model for brand lift"
)

# Constant formula (e.g., fixed value)
constant_formula = MetricFormula(
    formula_type="constant",
    coefficient=Decimal("1000"),
    comments="Fixed reach estimate"
)
```

### Usage in LineItems

```python
# Set metric_formulas dictionary on lineitem
lineitem.metric_formulas = {
    "metric_impressions": MetricFormula(
        formula_type="cost_per_unit",
        base_metric="cost_total",
        coefficient=Decimal("0.008")
    ),
    "metric_clicks": MetricFormula(
        formula_type="conversion_rate",
        base_metric="metric_impressions",
        coefficient=Decimal("0.025")
    )
}
```

---

## Dictionary Model (v3.0)

The `Dictionary` class configures custom fields and formula defaults for the media plan.

### Dictionary Structure (v3.0)

**v3.0 Enhancements**:
- `meta_custom_dimensions`: Configure dim_custom1-5 for meta level (NEW)
- `campaign_custom_dimensions`: Configure dim_custom1-5 for campaign level (NEW)
- `lineitem_custom_dimensions`: Configure dim_custom1-10 for lineitem level (renamed from `custom_dimensions`)
- `standard_metrics`: Configure formula support for standard metrics (NEW)
- `custom_metrics`: Configure custom metrics with formula support (enhanced)
- `custom_costs`: Configure custom cost fields

### Key Methods

**`get_metric_formula_definition(metric_name: str) -> Optional[Dict[str, Any]]`**
- **Location**: `src/mediaplanpy/models/dictionary.py:526`
- **Description**: Get formula definition for a specific metric from dictionary
- **Returns**: Dict with "formula_type" and "base_metric" keys, or defaults
- **Default Behavior**: Returns {"formula_type": "cost_per_unit", "base_metric": "cost_total"} for standard metrics if not configured

---

## Storage Functions

Standalone functions for storage operations across different backends.

**`read_mediaplan(workspace_config, path, format_name=None) -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/storage/__init__.py:50`
- **Description**: Reads media plan from any storage backend
- **Key Use Cases**: Direct file reading, batch processing
- **Example**:
```python
from mediaplanpy.storage import read_mediaplan

data = read_mediaplan(workspace_config, "mediaplans/plan.json")
```

**`write_mediaplan(workspace_config, data, path, format_name=None, **format_options) -> None`**
- **Location**: `src/mediaplanpy/storage/__init__.py:80`
- **Description**: Writes media plan to storage
- **Key Use Cases**: Batch saves, custom storage workflows
- **Example**:
```python
from mediaplanpy.storage import write_mediaplan

write_mediaplan(workspace_config, media_plan_data, "backup/plan.json")
```

**`get_storage_backend(workspace_config) -> StorageBackend`**
- **Location**: `src/mediaplanpy/storage/__init__.py:25`
- **Description**: Creates storage backend instance
- **Key Use Cases**: Direct storage operations, custom workflows
- **Returns**: LocalStorageBackend, S3StorageBackend, etc.

**`get_format_handler_instance(format_name_or_path, **options) -> FormatHandler`**
- **Location**: `src/mediaplanpy/storage/formats/__init__.py:40`
- **Description**: Creates format handler instance
- **Key Use Cases**: Custom format handling, file processing

---

## Schema Management

Functions for schema validation and migration.

### Version Information

**`get_current_version() -> str`**
- **Location**: `src/mediaplanpy/schema/__init__.py:50`
- **Description**: Gets current schema version
- **Key Use Cases**: Version checking, compatibility validation
- **Returns**: Current version ("3.0")

**`get_supported_versions() -> List[str]`**
- **Location**: `src/mediaplanpy/schema/__init__.py:60`
- **Description**: Gets supported schema versions
- **Key Use Cases**: Version compatibility checking
- **Returns**: List of supported versions (["2.0", "3.0"])

### Validation Functions

**`validate(media_plan, version=None) -> List[str]`**
- **Location**: `src/mediaplanpy/schema/__init__.py:70`
- **Description**: Validates media plan against schema
- **Key Use Cases**: Data validation, compliance checking
- **Example**:
```python
from mediaplanpy.schema import validate

errors = validate(media_plan_data, "3.0")
if not errors:
    print("Media plan is valid!")
```

**`validate_file(file_path, version=None) -> List[str]`**
- **Location**: `src/mediaplanpy/schema/__init__.py:90`
- **Description**: Validates JSON file against schema
- **Key Use Cases**: File validation, batch processing

### Migration Functions

**`migrate(media_plan, from_version, to_version) -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/schema/__init__.py:110`
- **Description**: Migrates between schema versions
- **Key Use Cases**: Schema upgrades, data migration
- **Example**:
```python
from mediaplanpy.schema import migrate

migrated_data = migrate(old_plan, "2.0", "3.0")
```

### Version Utility Functions

**`normalize_version(version) -> str`**
- **Description**: Normalizes version format (v3.0.0 → 3.0)
- **Key Use Cases**: Version comparison, normalization

**`get_compatibility_type(version) -> str`**
- **Description**: Gets compatibility type for version
- **Returns**: "current", "backwards_compatible", "deprecated", "unsupported"

---

## Excel Integration

Functions for Excel format support with formula-aware import/export (v3.0).

**`export_to_excel(media_plan, path=None, template_path=None, include_documentation=True, workspace_manager=None, **kwargs) -> str`**
- **Location**: `src/mediaplanpy/excel/exporter.py:30`
- **Description**: Exports media plan to Excel with formula-aware column generation
- **Key Use Cases**: Client deliverables, offline editing
- **v3.0 Enhancements**:
  - Smart column generation based on dictionary formula configurations
  - Creates coefficient columns (CPU, CVR, Constant) based on formula_type
  - Separate Target Audiences and Target Locations worksheets
- **Example**:
```python
from mediaplanpy.excel import export_to_excel

excel_path = export_to_excel(
    media_plan_data,
    path="client_report.xlsx",
    include_documentation=True
)
```

**`import_from_excel(file_path, **kwargs) -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/excel/importer.py:40`
- **Description**: Imports from Excel with formula-aware coefficient updates
- **Key Use Cases**: Client data import, offline editing workflow
- **v3.0 Enhancements**:
  - Automatically updates metric_formulas coefficients from edited values
  - Processes dependencies in topological order
  - Preserves lineitem-level formula overrides through JSON column

**`validate_excel(file_path, schema_validator=None, schema_version=None) -> List[str]`**
- **Location**: `src/mediaplanpy/excel/validator.py:30`
- **Description**: Validates Excel file against schema
- **Key Use Cases**: Pre-import validation, quality control
- **Example**:
```python
from mediaplanpy.excel import validate_excel

errors = validate_excel("client_data.xlsx")
if not errors:
    # Safe to import
    data = import_from_excel("client_data.xlsx")
```

---

## Utility Functions

Additional utility functions available in the SDK.

**`is_database_available() -> bool`**
- **Location**: `src/mediaplanpy/__init__.py:172`
- **Description**: Checks if database functionality is available
- **Key Use Cases**: Feature availability checking

**`get_version_info() -> Dict[str, Any]`**
- **Location**: `src/mediaplanpy/__init__.py:181`
- **Description**: Gets detailed SDK version information
- **Key Use Cases**: Troubleshooting, compatibility checking
- **Returns**: SDK version, schema version, release notes

---

## Error Handling

The SDK uses custom exception hierarchy:

- `MediaPlanError`: Base exception
- `StorageError`: Storage operation failures
- `ValidationError`: Data validation failures
- `SchemaVersionError`: Version compatibility issues
- `WorkspaceError`: Workspace configuration problems

---

## Best Practices

1. **Always use WorkspaceManager** for production workflows
2. **Enable validation** by default (`validate_version=True`)
3. **Check compatibility** before operations on mixed-version data
4. **Use dry_run** for destructive operations when possible
5. **Handle version migration** gracefully with proper error handling
6. **Use formula hierarchy** (lineitem override → dictionary → defaults) for flexible metric calculations
7. **Leverage CLI commands** for administrative tasks and migrations
8. **Use target_audiences and target_locations arrays** for v3.0 targeting (not flat fields)
9. **Configure formulas at dictionary level** for workspace-wide defaults, override at lineitem level for specific cases
10. **Use set_metric_value() and configure_metric_formula()** for automatic recalculation of dependent metrics

---

## Related Documentation

- **[CHANGE_LOG.md](CHANGE_LOG.md)** - Complete version history and v3.0 additions
- **[docs/MIGRATION_V2_TO_V3.md](docs/MIGRATION_V2_TO_V3.md)** - Migration guide for v2.0 to v3.0 upgrade
- **[GET_STARTED.md](GET_STARTED.md)** - Quick start guide and basic workflows
- **[docs/database_configuration.md](docs/database_configuration.md)** - PostgreSQL integration setup
- **[docs/cloud_storage_configuration.md](docs/cloud_storage_configuration.md)** - Amazon S3 storage configuration
- **[examples/](examples/)** - Comprehensive examples library demonstrating v3.0 features

---

*This API reference covers MediaPlanPy SDK v3.0.0. For the latest updates, see the project's CHANGE_LOG.md and the migration guide at docs/MIGRATION_V2_TO_V3.md.*
