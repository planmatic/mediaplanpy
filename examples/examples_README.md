# MediaPlanPy Examples - v3.0 SDK

Welcome to the MediaPlanPy v3.0 examples! These scripts demonstrate how to use the MediaPlanPy SDK for working with media plans following the Media Plan Open Data Standard v3.0.

## Prerequisites

- **Python 3.8+**
- **MediaPlanPy SDK v3.0.0 or higher**

For installation instructions, please refer to **GET_STARTED.md** in the root directory.

### Optional for Specific Examples
- **AWS credentials:** For S3 storage backend examples (examples_01_create_workspace.py)
- **PostgreSQL:** For database integration (optional - database features are transparent to SDK usage)

---

## Quick Start

Get started with MediaPlanPy in 3 simple steps:

### 1. Create a Workspace
```bash
python examples_01_create_workspace.py
```
Creates a workspace configuration for storing media plans.

### 2. Create Your First Media Plan
```bash
python examples_03_create_mediaplan.py
```
Demonstrates creating media plans from minimal to advanced with all v3.0 features.

### 3. Explore the Examples
Run any example file to learn specific functionality. Each file is independent and well-documented.

---

## Examples Overview

All examples are located in the `/examples` directory. Run them in any order based on your needs.

| # | File | Purpose | Key v3.0 Features |
|---|------|---------|-------------------|
| 1 | `examples_01_create_workspace.py` | Create workspace configurations | Workspace versioning, local & S3 storage, schema v3.0 enforcement |
| 2 | `examples_02_load_workspace.py` | Load workspaces three ways | Load by ID, by path, by dictionary; version validation |
| 3 | `examples_03_create_mediaplan.py` | Create media plans (minimal → advanced) | target_audiences, target_locations, metric_formulas, KPIs, custom dimensions, Dictionary |
| 4 | `examples_04_load_mediaplan.py` | Load and inspect media plans | Access nested arrays, MetricFormula objects, all v3.0 fields |
| 5 | `examples_05_edit_mediaplan.py` | Edit media plans, configure Dictionary | Proper LineItem CRUD, Dictionary config (scoped dimensions, formulas), version management |
| 6 | `examples_06_export_mediaplan.py` | Export to JSON and Excel | v3.0 structure serialization, arrays & nested objects |
| 7 | `examples_07_import_mediaplan.py` | Import from JSON and Excel | Automatic schema detection, object reconstruction, data integrity checks |
| 8 | `examples_08_list_objects.py` | Query workspace contents | List campaigns/plans/lineitems, DataFrame output, filters on v3.0 fields |
| 9 | `examples_09_sql_queries.py` | Run SQL queries on media plans | DuckDB queries, v3.0 columns, multi-dimensional analysis |
| 10 | `examples_10_manage_mediaplan.py` | Lifecycle management | Delete (with dry_run), archive, restore, version management, parent_id tracking |
| 11 | `examples_11_manage_lineitems.py` | Comprehensive LineItem CRUD operations | Load/create/edit/delete line items, dimensions, metrics, costs, formulas, custom_properties, bulk operations |
| 12 | `examples_12_manage_dictionary.py` | Configure Dictionary for custom fields | Scoped dimensions (meta/campaign/lineitem), custom metrics with formulas, custom costs, standard metric formulas |
| 13 | `examples_13_cli_interface.md` | CLI commands for workspace management | Workspace create/settings/validate/upgrade, list campaigns/plans, CLI inspection tools |
| 14 | `examples_14_api_client.py` | Interface with Planmatic API Server | API authentication, remote workspace operations, load/import media plans via API |
| 15 | `examples_15_formulas.py` | Formula management and auto-recalculation | Dynamic formula system, automatic recalculation, coefficient management, dependency chains |

---

## What's New in v3.0

MediaPlanPy v3.0 brings major enhancements to the Media Plan Open Data Standard with 40+ new fields and powerful new capabilities.

### Key Highlights

- **Target Audiences Arrays** - Rich audience segmentation with 13+ attributes per audience
- **Target Locations Arrays** - Geographic targeting with multiple location types
- **KPIs** - 5 campaign-level KPI name/value pairs for performance tracking
- **Custom Dimensions** - dim_custom1-5 at meta, campaign, and lineitem levels
- **Custom Properties** - Extensibility dictionaries at all levels
- **Metric Formulas** - Define calculated metrics with MetricFormula objects
- **Dictionary** - Configure captions and formulas for custom fields
- **Enhanced Metrics** - 10+ new metrics (reach, views, engagement)
- **Enhanced Costs** - cost_minimum, cost_maximum, exchange rates, custom1-10
- **Buy Information** - buy_type and buy_commitment fields

For a complete list of changes and detailed field descriptions, see **CHANGELOG_V2_TO_V3.md** in the docs/ directory.

### Example v3.0 Features in Code

```python
# Target audiences array
target_audiences = [
    {
        "name": "Adults 25-54",
        "demo_age_start": 25,
        "demo_age_end": 54,
        "interest_attributes": "Technology, Business"
    }
]

# Custom dimensions
campaign_dim_custom1 = "Vertical: Technology"

# Metric formulas
metric_formulas = {
    "cpm": {
        "formula_type": "cost_per_unit",
        "base_metric": "cost_total",
        "coefficient": 1000.0
    }
}
```

---

## Recent Enhancements (December 2025)

### NEW: examples_13_cli_interface.md
Comprehensive CLI documentation for administrative and inspection tasks:
- ✅ **Workspace Management** - create, settings, validate, upgrade, statistics, version
- ✅ **Inspection Commands** - list campaigns, list mediaplans with filtering
- ✅ **Common Workflows** - Setup, upgrade, debugging, S3 configuration
- ✅ **Error Handling** - Common errors and solutions
- ✅ **Concise Format** - Focused on practical usage with clear examples

### NEW: examples_14_api_client.py
Interface with Planmatic API Server for remote operations:
- ✅ **API Authentication** - Request API key, authenticate with session tokens
- ✅ **Remote Workspace** - Load workspace from API server
- ✅ **Load Media Plans** - Retrieve current plans from campaigns via API
- ✅ **Import/Upload Plans** - Upload media plans to API server
- ✅ **Complete Workflow** - End-to-end example with all steps
- ✅ **Error Handling** - Comprehensive error handling and security notes

### NEW: examples_15_formulas.py
Progressive demonstration of the v3.0 dynamic formula system:
- ✅ **Auto-Recalculation** - Change cost_total → dependent metrics recalculate automatically
- ✅ **Bidirectional Updates** - Edit values to update formulas, or edit formulas to update values
- ✅ **Coefficient Management** - System preserves relationships when base metrics change
- ✅ **Dependency Chains** - Configure cascading calculations (cost → impressions → clicks → conversions)
- ✅ **Default Formulas** - Works without dictionary (defaults to cost_per_unit/cost_total)
- ✅ **Progressive Workflow** - 5-step demonstration from simple to advanced
- ✅ **Production-Ready** - Real-world patterns for formula management

### NEW: examples_11_manage_lineitems.py
Comprehensive guide to LineItem management with 11 complete examples:
- ✅ **Proper CRUD Pattern** - load_lineitem() → edit → update_lineitem() → save()
- ✅ **Full Field Coverage** - dimensions, metrics, costs, formulas, custom_properties
- ✅ **Advanced Operations** - Copy line items, bulk editing, validation patterns
- ✅ **900+ lines** of production-ready code examples

### NEW: examples_12_manage_dictionary.py
Dedicated guide to Dictionary configuration with 6 comprehensive examples:
- ✅ **Scoped Dimensions** - Configure meta/campaign/lineitem custom dimensions separately
- ✅ **Custom Metrics with Formulas** - Enable metric_custom1-10 with formula support
- ✅ **Custom Costs** - Configure cost breakdown fields (cost_custom1-10)
- ✅ **Standard Metric Formulas** - Set formulas for metric_impressions, metric_clicks, etc.
- ✅ **Usage Examples** - Using custom fields in line items, querying enabled fields
- ✅ **800+ lines** of production-ready Dictionary examples

### ENHANCED: examples_05_edit_mediaplan.py
Streamlined for core editing patterns:
- ✅ **Proper LineItem CRUD** - Fixed to demonstrate correct load → edit → update pattern
- ✅ **Focused on Editing** - Basic properties, v3.0 arrays, KPIs, versioning
- ✅ **Simplified** - Dictionary examples moved to dedicated examples_12

### Dictionary Methods Enhanced
The SDK now includes full v3.0 Dictionary support:
- `set_custom_field_config()` - Now supports scope parameter and formula configuration
- `set_standard_metric_formula()` - Configure formulas for standard metrics (NEW)
- `get_standard_metric_formula()` - Query standard metric formulas (NEW)
- `remove_standard_metric_formula()` - Remove formula configurations (NEW)

**See:** `examples_12_manage_dictionary.py` for complete Dictionary usage examples.

---

## Running Examples

### In IDE (Recommended)

1. Open any example file in your Python IDE
2. Run the entire script or execute individual functions
3. Check console output for ✓ validation messages
4. View generated files in `examples/output/<example_name>/`

**Example - Running a single function:**
```python
# In examples_03_create_mediaplan.py
if __name__ == "__main__":
    # Run just the minimal example
    plan = create_minimal_hello_world_plan()
```

### From Command Line

```bash
# Navigate to the MediaPlanPy directory
cd /path/to/mediaplanpy

# Run any example
python examples/examples_01_create_workspace.py
python examples/examples_03_create_mediaplan.py
python examples/examples_08_list_objects.py

# Run with specific Python version
python3.10 examples/examples_03_create_mediaplan.py
```

### Expected Output

Each example prints:
- ✓ Success messages with validation
- Object IDs, names, and key properties
- File paths where outputs are saved
- Next steps guidance

**Example output:**
```
✓ Successfully created media plan
  - Media Plan ID: MP_2025_001
  - Campaign name: Q1 2025 Campaign
  - Budget: $500,000.00
  - Schema version: 3.0
  - Line items: 3
  - Saved to: /examples/output/mediaplan_examples/MP_2025_001.json
```

---

## Output Files

All examples write to the `examples/output/` directory with organized subdirectories:

```
examples/output/
├── workspace_examples/       # Workspace configs and storage
├── mediaplan_examples/        # Created media plans (JSON, Parquet)
├── export_examples/           # Exported JSON and Excel files
├── import_examples/           # Import test files
├── query_examples/            # Query result files
└── manage_examples/           # Management operation outputs
```

### File Formats

**JSON Files** - Human-readable, complete v3.0 structure:
```json
{
  "meta": { "id": "MP_001", "schema_version": "3.0", ... },
  "campaign": { "target_audiences": [...], "target_locations": [...], ... },
  "lineitems": [...]
}
```

**Parquet Files** - Columnar format for analytics (one row per line item):
- Optimized for queries and BI tools
- Includes all v3.0 columns flattened
- Supports SQL queries via DuckDB

**Excel Files** - Spreadsheet format with v3.0 columns:
- One sheet with flattened line item view
- All v3.0 fields as columns
- Editable and re-importable

---

## v3.0 vs v2.0 - Key Differences

These examples focus exclusively on v3.0. Here are the major differences from v2.0:

| Feature | v2.0 | v3.0 |
|---------|------|------|
| **Audiences** | Single object | Array of TargetAudience objects |
| **Locations** | Single object | Array of TargetLocation objects |
| **KPIs** | Not available | 5 KPI name/value pairs per campaign |
| **Custom Dimensions** | Not available | dim_custom1-5 at meta/campaign/lineitem |
| **Custom Properties** | Not available | Extensibility dicts at all levels |
| **Metric Formulas** | Not available | MetricFormula objects per line item |
| **Dictionary** | Not available | Configuration for custom fields & formulas |
| **Enhanced Metrics** | ~15 metrics | 25+ metrics including reach, views, engagement |
| **Buy Information** | Not available | buy_type, buy_commitment fields |
| **Cost Fields** | cost_total only | cost_minimum, cost_maximum, exchange_rate, custom1-10 |

### Migration Support

The SDK automatically migrates v2.0 media plans to v3.0 when loading:
- Single audience → target_audiences array (1 element)
- Single location → target_locations array (1 element)
- All existing fields preserved
- New fields available for editing

**Note:** These examples don't cover migration workflows. For migration guidance, see `docs/MIGRATION_V2_TO_V3.md`.

---

## Learning Path

### For Beginners - Start Here

1. **examples_01_create_workspace.py** - Understand workspace setup
2. **examples_03_create_mediaplan.py** - Focus on `create_minimal_hello_world_plan()`
3. **examples_04_load_mediaplan.py** - Learn to inspect media plans
4. **examples_06_export_mediaplan.py** - Export to JSON
5. **examples_08_list_objects.py** - Query your workspace

### For Advanced Users

1. **examples_03_create_mediaplan.py** - Run `create_advanced_plan_with_v3_features()`
2. **examples_05_edit_mediaplan.py** - Master version management and editing patterns
3. **examples_11_manage_lineitems.py** - Comprehensive LineItem management patterns
4. **examples_12_manage_dictionary.py** - Configure Dictionary for custom fields
5. **examples_15_formulas.py** - Master dynamic formulas and auto-recalculation
6. **examples_09_sql_queries.py** - Run complex analytics queries
7. **examples_10_manage_mediaplan.py** - Lifecycle management

### For Specific Use Cases

**Working with Formulas:**
- `examples_15_formulas.py` → Auto-recalculation, coefficient management, dependency chains
- `examples_12_manage_dictionary.py` → Configure formula definitions for metrics

**Working with Line Items:**
- `examples_11_manage_lineitems.py` → Complete CRUD operations, copy, bulk edit, validation patterns

**Working with Excel:**
- `examples_06_export_mediaplan.py` → `export_to_excel()`
- `examples_07_import_mediaplan.py` → `import_from_excel()`

**Configuring Custom Fields:**
- `examples_12_manage_dictionary.py` → Complete Dictionary configuration guide
- `examples_11_manage_lineitems.py` → Using custom dimensions, metrics, and costs

**S3 Integration:**
- `examples_01_create_workspace.py` → `create_custom_workspace_with_s3()`

**Advanced Queries:**
- `examples_09_sql_queries.py` → `complex_sql_query_with_aggregations()`

**Version Management:**
- `examples_05_edit_mediaplan.py` → `save_with_versioning_options()`
- `examples_10_manage_mediaplan.py` → `manage_plan_versions()`

**CLI Management:**
- `examples_13_cli_interface.md` → Complete CLI reference for workspace management and inspection

**API Server Integration:**
- `examples_14_api_client.py` → Authenticate, load workspace, load/import plans via Planmatic API

---

## Troubleshooting

### Common Issues

**Import Error: "No module named mediaplanpy"**
```bash
# Solution: Install the package
pip install mediaplanpy>=3.0.0

# Or install in development mode
pip install -e .
```

**Version Mismatch Error: "Workspace requires v3.0, found v2.0"**
```bash
# Solution: Workspace needs upgrading
# See docs/workspace_query.md for upgrade instructions
```

**Database Connection Errors**
```bash
# Database is optional - examples work without it
# If you want database features, install PostgreSQL:
pip install "mediaplanpy[database]>=3.0.0"
```

**Missing Dependencies for Excel/Parquet**
```bash
# Install specific extras
pip install "mediaplanpy[excel]>=3.0.0"
pip install "mediaplanpy[parquet]>=3.0.0"
```

### Getting Help

- **SDK Documentation:** See `SDK_REFERENCE.md` for complete API reference
- **Migration Guide:** See `docs/MIGRATION_V2_TO_V3.md` for v2.0 → v3.0 migration
- **Storage Guide:** See `docs/storage.md` for storage backend configuration
- **Workspace Guide:** See `docs/workspace_query.md` for workspace management

---

## Need Help?

- **GitHub Issues:** Report bugs or request features at the MediaPlanPy repository
- **Documentation:** Check the docs/ directory for detailed guides
- **Examples:** All examples include detailed docstrings and comments

---

## License

See LICENSE file for license information.

---

**Last Updated:** December 19, 2025 for MediaPlanPy v3.0.0 (includes examples_11-15: LineItems, Dictionary, CLI, API, and Formulas)
