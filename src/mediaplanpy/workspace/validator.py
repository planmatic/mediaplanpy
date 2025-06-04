"""
Updated workspace configuration validation utilities with lenient mode support.
"""
import json
import logging
import os
import pathlib
from typing import Dict, Any, List
from datetime import datetime

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

def validate_workspace(config: Dict[str, Any], lenient_mode: bool = False) -> List[str]:
    """
    Validate a workspace configuration against the updated schema.

    Args:
        config: The workspace configuration to validate.
        lenient_mode: If True, treat deprecated field warnings as non-blocking.
                     Used during workspace loading to allow migration.

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
    errors.extend(validate_workspace_settings(config))

    # Handle deprecated schema_settings with lenient mode
    migration_issues = validate_schema_settings_migration(config, lenient_mode=lenient_mode)
    if not lenient_mode:
        # In strict mode, treat migration issues as errors
        errors.extend(migration_issues)
    elif migration_issues:
        # In lenient mode, just log warnings
        for issue in migration_issues:
            logger.warning(f"Workspace migration notice: {issue}")

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


def validate_workspace_settings(config: Dict[str, Any]) -> List[str]:
    """
    Validate workspace_settings configuration for version tracking.

    Args:
        config: The workspace configuration to validate.

    Returns:
        A list of validation errors, if any.
    """
    errors = []
    workspace_settings = config.get('workspace_settings', {})

    # Validate schema_version format (2-digit: X.Y)
    schema_version = workspace_settings.get('schema_version')
    if schema_version:
        if not _is_valid_2digit_version(schema_version):
            errors.append(f"Invalid schema_version format: {schema_version}. Expected format: 'X.Y' (e.g., '1.0')")
        else:
            # Check if schema version is supported
            try:
                from mediaplanpy.schema.version_utils import get_compatibility_type, normalize_version

                normalized_version = normalize_version(schema_version)
                compatibility = get_compatibility_type(normalized_version)

                if compatibility == "unsupported":
                    errors.append(f"Workspace schema version {schema_version} is not supported by current SDK")
                elif compatibility == "unknown":
                    errors.append(f"Cannot determine compatibility for schema version {schema_version}")

            except Exception as e:
                logger.warning(f"Could not validate schema version compatibility: {e}")

    # Validate sdk_version_required format (X.Y.Z or X.Y.x)
    sdk_version_required = workspace_settings.get('sdk_version_required')
    if sdk_version_required:
        if not _is_valid_sdk_version_pattern(sdk_version_required):
            errors.append(f"Invalid sdk_version_required format: {sdk_version_required}. Expected format: 'X.Y.Z' or 'X.Y.x'")
        else:
            # Check SDK version compatibility
            try:
                from mediaplanpy import __version__
                current_sdk_version = __version__

                # Convert X.Y.x to X.Y.0 for comparison
                required_version = sdk_version_required.replace('.x', '.0')

                from mediaplanpy.schema.version_utils import compare_versions
                if compare_versions(current_sdk_version, required_version) < 0:
                    errors.append(f"Current SDK version {current_sdk_version} is below workspace required version {sdk_version_required}")

            except Exception as e:
                logger.warning(f"Could not validate SDK version compatibility: {e}")

    # Validate last_upgraded date format
    last_upgraded = workspace_settings.get('last_upgraded')
    if last_upgraded:
        if not _is_valid_date_format(last_upgraded):
            errors.append(f"Invalid last_upgraded date format: {last_upgraded}. Expected format: 'YYYY-MM-DD'")

    return errors


def validate_schema_settings_migration(config: Dict[str, Any], lenient_mode: bool = False) -> List[str]:
    """
    Validate that deprecated schema_settings fields have been properly migrated.

    Args:
        config: The workspace configuration to validate.
        lenient_mode: If True, return informational messages instead of errors.

    Returns:
        A list of validation errors or informational messages, if any.
    """
    issues = []
    schema_settings = config.get('schema_settings', {})

    # Check for deprecated fields
    deprecated_fields = ['preferred_version', 'auto_migrate']
    found_deprecated = []

    for field in deprecated_fields:
        if field in schema_settings:
            found_deprecated.append(field)

    if found_deprecated:
        if lenient_mode:
            # In lenient mode, this is informational since automatic migration will handle it
            message = f"Found deprecated schema_settings fields: {', '.join(found_deprecated)}. " \
                     f"These will be automatically migrated during workspace loading."
            issues.append(message)
        else:
            # In strict mode, this is an error that blocks operation
            message = f"Deprecated schema_settings fields found: {', '.join(found_deprecated)}. " \
                     f"These fields have been moved to workspace_settings or are no longer used. " \
                     f"Run workspace.upgrade_workspace() to migrate configuration."
            issues.append(message)

    return issues


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


def validate_workspace_upgrade_readiness(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if a workspace is ready for upgrade and identify potential issues.

    Args:
        config: The workspace configuration to check.

    Returns:
        Dictionary with readiness assessment and recommendations.
    """
    readiness = {
        "ready_for_upgrade": True,
        "blocking_issues": [],
        "warnings": [],
        "recommendations": []
    }

    # Check workspace status
    workspace_status = config.get('workspace_status', 'active')
    if workspace_status != 'active':
        readiness["ready_for_upgrade"] = False
        readiness["blocking_issues"].append(f"Workspace status is '{workspace_status}', must be 'active' for upgrade")

    # Check storage configuration
    storage_errors = validate_storage_config(config)
    if storage_errors:
        readiness["ready_for_upgrade"] = False
        readiness["blocking_issues"].extend([f"Storage config error: {error}" for error in storage_errors])

    # Check database configuration if enabled
    db_config = config.get('database', {})
    if db_config.get('enabled', False):
        db_errors = validate_database_config(config)
        if db_errors:
            readiness["warnings"].extend([f"Database config warning: {error}" for error in db_errors])
            readiness["recommendations"].append("Fix database configuration issues before upgrade")

        # Test database connection
        connection_errors = test_database_connection(config)
        if connection_errors:
            readiness["warnings"].extend([f"Database connection issue: {error}" for error in connection_errors])
            readiness["recommendations"].append("Ensure database is accessible before upgrade")

    # Check for deprecated fields (these are handled automatically now)
    migration_issues = validate_schema_settings_migration(config, lenient_mode=True)
    if migration_issues:
        readiness["recommendations"].append("Configuration contains deprecated fields that will be automatically migrated")

    # Check workspace_settings existence
    workspace_settings = config.get('workspace_settings')
    if not workspace_settings:
        readiness["recommendations"].append("Workspace settings will be initialized during loading")
    else:
        # Validate existing workspace_settings
        ws_errors = validate_workspace_settings(config)
        if ws_errors:
            readiness["warnings"].extend([f"Workspace settings issue: {error}" for error in ws_errors])

    return readiness


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


def _is_valid_2digit_version(version: str) -> bool:
    """
    Check if a version string follows the 2-digit format (X.Y).

    Args:
        version: Version string to validate.

    Returns:
        True if valid 2-digit version format, False otherwise.
    """
    if not version:
        return False

    import re
    return bool(re.match(r'^[0-9]+\.[0-9]+$', version))


def _is_valid_sdk_version_pattern(version: str) -> bool:
    """
    Check if a version string follows the SDK version pattern (X.Y.Z or X.Y.x).

    Args:
        version: Version string to validate.

    Returns:
        True if valid SDK version pattern, False otherwise.
    """
    if not version:
        return False

    import re
    return bool(re.match(r'^[0-9]+\.[0-9]+\.[0-9x]+$', version))


def _is_valid_date_format(date_str: str) -> bool:
    """
    Check if a date string follows the YYYY-MM-DD format.

    Args:
        date_str: Date string to validate.

    Returns:
        True if valid date format, False otherwise.
    """
    if not date_str:
        return False

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False