"""
Tests for the schema module with v1.0.0 schema support.
"""
import os
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import requests

from mediaplanpy.schema import (
    SchemaRegistry,
    SchemaValidator,
    SchemaMigrator,
    get_current_version,
    get_supported_versions,
    validate
)
from mediaplanpy.exceptions import SchemaError, ValidationError, SchemaVersionError


@pytest.fixture
def mock_response():
    """Create a mock response for requests."""
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current": "v1.0.0",
        "supported": ["v0.0.0", "v1.0.0"],
        "deprecated": [],
        "description": "Test schema version configuration"
    }
    return mock_resp


@pytest.fixture
def mock_schema_response_v0():
    """Create a mock schema response for v0.0.0 schema."""
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Media Plan v0.0.0",
        "type": "object",
        "required": ["meta", "campaign", "lineitems"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["schema_version", "created_by", "created_at"],
                "properties": {
                    "schema_version": {"type": "string"},
                    "created_by": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "comments": {"type": "string"}
                }
            },
            "campaign": {
                "type": "object"
            },
            "lineitems": {
                "type": "array",
                "items": {"type": "object"}
            }
        }
    }
    return mock_resp


@pytest.fixture
def mock_schema_response_v1():
    """Create a mock schema response for v1.0.0 schema."""
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Media Plan v1.0.0",
        "type": "object",
        "required": ["meta", "campaign", "lineitems"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["id", "schema_version", "created_by", "created_at"],
                "properties": {
                    "id": {"type": "string"},
                    "schema_version": {"type": "string"},
                    "name": {"type": "string"},
                    "created_by": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "comments": {"type": "string"}
                }
            },
            "campaign": {
                "type": "object"
            },
            "lineitems": {
                "type": "array",
                "items": {"type": "object"}
            }
        }
    }
    return mock_resp


@pytest.fixture
def temp_schema_dir():
    """Create a temporary directory for schema files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def sample_v0_mediaplan():
    """Create a sample v0.0.0 media plan for testing."""
    return {
        "meta": {
            "schema_version": "v0.0.0",
            "created_by": "test@example.com",
            "created_at": "2025-01-01T00:00:00Z",
            "comments": "Test comment"
        },
        "campaign": {
            "id": "test_campaign",
            "name": "Test Campaign",
            "objective": "awareness",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "budget": {
                "total": 100000,
                "by_channel": {
                    "social": 50000,
                    "display": 50000
                }
            },
            "target_audience": {
                "age_range": "18-34",
                "location": "United States",
                "interests": ["sports", "technology"]
            }
        },
        "lineitems": [
            {
                "id": "line_item_1",
                "channel": "social",
                "platform": "Facebook",
                "publisher": "Meta",
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "budget": 50000,
                "kpi": "CPM"
            }
        ]
    }


@pytest.fixture
def sample_v1_mediaplan():
    """Create a sample v1.0.0 media plan for testing."""
    return {
        "meta": {
            "id": "mediaplan_12345",
            "schema_version": "v1.0.0",
            "name": "Test Media Plan",
            "created_by": "test@example.com",
            "created_at": "2025-01-01T00:00:00Z",
            "comments": "Test comment"
        },
        "campaign": {
            "id": "test_campaign",
            "name": "Test Campaign",
            "objective": "awareness",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "budget_total": 100000,
            "audience_age_start": 18,
            "audience_age_end": 34,
            "audience_gender": "Any",
            "audience_interests": ["sports", "technology"],
            "location_type": "Country",
            "locations": ["United States"]
        },
        "lineitems": [
            {
                "id": "line_item_1",
                "name": "Social Media Line Item",
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "cost_total": 50000,
                "channel": "social",
                "vehicle": "Facebook",
                "partner": "Meta",
                "kpi": "CPM"
            }
        ]
    }


class TestSchemaRegistry:
    """Tests for the SchemaRegistry class."""

    def test_init_default(self):
        """Test initializing with default values."""
        registry = SchemaRegistry()
        assert registry.repo_url == SchemaRegistry.DEFAULT_REPO_URL
        assert registry.local_cache_dir.exists()

    def test_init_custom(self, temp_schema_dir):
        """Test initializing with custom values."""
        custom_url = "https://example.com/repo/"
        registry = SchemaRegistry(repo_url=custom_url, local_cache_dir=temp_schema_dir)
        assert registry.repo_url == custom_url
        assert str(registry.local_cache_dir) == temp_schema_dir

    @mock.patch('requests.get')
    def test_load_versions_info(self, mock_get, mock_response, temp_schema_dir):
        """Test loading version information."""
        mock_get.return_value = mock_response

        registry = SchemaRegistry(local_cache_dir=temp_schema_dir)
        versions = registry.load_versions_info(force_refresh=True)

        assert versions["current"] == "v1.0.0"  # Now v1.0.0 is the current version
        assert "v0.0.0" in versions["supported"]
        assert "v1.0.0" in versions["supported"]
        assert mock_get.called

        # Test caching behavior
        _ = registry.load_versions_info()  # Should use cached data
        assert mock_get.call_count == 1  # Should not call again

    def test_get_current_version(self, mock_response):
        """Test getting current version."""
        with mock.patch.object(SchemaRegistry, 'load_versions_info', return_value=mock_response.json()):
            registry = SchemaRegistry()
            assert registry.get_current_version() == "v1.0.0"  # Now v1.0.0

    def test_get_supported_versions(self, mock_response):
        """Test getting supported versions."""
        with mock.patch.object(SchemaRegistry, 'load_versions_info', return_value=mock_response.json()):
            registry = SchemaRegistry()
            assert registry.get_supported_versions() == ["v0.0.0", "v1.0.0"]

    def test_is_version_supported(self, mock_response):
        """Test checking if a version is supported."""
        with mock.patch.object(SchemaRegistry, 'load_versions_info', return_value=mock_response.json()):
            registry = SchemaRegistry()
            assert registry.is_version_supported("v0.0.0")
            assert registry.is_version_supported("v1.0.0")
            assert not registry.is_version_supported("v0.9.0")

    @mock.patch('requests.get')
    def test_load_schema_v0(self, mock_get, mock_schema_response_v0, temp_schema_dir):
        """Test loading a v0.0.0 schema."""
        mock_get.return_value = mock_schema_response_v0

        # Mock the is_version_supported method to always return True
        with mock.patch.object(SchemaRegistry, 'is_version_supported', return_value=True):
            registry = SchemaRegistry(local_cache_dir=temp_schema_dir)
            schema = registry.load_schema(version="v0.0.0", schema_name="mediaplan.schema.json", force_refresh=True)

            assert schema["title"] == "Media Plan v0.0.0"
            assert mock_get.called

    @mock.patch('requests.get')
    def test_load_schema_v1(self, mock_get, mock_schema_response_v1, temp_schema_dir):
        """Test loading a v1.0.0 schema."""
        mock_get.return_value = mock_schema_response_v1

        # Mock the is_version_supported method to always return True
        with mock.patch.object(SchemaRegistry, 'is_version_supported', return_value=True):
            registry = SchemaRegistry(local_cache_dir=temp_schema_dir)
            schema = registry.load_schema(version="v1.0.0", schema_name="mediaplan.schema.json", force_refresh=True)

            assert schema["title"] == "Media Plan v1.0.0"
            assert "id" in schema["properties"]["meta"]["required"]  # Check for new required field
            assert mock_get.called


class TestSchemaValidator:
    """Tests for the SchemaValidator class."""

    def test_init_default(self):
        """Test initializing with default values."""
        validator = SchemaValidator()
        assert isinstance(validator.registry, SchemaRegistry)

    def test_init_custom_registry(self):
        """Test initializing with a custom registry."""
        registry = SchemaRegistry()
        validator = SchemaValidator(registry=registry)
        assert validator.registry == registry

    def test_validate_success_v0(self, sample_v0_mediaplan):
        """Test successful validation of v0.0.0 schema."""
        # Mock the registry and validation for v0.0.0
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True
        mock_registry.load_schema.return_value = {
            "type": "object",
            "required": ["meta", "campaign", "lineitems"],
            "properties": {
                "meta": {
                    "type": "object",
                    "required": ["schema_version", "created_by", "created_at"],
                    "properties": {
                        "schema_version": {"type": "string"}
                    }
                }
            }
        }
        mock_registry.get_schema_path.return_value = "mock://schema/path"

        validator = SchemaValidator(registry=mock_registry)
        errors = validator.validate(sample_v0_mediaplan, "v0.0.0")

        assert len(errors) == 0
        assert mock_registry.load_schema.called

    def test_validate_success_v1(self, sample_v1_mediaplan):
        """Test successful validation of v1.0.0 schema."""
        # Mock the registry and validation for v1.0.0
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True
        mock_registry.load_schema.return_value = {
            "type": "object",
            "required": ["meta", "campaign", "lineitems"],
            "properties": {
                "meta": {
                    "type": "object",
                    "required": ["id", "schema_version", "created_by", "created_at"],
                    "properties": {
                        "id": {"type": "string"},
                        "schema_version": {"type": "string"}
                    }
                }
            }
        }
        mock_registry.get_schema_path.return_value = "mock://schema/path"

        validator = SchemaValidator(registry=mock_registry)
        errors = validator.validate(sample_v1_mediaplan, "v1.0.0")

        assert len(errors) == 0
        assert mock_registry.load_schema.called

    def test_validate_failure_v1_missing_id(self, sample_v1_mediaplan):
        """Test validation failure for v1.0.0 schema with missing id."""
        # Create invalid sample by removing required id field
        invalid_sample = sample_v1_mediaplan.copy()
        invalid_meta = invalid_sample["meta"].copy()
        del invalid_meta["id"]
        invalid_sample["meta"] = invalid_meta

        # Mock the registry and validation
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True
        mock_registry.load_schema.return_value = {
            "type": "object",
            "required": ["meta"],
            "properties": {
                "meta": {
                    "type": "object",
                    "required": ["id", "schema_version"],
                    "properties": {
                        "id": {"type": "string"},
                        "schema_version": {"type": "string"}
                    }
                }
            }
        }
        mock_registry.get_schema_path.return_value = "mock://schema/path"

        validator = SchemaValidator(registry=mock_registry)
        errors = validator.validate(invalid_sample, "v1.0.0")

        assert len(errors) > 0
        assert "id" in errors[0]


class TestSchemaMigrator:
    """Tests for the SchemaMigrator class."""

    def test_init_default(self):
        """Test initializing with default values."""
        migrator = SchemaMigrator()
        assert isinstance(migrator.registry, SchemaRegistry)

    def test_init_custom_registry(self):
        """Test initializing with a custom registry."""
        registry = SchemaRegistry()
        migrator = SchemaMigrator(registry=registry)
        assert migrator.registry == registry

    def test_default_migrations_v0_to_v1(self):
        """Test that default migrations include v0.0.0 to v1.0.0."""
        # Create a migrator with mocked registry
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True
        migrator = SchemaMigrator(registry=mock_registry)

        # Check migration path exists
        assert migrator.can_migrate("v0.0.0", "v1.0.0")

    def test_migrate_v0_to_v1(self, sample_v0_mediaplan):
        """Test migration from v0.0.0 to v1.0.0."""
        # Create a migrator with mocked registry
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True
        migrator = SchemaMigrator(registry=mock_registry)

        # Migrate
        result = migrator.migrate(sample_v0_mediaplan, "v0.0.0", "v1.0.0")

        # Verify v1.0.0 structure
        assert result["meta"]["schema_version"] == "v1.0.0"
        assert "id" in result["meta"]  # Should have generated an ID
        assert "budget_total" in result["campaign"]  # Should convert budget to budget_total
        assert "budget" not in result["campaign"]  # Should remove old budget object

        # Verify line item conversion
        line_item = result["lineitems"][0]
        assert "cost_total" in line_item  # Should rename budget to cost_total
        assert "budget" not in line_item  # Should remove old budget
        assert "name" in line_item  # Should add a name
        assert "vehicle" in line_item  # Should convert platform to vehicle
        assert "platform" not in line_item  # Should remove old platform
        assert "partner" in line_item  # Should convert publisher to partner
        assert "publisher" not in line_item  # Should remove old publisher

    def test_find_migration_path_direct(self):
        """Test finding a direct migration path."""
        migrator = SchemaMigrator()

        # Direct path from v0.0.0 to v1.0.0 should exist in default migrations
        path = migrator.find_migration_path("v0.0.0", "v1.0.0")
        assert path == ["v1.0.0"]

    def test_migrate_no_path(self):
        """Test migration with no path."""
        # Create a migrator with mocked registry
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True

        # Create a fresh migrator without default registrations
        migrator = SchemaMigrator(registry=mock_registry)
        migrator.migration_paths = {}  # Clear default registrations

        # Migrate with no registered paths
        media_plan = {
            "meta": {
                "schema_version": "v0.9.0"
            }
        }

        with pytest.raises(SchemaError):
            migrator.migrate(media_plan, "v0.9.0", "v1.0.0")


class TestModuleFunctions:
    """Tests for module-level functions."""

    @mock.patch('mediaplanpy.schema.default_registry.get_current_version')
    def test_get_current_version(self, mock_get):
        """Test get_current_version function."""
        mock_get.return_value = "v1.0.0"  # Now v1.0.0

        version = get_current_version()
        assert version == "v1.0.0"
        assert mock_get.called

    @mock.patch('mediaplanpy.schema.default_registry.get_supported_versions')
    def test_get_supported_versions(self, mock_get):
        """Test get_supported_versions function."""
        mock_get.return_value = ["v0.0.0", "v1.0.0"]

        versions = get_supported_versions()
        assert versions == ["v0.0.0", "v1.0.0"]
        assert mock_get.called

    @mock.patch('mediaplanpy.schema.default_validator.validate')
    def test_validate(self, mock_validate):
        """Test validate function."""
        mock_validate.return_value = []

        media_plan = {"meta": {"schema_version": "v1.0.0", "id": "mediaplan_12345"}}
        errors = validate(media_plan)

        assert errors == []
        assert mock_validate.called