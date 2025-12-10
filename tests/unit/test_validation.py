"""
Unit tests for v3.0 schema validation.

Tests the SchemaValidator with v3.0 media plans, including validation of:
- Array structures (target_audiences, target_locations, metric_formulas)
- Deprecated field warnings
- Business logic validation
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.schema import SchemaValidator
from mediaplanpy.exceptions import SchemaVersionError, ValidationError


class TestSchemaValidatorV3Basic:
    """Test basic v3.0 schema validation."""

    def test_validate_v3_minimal_mediaplan_valid(self, fixtures_dir):
        """Test validation of minimal valid v3.0 media plan."""
        import json

        # Load fixture
        with open(fixtures_dir / "mediaplan_v3_minimal.json") as f:
            mediaplan = json.load(f)

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have no errors
        assert len(errors) == 0

    def test_validate_v3_full_mediaplan_valid(self, fixtures_dir):
        """Test validation of complete valid v3.0 media plan."""
        import json

        # Load fixture
        with open(fixtures_dir / "mediaplan_v3_full.json") as f:
            mediaplan = json.load(f)

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have no errors
        assert len(errors) == 0

    def test_validate_detects_version_from_meta(self, fixtures_dir):
        """Test that validator auto-detects v3.0 version from meta."""
        import json

        # Load fixture
        with open(fixtures_dir / "mediaplan_v3_minimal.json") as f:
            mediaplan = json.load(f)

        validator = SchemaValidator()
        # Don't specify version - should auto-detect from meta.schema_version
        errors = validator.validate(mediaplan)

        assert len(errors) == 0


class TestV3ArrayStructureValidation:
    """Test validation of v3.0 array structures."""

    def test_target_audiences_array_valid(self):
        """Test validation of valid target_audiences array."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "target_audiences": [
                    {
                        "name": "Adults 25-54",
                        "demo_age_start": 25,
                        "demo_age_end": 54
                    }
                ]
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should not have errors about array structure
        array_errors = [e for e in errors if "target_audiences" in e and "array" in e.lower()]
        assert len(array_errors) == 0

    def test_target_audiences_missing_name(self):
        """Test that missing required 'name' field is detected."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "target_audiences": [
                    {
                        "demo_age_start": 25,
                        "demo_age_end": 54
                        # Missing required 'name' field
                    }
                ]
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have error about missing name
        name_errors = [e for e in errors if "name" in e.lower() and "target_audiences" in e]
        assert len(name_errors) > 0

    def test_target_audiences_invalid_age_range(self):
        """Test that invalid age range (start > end) is detected."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "target_audiences": [
                    {
                        "name": "Invalid",
                        "demo_age_start": 50,
                        "demo_age_end": 25  # Invalid: start > end
                    }
                ]
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have error about age range
        age_errors = [e for e in errors if "age" in e.lower() and (">" in e or "must be" in e)]
        assert len(age_errors) > 0

    def test_target_locations_valid(self):
        """Test validation of valid target_locations array."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "target_locations": [
                    {
                        "name": "California",
                        "location_type": "State",
                        "population_percent": 0.12
                    }
                ]
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should not have errors about array structure
        array_errors = [e for e in errors if "target_locations" in e and "array" in e.lower()]
        assert len(array_errors) == 0

    def test_target_locations_invalid_population_percent(self):
        """Test that invalid population_percent (> 1) is detected."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "target_locations": [
                    {
                        "name": "Invalid",
                        "population_percent": 1.5  # Invalid: > 1
                    }
                ]
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have error about population_percent
        pop_errors = [e for e in errors if "population_percent" in e.lower()]
        assert len(pop_errors) > 0

    def test_metric_formulas_valid(self):
        """Test validation of valid metric_formulas."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": [
                {
                    "id": "LI001",
                    "name": "Test",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-31",
                    "cost_total": 10000,
                    "metric_formulas": {
                        "cpm": {
                            "formula_type": "cost_per_unit",
                            "base_metric": "cost_total"
                        }
                    }
                }
            ]
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should not have errors about metric_formulas
        formula_errors = [e for e in errors if "metric_formulas" in e]
        assert len(formula_errors) == 0

    def test_metric_formulas_missing_formula_type(self):
        """Test that missing formula_type is detected."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": [
                {
                    "id": "LI001",
                    "name": "Test",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-31",
                    "cost_total": 10000,
                    "metric_formulas": {
                        "cpm": {
                            "base_metric": "cost_total"
                            # Missing required formula_type
                        }
                    }
                }
            ]
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have error about missing formula_type
        formula_errors = [e for e in errors if "formula_type" in e.lower() and "missing" in e.lower()]
        assert len(formula_errors) > 0


class TestDeprecatedFieldWarnings:
    """Test validation warnings for deprecated v2.0 fields."""

    def test_deprecated_audience_fields_warning(self):
        """Test that using deprecated audience fields generates warning."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                # Using deprecated v2.0 fields
                "audience_name": "Adults 25-54",
                "audience_age_start": 25,
                "audience_age_end": 54
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have warning about deprecated audience fields
        warnings = [e for e in errors if "deprecated" in e.lower() and "audience" in e.lower()]
        assert len(warnings) > 0

    def test_deprecated_location_fields_warning(self):
        """Test that using deprecated location fields generates warning."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                # Using deprecated v2.0 fields
                "location_type": "State",
                "locations": ["California"]
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have warning about deprecated location fields
        warnings = [e for e in errors if "deprecated" in e.lower() and "location" in e.lower()]
        assert len(warnings) > 0

    def test_dictionary_custom_dimensions_warning(self):
        """Test warning for old dictionary field name."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000
            },
            "lineitems": [],
            "dictionary": {
                # Using old field name instead of lineitem_custom_dimensions
                "custom_dimensions": {
                    "dim_custom1": {"status": "enabled", "caption": "Test"}
                }
            }
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have warning about dictionary field rename
        warnings = [e for e in errors if "custom_dimensions" in e.lower() and "lineitem" in e.lower()]
        assert len(warnings) > 0


class TestComprehensiveValidation:
    """Test comprehensive validation with categorized results."""

    def test_comprehensive_validation_v3(self, fixtures_dir):
        """Test comprehensive validation returns categorized results."""
        import json

        # Load fixture
        with open(fixtures_dir / "mediaplan_v3_full.json") as f:
            mediaplan = json.load(f)

        validator = SchemaValidator()
        result = validator.validate_comprehensive(mediaplan, version="3.0")

        # Should have result structure
        assert "errors" in result
        assert "warnings" in result
        assert "info" in result

        # Should have info about v3.0 features
        assert any("v3.0" in info or "target_audiences" in info for info in result["info"])

    def test_comprehensive_validation_shows_array_counts(self):
        """Test that comprehensive validation reports array counts in info."""
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
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "target_audiences": [
                    {"name": "Audience 1"},
                    {"name": "Audience 2"}
                ],
                "target_locations": [
                    {"name": "Location 1"}
                ]
            },
            "lineitems": []
        }

        validator = SchemaValidator()
        result = validator.validate_comprehensive(mediaplan, version="3.0")

        # Should mention audience and location counts
        info_str = " ".join(result["info"])
        assert "2 audience" in info_str or "target_audiences" in info_str
        assert "1 location" in info_str or "target_locations" in info_str


class TestBusinessLogicValidation:
    """Test business logic validation for v3.0."""

    def test_date_consistency_validation(self):
        """Test that lineitem dates must be within campaign dates."""
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
            "lineitems": [
                {
                    "id": "LI001",
                    "name": "Test",
                    "start_date": "2024-12-01",  # Before campaign start
                    "end_date": "2025-03-31",
                    "cost_total": 10000
                }
            ]
        }

        validator = SchemaValidator()
        errors = validator.validate(mediaplan, version="3.0")

        # Should have error about date consistency (looks for "before" or "after" in error message)
        date_errors = [e for e in errors if "before" in e.lower() or "after" in e.lower()]
        assert len(date_errors) > 0
