"""
Tests for the schema module.
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
        "current": "v0.0.0",
        "supported": ["v0.0.0", "v0.9.0"],  # Adding v0.9.0 for migration tests
        "deprecated": [],
        "description": "Test schema version configuration"
    }
    return mock_resp


@pytest.fixture
def mock_schema_response():
    """Create a mock schema response for requests."""
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Test Schema",
        "type": "object",
        "required": ["meta"],
        "properties": {
            "meta": {
                "type": "object",
                "required": ["schema_version"],
                "properties": {
                    "schema_version": {"type": "string"}
                }
            }
        }
    }
    return mock_resp


@pytest.fixture
def temp_schema_dir():
    """Create a temporary directory for schema files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


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

        assert versions["current"] == "v0.0.0"
        assert "v0.0.0" in versions["supported"]
        assert mock_get.called

        # Test caching behavior
        _ = registry.load_versions_info()  # Should use cached data
        assert mock_get.call_count == 1  # Should not call again

    def test_get_current_version(self, mock_response):
        """Test getting current version."""
        with mock.patch.object(SchemaRegistry, 'load_versions_info', return_value=mock_response.json()):
            registry = SchemaRegistry()
            assert registry.get_current_version() == "v0.0.0"

    def test_get_supported_versions(self, mock_response):
        """Test getting supported versions."""
        with mock.patch.object(SchemaRegistry, 'load_versions_info', return_value=mock_response.json()):
            registry = SchemaRegistry()
            assert registry.get_supported_versions() == ["v0.0.0", "v0.9.0"]

    def test_is_version_supported(self, mock_response):
        """Test checking if a version is supported."""
        with mock.patch.object(SchemaRegistry, 'load_versions_info', return_value=mock_response.json()):
            registry = SchemaRegistry()
            assert registry.is_version_supported("v0.0.0")
            assert registry.is_version_supported("v0.9.0")
            assert not registry.is_version_supported("v0.8.0")

    @mock.patch('requests.get')
    def test_load_schema(self, mock_get, mock_schema_response, temp_schema_dir):
        """Test loading a schema."""
        mock_get.return_value = mock_schema_response

        # Mock the is_version_supported method to always return True
        # This avoids the extra call that was causing the test to fail
        with mock.patch.object(SchemaRegistry, 'is_version_supported', return_value=True):
            registry = SchemaRegistry(local_cache_dir=temp_schema_dir)
            schema = registry.load_schema(version="v0.0.0", schema_name="mediaplan.schema.json", force_refresh=True)

            assert schema["title"] == "Test Schema"
            assert mock_get.called

            # Test caching behavior
            _ = registry.load_schema(version="v0.0.0", schema_name="mediaplan.schema.json")  # Should use cached data
            assert mock_get.call_count == 1  # Should not call again


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

    def test_validate_success(self):
        """Test successful validation."""
        media_plan = {
            "meta": {
                "schema_version": "v0.0.0"
            }
        }

        # Mock the registry and validation
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True
        mock_registry.load_schema.return_value = {
            "type": "object",
            "required": ["meta"],
            "properties": {
                "meta": {
                    "type": "object",
                    "properties": {
                        "schema_version": {"type": "string"}
                    }
                }
            }
        }
        mock_registry.get_schema_path.return_value = "mock://schema/path"

        validator = SchemaValidator(registry=mock_registry)
        errors = validator.validate(media_plan)

        assert len(errors) == 0
        assert mock_registry.load_schema.called

    def test_validate_failure(self):
        """Test validation failure."""
        media_plan = {
            "meta": {
                # Missing required schema_version
            }
        }

        # Mock the registry and validation
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True
        mock_registry.load_schema.return_value = {
            "type": "object",
            "required": ["meta"],
            "properties": {
                "meta": {
                    "type": "object",
                    "required": ["schema_version"],
                    "properties": {
                        "schema_version": {"type": "string"}
                    }
                }
            }
        }
        mock_registry.get_schema_path.return_value = "mock://schema/path"

        validator = SchemaValidator(registry=mock_registry)
        errors = validator.validate(media_plan)

        assert len(errors) > 0
        assert "schema_version" in errors[0]


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

    def test_register_migration(self):
        """Test registering a migration path."""
        migrator = SchemaMigrator()

        # Define a simple migration function
        def migration_func(data):
            return data

        # Register it
        migrator.register_migration("v0.9.0", "v0.0.0", migration_func)

        # Check if it was registered
        assert migrator.can_migrate("v0.9.0", "v0.0.0")
        assert not migrator.can_migrate("v0.0.0", "v1.1.0")

    def test_find_migration_path_direct(self):
        """Test finding a direct migration path."""
        migrator = SchemaMigrator()

        # Register a direct path
        migrator.register_migration("v0.9.0", "v0.0.0", lambda x: x)

        # Find path
        path = migrator.find_migration_path("v0.9.0", "v0.0.0")
        assert path == ["v0.0.0"]

    def test_find_migration_path_indirect(self):
        """Test finding an indirect migration path."""
        migrator = SchemaMigrator()

        # Register multiple paths
        migrator.register_migration("v0.9.0", "v0.9.5", lambda x: x)
        migrator.register_migration("v0.9.5", "v0.0.0", lambda x: x)

        # Find path
        path = migrator.find_migration_path("v0.9.0", "v0.0.0")
        assert path == ["v0.9.5", "v0.0.0"]

    def test_migrate_success(self):
        """Test successful migration."""
        # Create a migrator with mocked registry
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True  # All versions supported
        migrator = SchemaMigrator(registry=mock_registry)

        # Define a simple migration function
        def migration_func(data):
            result = data.copy()
            result["migrated"] = True
            return result

        # Register it
        migrator.register_migration("v0.9.0", "v0.0.0", migration_func)

        # Migrate
        media_plan = {
            "meta": {
                "schema_version": "v0.9.0"
            }
        }

        result = migrator.migrate(media_plan, "v0.9.0", "v0.0.0")

        assert result["migrated"] is True
        assert result["meta"]["schema_version"] == "v0.0.0"

    def test_migrate_no_path(self):
        """Test migration with no path."""
        # Create a migrator with mocked registry
        mock_registry = mock.Mock()
        mock_registry.is_version_supported.return_value = True  # All versions supported
        migrator = SchemaMigrator(registry=mock_registry)

        # Migrate with no registered paths
        media_plan = {
            "meta": {
                "schema_version": "v0.9.0"
            }
        }

        with pytest.raises(SchemaError):
            migrator.migrate(media_plan, "v0.9.0", "v0.0.0")


class TestModuleFunctions:
    """Tests for module-level functions."""

    @mock.patch('mediaplanpy.schema.default_registry.get_current_version')
    def test_get_current_version(self, mock_get):
        """Test get_current_version function."""
        mock_get.return_value = "v0.0.0"

        version = get_current_version()
        assert version == "v0.0.0"
        assert mock_get.called

    @mock.patch('mediaplanpy.schema.default_registry.get_supported_versions')
    def test_get_supported_versions(self, mock_get):
        """Test get_supported_versions function."""
        mock_get.return_value = ["v0.0.0"]

        versions = get_supported_versions()
        assert versions == ["v0.0.0"]
        assert mock_get.called

    @mock.patch('mediaplanpy.schema.default_validator.validate')
    def test_validate(self, mock_validate):
        """Test validate function."""
        mock_validate.return_value = []

        media_plan = {"meta": {"schema_version": "v0.0.0"}}
        errors = validate(media_plan)

        assert errors == []
        assert mock_validate.called