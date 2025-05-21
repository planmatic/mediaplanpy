"""
Unit tests for the standardized Excel import/export methods.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, mock_open

from datetime import datetime, date

from mediaplanpy.models import MediaPlan, Meta, Campaign
from mediaplanpy.exceptions import StorageError
from mediaplanpy.workspace import WorkspaceManager


class TestExcelMethods(unittest.TestCase):
    """Test cases for the standardized Excel import/export methods."""

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

    # export_to_excel tests

    def test_export_to_excel_local(self):
        """Test export_to_excel to local file system."""
        # Set up patch for exporter.export_to_excel
        with patch('mediaplanpy.excel.exporter.export_to_excel') as mock_export:
            # Set up return value
            expected_path = os.path.join(self.temp_dir, f"{self.media_plan.meta.id}.xlsx")
            mock_export.return_value = expected_path

            # Export to the temporary directory
            file_path = self.media_plan.export_to_excel(file_path=self.temp_dir)

            # Verify export_to_excel was called with correct parameters
            mock_export.assert_called_once()
            args, kwargs = mock_export.call_args

            # Verify data was passed
            self.assertEqual(args[0], self.media_plan.to_dict())

            # Verify path was correct
            self.assertEqual(kwargs['path'], expected_path)

            # Verify result
            self.assertEqual(file_path, expected_path)

    def test_export_to_excel_workspace(self):
        """Test export_to_excel to workspace storage."""
        # Create mock workspace manager
        mock_workspace_manager = MagicMock(spec=WorkspaceManager)
        mock_workspace_manager.is_loaded = True

        # Create mock storage backend
        mock_storage_backend = MagicMock()
        mock_storage_backend.exists.return_value = False
        mock_workspace_manager.get_storage_backend.return_value = mock_storage_backend

        # Mock workspace Excel config
        mock_workspace_manager.get_excel_config.return_value = {
            "template_path": "/path/to/template.xlsx"
        }

        # Set up patch for export function
        with patch('mediaplanpy.excel.exporter.export_to_excel') as mock_export:
            # Set up return value - use OS-specific path
            expected_path = os.path.join("exports", f"{self.media_plan.meta.id}.xlsx")
            mock_export.return_value = expected_path

            # Export to workspace
            result = self.media_plan.export_to_excel(workspace_manager=mock_workspace_manager)

            # Verify workspace storage was used
            mock_workspace_manager.get_storage_backend.assert_called()

            # Verify create_directory was attempted
            mock_storage_backend.create_directory.assert_called_once_with("exports")

            # Verify export_to_excel was called with correct parameters
            mock_export.assert_called_once()
            args, kwargs = mock_export.call_args

            # Verify data was passed
            self.assertEqual(args[0], self.media_plan.to_dict())

            # Verify path was correct - use OS-specific path join
            self.assertEqual(kwargs['path'], expected_path)

            # Verify template_path was taken from workspace config
            self.assertEqual(kwargs['template_path'], "/path/to/template.xlsx")

            # Verify workspace_manager was passed
            self.assertEqual(kwargs['workspace_manager'], mock_workspace_manager)

            # Verify result
            self.assertEqual(result, expected_path)

    def test_export_to_excel_custom_filename(self):
        """Test export_to_excel with custom filename."""
        # Set up patch
        with patch('mediaplanpy.excel.exporter.export_to_excel') as mock_export:
            # Set up mock
            custom_filename = "custom_name.xlsx"
            expected_path = os.path.join(self.temp_dir, custom_filename)
            mock_export.return_value = expected_path

            # Export with custom filename
            result = self.media_plan.export_to_excel(
                file_path=self.temp_dir,
                file_name=custom_filename
            )

            # Verify export_to_excel was called with correct parameters
            args, kwargs = mock_export.call_args
            self.assertEqual(kwargs['path'], expected_path)

            # Verify result
            self.assertEqual(result, expected_path)

    def test_export_to_excel_template_path(self):
        """Test export_to_excel with custom template path."""
        # Set up patch
        with patch('mediaplanpy.excel.exporter.export_to_excel') as mock_export:
            # Set up mock
            template_path = "/path/to/custom_template.xlsx"
            expected_path = os.path.join(self.temp_dir, f"{self.media_plan.meta.id}.xlsx")
            mock_export.return_value = expected_path

            # Export with custom template
            result = self.media_plan.export_to_excel(
                file_path=self.temp_dir,
                template_path=template_path
            )

            # Verify export_to_excel was called with correct parameters
            args, kwargs = mock_export.call_args
            self.assertEqual(kwargs['template_path'], template_path)

            # Verify result
            self.assertEqual(result, expected_path)

    def test_export_to_excel_no_storage_location(self):
        """Test export_to_excel raises error when neither workspace_manager nor file_path is provided."""
        with self.assertRaises(ValueError) as context:
            self.media_plan.export_to_excel()

        self.assertIn("Either workspace_manager or file_path must be provided", str(context.exception))

    def test_export_to_excel_no_overwrite(self):
        """Test export_to_excel raises error when file exists and overwrite=False."""
        # Create mock storage backend that reports file already exists
        mock_workspace_manager = MagicMock(spec=WorkspaceManager)
        mock_workspace_manager.is_loaded = True
        mock_storage_backend = MagicMock()
        mock_storage_backend.exists.return_value = True
        mock_workspace_manager.get_storage_backend.return_value = mock_storage_backend

        # Attempt export
        with self.assertRaises(StorageError) as context:
            self.media_plan.export_to_excel(workspace_manager=mock_workspace_manager)

        # Verify error message
        self.assertIn("already exists", str(context.exception))

    def test_export_to_excel_with_overwrite(self):
        """Test export_to_excel overwrites when overwrite=True."""
        # Create mock storage backend that reports file already exists
        mock_workspace_manager = MagicMock(spec=WorkspaceManager)
        mock_workspace_manager.is_loaded = True
        mock_storage_backend = MagicMock()
        mock_storage_backend.exists.return_value = True
        mock_workspace_manager.get_storage_backend.return_value = mock_storage_backend

        # Set up patch
        with patch('mediaplanpy.excel.exporter.export_to_excel') as mock_export:
            # Set up mock - use OS-specific path
            expected_path = os.path.join("exports", f"{self.media_plan.meta.id}.xlsx")
            mock_export.return_value = expected_path

            # Export with overwrite
            result = self.media_plan.export_to_excel(
                workspace_manager=mock_workspace_manager,
                overwrite=True
            )

            # Verify export_to_excel was called
            mock_export.assert_called_once()

            # Verify result
            self.assertEqual(result, expected_path)

    # import_from_excel tests

    def test_import_from_excel_local(self):
        """Test import_from_excel from local file system."""
        # Mock file exists
        excel_file = os.path.join(self.temp_dir, "test.xlsx")

        # Use a context manager to apply multiple patches
        with patch('os.path.exists', return_value=True), \
             patch('mediaplanpy.excel.importer.import_from_excel') as mock_import:

            # Mock import_from_excel to return media plan data
            mock_import.return_value = self.media_plan.to_dict()

            # Import from Excel
            imported_plan = MediaPlan.import_from_excel(
                file_name="test.xlsx",
                file_path=self.temp_dir
            )

            # Verify import_from_excel was called with correct path
            mock_import.assert_called_once_with(excel_file)

            # Verify imported plan matches original
            self.assertEqual(imported_plan.meta.id, self.media_plan.meta.id)

    def test_import_from_excel_file_not_found(self):
        """Test import_from_excel raises error when file doesn't exist."""
        # Mock file doesn't exist
        with patch('os.path.exists', return_value=False):
            # Try to import a non-existent file
            with self.assertRaises(StorageError):
                MediaPlan.import_from_excel(
                    file_name="non_existent.xlsx",
                    file_path=self.temp_dir
                )

    def test_import_from_excel_no_storage_location(self):
        """Test import_from_excel raises error when neither workspace_manager nor file_path is provided."""
        with self.assertRaises(ValueError) as context:
            MediaPlan.import_from_excel(file_name="test.xlsx")

        self.assertIn("Either workspace_manager or file_path must be provided", str(context.exception))

    def test_import_from_excel_workspace(self):
        """Test import_from_excel from workspace storage."""
        # Create temp file path using os-specific path style
        temp_path = os.path.join(tempfile.gettempdir(), "mock_temp_file.xlsx")

        # Create mock workspace manager
        mock_workspace_manager = MagicMock(spec=WorkspaceManager)
        mock_workspace_manager.is_loaded = True

        # Create mock storage backend
        mock_storage_backend = MagicMock()
        # Mock file exists in imports directory
        mock_storage_backend.exists.return_value = True
        mock_workspace_manager.get_storage_backend.return_value = mock_storage_backend

        # Mock file content
        mock_storage_backend.read_file.return_value = b"dummy content"

        # Multiple patches needed
        with patch('tempfile.NamedTemporaryFile') as mock_tmp, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.unlink') as mock_unlink, \
             patch('mediaplanpy.excel.importer.import_from_excel') as mock_import:

            # Set up mock temp file
            mock_tmp_instance = MagicMock()
            mock_tmp_instance.name = temp_path
            mock_tmp.return_value.__enter__.return_value = mock_tmp_instance

            # Set up mock import return
            mock_import.return_value = self.media_plan.to_dict()

            # Import from workspace
            file_name = "test.xlsx"
            imported_plan = MediaPlan.import_from_excel(
                file_name=file_name,
                workspace_manager=mock_workspace_manager
            )

            # Verify storage_backend.read_file was called
            mock_storage_backend.read_file.assert_called_once()
            args, kwargs = mock_storage_backend.read_file.call_args

            # Path should be in imports directory (using OS-specific path)
            imports_dir = os.path.join("imports", file_name)
            self.assertTrue(args[0].endswith(file_name))

            # binary should be True for Excel
            self.assertEqual(kwargs['binary'], True)

            # Verify import_from_excel was called
            mock_import.assert_called_once_with(temp_path)

            # Verify imported plan matches original
            self.assertEqual(imported_plan.meta.id, self.media_plan.meta.id)


if __name__ == "__main__":
    unittest.main()