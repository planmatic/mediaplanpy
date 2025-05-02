"""
JSON format handler for mediaplanpy.

This module provides a JSON format handler for serializing and
deserializing media plans to/from JSON format.
"""

import json
import logging
from typing import Dict, Any, BinaryIO, TextIO, Union, Optional

from mediaplanpy.exceptions import StorageError
from mediaplanpy.storage.formats.base import FormatHandler, register_format

logger = logging.getLogger("mediaplanpy.storage.formats.json")


@register_format
class JsonFormatHandler(FormatHandler):
    """
    Handler for JSON format.

    Serializes and deserializes media plans to/from JSON format.
    """

    format_name = "json"
    file_extension = "json"
    media_types = ["application/json"]

    def __init__(self, indent: int = 2, ensure_ascii: bool = False, **kwargs):
        """
        Initialize the JSON format handler.

        Args:
            indent: Number of spaces for indentation.
            ensure_ascii: If True, guarantee that all output is ASCII.
            **kwargs: Additional JSON encoding options.
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.options = kwargs

    def serialize(self, data: Dict[str, Any], **kwargs) -> str:
        """
        Serialize data to JSON string.

        Args:
            data: The data to serialize.
            **kwargs: Additional JSON encoding options.

        Returns:
            The serialized JSON string.

        Raises:
            StorageError: If the data cannot be serialized.
        """
        # Merge instance options with method kwargs
        options = {**self.options, **kwargs}
        indent = options.pop("indent", self.indent)
        ensure_ascii = options.pop("ensure_ascii", self.ensure_ascii)

        try:
            return json.dumps(
                data,
                indent=indent,
                ensure_ascii=ensure_ascii,
                **options
            )
        except Exception as e:
            raise StorageError(f"Failed to serialize data to JSON: {e}")

    def deserialize(self, content: Union[str, bytes], **kwargs) -> Dict[str, Any]:
        """
        Deserialize content from JSON string.

        Args:
            content: The JSON content to deserialize.
            **kwargs: Additional JSON decoding options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be deserialized.
        """
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8')

            return json.loads(content, **kwargs)
        except Exception as e:
            raise StorageError(f"Failed to deserialize JSON content: {e}")

    def serialize_to_file(self, data: Dict[str, Any], file_obj: Union[TextIO, BinaryIO], **kwargs) -> None:
        """
        Serialize data and write it to a file object.

        Args:
            data: The data to serialize.
            file_obj: A file-like object to write to.
            **kwargs: Additional JSON encoding options.

        Raises:
            StorageError: If the data cannot be serialized or written.
        """
        try:
            # Merge instance options with method kwargs
            options = {**self.options, **kwargs}
            indent = options.pop("indent", self.indent)
            ensure_ascii = options.pop("ensure_ascii", self.ensure_ascii)

            # Check if we need to handle binary mode
            if hasattr(file_obj, 'mode') and 'b' in file_obj.mode:
                json_str = json.dumps(
                    data,
                    indent=indent,
                    ensure_ascii=ensure_ascii,
                    **options
                )
                file_obj.write(json_str.encode('utf-8'))
            else:
                json.dump(
                    data,
                    file_obj,
                    indent=indent,
                    ensure_ascii=ensure_ascii,
                    **options
                )
        except Exception as e:
            raise StorageError(f"Failed to serialize and write JSON data: {e}")

    def deserialize_from_file(self, file_obj: Union[TextIO, BinaryIO], **kwargs) -> Dict[str, Any]:
        """
        Read and deserialize data from a file object.

        Args:
            file_obj: A file-like object to read from.
            **kwargs: Additional JSON decoding options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be read or deserialized.
        """
        try:
            # Check if we need to handle binary mode
            if hasattr(file_obj, 'mode') and 'b' in file_obj.mode:
                content = file_obj.read()
                return self.deserialize(content, **kwargs)
            else:
                return json.load(file_obj, **kwargs)
        except Exception as e:
            raise StorageError(f"Failed to read and deserialize JSON data: {e}")