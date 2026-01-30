# Database Configuration Guide

This guide explains how to configure PostgreSQL database integration for MediaPlanPy. Database integration is optional and useful for analytics, visualization, and multi-user scenarios.

## Overview

By default, MediaPlanPy stores media plans as JSON and Parquet files in your workspace. If you would like to **push media plans to PostgreSQL** for analytics or visualization purposes, follow the steps in this guide.

---

## Step 1: Install PostgreSQL

If you don't already have PostgreSQL installed, install it for your operating system:

### Windows

Download and install PostgreSQL from the [official installer](https://www.postgresql.org/download/windows/).

During setup, make note of the **username**, **password**, and **port** (default: `5432`).

### macOS

```bash
brew install postgresql
brew services start postgresql
```

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### Verify Installation

After installation, verify PostgreSQL is running:

```bash
psql --version
```

---

## Step 2: Create or Reuse a Database

You may either create a new database dedicated to MediaPlanPy or use an existing PostgreSQL database.

### Create a New Database

You can create a database using the PGAdmin user interface or via command line:

```bash
psql -U postgres
CREATE DATABASE mediaplanpy;
\q
```

### Use an Existing Database

If you choose to use an existing database, simply update the connection properties in the workspace settings accordingly.

---

## Step 3: Update Workspace Settings

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

**Configuration Options:**

- **enabled**: Set to `true` to enable database integration
- **host**: Database host (typically `localhost` for local development)
- **port**: Database port (default: `5432`)
- **database**: Database name
- **schema**: Schema name (default: `public`)
- **table_name**: Table name for media plans (will be auto-created if it doesn't exist)
- **username**: Database username
- **password_env_var**: Environment variable name containing the password
- **ssl**: Enable SSL connection (set to `true` for production)
- **connection_timeout**: Connection timeout in seconds
- **auto_create_table**: Automatically create the table if it doesn't exist

---

## Step 4: Configure Password as Environment Variable

To avoid storing your password in plain text, save it as an environment variable:

### Windows (PowerShell)

```powershell
setx MEDIAPLAN_DB_PASSWORD "your_password_here"
```

### macOS/Linux (bash/zsh)

```bash
export MEDIAPLAN_DB_PASSWORD="your_password_here"
```

To make this permanent on macOS/Linux, add the `export` line to your `~/.bashrc` or `~/.zshrc`.

---

## Step 5: Test the Database Connection

Now that your database is configured, test the connection in Python:

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
print("Media plan saved successfully to database!")
```

---

## Step 6: Verify the Connection

### Check for Errors

Check that no errors appear in your Python logs when saving the plan.

### Verify Data in Database

Manually verify that a new record was inserted into your target database table (`media_plans` by default).

**Using psql command line:**

```bash
psql -U postgres -d mediaplanpy -c "SELECT meta_id, meta_name, campaign_name FROM public.media_plans;"
```

**Using PGAdmin:**

Open PGAdmin, navigate to your database, and browse the `media_plans` table.

If you see your newly created plan listed in the table, the connection is working correctly.

---

## Troubleshooting

### Connection Refused

If you see "connection refused" errors:
- Verify PostgreSQL is running: `pg_isready`
- Check the host and port in workspace settings
- Ensure firewall allows connections on port 5432

### Authentication Failed

If you see authentication errors:
- Verify the username is correct
- Ensure the environment variable is set correctly: `echo $MEDIAPLAN_DB_PASSWORD`
- Check PostgreSQL authentication settings in `pg_hba.conf`

### Table Not Created

If the table is not auto-created:
- Verify `auto_create_table` is set to `true`
- Check that the database user has CREATE TABLE permissions
- Manually create the table using the schema from SDK documentation

### Permission Denied

If you see permission errors:
- Ensure the database user has INSERT, SELECT, UPDATE permissions
- Grant permissions: `GRANT ALL ON TABLE media_plans TO postgres;`

---

## Advanced Configuration

### SSL Connections

For production environments, enable SSL:

```json
"database": {
  "enabled": true,
  "ssl": true,
  "ssl_mode": "require"
}
```

### Connection Pooling

For high-performance scenarios, configure connection pooling in your workspace settings.

### Multiple Workspaces Sharing a Database

Multiple workspaces can share the same database by using different table names:

```json
"database": {
  "table_name": "media_plans_prod"  // Workspace 1
}
```

```json
"database": {
  "table_name": "media_plans_dev"   // Workspace 2
}
```

---

## Related Documentation

- [GET_STARTED.md](../GET_STARTED.md) - Basic setup guide
- [Cloud Storage Configuration](cloud_storage_configuration.md) - S3 integration guide
- [SDK Reference](../SDK_REFERENCE.md) - Complete API documentation

---

## Contact & Support

For questions or support:
- Visit our [website](https://www.planmatic.io)
- Follow us on [LinkedIn](https://www.linkedin.com/company/planmatic)
- Email us at [contact@planmatic.io](mailto:contact@planmatic.io)
