# Changelog

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