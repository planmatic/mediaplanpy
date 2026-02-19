"""
Unit tests for v2.0 to v3.0 schema migration.

Tests the SchemaMigrator with v2.0 media plans, including migration of:
- Campaign audience fields to target_audiences array
- Campaign location fields to target_locations array
- Dictionary custom_dimensions to lineitem_custom_dimensions
- Schema version updates
"""

import pytest
import json
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.schema import SchemaMigrator, SchemaValidator
from mediaplanpy.exceptions import SchemaVersionError, SchemaMigrationError


class TestBasicMigration:
    """Test basic v2.0 to v3.0 migration."""

    def test_migrate_v2_to_v3_version_update(self):
        """Test that schema version is updated from v2.0 to v3.0."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Check version was updated
        assert migrated["meta"]["schema_version"] == "3.0"

    def test_migrate_from_fixture(self, fixtures_dir):
        """Test migration using v2.0 fixture file."""
        # Load v2.0 fixture
        with open(fixtures_dir / "mediaplan_v2_migration.json") as f:
            mediaplan_v2 = json.load(f)

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Verify it's now v3.0
        assert migrated["meta"]["schema_version"] == "3.0"

        # Verify it validates as v3.0
        validator = SchemaValidator()
        errors = validator.validate(migrated, version="3.0")
        assert len(errors) == 0, f"Migrated plan has validation errors: {errors}"

    def test_migrate_same_version_no_op(self):
        """Test that migrating to same version is a no-op."""
        mediaplan = {
            "meta": {
                "id": "MP001",
                "schema_version": "v3.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan, "3.0", "3.0")

        # Should be unchanged (except possibly schema_version format)
        assert migrated["meta"]["schema_version"] == "3.0"
        assert migrated["campaign"]["id"] == "CAM001"


class TestAudienceMigration:
    """Test migration of audience fields from v2.0 to v3.0."""

    def test_migrate_full_audience_fields(self):
        """Test migration of complete audience fields to target_audiences array."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                # v2.0 audience fields
                "audience_name": "Adults 25-54",
                "audience_age_start": 25,
                "audience_age_end": 54,
                "audience_gender": "Any",
                "audience_interests": ["Technology", "Travel"]
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Check deprecated fields are removed
        campaign = migrated["campaign"]
        assert "audience_name" not in campaign
        assert "audience_age_start" not in campaign
        assert "audience_age_end" not in campaign
        assert "audience_gender" not in campaign
        assert "audience_interests" not in campaign

        # Check target_audiences array was created
        assert "target_audiences" in campaign
        assert len(campaign["target_audiences"]) == 1

        # Check fields were migrated correctly
        audience = campaign["target_audiences"][0]
        assert audience["name"] == "Adults 25-54"
        assert audience["demo_age_start"] == 25
        assert audience["demo_age_end"] == 54
        assert audience["demo_gender"] == "Any"
        assert "Technology, Travel" in audience["interest_attributes"]

    def test_migrate_audience_without_name(self):
        """Test that audience name is generated when missing."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                # v2.0 audience fields without name
                "audience_age_start": 35,
                "audience_age_end": 55,
                "audience_gender": "Male"
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Check generated name
        audience = migrated["campaign"]["target_audiences"][0]
        assert audience["name"] == "Males 35-55"

    def test_migrate_no_audience_fields(self):
        """Test that no target_audiences array is created when no audience fields present."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
                # No audience fields
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Should not create empty target_audiences
        assert "target_audiences" not in migrated["campaign"]


class TestLocationMigration:
    """Test migration of location fields from v2.0 to v3.0."""

    def test_migrate_location_fields(self):
        """Test migration of location fields to target_locations array."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                # v2.0 location fields
                "location_type": "State",
                "locations": ["California", "New York"]
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Check deprecated fields are removed
        campaign = migrated["campaign"]
        assert "location_type" not in campaign
        assert "locations" not in campaign

        # Check target_locations array was created
        assert "target_locations" in campaign
        assert len(campaign["target_locations"]) == 1

        # Check fields were migrated correctly
        location = campaign["target_locations"][0]
        assert location["name"] == "California and New York"
        assert location["location_type"] == "State"
        assert location["location_list"] == ["California", "New York"]

    def test_migrate_single_location_name(self):
        """Test that single location uses location name directly."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "locations": ["California"]
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Check single location name
        location = migrated["campaign"]["target_locations"][0]
        assert location["name"] == "California"

    def test_migrate_no_location_fields(self):
        """Test that no target_locations array is created when no locations present."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
                # No location fields
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Should not create empty target_locations
        assert "target_locations" not in migrated["campaign"]


class TestDictionaryMigration:
    """Test migration of dictionary fields from v2.0 to v3.0."""

    def test_migrate_dictionary_custom_dimensions(self):
        """Test that dictionary.custom_dimensions is renamed to lineitem_custom_dimensions."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": [],
            "dictionary": {
                "custom_dimensions": {
                    "dim_custom1": {"status": "enabled", "caption": "Placement Type"}
                }
            }
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Check old field is removed
        assert "custom_dimensions" not in migrated["dictionary"]

        # Check new field exists with same data
        assert "lineitem_custom_dimensions" in migrated["dictionary"]
        assert "dim_custom1" in migrated["dictionary"]["lineitem_custom_dimensions"]
        assert migrated["dictionary"]["lineitem_custom_dimensions"]["dim_custom1"]["status"] == "enabled"

    def test_migrate_no_dictionary(self):
        """Test migration when no dictionary is present."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
            # No dictionary
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Should work without errors
        assert "dictionary" not in migrated


class TestCompleteMigration:
    """Test complete migration scenarios with multiple features."""

    def test_migrate_complete_v2_plan(self):
        """Test migration of complete v2.0 plan with all deprecated fields."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Complete v2.0 Plan",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test Campaign",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                # v2.0 audience fields
                "audience_name": "Tech-Savvy Adults",
                "audience_age_start": 25,
                "audience_age_end": 54,
                "audience_gender": "Any",
                "audience_interests": ["Technology", "Gadgets"],
                # v2.0 location fields
                "location_type": "State",
                "locations": ["California", "New York", "Texas"]
            },
            "lineitems": [
                {
                    "id": "LI001",
                    "name": "Test Line Item",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-31",
                    "cost_total": 10000
                }
            ],
            "dictionary": {
                "custom_dimensions": {
                    "dim_custom1": {"status": "enabled", "caption": "Placement"},
                    "dim_custom2": {"status": "enabled", "caption": "Format"}
                }
            }
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Verify schema version
        assert migrated["meta"]["schema_version"] == "3.0"

        # Verify audience migration
        assert "target_audiences" in migrated["campaign"]
        assert migrated["campaign"]["target_audiences"][0]["name"] == "Tech-Savvy Adults"

        # Verify location migration
        assert "target_locations" in migrated["campaign"]
        assert "California" in migrated["campaign"]["target_locations"][0]["location_list"]

        # Verify dictionary migration
        assert "lineitem_custom_dimensions" in migrated["dictionary"]
        assert "custom_dimensions" not in migrated["dictionary"]

        # Verify no deprecated fields remain
        campaign = migrated["campaign"]
        assert "audience_name" not in campaign
        assert "locations" not in campaign

        # Verify migrated plan validates
        validator = SchemaValidator()
        errors = validator.validate(migrated, version="3.0")
        assert len(errors) == 0, f"Migrated plan has validation errors: {errors}"

    def test_migrate_preserves_v3_fields(self):
        """Test that v3.0 fields present in v2.0 plan are preserved."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z",
                "dim_custom1": "Project: Launch"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "kpi_name1": "CPM",
                "kpi_value1": 15.0
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # v3.0 fields should be preserved
        assert migrated["meta"]["dim_custom1"] == "Project: Launch"
        assert migrated["campaign"]["kpi_name1"] == "CPM"
        assert migrated["campaign"]["kpi_value1"] == 15.0


class TestMigrationEdgeCases:
    """Test edge cases and error handling in migration."""

    def test_migrate_invalid_source_version(self):
        """Test that migrating from v0.0 raises error."""
        mediaplan = {
            "meta": {"schema_version": "v0.0"},
            "campaign": {},
            "lineitems": []
        }

        migrator = SchemaMigrator()
        with pytest.raises(SchemaVersionError, match="no longer supported"):
            migrator.migrate(mediaplan, "0.0", "3.0")

    def test_migrate_missing_meta(self):
        """Test migration when meta section is missing."""
        mediaplan_v2 = {
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Should create meta with version
        assert "meta" in migrated
        assert migrated["meta"]["schema_version"] == "3.0"

    def test_migrate_original_unchanged(self):
        """Test that migration doesn't modify the original data."""
        original = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "audience_name": "Adults 25-54"
            },
            "lineitems": []
        }

        # Store original values
        original_version = original["meta"]["schema_version"]
        original_audience = original["campaign"]["audience_name"]

        migrator = SchemaMigrator()
        migrated = migrator.migrate(original, "2.0", "3.0")

        # Original should be unchanged
        assert original["meta"]["schema_version"] == original_version
        assert original["campaign"]["audience_name"] == original_audience


class TestMigrationMetadata:
    """Test that migration records metadata and preserves timestamps."""

    def test_migrate_records_custom_properties(self):
        """Test that migration adds schema_migration info to custom_properties."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z"
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Verify custom_properties contains migration metadata
        assert "custom_properties" in migrated["meta"]
        assert "schema_migration" in migrated["meta"]["custom_properties"]

        migration_info = migrated["meta"]["custom_properties"]["schema_migration"]
        assert migration_info["from_version"] == "2.0"
        assert migration_info["to_version"] == "3.0"
        assert "migrated_at" in migration_info

        # Verify migrated_at is a valid ISO timestamp
        migrated_at = datetime.fromisoformat(migration_info["migrated_at"])
        assert isinstance(migrated_at, datetime)

    def test_migrate_preserves_existing_custom_properties(self):
        """Test that migration preserves existing custom_properties entries."""
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": "2025-01-01T00:00:00Z",
                "custom_properties": {
                    "project_code": "PRJ-123",
                    "team": "Marketing"
                }
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # Verify existing custom_properties are preserved
        custom_props = migrated["meta"]["custom_properties"]
        assert custom_props["project_code"] == "PRJ-123"
        assert custom_props["team"] == "Marketing"

        # Verify migration metadata was also added
        assert "schema_migration" in custom_props
        assert custom_props["schema_migration"]["from_version"] == "2.0"

    def test_migrate_preserves_created_at(self):
        """Test that migration does not alter the created_at timestamp."""
        original_timestamp = "2025-01-01T00:00:00Z"
        mediaplan_v2 = {
            "meta": {
                "id": "MP001",
                "schema_version": "v2.0",
                "name": "Test",
                "created_by_name": "Test User",
                "created_at": original_timestamp
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": []
        }

        migrator = SchemaMigrator()
        migrated = migrator.migrate(mediaplan_v2, "2.0", "3.0")

        # created_at should be preserved unchanged
        assert migrated["meta"]["created_at"] == original_timestamp
