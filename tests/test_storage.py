"""
Tests for the storage module with v1.0.0 schema support.
"""
import os
import json
import tempfile
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import pytest
from unittest import mock

from mediaplanpy.exceptions import StorageError, FileReadError, FileWriteError
from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.models import MediaPlan, Meta, Campaign, Budget, LineItem
from mediaplanpy.storage import (
    get_storage_backend,
    get_format_handler_instance,
    read_mediaplan,
    write_mediaplan
)
from mediaplanpy.storage.formats import JsonFormatHandler
from mediaplanpy.storage.local import LocalStorageBackend


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def temp_workspace_file(temp_storage_dir):
    """Create a temporary workspace configuration file."""
    # Create a valid workspace config
    workspace_config = {
        "workspace_name": "Test Storage Workspace",
        "environment": "testing",
        "storage": {
            "mode": "local",
            "local": {
                "base_path": temp_storage_dir,
                "create_if_missing": True
            }
        },
        "schema_settings": {
            "preferred_version": "v1.0.0",  # Updated to v1.0.0
            "auto_migrate": False,
            "offline_mode": True
        },
        "database": {
            "enabled": False
        },
        "logging": {
            "level": "DEBUG"
        }
    }

    # Write the config to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as tmp:
        json.dump(workspace_config, tmp)
        tmp_path = tmp.name

    yield tmp_path

    # Clean up
    os.unlink(tmp_path)


@pytest.fixture
def sample_mediaplan_v1():
    """Create a sample media plan (v1.0.0) for testing."""
    return MediaPlan(
        meta=Meta(
            id="mediaplan_12345",
            schema_version="v1.0.0",
            created_by="test@example.com",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            name="Test Media Plan",
            comments="Test media plan"
        ),
        campaign=Campaign(
            id="test_campaign",
            name="Test Campaign",
            objective="awareness",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            audience_age_start=18,
            audience_age_end=34,
            location_type="Country",
            locations=["United States"]
        ),
        lineitems=[
            LineItem(
                id="test_lineitem",
                name="Social Line Item",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
                cost_total=Decimal("50000"),
                channel="social",
                vehicle="Facebook",
                partner="Meta",
                kpi="CPM"
            )
        ]
    )


class TestJsonFormatHandler:
    """Test the JSON format handler."""

    def test_init(self):
        """Test initialization."""
        handler = JsonFormatHandler()
        assert handler.format_name == "json"
        assert handler.file_extension == "json"
        assert handler.indent == 2
        assert handler.ensure_ascii is False

        # Custom options
        handler = JsonFormatHandler(indent=4, ensure_ascii=True)
        assert handler.indent == 4
        assert handler.ensure_ascii is True

    def test_serialize_deserialize(self):
        """Test serialization and deserialization."""
        handler = JsonFormatHandler()
        data = {"test": "value", "nested": {"key": 123}}

        # Serialize
        serialized = handler.serialize(data)
        assert isinstance(serialized, str)
        assert '"test": "value"' in serialized
        assert '"nested": {' in serialized

        # Deserialize
        deserialized = handler.deserialize(serialized)
        assert deserialized == data

    def test_serialize_to_file(self, tmp_path):
        """Test serialization to file."""
        handler = JsonFormatHandler()
        data = {"test": "value", "nested": {"key": 123}}

        # Create a file
        file_path = tmp_path / "test.json"
        with open(file_path, "w") as f:
            handler.serialize_to_file(data, f)

        # Verify file content
        with open(file_path, "r") as f:
            content = f.read()

        assert '"test": "value"' in content
        assert '"nested": {' in content

    def test_deserialize_from_file(self, tmp_path):
        """Test deserialization from file."""
        handler = JsonFormatHandler()
        data = {"test": "value", "nested": {"key": 123}}

        # Create a file
        file_path = tmp_path / "test.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        # Deserialize from file
        with open(file_path, "r") as f:
            deserialized = handler.deserialize_from_file(f)

        assert deserialized == data


class TestLocalStorageBackend:
    """Test the local storage backend."""

    def test_init(self, temp_storage_dir):
        """Test initialization."""
        # Create a workspace config
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir,
                    "create_if_missing": True
                }
            }
        }

        # Initialize backend
        backend = LocalStorageBackend(workspace_config)
        assert backend.base_path == os.path.abspath(temp_storage_dir)

        # Test invalid config (wrong mode)
        with pytest.raises(StorageError):
            LocalStorageBackend({"storage": {"mode": "s3"}})

        # Test missing base path
        with pytest.raises(StorageError):
            LocalStorageBackend({"storage": {"mode": "local", "local": {}}})

    def test_resolve_path(self, temp_storage_dir):
        """Test path resolution."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = LocalStorageBackend(workspace_config)

        # Relative path
        rel_path = "test/path.json"
        resolved = backend.resolve_path(rel_path)
        assert resolved == os.path.join(temp_storage_dir, rel_path)

        # Absolute path
        abs_path = os.path.abspath("/absolute/path.json")
        resolved = backend.resolve_path(abs_path)
        assert resolved == abs_path

    def test_exists(self, temp_storage_dir):
        """Test file existence check."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = LocalStorageBackend(workspace_config)

        # Create a test file
        test_file = os.path.join(temp_storage_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        # Check existence
        assert backend.exists("test.txt")
        assert not backend.exists("nonexistent.txt")

    def test_read_write_file(self, temp_storage_dir):
        """Test reading and writing files."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = LocalStorageBackend(workspace_config)

        # Write a file
        backend.write_file("test.txt", "test content")
        assert os.path.exists(os.path.join(temp_storage_dir, "test.txt"))

        # Read the file
        content = backend.read_file("test.txt")
        assert content == "test content"

        # Write a file in a subdirectory
        backend.write_file("subdir/test.txt", "test content in subdir")
        assert os.path.exists(os.path.join(temp_storage_dir, "subdir", "test.txt"))

        # Read the file
        content = backend.read_file("subdir/test.txt")
        assert content == "test content in subdir"

        # Binary mode
        binary_data = b"binary content"
        backend.write_file("binary.bin", binary_data)
        read_binary = backend.read_file("binary.bin", binary=True)
        assert read_binary == binary_data

    def test_list_files(self, temp_storage_dir):
        """Test listing files."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = LocalStorageBackend(workspace_config)

        # Create test files
        backend.write_file("test1.txt", "test1")
        backend.write_file("test2.txt", "test2")
        backend.write_file("subdir/test3.txt", "test3")

        # List all files
        files = backend.list_files("")
        assert len(files) == 2  # test1.txt and test2.txt (not including subdirectories)
        assert "test1.txt" in files
        assert "test2.txt" in files

        # List files in subdirectory
        files = backend.list_files("subdir")
        assert len(files) == 1
        assert "subdir/test3.txt" in files

        # List with pattern
        files = backend.list_files("", pattern="*.txt")
        assert len(files) == 2
        assert "test1.txt" in files
        assert "test2.txt" in files

    def test_delete_file(self, temp_storage_dir):
        """Test deleting files."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = LocalStorageBackend(workspace_config)

        # Create a test file
        backend.write_file("test.txt", "test")
        assert backend.exists("test.txt")

        # Delete the file
        backend.delete_file("test.txt")
        assert not backend.exists("test.txt")

    def test_get_file_info(self, temp_storage_dir):
        """Test getting file information."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = LocalStorageBackend(workspace_config)

        # Create a test file
        backend.write_file("test.txt", "test content")

        # Get file info
        info = backend.get_file_info("test.txt")
        assert info["path"] == "test.txt"
        assert info["size"] == len("test content")
        assert "modified" in info
        assert not info["is_directory"]

    def test_open_file(self, temp_storage_dir):
        """Test opening files."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = LocalStorageBackend(workspace_config)

        # Write content using open_file
        with backend.open_file("test.txt", "w") as f:
            f.write("test content")

        # Read content using open_file
        with backend.open_file("test.txt", "r") as f:
            content = f.read()

        assert content == "test content"

        # Binary mode
        with backend.open_file("binary.bin", "wb") as f:
            f.write(b"binary content")

        with backend.open_file("binary.bin", "rb") as f:
            binary_content = f.read()

        assert binary_content == b"binary content"


class TestStorageFunctions:
    """Test the storage module functions."""

    def test_get_storage_backend(self, temp_storage_dir):
        """Test getting a storage backend."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        backend = get_storage_backend(workspace_config)
        assert isinstance(backend, LocalStorageBackend)

        # Invalid mode
        with pytest.raises(StorageError):
            get_storage_backend({"storage": {"mode": "invalid"}})

    def test_get_format_handler_instance(self):
        """Test getting a format handler instance."""
        # By name
        handler = get_format_handler_instance("json")
        assert isinstance(handler, JsonFormatHandler)

        # By path
        handler = get_format_handler_instance("path/to/file.json")
        assert isinstance(handler, JsonFormatHandler)

        # Invalid format
        with pytest.raises(ValueError):
            get_format_handler_instance("invalid")

    def test_read_write_mediaplan_v1(self, temp_storage_dir, sample_mediaplan_v1):
        """Test reading and writing v1.0.0 media plans."""
        workspace_config = {
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_storage_dir
                }
            }
        }

        # Write media plan
        path = "test_mediaplan_v1.json"
        write_mediaplan(workspace_config, sample_mediaplan_v1.to_dict(), path)

        # Verify file exists
        assert os.path.exists(os.path.join(temp_storage_dir, path))

        # Read media plan
        data = read_mediaplan(workspace_config, path)

        # Verify v1.0.0 structure
        assert data["meta"]["schema_version"] == "v1.0.0"
        assert data["meta"]["id"] == "mediaplan_12345"
        assert data["meta"]["name"] == "Test Media Plan"
        assert data["campaign"]["name"] == "Test Campaign"
        assert data["campaign"]["budget_total"] == 100000
        assert len(data["lineitems"]) == 1
        assert data["lineitems"][0]["name"] == "Social Line Item"
        assert data["lineitems"][0]["cost_total"] == 50000


class TestMediaPlanStorageIntegration:
    """Test the integration with MediaPlan model."""

    def test_save_load_to_storage_v1(self, temp_workspace_file, sample_mediaplan_v1):
        """Test saving and loading v1.0.0 media plans using MediaPlan methods."""
        # Load workspace manager
        manager = WorkspaceManager(temp_workspace_file)
        manager.load()

        # Get the base path for verification
        base_path = manager.get_resolved_config()["storage"]["local"]["base_path"]

        # Save media plan
        path = "test_integration_v1.json"
        sample_mediaplan_v1.save_to_storage(manager, path)

        # Verify file exists
        assert os.path.exists(os.path.join(base_path, path))

        # Load media plan
        loaded_plan = MediaPlan.load_from_storage(manager, path)

        # Verify v1.0.0 data structure
        assert loaded_plan.meta.schema_version == "v1.0.0"
        assert loaded_plan.meta.id == "mediaplan_12345"
        assert loaded_plan.meta.name == "Test Media Plan"
        assert loaded_plan.campaign.name == "Test Campaign"
        assert loaded_plan.campaign.budget_total == Decimal("100000")
        assert len(loaded_plan.lineitems) == 1
        assert loaded_plan.lineitems[0].id == "test_lineitem"
        assert loaded_plan.lineitems[0].name == "Social Line Item"
        assert loaded_plan.lineitems[0].cost_total == Decimal("50000")

    def test_auto_path_generation_v1(self, temp_workspace_file, sample_mediaplan_v1):
        """Test automatic path generation based on media plan ID and campaign ID."""
        # Load workspace manager
        manager = WorkspaceManager(temp_workspace_file)
        manager.load()

        # Get the base path for verification
        base_path = manager.get_resolved_config()["storage"]["local"]["base_path"]

        # Test auto path generation with media plan ID
        saved_path = sample_mediaplan_v1.save_to_storage(manager)
        expected_path = f"{sample_mediaplan_v1.campaign.id}.json"

        # Verify file exists at the expected path
        assert os.path.exists(os.path.join(base_path, expected_path))
        assert saved_path == expected_path

        # Load by campaign ID
        loaded_plan = MediaPlan.load_from_storage(
            manager,
            campaign_id=sample_mediaplan_v1.campaign.id
        )

        # Verify data
        assert loaded_plan.meta.id == sample_mediaplan_v1.meta.id
        assert loaded_plan.campaign.name == sample_mediaplan_v1.campaign.name