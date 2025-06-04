#!/usr/bin/env python3
"""
Test script for validating Phase 5.2 migration implementation.

This script tests the updated schema migration functionality.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mediaplanpy.schema.migration import SchemaMigrator
from mediaplanpy.schema.registry import SchemaRegistry
import json


def test_migration_paths():
    """Test migration path discovery."""
    print("=== Testing Migration Path Discovery ===")

    migrator = SchemaMigrator()

    # Test various format combinations
    test_cases = [
        ("v0.0.0", "v1.0.0"),  # Legacy format
        ("0.0", "1.0"),  # New format
        ("v0.0.0", "1.0"),  # Cross-format
        ("0.0", "v1.0.0"),  # Cross-format
    ]

    for from_v, to_v in test_cases:
        can_migrate = migrator.can_migrate(from_v, to_v)
        path = migrator.find_migration_path(from_v, to_v)
        print(f"  {from_v} → {to_v}: {'✓' if can_migrate else '✗'} (path: {path})")


def test_migration_compatibility():
    """Test migration compatibility validation."""
    print("\n=== Testing Migration Compatibility ===")

    migrator = SchemaMigrator()

    test_cases = [
        ("v0.0.0", "1.0"),
        ("0.0", "v1.0.0"),
        ("1.0", "2.0"),  # Future migration
        ("invalid", "1.0"),  # Invalid source
    ]

    for from_v, to_v in test_cases:
        try:
            result = migrator.validate_migration_compatibility(from_v, to_v)
            status = "✓" if result["compatible"] else "✗"
            print(f"  {from_v} → {to_v}: {status}")
            if result["errors"]:
                print(f"    Errors: {result['errors']}")
            if result["warnings"]:
                print(f"    Warnings: {result['warnings']}")
        except Exception as e:
            print(f"  {from_v} → {to_v}: ✗ (Error: {e})")


def test_actual_migration():
    """Test actual data migration."""
    print("\n=== Testing Actual Data Migration ===")

    # Sample v0.0.0 data
    v0_data = {
        "meta": {
            "id": "test_plan",
            "schema_version": "v0.0.0",
            "created_by": "test@example.com",
            "created_at": "2025-01-01T00:00:00Z"
        },
        "campaign": {
            "id": "test_campaign",
            "name": "Test Campaign",
            "objective": "awareness",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "budget": {
                "total": 10000,
                "by_channel": {"digital": 8000, "tv": 2000}
            },
            "target_audience": {
                "age_range": "25-54",
                "location": "United States",
                "interests": ["technology", "sports"]
            }
        },
        "lineitems": [
            {
                "id": "li_001",
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "budget": 5000,
                "channel": "digital",
                "platform": "Google",
                "publisher": "Google Ads",
                "creative_ids": ["creative_1", "creative_2"]
            }
        ]
    }

    migrator = SchemaMigrator()

    # Test different migration paths
    test_migrations = [
        ("v0.0.0", "v1.0.0"),
        ("v0.0.0", "1.0"),
    ]

    for from_v, to_v in test_migrations:
        try:
            # Update source version in data
            test_data = v0_data.copy()
            test_data["meta"]["schema_version"] = from_v

            result = migrator.migrate(test_data, from_v, to_v)

            print(f"  Migration {from_v} → {to_v}: ✓")
            print(f"    Result version: {result['meta']['schema_version']}")

            # Validate key transformations
            campaign = result["campaign"]
            if "budget_total" in campaign:
                print(f"    ✓ Budget transformed: {campaign['budget_total']}")
            if "audience_age_start" in campaign:
                print(f"    ✓ Age range parsed: {campaign['audience_age_start']}-{campaign['audience_age_end']}")

            lineitem = result["lineitems"][0] if result["lineitems"] else {}
            if "cost_total" in lineitem:
                print(f"    ✓ Line item budget→cost_total: {lineitem['cost_total']}")
            if "vehicle" in lineitem:
                print(f"    ✓ Platform→vehicle: {lineitem['vehicle']}")

        except Exception as e:
            print(f"  Migration {from_v} → {to_v}: ✗ (Error: {e})")


def test_supported_paths():
    """Test getting all supported migration paths."""
    print("\n=== Testing Supported Migration Paths ===")

    migrator = SchemaMigrator()
    paths = migrator.get_supported_migration_paths()

    for source, targets in paths.items():
        print(f"  {source} → {targets}")


if __name__ == "__main__":
    print("Testing Phase 5.2 Migration Implementation")
    print("=" * 50)

    try:
        test_migration_paths()
        test_migration_compatibility()
        test_actual_migration()
        test_supported_paths()

        print("\n" + "=" * 50)
        print("✓ All migration tests completed successfully!")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)