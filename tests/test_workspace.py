"""
Tests for the workspace module with schema integration for v1.0.0.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path
from unittest import mock
import copy

# Import the WorkspaceManager and exceptions
from mediaplanpy.workspace import (
    WorkspaceManager,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)

from mediaplanpy.schema import SchemaRegistry, SchemaValidator, SchemaMigrator


# Fixture for a temporary workspace.json file
@pytest.fixture
def temp_workspace_file():
    """Create a temporary workspace.json file for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a valid workspace config
        workspace_config = {
            "workspace_name": "Test Workspace",
            "environment": "testing",
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": "${user_documents}/mediaplanpy_test",
                    "create_if_missing": True
                }
            },
            "schema_settings": {
                "preferred_version": "v1.0.0",  # Updated to v1.0.0
                "auto_migrate": False,
                "offline_mode": True,
                "repository_url": "https://example.com/schemas/",
                "local_cache_dir": "${user_documents}/mediaplanpy_test/schemas"
            },
            "database": {
                "enabled": False
            },
            "google_sheets": {
                "enabled": False
            },
            "logging": {
                "level": "DEBUG"
            }
        }

        # Write the config to a file
        config_path = Path(tmp_dir) / "workspace.json"
        with open(config_path, 'w') as f:
            json.dump(workspace_config, f)

        yield str(config_path)


# Fixture for an invalid workspace.json file
@pytest.fixture
def invalid_workspace_file():
    """Create an invalid workspace.json file for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create an invalid workspace config (missing required fields)
        workspace_config = {
            "workspace_name": "Invalid Workspace",
            # Missing "storage" field which is required
            "database": {
                "enabled": True,
                # Missing required host when enabled is True
            }
        }

        # Write the config to a file
        config_path = Path(tmp_dir) / "invalid_workspace.json"
        with open(config_path, 'w') as f:
            json.dump(workspace_config, f)

        yield str(config_path)


# Fixture for a sample media plan v1.0.0
@pytest.fixture
def sample_media_plan_v1():
    """Create a sample v1.0.0 media plan for testing."""
    return {
        "meta": {
            "id": "mediaplan_12345",
            "schema_version": "v1.0.0",
            "name": "Test Media Plan",
            "created_by": "test@example.com",
            "created_at": "2025-01-01T00:00:00Z"
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
                "id": "test_lineitem",
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


# Fixture for a sample media plan v0.0.0
@pytest.fixture
def sample_media_plan_v0():
    """Create a sample v0.0.0 media plan for testing."""
    return {
        "meta": {
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
                "total": 100000
            },
            "target_audience": {
                "age_range": "18-34",
                "location": "United States",
                "interests": ["sports", "technology"]
            }
        },
        "lineitems": [
            {
                "id": "test_lineitem",
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


# Test loading a workspace file
def test_load_workspace(temp_workspace_file):
    """Test loading a workspace file."""
    manager = WorkspaceManager(temp_workspace_file)
    config = manager.load()

    assert config is not None
    assert config["workspace_name"] == "Test Workspace"
    assert config["environment"] == "testing"
    assert config["storage"]["mode"] == "local"
    assert config["schema_settings"]["preferred_version"] == "v1.0.0"  # Updated


# Test validation of a valid workspace
def test_validate_valid_workspace(temp_workspace_file):
    """Test validation of a valid workspace file."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    # This should not raise an exception
    assert manager.validate() is True


# Test validation of an invalid workspace
def test_validate_invalid_workspace(invalid_workspace_file):
    """Test validation of an invalid workspace file."""
    manager = WorkspaceManager(invalid_workspace_file)
    manager.load()

    # This should raise a WorkspaceValidationError
    with pytest.raises(WorkspaceValidationError):
        manager.validate()


# Test workspace file not found
def test_workspace_not_found():
    """Test handling of a missing workspace file."""
    # Use a non-existent path
    manager = WorkspaceManager("/path/to/nonexistent/workspace.json")

    # This should raise a WorkspaceNotFoundError
    with pytest.raises(WorkspaceNotFoundError):
        manager.load()


# Test creating a default workspace
def test_create_default_workspace():
    """Test creation of a default workspace file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace_path = os.path.join(tmp_dir, "new_workspace.json")

        manager = WorkspaceManager()
        config = manager.create_default_workspace(workspace_path)

        # Check if file was created
        assert os.path.exists(workspace_path)

        # Check default values
        assert config["workspace_name"] == "Default"
        assert config["storage"]["mode"] == "local"
        assert config["database"]["enabled"] is False

        # Check schema settings - should now default to v1.0.0
        assert "schema_settings" in config
        assert config["schema_settings"]["preferred_version"] == "v1.0.0"  # Updated


# Test resolving path variables
def test_resolve_path_variables(temp_workspace_file):
    """Test resolving path variables in the workspace config."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    resolved_config = manager.get_resolved_config()

    # Check if ${user_documents} was resolved
    local_config = resolved_config["storage"]["local"]
    assert "${user_documents}" not in local_config["base_path"]

    # The exact path depends on the OS, so just check that it was changed
    if os.name == 'nt':  # Windows
        assert "Documents" in local_config["base_path"]
    elif os.name == 'posix':  # macOS/Linux
        assert "Documents" in local_config["base_path"] or "Home" in local_config["base_path"]


# Test getting specific config sections
def test_get_config_sections(temp_workspace_file):
    """Test getting specific sections of the workspace config."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    # Get storage config
    storage_config = manager.get_storage_config()
    assert storage_config["mode"] == "local"

    # Get database config
    db_config = manager.get_database_config()
    assert db_config["enabled"] is False

    # Get schema settings
    schema_settings = manager.get_schema_settings()
    assert schema_settings["preferred_version"] == "v1.0.0"  # Updated
    assert schema_settings["offline_mode"] is True


# Test creating workspace with nested directories
def test_create_workspace_nested_dirs():
    """Test creating a workspace file in nested directories that don't exist yet."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a path with nested directories that don't exist
        nested_path = os.path.join(tmp_dir, "a", "b", "c", "workspace.json")

        manager = WorkspaceManager()
        config = manager.create_default_workspace(nested_path)

        # Check if file was created
        assert os.path.exists(nested_path)


# Test schema registry integration
def test_schema_registry_integration(temp_workspace_file):
    """Test integration with schema registry."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    # Access schema registry
    registry = manager.schema_registry

    # Check if registry was initialized with workspace settings
    assert registry.repo_url == "https://example.com/schemas/"

    # Use OS-aware path checking
    local_cache_dir = str(registry.local_cache_dir)
    assert "mediaplanpy_test" in local_cache_dir
    assert "schemas" in local_cache_dir


# Test media plan validation
def test_validate_media_plan_v1(temp_workspace_file, sample_media_plan_v1):
    """Test validating a v1.0.0 media plan using workspace settings."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    # Make a deep copy to avoid modifications affecting other tests
    media_plan = copy.deepcopy(sample_media_plan_v1)

    # Mock the schema validator to avoid actual schema loading
    mock_validator = mock.Mock()
    mock_validator.validate.return_value = []  # No validation errors
    manager._schema_validator = mock_validator

    # Validate media plan
    errors = manager.validate_media_plan(media_plan)

    # Check validation was called with the correct version
    assert mock_validator.validate.called
    assert mock_validator.validate.call_args[0][0] == media_plan
    assert mock_validator.validate.call_args[0][1] == "v1.0.0"  # Default now v1.0.0

    # Check no errors were returned
    assert errors == []


# Test media plan validation with invalid v1.0.0 plan
def test_validate_media_plan_v1_invalid(temp_workspace_file, sample_media_plan_v1):
    """Test validating an invalid v1.0.0 media plan using workspace settings."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    # Make a deep copy and remove required field
    media_plan = copy.deepcopy(sample_media_plan_v1)
    del media_plan["meta"]["id"]  # Remove required field in v1.0.0

    # Mock the schema validator to return an error
    mock_validator = mock.Mock()
    mock_validator.validate.return_value = ["meta.id is required"]
    manager._schema_validator = mock_validator

    # Validate media plan
    errors = manager.validate_media_plan(media_plan)

    # Check validation was called
    assert mock_validator.validate.called

    # Check errors were returned
    assert len(errors) > 0
    assert "id" in errors[0]


# Test media plan migration
def test_migrate_media_plan_v0_to_v1(temp_workspace_file, sample_media_plan_v0):
    """Test migrating a v0.0.0 media plan to v1.0.0 using workspace settings."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    # Make a deep copy to avoid modifications affecting other tests
    media_plan = copy.deepcopy(sample_media_plan_v0)

    # Mock the schema migrator to simulate migration
    mock_migrator = mock.Mock()
    # Create a simulated migrated plan with v1.0.0 structure
    migrated_plan = {
        "meta": {
            "id": "mediaplan_" + media_plan["campaign"]["id"],  # Generated ID
            "schema_version": "v1.0.0",
            "name": media_plan["campaign"]["name"],  # Generated name
            "created_by": media_plan["meta"]["created_by"],
            "created_at": media_plan["meta"]["created_at"]
        },
        "campaign": {
            "id": media_plan["campaign"]["id"],
            "name": media_plan["campaign"]["name"],
            "objective": media_plan["campaign"]["objective"],
            "start_date": media_plan["campaign"]["start_date"],
            "end_date": media_plan["campaign"]["end_date"],
            "budget_total": media_plan["campaign"]["budget"]["total"],
            "audience_age_start": 18,
            "audience_age_end": 34,
            "location_type": "Country",
            "locations": ["United States"],
            "audience_interests": media_plan["campaign"]["target_audience"]["interests"]
        },
        "lineitems": [
            {
                "id": media_plan["lineitems"][0]["id"],
                "name": "Social Media Line Item",  # Generated name
                "start_date": media_plan["lineitems"][0]["start_date"],
                "end_date": media_plan["lineitems"][0]["end_date"],
                "cost_total": media_plan["lineitems"][0]["budget"],
                "channel": media_plan["lineitems"][0]["channel"],
                "vehicle": media_plan["lineitems"][0]["platform"],
                "partner": media_plan["lineitems"][0]["publisher"],
                "kpi": media_plan["lineitems"][0]["kpi"]
            }
        ]
    }
    mock_migrator.migrate.return_value = migrated_plan
    manager._schema_migrator = mock_migrator

    # Migrate media plan
    result = manager.migrate_media_plan(media_plan)

    # Check migration was called with the correct versions
    assert mock_migrator.migrate.called
    assert mock_migrator.migrate.call_args[0][0] == media_plan
    assert mock_migrator.migrate.call_args[0][1] == "v0.0.0"  # From version
    assert mock_migrator.migrate.call_args[0][2] == "v1.0.0"  # To version (from workspace settings)

    # Check result has v1.0.0 structure
    assert result["meta"]["schema_version"] == "v1.0.0"
    assert "id" in result["meta"]
    assert "name" in result["meta"]
    assert "budget_total" in result["campaign"]
    assert "budget" not in result["campaign"]
    assert "target_audience" not in result["campaign"]
    assert "audience_interests" in result["campaign"]
    assert "name" in result["lineitems"][0]
    assert "cost_total" in result["lineitems"][0]
    assert "budget" not in result["lineitems"][0]
    assert "vehicle" in result["lineitems"][0]
    assert "platform" not in result["lineitems"][0]


# Test getting storage backend
def test_get_storage_backend(temp_workspace_file):
    """Test getting the storage backend."""
    manager = WorkspaceManager(temp_workspace_file)
    manager.load()

    # Get storage backend
    backend = manager.get_storage_backend()

    # Verify it's created
    assert backend is not None
    assert hasattr(backend, 'base_path')