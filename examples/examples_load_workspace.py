"""
MediaPlanPy Examples - Load Workspace

This script demonstrates how to load workspace configurations using MediaPlanPy SDK v3.0.
Workspaces can be loaded in three different ways depending on your use case.

v3.0 Features Demonstrated:
- WorkspaceManager.load() three loading patterns
- Workspace version validation (v3.0 required)
- Schema version enforcement
- Automatic configuration migration for deprecated fields
- Workspace status checking (active/inactive)

Prerequisites:
- MediaPlanPy SDK v3.0.0+ installed
- Workspace configurations created (see examples_create_workspace.py)

How to Run:
1. First run examples_create_workspace.py to create test workspaces
2. Open this file in your IDE
3. Run the entire script: python examples_load_workspace.py
4. Or run individual functions by calling them from __main__

Next Steps After Running:
- Use the loaded WorkspaceManager to create media plans
- Access storage backend via manager.get_storage_backend()
- Query workspace contents via manager.list_campaigns(), etc.
"""

import os
import json
from pathlib import Path
from datetime import datetime

from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy import __schema_version__


def load_by_path():
    """
    Load workspace by direct file path.

    Use Case:
        When you have the full path to a workspace settings file.
        This is the most straightforward loading method.

    v3.0 Features:
        - Direct file loading with workspace_path parameter
        - Schema version validation (must be v3.0)
        - Automatic migration of deprecated fields
        - Workspace status check with warning if inactive

    Returns:
        Loaded workspace configuration dictionary

    Next Steps:
        - Manager is ready for media plan operations
        - Check manager.is_loaded to verify
        - Access storage backend via manager.get_storage_backend()

    Prerequisites:
        - Run examples_create_workspace.py first to create workspaces
        - This example assumes workspaces exist in examples/output/workspace_examples/
    """
    # For this example, we'll reference the workspace created in examples_create_workspace.py
    # In a real scenario, you would have the actual path to your workspace settings file
    output_dir = Path(__file__).parent / "output" / "workspace_examples"
    settings_path = output_dir / "production_workspace_settings.json"

    print("\n" + "="*60)
    print("Loading Workspace by Path")
    print("="*60)
    print(f"Settings file: {settings_path}")

    # Now load by direct path - this is the simplest method
    manager = WorkspaceManager()
    config = manager.load(workspace_path=str(settings_path))

    print(f"\n✓ Successfully loaded workspace by path")
    print(f"\nWorkspace Details:")
    print(f"  - Workspace ID: {config['workspace_id']}")
    print(f"  - Workspace name: {config['workspace_name']}")
    print(f"  - Schema version: {config['workspace_settings']['schema_version']}")
    print(f"  - Storage mode: {config['storage']['mode']}")
    print(f"  - Status: {config['workspace_status']}")
    print(f"  - Is loaded: {manager.is_loaded}")

    print(f"\nStorage Configuration:")
    if config['storage']['mode'] == 'local':
        print(f"  - Base path: {config['storage']['local']['base_path']}")
    elif config['storage']['mode'] == 's3':
        print(f"  - S3 bucket: {config['storage']['s3']['bucket']}")
        print(f"  - S3 region: {config['storage']['s3']['region']}")

    print(f"\nNext Steps:")
    print(f"  1. Create media plans: MediaPlan.create(...)")
    print(f"  2. Save plans: plan.save(manager)")
    print(f"  3. Query workspace: manager.list_campaigns()")

    return config


def load_by_workspace_id():
    """
    Load workspace by workspace_id using automatic search.

    Use Case:
        When you know the workspace_id but not the exact file location.
        The load() method searches multiple standard locations automatically.

    v3.0 Features:
        - Automatic file location search using workspace_id
        - Searches: default directory, current directory, user directories
        - Schema version validation
        - Error with helpful search paths if not found

    Returns:
        Loaded workspace configuration dictionary

    Next Steps:
        - Use loaded manager to create/load media plans
        - The manager now knows where to store files
        - Access configuration via manager.config

    Prerequisites:
        - Run examples_create_workspace.py first to create workspaces in default location
        - Note the workspace_id printed at the end of that script
        - Update the workspace_id variable below with your actual workspace ID

    Note:
        The workspace_id search looks in these locations (in order):
        1. Default directory (C:/mediaplanpy on Windows, ~/mediaplanpy on Unix)
        2. Current working directory
        3. User config directories (~/.mediaplanpy or ~/.config/mediaplanpy)

        File names checked: {workspace_id}_settings.json or {workspace_id}.json
    """
    # UPDATE THIS: Replace with actual workspace_id from examples_create_workspace.py
    # After running examples_create_workspace.py, copy the workspace_id printed at the end
    workspace_id = "workspace_xxxxxxxx"  # Replace with actual ID

    print("\n" + "="*60)
    print("Loading Workspace by ID")
    print("="*60)
    print(f"Attempting to load workspace_id: {workspace_id}")
    print(f"Searching in standard locations...")

    # Load by workspace_id - this will search in standard locations
    manager = WorkspaceManager()

    try:
        config = manager.load(workspace_id=workspace_id)

        print(f"\n✓ Successfully loaded workspace by ID")
        print(f"\nWorkspace Details:")
        print(f"  - Workspace ID: {config['workspace_id']}")
        print(f"  - Workspace name: {config['workspace_name']}")
        print(f"  - Schema version: {config['workspace_settings']['schema_version']}")
        print(f"  - Storage mode: {config['storage']['mode']}")
        print(f"  - Status: {config['workspace_status']}")

        print(f"\nSearch Locations Checked:")
        print(f"  1. Default directory: C:/mediaplanpy/{workspace_id}_settings.json")
        print(f"  2. Current directory: ./{workspace_id}_settings.json")
        print(f"  3. User directories: ~/.mediaplanpy/{workspace_id}_settings.json")

        return config

    except FileNotFoundError as e:
        print(f"\n✗ Workspace not found")
        print(f"\nTo fix this:")
        print(f"  1. Run examples_create_workspace.py first")
        print(f"  2. Copy the workspace_id from the output")
        print(f"  3. Update the workspace_id variable in this function")
        print(f"\nSearch locations checked:")
        print(f"  1. C:/mediaplanpy/{workspace_id}_settings.json")
        print(f"  2. ./{workspace_id}_settings.json")
        print(f"  3. ~/.mediaplanpy/{workspace_id}_settings.json")
        raise


def load_by_dict():
    """
    Load workspace from in-memory configuration dictionary.

    Use Case:
        Testing, dynamic configuration, non-file-based configs,
        programmatic workspace generation, or config from external sources.

    v3.0 Features:
        - In-memory workspace creation without files
        - Programmatic configuration building
        - Full schema validation on dictionary
        - Migration of deprecated fields

    Returns:
        Loaded workspace configuration dictionary

    Next Steps:
        - Useful for testing without file I/O
        - Can modify config dict before loading
        - Manager has no workspace_path (file-less operation)
        - Still fully functional for creating/loading media plans

    Note:
        This method is ideal for:
        - Unit testing
        - Dynamic configuration generation
        - Loading configs from databases or APIs
        - Temporary workspaces
    """
    print("\n" + "="*60)
    print("Loading Workspace from Dictionary")
    print("="*60)

    # Create config dict programmatically
    # This matches the structure of a workspace settings file
    config_dict = {
        "workspace_id": "test_dict_workspace",
        "workspace_name": "In-Memory Test Workspace",
        "workspace_status": "active",
        "environment": "testing",

        # Storage configuration
        "storage": {
            "mode": "local",
            "local": {
                "base_path": "C:/mediaplanpy/test_dict_workspace",  # Or ~/mediaplanpy on Unix
                "create_if_missing": True
            },
            "s3": {
                "bucket": "",
                "region": "",
                "prefix": "test_dict_workspace",
                "profile": "",
                "endpoint_url": "",
                "use_ssl": True
            }
        },

        # Workspace settings - MUST include schema version
        "workspace_settings": {
            "schema_version": __schema_version__,
            "last_upgraded": datetime.now().strftime("%Y-%m-%d"),
            "sdk_version_required": f"{__schema_version__.split('.')[0]}.0.x"
        },

        # Database configuration
        "database": {
            "enabled": False,
            "host": "localhost",
            "port": 5432,
            "database": "mediaplanpy",
            "schema": "public",
            "table_name": "media_plans",
            "username": "postgres",
            "password_env_var": "MEDIAPLAN_DB_PASSWORD",
            "ssl": False,
            "connection_timeout": 30,
            "auto_create_table": True
        },

        # Excel configuration
        "excel": {
            "enabled": True
        },

        # Google Sheets configuration
        "google_sheets": {
            "enabled": False
        },

        # Logging configuration
        "logging": {
            "level": "INFO"
        }
    }

    print("Created configuration dictionary with:")
    print(f"  - Workspace ID: {config_dict['workspace_id']}")
    print(f"  - Schema version: {config_dict['workspace_settings']['schema_version']}")
    print(f"  - Storage mode: {config_dict['storage']['mode']}")

    # Load from dict - no file I/O involved
    manager = WorkspaceManager()
    loaded_config = manager.load(config_dict=config_dict)

    print(f"\n✓ Successfully loaded workspace from dictionary")
    print(f"\nWorkspace Details:")
    print(f"  - Workspace name: {loaded_config['workspace_name']}")
    print(f"  - Environment: {loaded_config['environment']}")
    print(f"  - Config source: In-memory dictionary")
    print(f"  - Has file path: {manager.workspace_path is not None}")
    print(f"  - Is loaded: {manager.is_loaded}")

    print(f"\nFeatures:")
    print(f"  - Storage mode: {loaded_config['storage']['mode']}")
    print(f"  - Excel enabled: {loaded_config['excel']['enabled']}")
    print(f"  - Database enabled: {loaded_config['database']['enabled']}")

    print(f"\nUse Cases for Dictionary Loading:")
    print(f"  - Unit testing (no file system dependency)")
    print(f"  - Dynamic config generation from templates")
    print(f"  - Loading from databases or external APIs")
    print(f"  - Temporary workspaces for one-time operations")

    return loaded_config


if __name__ == "__main__":
    print("="*60)
    print("MediaPlanPy v3.0 - Workspace Loading Examples")
    print("="*60)

    print("\n=== Example 1: Load by Path ===")
    config1 = load_by_path()

    print("\n=== Example 2: Load by Workspace ID ===")
    # Note: This will fail unless you update the workspace_id in the function
    try:
        config2 = load_by_workspace_id()
    except FileNotFoundError:
        print("\nSkipping Example 2 - Update workspace_id in function first")
        config2 = None

    print("\n=== Example 3: Load by Dictionary ===")
    config3 = load_by_dict()

    print("\n" + "="*60)
    print("Workspace Loading Examples Completed!")
    print("="*60)
    print(f"\nLoaded workspaces using different methods:")
    print(f"  1. By path: {config1['workspace_name']}")
    if config2:
        print(f"  2. By ID: {config2['workspace_name']}")
    else:
        print(f"  2. By ID: (skipped - needs workspace_id update)")
    print(f"  3. By dict: {config3['workspace_name']}")
    print(f"\nNext Steps:")
    print(f"  - Run examples_create_mediaplan.py to create media plans")
    print(f"  - Use these loaded workspaces for media plan storage")
