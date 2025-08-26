"""
Media Plan OSC - Python SDK for Media Plans.

A lightweight, open-source Python SDK for interacting with the open data
standard for media plans.
"""

# Central Version Definitions - Updated for v2.0
__version__ = '2.0.3'          # SDK version - Updated to v2.0.0
__schema_version__ = '2.0'     # Current schema version supported - Updated to v2.0

VERSION_NOTES = {
    '1.0.0': 'v1.0 schema support with new versioning strategy - Schema 1.0',
    '2.0.0': 'v2.0 schema support with v1.0 backwards compatibility - v0.0 support removed',
    '2.0.1': 'v2.0 schema support with minor non-breaking functionality upgrades',
    '2.0.2': 'v2.0 schema support with minor non-breaking functionality upgrades',
    '2.0.3': 'Implement support for S3 storage',
}

# Schema version compatibility constants - Updated for v2.0
CURRENT_MAJOR = 2
CURRENT_MINOR = 0
SUPPORTED_MAJOR_VERSIONS = [1, 2]  # v0.0 no longer supported - only v1.0 and v2.0

# Setup package-level logger
import logging

logger = logging.getLogger("mediaplanpy")
logger.setLevel(logging.INFO)

# Import workspace module
from mediaplanpy.workspace import (
    WorkspaceManager,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)

# Import exceptions
from mediaplanpy.exceptions import (
    MediaPlanError,
    SchemaError,
    SchemaVersionError,
    SchemaRegistryError,
    SchemaMigrationError,
    ValidationError,
    StorageError,
    FileReadError,
    FileWriteError,
    S3Error,
    DatabaseError,
    WorkspaceInactiveError,
    FeatureDisabledError
)

# Import schema module
from mediaplanpy.schema import (
    get_current_version,
    get_supported_versions,
    validate,
    validate_file,
    migrate,
    SchemaRegistry,
    SchemaValidator,
    SchemaMigrator,
    SchemaManager
)

# Import models
from mediaplanpy.models import (
    BaseModel,
    LineItem,
    Campaign,
    Budget,
    TargetAudience,
    MediaPlan,
    Meta
)

# Import storage module
from mediaplanpy.storage import (
    read_mediaplan,
    write_mediaplan,
    get_storage_backend,
    get_format_handler_instance,
    JsonFormatHandler
)

# Import Excel module
from mediaplanpy.excel import (
    export_to_excel,
    import_from_excel,
    update_from_excel,
    validate_excel,
    ExcelFormatHandler
)

# Import database integration (this will patch MediaPlan with database methods)
try:
    import mediaplanpy.models.mediaplan_database
    _database_available = True
except ImportError:
    _database_available = False
    logger.debug("Database functionality not available - psycopg2-binary not installed")

__all__ = [
    # Version information
    '__version__',
    '__schema_version__',
    'VERSION_NOTES',
    'CURRENT_MAJOR',
    'CURRENT_MINOR',
    'SUPPORTED_MAJOR_VERSIONS',

    # Workspace
    'WorkspaceManager',
    'WorkspaceError',
    'WorkspaceNotFoundError',
    'WorkspaceValidationError',

    # Exceptions
    'MediaPlanError',
    'SchemaError',
    'SchemaVersionError',
    'SchemaRegistryError',
    'SchemaMigrationError',
    'ValidationError',
    'StorageError',
    'FileReadError',
    'FileWriteError',
    'S3Error',
    'DatabaseError',
    'WorkspaceInactiveError',
    'FeatureDisabledError',

    # Schema
    'get_current_version',
    'get_supported_versions',
    'validate',
    'validate_file',
    'migrate',
    'SchemaRegistry',
    'SchemaValidator',
    'SchemaMigrator',
    'SchemaManager',

    # Models
    'BaseModel',
    'LineItem',
    'Campaign',
    'Budget',
    'TargetAudience',
    'MediaPlan',
    'Meta',

    # Storage
    'read_mediaplan',
    'write_mediaplan',
    'get_storage_backend',
    'get_format_handler_instance',
    'JsonFormatHandler',

    # Excel
    'export_to_excel',
    'import_from_excel',
    'update_from_excel',
    'validate_excel',
    'ExcelFormatHandler',
]

# Add database availability info
def is_database_available():
    """
    Check if database functionality is available.

    Returns:
        True if psycopg2-binary is installed and database functionality is available.
    """
    return _database_available

def get_version_info():
    """
    Get detailed version information.

    Returns:
        Dictionary containing SDK version, schema version, and release notes.
    """
    return {
        'sdk_version': __version__,
        'schema_version': __schema_version__,
        'release_notes': VERSION_NOTES.get(__version__, 'No release notes available'),
        'supported_major_versions': SUPPORTED_MAJOR_VERSIONS,
        'current_major': CURRENT_MAJOR,
        'current_minor': CURRENT_MINOR
    }