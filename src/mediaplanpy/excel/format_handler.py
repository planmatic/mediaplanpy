"""
Excel format handler for mediaplanpy - Updated for v2.0 Schema Support Only.

This module provides the ExcelFormatHandler class for serializing and
deserializing media plans to/from Excel format using v2.0 schema exclusively.
"""

import os
import logging
import tempfile
from typing import Dict, Any, BinaryIO, TextIO, Union, Optional

import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

from mediaplanpy.exceptions import StorageError
from mediaplanpy.storage.formats.base import FormatHandler, register_format

logger = logging.getLogger("mediaplanpy.excel.format_handler")


@register_format
class ExcelFormatHandler(FormatHandler):
    """
    Handler for Excel format supporting v2.0 schema exclusively.

    Serializes and deserializes media plans to/from Excel format using
    the v2.0 schema with all new fields and dictionary configuration.
    """

    format_name = "excel"
    file_extension = "xlsx"
    media_types = ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]

    def __init__(self, template_path: Optional[str] = None, **kwargs):
        """
        Initialize the Excel format handler for v2.0 schema.

        Args:
            template_path: Optional path to an Excel template file
            **kwargs: Additional Excel options
        """
        self.template_path = template_path
        self.options = kwargs

    def serialize(self, data: Dict[str, Any], **kwargs) -> bytes:
        """
        Serialize data to Excel binary format using v2.0 schema.

        Args:
            data: The data to serialize (must be v2.0 schema)
            **kwargs: Additional Excel options

        Returns:
            The serialized Excel binary data

        Raises:
            StorageError: If the data cannot be serialized or is not v2.0 schema
        """
        try:
            # Validate schema version
            schema_version = data.get("meta", {}).get("schema_version", "unknown")
            if not self._is_v2_schema_version(schema_version):
                raise StorageError(f"Excel format handler only supports v2.0 schema. Found: {schema_version}")

            # Create a workbook for serialization
            workbook = self._create_v2_workbook(data, **kwargs)

            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                workbook.save(tmp.name)
                tmp_path = tmp.name

            # Read the binary content
            with open(tmp_path, 'rb') as f:
                binary_content = f.read()

            # Clean up the temp file
            os.unlink(tmp_path)

            logger.info("Successfully serialized v2.0 media plan to Excel format")
            return binary_content

        except Exception as e:
            raise StorageError(f"Failed to serialize data to Excel: {e}")

    def deserialize(self, content: bytes, **kwargs) -> Dict[str, Any]:
        """
        Deserialize content from Excel binary format to v2.0 schema.

        Args:
            content: The Excel binary content to deserialize
            **kwargs: Additional Excel options

        Returns:
            The deserialized data as a dictionary in v2.0 schema format

        Raises:
            StorageError: If the content cannot be deserialized or is not v2.0 compatible
        """
        try:
            # Save content to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # Load the workbook
            workbook = openpyxl.load_workbook(tmp_path)

            # Convert to v2.0 media plan structure
            media_plan = self._extract_v2_media_plan(workbook, **kwargs)

            # Clean up
            os.unlink(tmp_path)

            logger.info("Successfully deserialized Excel content to v2.0 media plan")
            return media_plan

        except Exception as e:
            raise StorageError(f"Failed to deserialize Excel content: {e}")

    def serialize_to_file(self, data: Dict[str, Any], file_obj: BinaryIO, **kwargs) -> None:
        """
        Serialize data and write it to a file object using v2.0 schema.

        Args:
            data: The data to serialize (must be v2.0 schema)
            file_obj: A file-like object to write to
            **kwargs: Additional Excel options

        Raises:
            StorageError: If the data cannot be serialized or written
        """
        try:
            binary_data = self.serialize(data, **kwargs)
            file_obj.write(binary_data)
            logger.debug("Successfully serialized v2.0 media plan to file object")
        except Exception as e:
            raise StorageError(f"Failed to serialize and write Excel data: {e}")

    def deserialize_from_file(self, file_obj: BinaryIO, **kwargs) -> Dict[str, Any]:
        """
        Read and deserialize data from a file object to v2.0 schema.

        Args:
            file_obj: A file-like object to read from
            **kwargs: Additional Excel options

        Returns:
            The deserialized data as a dictionary in v2.0 schema format

        Raises:
            StorageError: If the content cannot be read or deserialized
        """
        try:
            content = file_obj.read()
            media_plan = self.deserialize(content, **kwargs)
            logger.debug("Successfully deserialized file object to v2.0 media plan")
            return media_plan
        except Exception as e:
            raise StorageError(f"Failed to read and deserialize Excel data: {e}")

    def _is_v2_schema_version(self, version: str) -> bool:
        """
        Check if the schema version is v2.0.

        Args:
            version: The schema version to check

        Returns:
            True if the version is v2.0, False otherwise
        """
        if not version:
            return False

        # Normalize version format (handle both "2.0" and "v2.0")
        normalized = version.replace("v", "") if version.startswith("v") else version
        return normalized == "2.0"

    def _create_v2_workbook(self, data: Dict[str, Any], **kwargs) -> Workbook:
        """
        Create a workbook from v2.0 media plan data.

        Args:
            data: The v2.0 media plan data
            **kwargs: Additional options

        Returns:
            An openpyxl Workbook object with v2.0 structure
        """
        # Import the exporter to leverage its functionality
        from mediaplanpy.excel.exporter import _create_v2_workbook, _populate_v2_workbook, _add_v2_validation_and_formatting

        # Create workbook with v2.0 structure
        workbook = _create_v2_workbook()

        # Populate with data
        include_documentation = kwargs.get('include_documentation', True)
        _populate_v2_workbook(workbook, data, include_documentation)

        # Add validation and formatting
        _add_v2_validation_and_formatting(workbook)

        logger.debug("Created v2.0 workbook with all sheets and formatting")
        return workbook

    def _extract_v2_media_plan(self, workbook: Workbook, **kwargs) -> Dict[str, Any]:
        """
        Extract v2.0 media plan data from a workbook.

        Args:
            workbook: The openpyxl Workbook
            **kwargs: Additional options

        Returns:
            The media plan data as a dictionary in v2.0 format

        Raises:
            StorageError: If extraction fails or data is not v2.0 compatible
        """
        # Import the importer to leverage its functionality
        from mediaplanpy.excel.importer import _import_v2_media_plan, _detect_schema_version

        # Detect schema version
        schema_version = _detect_schema_version(workbook)
        if not self._is_v2_schema_version(schema_version):
            raise StorageError(
                f"Excel content is not v2.0 compatible. Found schema version: {schema_version}. "
                f"Please use a v2.0 compatible Excel file."
            )

        # Extract v2.0 media plan
        media_plan = _import_v2_media_plan(workbook)

        logger.debug("Extracted v2.0 media plan from workbook")
        return media_plan

    def validate_media_plan_structure(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate media plan structure for v2.0 schema compatibility.

        Args:
            data: The media plan data to validate

        Returns:
            List of validation errors, empty if valid
        """
        errors = []

        # Check schema version
        schema_version = data.get("meta", {}).get("schema_version")
        if not self._is_v2_schema_version(schema_version):
            errors.append(f"Schema version must be v2.0 for Excel format, found: {schema_version}")

        # Check required top-level sections
        required_sections = ["meta", "campaign", "lineitems"]
        for section in required_sections:
            if section not in data:
                errors.append(f"Missing required section: {section}")

        # Check meta section for v2.0 required fields
        if "meta" in data:
            meta = data["meta"]
            required_meta_fields = ["id", "schema_version", "created_by_name", "created_at"]
            for field in required_meta_fields:
                if field not in meta or not meta[field]:
                    errors.append(f"Missing required meta field: {field}")

        # Check campaign section for required fields
        if "campaign" in data:
            campaign = data["campaign"]
            required_campaign_fields = ["id", "name", "objective", "start_date", "end_date", "budget_total"]
            for field in required_campaign_fields:
                if field not in campaign or campaign[field] is None:
                    errors.append(f"Missing required campaign field: {field}")

        # Check lineitems structure
        if "lineitems" in data:
            if not isinstance(data["lineitems"], list):
                errors.append("lineitems must be a list")
            else:
                for i, lineitem in enumerate(data["lineitems"]):
                    if not isinstance(lineitem, dict):
                        errors.append(f"Line item {i} must be a dictionary")
                        continue

                    required_lineitem_fields = ["id", "name", "start_date", "end_date", "cost_total"]
                    for field in required_lineitem_fields:
                        if field not in lineitem or lineitem[field] is None:
                            errors.append(f"Line item {i} missing required field: {field}")

        # Check dictionary structure if present (optional in v2.0)
        if "dictionary" in data:
            dictionary = data["dictionary"]
            if not isinstance(dictionary, dict):
                errors.append("dictionary must be a dictionary object")
            else:
                # Validate dictionary sections
                valid_sections = ["custom_dimensions", "custom_metrics", "custom_costs"]
                for section_name, section_data in dictionary.items():
                    if section_name not in valid_sections:
                        errors.append(f"Invalid dictionary section: {section_name}")
                    elif not isinstance(section_data, dict):
                        errors.append(f"Dictionary section {section_name} must be a dictionary")

        return errors

    def get_supported_features(self) -> Dict[str, Any]:
        """
        Get information about supported features for v2.0 Excel format.

        Returns:
            Dictionary describing supported features
        """
        return {
            "schema_version": "2.0",
            "format_name": self.format_name,
            "file_extension": self.file_extension,
            "supports_dictionary": True,
            "supports_all_v2_fields": True,
            "worksheets": [
                "Metadata",
                "Campaign",
                "Line Items",
                "Dictionary",
                "Documentation"
            ],
            "new_v2_features": {
                "campaign_fields": [
                    "budget_currency", "agency_id", "agency_name",
                    "advertiser_id", "advertiser_name", "product_id",
                    "campaign_type_id", "campaign_type_name",
                    "workflow_status_id", "workflow_status_name"
                ],
                "lineitem_fields": [
                    "cost_currency", "dayparts", "dayparts_custom",
                    "inventory", "inventory_custom"
                ],
                "new_standard_metrics": [
                    "metric_engagements", "metric_followers", "metric_visits",
                    "metric_leads", "metric_sales", "metric_add_to_cart",
                    "metric_app_install", "metric_application_start", "metric_application_complete",
                    "metric_contact_us", "metric_download", "metric_signup",
                    "metric_max_daily_spend", "metric_max_daily_impressions", "metric_audience_size"
                ],
                "meta_fields": [
                    "created_by_name", "created_by_id", "is_current", "is_archived", "parent_id"
                ]
            }
        }

    def get_file_extension(self) -> str:
        """
        Get the file extension for Excel format.

        Returns:
            The file extension string
        """
        return f".{self.file_extension}"

    def is_binary_format(self) -> bool:
        """
        Check if this is a binary format.

        Returns:
            True for Excel format
        """
        return True