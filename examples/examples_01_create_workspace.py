"""
MediaPlanPy Examples - Create Workspace

This script demonstrates how to create workspace configurations using MediaPlanPy SDK v3.0.
Workspaces define where media plans are stored and how they are managed.

v3.0 Features Demonstrated:
- Workspace schema version 3.0
- WorkspaceManager.create() API
- Local filesystem storage configuration
- S3 cloud storage configuration
- Database integration setup (optional)
- Workspace status management

Prerequisites:
- MediaPlanPy SDK v3.0.0+ installed
- AWS credentials configured (for S3 example only)

How to Run:
1. Open this file in your IDE
2. Run the entire script: python examples_create_workspace.py
3. Or run individual functions by calling them from __main__
4. Check examples/output/workspace_examples/ for generated workspace configs

Next Steps After Running:
- Use the workspace_id with WorkspaceManager.load() (see examples_load_workspace.py)
- Create media plans using the workspace (see examples_create_mediaplan.py)
- Media plans will be saved to the configured storage location
"""

import os
from pathlib import Path
from datetime import datetime

from mediaplanpy.workspace import WorkspaceManager


def create_default_workspace():
    """
    Create a default workspace with local filesystem storage in the default location.

    Use Case:
        Starting point for most users - simple local filesystem storage with
        minimal configuration. Workspace is created in the standard default location
        (C:/mediaplanpy on Windows, ~/mediaplanpy on Unix).

    v3.0 Features:
        - Workspace schema version 3.0 (enforced)
        - Known workspace_id for easy reference in other examples
        - Local storage backend in default location
        - Excel export enabled by default
        - Workspace status set to 'active'

    Returns:
        Tuple of (workspace_id, settings_path)

    Next Steps:
        - Use workspace_id "test_workspace_local" in other examples
        - Load with: WorkspaceManager.load(workspace_id="test_workspace_local")
        - Create media plans using this workspace
        - Files saved to default location (C:/mediaplanpy/test_workspace_local)
    """
    print("\n" + "="*60)
    print("Creating Default Workspace")
    print("="*60)
    print("This workspace will be created in the default location:")
    print("  Windows: C:/mediaplanpy/")
    print("  Unix:    ~/mediaplanpy/")

    # Create workspace manager
    manager = WorkspaceManager()

    # Create workspace in DEFAULT location with KNOWN ID
    # By not specifying settings_path_name or storage_path_name,
    # the workspace is created in the default location
    workspace_id, settings_path = manager.create(
        workspace_name="Test Local Workspace",
        overwrite=True  # Overwrite if exists (for demo purposes)
    )

    print(f"\n✓ Workspace Created Successfully")
    print(f"\nWorkspace Details:")
    print(f"  - Workspace ID: {workspace_id}")
    print(f"  - Settings file: {settings_path}")

    # Load and inspect the configuration
    loaded_config = manager.load(workspace_path=settings_path)

    print(f"\nConfiguration:")
    print(f"  - Name: {loaded_config['workspace_name']}")
    print(f"  - Schema version: {loaded_config['workspace_settings']['schema_version']}")
    print(f"  - Storage mode: {loaded_config['storage']['mode']}")
    print(f"  - Storage path: {loaded_config['storage']['local']['base_path']}")
    print(f"  - Status: {loaded_config['workspace_status']}")
    print(f"  - Excel enabled: {loaded_config['excel']['enabled']}")
    print(f"  - Database enabled: {loaded_config['database']['enabled']}")

    print(f"\nHow to Load This Workspace:")
    print(f"  Method 1: manager.load(workspace_id='{workspace_id}')")
    print(f"  Method 2: manager.load(workspace_path='{settings_path}')")

    print(f"\nNext Steps:")
    print(f"  1. Run examples_load_workspace.py to see loading methods")
    print(f"  2. Run examples_create_mediaplan.py to create media plans")
    print(f"  3. Media plans will be saved to the storage path shown above")

    return workspace_id, settings_path


def create_custom_workspace_with_s3():
    """
    Create a workspace with AWS S3 storage and database configuration.

    Use Case:
        Production deployments, team collaboration, cloud-native architectures.
        S3 storage enables multi-user access, automatic backups, and scalability.
        This example shows how to configure custom storage and database settings.

    v3.0 Features:
        - S3 storage backend configuration
        - Custom workspace settings (environment, status)
        - Excel configuration options
        - Database integration setup (PostgreSQL)
        - SDK version requirements enforcement

    Returns:
        Tuple of (workspace_id, settings_path)

    Next Steps:
        - Configure AWS credentials (IAM roles, AWS CLI profile, or env vars)
        - Set MEDIAPLAN_DB_PASSWORD environment variable for database
        - Load workspace by ID to use in other examples
        - Media plans will be saved to S3 bucket

    Note:
        This example uses placeholder AWS credentials. In production:
        - Use AWS IAM roles (recommended)
        - Use AWS CLI configured profiles
        - Use environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    """
    print("\n" + "="*60)
    print("Creating S3 Workspace with Database")
    print("="*60)
    print("This workspace demonstrates:")
    print("  - S3 cloud storage configuration")
    print("  - PostgreSQL database integration")
    print("  - Custom environment settings")

    manager = WorkspaceManager()

    # Create workspace with S3 storage and custom settings
    # Created in default location for easy loading by workspace_id
    workspace_id, settings_path = manager.create(
        workspace_name="Test S3 Workspace",
        overwrite=True,

        # Environment and status
        environment="production",
        workspace_status="active",

        # Storage configuration - pass as dictionary matching top-level config structure
        storage={
            "mode": "s3",
            "s3": {
                "bucket": "my-mediaplan-bucket",
                "region": "us-east-1",
                "prefix": "mediaplans/production",
                "profile": "",  # Or specify: "my-aws-profile"
                "endpoint_url": "",  # For S3-compatible services
                "use_ssl": True
            }
        },

        # Excel configuration - pass as dictionary
        excel={
            "enabled": True
            # "template_path": "/path/to/custom_template.xlsx"  # Optional: custom template
        },

        # Database configuration - pass as dictionary
        database={
            "enabled": True,
            "host": "localhost",
            "port": 5432,
            "database": "mediaplanpy",
            "schema": "public",
            "table_name": "media_plans",
            "username": "postgres",
            "password_env_var": "MEDIAPLAN_DB_PASSWORD",  # Use environment variable for password
            "ssl": True,
            "connection_timeout": 30,
            "auto_create_table": True
        }
    )

    print("\n" + "="*60)
    print("SUCCESS: Custom S3 Workspace Created")
    print("="*60)
    print(f"  Workspace ID: {workspace_id}")
    print(f"  Settings file: {settings_path}")
    print(f"  Storage mode: S3")

    # Load and inspect the configuration
    # Use the settings_path returned from create()
    loaded_config = manager.load(workspace_path=settings_path)

    print(f"\nConfiguration:")
    print(f"  - Name: {loaded_config['workspace_name']}")
    print(f"  - Environment: {loaded_config['environment']}")
    print(f"  - Status: {loaded_config['workspace_status']}")
    print(f"  - Schema version: {loaded_config['workspace_settings']['schema_version']}")

    print(f"\nStorage (S3):")
    print(f"  - Mode: {loaded_config['storage']['mode']}")
    print(f"  - Bucket: {loaded_config['storage']['s3']['bucket']}")
    print(f"  - Region: {loaded_config['storage']['s3']['region']}")
    print(f"  - Prefix: {loaded_config['storage']['s3']['prefix']}")

    print(f"\nDatabase:")
    print(f"  - Enabled: {loaded_config['database']['enabled']}")
    if loaded_config['database']['enabled']:
        print(f"  - Host: {loaded_config['database']['host']}")
        print(f"  - Database: {loaded_config['database']['database']}")
        print(f"  - Schema: {loaded_config['database']['schema']}")

    print(f"\nPrerequisites to Use This Workspace:")
    print(f"  1. Configure AWS credentials:")
    print(f"     - Recommended: IAM roles")
    print(f"     - Alternative: AWS CLI profile (aws configure --profile my-profile)")
    print(f"     - Alternative: Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
    print(f"  2. Set database password:")
    print(f"     - export MEDIAPLAN_DB_PASSWORD=your_password")

    print(f"\nHow to Load This Workspace:")
    print(f"  manager.load(workspace_id='{workspace_id}')")

    return workspace_id, settings_path


if __name__ == "__main__":
    print("="*60)
    print("MediaPlanPy v3.0 - Workspace Creation Examples")
    print("="*60)

    print("\n=== Example 1: Create Default Local Workspace ===")
    workspace_id_1, path_1 = create_default_workspace()

    print("\n=== Example 2: Create S3 Workspace with Database ===")
    workspace_id_2, path_2 = create_custom_workspace_with_s3()

    print("\n" + "="*60)
    print("Summary: Workspace Creation Complete")
    print("="*60)
    print(f"\nCreated 2 workspaces in default location:")
    print(f"  1. Local:  {workspace_id_1}")
    print(f"  2. S3:     {workspace_id_2}")

    print(f"\nWorkspaces can be loaded by ID:")
    print(f"  manager = WorkspaceManager()")
    print(f"  manager.load(workspace_id='{workspace_id_1}')")

    print(f"\nNext Steps:")
    print(f"  - Run examples_load_workspace.py to see loading methods")
    print(f"  - Run examples_create_mediaplan.py to create media plans")
