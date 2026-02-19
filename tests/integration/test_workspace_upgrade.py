"""
Integration tests for workspace upgrade from v2.0 to v3.0.

Tests the WorkspaceUpgrader functionality, including:
- Pre-upgrade validation
- Dry-run previews
- JSON file migration
- Backup creation
- Workspace settings update
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.workspace.upgrader import WorkspaceUpgrader
from mediaplanpy.exceptions import WorkspaceError, SchemaVersionError


@pytest.fixture
def temp_workspace_dir():
    """Create a temporary workspace directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def workspace_v2_config(temp_workspace_dir):
    """Create a v2.0 workspace configuration."""
    config = {
        "workspace_id": "test_workspace_v2",
        "workspace_name": "Test Workspace v2.0",
        "workspace_settings": {
            "schema_version": "2.0"
        },
        "storage": {
            "mode": "local",
            "local": {
                "base_path": temp_workspace_dir
            }
        },
        "database": {
            "enabled": False
        }
    }

    config_path = os.path.join(temp_workspace_dir, "workspace.json")
    with open(config_path, 'w') as f:
        json.dump(config, f)

    return config_path


@pytest.fixture
def workspace_v2_with_mediaplans(temp_workspace_dir, mediaplan_v2_dict):
    """Create a v2.0 workspace with sample media plans."""
    config = {
        "workspace_id": "test_workspace_v2",
        "workspace_name": "Test Workspace v2.0 with Media Plans",
        "workspace_settings": {
            "schema_version": "2.0"
        },
        "storage": {
            "mode": "local",
            "local": {
                "base_path": temp_workspace_dir
            }
        },
        "database": {
            "enabled": False
        }
    }

    config_path = os.path.join(temp_workspace_dir, "workspace.json")
    with open(config_path, 'w') as f:
        json.dump(config, f)

    # Create mediaplans subdirectory (workspace upgrader looks here first)
    mediaplans_dir = os.path.join(temp_workspace_dir, "mediaplans")
    os.makedirs(mediaplans_dir, exist_ok=True)

    # Create a sample v2.0 media plan file in mediaplans directory
    mediaplan_path = os.path.join(mediaplans_dir, "mediaplan_v2_001.json")
    with open(mediaplan_path, 'w') as f:
        json.dump(mediaplan_v2_dict, f)

    return config_path


class TestWorkspaceUpgradeValidation:
    """Test workspace upgrade validation and prerequisites."""

    def test_dry_run_preview(self, workspace_v2_with_mediaplans):
        """Test that dry run shows what would be upgraded without making changes."""
        workspace_manager = WorkspaceManager(workspace_path=workspace_v2_with_mediaplans)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=True)

        # Verify dry run flag
        assert result["dry_run"] is True

        # In dry run mode, workspace_updated=True means "would update" (not "did update")
        assert result["workspace_updated"] is True

        # Should show files that would be processed
        assert "files_processed" in result

    def test_validate_workspace_loaded(self, workspace_v2_config):
        """Test that upgrade requires workspace to be loaded first."""
        workspace_manager = WorkspaceManager(workspace_path=workspace_v2_config)
        # Don't load the workspace

        upgrader = WorkspaceUpgrader(workspace_manager)

        # Should raise error if not loaded
        with pytest.raises(WorkspaceError, match="No workspace configuration loaded"):
            upgrader.upgrade()

    def test_rejects_v1_files(self, temp_workspace_dir):
        """Test that upgrade rejects v1.0 media plans."""
        # Create workspace config
        config = {
            "workspace_id": "test_workspace_v1",
            "workspace_name": "Test Workspace with v1.0 Files",
            "workspace_settings": {
                "schema_version": "2.0"  # workspace is v2.0 but has v1.0 files
            },
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_workspace_dir
                }
            },
            "database": {
                "enabled": False
            }
        }

        config_path = os.path.join(temp_workspace_dir, "workspace.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)

        # Create mediaplans subdirectory
        mediaplans_dir = os.path.join(temp_workspace_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        # Create a v1.0 media plan file
        mediaplan_v1 = {
            "meta": {
                "id": "MP_V1_001",
                "schema_version": "v1.0",  # v1.0 - should be rejected
                "name": "v1.0 Media Plan",
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

        mediaplan_path = os.path.join(mediaplans_dir, "mediaplan_v1_001.json")
        with open(mediaplan_path, 'w') as f:
            json.dump(mediaplan_v1, f)

        # Try to upgrade
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)

        # Dry run should show v1 rejection
        result = upgrader.upgrade(dry_run=True)
        assert result["v1_files_rejected"] > 0
        assert any("v1.0" in error for error in result["errors"])

        # Actual upgrade should raise error
        with pytest.raises(WorkspaceError, match="v1.0"):
            upgrader.upgrade(dry_run=False)


class TestWorkspaceUpgradeExecution:
    """Test actual workspace upgrade execution."""

    def test_upgrade_empty_workspace(self, workspace_v2_config):
        """Test upgrading workspace with no media plans."""
        workspace_manager = WorkspaceManager(workspace_path=workspace_v2_config)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        # Should complete successfully even with no files
        assert result["dry_run"] is False
        assert result["target_schema_version"] == "3.0"
        assert result["workspace_updated"] is True

        # Verify workspace config was updated
        workspace_manager.load()  # Reload to get updated config
        assert workspace_manager.config["workspace_settings"]["schema_version"] == "3.0"

    def test_upgrade_with_v2_mediaplans(self, workspace_v2_with_mediaplans):
        """Test upgrading workspace with v2.0 media plans."""
        workspace_manager = WorkspaceManager(workspace_path=workspace_v2_with_mediaplans)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        # Verify upgrade completed
        assert result["dry_run"] is False
        assert result["workspace_updated"] is True
        assert result["json_files_migrated"] > 0

        # Verify files were migrated
        assert len(result["files_processed"]) > 0
        assert len(result["files_failed"]) == 0

    def test_upgrade_creates_backups(self, workspace_v2_with_mediaplans):
        """Test that upgrade creates backup directory and files."""
        workspace_manager = WorkspaceManager(workspace_path=workspace_v2_with_mediaplans)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        # Verify backups were created
        assert "backups_created" in result
        assert "backup_directory" in result["backups_created"]

        backup_dir = result["backups_created"]["backup_directory"]
        assert os.path.exists(backup_dir)

        # Verify backup contains files
        backup_files = os.listdir(backup_dir)
        assert len(backup_files) > 0

    def test_upgrade_migrates_audience_fields(self, temp_workspace_dir):
        """Test that upgrade migrates v2.0 audience fields to v3.0 target_audiences."""
        # Create workspace with v2.0 plan that has audience fields
        config = {
            "workspace_id": "test_workspace_audiences",
            "workspace_name": "Test Workspace with Audiences",
            "workspace_settings": {
                "schema_version": "2.0"
            },
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_workspace_dir
                }
            },
            "database": {
                "enabled": False
            }
        }

        config_path = os.path.join(temp_workspace_dir, "workspace.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)

        # Create mediaplans subdirectory
        mediaplans_dir = os.path.join(temp_workspace_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        # Create v2.0 media plan with audience fields
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
                "audience_age_end": 54
            },
            "lineitems": []
        }

        mediaplan_path = os.path.join(mediaplans_dir, "mediaplan_001.json")
        with open(mediaplan_path, 'w') as f:
            json.dump(mediaplan_v2, f)

        # Upgrade workspace
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        # Verify migration occurred
        assert result["json_files_migrated"] > 0

        # Load migrated file and verify target_audiences
        with open(mediaplan_path, 'r') as f:
            migrated = json.load(f)

        assert migrated["meta"]["schema_version"] in ["3.0", "v3.0"]
        assert "target_audiences" in migrated["campaign"]
        assert migrated["campaign"]["target_audiences"][0]["name"] == "Adults 25-54"
        assert "audience_name" not in migrated["campaign"]

    def test_upgrade_migrates_location_fields(self, temp_workspace_dir):
        """Test that upgrade migrates v2.0 location fields to v3.0 target_locations."""
        # Create workspace with v2.0 plan that has location fields
        config = {
            "workspace_id": "test_workspace_locations",
            "workspace_name": "Test Workspace with Locations",
            "workspace_settings": {
                "schema_version": "2.0"
            },
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_workspace_dir
                }
            },
            "database": {
                "enabled": False
            }
        }

        config_path = os.path.join(temp_workspace_dir, "workspace.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)

        # Create mediaplans subdirectory
        mediaplans_dir = os.path.join(temp_workspace_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        # Create v2.0 media plan with location fields
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

        mediaplan_path = os.path.join(mediaplans_dir, "mediaplan_001.json")
        with open(mediaplan_path, 'w') as f:
            json.dump(mediaplan_v2, f)

        # Upgrade workspace
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        # Verify migration occurred
        assert result["json_files_migrated"] > 0

        # Load migrated file and verify target_locations
        with open(mediaplan_path, 'r') as f:
            migrated = json.load(f)

        assert migrated["meta"]["schema_version"] in ["3.0", "v3.0"]
        assert "target_locations" in migrated["campaign"]
        assert "California" in migrated["campaign"]["target_locations"][0]["location_list"]
        assert "locations" not in migrated["campaign"]


class TestWorkspaceUpgradeResults:
    """Test upgrade result reporting and error handling."""

    def test_upgrade_result_structure(self, workspace_v2_config):
        """Test that upgrade returns well-structured result dictionary."""
        workspace_manager = WorkspaceManager(workspace_path=workspace_v2_config)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=True)

        # Verify result structure
        assert "dry_run" in result
        assert "target_sdk_version" in result
        assert "target_schema_version" in result
        assert "files_processed" in result
        assert "files_failed" in result
        assert "errors" in result
        assert "database_upgraded" in result
        assert "workspace_updated" in result
        assert "json_files_migrated" in result
        assert "backups_created" in result

        # Verify target versions
        assert result["target_schema_version"] == "3.0"

    def test_upgrade_reports_errors(self, temp_workspace_dir):
        """Test that upgrade reports errors when migration fails."""
        # Create workspace with invalid JSON file
        config = {
            "workspace_id": "test_workspace_errors",
            "workspace_name": "Test Workspace with Errors",
            "workspace_settings": {
                "schema_version": "2.0"
            },
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_workspace_dir
                }
            },
            "database": {
                "enabled": False
            }
        }

        config_path = os.path.join(temp_workspace_dir, "workspace.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)

        # Create mediaplans subdirectory
        mediaplans_dir = os.path.join(temp_workspace_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        # Create invalid JSON file
        invalid_path = os.path.join(mediaplans_dir, "mediaplan_invalid.json")
        with open(invalid_path, 'w') as f:
            f.write("{invalid json content")

        # Try to upgrade
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        # Should report the failed file
        # (depending on implementation, may be in files_failed or errors)
        assert len(result["files_failed"]) > 0 or len(result["errors"]) > 0

    def test_upgrade_preserves_created_at(self, temp_workspace_dir):
        """Test that upgrade preserves meta.created_at and records migration metadata."""
        # Create workspace with v2.0 plan
        config = {
            "workspace_id": "test_workspace_timestamps",
            "workspace_name": "Test Workspace Timestamp Preservation",
            "workspace_settings": {
                "schema_version": "2.0"
            },
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": temp_workspace_dir
                }
            },
            "database": {
                "enabled": False
            }
        }

        config_path = os.path.join(temp_workspace_dir, "workspace.json")
        with open(config_path, 'w') as f:
            json.dump(config, f)

        # Create mediaplans subdirectory
        mediaplans_dir = os.path.join(temp_workspace_dir, "mediaplans")
        os.makedirs(mediaplans_dir, exist_ok=True)

        # Create v2.0 media plan with a specific created_at timestamp
        original_created_at = "2024-06-15T10:30:00"
        mediaplan_v2 = {
            "meta": {
                "id": "MP_TS_001",
                "schema_version": "v2.0",
                "name": "Timestamp Test Plan",
                "created_by_name": "Test User",
                "created_at": original_created_at
            },
            "campaign": {
                "id": "CAM001",
                "name": "Test",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "budget_total": 100000,
                "audience_name": "Adults 25-54",
                "audience_age_start": 25,
                "audience_age_end": 54,
                "location_type": "State",
                "locations": ["California"]
            },
            "lineitems": []
        }

        mediaplan_path = os.path.join(mediaplans_dir, "mediaplan_ts_001.json")
        with open(mediaplan_path, 'w') as f:
            json.dump(mediaplan_v2, f)

        # Upgrade workspace
        workspace_manager = WorkspaceManager(workspace_path=config_path)
        workspace_manager.load(upgrade_mode=True)

        upgrader = WorkspaceUpgrader(workspace_manager)
        result = upgrader.upgrade(dry_run=False)

        assert result["json_files_migrated"] > 0

        # Load migrated file and verify created_at is preserved
        with open(mediaplan_path, 'r') as f:
            migrated = json.load(f)

        # created_at should still reflect the original creation date, not the migration time
        migrated_created_at = migrated["meta"]["created_at"]
        assert original_created_at in migrated_created_at, (
            f"created_at was overwritten: expected '{original_created_at}' "
            f"to be in '{migrated_created_at}'"
        )

        # custom_properties should contain migration metadata
        assert "custom_properties" in migrated["meta"]
        custom_props = migrated["meta"]["custom_properties"]
        assert "schema_migration" in custom_props
        assert custom_props["schema_migration"]["from_version"] == "2.0"
        assert custom_props["schema_migration"]["to_version"] == "3.0"
        assert "migrated_at" in custom_props["schema_migration"]
