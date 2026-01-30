# Changelog

## [v3.0.0] - 2026-01-30

### Major Release - Schema v3.0 Support

This is a major release with comprehensive enhancements across schema support, formula systems, Excel integration, CLI capabilities, and developer documentation.

### Added
- **Schema v3.0 Support** (40% more fields: 155 vs 116 in v2.0)
  - Target audiences and locations now support arrays with 13+ attributes each
  - Metric formulas for calculated metrics (power functions, conversion rates, cost-per-unit, constant)
  - Campaign KPI tracking fields (kpi_name1-5, kpi_value1-5)
  - Custom dimension fields at Meta and Campaign levels (dim_custom1-5)
  - Custom properties objects for extensibility at all levels
  - 11 new standard metrics (view_starts, view_completions, reach, units, impression_share, page_views, likes, shares, comments, conversions)
  - Buy information fields (buy_type, buy_commitment)
  - Multi-currency support (cost_currency_exchange_rate)
  - Budget constraints for optimization (cost_minimum, cost_maximum)
  - Aggregation support (is_aggregate, aggregation_level)

- **3-Tier Formula Hierarchy System**
  - LineItem-level formula overrides for flexible metric calculations
  - Dictionary-level default formulas for workspace-wide consistency
  - System-level defaults for standard behavior
  - New `LineItem.get_metric_formula_definition()` method for hierarchy resolution
  - Enhanced `LineItem.configure_metric_formula()` with formula_type and base_metric override support
  - Support for all formula types: cost_per_unit, conversion_rate, power_function, constant
  - Automatic dependency resolution and topological sorting for formula calculations
  - Formula recalculation engine with support for complex dependency chains

- **Enhanced CLI for Workspace Management**
  - New `mediaplanpy workspace upgrade` command for v2.0 → v3.0 migration
  - Interactive upgrade process with automatic backup creation
  - Workspace validation and version enforcement
  - Improved command structure and help documentation
  - Better error handling and user feedback

- **Revamped Examples Library**
  - Comprehensive examples demonstrating all key SDK functionality
  - Formula system examples (hierarchy, calculation, dependency chains)
  - Excel import/export workflows with formula preservation
  - Database integration patterns
  - Advanced querying and analytics examples
  - Migration and workspace management examples
  - All examples updated for v3.0 schema

### Improved
- **Migration System** (CLI-based)
  - **Use CLI command `mediaplanpy workspace upgrade` for migration** (recommended approach)
  - v2.0 → v3.0 migration with automatic audience/location name generation
  - Systematic name generation rules for target_audiences and target_locations arrays
  - Dictionary field renamed: custom_dimensions → lineitem_custom_dimensions
  - Workspace upgrade requires explicit user action (strict version enforcement)
  - Automatic validation before and after migration
  - Comprehensive backup system before any destructive operations
  - Removed v0.0 and v1.0 support (breaking change)

- **Excel Integration - Formula-Aware Import/Export**
  - **Export**: Smart column generation based on dictionary formula configurations
    - Creates appropriate columns (CPU, CVR, Constant, Coefficient) based on formula_type
    - Excel formulas match actual formula types (not hardcoded to cost_per_unit)
    - Coefficient values exported from metric_formulas when available
    - Reverse-calculated coefficients when formulas don't exist
    - Parameter columns for power_function formulas
    - Separate Target Audiences and Target Locations worksheets
  - **Import**: Automatic coefficient updates from edited values
    - Reads coefficient/parameter columns based on dictionary configuration
    - Updates metric_formulas coefficients when users edit metric values
    - Processes dependencies in topological order (handles chains)
    - Formula-aware: respects formula_type when calculating coefficients
    - Preserves lineitem-level formula overrides through JSON column
  - Full round-trip integrity: export → edit → import → export maintains all formula configurations

- **Database & Storage**
  - Enhanced database schema migration with ALTER TABLE support for v2.0 → v3.0 upgrades
  - New columns for target_audiences, target_locations, metric_formulas (JSONB)
  - Automatic backups created before workspace upgrades
  - Comprehensive validation for new array and formula structures
  - Improved PostgreSQL performance with optimized indexing

- **Workspace Management**
  - Strict version enforcement: v3.0 SDK only loads v3.0 workspaces
  - Enhanced workspace settings validation
  - Improved error messages for version mismatches
  - Better logging and diagnostic information

### Breaking Changes
- **SDK v3.0.x only loads v3.0 workspaces**
  - v2.0 workspaces must be explicitly upgraded using `mediaplanpy workspace upgrade`
  - SDK v2.0.7 must be used to continue working with v2.0 workspaces
  - No backward compatibility - strict version enforcement
- **Schema v0.0 and v1.0 no longer supported** (removed from codebase)
- **Campaign schema restructuring** (handled automatically by migration):
  - Audience fields (audience_name, audience_age_*, audience_gender, audience_interests) → target_audiences array
  - Location fields (location_type, locations) → target_locations array
- **Dictionary schema changes**:
  - custom_dimensions renamed to lineitem_custom_dimensions
  - New groups added: meta_custom_dimensions, campaign_custom_dimensions, standard_metrics
- **Excel format changes**:
  - Separate worksheets for Target Audiences and Target Locations
  - Formula-specific columns (CPU/CVR/Constant/Coefficient) based on dictionary configuration
  - Metric Formulas JSON column for lineitem-level overrides
- **API changes**:
  - Removed deprecated from_v0_* and from_v1_* conversion methods
  - 47 methods updated to support new v3.0 schema structures

### Migration Guide
**For v2.0 Users**: To upgrade existing v2.0 workspaces to v3.0:
```bash
# Upgrade using CLI (recommended)
mediaplanpy workspace upgrade

# Or continue using SDK v2.0.7
pip install mediaplanpy==2.0.7
```

See detailed migration guide: [docs/migration_guide_v2_to_v3.md](docs/migration_guide_v2_to_v3.md)

### Documentation
- Updated README.md with v3.0 installation instructions and version guidance
- Updated GET_STARTED.md with v3.0 examples and migration paths
- New cloud_storage_configuration.md guide for S3 setup with workspace isolation best practices
- New database_configuration.md guide for PostgreSQL setup
- Revamped SDK_REFERENCE.md with v3.0 API documentation
- Complete examples library demonstrating all v3.0 features
- Migration guide with systematic rules for v2.0 → v3.0 transformation

### Technical Improvements
- Enhanced schema validation with comprehensive v3.0 field validation
- Improved error messages and logging throughout the SDK
- Better performance for formula calculations with optimized dependency resolution
- Memory optimization for large media plans with formulas
- Type hints and documentation improvements across codebase
- Enhanced test coverage for v3.0 features

### Version Compatibility
- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Schema**: v3.0 (v2.0 migration support via CLI)
- **PyPI Package**: Available as `pip install mediaplanpy`

---

## [v2.0.7] - 2025-10-18

### Fixed
- `Workspace.list_campaigns()`
  Bug fix whereby duplicate entries were being returned in campaign list.


## [v2.0.6] - 2025-10-10

### Fixed
- `MediaPlan.load()`
  Change approach to loading S3 Storage Backend due to circular import issues on Linux.

### Improved
- `Workspace.create()`
  Optimized indexing for PostgreSQL database table and removed unnecessary indexes.
  Note: Existing databases are not automatically upgraded with new indexes.
- `Mediaplan.load()`, `Mediaplan.import_from_excel()`, `Mediaplan.import_from_json()`  
  Removed unnecessary media plan data validation for agency, advertiser, product and workflow_status id / names.


## [v2.0.5] - 2025-09-10

### Improved
- `MediaPlan.set_as_current()`
  Performance optimization for faster execution in large workspaces with cloud-based storage.
- `Workspace.sql_query()`  
  Performance optimization for single plan SQL queries on database enabled workspaces.


## [v2.0.4] - 2025-09-08

### Improved
- `Workspace.sql_query()`  
  Upgraded performance for S3 storage by querying Database (PostgreSQL) instead of Parquet files, when enabled.
- `Workspace.list_campaigns()`  
  Upgraded performance by leveraging native workspace.sql_query() method. 
- `Workspace.list_mediaplans()`  
  Upgraded performance by leveraging native workspace.sql_query() method. 
- `Workspace.list_lineitems()`  
  Upgraded performance by leveraging native workspace.sql_query() method. 


## [v2.0.3] - 2025-08-26

### Added
- S3 Storage Support  
  Cloud storage in S3 now supported across all core SDK functionality. Configure in Workspace Settings JSON. 


## [v2.0.2] - 2025-08-25

### Improved
- `MediaPlan.export_to_excel()`
  Added formulas for cost allocation and metric columns so that they auto-calculate with budget changes.
- `Workspace.create()`
  Upgraded to include database connection settings in default Workspace Settings for ease of configuration.


## [v2.0.1] - 2025-07-31

### Added
- `MediaPlan.archive(workspace_manager)`  
  Archive a media plan by marking it as archived (`is_archived=True`), saving its status and updating storage/database accordingly. 
  Prevents archiving if the plan is currently current (`is_current=True`).
- `MediaPlan.restore(workspace_manager)`  
  Restore an archived media plan by setting `is_archived=False` and updating storage/database accordingly.
- `MediaPlan.set_as_current(workspace_manager)`  
  Promotes the selected media plan to be the current version for its campaign, automatically demoting any other plans marked as current.
- `MediaPlan.save(set_as_current=True)` *(optional argument)*  
  New boolean flag added to the `save()` method to allow setting a plan as current at the time of saving.

### Improved
- `MediaPlan.export_to_excel()`  
  Enhanced layout and formatting of the exported Excel workbook, especially the **Dictionary** and **Documentation** worksheets, for improved readability and compliance with schema documentation standards.

### Fixed
- `MediaPlan.import()`  
  Improved validation to prevent duplicate line item IDs and custom column captions during plan import, ensuring better data integrity.