#!/usr/bin/env python3
"""
Example script demonstrating database integration functionality.

This script shows how to:
1. Configure a workspace with database settings
2. Create and save a media plan with automatic database sync
3. Test database connectivity and validation

Prerequisites:
- PostgreSQL server running
- psycopg2-binary installed: pip install psycopg2-binary
- Environment variable set with database password
"""

import os
import json
import tempfile
from datetime import date, datetime
from decimal import Decimal

# Import mediaplanpy
import mediaplanpy
from mediaplanpy import WorkspaceManager, MediaPlan


def create_test_workspace_config():
    """Create a test workspace configuration with database enabled."""

    # Create a temporary directory for workspace storage
    temp_dir = tempfile.mkdtemp(prefix="mediaplanpy_test_")

    config = {
        "workspace_id": "test_db_workspace",
        "workspace_name": "Test Database Workspace",
        "workspace_status": "active",
        "environment": "development",
        "storage": {
            "mode": "local",
            "local": {
                "base_path": temp_dir,
                "create_if_missing": True
            }
        },
        "schema_settings": {
            "preferred_version": "v1.0.0",
            "auto_migrate": False,
            "offline_mode": False
        },
        "database": {
            "enabled": True,
            "host": "localhost",
            "port": 5432,
            "database": "mediaplanpy",
            "schema": "public",
            "table_name": "media_plans",
            "username": "superuser",
            "password_env_var": "MEDIAPLAN_DB_PASSWORD",
            "ssl": False,  # Set to True for production
            "connection_timeout": 30,
            "auto_create_table": True
        },
        "excel": {
            "enabled": True
        },
        "logging": {
            "level": "INFO"
        }
    }

    return config, temp_dir


def create_sample_media_plan():
    """Create a sample media plan for testing."""

    media_plan = MediaPlan.create(
        created_by="test_user@example.com",
        campaign_name="Summer Campaign 2025",
        campaign_objective="Drive brand awareness and website traffic",
        campaign_start_date="2025-06-01",
        campaign_end_date="2025-08-31",
        campaign_budget=50000,
        schema_version="v1.0.0"
    )

    # Add some line items
    media_plan.create_lineitem({
        "name": "Facebook Feed Ads",
        "channel": "social",
        "vehicle": "Facebook",
        "partner": "Meta",
        "media_product": "Feed Ads",
        "cost_total": 15000,
        "adformat": "image",
        "kpi": "CPM",
        "cost_media": 12000,
        "cost_platform": 3000,
        "metric_impressions": 500000,
        "metric_clicks": 15000
    })

    media_plan.create_lineitem({
        "name": "Google Search Ads",
        "channel": "search",
        "vehicle": "Google Ads",
        "partner": "Google",
        "media_product": "Search Ads",
        "cost_total": 20000,
        "adformat": "text",
        "kpi": "CPC",
        "cost_media": 18000,
        "cost_platform": 2000,
        "metric_impressions": 200000,
        "metric_clicks": 20000
    })

    media_plan.create_lineitem({
        "name": "YouTube Pre-roll",
        "channel": "video",
        "vehicle": "YouTube",
        "partner": "Google",
        "media_product": "Pre-roll Ads",
        "cost_total": 15000,
        "adformat": "video",
        "kpi": "CPV",
        "cost_media": 13000,
        "cost_creative": 2000,
        "metric_views": 300000,
        "metric_clicks": 9000
    })

    return media_plan


def main():
    """Main test function."""

    print("🧪 MediaPlanPy Database Integration Test")
    print("=" * 50)

    # Check if database functionality is available
    if not mediaplanpy.is_database_available():
        print("❌ Database functionality not available")
        print("Install psycopg2-binary: pip install psycopg2-binary")
        return 1

    print("✅ Database functionality available")

    # Check environment variable
    db_password = os.environ.get("MEDIAPLAN_DB_PASSWORD")
    if not db_password:
        print("⚠️  Warning: MEDIAPLAN_DB_PASSWORD environment variable not set")
        print("Set it with: export MEDIAPLAN_DB_PASSWORD=your_password")
        print("Continuing with test (connection may fail)...")
    else:
        print("✅ Database password environment variable found")

    print()

    # Create test workspace configuration
    print("1️⃣ Creating test workspace configuration...")
    config, temp_dir = create_test_workspace_config()
    print(f"   Workspace storage: {temp_dir}")
    print(f"   Database: {config['database']['host']}:{config['database']['port']}/{config['database']['database']}")

    # Initialize workspace manager
    print("\n2️⃣ Initializing workspace manager...")
    workspace_manager = WorkspaceManager()
    try:
        workspace_manager.load(config_dict=config)
        print("✅ Workspace loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load workspace: {e}")
        return 1

    # Test database connection
    print("\n3️⃣ Testing database connection...")
    try:
        connection_ok = MediaPlan.test_database_connection(workspace_manager)
        if connection_ok:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            print("Check your PostgreSQL server and credentials")
            return 1
    except Exception as e:
        print(f"❌ Database connection test error: {e}")
        return 1

    # Create database table
    print("\n4️⃣ Creating database table...")
    try:
        table_created = MediaPlan.create_database_table(workspace_manager)
        if table_created:
            print("✅ Database table created successfully")
        else:
            print("❌ Failed to create database table")
            return 1
    except Exception as e:
        print(f"❌ Database table creation error: {e}")
        return 1

    # Validate database schema
    print("\n5️⃣ Validating database schema...")
    try:
        schema_valid = MediaPlan.validate_database_schema(workspace_manager)
        if schema_valid:
            print("✅ Database schema validation successful")
        else:
            print("❌ Database schema validation failed")
            return 1
    except Exception as e:
        print(f"❌ Database schema validation error: {e}")
        return 1

    # Create sample media plan
    print("\n6️⃣ Creating sample media plan...")
    try:
        media_plan = create_sample_media_plan()
        print(f"✅ Created media plan: {media_plan.meta.id}")
        print(f"   Campaign: {media_plan.campaign.name}")
        print(f"   Line items: {len(media_plan.lineitems)}")
        print(f"   Total budget: ${media_plan.campaign.budget_total:,.2f}")
    except Exception as e:
        print(f"❌ Failed to create media plan: {e}")
        return 1

    # Save media plan (should automatically sync to database)
    print("\n7️⃣ Saving media plan with database sync...")
    try:
        saved_path = media_plan.save(workspace_manager)
        print(f"✅ Media plan saved successfully")
        print(f"   File path: {saved_path}")
        print(f"   Database sync: Automatic (check logs above)")
    except Exception as e:
        print(f"❌ Failed to save media plan: {e}")
        return 1

    # Test overwrite functionality
    print("\n8️⃣ Testing overwrite functionality...")
    try:
        # Modify the media plan
        media_plan.campaign.name = "Updated Summer Campaign 2025"
        media_plan.create_lineitem({
            "name": "Instagram Stories",
            "channel": "social",
            "vehicle": "Instagram",
            "partner": "Meta",
            "cost_total": 8000,
            "adformat": "story",
            "kpi": "CPM"
        })

        # Save with overwrite=True
        saved_path = media_plan.save(workspace_manager, overwrite=True)
        print(f"✅ Media plan updated successfully")
        print(f"   New line items count: {len(media_plan.lineitems)}")
        print(f"   Database records replaced (check logs above)")
    except Exception as e:
        print(f"❌ Failed to update media plan: {e}")
        return 1

    # Test deletion
    print("\n9️⃣ Testing deletion with database cleanup...")
    try:
        # First do a dry run
        result = media_plan.delete(workspace_manager, dry_run=True)
        print(f"🔍 Dry run results:")
        print(f"   Files to delete: {len(result['deleted_files'])}")
        print(f"   Database records to delete: {'Yes' if result['database_deleted'] else 'No'}")

        # Actually delete
        result = media_plan.delete(workspace_manager, dry_run=False)
        print(f"✅ Media plan deleted successfully")
        print(f"   Files deleted: {result['files_deleted']}")
        print(f"   Database rows deleted: {result['database_rows_deleted']}")

    except Exception as e:
        print(f"❌ Failed to delete media plan: {e}")
        return 1

    print("\n🎉 All tests completed successfully!")
    print("\nNext steps:")
    print("- Check your PostgreSQL database to see the synced data")
    print("- Try creating media plans through your application")
    print("- Monitor the logs for database sync operations")

    # Cleanup
    import shutil
    try:
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        print(f"⚠️  Could not clean up temporary directory: {e}")

    return 0


if __name__ == "__main__":
    exit(main())