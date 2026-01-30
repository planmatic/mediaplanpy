# Cloud Storage Configuration Guide

This guide explains how to configure Amazon S3 cloud storage for MediaPlanPy. Cloud storage is optional and useful for team collaboration, backup, and cloud-based workflows.

## Overview

By default, MediaPlanPy stores media plans locally in your workspace directory. You can optionally configure cloud storage to store media plans in **Amazon S3** for team collaboration, backup, or cloud-based workflows.

### Complete Workspace Settings Example

Here's a complete example of workspace settings with S3 storage configured:

```json
{
  "workspace_id": "workspace_abc123",
  "workspace_name": "Client A Production Workspace",
  "workspace_status": "active",
  "environment": "production",
  "storage": {
    "mode": "s3",
    "local": {
      "base_path": "/opt/planmatic/data",
      "create_if_missing": true
    },
    "s3": {
      "bucket": "my-company-mediaplan-prod",
      "region": "us-east-1",
      "prefix": "workspace_abc123",
      "profile": "",
      "endpoint_url": "",
      "use_ssl": true
    }
  },
  "workspace_settings": {
    "schema_version": "3.0",
    "last_upgraded": "2026-01-28",
    "sdk_version_required": "3.0.0"
  },
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
}
```

**Key Points:**
- The `bucket` name includes the environment (`-prod`) for environment isolation
- The `prefix` matches the `workspace_id` for proper workspace isolation
- Both `local` and `s3` configurations can coexist; `mode` determines which is active
- The workspace automatically creates subdirectories (mediaplans, exports, imports, backups) within the prefix

---

## Amazon S3 Configuration

### Step 1: Install AWS Dependencies

Install the required dependencies for S3 support:

```bash
pip install boto3
```

---

### Step 2: Set Up AWS Credentials

You can configure AWS credentials using one of these methods:

#### Method 1: AWS CLI (Recommended)

Install the AWS CLI and configure your credentials:

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

This will prompt you for:
- **AWS Access Key ID**: Your AWS access key
- **AWS Secret Access Key**: Your AWS secret key
- **Default region**: e.g., `us-east-1`
- **Default output format**: e.g., `json`

#### Method 2: Environment Variables

Set AWS credentials as environment variables:

**Windows (PowerShell):**

```powershell
setx AWS_ACCESS_KEY_ID "your_access_key"
setx AWS_SECRET_ACCESS_KEY "your_secret_key"
setx AWS_DEFAULT_REGION "us-east-1"
```

**macOS/Linux (bash/zsh):**

```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="us-east-1"
```

To make this permanent on macOS/Linux, add the `export` lines to your `~/.bashrc` or `~/.zshrc`.

---

### Step 3: Create or Use an S3 Bucket

Create a new S3 bucket for MediaPlanPy or use an existing one.

**Best Practice**: Create separate buckets for each environment (production, staging, development).

#### Create Buckets Using AWS CLI

```bash
# Create production bucket
aws s3 mb s3://my-company-mediaplan-prod --region us-east-1

# Create staging bucket
aws s3 mb s3://my-company-mediaplan-stage --region us-east-1

# Create development bucket
aws s3 mb s3://my-company-mediaplan-dev --region us-east-1

# Verify buckets were created
aws s3 ls | grep mediaplan
```

#### Create Bucket Using AWS Console

1. Go to the [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Click "Create bucket"
3. Enter bucket name with environment suffix (e.g., `my-company-mediaplan-prod`)
4. Select region (e.g., `us-east-1`)
5. Configure bucket settings (enable versioning and encryption recommended)
6. Click "Create bucket"
7. Repeat for each environment (stage, dev)

---

### Step 4: Update Workspace Settings for S3

Locate your workspace settings file (by default stored in `C:\mediaplanpy` on Windows, or the equivalent base path on macOS/Linux).

Open the JSON file and update the **storage** section:

```json
"storage": {
  "mode": "s3",
  "s3": {
    "bucket": "my-company-mediaplan-prod",
    "region": "us-east-1",
    "prefix": "workspace_abc123",
    "profile": "",
    "endpoint_url": "",
    "use_ssl": true
  }
}
```

**Configuration Options:**

- **mode**: Set to `"s3"` to use S3 storage
- **bucket**: Your S3 bucket name with environment suffix (e.g., `"my-company-mediaplan-prod"`)
- **region**: AWS region where your bucket is located (e.g., `"us-east-1"`)
- **prefix**: **Important**: Set this to your `workspace_id` to isolate files per workspace within the environment (e.g., `"workspace_abc123"`)
- **profile**: AWS profile name (leave empty `""` to use default credentials)
- **endpoint_url**: Custom S3 endpoint (leave empty `""` for standard AWS S3)
- **use_ssl**: Enable SSL/TLS connections (recommended: `true`)

**Best Practice - Environment and Workspace Isolation:**

**1. Separate buckets per environment**: Use different buckets for prod, stage, and dev
**2. Workspace ID as prefix**: Always set the `prefix` to match your `workspace_id`

This two-level isolation ensures:
- **Environment isolation**: Production is completely separated from dev/stage
- **Workspace isolation**: Multiple workspaces can coexist within same environment bucket
- **No file conflicts**: Each workspace has its own namespace
- **Granular access control**: Control access by environment and workspace
- **Clear organization**: Easy to manage and audit

The SDK automatically creates subdirectories within the workspace prefix:

```
# Production bucket (environment isolation)
s3://my-company-mediaplan-prod/
  ├── workspace_client_a/          # Workspace isolation
  │   ├── mediaplans/              # Media plan JSON files
  │   │   ├── mp_001.json
  │   │   └── mp_002.json
  │   ├── exports/                 # Exported files (Excel, etc.)
  │   ├── imports/                 # Files staged for import
  │   └── backups/                 # Backup files
  └── workspace_client_b/          # Another workspace
      ├── mediaplans/
      ├── exports/
      ├── imports/
      └── backups/
```

---

### Step 5: Test S3 Connection

Now test the S3 connection by creating and saving a media plan:

```python
from mediaplanpy import WorkspaceManager, MediaPlan

# Load workspace with S3 storage
workspace = WorkspaceManager()
workspace.load(workspace_id="your_workspace_id")

# Create a new Media Plan
plan = MediaPlan.create(
    created_by="you@example.com",
    campaign_name="S3 Test Campaign",
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

# Save to S3
plan.save(workspace)
print(f"Media plan saved to S3: s3://my-company-mediaplan-prod/{workspace.workspace_id}/mediaplans/{plan.meta.id}.json")
```

---

### Step 6: Verify S3 Storage

You can verify your media plans are stored in S3 using the AWS CLI:

```bash
# List workspaces in the production bucket
aws s3 ls s3://my-company-mediaplan-prod/

# List media plans for a specific workspace
aws s3 ls s3://my-company-mediaplan-prod/workspace_abc123/mediaplans/

# Download a specific media plan
aws s3 cp s3://my-company-mediaplan-prod/workspace_abc123/mediaplans/mp_12345.json ./

# View media plan content
cat mp_12345.json

# List all subdirectories for a workspace
aws s3 ls s3://my-company-mediaplan-prod/workspace_abc123/
```

Or view your files through the [AWS S3 Console](https://console.aws.amazon.com/s3/).

---

## Advanced Configuration

### Multi-Workspace Deployments

When deploying multiple workspaces, follow these best practices:

**1. Separate Buckets Per Environment**

**Best Practice**: Use a separate S3 bucket for each environment (dev, stage, prod). This provides:
- **Environment Isolation**: Development changes don't affect production
- **Security**: Different access controls and encryption keys per environment
- **Cost Tracking**: Clear separation of costs by environment
- **Compliance**: Easier to meet audit and regulatory requirements

Example bucket naming:
- Production: `my-company-mediaplan-prod`
- Staging: `my-company-mediaplan-stage`
- Development: `my-company-mediaplan-dev`

**2. Use Workspace ID as Prefix Within Each Bucket**

Always set the S3 prefix to the workspace_id:

```json
"storage": {
  "mode": "s3",
  "s3": {
    "bucket": "my-company-mediaplan-prod",  // Environment-specific bucket
    "prefix": "workspace_abc123",           // Must match workspace_id
    "region": "us-east-1"
  }
}
```

**3. Benefits of This Approach**

- **Environment Isolation**: Clear separation between dev/stage/prod
- **Workspace Isolation**: Multiple workspaces can coexist within same environment
- **No File Conflicts**: Each workspace has its own namespace
- **Granular Access Control**: Grant users access to specific environments and workspaces
- **Independent Operations**: One workspace's operations don't affect others

**4. Example Production Multi-Workspace Structure**

```
# Production Environment
s3://my-company-mediaplan-prod/
  ├── workspace_client_a/
  │   ├── mediaplans/
  │   ├── exports/
  │   ├── imports/
  │   └── backups/
  └── workspace_client_b/
      ├── mediaplans/
      ├── exports/
      ├── imports/
      └── backups/

# Staging Environment (separate bucket)
s3://my-company-mediaplan-stage/
  ├── workspace_test_001/
  │   ├── mediaplans/
  │   ├── exports/
  │   ├── imports/
  │   └── backups/
  └── workspace_test_002/
      ├── mediaplans/
      ├── exports/
      ├── imports/
      └── backups/

# Development Environment (separate bucket)
s3://my-company-mediaplan-dev/
  └── workspace_dev_sandbox/
      ├── mediaplans/
      ├── exports/
      ├── imports/
      └── backups/
```

---

## Troubleshooting

### Authentication Errors

If you see "Access Denied" or authentication errors:

- Verify AWS credentials are set correctly: `aws configure list`
- Check IAM user has S3 permissions: `s3:PutObject`, `s3:GetObject`, `s3:ListBucket`
- Ensure region matches bucket region

### Bucket Not Found

If you see "NoSuchBucket" errors:

- Verify bucket name is spelled correctly
- Check bucket exists: `aws s3 ls s3://my-mediaplan-bucket`
- Ensure you have access to the bucket

### Connection Timeout

If operations timeout:

- Check internet connectivity
- Verify AWS region is accessible
- Increase connection timeout in boto3 configuration

### Permission Denied

If you see permission errors:

- Check IAM policy allows required S3 actions
- Verify bucket policy doesn't block access
- Ensure credentials belong to correct AWS account
- Verify the S3 prefix (workspace_id) is correctly configured

### Files Not Found / Wrong Location

If files are saved to unexpected locations:

- Verify `prefix` in storage configuration matches your `workspace_id`
- Check that you're not using a hardcoded prefix like `"mediaplans/"`
- Confirm the workspace settings file is correct: `prefix` should be `workspace_abc123` not `workspace_abc123/mediaplans/`
- The SDK automatically appends subdirectories (mediaplans, exports, imports, backups) to the prefix

---

## Related Documentation

- [GET_STARTED.md](../GET_STARTED.md) - Basic setup guide
- [Database Configuration](database_configuration.md) - PostgreSQL integration guide
- [SDK Reference](../SDK_REFERENCE.md) - Complete API documentation
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/) - Official AWS S3 docs

---

## Contact & Support

For questions or support:
- Visit our [website](https://www.planmatic.io)
- Follow us on [LinkedIn](https://www.linkedin.com/company/planmatic)
- Email us at [contact@planmatic.io](mailto:contact@planmatic.io)
