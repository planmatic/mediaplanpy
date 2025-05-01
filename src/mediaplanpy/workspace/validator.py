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
        if not db_config.get('host'):
            errors.append("Database integration enabled but no host specified.")
        if not db_config.get('database'):
            errors.append("Database integration enabled but no database name specified.")

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