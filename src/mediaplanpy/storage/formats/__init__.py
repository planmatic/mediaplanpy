"""
Format handlers for mediaplanpy.

This package provides format handlers for serializing and deserializing
media plans to/from various file formats.
"""
from mediaplanpy.storage.formats.base import (
    FormatHandler,
    register_format,
    get_format_handler,
    get_format_handler_for_file
)
from mediaplanpy.storage.formats.json_format import JsonFormatHandler
from mediaplanpy.storage.formats.parquet import ParquetFormatHandler


# Convenience function to get a format handler instance
def get_format_handler_instance(format_name_or_path: str, **options) -> FormatHandler:
    """
    Get a format handler instance by name or file path.

    Args:
        format_name_or_path: Either a format name (e.g., 'json') or a file path
                            from which the format will be inferred.
        **options: Additional options to pass to the format handler constructor.

    Returns:
        A format handler instance.

    Raises:
        ValueError: If no format handler is found.
    """
    # Check if it looks like a path with an extension
    if '.' in format_name_or_path:
        handler_class = get_format_handler_for_file(format_name_or_path)
        if handler_class:
            return handler_class(**options)

    # Otherwise, treat it as a format name
    try:
        handler_class = get_format_handler(format_name_or_path)
        return handler_class(**options)
    except ValueError:
        # If not found by name and it has a dot, it might be a path
        # Try to get by extension as a fallback
        if '.' in format_name_or_path:
            extension = format_name_or_path.split('.')[-1].lower()
            for handler_cls in _format_registry.values():
                if handler_cls.file_extension == extension:
                    return handler_cls(**options)

        # If we get here, no handler was found
        raise ValueError(f"No format handler found for '{format_name_or_path}'")


__all__ = [
    'FormatHandler',
    'register_format',
    'get_format_handler',
    'get_format_handler_for_file',
    'get_format_handler_instance',
    'JsonFormatHandler',
    'ParquetFormatHandler'
]