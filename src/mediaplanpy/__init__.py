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

    # Version
    '__version__'
]