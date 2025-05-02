"""
Base format interface for mediaplanpy.

This module defines the abstract base class for file format handlers.
Format handlers are responsible for serializing and deserializing
media plans to/from various file formats.
"""

import abc
from typing import Dict, Any, BinaryIO, TextIO, Union, Optional, Type

from mediaplanpy.exceptions import StorageError


class FormatHandler(abc.ABC):
    """
    Abstract base class for format handlers.

    A format handler is responsible for serializing and deserializing
    media plans to/from a specific file format, such as JSON or Parquet.
    """

    # Format name (used for registration and lookup)
    format_name: str = None

    # File extension (without the dot)
    file_extension: str = None

    # Media types for this format
    media_types: list = []

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
        ext = cls.get_file_extension()
        return filename.lower().endswith(f".{ext}")

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
    for handler_class in _format_registry.values():
        if handler_class.matches_extension(filename):
            return handler_class

    return None