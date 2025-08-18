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



## Configure Database Connection (Optional)

By default, `mediaplanpy` stores media plans as JSON and Parquet files in your workspace.  
If you would like to **push media plans in PostgreSQL** for anlaytics of visualization purpose, follow these steps.

### Step 1: Install PostgreSQL (if required)

- **Windows**  
  Download and install PostgreSQL from the [official installer](https://www.postgresql.org/download/windows/).  
  During setup, make note of the **username**, **password**, and **port** (default: `5432`).

- **macOS**  
  ```bash
  brew install postgresql
  brew services start postgresql
  ```

- **Linux (Debian/Ubuntu)**  
  ```bash
  sudo apt update
  sudo apt install postgresql postgresql-contrib
  sudo systemctl enable postgresql
  sudo systemctl start postgresql
  ```

After installation, verify it works by running:

```bash
psql --version
```

### Step 2: Create or Reuse a Database

You may either create a new database dedicated to `mediaplanpy` or use an existing PostgreSQL database.

To create a new database you can use the PGAdmin user interface or:

```bash
psql -U postgres
CREATE DATABASE mediaplanpy;
```

If you choose to use an existing database, simply update the connection properties in the workspace settings accordingly.

### Step 3: Update Workspace Settings

Locate your workspace settings file (by default stored in `C:\mediaplanpy` on Windows, or the equivalent base path on macOS/Linux).  
Open the JSON file and update the **database** section:

```json
"database": {
  "enabled": true,
  "host": "localhost",
  "port": 5432,
  "database": "mediaplanpy",
  "schema": "public",
  "table_name": "media_plans",
  "username": "postgres",
  "password_env_var": "MEDIAPLAN_DB_PASSWORD",
  "ssl": false,
  "connection_timeout": 30,
  "auto_create_table": true
}
```

- Set `"enabled": true`  
- Confirm or adjust database name, username, schema, and table name (the table will be created automatically if it does not exist)
- The password will be supplied via an environment variable (next step)

### Step 4: Configure Password as Environment Variable

To avoid storing your password in plain text, save it as an environment variable:

- **Windows (PowerShell)**  
  ```powershell
  setx MEDIAPLAN_DB_PASSWORD "your_password_here"
  ```

- **macOS/Linux (bash/zsh)**  
  ```bash
  export MEDIAPLAN_DB_PASSWORD="your_password_here"
  ```

To make this permanent on macOS/Linux, add the `export` line to your `~/.bashrc` or `~/.zshrc`.

### Step 5: Test the Database Connection

Now that your database is configured, you can test it in Python:

```python
from mediaplanpy import WorkspaceManager, MediaPlan

# Load your existing workspace
workspace = WorkspaceManager()
workspace.load(workspace_id="workspace_6b48be28")  # Replace with your Workspace ID

# Create a new Media Plan
plan = MediaPlan.create(
    created_by="you@example.com",
    campaign_name="Database Test Campaign",
    campaign_objective="Awareness",
    campaign_start_date="2025-09-01",
    campaign_end_date="2025-11-30",
    campaign_budget=10000,
    workspace_manager=workspace
)

# Add a line item
lineitem = plan.create_lineitem({
    "name": "Search Ads",
    "channel": "Search",
    "vehicle": "Google",
    "partner": "Google",
    "media_product": "Google Ads",
    "location_type": "Country",
    "location_name": "USA",
    "target_audience": "Adults 18-54",
    "adformat": "Text",
    "kpi": "Clicks",
    "cost_total": 2500,
    "cost_currency": "USD"
})

# Save the plan (this will insert into the database)
plan.save(workspace)
```

### Step 6: Verify the Connection

1. Check that no errors appear in your Python logs when saving the plan.  
2. Manually verify that a new record was inserted into your target database table (`media_plans` by default).  
   For example:

```bash
psql -U postgres -d mediaplanpy -c "SELECT * FROM public.media_plans;"
```

If you see your newly created plan listed in the table, the connection is working correctly.