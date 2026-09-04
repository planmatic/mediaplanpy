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

    def __init__(self, message, errors=None):
        super().__init__(message)
        self._errors = errors

    def errors(self):
        """Structured per-field error list (field, message, type, input), if available.

        Passthrough from the underlying pydantic ValidationError when one caused this
        exception; otherwise an empty list.
        """
        return self._errors if self._errors is not None else []


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


class MediaPlanNotFoundError(StorageError):
    """Raised when MediaPlan.load() can't find the requested plan - genuinely missing,
    not a different storage failure (permission, corruption, network)."""
    pass


class CampaignNotFoundError(MediaPlanError):
    """Raised when a campaign lifecycle operation is asked for a campaign_id that
    has no media plans in the workspace.

    Campaigns have no independent existence in this data model -- they are derived
    from media plan files -- so "campaign not found" means "no media plan carries
    this campaign_id", which is not a storage failure. Kept distinct from
    StorageError so consumers can map it to a 404 without string-matching a
    message (same reasoning as MediaPlanNotFoundError above).
    """
    pass


class SQLQueryError(Exception):
    """Exception raised for SQL query errors."""
    pass


class UnsupportedVersionError(SchemaError):
    """Exception raised when a schema version is not supported by the current SDK."""
    pass


class VersionCompatibilityError(SchemaError):
    """Exception raised when there are version compatibility issues during import."""
    pass