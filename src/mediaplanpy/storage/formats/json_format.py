"""
Enhanced JSON format handler for mediaplanpy with version validation and compatibility.

This module provides a JSON format handler for serializing and
deserializing media plans with proper version handling and validation.
"""

import json
import logging
from typing import Dict, Any, BinaryIO, TextIO, Union, Optional

from mediaplanpy.exceptions import StorageError, SchemaVersionError
from mediaplanpy.storage.formats.base import FormatHandler, register_format

logger = logging.getLogger("mediaplanpy.storage.formats.json")


@register_format
class JsonFormatHandler(FormatHandler):
    """
    Handler for JSON format with version validation and compatibility checking.

    Serializes and deserializes media plans to/from JSON format while ensuring
    schema version compatibility and providing migration warnings.
    """

    format_name = "json"
    file_extension = "json"
    media_types = ["application/json"]

    def __init__(self, indent: int = 2, ensure_ascii: bool = False,
                 validate_version: bool = True, **kwargs):
        """
        Initialize the JSON format handler.

        Args:
            indent: Number of spaces for indentation.
            ensure_ascii: If True, guarantee that all output is ASCII.
            validate_version: If True, validate schema versions during operations.
            **kwargs: Additional JSON encoding options.
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self.validate_version = validate_version
        self.options = kwargs

    def validate_schema_version(self, data: Dict[str, Any]) -> None:
        """
        Validate schema version in media plan data.

        Args:
            data: Media plan data to validate

        Raises:
            SchemaVersionError: If version is invalid or incompatible
        """
        if not self.validate_version:
            return

        # Extract schema version
        schema_version = data.get("meta", {}).get("schema_version")
        if not schema_version:
            logger.warning("No schema version found in media plan data")
            return

        try:
            from mediaplanpy.schema.version_utils import (
                normalize_version,
                get_compatibility_type,
                get_migration_recommendation
            )

            # Normalize and check compatibility
            normalized_version = normalize_version(schema_version)
            compatibility = get_compatibility_type(normalized_version)

            if compatibility == "unsupported":
                recommendation = get_migration_recommendation(normalized_version)
                raise SchemaVersionError(
                    f"Schema version '{schema_version}' is not supported. "
                    f"{recommendation.get('message', 'Upgrade required.')}"
                )
            elif compatibility == "deprecated":
                logger.warning(
                    f"Schema version '{schema_version}' is deprecated. "
                    "Consider upgrading to current version."
                )
            elif compatibility == "forward_minor":
                logger.warning(
                    f"Schema version '{schema_version}' is newer than current SDK supports. "
                    "Some features may not be available."
                )

        except ImportError:
            # Fallback validation if version utilities not available
            import re
            # Remove 'v' prefix and check for 2-digit format
            clean_version = schema_version.lstrip('v')
            if not re.match(r'^[0-9]+\.[0-9]+(\.[0-9]+)?$', clean_version):
                raise SchemaVersionError(f"Invalid schema version format: '{schema_version}'")

    def normalize_version_in_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize schema version in data to 2-digit format.

        Args:
            data: Media plan data

        Returns:
            Data with normalized schema version
        """
        if not self.validate_version:
            return data

        schema_version = data.get("meta", {}).get("schema_version")
        if not schema_version:
            return data

        try:
            from mediaplanpy.schema.version_utils import normalize_version

            # Normalize version to 2-digit format
            normalized_version = normalize_version(schema_version)

            # Update the data if version changed
            if normalized_version != schema_version:
                logger.debug(f"Normalized version from '{schema_version}' to '{normalized_version}'")
                data = data.copy()  # Avoid modifying original
                if "meta" not in data:
                    data["meta"] = {}
                data["meta"]["schema_version"] = f"v{normalized_version}"

        except Exception as e:
            logger.warning(f"Could not normalize schema version '{schema_version}': {e}")

        return data

    def serialize(self, data: Dict[str, Any], **kwargs) -> str:
        """
        Serialize data to JSON string with version validation.

        Args:
            data: The data to serialize.
            **kwargs: Additional JSON encoding options.

        Returns:
            The serialized JSON string.

        Raises:
            StorageError: If the data cannot be serialized.
            SchemaVersionError: If version validation fails.
        """
        try:
            # Validate version before serialization
            self.validate_schema_version(data)

            # Normalize version format
            data = self.normalize_version_in_data(data)

            # Merge instance options with method kwargs
            options = {**self.options, **kwargs}
            indent = options.pop("indent", self.indent)
            ensure_ascii = options.pop("ensure_ascii", self.ensure_ascii)

            return json.dumps(
                data,
                indent=indent,
                ensure_ascii=ensure_ascii,
                **options
            )
        except SchemaVersionError:
            # Re-raise version errors
            raise
        except Exception as e:
            raise StorageError(f"Failed to serialize data to JSON: {e}")

    def deserialize(self, content: Union[str, bytes], **kwargs) -> Dict[str, Any]:
        """
        Deserialize content from JSON string with version validation.

        Args:
            content: The JSON content to deserialize.
            **kwargs: Additional JSON decoding options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be deserialized.
            SchemaVersionError: If version validation fails.
        """
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8')

            data = json.loads(content, **kwargs)

            # Validate version after deserialization
            self.validate_schema_version(data)

            # Normalize version format
            data = self.normalize_version_in_data(data)

            return data

        except SchemaVersionError:
            # Re-raise version errors
            raise
        except json.JSONDecodeError as e:
            raise StorageError(f"Failed to parse JSON content: {e}")
        except Exception as e:
            raise StorageError(f"Failed to deserialize JSON content: {e}")

    def serialize_to_file(self, data: Dict[str, Any], file_obj: Union[TextIO, BinaryIO], **kwargs) -> None:
        """
        Serialize data and write it to a file object with version validation.

        Args:
            data: The data to serialize.
            file_obj: A file-like object to write to.
            **kwargs: Additional JSON encoding options.

        Raises:
            StorageError: If the data cannot be serialized or written.
            SchemaVersionError: If version validation fails.
        """
        try:
            # Validate version before serialization
            self.validate_schema_version(data)

            # Normalize version format
            data = self.normalize_version_in_data(data)

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
        except SchemaVersionError:
            # Re-raise version errors
            raise
        except Exception as e:
            raise StorageError(f"Failed to serialize and write JSON data: {e}")

    def deserialize_from_file(self, file_obj: Union[TextIO, BinaryIO], **kwargs) -> Dict[str, Any]:
        """
        Read and deserialize data from a file object with version validation.

        Args:
            file_obj: A file-like object to read from.
            **kwargs: Additional JSON decoding options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be read or deserialized.
            SchemaVersionError: If version validation fails.
        """
        try:
            # Check if we need to handle binary mode
            if hasattr(file_obj, 'mode') and 'b' in file_obj.mode:
                content = file_obj.read()
                return self.deserialize(content, **kwargs)
            else:
                data = json.load(file_obj, **kwargs)

                # Validate version after deserialization
                self.validate_schema_version(data)

                # Normalize version format
                data = self.normalize_version_in_data(data)

                return data

        except SchemaVersionError:
            # Re-raise version errors
            raise
        except json.JSONDecodeError as e:
            raise StorageError(f"Failed to parse JSON file: {e}")
        except Exception as e:
            raise StorageError(f"Failed to read and deserialize JSON data: {e}")

    def get_schema_version_from_data(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract schema version from media plan data.

        Args:
            data: Media plan data

        Returns:
            Schema version string or None if not found
        """
        return data.get("meta", {}).get("schema_version")

    def update_schema_version(self, data: Dict[str, Any], new_version: str) -> Dict[str, Any]:
        """
        Update schema version in media plan data.

        Args:
            data: Media plan data
            new_version: New schema version to set

        Returns:
            Updated data with new schema version
        """
        if self.validate_version:
            # Validate the new version
            try:
                from mediaplanpy.schema.version_utils import normalize_version
                normalized_version = normalize_version(new_version)
                new_version = f"v{normalized_version}"
            except Exception as e:
                logger.warning(f"Could not normalize new schema version '{new_version}': {e}")

        # Create a copy to avoid modifying original
        updated_data = data.copy()
        if "meta" not in updated_data:
            updated_data["meta"] = {}

        updated_data["meta"]["schema_version"] = new_version

        return updated_data