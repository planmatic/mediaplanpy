# MediaPlanPy CLI Interface - Examples

This guide demonstrates how to use the MediaPlanPy command-line interface (CLI) for workspace management and inspection tasks.

## Overview

The MediaPlanPy CLI provides administrative and inspection commands for managing workspaces. It is **not** designed for creating or editing media plans - use the Python API for operational tasks.

**CLI Philosophy:**
- **Administrative**: Workspace setup, configuration, and maintenance
- **Inspection**: Query and validate workspace contents
- **Developer-friendly**: Debugging and verification tools

## Prerequisites

- **MediaPlanPy SDK v3.0.0+** installed

## Global Commands

### Check SDK Version

```bash
mediaplanpy --version
```

**Output:**
```
mediaplanpy 3.0.0 (schema v3.0)
```

### Get Help

```bash
mediaplanpy --help
```

Shows all available commands with brief descriptions.

---

## Workspace Management Commands

### 1. Create Workspace

Create a new workspace configuration with v3.0 defaults.

**Basic Usage (Local Storage):**
```bash
mediaplanpy workspace create --name "My Workspace"
```

**Output:**
```
Created workspace 'My Workspace' with ID 'ws_abc123'
Settings file: /path/to/workspace.json
Schema version: v3.0
Storage mode: local
Storage path: /path/to/mediaplans

Next steps:
   - Review settings: mediaplanpy workspace settings --workspace_id ws_abc123
   - Start using Python API to create media plans
```

**Create with S3 Storage:**
```bash
mediaplanpy workspace create --name "Production Workspace" --storage s3
```

**Output:**
```
Created workspace 'Production Workspace' with ID 'ws_xyz789'
Settings file: /path/to/workspace.json
Schema version: v3.0
Storage mode: s3

IMPORTANT: Please edit the workspace settings file to configure S3:
   File: /path/to/workspace.json
   Update: storage.s3.bucket (currently: 'YOUR-BUCKET-NAME')
   Update: storage.s3.region (currently: 'us-east-1')

Next steps:
   - Edit workspace settings file with your S3 bucket details
   - Validate: mediaplanpy workspace validate --workspace_id ws_xyz789
```

**Create with Database:**
```bash
mediaplanpy workspace create --name "DB Workspace" --database true
```

**Options:**
- `--path <path>`: Path to create workspace.json (default: ./workspace.json)
- `--name <name>`: Workspace name (default: "Workspace created YYYYMMDD")
- `--storage <mode>`: Storage mode: local or s3 (default: local)
- `--database <bool>`: Enable database: true or false (default: false)
- `--force`: Overwrite existing workspace.json if present

---

### 2. Show Workspace Settings

Display complete workspace configuration.

```bash
mediaplanpy workspace settings --workspace_id ws_abc123
```

**Output:**
```
Workspace Settings

Basic Information:
   Name: My Workspace
   ID: ws_abc123
   Environment: production
   Schema version: v3.0
   Settings file: /path/to/workspace.json

Storage Configuration:
   Mode: local
   Base path: /path/to/mediaplans
   Formats: json, parquet
   Create if missing: true

Database Configuration:
   Enabled: No

SDK Compatibility:
   Current SDK: v3.0.0
   Required SDK: v3.0.x
   Status: Compatible

Workspace Settings:
   Last upgraded: 2024-12-10
   SDK version required: 3.0.x
```

---

### 3. Validate Workspace

Run comprehensive validation checks on workspace configuration and connectivity.

```bash
mediaplanpy workspace validate --workspace_id ws_abc123
```

**Output:**
```
Workspace Validation Report

Workspace: My Workspace (ws_abc123)

[1/7] Workspace settings file: ✅ PASS
   Location: /path/to/workspace.json

[2/7] Settings file format: ✅ PASS
   Valid JSON

[3/7] Settings file schema: ✅ PASS
   Valid workspace configuration

[4/7] SDK compatibility: ✅ PASS
   Workspace schema v3.0 compatible with SDK v3.0.0

[5/7] Storage access: ✅ PASS
   Local storage folder accessible: /path/to/mediaplans

[6/7] Database connection: ✅ PASS
   Database not enabled (skipped)

[7/7] Overall status: ✅ PASS

Workspace is valid and ready to use.
```

**Use Case:**
- Verify workspace configuration after setup
- Troubleshoot connection issues with S3 or database
- Confirm SDK compatibility before operations

---

### 4. Upgrade Workspace

Upgrade workspace from v2.0 to v3.0 schema.

**Preview Upgrade (Dry Run - Default):**
```bash
mediaplanpy workspace upgrade --workspace_id ws_abc123
```

**Output:**
```
Workspace Upgrade Preview (Dry Run)

Workspace: My Workspace (ws_abc123)

Current State:
   Schema version: v2.0
   JSON files: 45
   Parquet files: 45

Planned Changes:
   Target schema: v3.0

   Files to migrate: 45
   - Audience fields will become target_audiences array
   - Location fields will become target_locations array
   - Dictionary field will be renamed

   Backups to create:
   - JSON backup: /backups/json_20241210_143022/
   - Parquet backup: /backups/parquet_20241210_143022/

This is a dry run. No changes made.
To perform actual upgrade: add --execute flag
```

**Execute Upgrade:**
```bash
mediaplanpy workspace upgrade --workspace_id ws_abc123 --execute
```

**Output:**
```
Upgrading Workspace to v3.0

Workspace: My Workspace (ws_abc123)

Step 1/5: Creating backups...
   JSON files backed up (45 files)
   Parquet files backed up (45 files)
   Backup location: /backups/backup_20241210_143022/

Step 2/5: Migrating JSON files...
   Migrated 45 files (v2.0 to v3.0)

Step 3/5: Regenerating Parquet files...
   Regenerated 45 files with v3.0 schema

Step 4/5: Upgrading database schema...
   Database not enabled or already upgraded

Step 5/5: Updating workspace settings...
   Workspace settings updated to v3.0

Upgrade Complete

Summary:
   Files migrated: 45
   Parquet regenerated: 45
   Database upgraded: No
   Schema version: v3.0

Backups saved to: /backups/backup_20241210_143022/
Workspace is now compatible with SDK v3.0.0
```

**Options:**
- `--execute`: Execute the upgrade (default is dry-run for safety)

**Important:**
- Default behavior is dry-run (preview only)
- Backups are always created before upgrade
- Migration handles v2.0 → v3.0 transformations automatically

---

### 5. Workspace Statistics

Display workspace statistics and storage information.

```bash
mediaplanpy workspace statistics --workspace_id ws_abc123
```

**Output:**
```
Workspace Statistics

Workspace: My Workspace (ws_abc123)
Schema version: v3.0

Content Summary:
   Media plans: 45
   Campaigns: 32
   Line items: 1,247

Storage:
   JSON files: 45 files (12.3 MB)
   Parquet files: 45 files (8.7 MB)
   Total size: 21.0 MB

Database:
   Enabled: No

Last Activity:
   Last modified: 2024-12-09 15:42:33

Schema:
   Version: v3.0
   Upgrade available: No
```

---

### 6. Schema Version Information

Display comprehensive schema version details for workspace.

```bash
mediaplanpy workspace version --workspace_id ws_abc123
```

**Output:**
```
Schema Version Information

Workspace: My Workspace (ws_abc123)

SDK Information:
   SDK version: 3.0.0
   Current schema: v3.0
   Supported schemas: v2.0 (deprecated), v3.0 (current)

Workspace Configuration:
   Workspace schema version: v3.0
   Last upgraded: 2024-12-09
   SDK version required: 3.0.x
   Status: Compatible

JSON Files:
   Total files: 45

   By schema version:
   v3.0: 45 files (100%)

   Status: ✅ All files current

Database Schema:
   Enabled: No

Overall Status: ✅ Workspace fully upgraded to v3.0

Documentation: https://github.com/media-plan-schema/mediaplanschema/tree/main/schemas/3.0/documentation
```

**Use Case:**
- Verify all files have been migrated to v3.0
- Check for mixed version scenarios
- Confirm database schema version

---

## Inspection Commands

### 7. List Campaigns

List all campaigns in workspace with summary information.

**Table Format (Default):**
```bash
mediaplanpy list campaigns --workspace_id ws_abc123
```

**Output:**
```
Campaigns in workspace 'My Workspace'

Campaign ID  Campaign Name          Budget       Currency  Start Date  End Date    # Plans
──────────────────────────────────────────────────────────────────────────────────────────
camp_001     Summer Launch 2024     $500,000     USD       2024-06-01  2024-08-31  3
camp_002     Holiday Campaign       $1,200,000   USD       2024-11-15  2024-12-31  1
camp_003     Q1 Brand Awareness     $350,000     USD       2024-01-01  2024-03-31  2

Total: 3 campaigns
```

**JSON Format:**
```bash
mediaplanpy list campaigns --workspace_id ws_abc123 --format json
```

**Output:**
```json
{
  "workspace_id": "ws_abc123",
  "workspace_name": "My Workspace",
  "total_count": 3,
  "returned_count": 3,
  "limit": 100,
  "offset": 0,
  "campaigns": [
    {
      "campaign_id": "camp_001",
      "campaign_name": "Summer Launch 2024",
      "budget_total": 500000,
      "budget_currency": "USD",
      "start_date": "2024-06-01",
      "end_date": "2024-08-31",
      "mediaplan_count": 3
    }
  ]
}
```

**Options:**
- `--format <format>`: Output format: table or json (default: table)
- `--limit <n>`: Limit results to n rows (default: 100)
- `--offset <n>`: Skip first n rows (default: 0)

**Use Case:**
- Get overview of all campaigns in workspace
- Export campaign list for reporting (use --format json)
- Pagination for large workspaces

---

### 8. List Media Plans

List all media plans in workspace with filtering options.

**All Media Plans:**
```bash
mediaplanpy list mediaplans --workspace_id ws_abc123
```

**Output:**
```
Media Plans in workspace 'My Workspace'

Media Plan ID        Created By        Created At           Campaign Name          Schema Version  # Line Items
──────────────────────────────────────────────────────────────────────────────────────────────────────────────
mp_001               John Smith        2024-12-01 09:15:33  Summer Launch 2024     v3.0            45
mp_002               Jane Doe          2024-12-05 14:22:18  Holiday Campaign       v3.0            67
mp_003               John Smith        2024-12-08 11:04:55  Q1 Brand Awareness     v3.0            28

Total: 3 media plans
```

**Filter by Campaign:**
```bash
mediaplanpy list mediaplans --workspace_id ws_abc123 --campaign_id camp_001
```

**Output:**
```
Media Plans in workspace 'My Workspace' (Campaign: camp_001)

Media Plan ID        Created By        Created At           Campaign Name          Schema Version  # Line Items
──────────────────────────────────────────────────────────────────────────────────────────────────────────────
mp_001               John Smith        2024-12-01 09:15:33  Summer Launch 2024     v3.0            45
mp_004               Jane Doe          2024-12-03 16:20:11  Summer Launch 2024     v3.0            52

Total: 2 media plans
```

**JSON Format:**
```bash
mediaplanpy list mediaplans --workspace_id ws_abc123 --format json
```

**Options:**
- `--campaign_id <id>`: Filter by campaign ID (optional)
- `--format <format>`: Output format: table or json (default: table)
- `--limit <n>`: Limit results to n rows (default: 100)
- `--offset <n>`: Skip first n rows (default: 0)

**Use Case:**
- View all media plans in workspace
- Filter plans by campaign
- Export media plan list for analysis

---

## Common Workflows

### Workflow 1: Setting Up New Project

```bash
# 1. Create workspace
mediaplanpy workspace create --name "My Project 2024"

# 2. Review settings
mediaplanpy workspace settings --workspace_id ws_abc123

# 3. Validate configuration
mediaplanpy workspace validate --workspace_id ws_abc123

# 4. Use Python API to create media plans
# (See examples_03_create_mediaplan.py)
```

### Workflow 2: Upgrading Existing Workspace

```bash
# 1. Check current version
mediaplanpy workspace version --workspace_id ws_abc123

# 2. Preview upgrade (dry-run)
mediaplanpy workspace upgrade --workspace_id ws_abc123

# 3. Perform upgrade
mediaplanpy workspace upgrade --workspace_id ws_abc123 --execute

# 4. Verify upgrade
mediaplanpy workspace version --workspace_id ws_abc123
mediaplanpy workspace statistics --workspace_id ws_abc123
```

### Workflow 3: Debugging/Inspection

```bash
# 1. Check workspace status
mediaplanpy workspace settings --workspace_id ws_abc123

# 2. Validate configuration
mediaplanpy workspace validate --workspace_id ws_abc123

# 3. View campaigns
mediaplanpy list campaigns --workspace_id ws_abc123

# 4. View media plans
mediaplanpy list mediaplans --workspace_id ws_abc123

# 5. Export data for analysis
mediaplanpy list campaigns --workspace_id ws_abc123 --format json > campaigns.json
```

### Workflow 4: S3 Storage Setup

```bash
# 1. Create workspace with S3
mediaplanpy workspace create --name "S3 Workspace" --storage s3

# 2. Edit workspace.json to add S3 bucket details
# (Manual step - update storage.s3.bucket and storage.s3.region)

# 3. Validate S3 connectivity
mediaplanpy workspace validate --workspace_id ws_xyz789

# 4. Confirm settings
mediaplanpy workspace settings --workspace_id ws_xyz789
```

---

## Error Handling

### Common Errors and Solutions

**Error: Workspace not found**
```
Error: Workspace not found
   Could not find workspace settings file for workspace_id: ws_abc123

Suggestion:
   Create a new workspace: mediaplanpy workspace create
   Or verify workspace_id is correct
```

**Solution:**
- Verify the workspace_id is correct
- Check that workspace.json exists in the expected location
- Create a new workspace if needed

**Error: SDK compatibility**
```
[4/7] SDK compatibility: ❌ FAIL
   Workspace schema v2.0 incompatible with SDK v3.0.0
   Action required: Run workspace upgrade
```

**Solution:**
```bash
mediaplanpy workspace upgrade --workspace_id ws_abc123 --execute
```

**Error: Storage access**
```
[5/7] Storage access: ❌ FAIL
   S3 bucket not configured (currently: 'YOUR-BUCKET-NAME')
   Action required: Edit workspace settings file
```

**Solution:**
- Edit workspace.json
- Update storage.s3.bucket with your actual bucket name
- Validate again: `mediaplanpy workspace validate --workspace_id ws_abc123`

---

## Tips and Best Practices

### 1. Always Validate After Setup
```bash
# After creating or modifying workspace
mediaplanpy workspace validate --workspace_id ws_abc123
```

### 2. Use Dry-Run Before Upgrade
```bash
# Preview changes first
mediaplanpy workspace upgrade --workspace_id ws_abc123

# Then execute if everything looks good
mediaplanpy workspace upgrade --workspace_id ws_abc123 --execute
```

### 3. Export Data for Analysis
```bash
# Export campaigns and media plans as JSON
mediaplanpy list campaigns --workspace_id ws_abc123 --format json > campaigns.json
mediaplanpy list mediaplans --workspace_id ws_abc123 --format json > mediaplans.json
```

### 4. Monitor Workspace Health
```bash
# Regular health checks
mediaplanpy workspace statistics --workspace_id ws_abc123
mediaplanpy workspace version --workspace_id ws_abc123
```

### 5. Check Version Compatibility
```bash
# Before starting work
mediaplanpy --version
mediaplanpy workspace settings --workspace_id ws_abc123
```

---

## CLI vs Python API

**Use CLI for:**
- Workspace setup and configuration
- Validation and health checks
- Inspection and debugging
- Schema version management
- Querying workspace contents

**Use Python API for:**
- Creating media plans
- Editing media plans
- Managing line items
- Complex workflows and automation
- Integration with other tools

---

## Reference

### Complete Command List

```bash
# Global
mediaplanpy --version
mediaplanpy --help

# Workspace Management
mediaplanpy workspace create [OPTIONS]
mediaplanpy workspace settings --workspace_id <id>
mediaplanpy workspace validate --workspace_id <id>
mediaplanpy workspace upgrade --workspace_id <id> [--execute]
mediaplanpy workspace statistics --workspace_id <id>
mediaplanpy workspace version --workspace_id <id>

# Inspection
mediaplanpy list campaigns --workspace_id <id> [OPTIONS]
mediaplanpy list mediaplans --workspace_id <id> [OPTIONS]
```

### Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Workspace not found
- `4`: Version incompatibility
- `5`: Permission denied

---

## Next Steps

- **Create media plans**: See `examples_03_create_mediaplan.py`
- **Load and edit plans**: See `examples_04_load_mediaplan.py` and `examples_05_edit_mediaplan.py`
- **Manage line items**: See `examples_11_manage_lineitems.py`
- **Configure Dictionary**: See `examples_12_manage_dictionary.py`
- **SQL queries**: See `examples_09_sql_queries.py`

---

**Last Updated:** December 15, 2025 for MediaPlanPy v3.0.0
