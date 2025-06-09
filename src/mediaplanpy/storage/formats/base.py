"""
Enhanced base format interface for mediaplanpy with version validation support.

This module defines the abstract base class for file format handlers with
shared version validation and compatibility checking capabilities.
"""

import abc
import logging
from typing import Dict, Any, BinaryIO, TextIO, Union, Optional, Type, List

from mediaplanpy.exceptions import StorageError, SchemaVersionError

logger = logging.getLogger("mediaplanpy.storage.formats.base")


class FormatHandler(abc.ABC):
    """
    Abstract base class for format handlers with version validation support.
    """

    # Format name (used for registration and lookup)
    format_name: str = None

    # File extension (without the dot)
    file_extension: str = None

    # Media types for this format
    media_types: list = []

    # Whether this format requires binary mode
    is_binary: bool = False

    @classmethod
    def get_file_extension(cls) -> str:
        """
        Get the file extension for this format.

        Returns:
            The file extension (without the dot).
        """
        if cls.file_extension is None:
            raise NotImplementedError(f"File extension not defined for {cls.__name__}")
        return cls.file_extension

    @classmethod
    def matches_extension(cls, filename: str) -> bool:
        """
        Check if a filename matches this format's extension.

        Args:
            filename: The filename to check.

        Returns:
            True if the filename has this format's extension, False otherwise.
        """
        if not filename or not cls.file_extension:
            return False

        try:
            extension = filename.split('.')[-1].lower()
            return extension == cls.file_extension.lower()
        except (IndexError, AttributeError):
            return False

    def validate_media_plan_structure(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate media plan structure using JSON schema validation.

        This method now leverages the actual JSON schema definitions instead of
        hard-coding required fields, ensuring version-aware validation.

        Args:
            data: Media plan data to validate

        Returns:
            List of validation errors, empty if valid
        """
        errors = []

        # Get schema version from data to use appropriate validation
        schema_version = self.get_version_from_data(data)

        try:
            # Try to use the actual schema validator
            from mediaplanpy.schema import SchemaValidator

            validator = SchemaValidator()
            schema_errors = validator.validate(data, schema_version)

            if schema_errors:
                # Convert schema validation errors to format handler errors
                errors.extend([str(error) for error in schema_errors])

            return errors

        except ImportError:
            logger.warning("Schema validator not available, falling back to basic validation")
            return self._basic_structure_validation(data, schema_version)
        except Exception as e:
            logger.warning(f"Schema validation failed: {e}, falling back to basic validation")
            return self._basic_structure_validation(data, schema_version)

    def _basic_structure_validation(self, data: Dict[str, Any], schema_version: Optional[str] = None) -> List[str]:
        """
        Basic fallback validation when JSON schema validation is not available.

        This provides minimal validation and is version-aware for known differences.

        Args:
            data: Media plan data to validate
            schema_version: Schema version to guide validation

        Returns:
            List of validation errors
        """
        errors = []

        # Check for required top-level sections (consistent across versions)
        required_sections = ["meta", "campaign"]
        for section in required_sections:
            if section not in data:
                errors.append(f"Missing required section: {section}")

        # Version-aware meta field validation
        if "meta" in data:
            errors.extend(self._validate_meta_section(data["meta"], schema_version))

        # Version-aware campaign field validation
        if "campaign" in data:
            errors.extend(self._validate_campaign_section(data["campaign"], schema_version))

        # Validate line items if present
        if "lineitems" in data:
            errors.extend(self._validate_lineitems_section(data["lineitems"], schema_version))

        return errors

    def _validate_meta_section(self, meta: Dict[str, Any], schema_version: Optional[str] = None) -> List[str]:
        """
        Validate meta section with version-aware field requirements.

        Args:
            meta: Meta section data
            schema_version: Schema version for validation context

        Returns:
            List of validation errors for meta section
        """
        errors = []

        # Core fields required across all versions
        core_required_fields = ["id", "schema_version"]

        # Version-specific required fields
        if schema_version and schema_version.startswith(('v2.', '2.')):
            # v2.0 requires created_by_name instead of created_by
            version_required_fields = ["created_by_name"]
        else:
            # v1.0 and fallback requires created_by
            version_required_fields = ["created_by"]

        all_required_fields = core_required_fields + version_required_fields

        for field in all_required_fields:
            if field not in meta:
                errors.append(f"Missing required meta field: {field}")

        return errors

    def _validate_campaign_section(self, campaign: Dict[str, Any], schema_version: Optional[str] = None) -> List[str]:
        """
        Validate campaign section with version-aware field requirements.

        Args:
            campaign: Campaign section data
            schema_version: Schema version for validation context

        Returns:
            List of validation errors for campaign section
        """
        errors = []

        # Core fields required across all versions
        required_campaign_fields = ["id", "name", "objective", "start_date", "end_date"]

        for field in required_campaign_fields:
            if field not in campaign:
                errors.append(f"Missing required campaign field: {field}")

        # Optional v2.0 specific validations could be added here
        # but we avoid hard-coding them since they're optional

        return errors

    def _validate_lineitems_section(self, lineitems: Any, schema_version: Optional[str] = None) -> List[str]:
        """
        Validate lineitems section with version-aware field requirements.

        Args:
            lineitems: Lineitems section data
            schema_version: Schema version for validation context

        Returns:
            List of validation errors for lineitems section
        """
        errors = []

        if not isinstance(lineitems, list):
            errors.append("lineitems must be a list")
            return errors

        # Core fields required across all versions
        required_lineitem_fields = ["id", "name", "start_date", "end_date", "cost_total"]

        for i, lineitem in enumerate(lineitems):
            if not isinstance(lineitem, dict):
                errors.append(f"Line item {i} must be a dictionary")
                continue

            for field in required_lineitem_fields:
                if field not in lineitem:
                    errors.append(f"Line item {i}: missing required field: {field}")

        return errors

    def validate_with_schema_registry(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate using the schema registry if available.

        This is the preferred validation method as it uses the actual
        JSON schema definitions and is fully version-aware.

        Args:
            data: Media plan data to validate

        Returns:
            List of validation errors, empty if valid
        """
        try:
            from mediaplanpy.schema import SchemaRegistry, SchemaValidator

            # Get the schema version
            schema_version = self.get_version_from_data(data)
            if not schema_version:
                return ["No schema version found in data"]

            # Create validator with registry
            registry = SchemaRegistry()
            validator = SchemaValidator(registry=registry)

            # Validate against the specific schema version
            errors = validator.validate(data, schema_version)

            return [str(error) for error in errors] if errors else []

        except ImportError as e:
            logger.debug(f"Schema registry not available: {e}")
            return []  # Will fall back to basic validation
        except Exception as e:
            logger.warning(f"Schema registry validation failed: {e}")
            return [f"Schema validation error: {str(e)}"]

    def get_version_from_data(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract schema version from media plan data.

        Args:
            data: Media plan data

        Returns:
            Schema version string or None if not found
        """
        return data.get("meta", {}).get("schema_version")

    def validate_version_format(self, version: str) -> bool:
        """
        Validate that a version string follows expected format.

        Args:
            version: Version string to validate

        Returns:
            True if format is valid
        """
        if not version:
            return False

        try:
            from mediaplanpy.schema.version_utils import validate_version_format
            return validate_version_format(version)
        except ImportError:
            # Fallback validation
            import re
            # Allow both v1.0.0 and 1.0 formats
            return bool(re.match(r'^v?[0-9]+\.[0-9]+(\.[0-9]+)?$', version.strip()))

    def normalize_version(self, version: str) -> str:
        """
        Normalize version to standard 2-digit format.

        Args:
            version: Version string to normalize

        Returns:
            Normalized version string

        Raises:
            SchemaVersionError: If version format is invalid
        """
        if not version:
            raise SchemaVersionError("Version cannot be empty")

        try:
            from mediaplanpy.schema.version_utils import normalize_version
            return normalize_version(version)
        except ImportError:
            # Fallback normalization
            import re
            # Remove 'v' prefix and convert to X.Y format
            clean_version = version.lstrip('v')
            parts = clean_version.split('.')
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
            else:
                raise SchemaVersionError(f"Invalid version format: {version}")
        except Exception as e:
            raise SchemaVersionError(f"Failed to normalize version '{version}': {e}")

    def check_version_compatibility(self, version: str) -> Dict[str, Any]:
        """
        Check version compatibility with current SDK.

        Args:
            version: Schema version to check

        Returns:
            Dictionary with compatibility information
        """
        compatibility_info = {
            "version": version,
            "normalized_version": None,
            "is_compatible": False,
            "compatibility_type": "unknown",
            "warnings": [],
            "errors": []
        }

        try:
            # Normalize version
            normalized_version = self.normalize_version(version)
            compatibility_info["normalized_version"] = normalized_version

            # Get compatibility type
            try:
                from mediaplanpy.schema.version_utils import (
                    get_compatibility_type,
                    get_migration_recommendation
                )

                compatibility_type = get_compatibility_type(normalized_version)
                compatibility_info["compatibility_type"] = compatibility_type

                if compatibility_type == "native":
                    compatibility_info["is_compatible"] = True
                elif compatibility_type == "forward_minor":
                    compatibility_info["is_compatible"] = True
                    compatibility_info["warnings"].append(
                        f"Schema version {version} is newer than current SDK supports. "
                        "Some features may not be available."
                    )
                elif compatibility_type == "backward_compatible":
                    compatibility_info["is_compatible"] = True
                    compatibility_info["warnings"].append(
                        f"Schema version {version} will be upgraded during processing."
                    )
                elif compatibility_type == "deprecated":
                    compatibility_info["is_compatible"] = True
                    compatibility_info["warnings"].append(
                        f"Schema version {version} is deprecated. Consider upgrading."
                    )
                elif compatibility_type == "unsupported":
                    compatibility_info["is_compatible"] = False
                    recommendation = get_migration_recommendation(normalized_version)
                    compatibility_info["errors"].append(
                        recommendation.get("message", f"Schema version {version} is not supported")
                    )

            except ImportError:
                # Fallback compatibility check
                major_version = int(normalized_version.split('.')[0])
                if major_version >= 1:
                    compatibility_info["is_compatible"] = True
                else:
                    compatibility_info["is_compatible"] = False
                    compatibility_info["errors"].append(
                        f"Schema version {version} (major version {major_version}) is not supported"
                    )

        except SchemaVersionError as e:
            compatibility_info["errors"].append(str(e))
        except Exception as e:
            compatibility_info["errors"].append(f"Version compatibility check failed: {str(e)}")

        return compatibility_info

    def apply_version_migration_warnings(self, data: Dict[str, Any]) -> None:
        """
        Apply appropriate warnings based on version compatibility.

        Args:
            data: Media plan data
        """
        version = self.get_version_from_data(data)
        if not version:
            logger.warning("No schema version found in media plan data")
            return

        compatibility = self.check_version_compatibility(version)

        for warning in compatibility["warnings"]:
            logger.warning(warning)

        for error in compatibility["errors"]:
            logger.error(error)

    @abc.abstractmethod
    def serialize(self, data: Dict[str, Any], **kwargs) -> Union[str, bytes]:
        """
        Serialize data to the format's string or binary representation.

        Args:
            data: The data to serialize.
            **kwargs: Additional format-specific options.

        Returns:
            The serialized data as a string or bytes.

        Raises:
            StorageError: If the data cannot be serialized.
        """
        pass

    @abc.abstractmethod
    def deserialize(self, content: Union[str, bytes], **kwargs) -> Dict[str, Any]:
        """
        Deserialize content from the format's string or binary representation.

        Args:
            content: The content to deserialize.
            **kwargs: Additional format-specific options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be deserialized.
        """
        pass

    @abc.abstractmethod
    def serialize_to_file(self, data: Dict[str, Any], file_obj: Union[TextIO, BinaryIO], **kwargs) -> None:
        """
        Serialize data and write it to a file object.

        Args:
            data: The data to serialize.
            file_obj: A file-like object to write to.
            **kwargs: Additional format-specific options.

        Raises:
            StorageError: If the data cannot be serialized or written.
        """
        pass

    @abc.abstractmethod
    def deserialize_from_file(self, file_obj: Union[TextIO, BinaryIO], **kwargs) -> Dict[str, Any]:
        """
        Read and deserialize data from a file object.

        Args:
            file_obj: A file-like object to read from.
            **kwargs: Additional format-specific options.

        Returns:
            The deserialized data as a dictionary.

        Raises:
            StorageError: If the content cannot be read or deserialized.
        """
        pass


# Registry of format handlers
_format_registry = {}


def register_format(format_class: Type[FormatHandler]) -> Type[FormatHandler]:
    """
    Register a format handler class.

    This can be used as a decorator on format handler classes.

    Args:
        format_class: The format handler class to register.

    Returns:
        The format handler class (for decorator usage).

    Raises:
        ValueError: If the format handler has no format_name.
    """
    if not format_class.format_name:
        raise ValueError(f"Format handler {format_class.__name__} has no format_name")

    _format_registry[format_class.format_name] = format_class
    return format_class


def get_format_handler(format_name: str) -> Type[FormatHandler]:
    """
    Get a format handler class by name.

    Args:
        format_name: The name of the format handler.

    Returns:
        The format handler class.

    Raises:
        ValueError: If no format handler is registered with the given name.
    """
    if format_name not in _format_registry:
        raise ValueError(f"No format handler registered for format '{format_name}'")

    return _format_registry[format_name]


def get_format_handler_for_file(filename: str) -> Optional[Type[FormatHandler]]:
    """
    Get a format handler class based on a filename.

    Args:
        filename: The name of the file.

    Returns:
        The format handler class, or None if no handler matches the filename.
    """
    try:
        extension = filename.split('.')[-1].lower()
        for handler_class in _format_registry.values():
            if handler_class.file_extension == extension:
                return handler_class
    except (IndexError, AttributeError):
        pass

    return None


def validate_all_formats_version_compatibility(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Check version compatibility across all registered format handlers.

    Args:
        data: Media plan data to check

    Returns:
        Dictionary mapping format names to their compatibility results
    """
    results = {}

    for format_name, handler_class in _format_registry.items():
        try:
            handler = handler_class()
            results[format_name] = handler.check_version_compatibility(
                handler.get_version_from_data(data) or "unknown"
            )
        except Exception as e:
            results[format_name] = {
                "error": f"Failed to check compatibility: {str(e)}",
                "is_compatible": False
            }

    return results