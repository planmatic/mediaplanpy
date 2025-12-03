# Changelog

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