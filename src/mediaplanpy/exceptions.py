"""
Exceptions for the mediaplanpy package.

This module defines custom exceptions used throughout the package.
"""


class MediaPlanError(Exception):
    """Base exception for all mediaplanpy errors."""
    pass


class WorkspaceError(MediaPlanError):
    """Base exception for workspace-related errors."""
    pass


class WorkspaceNotFoundError(WorkspaceError):
    """Exception raised when a workspace configuration cannot be found."""
    pass


class WorkspaceValidationError(WorkspaceError):
    """Exception raised when a workspace configuration fails validation."""
    pass


class WorkspaceInactiveError(WorkspaceError):
    """Exception raised when trying to perform restricted operations on an inactive workspace."""
    pass


class FeatureDisabledError(WorkspaceError):
    """Exception raised when trying to use a disabled feature."""
    pass


class SchemaError(MediaPlanError):
    """Base exception for schema-related errors."""
    pass


class SchemaVersionError(SchemaError):
    """Exception raised when a schema version is not supported."""
    pass


class SchemaRegistryError(SchemaError):
    """Exception raised when there's an issue with the schema registry."""
    pass


class SchemaMigrationError(SchemaError):
    """Exception raised when a schema migration fails."""
    pass


class ValidationError(SchemaError):
    """Exception raised when a media plan fails validation against the schema."""
    pass


class StorageError(MediaPlanError):
    """Base exception for storage-related errors."""
    pass


class FileReadError(StorageError):
    """Exception raised when a file cannot be read."""
    pass


class FileWriteError(StorageError):
    """Exception raised when a file cannot be written."""
    pass


class S3Error(StorageError):
    """Exception raised when an S3 operation fails."""
    pass


class DatabaseError(StorageError):
    """Exception raised when a database operation fails."""
    pass