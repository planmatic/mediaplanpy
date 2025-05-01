"""
Media Plan OSC - Python SDK for Media Plans.

A lightweight, open-source Python SDK for interacting with the open data
standard for media plans.
"""

__version__ = '0.1.0'

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
    DatabaseError
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
    SchemaMigrator
)

# Import models (commented out until implemented)
# from mediaplanpy.models import (
#     MediaPlan,
#     Campaign,
#     LineItem
# )

# Import the main IO functions (commented out until implemented)
# from mediaplanpy.io import read_mediaplan, write_mediaplan

__all__ = [
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

    # Schema
    'get_current_version',
    'get_supported_versions',
    'validate',
    'validate_file',
    'migrate',
    'SchemaRegistry',
    'SchemaValidator',
    'SchemaMigrator',

    # Models (commented out until implemented)
    # 'MediaPlan',
    # 'Campaign',
    # 'LineItem',

    # Version
    '__version__'
]