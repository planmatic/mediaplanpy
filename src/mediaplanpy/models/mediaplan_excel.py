"""
Integration of MediaPlan models with Excel functionality.

This module enhances the MediaPlan model with methods for exporting to
and importing from Excel format.
"""

import os
import logging
from typing import Dict, Any, Optional, Union, List

from mediaplanpy.exceptions import StorageError, ValidationError
from mediaplanpy.models.mediaplan import MediaPlan
from mediaplanpy.excel.exporter import export_to_excel
from mediaplanpy.excel.importer import import_from_excel, update_from_excel
from mediaplanpy.excel.validator import validate_excel
from mediaplanpy.workspace import WorkspaceManager

logger = logging.getLogger("mediaplanpy.models.mediaplan_excel")


# Add Excel-related methods to MediaPlan class
def export_to_excel_method(self, path: Optional[str] = None,
                          template_path: Optional[str] = None,
                          include_documentation: bool = True,
                          **options) -> str:
    """
    Export the media plan to Excel format.

    Args:
        path: Optional path to save the Excel file. If None, a default path is generated.
        template_path: Optional path to an Excel template file.
        include_documentation: Whether to include a documentation sheet.
        **options: Additional export options.

    Returns:
        The path where the Excel file was saved.

    Raises:
        StorageError: If the export fails.
    """
    try:
        # Convert model to dictionary
        data = self.to_dict()

        # Export to Excel
        exported_path = export_to_excel(data, path, template_path, include_documentation, **options)

        logger.info(f"Media plan exported to Excel: {exported_path}")
        return exported_path

    except Exception as e:
        raise StorageError(f"Failed to export media plan to Excel: {e}")


def from_excel_class_method(cls, file_path: str, **options) -> 'MediaPlan':
    """
    Create a new MediaPlan instance from an Excel file.

    Args:
        file_path: Path to the Excel file.
        **options: Additional import options.

    Returns:
        A new MediaPlan instance.

    Raises:
        ValidationError: If the Excel file is invalid.
        StorageError: If the import fails.
    """
    try:
        # Import from Excel
        data = import_from_excel(file_path, **options)

        # Handle enum field values to avoid validation errors
        data = _sanitize_data_for_model(data)

        # Convert to MediaPlan instance
        media_plan = cls.from_dict(data)

        logger.info(f"Media plan created from Excel: {file_path}")
        return media_plan

    except Exception as e:
        raise StorageError(f"Failed to create media plan from Excel: {e}")


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
        updated_data = update_from_excel(current_data, file_path, **options)

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


def export_to_excel_workspace(self, workspace_manager: WorkspaceManager,
                             path: Optional[str] = None,
                             template_path: Optional[str] = None,
                             **options) -> str:
    """
    Export the media plan to Excel using workspace settings.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: Optional path to save the Excel file. If None, a default path is generated.
        template_path: Optional path to an Excel template file. If None, uses the workspace default.
        **options: Additional export options.

    Returns:
        The path where the Excel file was saved.

    Raises:
        StorageError: If the export fails.
    """
    try:
        # Check if workspace is loaded
        if not workspace_manager.is_loaded:
            workspace_manager.load()

        # Get excel settings from workspace
        excel_config = workspace_manager.get_excel_config()

        # If template_path not provided, check workspace settings
        if template_path is None and "template_path" in excel_config:
            template_path = excel_config["template_path"]

        # Determine path (storage-relative)
        if not path and "default_export_path" in excel_config:
            # Use workspace default export path
            path = excel_config["default_export_path"]

            # Check if we need to add campaign ID or timestamp
            if "{campaign_id}" in path:
                path = path.replace("{campaign_id}", self.campaign.id)
            if "{timestamp}" in path:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = path.replace("{timestamp}", timestamp)

        # Convert model to dictionary
        data = self.to_dict()

        # Export to Excel
        storage_backend = workspace_manager.get_storage_backend()

        # Export to a temp file first
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        # Export to the temp file
        export_to_excel(data, tmp_path, template_path, **options)

        # Read the content
        with open(tmp_path, "rb") as f:
            content = f.read()

        # Clean up temp file
        os.unlink(tmp_path)

        # Write to storage backend
        if not path:
            # Default path based on campaign ID
            path = f"{self.campaign.id}.xlsx"

        storage_backend.write_file(path, content)

        logger.info(f"Media plan exported to Excel in workspace: {path}")
        return path

    except Exception as e:
        raise StorageError(f"Failed to export media plan to Excel in workspace: {e}")


def from_excel_workspace_class_method(cls, workspace_manager: WorkspaceManager,
                                     path: str, **options) -> 'MediaPlan':
    """
    Create a new MediaPlan instance from an Excel file in workspace storage.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: Path to the Excel file in the workspace storage.
        **options: Additional import options.

    Returns:
        A new MediaPlan instance.

    Raises:
        ValidationError: If the Excel file is invalid.
        StorageError: If the import fails.
    """
    try:
        # Check if workspace is loaded
        if not workspace_manager.is_loaded:
            workspace_manager.load()

        # Get storage backend
        storage_backend = workspace_manager.get_storage_backend()

        # Check if file exists
        if not storage_backend.exists(path):
            raise StorageError(f"Excel file not found in workspace: {path}")

        # Read content to a temp file
        content = storage_backend.read_file(path, binary=True)

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Import from the temp file
        media_plan = cls.import_from_excel_path(tmp_path, **options)

        # Clean up
        os.unlink(tmp_path)

        logger.info(f"Media plan created from Excel in workspace: {path}")
        return media_plan

    except Exception as e:
        raise StorageError(f"Failed to create media plan from Excel in workspace: {e}")


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
MediaPlan.export_to_excel = export_to_excel_workspace
MediaPlan.export_to_excel_path = export_to_excel_method
MediaPlan.import_from_excel = classmethod(from_excel_workspace_class_method)
MediaPlan.import_from_excel_path = classmethod(from_excel_class_method)
MediaPlan.update_from_excel_path = update_from_excel_method
MediaPlan.validate_excel = classmethod(validate_excel_class_method)
