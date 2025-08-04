# MediaPlanPy - Technical Architecture & Implementation Summary

## Table of Contents
1. [Project Overview](#project-overview)
2. [Package & Module Architecture](#package--module-architecture)
3. [Core Data Models & Classes](#core-data-models--classes)
4. [Method Signatures Reference](#method-signatures-reference)
5. [Design Patterns & Architectural Patterns](#design-patterns--architectural-patterns)
6. [Configuration & Workspace System](#configuration--workspace-system)
7. [Database & Persistence](#database--persistence)
8. [Constants & Configuration Values](#constants--configuration-values)

---

## Project Overview

### Purpose & Scope
MediaPlanPy is an open source Python SDK that provides foundational tools for building, managing, and analyzing media plans based on the open data standard (mediaplanschema). It serves as the official Python implementation of the MediaPlan Schema standard.

### Target Users
- Media planners and advertising professionals
- Developers building media planning applications
- Data analysts working with media plan data
- Teams needing programmatic access to media plan operations

### Key Features
- **Multi-Format Support**: JSON, Excel, and Parquet files
- **Schema Versioning**: Automatic version detection and migration (v1.0 ↔ v2.0)
- **Flexible Storage**: Local filesystem, S3, Google Drive, and PostgreSQL backends
- **Workspace Management**: Multi-environment support with isolated configurations
- **CLI Interface**: Comprehensive command-line tools
- **Validation Framework**: Schema-based validation with detailed error reporting
- **Analytics Ready**: Built-in Parquet generation and SQL query capabilities
- **Database Integration**: Automatic PostgreSQL synchronization

### Technology Stack
- **Core Language**: Python 3.8+
- **Data Models**: Pydantic 2.0+ for validation and serialization
- **Data Processing**: Pandas 1.3+ for data manipulation
- **File Formats**: OpenPyXL (Excel), PyArrow (Parquet), JSON (built-in)
- **Database**: PostgreSQL via psycopg2-binary
- **Cloud Storage**: Boto3 (S3), Google API Client (Drive)
- **Analytics**: DuckDB for advanced querying
- **Schema**: JSON Schema with custom validation logic

---

## Package & Module Architecture

### Directory Structure

```
src/mediaplanpy/
├── __init__.py                 # Package initialization, version management
├── cli.py                      # Command-line interface
├── exceptions.py               # Custom exception hierarchy
├── models/                     # Core data models
│   ├── __init__.py
│   ├── base.py                 # BaseModel with common functionality
│   ├── campaign.py             # Campaign model with v2.0 fields
│   ├── dictionary.py           # CustomFieldConfig and Dictionary models
│   ├── lineitem.py             # LineItem model with 60+ fields
│   ├── mediaplan.py            # MediaPlan orchestration model
│   ├── mediaplan_database.py   # Database integration patches
│   ├── mediaplan_excel.py      # Excel integration patches
│   ├── mediaplan_json.py       # JSON integration patches
│   └── mediaplan_storage.py    # Storage integration patches
├── schema/                     # Schema management and validation
│   ├── __init__.py
│   ├── definitions/            # JSON schema files
│   │   ├── 1.0/               # v1.0 schema definitions
│   │   └── 2.0/               # v2.0 schema definitions
│   ├── manager.py              # High-level schema operations
│   ├── migration.py            # Schema migration logic
│   ├── registry.py             # Schema registry and loading
│   ├── validator.py            # Schema validation engine
│   ├── version_utils.py        # Version comparison utilities
│   └── schema_versions.json    # Version metadata
├── storage/                    # Storage backends and formats
│   ├── __init__.py
│   ├── base.py                 # Abstract storage interface
│   ├── database.py             # PostgreSQL backend
│   ├── local.py                # Local filesystem backend
│   ├── s3.py                   # AWS S3 backend
│   ├── gdrive.py               # Google Drive backend
│   └── formats/                # File format handlers
│       ├── __init__.py
│       ├── base.py             # Abstract format interface
│       ├── json_format.py      # JSON serialization
│       └── parquet.py          # Parquet serialization
├── excel/                      # Excel integration
│   ├── __init__.py
│   ├── exporter.py             # Excel export functionality
│   ├── importer.py             # Excel import functionality
│   ├── format_handler.py       # Excel format processing
│   ├── validator.py            # Excel validation
│   └── templates/              # Excel templates
│       └── default_template.xlsx
└── workspace/                  # Workspace management
    ├── __init__.py
    ├── loader.py               # WorkspaceManager class
    ├── query.py                # Cross-workspace querying
    ├── validator.py            # Workspace validation
    └── schemas/                # Workspace schema definitions
        └── workspace.schema.json
```

### Module Dependencies

**Core Dependency Flow:**
```
mediaplanpy.__init__ 
├── models/* (core data structures)
│   └── base.py (shared functionality)
├── schema/* (validation & migration)
├── storage/* (persistence backends)
├── excel/* (Excel integration)
└── workspace/* (configuration management)
```

**Key Integration Points:**
- `models.mediaplan` imports and orchestrates all other models
- `workspace.loader` provides configuration to all other modules
- `schema.validator` is used by all models for validation
- `storage.base` defines interfaces implemented by all backends

### Package Organization

**Models Package** (`mediaplanpy.models`):
- Core business objects representing media plan entities
- Pydantic-based with automatic validation and serialization
- Integration modules patch additional methods onto core models

**Schema Package** (`mediaplanpy.schema`):
- JSON schema management and validation
- Version migration and compatibility checking
- Centralized schema registry with bundled definitions

**Storage Package** (`mediaplanpy.storage`):
- Abstract storage interface with multiple backends
- Format handlers for different file types
- Database integration for analytics and synchronization

**Excel Package** (`mediaplanpy.excel`):
- Specialized Excel import/export functionality
- Template-based formatting with custom validation
- Integration with the core model system

**Workspace Package** (`mediaplanpy.workspace`):
- Configuration management and environment isolation
- Cross-workspace querying and data discovery
- Automatic migration of deprecated configuration fields

### Entry Points

**Primary APIs:**
```python
# Package-level imports
from mediaplanpy import MediaPlan, WorkspaceManager, validate, migrate

# CLI interface
mediaplanpy --help
mediaplanpy workspace init
mediaplanpy schema validate
```

**Usage Patterns:**
```python
# High-level API
workspace = WorkspaceManager()
workspace.load()
media_plan = MediaPlan.create(...)
media_plan.save(workspace)

# Direct model usage
media_plan = MediaPlan.load(workspace, path="plan.json")
errors = media_plan.validate_comprehensive()
```

---

## Core Data Models & Classes

### Class Hierarchy

```
BaseModel (mediaplanpy.models.base)
├── Meta (mediaplanpy.models.mediaplan)
├── Campaign (mediaplanpy.models.campaign)
├── LineItem (mediaplanpy.models.lineitem)
├── Dictionary (mediaplanpy.models.dictionary)
├── CustomFieldConfig (mediaplanpy.models.dictionary)
├── MediaPlan (mediaplanpy.models.mediaplan)
├── Budget (mediaplanpy.models.campaign) [Legacy]
└── TargetAudience (mediaplanpy.models.campaign) [Legacy]
```

### BaseModel (mediaplanpy.models.base.BaseModel)

**Purpose**: Foundation class providing common functionality for all media plan models.

**Key Attributes:**
- `model_config`: Pydantic configuration for validation behavior
- `SCHEMA_VERSION`: Class property returning current schema version

**Constructor Signature:**
```python
def __init__(self, **data)
```

**Key Methods:**
```python
def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]
def to_json(self, exclude_none: bool = True, indent: int = 2) -> str
def validate_model(self) -> List[str]
def assert_valid(self) -> None
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "BaseModel"
@classmethod
def from_json(cls, json_str: str) -> "BaseModel"
def validate_against_schema(self, validator: Optional[SchemaValidator] = None) -> List[str]
def deep_copy(self) -> "BaseModel"
```

### MediaPlan (mediaplanpy.models.mediaplan.MediaPlan)

**Purpose**: Top-level orchestration model representing a complete media plan with metadata, campaign, line items, and configuration dictionary.

**Key Attributes:**
```python
meta: Meta                              # Metadata and identification
campaign: Campaign                      # Campaign details and budget
lineitems: List[LineItem] = []         # List of line items
dictionary: Optional[Dictionary] = None # v2.0: Custom field configuration
```

**Constructor Signature:**
```python
def __init__(self, 
             meta: Meta, 
             campaign: Campaign, 
             lineitems: List[LineItem] = None,
             dictionary: Optional[Dictionary] = None)
```

**Relationships:**
- **Composition**: Contains Meta, Campaign, LineItem objects
- **Aggregation**: Optional Dictionary for custom field configuration
- **Associations**: Links to WorkspaceManager for persistence operations

**Key Methods:**
```python
# Line Item Management
def create_lineitem(self, line_items: Union[LineItem, Dict, List], validate: bool = True, **kwargs) -> Union[LineItem, List[LineItem]]
def load_lineitem(self, line_item_id: str) -> Optional[LineItem]
def update_lineitem(self, line_item: LineItem, validate: bool = True) -> LineItem
def delete_lineitem(self, line_item_id: str, validate: bool = False) -> bool

# Media Plan Lifecycle
def archive(self, workspace_manager: 'WorkspaceManager') -> None
def restore(self, workspace_manager: 'WorkspaceManager') -> None
def set_as_current(self, workspace_manager: 'WorkspaceManager', update_self: bool = True) -> Dict[str, Any]

# Validation and Migration
def validate_comprehensive(self, validator: Optional[SchemaValidator] = None, version: Optional[str] = None) -> Dict[str, List[str]]
def migrate_to_version(self, migrator: Optional[SchemaMigrator] = None, to_version: Optional[str] = None) -> "MediaPlan"

# v2.0 Dictionary Management
def get_custom_field_config(self, field_name: str) -> Optional[Dict[str, Any]]
def set_custom_field_config(self, field_name: str, enabled: bool, caption: Optional[str] = None)
def get_enabled_custom_fields(self) -> Dict[str, str]

# Factory Methods
@classmethod
def create(cls, created_by: str, campaign_name: str, campaign_objective: str, 
           campaign_start_date: Union[str, date], campaign_end_date: Union[str, date],
           campaign_budget: Union[str, int, float, Decimal], **kwargs) -> "MediaPlan"

# Version Compatibility
@classmethod
def check_schema_version(cls, data: Dict[str, Any]) -> None
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "MediaPlan"
```

### Campaign (mediaplanpy.models.campaign.Campaign)

**Purpose**: Represents campaign-level information including budget, targeting, and v2.0 organizational fields.

**Key Attributes:**
```python
# Required fields
id: str
name: str
objective: str
start_date: date
end_date: date
budget_total: Decimal

# v2.0 New Fields
budget_currency: Optional[str] = None        # Currency code (USD, EUR, GBP)
agency_id: Optional[str] = None              # Agency identification
agency_name: Optional[str] = None
advertiser_id: Optional[str] = None          # Client/advertiser identification
advertiser_name: Optional[str] = None
product_id: Optional[str] = None             # Product identification
campaign_type_id: Optional[str] = None       # Campaign type classification
campaign_type_name: Optional[str] = None
workflow_status_id: Optional[str] = None     # Workflow tracking
workflow_status_name: Optional[str] = None

# Audience and Targeting (v1.0 compatible)
audience_name: Optional[str] = None
audience_age_start: Optional[int] = None
audience_age_end: Optional[int] = None
audience_gender: Optional[str] = None        # ["Male", "Female", "Any"]
audience_interests: Optional[List[str]] = None
location_type: Optional[str] = None          # ["Country", "State"]
locations: Optional[List[str]] = None
```

**Constructor Signature:**
```python
def __init__(self, id: str, name: str, objective: str, start_date: date, 
             end_date: date, budget_total: Decimal, **kwargs)
```

### LineItem (mediaplanpy.models.lineitem.LineItem)

**Purpose**: Represents the most granular executable unit of a media plan with comprehensive field support.

**Key Attributes:**
```python
# Required fields
id: str
name: str
start_date: date
end_date: date
cost_total: Decimal

# v2.0 New Fields
cost_currency: Optional[str] = None          # Currency for all cost fields
dayparts: Optional[str] = None               # Time period targeting
dayparts_custom: Optional[str] = None
inventory: Optional[str] = None              # Inventory type specification
inventory_custom: Optional[str] = None

# Channel and Vehicle (v1.0 compatible)
channel: Optional[str] = None                # Primary channel category
vehicle: Optional[str] = None                # Platform/vehicle
partner: Optional[str] = None                # Publisher/partner
media_product: Optional[str] = None          # Media product offering

# Cost Breakdown (6 fields)
cost_media: Optional[Decimal] = None
cost_buying: Optional[Decimal] = None
cost_platform: Optional[Decimal] = None
cost_data: Optional[Decimal] = None
cost_creative: Optional[Decimal] = None
cost_custom1-10: Optional[Decimal] = None    # 10 custom cost fields

# Metrics - Standard (v1.0: 3 fields, v2.0: +17 new fields)
metric_impressions: Optional[Decimal] = None
metric_clicks: Optional[Decimal] = None
metric_views: Optional[Decimal] = None
# v2.0 New Standard Metrics
metric_engagements: Optional[Decimal] = None
metric_followers: Optional[Decimal] = None
metric_visits: Optional[Decimal] = None
metric_leads: Optional[Decimal] = None
metric_sales: Optional[Decimal] = None
metric_add_to_cart: Optional[Decimal] = None
metric_app_install: Optional[Decimal] = None
metric_application_start: Optional[Decimal] = None
metric_application_complete: Optional[Decimal] = None
metric_contact_us: Optional[Decimal] = None
metric_download: Optional[Decimal] = None
metric_signup: Optional[Decimal] = None
metric_max_daily_spend: Optional[Decimal] = None
metric_max_daily_impressions: Optional[Decimal] = None
metric_audience_size: Optional[Decimal] = None
metric_custom1-10: Optional[Decimal] = None  # 10 custom metric fields

# Custom Dimensions (10 fields)
dim_custom1-10: Optional[str] = None         # Flexible custom categorization
```

**Constructor Signature:**
```python
def __init__(self, id: str, name: str, start_date: date, end_date: date, 
             cost_total: Decimal, **kwargs)
```

**Key Methods:**
```python
def validate(self) -> List[str]              # Comprehensive validation
```

### Meta (mediaplanpy.models.mediaplan.Meta)

**Purpose**: Metadata container for media plan identification and status tracking.

**Key Attributes:**
```python
# Required fields
id: str                                      # Unique media plan identifier
schema_version: str                          # Schema version ("v1.0", "v2.0")
created_by_name: str                         # v2.0: Required creator name

# Optional fields
created_at: datetime = datetime.now()
name: Optional[str] = None                   # Media plan display name
comments: Optional[str] = None

# v2.0 New Status Fields
created_by_id: Optional[str] = None          # Creator user ID
is_current: Optional[bool] = None            # Current version flag
is_archived: Optional[bool] = None           # Archive status
parent_id: Optional[str] = None              # Parent plan reference
```

### Dictionary (mediaplanpy.models.dictionary.Dictionary)

**Purpose**: v2.0 configuration system for enabling and labeling custom fields.

**Key Attributes:**
```python
custom_dimensions: Optional[Dict[str, CustomFieldConfig]] = None    # dim_custom1-10 config
custom_metrics: Optional[Dict[str, CustomFieldConfig]] = None       # metric_custom1-10 config
custom_costs: Optional[Dict[str, CustomFieldConfig]] = None         # cost_custom1-10 config
```

**Key Methods:**
```python
def is_field_enabled(self, field_name: str) -> bool
def get_field_caption(self, field_name: str) -> Optional[str]
def get_enabled_fields(self) -> Dict[str, str]
```

### CustomFieldConfig (mediaplanpy.models.dictionary.CustomFieldConfig)

**Purpose**: Configuration object for individual custom fields.

**Key Attributes:**
```python
status: str                                  # "enabled" or "disabled"
caption: Optional[str] = None                # Display label for the field
```

---

## Method Signatures Reference

### MediaPlan Core Operations

```python
# Creation and Loading
@classmethod
def create(cls, created_by: str, campaign_name: str, campaign_objective: str,
          campaign_start_date: Union[str, date], campaign_end_date: Union[str, date],
          campaign_budget: Union[str, int, float, Decimal], schema_version: Optional[str] = None,
          workspace_manager: Optional['WorkspaceManager'] = None, **kwargs) -> "MediaPlan"

@classmethod  
def load(cls, workspace_manager: 'WorkspaceManager', path: Optional[str] = None,
        media_plan_id: Optional[str] = None, validate_version: bool = True,
        auto_migrate: bool = True) -> "MediaPlan"

# Persistence Operations  
def save(self, workspace_manager: 'WorkspaceManager', path: Optional[str] = None,
        overwrite: bool = False, include_parquet: bool = False,
        include_database: bool = False, set_as_current: bool = False,
        validate_version: bool = True) -> str

def delete(self, workspace_manager: 'WorkspaceManager', include_parquet: bool = True,
          include_database: bool = True) -> Dict[str, bool]

# Line Item Management
def create_lineitem(self, line_items: Union[LineItem, Dict[str, Any], List[Union[LineItem, Dict[str, Any]]]],
                   validate: bool = True, **kwargs) -> Union[LineItem, List[LineItem]]

def load_lineitem(self, line_item_id: str) -> Optional[LineItem]

def update_lineitem(self, line_item: LineItem, validate: bool = True) -> LineItem

def delete_lineitem(self, line_item_id: str, validate: bool = False) -> bool

# Status Management
def archive(self, workspace_manager: 'WorkspaceManager') -> None

def restore(self, workspace_manager: 'WorkspaceManager') -> None

def set_as_current(self, workspace_manager: 'WorkspaceManager', 
                  update_self: bool = True) -> Dict[str, Any]

# Validation and Migration
def validate_model(self) -> List[str]

def validate_against_schema(self, validator: Optional[SchemaValidator] = None,
                           version: Optional[str] = None) -> List[str]

def validate_comprehensive(self, validator: Optional[SchemaValidator] = None,
                          version: Optional[str] = None) -> Dict[str, List[str]]

def migrate_to_version(self, migrator: Optional[SchemaMigrator] = None,
                      to_version: Optional[str] = None) -> "MediaPlan"

# Excel Integration
def export_to_excel(self, workspace_manager: 'WorkspaceManager', file_path: str,
                   template_path: Optional[str] = None, include_documentation: bool = True,
                   include_dictionary: bool = True) -> str

def import_from_excel(self, workspace_manager: 'WorkspaceManager', file_path: str,
                     validate_schema: bool = True, auto_migrate: bool = True) -> Dict[str, Any]

def update_from_excel(self, workspace_manager: 'WorkspaceManager', file_path: str,
                     validate_schema: bool = True) -> Dict[str, Any]

# v2.0 Dictionary Management
def get_custom_field_config(self, field_name: str) -> Optional[Dict[str, Any]]

def set_custom_field_config(self, field_name: str, enabled: bool, 
                           caption: Optional[str] = None)

def get_enabled_custom_fields(self) -> Dict[str, str]
```

### WorkspaceManager Operations

```python
# Workspace Lifecycle
def __init__(self, workspace_path: Optional[str] = None)

def create(self, settings_path_name: Optional[str] = None,
          settings_file_name: Optional[str] = None,
          storage_path_name: Optional[str] = None,
          workspace_name: str = "Default", overwrite: bool = False,
          **kwargs) -> Tuple[str, str]

def load(self, workspace_path: Optional[str] = None,
        workspace_id: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]

def validate(self) -> bool

# Configuration Access
def get_resolved_config(self) -> Dict[str, Any]
def get_storage_config(self) -> Dict[str, Any]
def get_database_config(self) -> Dict[str, Any]
def get_excel_config(self) -> Dict[str, Any]

# Backend Access
def get_storage_backend(self) -> 'StorageBackend'
def get_schema_manager(self) -> 'SchemaManager'

# Status Checking
def check_workspace_active(self, operation: str, allow_warnings: bool = False) -> None
def check_excel_enabled(self, operation: str) -> None

# Version Management
def upgrade_workspace(self, target_sdk_version: Optional[str] = None,
                     dry_run: bool = False) -> Dict[str, Any]

def get_workspace_version_info(self) -> Dict[str, Any]
def check_workspace_compatibility(self) -> Dict[str, Any]

# Media Plan Operations
def validate_media_plan(self, media_plan: Dict[str, Any],
                       version: Optional[str] = None) -> List[str]

def migrate_media_plan(self, media_plan: Dict[str, Any],
                      to_version: Optional[str] = None) -> Dict[str, Any]

# Querying (from workspace.query patch)
def list_media_plans(self, include_archived: bool = True,
                    campaign_id: Optional[str] = None) -> List[Dict[str, Any]]

def search_media_plans(self, query: str, fields: Optional[List[str]] = None,
                      include_archived: bool = True) -> List[Dict[str, Any]]

def get_media_plan_summary(self, media_plan_id: str) -> Optional[Dict[str, Any]]
```

### Schema Management Operations

```python
# SchemaValidator
def validate(self, media_plan: Dict[str, Any], version: Optional[str] = None) -> List[str]
def validate_comprehensive(self, media_plan: Dict[str, Any], 
                          version: Optional[str] = None) -> Dict[str, List[str]]
def validate_file(self, file_path: str, version: Optional[str] = None) -> List[str]

# SchemaMigrator  
def migrate(self, media_plan: Dict[str, Any], from_version: str, 
           to_version: str) -> Dict[str, Any]
def can_migrate(self, from_version: str, to_version: str) -> bool
def get_migration_path(self, from_version: str, to_version: str) -> List[str]

# SchemaRegistry
def get_schema(self, version: str) -> Dict[str, Any]
def get_current_version(self) -> str
def get_supported_versions(self) -> List[str]
def is_version_supported(self, version: str) -> bool
```

---

## Design Patterns & Architectural Patterns

### Core Design Patterns

**1. Repository Pattern**
- **Implementation**: `WorkspaceManager` and storage backends
- **Purpose**: Abstracts data persistence from business logic
- **Location**: `mediaplanpy.workspace.loader`, `mediaplanpy.storage.*`

**2. Strategy Pattern**
- **Implementation**: Storage backends and format handlers
- **Purpose**: Pluggable algorithms for different storage types and file formats
- **Location**: `mediaplanpy.storage.base.StorageBackend`, `mediaplanpy.storage.formats.base.FormatHandler`

**3. Factory Pattern**
- **Implementation**: `get_storage_backend()`, `get_format_handler_instance()`
- **Purpose**: Creates appropriate backend/handler instances based on configuration
- **Location**: `mediaplanpy.storage.__init__`

**4. Command Pattern**
- **Implementation**: CLI command structure
- **Purpose**: Encapsulates operations as objects for command-line interface
- **Location**: `mediaplanpy.cli`

**5. Template Method Pattern**
- **Implementation**: `BaseModel` validation methods
- **Purpose**: Defines validation algorithm structure with customizable steps
- **Location**: `mediaplanpy.models.base.BaseModel`

**6. Observer Pattern (Implicit)**
- **Implementation**: Validation and migration hooks
- **Purpose**: Automatic validation triggers on model changes
- **Location**: Pydantic model validators

**7. Decorator Pattern**
- **Implementation**: Model integration patches
- **Purpose**: Extends MediaPlan with additional functionality without inheritance
- **Location**: `mediaplanpy.models.mediaplan_*.py` modules

### Architectural Patterns

**1. Layered Architecture**
```
Presentation Layer    → CLI, API endpoints
Business Logic Layer → Models, validation, migration
Data Access Layer    → Storage backends, database integration
Infrastructure Layer → Schema registry, workspace management
```

**2. Plugin Architecture**
- **Extension Points**: Storage backends, format handlers, validation rules
- **Registration**: Dictionary-based registries for backend discovery
- **Interface**: Abstract base classes define contracts

**3. Configuration-Driven Architecture**
- **Workspace System**: Central configuration management
- **Environment Isolation**: Multiple workspace support
- **Feature Toggles**: Enable/disable functionality via configuration

**4. Schema-Driven Development**
- **JSON Schema**: Defines data structure and validation rules
- **Version Management**: Automated migration between schema versions
- **Validation Framework**: Centralized validation using schema definitions

### Error Handling Strategy

**Exception Hierarchy:**
```python
MediaPlanError                    # Base exception
├── WorkspaceError               # Workspace-related errors
│   ├── WorkspaceNotFoundError
│   ├── WorkspaceValidationError
│   ├── WorkspaceInactiveError
│   └── FeatureDisabledError
├── SchemaError                  # Schema-related errors
│   ├── SchemaVersionError
│   ├── SchemaRegistryError
│   ├── SchemaMigrationError
│   ├── ValidationError
│   ├── UnsupportedVersionError
│   └── VersionCompatibilityError
└── StorageError                 # Storage-related errors
    ├── FileReadError
    ├── FileWriteError
    ├── S3Error
    └── DatabaseError
```

**Error Handling Principles:**
- **Fail Fast**: Validate inputs early and raise specific exceptions
- **Error Context**: Include detailed context in error messages
- **Recovery Options**: Provide suggestions for resolving errors
- **Logging**: Comprehensive logging at appropriate levels

**Validation Strategy:**
- **Multi-Level Validation**: Pydantic field validators + model validators + schema validation
- **Comprehensive Reporting**: Categorized errors (errors, warnings, info)
- **Business Rules**: Custom validation methods for domain-specific rules

---

## Configuration & Workspace System

### Workspace Concept

A **workspace** in MediaPlanPy represents an isolated environment containing:
- **Storage Configuration**: Where media plans are stored (local, S3, database)
- **Schema Settings**: Version preferences and migration settings
- **Feature Toggles**: Enable/disable Excel, database, etc.
- **Environment Settings**: Development, staging, production configurations

### Workspace Settings Structure

**v2.0 Configuration Format:**
```json
{
  "workspace_id": "workspace_12345678",
  "workspace_name": "Production Environment",
  "workspace_status": "active",
  "environment": "production",
  
  "workspace_settings": {
    "schema_version": "2.0",
    "last_upgraded": "2024-01-15",
    "sdk_version_required": "2.0.x"
  },
  
  "storage": {
    "mode": "local",
    "local": {
      "base_path": "/data/mediaplans",
      "create_if_missing": true
    }
  },
  
  "database": {
    "enabled": true,
    "host": "localhost",
    "port": 5432,
    "database": "mediaplans",
    "schema": "public",
    "table_name": "media_plans"
  },
  
  "excel": {
    "enabled": true,
    "default_template": "templates/default_template.xlsx"
  }
}
```

### Settings Management

**Configuration Loading Priority:**
1. Explicit path parameter
2. Environment variable `MEDIAPLANPY_WORKSPACE_PATH`
3. Current working directory `./workspace.json`
4. User config directories (`~/.config/mediaplanpy/workspace.json`)

**Automatic Migration:**
- Deprecated `schema_settings` fields automatically migrated to `workspace_settings`
- v2.0 defaults applied for missing configuration values
- Configuration files updated in-place when migration occurs

**Variable Resolution:**
```json
{
  "storage": {
    "local": {
      "base_path": "${user_documents}/MediaPlans"
    }
  }
}
```

**Supported Variables:**
- `${user_documents}`: User's Documents directory
- `${user_home}`: User's home directory

### Environment Handling

**Environment Types:**
- **development**: Relaxed validation, detailed logging
- **staging**: Production-like with additional debugging
- **production**: Strict validation, optimized performance

**Environment-Specific Behavior:**
```python
# Development
workspace.config['environment'] = 'development'
# Enables: verbose logging, schema warnings, experimental features

# Production  
workspace.config['environment'] = 'production'
# Enables: strict validation, performance optimization, minimal logging
```

### Workspace Status Management

**Status Values:**
- **active**: Full functionality enabled
- **inactive**: Read-only mode, prevents modifications
- **maintenance**: Limited operations during upgrades

**Status Checking:**
```python
# Automatic status validation
workspace.check_workspace_active("media plan creation")
# Raises WorkspaceInactiveError if inactive

# Feature-specific checks
workspace.check_excel_enabled("Excel export")
# Raises FeatureDisabledError if Excel disabled
```

---

## Database & Persistence

### Database Integration Overview

MediaPlanPy provides optional PostgreSQL integration for:
- **Analytics and Reporting**: Flattened data optimized for SQL queries
- **Cross-Plan Analysis**: Query multiple media plans simultaneously  
- **Data Synchronization**: Automatic sync with file-based storage
- **Performance**: Indexed queries for large datasets

### Database Schema Structure

**Main Table: `media_plans`**
```sql
CREATE TABLE media_plans (
    -- Primary identification
    media_plan_id VARCHAR(255) PRIMARY KEY,
    media_plan_name VARCHAR(500),
    schema_version VARCHAR(20) NOT NULL,
    
    -- v2.0 Meta fields
    created_by_name VARCHAR(255) NOT NULL,
    created_by_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN,
    is_archived BOOLEAN,
    parent_id VARCHAR(255),
    
    -- Campaign information
    campaign_id VARCHAR(255) NOT NULL,
    campaign_name VARCHAR(500) NOT NULL,
    campaign_objective VARCHAR(500),
    campaign_start_date DATE NOT NULL,
    campaign_end_date DATE NOT NULL,
    campaign_budget_total DECIMAL(15,2) NOT NULL,
    
    -- v2.0 Campaign fields
    campaign_budget_currency VARCHAR(3),
    agency_id VARCHAR(255),
    agency_name VARCHAR(500),
    advertiser_id VARCHAR(255),
    advertiser_name VARCHAR(500),
    campaign_type_id VARCHAR(255),
    campaign_type_name VARCHAR(255),
    workflow_status_id VARCHAR(255),
    workflow_status_name VARCHAR(255),
    
    -- Line item information
    lineitem_id VARCHAR(255) NOT NULL,
    lineitem_name VARCHAR(500) NOT NULL,
    lineitem_start_date DATE NOT NULL,
    lineitem_end_date DATE NOT NULL,
    lineitem_cost_total DECIMAL(15,2) NOT NULL,
    
    -- v2.0 LineItem fields
    lineitem_cost_currency VARCHAR(3),
    lineitem_dayparts VARCHAR(255),
    lineitem_inventory VARCHAR(255),
    
    -- Channel and targeting
    lineitem_channel VARCHAR(255),
    lineitem_vehicle VARCHAR(255),
    lineitem_partner VARCHAR(255),
    
    -- Cost breakdown (6 standard + 10 custom)
    lineitem_cost_media DECIMAL(15,2),
    lineitem_cost_buying DECIMAL(15,2),
    lineitem_cost_platform DECIMAL(15,2),
    lineitem_cost_data DECIMAL(15,2),
    lineitem_cost_creative DECIMAL(15,2),
    lineitem_cost_custom1 DECIMAL(15,2),
    -- ... lineitem_cost_custom2-10
    
    -- Standard metrics (3 legacy + 17 v2.0)
    lineitem_metric_impressions DECIMAL(15,2),
    lineitem_metric_clicks DECIMAL(15,2),
    lineitem_metric_views DECIMAL(15,2),
    lineitem_metric_engagements DECIMAL(15,2),
    lineitem_metric_leads DECIMAL(15,2),
    lineitem_metric_sales DECIMAL(15,2),
    -- ... additional v2.0 metrics
    
    -- Custom metrics (10 fields)
    lineitem_metric_custom1 DECIMAL(15,2),
    -- ... lineitem_metric_custom2-10
    
    -- Custom dimensions (10 fields)
    lineitem_dim_custom1 VARCHAR(500),
    -- ... lineitem_dim_custom2-10
    
    -- Timestamps
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(1000),
    
    -- Indexes for performance
    INDEX idx_campaign_id (campaign_id),
    INDEX idx_schema_version (schema_version),
    INDEX idx_created_at (created_at),
    INDEX idx_is_current (is_current),
    INDEX idx_workflow_status (workflow_status_name),
    INDEX idx_campaign_dates (campaign_start_date, campaign_end_date)
);
```

### Database Operations

**Connection Management:**
```python
class PostgreSQLBackend:
    def get_connection(self) -> psycopg2.extensions.connection
    def test_connection(self) -> bool
    def close_connection(self) -> None
```

**Schema Management:**
```python
def create_table(self) -> bool                    # Create table with v2.0 schema
def validate_schema(self) -> bool                 # Validate existing schema compatibility
def migrate_schema(self) -> Dict[str, Any]        # Upgrade schema to v2.0
def table_exists(self) -> bool                    # Check table existence
```

**Data Operations:**
```python
def insert_media_plan(self, media_plan: MediaPlan) -> bool
def update_media_plan(self, media_plan: MediaPlan) -> bool
def delete_media_plan(self, media_plan_id: str) -> bool
def upsert_media_plan(self, media_plan: MediaPlan) -> bool
```

**Query Operations:**
```python
def get_media_plan_summary(self, media_plan_id: str) -> Optional[Dict[str, Any]]
def list_media_plans(self, campaign_id: Optional[str] = None, 
                    include_archived: bool = True) -> List[Dict[str, Any]]
def search_media_plans(self, query: str, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]
def get_version_statistics(self) -> Dict[str, int]
```

### Data Synchronization

**Automatic Sync Triggers:**
- `MediaPlan.save()` with `include_database=True`
- `MediaPlan.set_as_current()` (always syncs)
- `MediaPlan.archive()` and `MediaPlan.restore()`

**Sync Process:**
1. **Validation**: Check database schema compatibility
2. **Flattening**: Convert hierarchical MediaPlan to flat row structure
3. **Upsert**: Insert or update database record
4. **Verification**: Confirm successful sync

**Data Flattening Strategy:**
```python
# Hierarchical JSON
{
  "meta": {"id": "plan_123", "name": "Q1 Campaign"},
  "campaign": {"id": "camp_456", "budget_total": 50000},
  "lineitems": [
    {"id": "li_789", "cost_total": 25000},
    {"id": "li_890", "cost_total": 25000}
  ]
}

# Flattened Database Rows (2 rows)
media_plan_id: plan_123, campaign_id: camp_456, lineitem_id: li_789, lineitem_cost_total: 25000
media_plan_id: plan_123, campaign_id: camp_456, lineitem_id: li_890, lineitem_cost_total: 25000
```

### Version Compatibility

**Supported Versions:**
- **v1.0**: Full compatibility, all fields mapped
- **v2.0**: Native support, all new fields included
- **v0.0**: **REJECTED** - No longer supported in SDK v2.0

**Migration Process:**
```python
def migrate_existing_data(self) -> Dict[str, Any]:
    """
    Migrate existing database records to v2.0 format.
    Rejects v0.0 records completely.
    """
    # 1. Identify v0.0 records -> REJECT
    # 2. Migrate v1.0 records -> v2.0 format
    # 3. Update schema_version fields
    # 4. Add v2.0 columns with defaults
```

---

## Constants & Configuration Values

### Version Information

```python
# Package version constants (mediaplanpy/__init__.py)
__version__ = '2.0.1'                    # SDK version
__schema_version__ = '2.0'               # Current schema version
CURRENT_MAJOR = 2                        # Major version number
CURRENT_MINOR = 0                        # Minor version number
SUPPORTED_MAJOR_VERSIONS = [1, 2]        # Supported major versions

VERSION_NOTES = {
    '1.0.0': 'v1.0 schema support with new versioning strategy - Schema 1.0',
    '2.0.0': 'v2.0 schema support with v1.0 backwards compatibility - v0.0 support removed',
    '2.0.1': 'v2.0 schema support with minor non-breaking functionality upgrades'
}
```

### File Paths and Defaults

```python
# Workspace configuration (mediaplanpy/workspace/loader.py)
DEFAULT_FILENAME = "workspace.json"
ENV_VAR_NAME = "MEDIAPLANPY_WORKSPACE_PATH"

# Default workspace directories
DEFAULT_WORKSPACE_DIRECTORY = {
    'windows': "C:/mediaplanpy",
    'unix': "~/mediaplanpy"
}

# Schema file paths
SCHEMA_DEFINITIONS_PATH = "src/mediaplanpy/schema/definitions/"
SCHEMA_VERSIONS = {
    "1.0": "definitions/1.0/mediaplan.schema.json",
    "2.0": "definitions/2.0/mediaplan.schema.json"
}
```

### Field Constants

```python
# Campaign field validation (mediaplanpy/models/campaign.py)
VALID_OBJECTIVES = {
    "awareness", "consideration", "conversion", "retention", "loyalty", "other"
}

VALID_GENDERS = {"Male", "Female", "Any"}
VALID_LOCATION_TYPES = {"Country", "State"}

# v2.0 New constants
COMMON_CAMPAIGN_TYPES = {
    "Brand Awareness", "Performance", "Retargeting", "Launch", 
    "Seasonal", "Always On", "Tactical"
}

COMMON_WORKFLOW_STATUSES = {
    "Draft", "In Review", "Approved", "Live", "Paused", "Completed", "Cancelled"
}

# LineItem field validation (mediaplanpy/models/lineitem.py)  
VALID_CHANNELS = {
    "social", "search", "display", "video", "audio", "tv", "ooh", "print", "other"
}

VALID_KPIS = {"cpm", "cpc", "cpa", "ctr", "cpv", "cpl", "roas", "other"}

# v2.0 New constants
COMMON_DAYPARTS = {
    "All Day", "Morning", "Afternoon", "Evening", "Primetime", 
    "Late Night", "Weekdays", "Weekends"
}

COMMON_INVENTORY_TYPES = {
    "Premium", "Remnant", "Private Marketplace", "Open Exchange", 
    "Direct", "Programmatic", "Reserved", "Unreserved"
}

# Dictionary field validation (mediaplanpy/models/dictionary.py)
VALID_DIMENSION_FIELDS = {f"dim_custom{i}" for i in range(1, 11)}
VALID_METRIC_FIELDS = {f"metric_custom{i}" for i in range(1, 11)}
VALID_COST_FIELDS = {f"cost_custom{i}" for i in range(1, 11)}
```

### Storage Configuration

```python
# Storage backend registry (mediaplanpy/storage/__init__.py)
_storage_backends = {
    'local': LocalStorageBackend,
    's3': S3StorageBackend,
    'gdrive': GoogleDriveStorageBackend
}

# Format handler registry (mediaplanpy/storage/formats/__init__.py)
_format_handlers = {
    'json': JsonFormatHandler,
    'parquet': ParquetFormatHandler
}

# File extensions mapping
FORMAT_EXTENSIONS = {
    '.json': 'json',
    '.parquet': 'parquet',
    '.xlsx': 'excel',
    '.xls': 'excel'
}
```

### Database Configuration

```python
# Database defaults (mediaplanpy/storage/database.py)
DEFAULT_DATABASE_CONFIG = {
    'port': 5432,
    'schema': 'public',
    'table_name': 'media_plans',
    'connection_timeout': 30,
    'auto_create_table': True,
    'ssl': True
}

# Database field mappings
DATABASE_FIELD_MAPPINGS = {
    'meta.id': 'media_plan_id',
    'meta.name': 'media_plan_name',
    'meta.schema_version': 'schema_version',
    'campaign.id': 'campaign_id',
    'campaign.budget_total': 'campaign_budget_total'
    # ... complete mapping for all fields
}
```

### Validation Settings

```python
# Schema validation settings (mediaplanpy/schema/validator.py)
VALIDATION_CATEGORIES = {
    'errors': [],     # Blocking validation failures
    'warnings': [],   # Non-blocking issues
    'info': []        # Informational messages
}

# Version compatibility matrix (mediaplanpy/schema/version_utils.py)
VERSION_COMPATIBILITY = {
    'v0.0': 'unsupported',      # Completely removed in SDK v2.0
    'v1.0': 'backward_compatible',
    'v2.0': 'native',
    'v2.1': 'forward_minor'     # Future versions
}
```

### Excel Configuration

```python
# Excel template settings (mediaplanpy/excel/exporter.py)
EXCEL_WORKSHEET_NAMES = {
    'lineitems': 'Line Items',
    'dictionary': 'Dictionary', 
    'documentation': 'Documentation'
}

EXCEL_COLUMN_MAPPINGS = {
    'lineitem.id': 'Line Item ID',
    'lineitem.name': 'Line Item Name',
    'lineitem.cost_total': 'Total Cost'
    # ... complete column mapping
}

# Excel validation rules
EXCEL_VALIDATION_RULES = {
    'required_columns': ['Line Item ID', 'Line Item Name', 'Total Cost'],
    'numeric_columns': ['Total Cost', 'Impressions', 'Clicks'],
    'date_columns': ['Start Date', 'End Date']
}
```

---

**End of Technical Architecture Summary**

This comprehensive reference document covers all major architectural components, design patterns, and implementation details of the MediaPlanPy codebase. Use this as your primary reference for understanding the system structure and making informed development decisions.