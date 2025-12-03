"""
Updated workspace configuration loader with automatic migration of deprecated fields.

This module provides the WorkspaceManager class for loading, validating,
and managing workspace configurations with automatic handling of legacy settings.
"""

import os
import json
import logging
import pathlib
import uuid
from typing import Dict, Any, Optional, Union, List, Tuple
import glob
from datetime import datetime

from mediaplanpy.exceptions import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)
from mediaplanpy.workspace.validator import validate_workspace, WORKSPACE_SCHEMA
from mediaplanpy.schema import SchemaRegistry, SchemaValidator, SchemaMigrator

# Configure logging
logger = logging.getLogger("mediaplanpy.workspace.loader")


class WorkspaceInactiveError(WorkspaceError):
    """Exception raised when trying to perform restricted operations on an inactive workspace."""
    pass


class FeatureDisabledError(WorkspaceError):
    """Exception raised when trying to use a disabled feature."""
    pass


class WorkspaceManager:
    """
    Manages workspace configuration for the mediaplanpy package.

    The workspace configuration defines storage locations, database connections,
    and other global settings for the package.
    """

    # Default workspace file name
    DEFAULT_FILENAME = "workspace.json"

    # Environment variable that can override the default workspace path
    ENV_VAR_NAME = "MEDIAPLANPY_WORKSPACE_PATH"

    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize a WorkspaceManager.

        Args:
            workspace_path: Optional explicit path to workspace.json. If not provided,
                            will look in standard locations.
        """
        self.workspace_path = workspace_path
        self.config = None
        self._resolved_config = None

        # Schema components (initialized when needed)
        self._schema_registry = None
        self._schema_validator = None
        self._schema_migrator = None

    def _migrate_deprecated_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically migrate deprecated fields to new format.

        This method handles the migration from old schema_settings fields to
        new workspace_settings format as described in the versioning strategy.

        Args:
            config: The workspace configuration to migrate.

        Returns:
            Migrated configuration with deprecated fields handled.
        """
        # Create a copy to avoid modifying the original
        import copy
        migrated_config = copy.deepcopy(config)

        # Track if any migration was performed
        migration_performed = False

        # Handle deprecated schema_settings fields
        schema_settings = migrated_config.get('schema_settings', {})

        # Remove deprecated fields if they exist
        deprecated_fields = ['preferred_version', 'auto_migrate']
        for field in deprecated_fields:
            if field in schema_settings:
                removed_value = schema_settings.pop(field)
                migration_performed = True
                logger.info(f"Migrated deprecated field 'schema_settings.{field}' (was: {removed_value})")

        # Ensure workspace_settings exists with proper defaults
        if 'workspace_settings' not in migrated_config:
            migrated_config['workspace_settings'] = {}
            migration_performed = True
            logger.info("Added workspace_settings section")

        workspace_settings = migrated_config['workspace_settings']

        # Set default values for workspace_settings if not present - UPDATED FOR v2.0
        from mediaplanpy import __schema_version__
        current_schema_version = __schema_version__  # This will be "2.0"

        defaults = {
            'schema_version': current_schema_version,  # Now defaults to "2.0"
            'last_upgraded': datetime.now().strftime("%Y-%m-%d"),
            'sdk_version_required': f"{current_schema_version.split('.')[0]}.0.x"  # Now "2.0.x"
        }

        for key, default_value in defaults.items():
            if key not in workspace_settings:
                workspace_settings[key] = default_value
                migration_performed = True
                logger.info(f"Set workspace_settings.{key} to default value: {default_value}")

        # Clean up schema_settings if it's now empty
        if not schema_settings:
            migrated_config.pop('schema_settings', None)
            migration_performed = True
            logger.info("Removed empty schema_settings section")

        if migration_performed:
            logger.info("Workspace configuration automatically migrated to new format")

        return migrated_config

    @property
    def is_loaded(self) -> bool:
        """Return True if a workspace configuration is loaded."""
        return self.config is not None

    @property
    def schema_registry(self) -> SchemaRegistry:
        """
        Get the schema registry for this workspace.

        Returns:
            A SchemaRegistry instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        if self._schema_registry is None:
            # Initialize schema registry (no parameters needed for bundled schemas)
            self._schema_registry = SchemaRegistry()

        return self._schema_registry

    @property
    def schema_validator(self) -> SchemaValidator:
        """
        Get the schema validator for this workspace.

        Returns:
            A SchemaValidator instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if self._schema_validator is None:
            self._schema_validator = SchemaValidator(registry=self.schema_registry)
        return self._schema_validator

    @property
    def schema_migrator(self) -> SchemaMigrator:
        """
        Get the schema migrator for this workspace.

        Returns:
            A SchemaMigrator instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if self._schema_migrator is None:
            self._schema_migrator = SchemaMigrator(registry=self.schema_registry)
        return self._schema_migrator

    def check_workspace_active(self, operation: str, allow_warnings: bool = False) -> None:
        """
        Check if the workspace is active for the given operation.

        Args:
            operation: Name of the operation being attempted.
            allow_warnings: If True, show warning for inactive workspace instead of error.

        Raises:
            WorkspaceError: If no configuration is loaded.
            WorkspaceInactiveError: If workspace is inactive and allow_warnings is False.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        workspace_status = self.config.get('workspace_status', 'active')

        if workspace_status == 'inactive':
            message = f"Workspace '{self.config.get('workspace_name', 'Unknown')}' is inactive. Cannot perform operation: {operation}"

            if allow_warnings:
                logger.warning(message)
            else:
                raise WorkspaceInactiveError(message)

    def check_excel_enabled(self, operation: str) -> None:
        """
        Check if Excel functionality is enabled for the given operation.

        Args:
            operation: Name of the Excel operation being attempted.

        Raises:
            WorkspaceError: If no configuration is loaded.
            FeatureDisabledError: If Excel functionality is disabled.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        excel_config = self.config.get('excel', {})
        excel_enabled = excel_config.get('enabled', True)  # Default to True for backward compatibility

        if not excel_enabled:
            raise FeatureDisabledError(
                f"Excel functionality is disabled in workspace '{self.config.get('workspace_name', 'Unknown')}'. "
                f"Cannot perform operation: {operation}"
            )

    def _get_default_workspace_directory(self) -> str:
        """
        Get the default directory for workspace files.

        Returns:
            The platform-specific default directory path.
        """
        if os.name == 'nt':  # Windows
            return os.path.join("C:", os.sep, "mediaplanpy")
        else:  # macOS/Linux
            home = os.environ.get('HOME')
            if home:
                return os.path.join(home, "mediaplanpy")
            else:
                return os.path.join(os.getcwd(), "mediaplanpy")

    def locate_workspace_file(self) -> str:
        """
        Find the workspace.json file by checking several locations in order.

        Returns:
            Path to the workspace.json file.

        Raises:
            WorkspaceNotFoundError: If no workspace.json can be found.
        """
        search_paths = []

        # 1. Explicitly provided path
        if self.workspace_path:
            search_paths.append(pathlib.Path(self.workspace_path))

        # 2. Path from environment variable
        env_path = os.environ.get(self.ENV_VAR_NAME)
        if env_path:
            search_paths.append(pathlib.Path(env_path))

        # 3. Current working directory
        search_paths.append(pathlib.Path.cwd() / self.DEFAULT_FILENAME)

        # 4. User config directories
        if os.name == 'nt':  # Windows
            user_profile = os.environ.get('USERPROFILE')
            if user_profile:
                search_paths.append(pathlib.Path(user_profile) / '.mediaplanpy' / self.DEFAULT_FILENAME)
        else:  # macOS/Linux
            home = os.environ.get('HOME')
            if home:
                search_paths.append(pathlib.Path(home) / '.config' / 'mediaplanpy' / self.DEFAULT_FILENAME)

        # Check each path
        for path in search_paths:
            if path.exists():
                logger.debug(f"Found workspace configuration at {path}")
                return str(path)

        # If we got here, no workspace file was found
        search_paths_str = "\n  - ".join([str(p) for p in search_paths])
        raise WorkspaceNotFoundError(
            f"No workspace.json file found. Searched the following locations:\n  - {search_paths_str}"
        )

    def create(self, settings_path_name: Optional[str] = None,
               settings_file_name: Optional[str] = None,
               storage_path_name: Optional[str] = None,
               workspace_name: str = "Default",
               overwrite: bool = False,
               **kwargs) -> Tuple[str, str]:
        """
        Create a new workspace configuration.

        Args:
            settings_path_name: Folder where settings file is saved. Default is C:/mediaplanpy
            settings_file_name: Filename for settings. Default is {workspace_id}_settings.json
            storage_path_name: Folder for local storage. Default is C:/mediaplanpy/{workspace_id}
            workspace_name: Name of the workspace
            overwrite: Whether to overwrite an existing file
            **kwargs: Additional configuration options

        Returns:
            tuple: (workspace_id, settings_file_path)

        Raises:
            WorkspaceError: If creation fails
        """
        # Generate a unique workspace ID
        workspace_id = f"workspace_{uuid.uuid4().hex[:8]}"

        # Set default paths
        default_dir = self._get_default_workspace_directory()
        if settings_path_name is None:
            settings_path_name = default_dir

        if settings_file_name is None:
            settings_file_name = f"{workspace_id}_settings.json"

        if storage_path_name is None:
            storage_path_name = os.path.join(default_dir, workspace_id)

        # Create the settings file path
        settings_file_path = os.path.join(settings_path_name, settings_file_name)

        # Check if file exists
        if os.path.exists(settings_file_path) and not overwrite:
            raise WorkspaceError(
                f"Workspace file already exists at {settings_file_path}. Use overwrite=True to replace it.")

        # Load workspace template from JSON file
        from mediaplanpy import __schema_version__
        current_schema_version = __schema_version__

        # Get path to template file
        template_path = os.path.join(
            os.path.dirname(__file__),
            'schemas',
            'workspace.template.json'
        )

        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
        except Exception as e:
            raise WorkspaceError(f"Failed to load workspace template: {e}")

        # Replace placeholders in template
        template_content = template_content.replace('{{WORKSPACE_ID}}', workspace_id)
        template_content = template_content.replace('{{WORKSPACE_NAME}}', workspace_name)
        template_content = template_content.replace('{{STORAGE_PATH}}', storage_path_name)
        template_content = template_content.replace('{{SCHEMA_VERSION}}', current_schema_version)
        template_content = template_content.replace('{{LAST_UPGRADED}}', datetime.now().strftime("%Y-%m-%d"))
        template_content = template_content.replace('{{SDK_VERSION_REQUIRED}}', f"{current_schema_version.split('.')[0]}.0.x")

        # Parse the template into config dict
        try:
            config = json.loads(template_content)
        except Exception as e:
            raise WorkspaceError(f"Failed to parse workspace template: {e}")

        # Override with any provided config options
        for key, value in kwargs.items():
            if key in config:
                if isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value

        # Create settings directory if it doesn't exist
        try:
            os.makedirs(settings_path_name, exist_ok=True)
        except Exception as e:
            raise WorkspaceError(f"Failed to create settings directory: {e}")

        # Write the configuration to file
        try:
            with open(settings_file_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Created workspace '{workspace_name}' with ID '{workspace_id}' at {settings_file_path}")

            # Set the workspace path and config
            self.workspace_path = settings_file_path
            self.config = config
            self._resolved_config = None  # Reset resolved config

            return workspace_id, settings_file_path
        except Exception as e:
            raise WorkspaceError(f"Failed to create workspace: {e}")

    def load(self, workspace_path: Optional[str] = None,
             workspace_id: Optional[str] = None,
             config_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load a workspace configuration with automatic migration of deprecated fields.

        Args:
            workspace_path: Path to workspace settings file
            workspace_id: Workspace ID to locate settings file
            config_dict: Configuration dictionary to use directly

        Returns:
            The loaded workspace configuration

        Raises:
            WorkspaceNotFoundError: If workspace cannot be found
            WorkspaceValidationError: If configuration is invalid
            WorkspaceError: If loading fails
        """
        # Reset resolved config
        self._resolved_config = None

        # Use config_dict if provided
        if config_dict is not None:
            # Migrate deprecated fields before validation
            migrated_config = self._migrate_deprecated_fields(config_dict)

            # Validate the migrated configuration
            errors = validate_workspace(migrated_config, lenient_mode=True)
            if errors:
                raise WorkspaceValidationError("\n".join(errors))

            self.config = migrated_config
            self.workspace_path = None  # No file path
            logger.info(f"Loaded workspace '{self.config.get('workspace_name', 'Unnamed')}' from provided dictionary")

            # Check workspace status and show warning if inactive
            try:
                self.check_workspace_active("load", allow_warnings=True)
            except WorkspaceInactiveError:
                pass  # This won't be raised when allow_warnings=True

            return self.config

        # If workspace_id is provided, locate the settings file
        if workspace_id is not None:
            default_dir = self._get_default_workspace_directory()

            # Check default directory first
            settings_paths = [
                os.path.join(default_dir, f"{workspace_id}_settings.json"),
                os.path.join(default_dir, f"{workspace_id}.json")
            ]

            # Check current directory
            settings_paths.extend([
                os.path.join(os.getcwd(), f"{workspace_id}_settings.json"),
                os.path.join(os.getcwd(), f"{workspace_id}.json")
            ])

            # Check user directories
            if os.name == 'nt':  # Windows
                user_profile = os.environ.get('USERPROFILE')
                if user_profile:
                    settings_paths.extend([
                        os.path.join(user_profile, '.mediaplanpy', f"{workspace_id}_settings.json"),
                        os.path.join(user_profile, '.mediaplanpy', f"{workspace_id}.json")
                    ])
            else:  # macOS/Linux
                home = os.environ.get('HOME')
                if home:
                    settings_paths.extend([
                        os.path.join(home, '.config', 'mediaplanpy', f"{workspace_id}_settings.json"),
                        os.path.join(home, '.config', 'mediaplanpy', f"{workspace_id}.json")
                    ])

            # Check each path
            workspace_path_found = None
            for path in settings_paths:
                if os.path.exists(path):
                    workspace_path_found = path
                    break

            if workspace_path_found is None:
                search_paths_str = "\n  - ".join(settings_paths)
                raise WorkspaceNotFoundError(
                    f"No settings file found for workspace ID '{workspace_id}'. "
                    f"Searched in these locations:\n  - {search_paths_str}"
                )

            # Use the found path
            workspace_path = workspace_path_found

        # If workspace_path provided or found by ID, use it
        if workspace_path:
            self.workspace_path = workspace_path
        else:
            # Fall back to existing logic to locate workspace file
            self.workspace_path = self.locate_workspace_file()

        # Load the configuration from file
        try:
            with open(self.workspace_path, 'r') as f:
                raw_config = json.load(f)

            # Migrate deprecated fields before validation
            self.config = self._migrate_deprecated_fields(raw_config)

            # If migration was performed, save the updated configuration back to file
            if self.config != raw_config:
                try:
                    with open(self.workspace_path, 'w') as f:
                        json.dump(self.config, f, indent=2)
                    logger.info(f"Saved migrated workspace configuration to {self.workspace_path}")
                except Exception as e:
                    logger.warning(f"Could not save migrated configuration: {e}")

            # Validate the migrated configuration with lenient mode
            errors = validate_workspace(self.config, lenient_mode=True)
            if errors:
                raise WorkspaceValidationError("\n".join(errors))

            logger.info(f"Loaded workspace '{self.config.get('workspace_name', 'Unnamed')}' from {self.workspace_path}")

            # Check workspace status and show warning if inactive
            try:
                self.check_workspace_active("load", allow_warnings=True)
            except WorkspaceInactiveError:
                pass  # This won't be raised when allow_warnings=True

            return self.config
        except FileNotFoundError:
            raise WorkspaceNotFoundError(f"Workspace file not found at {self.workspace_path}")
        except json.JSONDecodeError as e:
            raise WorkspaceError(f"Failed to parse workspace settings: {e}")
        except Exception as e:
            raise WorkspaceError(f"Error loading workspace: {e}")

    def validate(self) -> bool:
        """
        Validate the loaded workspace configuration against the schema.

        Returns:
            True if the configuration is valid.

        Raises:
            WorkspaceValidationError: If the configuration fails validation.
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        errors = validate_workspace(self.config, lenient_mode=False)
        if errors:
            raise WorkspaceValidationError("\n".join(errors))

        return True

    def get_resolved_config(self) -> Dict[str, Any]:
        """
        Get the workspace configuration with all variables resolved.

        Returns:
            A copy of the workspace configuration with placeholder variables resolved.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        if self._resolved_config is None:
            self._resolved_config = self._resolve_config_variables(self.config)

        return self._resolved_config

    def _resolve_config_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively resolve variables in the configuration.

        Args:
            config: The configuration dictionary to resolve.

        Returns:
            A copy of the configuration with variables resolved.
        """
        # Create a deep copy to avoid modifying the original
        import copy
        resolved = copy.deepcopy(config)

        # Recursively process all string values
        def process_dict(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    process_dict(value)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            process_dict(item)
                        elif isinstance(item, str):
                            value[i] = self._resolve_path_variables(item)
                elif isinstance(value, str):
                    d[key] = self._resolve_path_variables(value)

        process_dict(resolved)
        return resolved

    def _resolve_path_variables(self, path: str) -> str:
        """
        Resolve placeholder variables in paths.

        Supports:
        - ${user_documents}: User's Documents directory
        - ${user_home}: User's home directory

        Args:
            path: The path string to resolve.

        Returns:
            The resolved path.
        """
        # Skip if not a string or has no variables
        if not path or not isinstance(path, str) or '${' not in path:
            return path

        # Resolve built-in variables
        if '${user_documents}' in path:
            if os.name == 'nt':  # Windows
                documents = os.path.join(os.environ.get('USERPROFILE', ''), 'Documents')
            elif os.name == 'posix':  # macOS/Linux
                documents = os.path.join(os.environ.get('HOME', ''), 'Documents')
            else:
                documents = ''
            path = path.replace('${user_documents}', documents)

        if '${user_home}' in path:
            home = os.environ.get('HOME') or os.environ.get('USERPROFILE', '')
            path = path.replace('${user_home}', home)

        return path

    def get_storage_config(self) -> Dict[str, Any]:
        """
        Get the resolved storage configuration section.

        Returns:
            The resolved storage configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('storage', {})

    def get_database_config(self) -> Dict[str, Any]:
        """
        Get the resolved database configuration section.

        Returns:
            The resolved database configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('database', {})

    def get_excel_config(self) -> Dict[str, Any]:
        """
        Get the resolved Excel configuration section.

        Returns:
            The resolved Excel configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('excel', {})

    def get_google_sheets_config(self) -> Dict[str, Any]:
        """
        Get the resolved Google Sheets configuration section.

        Returns:
            The resolved Google Sheets configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('google_sheets', {})

    def get_schema_settings(self) -> Dict[str, Any]:
        """
        Get the resolved schema settings configuration section.

        Returns:
            The resolved schema settings configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('schema_settings', {})

    def validate_media_plan(self, media_plan: Dict[str, Any], version: Optional[str] = None) -> List[str]:
        """
        Validate a media plan against the appropriate schema.

        Args:
            media_plan: The media plan data to validate.
            version: The schema version to validate against. If None, uses the preferred
                     version from workspace settings, or the version in the media plan.

        Returns:
            List of validation error messages, empty if validation succeeds.
        """
        # If no version specified, use preferred version from settings
        if version is None:
            schema_settings = self.get_schema_settings()
            version = schema_settings.get('preferred_version')

        # Validate using the schema validator
        return self.schema_validator.validate(media_plan, version)

    def migrate_media_plan(self, media_plan: Dict[str, Any], to_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Migrate a media plan to a specific schema version.

        Args:
            media_plan: The media plan data to migrate.
            to_version: The target schema version. If None, uses the preferred
                       version from workspace settings.

        Returns:
            The migrated media plan data.
        """
        # If no target version specified, use preferred version from settings
        if to_version is None:
            schema_settings = self.get_schema_settings()
            to_version = schema_settings.get('preferred_version')

        # Get current version from media plan
        from_version = media_plan.get("meta", {}).get("schema_version")
        if not from_version:
            raise WorkspaceError("Media plan does not specify a schema version")

        # Migrate using the schema migrator
        return self.schema_migrator.migrate(media_plan, from_version, to_version)

    def get_storage_backend(self) -> 'StorageBackend':
        """
        Get the storage backend for this workspace.

        Returns:
            A StorageBackend instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        from mediaplanpy.storage import get_storage_backend
        return get_storage_backend(self.get_resolved_config())

    def get_schema_manager(self) -> 'SchemaManager':
        """
        Get SchemaManager instance for this workspace.

        Returns:
            SchemaManager instance
        """
        from mediaplanpy.schema.manager import SchemaManager
        return SchemaManager()

    # Enhanced upgrade_workspace method in src/mediaplanpy/workspace/loader.py
    # Replace the existing upgrade_workspace method:

    def upgrade_workspace(self, target_sdk_version: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Upgrade entire workspace to new SDK/Schema version with v2.0 support.

        This method implements the workspace upgrade process for SDK v2.0:
        1. Validate workspace compatibility and reject v0.0 plans
        2. Upgrade all JSON media plans (v1.0 → v2.0 auto-migration)
        3. Regenerate all Parquet files with new v2.0 schema
        4. Upgrade database schema if PostgreSQL enabled
        5. Update workspace settings with new version info

        Args:
            target_sdk_version: Target SDK version (defaults to current SDK version)
            dry_run: If True, shows what would be upgraded without making changes

        Returns:
            UpgradeResult dictionary with files processed, errors, database changes

        Raises:
            WorkspaceError: If no configuration is loaded or upgrade fails
            WorkspaceInactiveError: If workspace is inactive
        """
        # Check if workspace is active
        self.check_workspace_active("workspace upgrade")

        # Ensure workspace is loaded
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        # Get current SDK and schema versions
        from mediaplanpy import __version__, __schema_version__

        if target_sdk_version is None:
            target_sdk_version = __version__

        target_schema_version = __schema_version__  # This will be "2.0"

        logger.info(f"Starting workspace upgrade to SDK {target_sdk_version}, Schema {target_schema_version}")

        # Initialize result dictionary
        result = {
            "dry_run": dry_run,
            "target_sdk_version": target_sdk_version,
            "target_schema_version": target_schema_version,
            "files_processed": [],
            "files_failed": [],
            "errors": [],
            "database_upgraded": False,
            "workspace_updated": False,
            "parquet_files_regenerated": 0,
            "json_files_migrated": 0,
            "v0_files_rejected": 0,  # NEW: Track v0.0 rejections
            "version_validation_errors": []  # NEW: Track version validation issues
        }

        try:
            # STEP 0: Pre-upgrade validation - reject v0.0 and validate compatibility
            validation_result = self._validate_upgrade_compatibility(target_schema_version, dry_run)
            result["v0_files_rejected"] = validation_result["v0_files_rejected"]
            result["version_validation_errors"].extend(validation_result["errors"])
            result["errors"].extend(validation_result["errors"])

            # If we found v0.0 files, this is a blocking error
            if validation_result["v0_files_rejected"] > 0:
                error_msg = (
                    f"Found {validation_result['v0_files_rejected']} media plan files with v0.0 schema. "
                    f"v0.0 support has been removed in SDK v2.0. Please use SDK v1.x to migrate "
                    f"v0.0 plans to v1.0 first, then upgrade to SDK v2.0."
                )
                result["errors"].append(error_msg)
                logger.error(error_msg)

                if not dry_run:
                    raise WorkspaceError(error_msg)

            # STEP 1: Upgrade all JSON media plans (v1.0 → v2.0)
            json_result = self._upgrade_json_mediaplans(target_schema_version, dry_run)
            result["json_files_migrated"] = json_result["migrated_count"]
            result["files_processed"].extend(json_result["processed_files"])
            result["files_failed"].extend(json_result["failed_files"])
            result["errors"].extend(json_result["errors"])

            # STEP 2: Regenerate all Parquet files with v2.0 schema
            parquet_result = self._regenerate_parquet_files(dry_run)
            result["parquet_files_regenerated"] = parquet_result["regenerated_count"]
            result["files_processed"].extend(parquet_result["processed_files"])
            result["files_failed"].extend(parquet_result["failed_files"])
            result["errors"].extend(parquet_result["errors"])

            # STEP 3: Upgrade database schema if enabled (with v2.0 support)
            if self._should_upgrade_database():
                db_result = self._upgrade_database_schema(dry_run)
                result["database_upgraded"] = db_result["upgraded"]
                result["errors"].extend(db_result["errors"])

            # STEP 4: Update workspace settings for v2.0
            workspace_result = self._update_workspace_settings(target_sdk_version, target_schema_version, dry_run)
            result["workspace_updated"] = workspace_result["updated"]
            result["errors"].extend(workspace_result["errors"])

            # Log comprehensive summary
            if dry_run:
                logger.info(f"[DRY RUN] Workspace upgrade would process {len(result['files_processed'])} files")
                if result["v0_files_rejected"] > 0:
                    logger.warning(f"[DRY RUN] Would reject {result['v0_files_rejected']} v0.0 files")
            else:
                logger.info(f"Workspace upgrade completed: {result['json_files_migrated']} JSON files migrated, "
                            f"{result['parquet_files_regenerated']} Parquet files regenerated")
                if result["v0_files_rejected"] > 0:
                    logger.warning(f"Rejected {result['v0_files_rejected']} v0.0 files (no longer supported)")

            return result

        except Exception as e:
            error_msg = f"Workspace upgrade failed: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
            raise WorkspaceError(error_msg)

    def _upgrade_json_mediaplans(self, target_schema_version: str, dry_run: bool) -> Dict[str, Any]:
        """
        Upgrade all JSON media plan files in the workspace to v2.0 schema.

        Enhanced for SDK v2.0 to handle:
        - v1.0 → v2.0 automatic migration
        - v0.0 rejection (no longer supported)
        - Better error handling and reporting

        Args:
            target_schema_version: Target schema version to migrate to (should be "2.0")
            dry_run: If True, don't actually modify files

        Returns:
            Dictionary with migration results
        """
        from mediaplanpy.models import MediaPlan
        from mediaplanpy.exceptions import SchemaVersionError, ValidationError

        result = {
            "migrated_count": 0,
            "already_current_count": 0,
            "v0_rejected_count": 0,
            "processed_files": [],
            "failed_files": [],
            "errors": []
        }

        try:
            # Get storage backend
            storage_backend = self.get_storage_backend()

            # Find all JSON files in mediaplans directory
            json_files = []
            try:
                json_files = storage_backend.list_files("mediaplans", "*.json")
            except Exception:
                # Try root directory as fallback
                json_files = storage_backend.list_files("", "*.json")

            logger.info(f"Found {len(json_files)} JSON files to process for v2.0 upgrade")

            for file_path in json_files:
                try:
                    result["processed_files"].append(file_path)

                    if dry_run:
                        # For dry run, just check what would be migrated
                        try:
                            content = storage_backend.read_file(file_path, binary=False)
                            import json
                            data = json.loads(content)

                            current_version = data.get("meta", {}).get("schema_version")

                            if not current_version:
                                result["errors"].append(f"File {file_path} has no schema version")
                                continue

                            # Check for v0.0 files and reject them
                            if current_version.startswith("v0.") or current_version.startswith("0."):
                                result["v0_rejected_count"] += 1
                                logger.warning(f"[DRY RUN] Would reject v0.0 file: {file_path}")
                                continue

                            # Normalize version for comparison
                            from mediaplanpy.schema.version_utils import normalize_version
                            normalized_version = normalize_version(current_version)
                            target_normalized = normalize_version(f"v{target_schema_version}")

                            if normalized_version != target_normalized:
                                result["migrated_count"] += 1
                                logger.info(
                                    f"[DRY RUN] Would migrate {file_path} from {current_version} to v{target_schema_version}")
                            else:
                                result["already_current_count"] += 1
                                logger.debug(f"[DRY RUN] File {file_path} already at target version")

                        except Exception as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Failed to check {file_path}: {str(e)}")
                    else:
                        # Actually perform migration
                        try:
                            # Pre-check for v0.0 files before attempting to load
                            content = storage_backend.read_file(file_path, binary=False)
                            import json
                            data = json.loads(content)

                            current_version = data.get("meta", {}).get("schema_version")

                            # CRITICAL: Reject v0.0 files immediately
                            if current_version and (
                                    current_version.startswith("v0.") or current_version.startswith("0.")):
                                result["v0_rejected_count"] += 1
                                result["failed_files"].append(file_path)
                                error_msg = (
                                    f"Cannot migrate {file_path}: schema version {current_version} (v0.0.x) "
                                    f"is no longer supported in SDK v2.0. Use SDK v1.x to migrate to v1.0 first."
                                )
                                result["errors"].append(error_msg)
                                logger.error(error_msg)
                                continue

                            # Load media plan (this will trigger automatic version handling)
                            media_plan = MediaPlan.load(self, path=file_path, validate_version=True, auto_migrate=False)

                            # Always save after migration attempt to ensure changes are persisted
                            media_plan.save(self, path=file_path, overwrite=True, validate_version=True)

                            # Normalize version for comparison
                            from mediaplanpy.schema.version_utils import normalize_version
                            normalized_version = normalize_version(current_version)
                            target_normalized = normalize_version(f"v{target_schema_version}")

                            # Check if migration actually occurred for logging
                            if normalized_version != target_normalized:
                                result["migrated_count"] += 1
                                logger.info(f"Migrated {file_path} from {current_version} to v{target_schema_version}")
                            else:
                                result["already_current_count"] += 1
                                logger.debug(f"File {file_path} already at target version")

                        except SchemaVersionError as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Schema version error for {file_path}: {str(e)}")
                            logger.error(f"Schema version error for {file_path}: {str(e)}")
                        except ValidationError as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Validation failed for {file_path}: {str(e)}")
                            logger.error(f"Validation failed for {file_path}: {str(e)}")
                        except Exception as e:
                            result["failed_files"].append(file_path)
                            result["errors"].append(f"Unexpected error with {file_path}: {str(e)}")
                            logger.error(f"Unexpected error with {file_path}: {str(e)}")

                except Exception as e:
                    result["failed_files"].append(file_path)
                    result["errors"].append(f"Error processing {file_path}: {str(e)}")

            # Log summary
            logger.info(f"JSON migration complete: {result['migrated_count']} migrated, "
                        f"{result['already_current_count']} already current, "
                        f"{result['v0_rejected_count']} v0.0 files rejected")

        except Exception as e:
            result["errors"].append(f"Error finding JSON files: {str(e)}")

        return result

    def _regenerate_parquet_files(self, dry_run: bool) -> Dict[str, Any]:
        """
        Regenerate all Parquet files with current v2.0 schema.

        Enhanced for SDK v2.0 to:
        - Support new v2.0 Parquet schema with additional fields
        - Better error handling for schema compatibility
        - Validation of source JSON files before regeneration

        Args:
            dry_run: If True, don't actually regenerate files

        Returns:
            Dictionary with regeneration results
        """
        from mediaplanpy.models import MediaPlan

        result = {
            "regenerated_count": 0,
            "skipped_count": 0,
            "orphaned_removed_count": 0,
            "processed_files": [],
            "failed_files": [],
            "errors": []
        }

        try:
            # Get storage backend
            storage_backend = self.get_storage_backend()

            # Find all Parquet files
            parquet_files = []
            try:
                parquet_files = storage_backend.list_files("mediaplans", "*.parquet")
            except Exception:
                # Try root directory as fallback
                parquet_files = storage_backend.list_files("", "*.parquet")

            logger.info(f"Found {len(parquet_files)} Parquet files to regenerate with v2.0 schema")

            for parquet_path in parquet_files:
                try:
                    result["processed_files"].append(parquet_path)

                    # Find corresponding JSON file
                    json_path = parquet_path.replace(".parquet", ".json")

                    if storage_backend.exists(json_path):
                        if dry_run:
                            # For dry run, check if JSON file is compatible with v2.0
                            try:
                                content = storage_backend.read_file(json_path, binary=False)
                                import json
                                data = json.loads(content)

                                schema_version = data.get("meta", {}).get("schema_version")

                                # Check if this is a v0.0 file (would be skipped)
                                if schema_version and (
                                        schema_version.startswith("v0.") or schema_version.startswith("0.")):
                                    result["skipped_count"] += 1
                                    logger.warning(
                                        f"[DRY RUN] Would skip Parquet regeneration for v0.0 file: {parquet_path}")
                                    continue

                                result["regenerated_count"] += 1
                                logger.info(f"[DRY RUN] Would regenerate {parquet_path} with v2.0 schema")

                            except Exception as e:
                                result["failed_files"].append(parquet_path)
                                result["errors"].append(f"Failed to check {json_path} for {parquet_path}: {str(e)}")
                        else:
                            try:
                                # Load media plan from JSON (this handles version compatibility)
                                media_plan = MediaPlan.load(self, path=json_path, validate_version=True,
                                                            auto_migrate=True)

                                # Check if the loaded plan has a compatible schema version
                                schema_version = media_plan.meta.schema_version
                                if schema_version and (
                                        schema_version.startswith("v0.") or schema_version.startswith("0.")):
                                    result["skipped_count"] += 1
                                    logger.warning(f"Skipping Parquet regeneration for v0.0 file: {parquet_path}")
                                    continue

                                # Save with Parquet regeneration (this will use v2.0 schema)
                                media_plan.save(
                                    self,
                                    path=json_path,
                                    overwrite=True,
                                    include_parquet=True,
                                    validate_version=True
                                )

                                result["regenerated_count"] += 1
                                logger.info(f"Regenerated Parquet file with v2.0 schema: {parquet_path}")

                            except Exception as e:
                                result["failed_files"].append(parquet_path)
                                result["errors"].append(f"Failed to regenerate {parquet_path}: {str(e)}")
                                logger.error(f"Failed to regenerate {parquet_path}: {str(e)}")
                    else:
                        # Orphaned Parquet file - remove it
                        if dry_run:
                            result["orphaned_removed_count"] += 1
                            logger.info(f"[DRY RUN] Would remove orphaned Parquet file: {parquet_path}")
                        else:
                            try:
                                storage_backend.delete_file(parquet_path)
                                result["orphaned_removed_count"] += 1
                                logger.info(f"Removed orphaned Parquet file: {parquet_path}")
                            except Exception as e:
                                result["errors"].append(f"Failed to remove orphaned file {parquet_path}: {str(e)}")

                except Exception as e:
                    result["failed_files"].append(parquet_path)
                    result["errors"].append(f"Error processing {parquet_path}: {str(e)}")

            # Log summary
            logger.info(f"Parquet regeneration complete: {result['regenerated_count']} regenerated, "
                        f"{result['skipped_count']} skipped, {result['orphaned_removed_count']} orphaned files removed")

        except Exception as e:
            result["errors"].append(f"Error finding Parquet files: {str(e)}")

        return result


    def _should_upgrade_database(self) -> bool:
        """
        Check if database should be upgraded.

        Returns:
            True if database upgrade should be attempted
        """
        db_config = self.get_database_config()
        return db_config.get("enabled", False)

    def _upgrade_database_schema(self, dry_run: bool) -> Dict[str, Any]:
        """
        Upgrade database schema if enabled, with v2.0 schema support.

        Enhanced for SDK v2.0 to:
        - Support new v2.0 database schema with additional fields
        - Handle migration from v1.0 to v2.0 schema
        - Validate existing data compatibility
        - Reject v0.0 data during migration

        Args:
            dry_run: If True, don't actually modify database

        Returns:
            Dictionary with upgrade results
        """
        result = {
            "upgraded": False,
            "schema_validated": False,
            "migration_performed": False,
            "v0_records_found": 0,
            "errors": []
        }

        try:
            from mediaplanpy.models import MediaPlan

            if dry_run:
                # Test connection and validate schema compatibility
                try:
                    if MediaPlan.test_database_connection(self):
                        logger.info("[DRY RUN] Database connection successful")

                        # Check current schema validation
                        if MediaPlan.validate_database_schema(self):
                            logger.info("[DRY RUN] Database schema is already v2.0 compatible")
                            result["schema_validated"] = True
                            result["upgraded"] = True
                        else:
                            logger.info("[DRY RUN] Database schema needs upgrade to v2.0")
                            result["upgraded"] = True  # Would be upgraded

                        # Check for v0.0 data that would be rejected
                        try:
                            from mediaplanpy.storage.database import PostgreSQLBackend
                            db_backend = PostgreSQLBackend(self.get_resolved_config())

                            if db_backend.table_exists():
                                version_stats = db_backend.get_version_statistics()
                                result["v0_records_found"] = version_stats.get("v0_records_found", 0)

                                if result["v0_records_found"] > 0:
                                    logger.warning(
                                        f"[DRY RUN] Found {result['v0_records_found']} v0.0 records in database that cannot be migrated")
                                    result["errors"].append(
                                        f"Database contains {result['v0_records_found']} v0.0 records that cannot be migrated to v2.0")
                        except Exception as e:
                            logger.warning(f"[DRY RUN] Could not check database version statistics: {e}")

                    else:
                        result["errors"].append("Database connection test failed")

                except Exception as e:
                    result["errors"].append(f"Database validation failed: {str(e)}")
            else:
                # Actually upgrade database
                try:
                    if MediaPlan.test_database_connection(self):
                        # Check for existing v0.0 data before proceeding
                        try:
                            from mediaplanpy.storage.database import PostgreSQLBackend
                            db_backend = PostgreSQLBackend(self.get_resolved_config())

                            if db_backend.table_exists():
                                # Run migration that will reject v0.0 records
                                migration_result = db_backend.migrate_existing_data()
                                result["v0_records_found"] = migration_result.get("v0_records_rejected", 0)

                                if migration_result.get("errors"):
                                    result["errors"].extend(migration_result["errors"])

                                if result["v0_records_found"] > 0:
                                    error_msg = (
                                        f"Database upgrade blocked: found {result['v0_records_found']} v0.0 records "
                                        f"that cannot be migrated. Please clean up v0.0 data before upgrading to v2.0."
                                    )
                                    result["errors"].append(error_msg)
                                    logger.error(error_msg)
                                    return result  # Early return on v0.0 data

                                result["migration_performed"] = True
                                logger.info(
                                    f"Database migration completed: {migration_result.get('records_migrated', 0)} records migrated")
                        except Exception as e:
                            logger.warning(f"Could not perform database migration: {e}")
                            result["errors"].append(f"Database migration failed: {str(e)}")

                        # Ensure table exists with current v2.0 schema
                        if MediaPlan.create_database_table(self):
                            logger.info("Database schema upgraded to v2.0 successfully")
                            result["upgraded"] = True

                            # Validate the upgraded schema
                            if MediaPlan.validate_database_schema(self):
                                logger.info("Database v2.0 schema validation successful")
                                result["schema_validated"] = True
                            else:
                                result["errors"].append("Database schema validation failed after upgrade")
                        else:
                            result["errors"].append("Failed to create/update database table to v2.0 schema")
                    else:
                        result["errors"].append("Database connection failed")

                except Exception as e:
                    result["errors"].append(f"Database upgrade failed: {str(e)}")

        except ImportError:
            result["errors"].append("Database functionality not available - psycopg2-binary not installed")
        except Exception as e:
            result["errors"].append(f"Database upgrade process failed: {str(e)}")

        return result

    def _update_workspace_settings(self, target_sdk_version: str, target_schema_version: str, dry_run: bool) -> Dict[
        str, Any]:
        """
        Update workspace settings with new v2.0 version information.

        Enhanced for SDK v2.0 to:
        - Update workspace_settings to v2.0 format
        - Remove deprecated schema_settings fields
        - Validate version compatibility
        - Handle version normalization

        Args:
            target_sdk_version: Target SDK version (should be "2.0.0")
            target_schema_version: Target schema version (should be "2.0")
            dry_run: If True, don't actually update configuration

        Returns:
            Dictionary with update results
        """
        result = {
            "updated": False,
            "deprecated_fields_removed": 0,
            "workspace_settings_updated": False,
            "errors": []
        }

        try:
            if dry_run:
                logger.info(
                    f"[DRY RUN] Would update workspace settings to SDK {target_sdk_version}, Schema {target_schema_version}")

                # Check what would be updated
                workspace_settings = self.config.get("workspace_settings", {})
                current_schema_version = workspace_settings.get("schema_version")
                current_sdk_required = workspace_settings.get("sdk_version_required")

                if current_schema_version != target_schema_version:
                    logger.info(
                        f"[DRY RUN] Would update schema_version from {current_schema_version} to {target_schema_version}")

                if current_sdk_required != f"{target_sdk_version.rsplit('.', 1)[0]}.x":
                    logger.info(
                        f"[DRY RUN] Would update sdk_version_required to {target_sdk_version.rsplit('.', 1)[0]}.x")

                # Check for deprecated fields that would be removed
                schema_settings = self.config.get("schema_settings", {})
                deprecated_fields = ["preferred_version", "auto_migrate"]
                found_deprecated = [field for field in deprecated_fields if field in schema_settings]

                if found_deprecated:
                    logger.info(f"[DRY RUN] Would remove deprecated fields: {', '.join(found_deprecated)}")
                    result["deprecated_fields_removed"] = len(found_deprecated)

                result["updated"] = True
            else:
                # Actually update workspace configuration
                try:
                    # Ensure workspace_settings exists
                    if "workspace_settings" not in self.config:
                        self.config["workspace_settings"] = {}

                    # Update workspace settings with v2.0 information
                    workspace_settings = self.config["workspace_settings"]
                    old_schema_version = workspace_settings.get("schema_version")
                    old_sdk_required = workspace_settings.get("sdk_version_required")

                    # Update to v2.0 versions
                    workspace_settings["schema_version"] = target_schema_version  # "2.0"
                    workspace_settings["last_upgraded"] = datetime.now().strftime("%Y-%m-%d")
                    workspace_settings["sdk_version_required"] = f"{target_sdk_version.rsplit('.', 1)[0]}.x"  # "2.0.x"

                    result["workspace_settings_updated"] = True
                    logger.info(
                        f"Updated workspace settings: schema_version {old_schema_version} → {target_schema_version}")

                    # Remove deprecated schema_settings fields if they exist
                    if "schema_settings" in self.config:
                        schema_settings = self.config["schema_settings"]
                        deprecated_fields = ["preferred_version", "auto_migrate"]

                        for field in deprecated_fields:
                            if field in schema_settings:
                                removed_value = schema_settings.pop(field)
                                result["deprecated_fields_removed"] += 1
                                logger.info(
                                    f"Removed deprecated field 'schema_settings.{field}' (was: {removed_value})")

                        # Remove schema_settings section if it's now empty
                        if not schema_settings:
                            self.config.pop("schema_settings", None)
                            logger.info("Removed empty schema_settings section")

                    # Save updated configuration if we have a file path
                    if self.workspace_path:
                        try:
                            import json
                            with open(self.workspace_path, 'w') as f:
                                json.dump(self.config, f, indent=2)

                            # Reset resolved config so it gets recalculated
                            self._resolved_config = None

                            logger.info(f"Saved updated workspace configuration to: {self.workspace_path}")
                            result["updated"] = True

                        except Exception as e:
                            result["errors"].append(f"Failed to save workspace configuration: {str(e)}")
                            logger.error(f"Failed to save workspace configuration: {str(e)}")
                    else:
                        # Configuration loaded from dict - just update in memory
                        logger.info("Updated workspace configuration in memory (no file to save)")
                        result["updated"] = True

                    # Validate the updated configuration
                    try:
                        from mediaplanpy.workspace.validator import validate_workspace
                        validation_errors = validate_workspace(self.config, lenient_mode=True)
                        if validation_errors:
                            logger.warning(
                                f"Workspace validation warnings after update: {'; '.join(validation_errors)}")
                        else:
                            logger.info("Workspace configuration validation successful after v2.0 update")
                    except Exception as e:
                        logger.warning(f"Could not validate updated workspace configuration: {e}")

                except Exception as e:
                    result["errors"].append(f"Failed to update workspace configuration: {str(e)}")
                    logger.error(f"Failed to update workspace configuration: {str(e)}")

        except Exception as e:
            result["errors"].append(f"Workspace settings update process failed: {str(e)}")

        return result

    def _validate_upgrade_compatibility(self, target_schema_version: str, dry_run: bool) -> Dict[str, Any]:
        """
        Validate workspace compatibility before upgrade and reject v0.0 files.

        This method scans all media plan files to identify version compatibility issues,
        specifically rejecting v0.0 files which are no longer supported in SDK v2.0.

        Args:
            target_schema_version: Target schema version to upgrade to
            dry_run: If True, don't actually modify files

        Returns:
            Dictionary with validation results including v0.0 rejections
        """
        result = {
            "v0_files_rejected": 0,
            "v1_files_found": 0,
            "v2_files_found": 0,
            "invalid_files": 0,
            "errors": []
        }

        try:
            # Get storage backend
            storage_backend = self.get_storage_backend()

            # Find all JSON files in mediaplans directory
            json_files = []
            try:
                json_files = storage_backend.list_files("mediaplans", "*.json")
            except Exception:
                # Try root directory as fallback
                try:
                    json_files = storage_backend.list_files("", "*.json")
                except Exception as e:
                    result["errors"].append(f"Could not list JSON files: {e}")
                    return result

            logger.info(f"Validating {len(json_files)} JSON files for upgrade compatibility")

            for file_path in json_files:
                try:
                    # Read and parse file to check version
                    content = storage_backend.read_file(file_path, binary=False)
                    import json
                    data = json.loads(content)

                    # Extract schema version
                    schema_version = data.get("meta", {}).get("schema_version")

                    if not schema_version:
                        result["invalid_files"] += 1
                        result["errors"].append(f"File {file_path} has no schema version")
                        continue

                    # Normalize version for comparison
                    try:
                        from mediaplanpy.schema.version_utils import normalize_version, get_compatibility_type

                        normalized_version = normalize_version(schema_version)
                        compatibility = get_compatibility_type(normalized_version)

                        # Check for v0.0 files - these are REJECTED
                        if normalized_version.startswith("0."):
                            result["v0_files_rejected"] += 1
                            error_msg = (
                                f"File {file_path} uses unsupported schema version {schema_version} (v0.0.x). "
                                f"v0.0 support has been removed in SDK v2.0. Use SDK v1.x to migrate to v1.0 first."
                            )
                            result["errors"].append(error_msg)
                            logger.error(error_msg)
                            continue

                        # Count version distribution
                        major_version = int(normalized_version.split('.')[0])
                        if major_version == 1:
                            result["v1_files_found"] += 1
                        elif major_version == 2:
                            result["v2_files_found"] += 1

                        # Check overall compatibility
                        if compatibility == "unsupported":
                            result["invalid_files"] += 1
                            result["errors"].append(f"File {file_path} has unsupported schema version {schema_version}")

                    except Exception as e:
                        result["invalid_files"] += 1
                        result["errors"].append(f"Could not validate version for {file_path}: {e}")

                except json.JSONDecodeError as e:
                    result["invalid_files"] += 1
                    result["errors"].append(f"Invalid JSON in {file_path}: {e}")
                except Exception as e:
                    result["invalid_files"] += 1
                    result["errors"].append(f"Error reading {file_path}: {e}")

            # Log validation summary
            logger.info(f"Version validation complete: {result['v1_files_found']} v1.0 files, "
                        f"{result['v2_files_found']} v2.0 files, {result['v0_files_rejected']} v0.0 files rejected, "
                        f"{result['invalid_files']} invalid files")

        except Exception as e:
            result["errors"].append(f"Validation failed: {e}")

        return result


    def get_workspace_version_info(self) -> Dict[str, Any]:
        """
        Get version information about the current workspace.

        Returns:
            Dictionary with workspace version details

        Raises:
            WorkspaceError: If no configuration is loaded
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        from mediaplanpy import __version__, __schema_version__

        # Get workspace settings
        workspace_settings = self.config.get("workspace_settings", {})

        # Get current SDK and schema versions
        current_sdk_version = __version__
        current_schema_version = __schema_version__

        # Get workspace versions
        workspace_schema_version = workspace_settings.get("schema_version")
        workspace_sdk_required = workspace_settings.get("sdk_version_required")
        last_upgraded = workspace_settings.get("last_upgraded")

        # Determine compatibility status
        compatibility_status = "unknown"
        needs_upgrade = False

        if workspace_schema_version:
            from mediaplanpy.schema.version_utils import compare_versions, normalize_version

            try:
                # Normalize versions for comparison
                norm_workspace = normalize_version(workspace_schema_version)
                norm_current = normalize_version(current_schema_version)

                version_comparison = compare_versions(norm_workspace, norm_current)

                if version_comparison == 0:
                    compatibility_status = "current"
                elif version_comparison < 0:
                    compatibility_status = "outdated"
                    needs_upgrade = True
                else:
                    compatibility_status = "newer"

            except Exception:
                compatibility_status = "unknown"
        else:
            compatibility_status = "no_version_info"
            needs_upgrade = True

        return {
            "current_sdk_version": current_sdk_version,
            "current_schema_version": current_schema_version,
            "workspace_schema_version": workspace_schema_version,
            "workspace_sdk_required": workspace_sdk_required,
            "last_upgraded": last_upgraded,
            "compatibility_status": compatibility_status,
            "needs_upgrade": needs_upgrade,
            "workspace_name": self.config.get("workspace_name", "Unknown"),
            "workspace_id": self.config.get("workspace_id", "Unknown")
        }


    def check_workspace_compatibility(self) -> Dict[str, Any]:
        """
        Check compatibility between workspace and current SDK/schema versions.

        Returns:
            Dictionary with compatibility check results

        Raises:
            WorkspaceError: If no configuration is loaded
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        version_info = self.get_workspace_version_info()

        # Detailed compatibility analysis
        compatibility_result = {
            "is_compatible": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        # Check schema version compatibility
        if version_info["workspace_schema_version"]:
            from mediaplanpy.schema.version_utils import get_compatibility_type, get_migration_recommendation

            try:
                compatibility_type = get_compatibility_type(version_info["workspace_schema_version"])

                if compatibility_type == "unsupported":
                    compatibility_result["is_compatible"] = False
                    compatibility_result["errors"].append(
                        f"Workspace schema version {version_info['workspace_schema_version']} is not supported by SDK {version_info['current_sdk_version']}"
                    )

                    recommendation = get_migration_recommendation(version_info["workspace_schema_version"])
                    compatibility_result["recommendations"].append(recommendation.get("message", "Upgrade required"))

                elif compatibility_type == "deprecated":
                    compatibility_result["warnings"].append(
                        f"Workspace schema version {version_info['workspace_schema_version']} is deprecated"
                    )
                    compatibility_result["recommendations"].append("Consider upgrading workspace to current schema version")

                elif compatibility_type == "forward_minor":
                    compatibility_result["warnings"].append(
                        f"Workspace schema version {version_info['workspace_schema_version']} is newer than SDK supports"
                    )
                    compatibility_result["recommendations"].append("Consider upgrading SDK or downgrading workspace")

            except Exception as e:
                compatibility_result["warnings"].append(f"Could not determine schema compatibility: {str(e)}")

        # Check SDK version requirements
        if version_info["workspace_sdk_required"]:
            required_version = version_info["workspace_sdk_required"].replace(".x", ".0")
            current_version = version_info["current_sdk_version"]

            try:
                from mediaplanpy.schema.version_utils import compare_versions
                if compare_versions(current_version, required_version) < 0:
                    compatibility_result["is_compatible"] = False
                    compatibility_result["errors"].append(
                        f"Current SDK version {current_version} is below required version {version_info['workspace_sdk_required']}"
                    )
                    compatibility_result["recommendations"].append(f"Upgrade SDK to version {required_version} or later")
            except Exception:
                compatibility_result["warnings"].append("Could not compare SDK version requirements")

        # Add general recommendations
        if version_info["needs_upgrade"]:
            compatibility_result["recommendations"].append(
                "Run workspace.upgrade_workspace() to upgrade to current versions")

        return compatibility_result
