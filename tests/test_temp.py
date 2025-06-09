"""
Test script to verify Phase 3 migration implementation (pytest compatible).

This script tests the updated migration logic to ensure:
1. v0.0 versions are properly rejected
2. v1.0 → v2.0 migration works correctly
3. Legacy format migrations work
4. Error handling is proper
"""

import pytest
import json
import copy
from datetime import datetime
from decimal import Decimal

from mediaplanpy.schema.migration import SchemaMigrator
from mediaplanpy.exceptions import SchemaVersionError, SchemaMigrationError


@pytest.fixture
def migrator():
    """Create a SchemaMigrator instance for testing."""
    return SchemaMigrator()


@pytest.fixture
def sample_v1_mediaplan():
    """Create a sample v1.0 media plan for testing."""
    return {
        "meta": {
            "id": "test_plan_001",
            "schema_version": "1.0",
            "created_by": "john.doe@example.com",
            "created_at": "2024-01-01T10:00:00",
            "name": "Test Media Plan"
        },
        "campaign": {
            "id": "campaign_001",
            "name": "Test Campaign",
            "objective": "Brand Awareness",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "budget_total": 10000.00,
            "product_name": "Test Product"
        },
        "lineitems": [
            {
                "id": "lineitem_001",
                "name": "Test Line Item",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "cost_total": 5000.00,
                "channel": "digital",
                "vehicle": "facebook"
            }
        ]
    }


def test_v0_rejection_in_migrate(migrator, sample_v1_mediaplan):
    """Test that v0.0 versions are properly rejected in migrate method."""

    v0_versions = ["0.0", "v0.0.0", "0.1", "v0.0.1"]

    for version in v0_versions:
        with pytest.raises(SchemaVersionError) as exc_info:
            migrator.migrate(sample_v1_mediaplan, version, "2.0")

        # Verify the error message mentions v0.0 and SDK v1.x
        error_msg = str(exc_info.value)
        assert "v0.0.x" in error_msg
        assert "SDK v2.0" in error_msg
        assert "SDK v1.x" in error_msg


def test_v0_rejection_in_can_migrate(migrator):
    """Test that v0.0 versions are properly rejected in can_migrate method."""

    v0_versions = ["0.0", "v0.0.0", "0.1", "v0.0.1"]

    for version in v0_versions:
        result = migrator.can_migrate(version, "2.0")
        assert result is False, f"can_migrate({version}, '2.0') should return False"


def test_v0_rejection_in_find_migration_path(migrator):
    """Test that v0.0 versions are properly rejected in find_migration_path method."""

    v0_versions = ["0.0", "v0.0.0", "0.1", "v0.0.1"]

    for version in v0_versions:
        path = migrator.find_migration_path(version, "2.0")
        assert path == [], f"find_migration_path({version}, '2.0') should return empty list"


def test_v1_to_v2_migration_success(migrator, sample_v1_mediaplan):
    """Test successful v1.0 → v2.0 migration."""

    # Migrate to v2.0
    v2_plan = migrator.migrate(sample_v1_mediaplan, "1.0", "2.0")

    # Verify migration results
    assert v2_plan["meta"]["schema_version"] == "2.0"

    # Check created_by → created_by_name migration
    assert "created_by_name" in v2_plan["meta"]
    assert v2_plan["meta"]["created_by_name"] == "john.doe@example.com"

    # Check created_by_id was added as None
    assert "created_by_id" in v2_plan["meta"]
    assert v2_plan["meta"]["created_by_id"] is None

    # Check that original data structure is preserved
    assert v2_plan["campaign"]["name"] == "Test Campaign"
    assert len(v2_plan["lineitems"]) == 1
    assert v2_plan["lineitems"][0]["name"] == "Test Line Item"


def test_legacy_format_migration(migrator, sample_v1_mediaplan):
    """Test legacy format migration (v1.0.0 → 2.0)."""

    # Create sample v1.0.0 plan (legacy format)
    v1_legacy_plan = copy.deepcopy(sample_v1_mediaplan)
    v1_legacy_plan["meta"]["schema_version"] = "v1.0.0"  # Legacy format

    # Migrate to v2.0
    v2_plan = migrator.migrate(v1_legacy_plan, "v1.0.0", "2.0")

    # Verify results
    assert v2_plan["meta"]["schema_version"] == "2.0"
    assert "created_by_name" in v2_plan["meta"]
    assert v2_plan["meta"]["created_by_name"] == "john.doe@example.com"


def test_migration_paths_valid(migrator):
    """Test valid migration path finding."""

    # Test valid paths
    valid_paths = [
        ("1.0", "2.0"),
        ("v1.0.0", "2.0"),
    ]

    for from_v, to_v in valid_paths:
        path = migrator.find_migration_path(from_v, to_v)
        assert len(path) > 0, f"Path should be found for {from_v} → {to_v}"
        assert path[-1] == to_v, f"Path should end with target version {to_v}"


def test_migration_compatibility_valid(migrator):
    """Test migration compatibility validation for valid migrations."""

    # Test v1.0 → v2.0 compatibility
    compat = migrator.validate_migration_compatibility("1.0", "2.0")
    assert compat["compatible"] is True
    assert len(compat["errors"]) == 0


def test_migration_compatibility_v0_rejection(migrator):
    """Test migration compatibility validation rejects v0.0."""

    # Test v0.0 → v2.0 compatibility (should fail)
    compat = migrator.validate_migration_compatibility("v0.0.0", "2.0")
    assert compat["compatible"] is False
    assert len(compat["errors"]) > 0
    assert any("v0.0" in error for error in compat["errors"])


def test_migration_preserves_data_structure(migrator, sample_v1_mediaplan):
    """Test that migration preserves all data structure and doesn't lose information."""

    # Add some additional data to test preservation
    enhanced_plan = copy.deepcopy(sample_v1_mediaplan)
    enhanced_plan["campaign"]["budget_total"] = 15000.50
    enhanced_plan["campaign"]["audience_age_start"] = 25
    enhanced_plan["campaign"]["audience_age_end"] = 45
    enhanced_plan["lineitems"][0]["cost_media"] = 3000.00
    enhanced_plan["lineitems"][0]["metric_impressions"] = 100000.0

    # Migrate
    v2_plan = migrator.migrate(enhanced_plan, "1.0", "2.0")

    # Verify all data is preserved
    assert v2_plan["campaign"]["budget_total"] == 15000.50
    assert v2_plan["campaign"]["audience_age_start"] == 25
    assert v2_plan["campaign"]["audience_age_end"] == 45
    assert v2_plan["lineitems"][0]["cost_media"] == 3000.00
    assert v2_plan["lineitems"][0]["metric_impressions"] == 100000.0


def test_migration_handles_missing_created_by(migrator, sample_v1_mediaplan):
    """Test migration when created_by field is missing."""

    # Remove created_by field
    plan_without_created_by = copy.deepcopy(sample_v1_mediaplan)
    del plan_without_created_by["meta"]["created_by"]

    # Migrate
    v2_plan = migrator.migrate(plan_without_created_by, "1.0", "2.0")

    # Should have created_by_name with default value
    assert "created_by_name" in v2_plan["meta"]
    assert v2_plan["meta"]["created_by_name"] == "Unknown User"
    assert v2_plan["meta"]["created_by_id"] is None


def test_same_version_migration_updates_format(migrator, sample_v1_mediaplan):
    """Test that migrating to the same version still updates the version format."""

    # Create a plan with v1.0.0 format
    legacy_plan = copy.deepcopy(sample_v1_mediaplan)
    legacy_plan["meta"]["schema_version"] = "v1.0.0"

    # "Migrate" to same version but different format
    result = migrator.migrate(legacy_plan, "v1.0.0", "1.0")

    # Should update version format
    assert result["meta"]["schema_version"] == "1.0"


def test_migration_register_rejects_v0(migrator):
    """Test that registering v0.0 migrations is rejected."""

    def dummy_migration(data):
        return data

    # Should raise error when trying to register v0.0 migration
    with pytest.raises(SchemaVersionError) as exc_info:
        migrator.register_migration("0.0", "1.0", dummy_migration)

    error_msg = str(exc_info.value)
    assert "v0.0" in error_msg
    assert "SDK v2.0" in error_msg


# Integration test that runs all major functionality
def test_phase3_integration(migrator, sample_v1_mediaplan):
    """Integration test covering the main Phase 3 functionality."""

    print("\n=== Phase 3 Integration Test ===")

    # 1. Verify v0.0 rejection works
    with pytest.raises(SchemaVersionError):
        migrator.migrate(sample_v1_mediaplan, "0.0", "2.0")
    print("✅ v0.0 rejection working")

    # 2. Verify v1.0 → v2.0 migration works
    v2_plan = migrator.migrate(sample_v1_mediaplan, "1.0", "2.0")
    assert v2_plan["meta"]["schema_version"] == "2.0"
    assert v2_plan["meta"]["created_by_name"] == "john.doe@example.com"
    print("✅ v1.0 → v2.0 migration working")

    # 3. Verify legacy format works
    legacy_plan = copy.deepcopy(sample_v1_mediaplan)
    legacy_plan["meta"]["schema_version"] = "v1.0.0"
    v2_legacy = migrator.migrate(legacy_plan, "v1.0.0", "2.0")
    assert v2_legacy["meta"]["schema_version"] == "2.0"
    print("✅ Legacy format migration working")

    # 4. Verify path finding excludes v0.0
    assert migrator.find_migration_path("0.0", "2.0") == []
    assert len(migrator.find_migration_path("1.0", "2.0")) > 0
    print("✅ Path finding working correctly")

    print("✅ All Phase 3 functionality verified!")