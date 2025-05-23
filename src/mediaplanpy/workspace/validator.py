"""
Workspace configuration validation utilities.
"""
import json
import logging
import os
import pathlib
from typing import Dict, Any, List

import jsonschema

from mediaplanpy.exceptions import WorkspaceValidationError

logger = logging.getLogger("mediaplanpy.workspace.validator")

def load_workspace_schema() -> Dict[str, Any]:
    """
    Load the workspace schema from the JSON file.

    Returns:
        The workspace JSON schema as a dictionary.
    """
    schema_path = pathlib.Path(__file__).parent / 'schemas' / 'workspace.schema.json'
    with open(schema_path, 'r') as f:
        return json.load(f)

# Load the schema at module initialization
WORKSPACE_SCHEMA = load_workspace_schema()

def validate_workspace(config: Dict[str, Any]) -> List[str]:
    """
    Validate a workspace configuration against the schema.

    Args:
        config: The workspace configuration to validate.

    Returns:
        A list of validation error messages, if any.

    Raises:
        WorkspaceValidationError: If the configuration fails validation.
    """
    errors = []

    try:
        # Validate against JSON schema
        jsonschema.validate(instance=config, schema=WORKSPACE_SCHEMA)
    except jsonschema.exceptions.ValidationError as e:
        path = " -> ".join([str(p) for p in e.path])
        errors.append(f"Schema validation failed at {path}: {e.message}")

    # Additional validations beyond the schema
    errors.extend(validate_storage_config(config))
    errors.extend(validate_database_config(config))
    errors.extend(validate_schema_settings(config))

    # Validate workspace_id existence
    if "workspace_id" not in config:
        errors.append("Missing required field: workspace_id")

    return errors


def validate_storage_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate storage-specific configuration.

    Args:
        config: The workspace configuration to validate.

    Returns:
        A list of validation errors, if any.
    """
    errors = []
    storage = config.get('storage', {})
    mode = storage.get('mode')

    if mode == 'local':
        local_config = storage.get('local', {})
        if not local_config.get('base_path'):
            errors.append("Local storage mode requires a base_path.")

    elif mode == 's3':
        s3_config = storage.get('s3', {})
        if not s3_config.get('bucket'):
            errors.append("S3 storage mode requires a bucket name.")

    return errors


def validate_database_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate database-specific configuration if enabled.

    Args:
        config: The workspace configuration to validate.

    Returns:
        A list of validation errors, if any.
    """
    errors = []
    db_config = config.get('database', {})

    if db_config.get('enabled', False):
        # Required fields when database is enabled
        required_fields = ['host', 'database']
        for field in required_fields:
            if not db_config.get(field):
                errors.append(f"Database integration enabled but missing required field: {field}")

        # Validate optional fields
        port = db_config.get('port')
        if port is not None:
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append(f"Database port must be a valid port number (1-65535), got: {port}")

        timeout = db_config.get('connection_timeout')
        if timeout is not None:
            if not isinstance(timeout, int) or timeout < 1:
                errors.append(f"Database connection_timeout must be a positive integer, got: {timeout}")

        # Validate table and schema names (basic validation)
        table_name = db_config.get('table_name')
        if table_name and not _is_valid_identifier(table_name):
            errors.append(f"Invalid table_name: {table_name}. Must be a valid SQL identifier.")

        schema_name = db_config.get('schema')
        if schema_name and not _is_valid_identifier(schema_name):
            errors.append(f"Invalid schema name: {schema_name}. Must be a valid SQL identifier.")

        # Check password environment variable if specified
        password_env_var = db_config.get('password_env_var')
        if password_env_var:
            if not _is_valid_env_var_name(password_env_var):
                errors.append(f"Invalid password_env_var name: {password_env_var}")
            elif not os.environ.get(password_env_var):
                # This is a warning, not an error - the env var might be set at runtime
                logger.warning(f"Database password environment variable '{password_env_var}' is not currently set")

    return errors


def validate_schema_settings(config: Dict[str, Any]) -> List[str]:
    """
    Validate schema-specific configuration.

    Args:
        config: The workspace configuration to validate.

    Returns:
        A list of validation errors, if any.
    """
    errors = []
    schema_settings = config.get('schema_settings', {})

    # Verify preferred_version, if specified, is a valid format (v followed by digits and dots)
    preferred_version = schema_settings.get('preferred_version')
    if preferred_version and not preferred_version.startswith('v'):
        errors.append(f"Schema version should start with 'v': {preferred_version}")

    # If we have a repository_url, make sure it's a proper URL
    repo_url = schema_settings.get('repository_url')
    if repo_url and not (repo_url.startswith('http://') or repo_url.startswith('https://')):
        errors.append(f"Repository URL should start with http:// or https://: {repo_url}")

    return errors


def test_database_connection(config: Dict[str, Any]) -> List[str]:
    """
    Test database connection with the provided configuration.

    Args:
        config: The workspace configuration to test.

    Returns:
        A list of connection error messages, empty if connection succeeds.
    """
    errors = []
    db_config = config.get('database', {})

    if not db_config.get('enabled', False):
        errors.append("Database is not enabled in configuration")
        return errors

    try:
        # Import the PostgreSQL backend
        from mediaplanpy.storage.database import PostgreSQLBackend

        # Create backend instance
        backend = PostgreSQLBackend(config)

        # Test connection
        if not backend.test_connection():
            errors.append("Database connection test failed")
        else:
            logger.info("Database connection test successful")

    except ImportError:
        errors.append("psycopg2-binary is required for database functionality")
    except Exception as e:
        errors.append(f"Database connection test failed: {e}")

    return errors


def _is_valid_identifier(name: str) -> bool:
    """
    Check if a name is a valid SQL identifier.

    Args:
        name: The identifier to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not name:
        return False

    # Basic validation: alphanumeric plus underscore, must start with letter or underscore
    import re
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


def _is_valid_env_var_name(name: str) -> bool:
    """
    Check if a name is a valid environment variable name.

    Args:
        name: The environment variable name to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not name:
        return False

    # Environment variable names should be uppercase letters, digits, and underscores
    import re
    return bool(re.match(r'^[A-Z][A-Z0-9_]*$', name))