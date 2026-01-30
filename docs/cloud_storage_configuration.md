# Cloud Storage Configuration Guide

This guide explains how to configure Amazon S3 cloud storage for MediaPlanPy. Cloud storage is optional and useful for team collaboration, backup, and cloud-based workflows.

## Overview

By default, MediaPlanPy stores media plans locally in your workspace directory. You can optionally configure cloud storage to store media plans in **Amazon S3** for team collaboration, backup, or cloud-based workflows.

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

#### Create Bucket Using AWS CLI

```bash
# Create a new bucket
aws s3 mb s3://my-mediaplan-bucket --region us-east-1

# Verify bucket was created
aws s3 ls
```

#### Create Bucket Using AWS Console

1. Go to the [AWS S3 Console](https://console.aws.amazon.com/s3/)
2. Click "Create bucket"
3. Enter bucket name (e.g., `my-mediaplan-bucket`)
4. Select region (e.g., `us-east-1`)
5. Configure bucket settings as needed
6. Click "Create bucket"

---

### Step 4: Update Workspace Settings for S3

Locate your workspace settings file (by default stored in `C:\mediaplanpy` on Windows, or the equivalent base path on macOS/Linux).

Open the JSON file and update the **storage** section:

```json
"storage": {
  "type": "s3",
  "bucket": "my-mediaplan-bucket",
  "prefix": "mediaplans/",
  "region": "us-east-1"
}
```

**Configuration Options:**

- **type**: Set to `"s3"` to use S3 storage
- **bucket**: Your S3 bucket name
- **prefix**: Optional folder prefix within the bucket (e.g., `"mediaplans/"`)
- **region**: AWS region where your bucket is located (e.g., `"us-east-1"`)

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
print(f"Media plan saved to S3: s3://my-mediaplan-bucket/mediaplans/{plan.meta.id}.json")
```

---

### Step 6: Verify S3 Storage

You can verify your media plans are stored in S3 using the AWS CLI:

```bash
# List media plans in S3
aws s3 ls s3://my-mediaplan-bucket/mediaplans/

# Download a specific media plan
aws s3 cp s3://my-mediaplan-bucket/mediaplans/mp_12345.json ./

# View media plan content
cat mp_12345.json
```

Or view your files through the [AWS S3 Console](https://console.aws.amazon.com/s3/).

---

## Switching Between Storage Backends

You can switch between local and S3 storage by updating the workspace settings file.

### Switch from Local to S3

Update workspace settings:

```json
"storage": {
  "type": "s3",
  "bucket": "my-mediaplan-bucket",
  "prefix": "mediaplans/",
  "region": "us-east-1"
}
```

The SDK will automatically detect the change on the next workspace load.

### Switch from S3 to Local

Update workspace settings:

```json
"storage": {
  "type": "local",
  "base_path": "C:\\mediaplanpy\\workspace_abc123"
}
```

---

## Advanced Configuration

### Cross-Region Replication

For disaster recovery, configure S3 bucket replication to another region:

1. Go to your bucket in AWS S3 Console
2. Navigate to "Management" > "Replication rules"
3. Create a replication rule to another region
4. MediaPlanPy will automatically use the primary bucket

### Server-Side Encryption

Enable S3 server-side encryption for enhanced security:

**Using AWS CLI:**

```bash
aws s3api put-bucket-encryption \
  --bucket my-mediaplan-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

**Using AWS Console:**

1. Go to your bucket
2. Navigate to "Properties" > "Default encryption"
3. Enable "AES-256" or "AWS-KMS" encryption

### Access Control

Configure bucket policies for team access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:user/teammember"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-mediaplan-bucket/mediaplans/*"
    }
  ]
}
```

### Lifecycle Policies

Configure S3 lifecycle policies to manage storage costs:

```bash
# Example: Move old media plans to Glacier after 90 days
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-mediaplan-bucket \
  --lifecycle-configuration file://lifecycle.json
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

---

## Cost Considerations

### S3 Pricing Overview

AWS S3 charges for:
- **Storage**: Per GB per month
- **Requests**: Per PUT, GET, LIST request
- **Data transfer**: Outbound data transfer charges

### Cost Optimization Tips

1. **Use lifecycle policies** to move old media plans to cheaper storage classes
2. **Enable compression** for JSON files before upload
3. **Use appropriate storage class**:
   - Standard for frequently accessed plans
   - Standard-IA for archived plans (accessed monthly)
   - Glacier for long-term archives (accessed rarely)
4. **Monitor usage** using AWS Cost Explorer

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
