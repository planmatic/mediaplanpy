#!/usr/bin/env python3
"""
Test script for MediaPlan.delete method
"""

import os
import tempfile
import shutil
from pathlib import Path
from decimal import Decimal
from datetime import date

import pytest
from mediaplanpy import MediaPlan, WorkspaceManager
from mediaplanpy.exceptions import StorageError, WorkspaceNotFoundError


def test_mediaplan_delete():
    """Test the MediaPlan delete functionality."""

    # Create a temporary directory for the test workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create workspace configuration
        manager = WorkspaceManager()
        workspace_id, settings_file = manager.create(
            settings_path_name=str(temp_path),
            storage_path_name=str(temp_path / "storage"),
            workspace_name="Delete Test Workspace",
            overwrite=True
        )

        print(f"Created test workspace: {workspace_id}")
        print(f"Settings file: {settings_file}")

        # Test basic delete functionality
        _test_basic_delete(manager)

        # Test dry run functionality
        _test_dry_run_delete(manager)

        # Test resurrection sequence
        _test_resurrection_sequence(manager)

        # Test error conditions
        _test_error_conditions(manager)

        print("=== All tests completed successfully ===")


def _test_basic_delete(manager: WorkspaceManager):
    """Test basic delete functionality."""
    print("\n--- Testing basic delete functionality ---")

    # Create a test media plan
    media_plan = MediaPlan.create(
        created_by="test@example.com",
        campaign_name="Test Delete Campaign",
        campaign_objective="Testing delete functionality",
        campaign_start_date=date(2025, 1, 1),
        campaign_end_date=date(2025, 12, 31),
        campaign_budget=Decimal("10000"),
        workspace_manager=manager
    )

    print(f"Created media plan with ID: {media_plan.meta.id}")

    # Save it to storage
    save_path = media_plan.save(manager)
    print(f"Saved media plan to: {save_path}")

    # Verify files exist by trying to load
    loaded_plan = MediaPlan.load(manager, media_plan_id=media_plan.meta.id)
    print(f"✅ Verified: Media plan exists in storage")
    assert loaded_plan.meta.id == media_plan.meta.id

    # Delete the media plan
    delete_result = media_plan.delete(manager, dry_run=False)
    print(f"Delete result: {delete_result}")

    # Verify the result structure
    assert "deleted_files" in delete_result
    assert "errors" in delete_result
    assert "mediaplan_id" in delete_result
    assert "files_found" in delete_result
    assert "files_deleted" in delete_result
    assert delete_result["mediaplan_id"] == media_plan.meta.id
    assert delete_result["files_deleted"] > 0
    assert len(delete_result["errors"]) == 0

    # Verify files are gone by attempting to load
    with pytest.raises(StorageError):
        MediaPlan.load(manager, media_plan_id=media_plan.meta.id)

    print("✅ Basic delete test passed")


def _test_dry_run_delete(manager: WorkspaceManager):
    """Test dry run functionality."""
    print("\n--- Testing dry run functionality ---")

    # Create and save a media plan
    media_plan = MediaPlan.create(
        created_by="test@example.com",
        campaign_name="Test Dry Run Campaign",
        campaign_objective="Testing dry run",
        campaign_start_date=date(2025, 1, 1),
        campaign_end_date=date(2025, 12, 31),
        campaign_budget=Decimal("5000"),
        workspace_manager=manager
    )

    save_path = media_plan.save(manager)
    print(f"Saved media plan for dry run test: {save_path}")

    # Perform dry run
    dry_result = media_plan.delete(manager, dry_run=True)
    print(f"Dry run result: {dry_result}")

    # Verify dry run result
    assert dry_result["dry_run"] == True
    assert dry_result["files_found"] > 0
    assert len(dry_result["deleted_files"]) > 0
    assert dry_result["files_deleted"] == 0  # No actual deletion in dry run

    # Verify files still exist after dry run
    loaded_plan = MediaPlan.load(manager, media_plan_id=media_plan.meta.id)
    assert loaded_plan.meta.id == media_plan.meta.id
    print("✅ Files still exist after dry run")

    # Clean up - actually delete the media plan
    actual_delete_result = media_plan.delete(manager, dry_run=False)
    assert actual_delete_result["files_deleted"] > 0

    print("✅ Dry run test passed")


def _test_resurrection_sequence(manager: WorkspaceManager):
    """Test the create → save → delete → save sequence."""
    print("\n--- Testing resurrection sequence ---")

    # Create and save media plan
    media_plan = MediaPlan.create(
        created_by="test@example.com",
        campaign_name="Test Resurrection Campaign",
        campaign_objective="Testing resurrection",
        campaign_start_date=date(2025, 1, 1),
        campaign_end_date=date(2025, 12, 31),
        campaign_budget=Decimal("7500"),
        workspace_manager=manager
    )

    original_id = media_plan.meta.id
    save_path = media_plan.save(manager)
    print(f"Original save: {save_path} with ID: {original_id}")

    # Delete it
    delete_result = media_plan.delete(manager, dry_run=False)
    assert delete_result["files_deleted"] > 0
    print("✅ Media plan deleted")

    # Save again (should get new ID by default due to overwrite=False)
    new_save_path = media_plan.save(manager)
    new_id = media_plan.meta.id

    print(f"Resurrection save: {new_save_path} with ID: {new_id}")
    print(f"Original ID: {original_id}")
    print(f"New ID: {new_id}")
    print(f"IDs are different: {original_id != new_id}")

    # Verify the IDs are different (resurrection with new ID)
    assert original_id != new_id

    # Verify the new media plan can be loaded
    loaded_plan = MediaPlan.load(manager, media_plan_id=new_id)
    assert loaded_plan.meta.id == new_id

    # Clean up the resurrected media plan
    cleanup_result = media_plan.delete(manager)
    assert cleanup_result["files_deleted"] > 0

    print("✅ Resurrection sequence test passed")


def _test_error_conditions(manager: WorkspaceManager):
    """Test error conditions and edge cases."""
    print("\n--- Testing error conditions ---")

    # Create a media plan but don't save it
    media_plan = MediaPlan.create(
        created_by="test@example.com",
        campaign_name="Test Error Campaign",
        campaign_objective="Testing errors",
        campaign_start_date=date(2025, 1, 1),
        campaign_end_date=date(2025, 12, 31),
        campaign_budget=Decimal("1000"),
        workspace_manager=manager
    )

    # Try to delete a media plan that was never saved
    delete_result = media_plan.delete(manager, dry_run=False)
    print(f"Delete result for unsaved media plan: {delete_result}")

    # Should not find any files but shouldn't error
    assert delete_result["files_found"] == 0
    assert delete_result["files_deleted"] == 0
    assert len(delete_result["errors"]) == 0

    print("✅ Error conditions test passed")


if __name__ == "__main__":
    test_mediaplan_delete()