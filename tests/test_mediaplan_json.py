"""
Unit tests for the standardized JSON import/export methods.
"""

import os
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, date

from mediaplanpy.models import MediaPlan, Meta, Campaign
from mediaplanpy.exceptions import StorageError
from mediaplanpy.workspace import WorkspaceManager

class TestJsonMethods(unittest.TestCase):
    """Test cases for the standardized JSON import/export methods."""

    def setUp(self):
        """Set up test data."""
        # Create a simple media plan for testing
        meta = Meta(
            id="test_mediaplan_001",
            schema_version="v1.0.0",
            created_by="test_user",
            created_at=datetime.now(),
            name="Test Media Plan"
        )

        campaign = Campaign(
            id="test_campaign_001",
            name="Test Campaign",
            objective="Test objective",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=100000
        )

        self.media_plan = MediaPlan(
            meta=meta,
            campaign=campaign,
            lineitems=[]
        )

        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory and its contents
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass

    # export_to_json tests

    def test_export_to_json_local(self):
        """Test export_to_json to local file system."""
        # Export to the temporary directory
        file_path = self.media_plan.export_to_json(file_path=self.temp_dir)

        # Verify file exists
        self.assertTrue(os.path.exists(file_path))

        # Verify file contains valid JSON
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Verify media plan data was saved correctly
        self.assertEqual(data["meta"]["id"], "test_mediaplan_001")
        self.assertEqual(data["campaign"]["id"], "test_campaign_001")

    def test_export_to_json_workspace(self):
        """Test export_to_json to workspace storage."""
        # Create mock workspace manager
        mock_workspace_manager = MagicMock(spec=WorkspaceManager)
        mock_workspace_manager.is_loaded = True

        # Create mock storage backend
        mock_storage_backend = MagicMock()
        mock_storage_backend.exists.return_value = False
        mock_workspace_manager.get_storage_backend.return_value = mock_storage_backend

        # Export to workspace
        result = self.media_plan.export_to_json(workspace_manager=mock_workspace_manager)

        # Verify workspace storage was used
        mock_workspace_manager.get_storage_backend.assert_called_once()

        # Verify create_directory was attempted
        mock_storage_backend.create_directory.assert_called_once_with("exports")

        # Verify write_file was called
        mock_storage_backend.write_file.assert_called_once()

        # Verify path contains exports directory
        args, kwargs = mock_storage_backend.write_file.call_args
        path = args[0]
        # Use os.path.normpath to handle path separators
        normalized_path = os.path.normpath(path)
        self.assertTrue("exports" in normalized_path)
        self.assertTrue(os.path.basename(normalized_path).endswith(".json"))

        # Verify returned path
        self.assertEqual(result, path)

    def test_export_to_json_custom_filename(self):
        """Test export_to_json with custom filename."""
        custom_filename = "custom_name.json"
        file_path = self.media_plan.export_to_json(
            file_path=self.temp_dir,
            file_name=custom_filename
        )

        # Verify path includes custom filename
        self.assertTrue(file_path.endswith(custom_filename))

        # Verify file exists
        self.assertTrue(os.path.exists(file_path))

    def test_export_to_json_format_options(self):
        """Test export_to_json with custom format options."""
        # Use custom indentation
        file_path = self.media_plan.export_to_json(
            file_path=self.temp_dir,
            indent=4,
            ensure_ascii=True
        )

        # Read the file content
        with open(file_path, 'r') as f:
            content = f.read()

        # Check that indentation was applied (approximate test)
        self.assertIn('    "', content)  # 4-space indentation

    def test_export_to_json_no_overwrite(self):
        """Test export_to_json raises error when file exists and overwrite=False."""
        # First export
        file_path = self.media_plan.export_to_json(file_path=self.temp_dir)

        # Second export should raise error
        with self.assertRaises(StorageError):
            self.media_plan.export_to_json(file_path=self.temp_dir)

    def test_export_to_json_with_overwrite(self):
        """Test export_to_json overwrites existing file when overwrite=True."""
        # First export
        file_path = self.media_plan.export_to_json(file_path=self.temp_dir)

        # Modify the media plan
        self.media_plan.meta.name = "Modified Test Media Plan"

        # Second export with overwrite
        file_path = self.media_plan.export_to_json(file_path=self.temp_dir, overwrite=True)

        # Verify file was overwritten with new data
        with open(file_path, 'r') as f:
            data = json.load(f)

        self.assertEqual(data["meta"]["name"], "Modified Test Media Plan")

    def test_export_to_json_no_storage_location(self):
        """Test export_to_json raises error when neither workspace_manager nor file_path is provided."""
        with self.assertRaises(ValueError) as context:
            self.media_plan.export_to_json()

        self.assertIn("Either workspace_manager or file_path must be provided", str(context.exception))

    # import_from_json tests

    def test_import_from_json_local(self):
        """Test import_from_json from local file system."""
        # First export a media plan
        file_path = self.media_plan.export_to_json(file_path=self.temp_dir)
        file_name = os.path.basename(file_path)

        # Now import it
        imported_plan = MediaPlan.import_from_json(
            file_name=file_name,
            file_path=self.temp_dir
        )

        # Verify imported plan matches original
        self.assertEqual(imported_plan.meta.id, self.media_plan.meta.id)
        self.assertEqual(imported_plan.campaign.id, self.media_plan.campaign.id)
        self.assertEqual(imported_plan.meta.name, self.media_plan.meta.name)

    def test_import_from_json_workspace(self):
        """Test import_from_json from workspace storage."""
        # Create mock workspace manager
        mock_workspace_manager = MagicMock(spec=WorkspaceManager)
        mock_workspace_manager.is_loaded = True

        # Create mock storage backend
        mock_storage_backend = MagicMock()
        # Mock file exists in imports directory
        mock_storage_backend.exists.return_value = True
        mock_workspace_manager.get_storage_backend.return_value = mock_storage_backend

        # Mock file content
        mock_content = json.dumps(self.media_plan.to_dict())
        mock_storage_backend.read_file.return_value = mock_content

        # Import from workspace
        file_name = f"{self.media_plan.meta.id}.json"
        imported_plan = MediaPlan.import_from_json(
            file_name=file_name,
            workspace_manager=mock_workspace_manager
        )

        # Verify storage_backend.read_file was called with correct path
        mock_storage_backend.read_file.assert_called_once()
        args, kwargs = mock_storage_backend.read_file.call_args

        # Path should be in imports directory - use normalized path for comparison
        path = args[0]
        expected_path = os.path.join("imports", file_name)
        self.assertTrue(path.replace('\\', '/').endswith(expected_path.replace('\\', '/')))

        # binary should be False
        self.assertEqual(kwargs['binary'], False)

        # Verify imported plan matches original
        self.assertEqual(imported_plan.meta.id, self.media_plan.meta.id)

    def test_import_from_json_file_not_found(self):
        """Test import_from_json raises error when file doesn't exist."""
        # Try to import a non-existent file
        with self.assertRaises(StorageError):
            MediaPlan.import_from_json(
                file_name="non_existent.json",
                file_path=self.temp_dir
            )

    def test_import_from_json_no_storage_location(self):
        """Test import_from_json raises error when neither workspace_manager nor file_path is provided."""
        with self.assertRaises(ValueError) as context:
            MediaPlan.import_from_json(file_name="test.json")

        self.assertIn("Either workspace_manager or file_path must be provided", str(context.exception))

if __name__ == "__main__":
    unittest.main()