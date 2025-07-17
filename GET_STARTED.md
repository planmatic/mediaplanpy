# Get Started with Mediaplanpy

Welcome! This guide will walk you through how to start using **mediaplanpy** in your own projects.

## Package Installation

We support **two primary approaches**:

- Installing the package using `pip` (recommended for most users)
- Cloning the repository for local development or contributions

### Option 1: Install with `pip` (from GitHub)

This is the simplest way to get started using the package in your project without cloning the source code.

### Requirements

- Python 3.8+
- `pip` installed

### Installation

You can install the package directly from GitHub using:

```bash
pip install git+https://github.com/planmatic/mediaplanpy
```

This will install the latest version of the package and all its dependencies.

### Option 2: Clone the Repo for Local Development

This approach is useful if you’d like to:

- Explore the source code
- Contribute improvements
- Develop against the latest changes

### Steps

1. **Clone the repository**

```bash
git clone https://github.com/planmatic/mediaplanpy
cd mediaplanpy
```

2. **Create a virtual environment (optional but recommended)**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install in editable mode**

```bash
pip install -e .
```

This allows you to make changes to the code and use them immediately without reinstalling.

---

## Sample Workflow

Follow these steps to create and save a basic media plan using `mediaplanpy`.

### Step 1: Import the Package

```python
# Import Package
from mediaplanpy import WorkspaceManager, MediaPlan
```

This gives you access to the main classes needed to work with media plans.

### Step 2: Initialize the Workspace Manager

```python
# Initialize Workspace Manager
workspace = WorkspaceManager()
```

The `WorkspaceManager` handles all file organization and data persistence. It must be initialized before creating or editing media plans.

### Step 3: Create and Load a Workspace

```python
# Create and Load a Workspace
workspace_id, settings_file_path = workspace.create()
workspace.load(workspace_id=workspace_id)
print(f"Workspace ID: {workspace_id}")
print(f"Workspace Settings File Path: {settings_file_path}")
```

This creates a new workspace and loads it into memory. All subsequent operations (saving plans, importing data) will be tied to this workspace.

**Tip:** By default, the workspace is saved under `C:\mediaplanpy`. You can open the corresponding JSON file to inspect and modify workspace settings manually.

### Step 4: Create a Media Plan

```python
# Create a Media Plan
media_plan = MediaPlan.create(
    created_by="you@example.com",
    campaign_name="Summer 2025 Campaign",
    campaign_objective="Brand Awareness",
    campaign_start_date="2025-07-01",
    campaign_end_date="2025-09-30",
    campaign_budget=100000,
    agency_id="A1",
    agency_name="Example Agency",
    advertiser_id="ADV1",
    advertiser_name="Sample Advertiser",
    product_id="P1",
    product_name="Sample Product",
    campaign_type_id="C1",
    campaign_type_name="Awareness",
    audience_name="Adults 18-54",
    audience_age_start=18,
    audience_age_end=54,
    audience_gender="Any",
    audience_interests=["Tech Enthusiasts"],
    location_type="Country",
    locations=["USA"],
    workflow_status_id="1",
    workflow_status_name="Planning",
    media_plan_name="Test Plan",
    created_by_id="U123",
    created_by_name="Your Name",
    comments="Initial version of media plan",
    is_current=True,
    is_archived=False,
    workspace_manager=workspace
)
print(f"Media Plan Created: {media_plan.meta.id}")
```

This creates a media plan with required campaign and metadata fields.

### Step 5: Add Line Items

```python
# Add Line Items
lineitem = media_plan.create_lineitem({
    "name": "Search",
    "channel": "Search",
    "vehicle": "Google",
    "partner": "Google",
    "media_product": "Google Ads",
    "location_type": "Country",
    "location_name": "USA",
    "target_audience": "Adults 18-54",
    "adformat": "Text",
    "kpi": "Clicks",
    "cost_total": 5000,
    "cost_currency": "USD"
})
print(f"Line Item Created: {lineitem.id}")
```

You can add as many line items as needed with different channels, costs, and configurations.

### Step 6: Save the Media Plan

```python
# Save the Media Plan
saved_path = media_plan.save(workspace)
print(f"Media plan saved to: {saved_path}")
```

This will persist your media plan to the workspace.

**Tip:** This operation generates both a `.json` file for the plan definition and a companion `.parquet` file which is used for analytics and SQL queries. You can inspect these files in the `mediaplans` subdirectory of your workspace.

### Step 7: Run SQL Query to Get Total Spend

```python
# Run SQL query for total spend
query = "SELECT SUM(lineitem_cost_total) AS total_spend FROM {*}"
result = workspace.sql_query(query)
print(result)
```

This uses DuckDB to aggregate total media spend across all saved plans.

### Step 8: List All Saved Media Plans

```python
# List saved media plans
plans = workspace.list_mediaplans()
for plan in plans:
    print(plan["meta_name"], plan["stat_total_cost"])
```

This will print the names and total spend of all media plans in your workspace.

### Step 9: Export Plan to Excel

```python
# Export media plan to Excel
media_plan.export_to_excel(
    workspace_manager=workspace,
    file_name="media_plan_export.xlsx",
    overwrite=True
)
```

This will save the media plan (including metadata and line items) to a formatted Excel file in the workspace's `exports` folder.

**Tip:** To modify a media plan via Excel, copy the exported file from the `exports` subdirectory into the `imports` subdirectory of your workspace. Make your edits there before importing it back in Step 10.


### Step 10: Import Plan from Excel

```python
# Import a new media plan from Excel
imported_plan = MediaPlan.import_from_excel(
    file_name="media_plan_export.xlsx",
    workspace_manager=workspace
)
saved_path = imported_plan.save(workspace)
print(f"Imported plan: {imported_plan.meta.id}")
```

This creates a new media plan from the Excel file placed in the `imports` subdirectory of your workspace.