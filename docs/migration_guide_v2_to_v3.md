# Migration Guide: v2.0 → v3.0

This guide provides step-by-step instructions for upgrading your MediaPlanPy SDK from v2.0 to v3.0.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Pre-Migration Checklist](#2-pre-migration-checklist)
3. [Schema Changes](#3-schema-changes)
4. [Workspace Upgrade](#4-workspace-upgrade)
5. [Code Migration](#5-code-migration)
6. [Excel File Changes](#6-excel-file-changes)
7. [Database Migration](#7-database-migration)
8. [Testing After Migration](#8-testing-after-migration)
9. [FAQs](#9-faqs)

---

## 1. Overview

### Why Upgrade to v3.0?

MediaPlanPy v3.0 introduces significant enhancements:

- **Target Audiences & Locations as Arrays**: Support for multiple audiences and locations per campaign with 13+ attributes each
- **Metric Formulas**: Calculate metrics using power functions, conversion rates, and cost-per-unit formulas
- **42+ New Fields**: Extended metadata, KPI tracking, custom dimensions at multiple levels
- **Improved Database Migration**: ALTER TABLE support for seamless schema upgrades
- **Better Excel Structure**: Separate worksheets for audiences and locations

### Breaking Changes Summary

⚠️ **Important**: v3.0 includes breaking changes:

1. **Campaign Structure**: `audience_*` and `location_*` fields replaced with arrays
2. **Dictionary Field**: `custom_dimensions` renamed to `lineitem_custom_dimensions`
3. **Legacy Support Removed**: v0.0 and v1.0 no longer supported
4. **Workspace Version Enforcement**: v3.0 SDK only loads v3.0 workspaces
5. **Excel Format**: New worksheet structure for audiences/locations

### Migration Timeline Recommendation

- **Small Projects** (< 10 media plans): 1-2 hours
- **Medium Projects** (10-100 media plans): 4-8 hours
- **Large Projects** (100+ media plans): 1-2 days

---

## 2. Pre-Migration Checklist

### Prerequisites

✅ **Before you begin, ensure you have**:

1. **Python 3.8+** installed
2. **Backup** of all media plan data (JSON files, database, Excel files)
3. **Git** for version control (recommended)
4. **Testing environment** to validate migration before production
5. **Access** to all storage backends (S3, Google Drive, database credentials)

### Installation

**Step 1**: Install MediaPlanPy v3.0.0

```bash
pip install --upgrade git+https://github.com/planmatic/mediaplanpy@v3.0.0
```

**Step 2**: Verify installation

```bash
python -c "import mediaplanpy; print(mediaplanpy.__version__)"
# Expected output: 3.0.0
```

### Backup Instructions

**Automatic Backups** (handled by upgrade process):
- JSON files: Copied to `mediaplans_backup_{timestamp}/`
- Database: Backup table created as `{table_name}_backup_{timestamp}`

**Manual Backup** (recommended as additional safety):

```bash
# Backup entire workspace directory
cp -r /path/to/workspace /path/to/workspace_backup_v2

# Export database (if using PostgreSQL)
pg_dump -h localhost -U user -d database > mediaplan_backup_v2.sql
```

---

## 3. Schema Changes

### Field-by-Field Comparison

#### Meta (MediaPlan Metadata)

| Change Type | Field Name | Description |
|-------------|------------|-------------|
| **NEW** | `dim_custom1-5` | Custom dimension fields at meta level |
| **NEW** | `custom_properties` | Extensibility object for custom metadata |

#### Campaign

| Change Type | v2.0 Field | v3.0 Field | Description |
|-------------|------------|------------|-------------|
| **REMOVED** | `audience_name` | - | Replaced by `target_audiences` array |
| **REMOVED** | `audience_age_start` | - | Replaced by `target_audiences` array |
| **REMOVED** | `audience_age_end` | - | Replaced by `target_audiences` array |
| **REMOVED** | `audience_gender` | - | Replaced by `target_audiences` array |
| **REMOVED** | `audience_interests` | - | Replaced by `target_audiences` array |
| **NEW** | - | `target_audiences` | Array of TargetAudience objects |
| **REMOVED** | `location_type` | - | Replaced by `target_locations` array |
| **REMOVED** | `locations` | - | Replaced by `target_locations` array |
| **NEW** | - | `target_locations` | Array of TargetLocation objects |
| **NEW** | - | `kpi_name1-5` | Campaign KPI tracking |
| **NEW** | - | `kpi_value1-5` | Campaign KPI values |
| **NEW** | - | `dim_custom1-5` | Custom dimensions at campaign level |
| **NEW** | - | `custom_properties` | Campaign-level extensibility |

#### LineItem

| Change Type | Field Name | Description |
|-------------|------------|-------------|
| **NEW** | `buy_type` | Type of buy (Direct, Programmatic, etc.) |
| **NEW** | `buy_commitment` | Commitment level |
| **NEW** | `aggregation_level` | Aggregation level indicator |
| **NEW** | `cost_currency_exchange_rate` | Multi-currency support |
| **NEW** | `cost_minimum` | Budget floor constraint |
| **NEW** | `cost_maximum` | Budget ceiling constraint |
| **NEW** | `metric_view_starts` | Video view starts |
| **NEW** | `metric_view_completions` | Video completions |
| **NEW** | `metric_reach` | Unique reach |
| **NEW** | `metric_units` | Generic unit metric |
| **NEW** | `metric_impression_share` | Share of impressions |
| **NEW** | `metric_page_views` | Page view count |
| **NEW** | `metric_likes` | Social likes |
| **NEW** | `metric_shares` | Social shares |
| **NEW** | `metric_comments` | Social comments |
| **NEW** | `metric_conversions` | Conversion events |
| **NEW** | `metric_formulas` | Formula configuration object |
| **NEW** | `custom_properties` | LineItem-level extensibility |

#### Dictionary

| Change Type | v2.0 Field | v3.0 Field | Description |
|-------------|------------|------------|-------------|
| **RENAMED** | `custom_dimensions` | `lineitem_custom_dimensions` | Clarified scope |
| **NEW** | - | `meta_custom_dimensions` | Meta-level dimension config |
| **NEW** | - | `campaign_custom_dimensions` | Campaign-level dimension config |
| **NEW** | - | `standard_metrics` | Formula support for standard metrics |

### New Object Structures

#### TargetAudience

```json
{
  "name": "Adults 25-34",
  "description": "Core target demographic",
  "demo_age_start": 25,
  "demo_age_end": 34,
  "demo_gender": "Any",
  "demo_attributes": "Homeowners, College Educated",
  "interest_attributes": "Technology, Travel",
  "intent_attributes": "In-market for electronics",
  "purchase_attributes": "Recent tech purchasers",
  "content_attributes": "News, Entertainment",
  "exclusion_list": "Competitors employees",
  "extension_approach": "Similar audiences",
  "population_size": 5000000
}
```

#### TargetLocation

```json
{
  "name": "Major US Markets",
  "description": "Top 10 DMAs",
  "location_type": "DMA",
  "location_list": ["New York", "Los Angeles", "Chicago"],
  "exclusion_type": "State",
  "exclusion_list": ["Alaska", "Hawaii"],
  "population_percent": 0.35
}
```

#### MetricFormula

```json
{
  "formula_type": "power_function",
  "base_metric": "metric_impressions",
  "coefficient": 0.15,
  "parameter1": 0.8,
  "parameter2": null,
  "parameter3": null,
  "comments": "Reach calculation based on impressions"
}
```

---

## 4. Workspace Upgrade

### Upgrade Process

The workspace upgrade is a **one-way process** that:
1. Creates automatic backups
2. Migrates all JSON files from v2.0 → v3.0
3. Regenerates Parquet files
4. Upgrades database schema (if enabled)
5. Updates workspace settings

### Step-by-Step Instructions

**Step 1**: Dry-Run Mode (Recommended)

```python
from mediaplanpy.workspace import WorkspaceManager

# Load v2.0 workspace (will fail in v3.0)
# This demonstrates the version enforcement
try:
    workspace = WorkspaceManager(settings_file_name="workspace_settings.json")
except WorkspaceError as e:
    print(f"Expected error: {e}")
    # Output: "Workspace schema version 2.0 is not compatible with SDK v3.0"
```

**Step 2**: Run Upgrade with Dry-Run

```python
from mediaplanpy.workspace.upgrader import WorkspaceUpgrader

upgrader = WorkspaceUpgrader(
    settings_file_name="workspace_settings.json"
)

# Preview changes without making them
result = upgrader.upgrade(dry_run=True)

print(f"Files to upgrade: {result['files_to_upgrade']}")
print(f"Estimated time: {result['estimated_time']}")
print(f"Warnings: {result['warnings']}")
```

**Step 3**: Execute Upgrade

```python
# Perform actual upgrade (creates automatic backups)
result = upgrader.upgrade(dry_run=False, skip_backup=False)

if result['success']:
    print(f"✅ Upgrade complete!")
    print(f"  - Files upgraded: {result['files_upgraded']}")
    print(f"  - Database migrated: {result['database_migrated']}")
    print(f"  - Backup location: {result['backup_location']}")
else:
    print(f"❌ Upgrade failed: {result['error']}")
    print(f"  - Restore from: {result['backup_location']}")
```

**Step 4**: Verify Workspace

```python
# Load upgraded workspace
workspace = WorkspaceManager(settings_file_name="workspace_settings.json")

# Verify version
print(f"Workspace version: {workspace.schema_version}")  # Should be 3.0

# Test query
campaigns = workspace.list_campaigns()
print(f"Found {len(campaigns)} campaigns")
```

### Automatic Backup Details

**JSON Files Backup**:
- Location: `{workspace_path}/mediaplans_backup_{timestamp}/`
- Contents: All files from `mediaplans/` directory
- Format: Exact copy of v2.0 JSON files

**Database Backup**:
- Table name: `{original_table}_backup_{timestamp}`
- Contents: Complete copy of all rows
- Note: Backup table is not automatically deleted

### Troubleshooting Upgrade Issues

**Issue**: Upgrade fails mid-process

**Solution**:
1. Check `upgrade_in_progress` flag in workspace settings
2. Review error logs
3. Restore from automatic backup if needed
4. Re-run upgrade after fixing issues

**Issue**: Shared database with multiple workspaces

**Solution**:
- Upgrade detects existing v3.0 schema automatically
- Only first workspace performs ALTER TABLE
- Subsequent workspaces skip schema migration
- All workspaces upgrade their JSON files independently

---

## 5. Code Migration

### MediaPlan.create() Changes

**v2.0 Code** (❌ No longer works):

```python
from mediaplanpy import MediaPlan

plan = MediaPlan.create(
    name="Summer Campaign",
    audience_name="Adults 25-34",
    audience_age_start=25,
    audience_age_end=34,
    audience_gender="Any",
    location_type="Country",
    locations=["United States"]
)
```

**v3.0 Code** (✅ Correct):

```python
from mediaplanpy import MediaPlan

plan = MediaPlan.create(
    name="Summer Campaign",
    target_audiences=[{
        "name": "Adults 25-34",
        "demo_age_start": 25,
        "demo_age_end": 34,
        "demo_gender": "Any"
    }],
    target_locations=[{
        "name": "United States",
        "location_type": "Country",
        "location_list": ["United States"]
    }]
)
```

### MediaPlan.create_lineitem() Updates

**New optional parameters** in v3.0:

```python
lineitem = plan.create_lineitem(
    name="Display Campaign",
    start_date="2025-01-01",
    end_date="2025-03-31",
    cost_total=50000,

    # NEW v3.0 parameters
    buy_type="Programmatic",
    buy_commitment="Non-guaranteed",
    cost_minimum=45000,
    cost_maximum=55000,

    # NEW metrics
    metric_view_completions=1500000,
    metric_reach=2000000,
    metric_conversions=15000,

    # NEW formula support
    metric_formulas={
        "metric_leads": {
            "formula_type": "conversion_rate",
            "base_metric": "metric_clicks",
            "coefficient": 0.05
        }
    },

    # NEW custom properties
    custom_properties={
        "campaign_manager": "John Doe",
        "approval_date": "2024-12-15"
    }
)
```

### Query Method Changes

**v2.0 Code**:

```python
campaigns = workspace.list_campaigns(
    filters={"audience_name": "Adults 25-34"}
)
```

**v3.0 Code** (backward compatible, but new fields available):

```python
campaigns = workspace.list_campaigns()

# New columns in result:
# - target_audiences_count
# - target_locations_count
# - kpi_name1-5, kpi_value1-5
# - dim_custom1-5

for campaign in campaigns:
    print(f"Campaign: {campaign['name']}")
    print(f"  Audiences: {campaign['target_audiences_count']}")
    print(f"  Locations: {campaign['target_locations_count']}")
```

---

## 6. Excel File Changes

### Worksheet Structure Changes

**v2.0 Structure**:
- Metadata
- Campaigns (with audience/location columns)
- LineItems
- Dictionary
- Documentation

**v3.0 Structure** (⚠️ Breaking Change):
- Metadata
- Campaigns (**audience/location columns removed**)
- **Target Audiences** (NEW worksheet)
- **Target Locations** (NEW worksheet)
- LineItems (with new columns)
- Dictionary (renamed sections)
- Documentation

### Campaign Worksheet Changes

**Removed Columns**:
- `audience_name`
- `audience_age_start`
- `audience_age_end`
- `audience_gender`
- `audience_interests`
- `location_type`
- `locations`

**Added Columns**:
- `kpi_name1` through `kpi_name5`
- `kpi_value1` through `kpi_value5`
- `dim_custom1` through `dim_custom5`
- `custom_properties`

### New Worksheets

#### Target Audiences Worksheet

| Column | Description |
|--------|-------------|
| campaign_id | Links to campaign |
| audience_sequence | Ordering (1, 2, 3...) |
| name | Audience name (required) |
| description | Audience description |
| demo_age_start | Age range start |
| demo_age_end | Age range end |
| demo_gender | Gender (Male/Female/Any) |
| ... | 8 more attribute columns |

#### Target Locations Worksheet

| Column | Description |
|--------|-------------|
| campaign_id | Links to campaign |
| location_sequence | Ordering (1, 2, 3...) |
| name | Location name (required) |
| location_type | Type (Country/State/DMA/etc.) |
| location_list | Comma-separated locations |
| ... | 4 more columns |

### Handling Existing Excel Files

**Option 1**: Import v2.0 Excel → Automatic Migration

```python
from mediaplanpy import MediaPlan

# Import v2.0 Excel file
plan = MediaPlan.import_from_excel("campaign_v2.xlsx")

# SDK automatically migrates to v3.0
print(f"Schema version: {plan.meta.schema_version}")  # "3.0"

# Export as v3.0 Excel
plan.export_to_excel("campaign_v3.xlsx")
```

**Option 2**: Manual Excel Update

1. Open v2.0 Excel file
2. Create "Target Audiences" worksheet
3. Move audience data from Campaign sheet
4. Create "Target Locations" worksheet
5. Move location data from Campaign sheet
6. Update Dictionary worksheet section names

---

## 7. Database Migration

### Automatic ALTER TABLE Process

The database migration automatically:
1. Detects existing table schema version
2. Adds v3.0 columns if missing
3. Preserves all existing data
4. Handles idempotent operations

**Migration happens automatically** during workspace upgrade or first save:

```python
from mediaplanpy import MediaPlan, WorkspaceManager

workspace = WorkspaceManager(settings_file_name="workspace_settings.json")

# Load v3.0 media plan
plan = MediaPlan.load(workspace, "plan_id")

# First save triggers database migration
plan.save(workspace)  # ALTER TABLE executed automatically
```

### Verification

**Check column addition**:

```sql
-- Connect to your PostgreSQL database
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'mediaplans'
  AND column_name LIKE '%kpi%'
ORDER BY column_name;

-- Should show: kpi_name1-5, kpi_value1-5
```

### Rollback Instructions

If you need to rollback:

```sql
-- Restore from backup table
DROP TABLE IF EXISTS mediaplans;
ALTER TABLE mediaplans_backup_20251210_143022 RENAME TO mediaplans;

-- Or restore from SQL dump
psql -h localhost -U user -d database < mediaplan_backup_v2.sql
```

### Shared Database Considerations

When multiple workspaces share a database:
- **First workspace** performs ALTER TABLE
- **Subsequent workspaces** detect v3.0 schema and skip migration
- **No conflicts** between workspaces
- Each workspace upgrades its own JSON files independently

---

## 8. Testing After Migration

### Validation Checklist

✅ **Step 1**: Verify Version

```python
import mediaplanpy
print(f"SDK Version: {mediaplanpy.__version__}")  # Should be 3.0.0

from mediaplanpy import WorkspaceManager
workspace = WorkspaceManager(settings_file_name="workspace_settings.json")
print(f"Workspace Version: {workspace.schema_version}")  # Should be 3.0
```

✅ **Step 2**: Load Media Plans

```python
# List all plans
plans = workspace.list_mediaplans()
print(f"Found {len(plans)} media plans")

# Load specific plan
plan = MediaPlan.load(workspace, plans[0]['id'])
print(f"Schema: {plan.meta.schema_version}")  # Should be 3.0
```

✅ **Step 3**: Verify Data Integrity

```python
# Check campaign audiences
for campaign in plan.campaigns:
    print(f"Campaign: {campaign.name}")
    print(f"  Audiences: {len(campaign.target_audiences)}")
    print(f"  Locations: {len(campaign.target_locations)}")

# Check lineitem metrics
for item in plan.lineitems:
    if item.metric_formulas:
        print(f"LineItem {item.name} has {len(item.metric_formulas)} formulas")
```

✅ **Step 4**: Test Queries

```python
# Query campaigns
campaigns = workspace.list_campaigns()
assert 'target_audiences_count' in campaigns[0]
assert 'kpi_name1' in campaigns[0]

# Query lineitems
items = workspace.list_lineitems()
print(f"Found {len(items)} line items")
```

✅ **Step 5**: Test Excel Export

```python
plan.export_to_excel("test_v3_export.xlsx")

# Verify worksheets exist
import openpyxl
wb = openpyxl.load_workbook("test_v3_export.xlsx")
assert "Target Audiences" in wb.sheetnames
assert "Target Locations" in wb.sheetnames
```

### Common Issues and Solutions

**Issue**: "Workspace schema version 2.0 is not compatible"

**Solution**: Run workspace upgrade (see Section 4)

**Issue**: Missing columns in database queries

**Solution**: Database migration may not have run. Save a plan to trigger it:
```python
plan.save(workspace)  # Triggers ALTER TABLE
```

**Issue**: Excel import fails with v2.0 file

**Solution**: SDK automatically migrates v2.0 Excel on import. If issues persist, manually create v3.0 structure.

---

## 9. FAQs

### Can I downgrade back to v2.0?

**No**, the migration is one-way. However:
- Automatic backups are created during upgrade
- You can restore from backups if needed
- We recommend testing in a non-production environment first

### What happens to my v2.0 data?

All v2.0 data is preserved and migrated:
- **Audience fields**: Converted to `target_audiences` array with single audience
- **Location fields**: Converted to `target_locations` array with single location
- **All other data**: Preserved exactly as-is
- **New fields**: Default to null/empty

### Do I need to update my code?

**Yes**, if you use:
- `MediaPlan.create()` with audience/location parameters (BREAKING)
- Direct access to `campaign.audience_name` (DEPRECATED, use `campaign.target_audiences`)
- Excel import/export (structure changed)

**No**, if you only:
- Load and query existing plans
- Use storage backends (automatic migration)

### How long does migration take?

- **Workspace upgrade**: 5-30 seconds per 100 media plans
- **Database migration**: 10-60 seconds (depending on row count)
- **Excel conversion**: Instant (happens on import)

### Can I migrate gradually?

**No**, the SDK enforces version compatibility:
- v3.0 SDK only loads v3.0 workspaces
- v2.0 SDK only loads v2.0 workspaces
- No mixed-version support

**Recommendation**: Test migration in dev environment first, then upgrade production in a single maintenance window.

### What if I have custom code that reads media plans?

Update your code to handle:
- `campaign.target_audiences` (array) instead of `campaign.audience_name` (string)
- `campaign.target_locations` (array) instead of `campaign.locations` (array of strings)
- `dictionary.lineitem_custom_dimensions` instead of `dictionary.custom_dimensions`

### Are there any performance impacts?

**Improvements in v3.0**:
- Database migrations use efficient ALTER TABLE
- Parquet generation is optimized
- Query performance unchanged

**No negative impacts** expected for typical workloads.

### How do I get help?

- **Documentation**: See SDK_REFERENCE.md for API details
- **Issues**: https://github.com/planmatic/mediaplanpy/issues
- **Discussions**: https://github.com/planmatic/mediaplanpy/discussions

---

## Summary

**Migration Steps Overview**:
1. ✅ Backup everything
2. ✅ Install v3.0 SDK
3. ✅ Run workspace upgrade (dry-run first)
4. ✅ Update code for breaking changes
5. ✅ Test thoroughly
6. ✅ Deploy to production

**Key Takeaways**:
- Migration is **one-way** (v2.0 → v3.0)
- **Automatic backups** are created
- **Data is preserved** and automatically migrated
- **Excel structure changed** (new worksheets)
- **Code updates required** for create() methods

For additional support, consult the [SDK Reference](../SDK_REFERENCE.md) or open a GitHub issue.

---

*Last Updated: 2025-12-10*
*SDK Version: 3.0.0*
