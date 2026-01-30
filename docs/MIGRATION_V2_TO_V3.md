# MediaPlanPy Migration Guide: v2.0 → v3.0

This guide provides step-by-step instructions for upgrading MediaPlanPy SDK from v2.0.7 to v3.0.0 using CLI commands.

## Prerequisites

Before you begin, ensure you have:
- ✅ MediaPlanPy SDK v2.0.7 currently installed
- ✅ Python 3.8 or higher
- ✅ Full backup of all workspace data
- ✅ Testing environment available (recommended)

## What's Changing

MediaPlanPy v3.0 introduces **schema v3.0** with breaking changes. See the [Change Log](../CHANGE_LOG.md) for complete details.

**Key Breaking Changes:**
- Campaign audience/location fields → arrays (`target_audiences`, `target_locations`)
- Dictionary field renamed: `custom_dimensions` → `lineitem_custom_dimensions`
- Excel format updated with new worksheets
- v0.0 and v1.0 support removed

**For detailed schema changes**, refer to:
- [Schema CHANGELOG](../../mediaplanschema/schemas/3.0/documentation/CHANGELOG_V2_TO_V3.md) - Field-by-field comparison
- [Schema Migration Guide](../../mediaplanschema/schemas/3.0/documentation/MIGRATION_V2_TO_V3.md) - Document transformation rules

---

## Step 1: Install SDK v3.0.0

Upgrade from v2.0.7 to v3.0.0:

```bash
pip install --upgrade mediaplanpy
```

Verify installation:

```bash
python -c "import mediaplanpy; print(mediaplanpy.__version__)"
# Expected: 3.0.0
```

**Note**: After this upgrade, SDK v3.0.x will **not load** v2.0 workspaces. To continue working with v2.0 workspaces, keep using:
```bash
pip install mediaplanpy==2.0.7
```

---

## Step 2: Workspace Validation (Optional)

Before upgrading, validate your workspace to check compatibility:

```bash
mediaplanpy workspace validate --workspace_id <workspace_id>
```

This command checks:
- Workspace schema version
- SDK compatibility
- Storage access
- Database connection (if enabled)
- Media plan file integrity

---

## Step 3: Workspace Upgrade - Dry Run

**Always run dry-run first** to preview changes without modifying anything:

```bash
mediaplanpy workspace upgrade --workspace_id <workspace_id>
```

The dry-run output shows:
- Current workspace state (schema version, media plan count)
- Changes that will be made (files to upgrade, database tables)
- Estimated upgrade time
- Backup locations

**Review the preview carefully** before proceeding to execution.

---

## Step 4: Workspace Upgrade - Execute

Once you've reviewed the dry-run output, execute the upgrade:

```bash
mediaplanpy workspace upgrade --workspace_id <workspace_id> --execute
```

The upgrade process:
1. **Creates automatic backups**:
   - JSON files → `mediaplans_backup_{timestamp}/`
   - Database → `{table_name}_backup_{timestamp}`
2. **Migrates all media plan JSON files** (v2.0 → v3.0):
   - Converts audience/location fields to arrays
   - Renames dictionary keys
   - Updates schema version
3. **Regenerates Parquet files** for analytics
4. **Upgrades database schema** (if PostgreSQL enabled):
   - Adds new v3.0 columns
   - Preserves all existing data
5. **Updates workspace settings** to v3.0

**Upgrade is one-way** - you cannot downgrade after execution. Backups are your rollback mechanism.

---

## Step 5: Verify Upgrade

After upgrade completes, verify the workspace:

```bash
mediaplanpy workspace settings --workspace_id <workspace_id>
```

Check that:
- Workspace schema version shows `3.0`
- SDK version required shows `3.0.0`
- Last upgraded timestamp is recent

List media plans to confirm migration:

```bash
mediaplanpy list mediaplans --workspace_id <workspace_id>
```

All media plans should now be v3.0.

---

## Step 6: Update Your Code

If your code uses campaign creation or accesses audience/location fields, update it for v3.0 compatibility.

**Before (v2.0)**:
```python
plan = MediaPlan.create(
    audience_name="Adults 25-34",
    audience_age_start=25,
    audience_age_end=34,
    location_type="Country",
    locations=["United States"]
)
```

**After (v3.0)**:
```python
plan = MediaPlan.create(
    target_audiences=[{
        "name": "Adults 25-34",
        "demo_age_start": 25,
        "demo_age_end": 34
    }],
    target_locations=[{
        "name": "United States",
        "location_type": "Country",
        "location_list": ["United States"]
    }]
)
```

For complete v3.0 examples, see the [examples library](../examples/).

---

## Rollback Procedure

If you need to roll back after migration:

### 1. Restore JSON Files

```bash
# Navigate to workspace directory
cd /path/to/workspace

# Remove v3.0 files
rm -rf mediaplans/

# Restore from backup
cp -r mediaplans_backup_20260130_143022/ mediaplans/
```

### 2. Restore Database (if enabled)

```sql
-- Connect to PostgreSQL
psql -h localhost -U user -d database

-- Drop v3.0 table
DROP TABLE IF EXISTS media_plans;

-- Restore from backup
ALTER TABLE media_plans_backup_20260130_143022 RENAME TO media_plans;
```

### 3. Restore Workspace Settings

Edit workspace settings JSON file and change:
```json
{
  "workspace_settings": {
    "schema_version": "2.0",
    "sdk_version_required": "2.0.7"
  }
}
```

### 4. Reinstall SDK v2.0.7

```bash
pip install mediaplanpy==2.0.7
```

---

## Common Scenarios

### Multiple Workspaces

Upgrade each workspace independently:

```bash
# Workspace 1
mediaplanpy workspace upgrade --workspace_id workspace_prod --execute

# Workspace 2
mediaplanpy workspace upgrade --workspace_id workspace_stage --execute
```

### Shared Database

When multiple workspaces share a PostgreSQL database:
- **First workspace**: Performs ALTER TABLE to add v3.0 columns
- **Subsequent workspaces**: Detect v3.0 schema, skip ALTER TABLE
- Each workspace upgrades its own JSON files independently

### S3 Storage

The upgrade process works with all storage backends:
- Local filesystem
- Amazon S3
- PostgreSQL

The CLI automatically handles your configured storage backend.

---

## Troubleshooting

### Error: "Workspace schema version 2.0 is not compatible"

This is expected after installing v3.0 SDK. Run the upgrade command to migrate.

### Error: "Upgrade failed"

1. Check the error message details
2. Verify you have write access to workspace directory
3. If database-enabled, verify database credentials
4. Restore from backup if needed
5. Review logs for specific error

### Dry-run Shows Warnings

Review warnings carefully. Common warnings:
- Missing media plan files
- Malformed JSON
- Database connection issues

Address warnings before executing upgrade.

---

## Getting Help

- **Documentation**: [GET_STARTED.md](../GET_STARTED.md), [SDK_REFERENCE.md](../SDK_REFERENCE.md)
- **Examples**: [examples/](../examples/)
- **Schema Details**: [Schema CHANGELOG](../../mediaplanschema/schemas/3.0/documentation/CHANGELOG_V2_TO_V3.md)
- **Issues**: [GitHub Issues](https://github.com/planmatic/mediaplanpy/issues)
- **Support**: contact@planmatic.io

---

## Summary

**Migration Workflow**:
1. ✅ Backup everything
2. ✅ Install v3.0 SDK: `pip install --upgrade mediaplanpy`
3. ✅ Validate workspace (optional): `mediaplanpy workspace validate --workspace_id <id>`
4. ✅ Dry-run upgrade: `mediaplanpy workspace upgrade --workspace_id <id>`
5. ✅ Execute upgrade: `mediaplanpy workspace upgrade --workspace_id <id> --execute`
6. ✅ Verify: `mediaplanpy workspace settings --workspace_id <id>`
7. ✅ Update code for v3.0 API changes

**Remember**:
- Migration is one-way (v2.0 → v3.0)
- Always run dry-run first
- Automatic backups are created
- Use `mediaplanpy==2.0.7` to stay on v2.0

---

*Last Updated: 2026-01-30*
*SDK Version: 3.0.0*
