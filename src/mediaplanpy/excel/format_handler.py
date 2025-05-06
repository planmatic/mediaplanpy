"""
Excel format handler for mediaplanpy.

This module provides the ExcelFormatHandler class for serializing and
deserializing media plans to/from Excel format.
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
    Handler for Excel format.

    Serializes and deserializes media plans to/from Excel format.
    """

    format_name = "excel"
    file_extension = "xlsx"
    media_types = ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]

    def __init__(self, template_path: Optional[str] = None, **kwargs):
        """
        Initialize the Excel format handler.

        Args:
            template_path: Optional path to an Excel template file.
            **kwargs: Additional Excel options.
        """
        self.template_path = template_path
        self.options = kwargs

    def serialize(self, data: Dict[str, Any], **kwargs) -> bytes:
        """
        Serialize data to Excel binary format.

        Args:
            data: The data to serialize.
            **kwargs: Additional Excel options.

        Returns:
            The serialized Excel binary data.

        Raises:
            StorageError: If the data cannot be serialized.
        """
        try:
            # Create a workbook for serialization
            workbook = self._create_workbook(data, **kwargs)

            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                workbook.save(tmp.name)
                tmp_path = tmp.name

            # Read the binary content
            with open(tmp_path, 'rb') as f:
                binary_content = f.read()

            # Clean up the temp file
            os.unlink(tmp_path)

            return binary_content
        except Exception as e:
            raise StorageError(f"Failed to serialize data to Excel: {e}")

    def deserialize(self, content: bytes, **kwargs) -> Dict[str, Any]:
        """
        Deserialize content from Excel binary format.

        Args:
            content: The Excel binary content to deserialize.
            **kwargs: Additional Excel options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be deserialized.
        """
        try:
            # Save content to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # Load the workbook
            workbook = openpyxl.load_workbook(tmp_path)

            # Convert to media plan structure
            media_plan = self._extract_media_plan(workbook, **kwargs)

            # Clean up
            os.unlink(tmp_path)

            return media_plan
        except Exception as e:
            raise StorageError(f"Failed to deserialize Excel content: {e}")

    def serialize_to_file(self, data: Dict[str, Any], file_obj: BinaryIO, **kwargs) -> None:
        """
        Serialize data and write it to a file object.

        Args:
            data: The data to serialize.
            file_obj: A file-like object to write to.
            **kwargs: Additional Excel options.

        Raises:
            StorageError: If the data cannot be serialized or written.
        """
        try:
            binary_data = self.serialize(data, **kwargs)
            file_obj.write(binary_data)
        except Exception as e:
            raise StorageError(f"Failed to serialize and write Excel data: {e}")

    def deserialize_from_file(self, file_obj: BinaryIO, **kwargs) -> Dict[str, Any]:
        """
        Read and deserialize data from a file object.

        Args:
            file_obj: A file-like object to read from.
            **kwargs: Additional Excel options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be read or deserialized.
        """
        try:
            content = file_obj.read()
            return self.deserialize(content, **kwargs)
        except Exception as e:
            raise StorageError(f"Failed to read and deserialize Excel data: {e}")

    def _create_workbook(self, data: Dict[str, Any], **kwargs) -> Workbook:
        """
        Create a workbook from media plan data.

        Args:
            data: The media plan data.
            **kwargs: Additional options.

        Returns:
            An openpyxl Workbook object.
        """
        # This is a placeholder. Actual implementation will be in the exporter module.
        # For now, just create a simple workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Media Plan"
        sheet['A1'] = "Media Plan Data"

        return workbook

    def _extract_media_plan(self, workbook: Workbook, **kwargs) -> Dict[str, Any]:
        """
        Extract media plan data from a workbook.

        Args:
            workbook: The openpyxl Workbook.
            **kwargs: Additional options.

        Returns:
            The media plan data as a dictionary.
        """
        # This is a placeholder. Actual implementation will be in the importer module.
        # For now, just return an empty media plan structure
        return {
            "meta": {
                "schema_version": "v1.0.0",
                "id": "excel_import",
                "created_by": "excel_import",
                "created_at": "2025-05-06T00:00:00Z"
            },
            "campaign": {
                "id": "campaign_from_excel",
                "name": "Campaign from Excel",
                "objective": "Imported from Excel",
                "start_date": "2025-06-01",
                "end_date": "2025-12-31",
                "budget_total": 0
            },
            "lineitems": []
        }