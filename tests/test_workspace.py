"""
Tests for the workspace module.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path

# Import the WorkspaceManager and exceptions
# Assuming the workspace module is in src/mediaplanpy/workspace/__init__.py
from mediaplanpy.workspace import (
    WorkspaceManager,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)


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


# Test loading a workspace file
def test_load_workspace(temp_workspace_file):
    """Test loading a workspace file."""
    manager = WorkspaceManager(temp_workspace_file)
    config = manager.load()

    assert config is not None
    assert config["workspace_name"] == "Test Workspace"
    assert config["environment"] == "testing"
    assert config["storage"]["mode"] == "local"


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