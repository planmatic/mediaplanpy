# MediaPlanPy SDK - API Reference

This document provides a comprehensive reference for all external methods available in the MediaPlanPy SDK, organized by entity type. This reference is intended for developers and agents building with the MediaPlanPy SDK.

## Table of Contents

1. [Workspace Management](#workspace-management)
2. [MediaPlan Operations](#mediaplan-operations)
3. [LineItem Operations](#lineitem-operations)
4. [Campaign Operations](#campaign-operations)
5. [Storage Functions](#storage-functions)
6. [Schema Management](#schema-management)
7. [Excel Integration](#excel-integration)
8. [Utility Functions](#utility-functions)

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
- **Description**: Retrieves campaigns with metadata and statistics
- **Key Use Cases**: Campaign reporting, dashboard data
- **Parameters**:
  - `filters`: Dictionary of filter criteria
  - `include_stats`: Include summary statistics
  - `return_dataframe`: Return pandas DataFrame instead of list
- **Example**:
```python
# Get all campaigns with stats
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
- **Parameters**:
  - `created_by`: Creator name/email
  - `campaign_name`: Campaign name
  - `campaign_objective`: Campaign objective
  - `campaign_start_date`: Start date
  - `campaign_end_date`: End date
  - `campaign_budget`: Total budget
- **Example**:
```python
from mediaplanpy import MediaPlan
from datetime import date
from decimal import Decimal

media_plan = MediaPlan.create(
    created_by="john.doe@company.com",
    campaign_name="Q4 Brand Campaign",
    campaign_objective="awareness",
    campaign_start_date=date(2024, 10, 1),
    campaign_end_date=date(2024, 12, 31),
    campaign_budget=Decimal("100000"),
    product_name="Premium Product Line"
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
- **Description**: Exports media plan to Excel format
- **Key Use Cases**: Client reporting, offline editing, presentation
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
migrated_plan = media_plan.migrate_to_version(to_version="2.0")
```

### Custom Fields (v2.0 Feature)

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

The `LineItem` class represents individual line items within media plans. LineItems primarily inherit methods from `BaseModel` and don't have many specialized external methods beyond the standard model operations.

### LineItem Data Model

LineItems contain rich data fields following the v2.0 schema:

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

**New v2.0 Fields**:
- `cost_currency`: Currency code
- `dayparts`: Time periods for ad delivery
- `inventory`: Inventory type
- Custom dimension fields (`dim_custom1` through `dim_custom10`)

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

### Campaign Data Model

**Core Fields**:
- `id`: Unique identifier
- `name`: Campaign name
- `objective`: Campaign objective (awareness, conversion, etc.)
- `start_date`, `end_date`: Campaign duration
- `budget_total`: Total campaign budget

**New v2.0 Fields**:
- `budget_currency`: Currency code
- `agency_id`, `agency_name`: Agency information
- `advertiser_id`, `advertiser_name`: Advertiser information
- `campaign_type_id`, `campaign_type_name`: Campaign classification
- `workflow_status_id`, `workflow_status_name`: Status tracking

### Validation Methods

**`validate_dates() -> Campaign`**
- **Location**: `src/mediaplanpy/models/campaign.py:94`
- **Description**: Validates start_date <= end_date
- **Key Use Cases**: Date consistency validation

**`validate_budget() -> Campaign`**
- **Location**: `src/mediaplanpy/models/campaign.py:110`
- **Description**: Validates budget > 0
- **Key Use Cases**: Budget validation

### Inherited Methods from BaseModel

Campaigns inherit standard model methods like `to_dict()`, `validate_model()`, etc.

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
- **Returns**: Current version (e.g., "2.0")

**`get_supported_versions() -> List[str]`**
- **Location**: `src/mediaplanpy/schema/__init__.py:60`
- **Description**: Gets supported schema versions
- **Key Use Cases**: Version compatibility checking
- **Returns**: List of supported versions

### Validation Functions

**`validate(media_plan, version=None) -> List[str]`**
- **Location**: `src/mediaplanpy/schema/__init__.py:70`
- **Description**: Validates media plan against schema
- **Key Use Cases**: Data validation, compliance checking
- **Example**:
```python
from mediaplanpy.schema import validate

errors = validate(media_plan_data, "2.0")
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

migrated_data = migrate(old_plan, "1.0", "2.0")
```

### Version Utility Functions

**`normalize_version(version) -> str`**
- **Description**: Normalizes version format (v1.0.0 → 1.0)
- **Key Use Cases**: Version comparison, normalization

**`get_compatibility_type(version) -> str`**
- **Description**: Gets compatibility type for version
- **Returns**: "current", "backwards_compatible", "deprecated", "unsupported"

---

## Excel Integration

Functions for Excel format support.

**`export_to_excel(media_plan, path=None, template_path=None, include_documentation=True, workspace_manager=None, **kwargs) -> str`**
- **Location**: `src/mediaplanpy/excel/exporter.py:30`
- **Description**: Exports media plan to Excel (v2.0 only)
- **Key Use Cases**: Client deliverables, offline editing
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
- **Description**: Imports from Excel with validation
- **Key Use Cases**: Client data import, offline editing workflow

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

## Best Practices

1. **Always use WorkspaceManager** for production workflows
2. **Enable validation** by default (`validate_version=True`)
3. **Check compatibility** before operations on mixed-version data
4. **Use dry_run** for destructive operations when possible
5. **Handle version migration** gracefully with proper error handling

---

*This API reference covers MediaPlanPy SDK v2.0.3. For the latest updates, see the project's CHANGE_LOG.md.*