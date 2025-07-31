"""
Integration of MediaPlan models with Excel functionality.

This module enhances the MediaPlan model with methods for exporting to
and importing from Excel format.
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional, Union, List

from mediaplanpy.exceptions import StorageError, ValidationError, SchemaVersionError
from mediaplanpy.models.mediaplan import MediaPlan
from mediaplanpy.excel import exporter, importer
from mediaplanpy.excel.validator import validate_excel
from mediaplanpy.workspace import WorkspaceManager

logger = logging.getLogger("mediaplanpy.models.mediaplan_excel")

# Constants for directory structure
EXPORTS_SUBDIR = "exports"
IMPORTS_SUBDIR = "imports"

def export_to_excel_method(self, workspace_manager=None, file_path=None, file_name=None,
                  template_path=None, include_documentation=True,
                  overwrite=False, **format_options) -> str:
    """
    Export the media plan to Excel format.

    Args:
        workspace_manager: Optional WorkspaceManager for saving to workspace storage.
                          If provided, this takes precedence over file_path.
        file_path: Optional path where to save the file. Required if workspace_manager
                  is not provided.
        file_name: Optional filename. If None, generates based on media plan ID.
        template_path: Optional path to an Excel template file.
        include_documentation: Whether to include a documentation sheet.
        overwrite: Whether to overwrite existing files.
        **format_options: Additional format-specific options.

    Returns:
        The complete path to the exported file.

    Raises:
        ValueError: If neither workspace_manager nor file_path is provided.
        StorageError: If export fails or file exists and overwrite=False.
        WorkspaceInactiveError: If workspace is inactive (warning only).
        FeatureDisabledError: If Excel functionality is disabled.
    """
    # Validate that at least one storage location is provided
    if workspace_manager is None and file_path is None:
        raise ValueError("Either workspace_manager or file_path must be provided")

    # Check workspace status and Excel availability if workspace_manager is provided
    if workspace_manager is not None:
        workspace_manager.check_workspace_active("Excel export", allow_warnings=True)
        workspace_manager.check_excel_enabled("Excel export")

    # Generate default filename if not provided
    if file_name is None:
        media_plan_id = self.meta.id
        file_name = f"{media_plan_id}.xlsx"

    # Convert model to dictionary
    data = self.to_dict()

    if workspace_manager is not None:
        # Use workspace storage (takes precedence)
        # Make sure workspace is loaded
        if not workspace_manager.is_loaded:
            workspace_manager.load()

        # Get Excel config from workspace
        excel_config = workspace_manager.get_excel_config()

        # If template_path not provided, check workspace settings
        if template_path is None and "template_path" in excel_config:
            template_path = excel_config["template_path"]

        # Get storage backend
        storage_backend = workspace_manager.get_storage_backend()

        # Create exports directory if it doesn't exist
        try:
            if hasattr(storage_backend, 'create_directory'):
                storage_backend.create_directory(EXPORTS_SUBDIR)
        except Exception as e:
            logger.warning(f"Could not create exports directory: {e}")

        # Full path in workspace storage
        full_path = os.path.join(EXPORTS_SUBDIR, file_name)

        # Check if file exists and handle overwrite flag
        if storage_backend.exists(full_path) and not overwrite:
            raise StorageError(
                f"File {full_path} already exists. Set overwrite=True to replace it."
            )

        try:
            # Export to Excel using the workspace manager
            result_path = exporter.export_to_excel(
                data,
                path=full_path,
                template_path=template_path,
                include_documentation=include_documentation,
                workspace_manager=workspace_manager,
                **format_options
            )

            logger.info(f"Media plan exported to Excel in workspace storage: {result_path}")
            return result_path
        except Exception as e:
            raise StorageError(f"Failed to export media plan to Excel: {e}")
    else:
        # Use local file system
        # Ensure directory exists
        if not os.path.exists(file_path):
            try:
                os.makedirs(file_path, exist_ok=True)
            except Exception as e:
                raise StorageError(f"Failed to create directory {file_path}: {e}")

        # Full path in local file system
        full_path = os.path.join(file_path, file_name)

        # Check if file exists and handle overwrite flag
        if os.path.exists(full_path) and not overwrite:
            raise StorageError(
                f"File {full_path} already exists. Set overwrite=True to replace it."
            )

        try:
            # Export to Excel directly
            result_path = exporter.export_to_excel(
                data,
                path=full_path,
                template_path=template_path,
                include_documentation=include_documentation,
                **format_options
            )

            logger.info(f"Media plan exported to Excel at: {result_path}")
            return result_path
        except Exception as e:
            raise StorageError(f"Failed to export media plan to Excel: {e}")


@classmethod
def import_from_excel_method(cls, file_name, workspace_manager=None, file_path=None,
                             **format_options):
    """
    Import a media plan from an Excel file with version handling.

    Args:
        file_name: Name of the file to import.
        workspace_manager: Optional WorkspaceManager for loading from workspace storage.
                          If provided, this takes precedence over file_path.
        file_path: Optional path to the file. Required if workspace_manager
                  is not provided.
        **format_options: Additional format-specific options.

    Returns:
        A new MediaPlan instance.

    Raises:
        ValueError: If neither workspace_manager nor file_path is provided.
        StorageError: If import fails or file doesn't exist.
        WorkspaceInactiveError: If workspace is inactive.
        FeatureDisabledError: If Excel functionality is disabled.
        SchemaVersionError: If schema version is not supported.
    """
    # Validate that at least one storage location is provided
    if workspace_manager is None and file_path is None:
        raise ValueError("Either workspace_manager or file_path must be provided")

    # Check workspace status and Excel availability if workspace_manager is provided
    if workspace_manager is not None:
        workspace_manager.check_workspace_active("Excel import")
        workspace_manager.check_excel_enabled("Excel import")

    if workspace_manager is not None:
        # Use workspace storage (takes precedence)
        # Make sure workspace is loaded
        if not workspace_manager.is_loaded:
            workspace_manager.load()

        # Get storage backend
        storage_backend = workspace_manager.get_storage_backend()

        # Check imports directory first
        imports_path = os.path.join(IMPORTS_SUBDIR, file_name)

        # Check if file exists in imports directory
        if storage_backend.exists(imports_path):
            full_path = imports_path
        else:
            # Try root directory as fallback
            if not storage_backend.exists(file_name):
                raise StorageError(f"File not found: neither {imports_path} nor {file_name} exists")

            # Use root path
            full_path = file_name
            logger.warning(f"Found file in root directory instead of imports directory")

        try:
            # Create a temporary file to work with
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Read content and write to temp file
                content = storage_backend.read_file(full_path, binary=True)
                with open(tmp_path, 'wb') as f:
                    f.write(content)

                # Import from the temp file using the importer module
                data = importer.import_from_excel(tmp_path, **format_options)

                # Create MediaPlan instance with version handling
                # The from_dict method will handle version compatibility and migration
                result = cls.from_dict(data)

                # Clean up
                os.unlink(tmp_path)

                logger.info(f"Media plan imported from Excel in workspace storage: {full_path}")
                return result

            except SchemaVersionError:
                # Clean up temp file and re-raise schema version errors
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                raise
            except Exception as e:
                # Clean up temp file in case of error
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                raise e

        except SchemaVersionError:
            # Re-raise schema version errors as-is
            raise
        except Exception as e:
            if not isinstance(e, StorageError):
                raise StorageError(f"Failed to import media plan from Excel: {e}")
            raise
    else:
        # Use local file system
        # Full path in local file system
        full_path = os.path.join(file_path, file_name)

        # Check if file exists
        if not os.path.exists(full_path):
            raise StorageError(f"File not found: {full_path}")

        try:
            # Import from Excel using the importer module and create MediaPlan instance
            data = importer.import_from_excel(full_path, **format_options)

            # Create MediaPlan instance with version handling
            # The from_dict method will handle version compatibility and migration
            result = cls.from_dict(data)

            logger.info(f"Media plan imported from Excel at: {full_path}")
            return result

        except SchemaVersionError:
            # Re-raise schema version errors as-is
            raise
        except Exception as e:
            raise StorageError(f"Failed to import media plan from Excel: {e}")


# Also update the update_from_excel_method to handle version compatibility
def update_from_excel_method(self, file_path: str, **options) -> None:
    """
    Update the media plan from an Excel file with version handling.

    Args:
        file_path: Path to the Excel file.
        **options: Additional import options.

    Raises:
        ValidationError: If the Excel file is invalid.
        StorageError: If the update fails.
        SchemaVersionError: If schema version compatibility issues arise.
    """
    try:
        # Get current plan as dictionary
        current_data = self.to_dict()

        # Import from Excel
        updated_data = importer.update_from_excel(current_data, file_path, **options)

        # Handle enum field values to avoid validation errors
        updated_data = _sanitize_data_for_model(updated_data)

        # Apply version compatibility checking to the updated data
        # This will handle any version differences and perform migration if needed
        temp_instance = self.__class__.from_dict(updated_data)

        # If we get here, the update is compatible, so apply changes in-place
        if "meta" in updated_data:
            # Update selectively to preserve ID and other metadata
            if "comments" in updated_data["meta"]:
                self.meta.comments = updated_data["meta"]["comments"]
            # Update schema version if it was changed during compatibility handling
            if "schema_version" in updated_data["meta"]:
                self.meta.schema_version = updated_data["meta"]["schema_version"]

        if "campaign" in updated_data:
            # Create a new campaign object and replace the current one
            from mediaplanpy.models.campaign import Campaign
            new_campaign = Campaign.from_dict(updated_data["campaign"])

            # Set each attribute
            for key, value in updated_data["campaign"].items():
                if hasattr(self.campaign, key):
                    try:
                        setattr(self.campaign, key, getattr(new_campaign, key))
                    except Exception as e:
                        # Skip attributes that cause validation errors
                        logger.warning(f"Could not set campaign attribute {key}: {e}")

        if "lineitems" in updated_data:
            # Clear existing line items and add new ones
            self.lineitems.clear()

            # Add each line item
            for line_item_data in updated_data["lineitems"]:
                try:
                    self.add_lineitem(line_item_data)
                except Exception as e:
                    # Log error but continue with other line items
                    logger.warning(f"Could not add line item: {e}")

        logger.info(f"Media plan updated from Excel: {file_path}")

    except SchemaVersionError:
        # Re-raise schema version errors as-is
        raise
    except Exception as e:
        raise StorageError(f"Failed to update media plan from Excel: {e}")

# Keep existing methods for update_from_excel_path and validate_excel
def update_from_excel_method(self, file_path: str, **options) -> None:
    """
    Update the media plan from an Excel file.

    Args:
        file_path: Path to the Excel file.
        **options: Additional import options.

    Raises:
        ValidationError: If the Excel file is invalid.
        StorageError: If the update fails.
    """
    try:
        # Get current plan as dictionary
        current_data = self.to_dict()

        # Update from Excel
        updated_data = importer.update_from_excel(current_data, file_path, **options)

        # Handle enum field values to avoid validation errors
        updated_data = _sanitize_data_for_model(updated_data)

        # Update in-place
        if "meta" in updated_data:
            # Update selectively to preserve ID and other metadata
            if "comments" in updated_data["meta"]:
                self.meta.comments = updated_data["meta"]["comments"]

        if "campaign" in updated_data:
            # Create a new campaign object and replace the current one
            from mediaplanpy.models.campaign import Campaign
            new_campaign = Campaign.from_dict(updated_data["campaign"])

            # Set each attribute
            for key, value in updated_data["campaign"].items():
                if hasattr(self.campaign, key):
                    try:
                        setattr(self.campaign, key, getattr(new_campaign, key))
                    except Exception as e:
                        # Skip attributes that cause validation errors
                        logger.warning(f"Could not set campaign attribute {key}: {e}")

        if "lineitems" in updated_data:
            # Clear existing line items and add new ones
            self.lineitems.clear()

            # Add each line item
            for line_item_data in updated_data["lineitems"]:
                try:
                    self.add_lineitem(line_item_data)
                except Exception as e:
                    # Log error but continue with other line items
                    logger.warning(f"Could not add line item: {e}")

        logger.info(f"Media plan updated from Excel: {file_path}")

    except Exception as e:
        raise StorageError(f"Failed to update media plan from Excel: {e}")


def validate_excel_class_method(cls, file_path: str, schema_version: Optional[str] = None) -> List[str]:
    """
    Validate an Excel file against the schema.

    Args:
        file_path: Path to the Excel file.
        schema_version: Optional schema version to validate against.

    Returns:
        A list of validation error messages, empty if validation succeeds.

    Raises:
        ValidationError: If the validation process fails.
    """
    try:
        # Validate Excel file
        errors = validate_excel(file_path, schema_version=schema_version)

        if not errors:
            logger.info(f"Excel file validated successfully: {file_path}")
        else:
            logger.warning(f"Excel file validation failed with {len(errors)} errors: {file_path}")

        return errors

    except Exception as e:
        raise ValidationError(f"Failed to validate Excel file: {e}")


def _sanitize_data_for_model(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize imported data to avoid validation errors when creating model instances.

    Args:
        data: The media plan data to sanitize.

    Returns:
        Sanitized media plan data.
    """
    import copy
    sanitized = copy.deepcopy(data)

    # Handle Campaign-specific enum fields
    if "campaign" in sanitized:
        campaign = sanitized["campaign"]

        # Handle audience_gender field
        if "audience_gender" in campaign:
            if not campaign["audience_gender"] or campaign["audience_gender"] == "":
                campaign["audience_gender"] = "Any"  # Default value

        # Handle location_type field
        if "location_type" in campaign:
            if not campaign["location_type"] or campaign["location_type"] == "":
                campaign["location_type"] = "Country"  # Default value

    # Handle Line Item-specific enum fields
    if "lineitems" in sanitized:
        for lineitem in sanitized["lineitems"]:
            # Handle location_type field
            if "location_type" in lineitem:
                if not lineitem["location_type"] or lineitem["location_type"] == "":
                    lineitem["location_type"] = "Country"  # Default value

    return sanitized

# Patch methods into MediaPlan class
def patch_mediaplan_excel_methods():
    """
    Add the Excel import/export methods to the MediaPlan class.
    """
    # Export to Excel
    MediaPlan.export_to_excel = export_to_excel_method

    # Import from Excel
    MediaPlan.import_from_excel = import_from_excel_method

    # Keep existing methods
    MediaPlan.update_from_excel_path = update_from_excel_method
    MediaPlan.validate_excel = validate_excel_class_method

    logger.debug("Added standardized Excel methods to MediaPlan class")

# Apply patches when this module is imported
patch_mediaplan_excel_methods()