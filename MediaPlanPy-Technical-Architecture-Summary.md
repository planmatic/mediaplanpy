# MediaPlanPy - Technical Architecture & Implementation Summary

## Table of Contents

1. [Project Overview](#project-overview)
2. [Package & Module Architecture](#package--module-architecture)
3. [Core Data Models & Classes](#core-data-models--classes)
4. [Design Patterns & Architectural Patterns](#design-patterns--architectural-patterns)
5. [Data Flow & Integration Points](#data-flow--integration-points)
6. [Configuration & Workspace System](#configuration--workspace-system)
7. [CLI Interface & Commands](#cli-interface--commands)
8. [Database & Persistence](#database--persistence)
9. [Validation & Schema System](#validation--schema-system)
10. [File Processing & Format Handlers](#file-processing--format-handlers)
11. [Method Signatures Reference](#method-signatures-reference)
12. [Constants & Configuration Values](#constants--configuration-values)
13. [Error Handling & Exception Hierarchy](#error-handling--exception-hierarchy)
14. [Extension & Customization Points](#extension--customization-points)
15. [Dependencies & External Integrations](#dependencies--external-integrations)
16. [Logging & Debugging](#logging--debugging)

---

## Project Overview

### Purpose & Scope
MediaPlanPy is the official Python SDK for the MediaPlan Schema standard, providing comprehensive tools for building, managing, and analyzing media plans. It implements the open data standard for media planning with full schema validation, versioning, and migration capabilities.

### Target Users
- **Media Planners**: Create, manage, and analyze media plans
- **Developers**: Build applications that handle media plan data
- **Data Analysts**: Query and analyze media plan metrics
- **System Integrators**: Connect media planning systems

### Key Features
- **Multi-Format Support**: JSON, Excel, Parquet file handling
- **Schema Versioning**: v1.0 and v2.0 support with automatic migration
- **Flexible Storage**: Local filesystem, S3, Google Drive, PostgreSQL backends
- **Workspace Management**: Multi-environment configuration system
- **CLI Interface**: Complete command-line toolset
- **Validation Framework**: Schema-based validation with detailed error reporting
- **Database Integration**: PostgreSQL synchronization for analytics

### Technology Stack
- **Primary Language**: Python 3.8+
- **Core Framework**: Pydantic v2 for data validation
- **Data Processing**: Pandas for data manipulation
- **File Formats**: openpyxl (Excel), pyarrow (Parquet), jsonschema
- **Storage**: boto3 (S3), google-api-python-client (Google Drive)
- **Database**: psycopg2-binary (PostgreSQL), duckdb (Analytics)
- **CLI**: argparse with hierarchical command structure

---

## Package & Module Architecture

### Directory Structure
```
src/mediaplanpy/
├── __init__.py                 # Main package entry point
├── cli.py                      # Command-line interface
├── exceptions.py               # Custom exception hierarchy
├── models/                     # Core data models
│   ├── __init__.py
│   ├── base.py                 # BaseModel with common functionality
│   ├── campaign.py             # Campaign model
│   ├── dictionary.py           # Custom field configuration
│   ├── lineitem.py             # LineItem model
│   ├── mediaplan.py            # MediaPlan model (main entity)
│   ├── mediaplan_database.py   # Database integration patches
│   ├── mediaplan_excel.py      # Excel integration patches
│   ├── mediaplan_json.py       # JSON integration patches
│   └── mediaplan_storage.py    # Storage integration patches
├── schema/                     # Schema validation and migration
│   ├── __init__.py
│   ├── definitions/            # JSON schema definitions
│   │   ├── 1.0/               # v1.0 schemas
│   │   └── 2.0/               # v2.0 schemas
│   ├── manager.py              # Schema management
│   ├── migration.py            # Schema migration logic
│   ├── registry.py             # Schema registry
│   ├── schema_versions.json    # Version metadata
│   ├── validator.py            # Schema validation
│   └── version_utils.py        # Version compatibility utilities
├── storage/                    # Storage backends and formats
│   ├── __init__.py
│   ├── base.py                 # Abstract storage backend
│   ├── database.py             # Database storage
│   ├── formats/                # Format handlers
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract format handler
│   │   ├── json_format.py      # JSON format handler
│   │   └── parquet.py          # Parquet format handler
│   ├── gdrive.py               # Google Drive backend
│   ├── local.py                # Local filesystem backend
│   └── s3.py                   # S3 storage backend
├── workspace/                  # Workspace management
│   ├── __init__.py
│   ├── loader.py               # WorkspaceManager
│   ├── query.py                # Query functionality
│   ├── schemas/                # Workspace schemas
│   │   └── workspace.schema.json
│   └── validator.py            # Workspace validation
└── excel/                      # Excel processing
    ├── __init__.py
    ├── exporter.py             # Excel export functionality
    ├── format_handler.py       # Excel format handler
    ├── importer.py             # Excel import functionality
    ├── templates/              # Excel templates
    │   └── default_template.xlsx
    └── validator.py            # Excel validation
```

### Module Dependencies
- **models** → schema, exceptions
- **storage** → exceptions, models
- **workspace** → storage, schema, exceptions
- **excel** → models, storage, workspace
- **cli** → workspace, schema, models, excel
- **schema** → exceptions

### Package Organization
- **Core Models**: Pydantic-based data models with validation
- **Storage Layer**: Pluggable storage backends with format handlers
- **Schema System**: JSON schema validation and migration
- **Workspace Management**: Configuration and environment handling
- **Excel Integration**: Import/export with template support
- **CLI Interface**: Complete command-line functionality

### Entry Points
- **CLI**: `mediaplanpy` command (entry point in pyproject.toml)
- **Python API**: Import from `mediaplanpy` package
- **Direct Module Access**: Individual component imports

---

## Core Data Models & Classes

### BaseModel (`src/mediaplanpy/models/base.py`)
**Purpose**: Foundation class for all MediaPlan models, extends Pydantic BaseModel

**Key Attributes**:
- `SCHEMA_VERSION`: Current schema version property
- `model_config`: Pydantic configuration (extra='allow', validate_assignment=True)

**Constructor**: Standard Pydantic initialization

**Critical Methods**:
```python
def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]
def to_json(self, exclude_none: bool = True, indent: int = 2) -> str
def validate_model(self) -> List[str]  # Override in subclasses
def assert_valid(self) -> None
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "BaseModel"
@classmethod
def from_json(cls, json_str: str) -> "BaseModel"
def export_to_json(self, file_path: str, indent: int = 2) -> None
def validate_against_schema(self, validator: Optional[SchemaValidator] = None) -> List[str]
def deep_copy(self) -> "BaseModel"
```

### MediaPlan (`src/mediaplanpy/models/mediaplan.py`)
**Purpose**: Main entity representing a complete media plan

**Key Attributes**:
- `meta: Meta` - Metadata including ID, schema version, creation info
- `campaign: Campaign` - Campaign details and configuration
- `lineitems: List[LineItem]` - List of line items
- `dictionary: Optional[Dictionary]` - Custom field configuration (v2.0)

**Constructor**: 
```python
MediaPlan(meta: Meta, campaign: Campaign, lineitems: List[LineItem], dictionary: Optional[Dictionary] = None)
```

**Critical Methods**:
```python
@classmethod
def check_schema_version(cls, data: Dict[str, Any]) -> None
def validate_model(self) -> List[str]
def create_lineitem(self, line_items: Union[LineItem, Dict, List], validate: bool = True, **kwargs) -> Union[LineItem, List[LineItem]]
def load_lineitem(self, line_item_id: str) -> Optional[LineItem]
def update_lineitem(self, line_item: LineItem, validate: bool = True) -> LineItem
def delete_lineitem(self, line_item_id: str, validate: bool = False) -> bool
def calculate_total_cost(self) -> Decimal
@classmethod
def create(cls, created_by: str, campaign_name: str, campaign_objective: str, 
           campaign_start_date: Union[str, date], campaign_end_date: Union[str, date], 
           campaign_budget: Union[str, int, float, Decimal], **kwargs) -> "MediaPlan"
def migrate_to_version(self, migrator: Optional[SchemaMigrator] = None, to_version: Optional[str] = None) -> "MediaPlan"
```

### Campaign (`src/mediaplanpy/models/campaign.py`)
**Purpose**: Represents campaign details within a media plan

**Key Attributes**:
- `id: str` - Unique identifier
- `name: str` - Campaign name
- `objective: str` - Campaign objective
- `start_date: date` - Campaign start date
- `end_date: date` - Campaign end date
- `budget_total: Decimal` - Total budget amount
- **v2.0 Fields**: `budget_currency`, `agency_id/name`, `advertiser_id/name`, `campaign_type_id/name`, `workflow_status_id/name`

**Constructor**: All required fields plus optional v2.0 fields

**Critical Methods**:
```python
def validate_model(self) -> List[str]
@classmethod
def from_v0_campaign(cls, v0_campaign: Dict[str, Any]) -> "Campaign"
```

### LineItem (`src/mediaplanpy/models/lineitem.py`)
**Purpose**: Represents individual line items within a media plan

**Key Attributes**:
- `id: str` - Unique identifier
- `name: str` - Line item name
- `start_date: date` - Start date
- `end_date: date` - End date
- `cost_total: Decimal` - Total cost
- **Channel Fields**: `channel`, `vehicle`, `partner`, `media_product`
- **Custom Fields**: `dim_custom1-10`, `cost_custom1-10`, `metric_custom1-10`
- **v2.0 Fields**: 17 new standard metrics, `cost_currency`, `dayparts`, `inventory`

**Constructor**: Required fields plus extensive optional field set

**Critical Methods**:
```python
def validate(self) -> List[str]  # Consolidated validation
def validate_model(self) -> List[str]  # Legacy method
@classmethod
def from_v0_lineitem(cls, v0_lineitem: Dict[str, Any]) -> "LineItem"
```

### Dictionary (`src/mediaplanpy/models/dictionary.py`)
**Purpose**: Configuration for custom fields (v2.0 feature)

**Key Attributes**:
- `custom_dimensions: Optional[Dict[str, CustomFieldConfig]]`
- `custom_metrics: Optional[Dict[str, CustomFieldConfig]]`
- `custom_costs: Optional[Dict[str, CustomFieldConfig]]`

**Critical Methods**:
```python
def is_field_enabled(self, field_name: str) -> bool
def get_field_caption(self, field_name: str) -> Optional[str]
def get_enabled_fields(self) -> Dict[str, str]
```

### Meta (`src/mediaplanpy/models/mediaplan.py`)
**Purpose**: Metadata for media plans

**Key Attributes**:
- `id: str` - Unique identifier
- `schema_version: str` - Schema version
- `created_by_name: str` - Creator name (required in v2.0)
- `created_at: datetime` - Creation timestamp
- **v2.0 Fields**: `created_by_id`, `is_current`, `is_archived`, `parent_id`

### Inheritance Hierarchy
```
BaseModel (Pydantic BaseModel)
├── MediaPlan
├── Campaign
├── LineItem
├── Dictionary
├── CustomFieldConfig
├── Meta
├── Budget (legacy)
└── TargetAudience (legacy)
```

---

## Design Patterns & Architectural Patterns

### Patterns Used

**1. Strategy Pattern**
- **Storage Backends**: `StorageBackend` abstract class with concrete implementations (`LocalStorageBackend`, `S3StorageBackend`, `GDriveStorageBackend`)
- **Format Handlers**: `FormatHandler` abstract class with concrete implementations (`JsonFormatHandler`, `ParquetFormatHandler`)

**2. Registry Pattern**
- **Storage Backend Registry**: `_storage_backends` dictionary in `storage/__init__.py`
- **Schema Registry**: `SchemaRegistry` class manages schema versions and definitions

**3. Factory Pattern**
- **Storage Backend Factory**: `get_storage_backend(workspace_config)` function
- **Format Handler Factory**: `get_format_handler_instance(format_name)` function

**4. Decorator/Mixin Pattern**
- **Model Extensions**: Database, Excel, JSON, and Storage functionality added via imports in `models/__init__.py`
- **Workspace Extensions**: Query functionality patched into `WorkspaceManager`

**5. Command Pattern**
- **CLI Interface**: Hierarchical command structure with handler functions
- **Migration Commands**: Schema migration operations encapsulated as commands

### Plugin/Extension System
- **Storage Backends**: Add new backends by implementing `StorageBackend` and registering in `_storage_backends`
- **Format Handlers**: Add new formats by implementing `FormatHandler` and registering
- **Model Extensions**: Patch additional methods into core models via module imports

### Configuration Management
- **Workspace Configuration**: JSON-based configuration with schema validation
- **Environment Variables**: Database passwords and external service credentials
- **Template System**: Excel templates for export formatting

### Error Handling Strategy
- **Exception Hierarchy**: Custom exceptions extending from `MediaPlanError`
- **Validation Errors**: Detailed error messages with field-level validation
- **Graceful Degradation**: Optional features fail gracefully when dependencies unavailable

---

## Data Flow & Integration Points

### Data Processing Pipeline
1. **Input**: JSON, Excel, or direct Python objects
2. **Validation**: Schema validation and business rule checking
3. **Migration**: Automatic version migration if needed
4. **Processing**: Model instantiation and manipulation
5. **Storage**: Persistence to configured storage backend
6. **Output**: JSON, Excel, Parquet, or database synchronization

### File Format Handling
**JSON Format**:
- **Input**: `MediaPlan.from_dict()`, `MediaPlan.import_from_json()`
- **Output**: `MediaPlan.to_dict()`, `MediaPlan.export_to_json()`
- **Validation**: Schema validation against JSON Schema definitions

**Excel Format**:
- **Input**: `MediaPlan.import_from_excel()` via `ExcelImporter`
- **Output**: `MediaPlan.export_to_excel()` via `ExcelExporter`
- **Templates**: Customizable Excel templates for formatting

**Parquet Format**:
- **Output**: Via `ParquetFormatHandler` for analytics
- **Structure**: Flattened structure optimized for analytics queries

### Storage Backends
**Local Storage**:
- **Implementation**: `LocalStorageBackend`
- **Configuration**: `base_path`, `create_if_missing`
- **Features**: Directory creation, file operations

**S3 Storage**:
- **Implementation**: `S3StorageBackend`
- **Configuration**: `bucket`, `prefix`, `profile`, `region`
- **Features**: AWS credential handling, object operations

**Google Drive Storage**:
- **Implementation**: `GDriveStorageBackend`
- **Configuration**: `folder_id`, `credentials_path`, `token_path`
- **Features**: OAuth authentication, folder operations

### Import/Export Workflows
**JSON Import**:
1. Load JSON file
2. Parse and validate structure
3. Check schema version compatibility
4. Migrate if needed
5. Create MediaPlan instance
6. Validate business rules

**Excel Import**:
1. Load Excel file using openpyxl
2. Extract data from worksheets
3. Map columns to model fields
4. Validate data types and constraints
5. Create MediaPlan instance
6. Apply custom field mappings

**Export Process**:
1. Serialize MediaPlan to dictionary
2. Apply format-specific transformations
3. Write to storage backend
4. Generate additional formats (Parquet) if configured
5. Sync to database if enabled

### Validation Pipeline
1. **Field Validation**: Pydantic field validators
2. **Model Validation**: Custom `validate_model()` methods
3. **Schema Validation**: JSON Schema validation
4. **Business Rules**: Cross-field and cross-model validation
5. **Comprehensive Validation**: Combined validation with categorized results

---

## Configuration & Workspace System

### Workspace Concept
A workspace defines the environment and configuration for media plan operations:
- **Storage Configuration**: Where media plans are stored
- **Schema Settings**: Version compatibility and migration preferences
- **Database Integration**: Optional PostgreSQL synchronization
- **Feature Toggles**: Enable/disable functionality per environment

### Configuration Schema
**Core Structure** (`workspace.schema.json`):
```json
{
  "workspace_id": "string (required)",
  "workspace_name": "string (required)", 
  "workspace_status": "active|inactive",
  "environment": "development|testing|production",
  "storage": { "mode": "local|s3|gdrive", ... },
  "workspace_settings": {
    "schema_version": "2.0",
    "last_upgraded": "2025-01-30",
    "sdk_version_required": "2.0.x"
  },
  "database": { "enabled": true, ... },
  "excel": { "enabled": true, ... },
  "logging": { "level": "INFO", ... }
}
```

### Settings Management
**WorkspaceManager** (`src/mediaplanpy/workspace/loader.py`):
```python
class WorkspaceManager:
    def __init__(self, workspace_path: Optional[str] = None)
    def load(self) -> Dict[str, Any]
    def validate(self) -> bool
    def get_resolved_config(self) -> Dict[str, Any]
    def create(self, **kwargs) -> Tuple[str, str]
    def upgrade_workspace(self, target_sdk_version: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]
    def check_workspace_compatibility(self) -> Dict[str, Any]
```

### Environment Handling
- **Development**: Relaxed validation, local storage default
- **Testing**: Stricter validation, isolated storage
- **Production**: Full validation, enterprise storage backends

### Configuration Resolution
1. Load workspace.json
2. Resolve environment variables
3. Apply environment-specific overrides
4. Validate final configuration
5. Create resolved configuration object

---

## CLI Interface & Commands

### Command Structure
**Hierarchical Organization**:
```
mediaplanpy
├── workspace
│   ├── init          # Create workspace
│   ├── validate      # Validate workspace
│   ├── info          # Show workspace info
│   ├── upgrade       # Upgrade workspace
│   ├── version       # Version information
│   └── check         # Compatibility check
├── schema
│   ├── info          # Schema information
│   ├── versions      # List versions
│   ├── validate      # Validate media plan
│   └── migrate       # Migrate schema version
├── excel
│   ├── export        # Export to Excel
│   ├── import        # Import from Excel
│   ├── update        # Update from Excel
│   └── validate      # Validate Excel file
└── mediaplan
    ├── create        # Create new media plan
    └── delete        # Delete media plan
```

### Command Handlers
**Handler Pattern**: Each command group has dedicated handler functions
- `handle_workspace_*()` functions for workspace operations
- `handle_schema_*()` functions for schema operations
- `handle_excel_*()` functions for Excel operations
- `handle_mediaplan_*()` functions for media plan operations

### Argument Patterns
**Common Arguments**:
- `--workspace`: Path to workspace.json
- `--version`: Schema version specification
- `--output`: Output file path
- `--dry-run`: Preview mode without changes

### Help System
- **Contextual Help**: Command-specific help messages
- **Version Information**: SDK and schema version display
- **Feature Discovery**: Show v2.0 features and capabilities

---

## Database & Persistence

### Database Integration
**PostgreSQL Backend**:
- **Purpose**: Analytics and reporting on media plan data
- **Implementation**: `mediaplan_database.py` patches methods into `MediaPlan`
- **Table Structure**: Flattened structure optimized for queries
- **Synchronization**: Automatic sync on save operations

### Schema Management
**Database Schema**:
- **Table**: Configurable table name (default: `media_plans`)
- **Columns**: All media plan fields flattened
- **Indexes**: Optimized for common query patterns
- **Constraints**: Foreign keys and validation constraints

### Query System
**Query Interface**:
```python
# Patched into WorkspaceManager via workspace/query.py
def query_mediaplans(self, **filters) -> List[Dict[str, Any]]
def get_mediaplan_summary(self, **filters) -> Dict[str, Any]
def aggregate_costs(self, group_by: List[str], **filters) -> Dict[str, Any]
```

**DuckDB Integration**:
- **Purpose**: Local analytics without PostgreSQL setup
- **Features**: SQL queries on media plan data
- **Performance**: Optimized for analytical workloads

### Data Synchronization
**Sync Process**:
1. MediaPlan saved to storage
2. Extract data for database
3. Transform to flat structure
4. Insert/update database record
5. Handle conflicts and errors

---

## Validation & Schema System

### Schema Versions
**Version Management**:
- **Current**: v2.0 (major version with new features)
- **Supported**: v1.0 (deprecated but supported with migration)
- **Removed**: v0.0 (no longer supported)

**Version Compatibility**:
```python
# From schema_versions.json
{
  "current": "2.0",
  "supported": ["1.0", "2.0"],
  "deprecated": ["1.0"],
  "compatibility": {
    "v2.0": {"supports": ["2.0"], "migrates_from": ["1.0"]},
    "v1.0": {"supports": ["1.0"], "migrates_from": []}
  }
}
```

### Validation Framework
**Multi-Level Validation**:
1. **Field Level**: Pydantic field validators
2. **Model Level**: Custom validation methods
3. **Schema Level**: JSON Schema validation
4. **Business Rules**: Cross-model validation

**SchemaValidator** (`src/mediaplanpy/schema/validator.py`):
```python
class SchemaValidator:
    def validate(self, data: Dict[str, Any], version: Optional[str] = None) -> List[str]
    def validate_file(self, file_path: str, version: Optional[str] = None) -> List[str]
    def validate_comprehensive(self, data: Dict[str, Any], version: Optional[str] = None) -> Dict[str, List[str]]
```

### Migration System
**SchemaMigrator** (`src/mediaplanpy/schema/migration.py`):
```python
class SchemaMigrator:
    def migrate(self, data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]
    def can_migrate(self, from_version: str, to_version: str) -> bool
    def get_migration_path(self, from_version: str, to_version: str) -> List[str]
```

**Migration Rules**:
- **v1.0 → v2.0**: Automatic migration, all new fields optional
- **v0.0 → v2.0**: Blocked, must use SDK v1.x first
- **Forward Compatibility**: v2.1 files downgraded to v2.0 with warnings

### Error Reporting
**Validation Results**:
```python
{
  "errors": ["Critical validation failures"],
  "warnings": ["Non-critical issues"], 
  "info": ["Informational messages"]
}
```

---

## File Processing & Format Handlers

### Format Handler Pattern
**Abstract Base Class** (`src/mediaplanpy/storage/formats/base.py`):
```python
class FormatHandler(abc.ABC):
    @abc.abstractmethod
    def serialize_to_file(self, data: Dict[str, Any], file_obj: Union[TextIO, BinaryIO]) -> None
    @abc.abstractmethod  
    def deserialize_from_file(self, file_obj: Union[TextIO, BinaryIO]) -> Dict[str, Any]
    @abc.abstractmethod
    def get_file_extension(self) -> str
```

### JSON Processing
**JsonFormatHandler**:
- **Serialization**: Standard JSON with proper date/decimal handling
- **Deserialization**: JSON parsing with validation
- **Features**: Pretty printing, custom encoders

### Excel Processing
**ExcelFormatHandler**:
- **Import Process**: Read worksheets, map columns, validate data
- **Export Process**: Apply templates, format cells, add documentation
- **Template System**: Customizable Excel templates
- **Validation**: Pre-import validation of Excel structure

**Excel Integration Methods** (patched into MediaPlan):
```python
def export_to_excel(self, file_path: str, template_path: Optional[str] = None, **options) -> str
@classmethod
def import_from_excel(cls, file_path: str) -> "MediaPlan"
def update_from_excel_path(self, file_path: str) -> None
@classmethod
def validate_excel(cls, file_path: str, schema_version: Optional[str] = None) -> List[str]
```

### Parquet Handling
**ParquetFormatHandler**:
- **Purpose**: Analytics-optimized format
- **Structure**: Flattened schema for efficient queries
- **Features**: Compression, columnar storage
- **Integration**: Generated alongside JSON storage

---

## Constants & Configuration Values

### Schema Constants
```python
# From __init__.py
__version__ = '2.0.0'
__schema_version__ = '2.0'
CURRENT_MAJOR = 2
CURRENT_MINOR = 0
SUPPORTED_MAJOR_VERSIONS = [1, 2]
```

### Field Validation Constants
**Campaign** (`src/mediaplanpy/models/campaign.py`):
```python
VALID_OBJECTIVES = {"awareness", "consideration", "conversion", "retention", "loyalty", "other"}
VALID_GENDERS = {"Male", "Female", "Any"}
VALID_LOCATION_TYPES = {"Country", "State"}
COMMON_CAMPAIGN_TYPES = {"Brand Awareness", "Performance", "Retargeting", "Launch", "Seasonal", "Always On", "Tactical"}
COMMON_WORKFLOW_STATUSES = {"Draft", "In Review", "Approved", "Live", "Paused", "Completed", "Cancelled"}
```

**LineItem** (`src/mediaplanpy/models/lineitem.py`):
```python
VALID_CHANNELS = {"social", "search", "display", "video", "audio", "tv", "ooh", "print", "other"}
VALID_KPIS = {"cpm", "cpc", "cpa", "ctr", "cpv", "cpl", "roas", "other"}
COMMON_DAYPARTS = {"All Day", "Morning", "Afternoon", "Evening", "Primetime", "Late Night", "Weekdays", "Weekends"}
COMMON_INVENTORY_TYPES = {"Premium", "Remnant", "Private Marketplace", "Open Exchange", "Direct", "Programmatic", "Reserved", "Unreserved"}
```

### Dictionary Constants
**Custom Field Definitions** (`src/mediaplanpy/models/dictionary.py`):
```python
VALID_DIMENSION_FIELDS = {f"dim_custom{i}" for i in range(1, 11)}
VALID_METRIC_FIELDS = {f"metric_custom{i}" for i in range(1, 11)}
VALID_COST_FIELDS = {f"cost_custom{i}" for i in range(1, 11)}
```

### Default Configuration Values
**Workspace Defaults**:
```python
{
  "environment": "development",
  "workspace_status": "active", 
  "storage": {"mode": "local", "local": {"create_if_missing": true}},
  "database": {"enabled": false, "port": 5432, "schema": "public"},
  "logging": {"level": "INFO"}
}
```

---

## Error Handling & Exception Hierarchy

### Custom Exception Classes
**Base Exception** (`src/mediaplanpy/exceptions.py`):
```python
MediaPlanError(Exception)  # Base for all package errors
├── WorkspaceError
│   ├── WorkspaceNotFoundError
│   ├── WorkspaceValidationError
│   ├── WorkspaceInactiveError
│   └── FeatureDisabledError
├── SchemaError
│   ├── SchemaVersionError
│   ├── SchemaRegistryError
│   ├── SchemaMigrationError
│   ├── ValidationError
│   ├── UnsupportedVersionError
│   └── VersionCompatibilityError
└── StorageError
    ├── FileReadError
    ├── FileWriteError
    ├── S3Error
    ├── DatabaseError
    └── SQLQueryError
```

### Error Handling Patterns
**Validation Errors**:
- **Field Level**: Pydantic ValidationError with field context
- **Model Level**: Custom validation with detailed messages
- **Schema Level**: JSON Schema validation errors

**Storage Errors**:
- **File Operations**: Wrapped with context information
- **Network Operations**: Retry logic and timeout handling
- **Authentication**: Clear credential error messages

**Migration Errors**:
- **Version Incompatibility**: Clear migration path guidance  
- **Data Transformation**: Preserve original data on failure
- **Schema Changes**: Detailed change documentation

### User-Facing Error Messages
**Error Message Patterns**:
- **❌**: Critical errors that prevent operation
- **⚠️**: Warnings that don't prevent operation
- **💡**: Recommendations and guidance
- **✨**: New features and capabilities

---

## Extension & Customization Points

### Plugin System
**Storage Backend Extension**:
1. Implement `StorageBackend` abstract class
2. Register in `_storage_backends` dictionary
3. Add configuration schema to workspace schema
4. Handle authentication and connection management

**Format Handler Extension**:
1. Implement `FormatHandler` abstract class
2. Register format mapping by file extension
3. Handle serialization/deserialization
4. Support both text and binary modes

### Custom Field System
**Dictionary-Based Configuration**:
- **Field Types**: Dimensions, metrics, costs (10 each)
- **Status**: Enabled/disabled per field
- **Captions**: Custom display names
- **Validation**: Type-specific validation rules

**Adding Custom Fields**:
1. Configure in Dictionary model
2. Use in LineItem instances
3. Validate through schema system
4. Export to Excel with custom headers

### Model Extensions
**Patching Pattern**:
- Database methods: `import mediaplanpy.models.mediaplan_database`
- Excel methods: `import mediaplanpy.models.mediaplan_excel`
- JSON methods: `import mediaplanpy.models.mediaplan_json`
- Storage methods: `import mediaplanpy.models.mediaplan_storage`

**Custom Validation**:
- Override `validate_model()` in subclasses
- Add business rule validation
- Integrate with schema validation system

### CLI Extensions
**Command Addition**:
1. Add command parser in `setup_argparse()`
2. Create handler function
3. Add to main command dispatcher
4. Include help text and argument validation

---

## Dependencies & External Integrations

### Required Dependencies
**Core Dependencies**:
```python
jsonschema>=4.0.0       # JSON schema validation
pydantic>=2.0.0         # Data validation and serialization
pandas>=1.3.0           # Data manipulation and analysis
openpyxl>=3.0.0         # Excel file processing
pyarrow>=7.0.0          # Parquet format support
duckdb>=0.9.2           # Local analytics database
```

**Cloud Storage**:
```python
boto3>=1.24.0                    # AWS S3 integration
google-api-python-client>=2.0.0  # Google Drive integration
google-auth-httplib2>=0.1.0      # Google authentication
google-auth-oauthlib>=0.5.0      # Google OAuth flow
```

**Database**:
```python
psycopg2-binary>=2.9.0  # PostgreSQL connectivity
```

### Optional Dependencies
**Development Tools**:
```python
pytest>=7.0.0          # Testing framework
pytest-cov>=4.0.0      # Coverage reporting
black>=22.0.0          # Code formatting
isort>=5.0.0           # Import sorting
mypy>=1.0.0            # Type checking
pre-commit>=2.0.0      # Git hooks
```

### External Service Integration
**AWS S3**:
- **Authentication**: AWS credentials via boto3
- **Features**: Bucket operations, object storage
- **Configuration**: Profile, region, bucket specification

**Google Drive**:
- **Authentication**: OAuth 2.0 flow
- **Features**: Folder operations, file sharing
- **Configuration**: Service account or user credentials

**PostgreSQL**:
- **Authentication**: Username/password or connection string
- **Features**: Table management, query execution
- **Configuration**: Host, port, database, schema specification

---

## Logging & Debugging

### Logging Hierarchy
**Logger Structure**:
```python
mediaplanpy                    # Root logger
├── mediaplanpy.models        # Model operations
│   ├── mediaplanpy.models.mediaplan  # MediaPlan operations
│   ├── mediaplanpy.models.campaign   # Campaign operations
│   └── mediaplanpy.models.lineitem   # LineItem operations
├── mediaplanpy.storage       # Storage operations
│   ├── mediaplanpy.storage.local     # Local storage
│   ├── mediaplanpy.storage.s3        # S3 operations
│   └── mediaplanpy.storage.gdrive    # Google Drive operations
├── mediaplanpy.schema        # Schema operations
│   ├── mediaplanpy.schema.validator  # Validation operations
│   └── mediaplanpy.schema.migration  # Migration operations
├── mediaplanpy.workspace     # Workspace operations
├── mediaplanpy.excel         # Excel operations
└── mediaplanpy.cli           # CLI operations
```

### Log Level Usage Patterns
**DEBUG**: Detailed execution flow, variable values, API calls
```python
logger.debug(f"Loading media plan from {file_path}")
logger.debug(f"Schema version compatibility: {compatibility}")
```

**INFO**: Normal operation flow, successful operations
```python
logger.info(f"Media plan migrated from {from_version} to {to_version}")
logger.info(f"Workspace created at {workspace_path}")
```

**WARNING**: Non-critical issues, deprecated features, compatibility warnings
```python
logger.warning(f"Schema version {file_version} is deprecated")
logger.warning(f"Custom field '{field_name}' enabled but not used")
```

**ERROR**: Operation failures, validation errors, system errors
```python
logger.error(f"Failed to connect to database: {error}")
logger.error(f"Schema validation failed: {errors}")
```

### Structured Logging
**Operation Context**:
```python
logger.info(f"📄 Migrating file: {args.file}")
logger.info(f"📋 From version: {from_version}")  
logger.info(f"🎯 To version: v{to_version}")
logger.info(f"✅ Migration completed successfully")
```

**Error Context**:
```python
logger.error(f"❌ Media plan validation failed with {len(errors)} errors:")
for i, error in enumerate(errors, 1):
    logger.error(f"   {i}. {error}")
```

### Debug Information
**Schema Operations**:
- Version compatibility checks
- Migration path determination
- Validation rule evaluation
- Field mapping during migration

**Storage Operations**:
- File path resolution
- Backend selection logic
- Authentication status
- Operation timing

**Model Operations**:
- Validation step execution
- Field transformation
- Business rule evaluation
- Cross-model relationship validation

### Troubleshooting Guidance
**Common Issues and Log Signatures**:

**Schema Version Issues**:
```
ERROR: Schema version v0.0 is not supported
SOLUTION: Use SDK v1.x to migrate v0.0 → v1.0 first
```

**Storage Connection Issues**:
```
ERROR: Failed to connect to S3 bucket 'bucket-name'
DEBUG: Using AWS profile 'default'
SOLUTION: Check AWS credentials and bucket permissions
```

**Validation Failures**:
```
ERROR: Line item starts before campaign: 2025-01-01 < 2025-01-15
SOLUTION: Adjust line item dates to be within campaign period
```

**Database Sync Issues**:
```
ERROR: Failed to sync to database: connection timeout
DEBUG: Database host: localhost:5432
SOLUTION: Check database connectivity and credentials
```

### Performance Monitoring
**Operation Timing**:
- Schema validation duration
- File I/O operations
- Database operations
- Migration processing time

**Resource Usage**:
- Memory usage for large media plans
- Disk space for storage operations
- Network usage for cloud operations

---

This technical summary provides a comprehensive reference for understanding and working with the MediaPlanPy codebase. Each section includes specific implementation details, method signatures, and architectural patterns that enable effective development and maintenance of the system.