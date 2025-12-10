"""
Schema validation module for mediaplanpy.

This module provides utilities for validating media plans
against the appropriate schema with support for v2.0 and v3.0.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import RefResolver

from mediaplanpy.exceptions import ValidationError, SchemaError, SchemaVersionError, SchemaRegistryError
from mediaplanpy.schema.registry import SchemaRegistry
from mediaplanpy.schema.version_utils import normalize_version, is_backwards_compatible, is_unsupported

logger = logging.getLogger("mediaplanpy.schema.validator")


class SchemaValidator:
    """
    Validator for media plan data with support for v2.0 and v3.0 schemas.

    Validates media plans against the appropriate schema version and includes
    custom business logic validation for version-specific features including:
    - v2.0: Dictionary configuration and field consistency
    - v3.0: Array structures (target_audiences, target_locations, metric_formulas)
      and deprecated field detection
    """

    def __init__(self, registry: Optional[SchemaRegistry] = None):
        """
        Initialize a SchemaValidator.

        Args:
            registry: Schema registry to use. If None, creates a new one.
        """
        self.registry = registry or SchemaRegistry()

    def validate(self, media_plan: Dict[str, Any], version: Optional[str] = None) -> List[str]:
        """
        Validate a media plan against a schema (supports v2.0 and v3.0).

        Args:
            media_plan: The media plan data to validate.
            version: The schema version to validate against. If None, uses the version
                     specified in the media plan, or the current version if not specified.

        Returns:
            List of validation error messages, empty if validation succeeds.

        Raises:
            SchemaVersionError: If the specified version is not supported.
            SchemaRegistryError: If the schema cannot be loaded.
        """
        # Determine which version to use
        if version is None:
            # Try to get version from media plan
            version = media_plan.get("meta", {}).get("schema_version")
            if version is None:
                # Fall back to current version
                version = self.registry.get_current_version()
                logger.warning(f"No schema version specified in media plan, using current: {version}")

        # Normalize version to 2-digit format for schema loading
        try:
            normalized_version = normalize_version(version)
        except Exception as e:
            raise SchemaVersionError(f"Invalid version format '{version}': {e}")

        logger.debug(f"Validating media plan against schema version {normalized_version} (original: {version})")

        # Check if normalized version is supported
        if not self.registry.is_version_supported(normalized_version):
            raise SchemaVersionError(
                f"Schema version '{version}' (normalized: '{normalized_version}') is not supported. "
                f"Supported versions: {', '.join(self.registry.get_supported_versions())}"
            )

        # Perform schema validation
        schema_errors = self._validate_against_json_schema(media_plan, normalized_version)

        # Perform custom business logic validation
        business_logic_errors = self._validate_business_logic(media_plan, normalized_version)

        # Combine all errors
        all_errors = schema_errors + business_logic_errors

        logger.debug(f"Validation completed with {len(all_errors)} errors ({len(schema_errors)} schema, {len(business_logic_errors)} business logic)")
        return all_errors

    def _validate_against_json_schema(self, media_plan: Dict[str, Any], version: str) -> List[str]:
        """
        Validate media plan against JSON schema for the specified version.

        Args:
            media_plan: The media plan data to validate.
            version: The normalized schema version to validate against.

        Returns:
            List of JSON schema validation errors.

        Raises:
            SchemaRegistryError: If the schema cannot be loaded.
        """
        errors = []

        try:
            # Load the main schema and all related schemas for this version
            main_schema = self.registry.load_schema(version, "mediaplan.schema.json")
            all_schemas = self.registry.load_all_schemas(version)
        except SchemaRegistryError as e:
            raise SchemaRegistryError(f"Failed to load schema for validation: {str(e)}")

        # Create a resolver with bundled schemas for $ref resolution
        # FIXED: More robust schema store creation
        schema_store = {}

        # Add all loaded schemas to the store using their filenames as keys
        for filename, schema_content in all_schemas.items():
            schema_store[filename] = schema_content
            logger.debug(f"Added schema to store: {filename}")

        # Ensure we have the main schema in the store
        if "mediaplan.schema.json" not in schema_store:
            schema_store["mediaplan.schema.json"] = main_schema

        # Create resolver with the schema store
        resolver = RefResolver(
            base_uri="",  # Empty base URI since we're using a store
            referrer=main_schema,
            store=schema_store
        )

        # Log what schemas are available for debugging
        logger.debug(f"Schema store contains: {list(schema_store.keys())}")

        # Perform JSON schema validation
        try:
            jsonschema.validate(instance=media_plan, schema=main_schema, resolver=resolver)
            logger.debug("JSON schema validation passed")
        except JsonSchemaValidationError as e:
            # Extract useful validation errors with enhanced v2.0 field support
            path = " -> ".join([str(p) for p in e.path]) if e.path else "root"

            # Enhance error messages for common v2.0 validation issues
            error_message = self._enhance_validation_error_message(e, path, version)
            errors.append(error_message)

            logger.debug(f"JSON schema validation failed: {error_message}")

        return errors

    def _enhance_validation_error_message(self, error: JsonSchemaValidationError, path: str, version: str) -> str:
        """
        Enhance validation error messages with version-specific context.

        Args:
            error: The JSON schema validation error.
            path: The path where the error occurred.
            version: The schema version being validated against.

        Returns:
            Enhanced error message.
        """
        base_message = f"Validation error at {path}: {error.message}"

        # Add specific guidance for common v2.0 validation issues
        if "created_by_name" in error.message and version.startswith("2."):
            base_message += " (Note: In schema v2.0, 'created_by_name' is required in the meta section)"
        elif "dictionary" in path and "additionalProperties" in error.message:
            base_message += " (Note: Dictionary configuration must follow the v2.0 schema structure)"
        elif any(field in error.message for field in ["budget_currency", "agency_id", "workflow_status"]):
            base_message += " (Note: This is a new optional field in schema v2.0)"

        # Add specific guidance for common v3.0 validation issues
        if version.startswith("3."):
            if "target_audiences" in path or "target_audiences" in error.message:
                base_message += " (Note: Schema v3.0 uses target_audiences array instead of audience_* fields)"
            elif "target_locations" in path or "target_locations" in error.message:
                base_message += " (Note: Schema v3.0 uses target_locations array instead of location_* fields)"
            elif "metric_formulas" in path or "metric_formulas" in error.message:
                base_message += " (Note: Schema v3.0 supports metric_formulas as a dictionary of formula objects)"
            elif "lineitem_custom_dimensions" in path or "lineitem_custom_dimensions" in error.message:
                base_message += " (Note: Schema v3.0 renamed 'custom_dimensions' to 'lineitem_custom_dimensions' in dictionary)"

        return base_message

    def _validate_business_logic(self, media_plan: Dict[str, Any], version: str) -> List[str]:
        """
        Validate business logic rules beyond JSON schema validation.

        Args:
            media_plan: The media plan data to validate.
            version: The normalized schema version.

        Returns:
            List of business logic validation errors.
        """
        errors = []

        # Existing business logic validation that should work for all versions
        errors.extend(self._validate_date_consistency(media_plan))

        # v2.0-specific business logic validation
        if version.startswith("2."):
            errors.extend(self._validate_dictionary_configuration(media_plan))
            errors.extend(self._validate_v2_field_consistency(media_plan))

        # v3.0-specific business logic validation
        if version.startswith("3."):
            errors.extend(self._validate_v3_field_consistency(media_plan))
            errors.extend(self._validate_v3_array_structures(media_plan))

        return errors

    def _validate_date_consistency(self, media_plan: Dict[str, Any]) -> List[str]:
        """
        Validate that line item dates are consistent with campaign dates.

        Args:
            media_plan: The media plan data to validate.

        Returns:
            List of date consistency errors.
        """
        errors = []

        if "lineitems" not in media_plan or "campaign" not in media_plan:
            return errors

        campaign = media_plan["campaign"]
        campaign_start = campaign.get("start_date")
        campaign_end = campaign.get("end_date")

        if not campaign_start or not campaign_end:
            return errors

        for i, item in enumerate(media_plan["lineitems"]):
            item_start = item.get("start_date")
            item_end = item.get("end_date")

            if item_start and item_start < campaign_start:
                errors.append(
                    f"Line item {i} ({item.get('id', 'unnamed')}) starts before campaign: "
                    f"{item_start} < {campaign_start}"
                )

            if item_end and campaign_end and item_end > campaign_end:
                errors.append(
                    f"Line item {i} ({item.get('id', 'unnamed')}) ends after campaign: "
                    f"{item_end} > {campaign_end}"
                )

        return errors

    def _validate_dictionary_configuration(self, media_plan: Dict[str, Any]) -> List[str]:
        """
        Validate v2.0 dictionary configuration and its consistency with line items.

        Args:
            media_plan: The media plan data to validate.

        Returns:
            List of dictionary validation errors and warnings.
        """
        errors = []

        dictionary = media_plan.get("dictionary")
        if not dictionary:
            # Dictionary is optional, so no error if missing
            return errors

        logger.debug("Validating v2.0 dictionary configuration")

        # Validate dictionary structure and business rules
        errors.extend(self._validate_dictionary_structure(dictionary))

        # Validate consistency between dictionary configuration and line item data
        if "lineitems" in media_plan:
            errors.extend(self._validate_dictionary_lineitem_consistency(dictionary, media_plan["lineitems"]))

        return errors

    def _validate_dictionary_structure(self, dictionary: Dict[str, Any]) -> List[str]:
        """
        Validate the internal structure and business rules of dictionary configuration.

        Args:
            dictionary: The dictionary configuration to validate.

        Returns:
            List of dictionary structure validation errors.
        """
        errors = []

        # Define valid custom field patterns
        valid_custom_dimensions = {f"dim_custom{i}" for i in range(1, 11)}
        valid_custom_metrics = {f"metric_custom{i}" for i in range(1, 11)}
        valid_custom_costs = {f"cost_custom{i}" for i in range(1, 11)}

        # Validate custom_dimensions section
        custom_dimensions = dictionary.get("custom_dimensions", {})
        if custom_dimensions:
            for field_name, config in custom_dimensions.items():
                if field_name not in valid_custom_dimensions:
                    errors.append(f"Invalid custom dimension field name: {field_name}")

                # Validate field configuration
                field_errors = self._validate_custom_field_config(config, field_name, "dimension")
                errors.extend(field_errors)

        # Validate custom_metrics section
        custom_metrics = dictionary.get("custom_metrics", {})
        if custom_metrics:
            for field_name, config in custom_metrics.items():
                if field_name not in valid_custom_metrics:
                    errors.append(f"Invalid custom metric field name: {field_name}")

                # Validate field configuration
                field_errors = self._validate_custom_field_config(config, field_name, "metric")
                errors.extend(field_errors)

        # Validate custom_costs section
        custom_costs = dictionary.get("custom_costs", {})
        if custom_costs:
            for field_name, config in custom_costs.items():
                if field_name not in valid_custom_costs:
                    errors.append(f"Invalid custom cost field name: {field_name}")

                # Validate field configuration
                field_errors = self._validate_custom_field_config(config, field_name, "cost")
                errors.extend(field_errors)

        return errors

    def _validate_custom_field_config(self, config: Dict[str, Any], field_name: str, field_type: str) -> List[str]:
        """
        Validate a single custom field configuration.

        Args:
            config: The custom field configuration.
            field_name: Name of the custom field.
            field_type: Type of custom field (dimension, metric, cost).

        Returns:
            List of validation errors for this custom field.
        """
        errors = []

        if not isinstance(config, dict):
            errors.append(f"Custom {field_type} field '{field_name}' configuration must be an object")
            return errors

        # Validate required 'status' field
        status = config.get("status")
        if status is None:
            errors.append(f"Custom {field_type} field '{field_name}' missing required 'status' field")
        elif status not in ["enabled", "disabled"]:
            errors.append(f"Custom {field_type} field '{field_name}' status must be 'enabled' or 'disabled', got: {status}")

        # Validate 'caption' field requirements
        caption = config.get("caption")
        if status == "enabled":
            if not caption:
                errors.append(f"Custom {field_type} field '{field_name}' requires 'caption' when status is 'enabled'")
            elif len(caption.strip()) == 0:
                errors.append(f"Custom {field_type} field '{field_name}' caption cannot be empty when enabled")
            elif len(caption) > 100:
                errors.append(f"Custom {field_type} field '{field_name}' caption too long (max 100 characters)")

        # Check for unexpected additional properties
        expected_properties = {"status", "caption"}
        unexpected_properties = set(config.keys()) - expected_properties
        if unexpected_properties:
            errors.append(f"Custom {field_type} field '{field_name}' has unexpected properties: {', '.join(unexpected_properties)}")

        return errors

    def _validate_dictionary_lineitem_consistency(self, dictionary: Dict[str, Any], lineitems: List[Dict[str, Any]]) -> List[str]:
        """
        Validate consistency between dictionary configuration and line item data.

        This checks for issues like:
        - Enabled custom fields that have no data in any line items (warning)
        - Line items with data in custom fields that aren't enabled in dictionary (warning)

        Args:
            dictionary: The dictionary configuration.
            lineitems: List of line items to check.

        Returns:
            List of consistency validation warnings.
        """
        warnings = []

        if not lineitems:
            # No line items to validate against
            return warnings

        # Get all enabled custom fields from dictionary
        # enabled_fields = self._get_enabled_custom_fields(dictionary)

        # Get all custom fields that have data in line items
        # fields_with_data = self._get_custom_fields_with_data(lineitems)

        # Check for enabled fields with no data (potential configuration issue)
        # unused_enabled_fields = enabled_fields - fields_with_data
        # for field in unused_enabled_fields:
        #     warnings.append(f"Warning: Custom field '{field}' is enabled in dictionary but has no data in any line items")

        # Check for fields with data that aren't enabled (potential missing configuration)
        # unenabled_fields_with_data = fields_with_data - enabled_fields
        # for field in unenabled_fields_with_data:
        #     warnings.append(f"Warning: Custom field '{field}' has data in line items but is not enabled in dictionary")

        return warnings

    def _get_enabled_custom_fields(self, dictionary: Dict[str, Any]) -> set:
        """
        Get set of all enabled custom fields from dictionary configuration.

        Args:
            dictionary: The dictionary configuration.

        Returns:
            Set of enabled custom field names.
        """
        enabled_fields = set()

        # Check custom_dimensions
        custom_dimensions = dictionary.get("custom_dimensions", {})
        for field_name, config in custom_dimensions.items():
            if isinstance(config, dict) and config.get("status") == "enabled":
                enabled_fields.add(field_name)

        # Check custom_metrics
        custom_metrics = dictionary.get("custom_metrics", {})
        for field_name, config in custom_metrics.items():
            if isinstance(config, dict) and config.get("status") == "enabled":
                enabled_fields.add(field_name)

        # Check custom_costs
        custom_costs = dictionary.get("custom_costs", {})
        for field_name, config in custom_costs.items():
            if isinstance(config, dict) and config.get("status") == "enabled":
                enabled_fields.add(field_name)

        return enabled_fields

    def _get_custom_fields_with_data(self, lineitems: List[Dict[str, Any]]) -> set:
        """
        Get set of all custom fields that have data in at least one line item.

        Args:
            lineitems: List of line items to check.

        Returns:
            Set of custom field names that have data.
        """
        fields_with_data = set()

        # Define all possible custom field names
        custom_field_patterns = (
            [f"dim_custom{i}" for i in range(1, 11)] +
            [f"metric_custom{i}" for i in range(1, 11)] +
            [f"cost_custom{i}" for i in range(1, 11)]
        )

        for lineitem in lineitems:
            for field_name in custom_field_patterns:
                field_value = lineitem.get(field_name)
                if field_value is not None and str(field_value).strip():
                    fields_with_data.add(field_name)

        return fields_with_data

    def _validate_v2_field_consistency(self, media_plan: Dict[str, Any]) -> List[str]:
        """
        Validate consistency of new v2.0 fields and their relationships.

        Args:
            media_plan: The media plan data to validate.

        Returns:
            List of v2.0 field consistency validation errors.
        """
        errors = []

        # Validate campaign field consistency
        # Removed unnecessary data validation
        # campaign = media_plan.get("campaign", {})
        # errors.extend(self._validate_campaign_v2_consistency(campaign))

        # Validate line item field consistency
        lineitems = media_plan.get("lineitems", [])
        for i, lineitem in enumerate(lineitems):
            lineitem_errors = self._validate_lineitem_v2_consistency(lineitem, i)
            errors.extend(lineitem_errors)

        # Validate meta field consistency
        meta = media_plan.get("meta", {})
        errors.extend(self._validate_meta_v2_consistency(meta))

        return errors

    def _validate_campaign_v2_consistency(self, campaign: Dict[str, Any]) -> List[str]:
        """
        Validate consistency of v2.0 campaign fields.

        Args:
            campaign: The campaign data to validate.

        Returns:
            List of campaign consistency validation errors.
        """
        errors = []

        # Validate ID and name field pairs consistency
        id_name_pairs = [
            ("agency_id", "agency_name", "agency"),
            ("advertiser_id", "advertiser_name", "advertiser"),
            ("campaign_type_id", "campaign_type_name", "campaign_type"),
            ("workflow_status_id", "workflow_status_name", "workflow_status")
        ]

        for id_field, name_field, field_type in id_name_pairs:
            id_value = campaign.get(id_field)
            name_value = campaign.get(name_field)

            # If both are provided, that's ideal
            if id_value and name_value:
                continue
            # If only one is provided, issue a warning (not an error for flexibility)
            elif id_value and not name_value:
                errors.append(f"Warning: {field_type}_id provided without corresponding {field_type}_name")
            elif name_value and not id_value:
                errors.append(f"Warning: {field_type}_name provided without corresponding {field_type}_id")

        return errors

    def _validate_lineitem_v2_consistency(self, lineitem: Dict[str, Any], lineitem_index: int) -> List[str]:
        """
        Validate consistency of v2.0 line item fields.

        Args:
            lineitem: The line item data to validate.
            lineitem_index: Index of the line item for error reporting.

        Returns:
            List of line item consistency validation errors.
        """
        errors = []

        # Validate application funnel consistency (new v2.0 metrics)
        # app_start = lineitem.get("metric_application_start")
        # app_complete = lineitem.get("metric_application_complete")
        #
        # if (app_start is not None and app_complete is not None and
        #     app_complete > app_start):
        #     errors.append(
        #         f"Line item {lineitem_index} ({lineitem.get('id', 'unnamed')}): "
        #         f"metric_application_complete ({app_complete}) cannot be greater than "
        #         f"metric_application_start ({app_start})"
        #     )

        # Validate currency consistency
        budget_currency = lineitem.get("cost_currency")
        if budget_currency:
            # Basic currency code validation (should be 3 letters)
            if len(budget_currency.strip()) != 3 or not budget_currency.isalpha():
                errors.append(
                    f"Line item {lineitem_index} ({lineitem.get('id', 'unnamed')}): "
                    f"cost_currency should be a 3-letter currency code, got: {budget_currency}"
                )

        return errors

    def _validate_meta_v2_consistency(self, meta: Dict[str, Any]) -> List[str]:
        """
        Validate consistency of v2.0 meta fields.

        Args:
            meta: The meta data to validate.

        Returns:
            List of meta consistency validation errors.
        """
        errors = []

        # Validate status field consistency
        is_current = meta.get("is_current")
        is_archived = meta.get("is_archived")

        if is_current is True and is_archived is True:
            errors.append("Media plan cannot be both current (is_current: true) and archived (is_archived: true)")

        # Validate parent_id doesn't reference itself
        parent_id = meta.get("parent_id")
        plan_id = meta.get("id")

        if parent_id and plan_id and parent_id == plan_id:
            errors.append("Media plan parent_id cannot reference itself")

        return errors

    def _validate_v3_field_consistency(self, media_plan: Dict[str, Any]) -> List[str]:
        """
        Validate consistency of v3.0 fields and detect usage of deprecated fields.

        Args:
            media_plan: The media plan data to validate.

        Returns:
            List of v3.0 field consistency validation errors and warnings.
        """
        errors = []

        # Check campaign for deprecated field usage
        campaign = media_plan.get("campaign", {})
        deprecated_audience_fields = {
            "audience_name", "audience_age_start", "audience_age_end",
            "audience_gender", "audience_interests"
        }
        deprecated_location_fields = {"location_type", "locations"}

        # Warn if deprecated audience fields are used
        used_deprecated_audience = [f for f in deprecated_audience_fields if campaign.get(f) is not None]
        if used_deprecated_audience:
            errors.append(
                f"Warning: Deprecated audience fields used in campaign: {', '.join(used_deprecated_audience)}. "
                "Consider migrating to target_audiences array in schema v3.0"
            )

        # Warn if deprecated location fields are used
        used_deprecated_location = [f for f in deprecated_location_fields if campaign.get(f) is not None]
        if used_deprecated_location:
            errors.append(
                f"Warning: Deprecated location fields used in campaign: {', '.join(used_deprecated_location)}. "
                "Consider migrating to target_locations array in schema v3.0"
            )

        # Validate dictionary field structure (lineitem_custom_dimensions vs custom_dimensions)
        dictionary = media_plan.get("dictionary", {})
        if dictionary:
            # Check if old field name is used
            if "custom_dimensions" in dictionary and "lineitem_custom_dimensions" not in dictionary:
                errors.append(
                    "Warning: Dictionary uses 'custom_dimensions' field. "
                    "In schema v3.0, this should be 'lineitem_custom_dimensions'"
                )

        return errors

    def _validate_v3_array_structures(self, media_plan: Dict[str, Any]) -> List[str]:
        """
        Validate v3.0 array structures (target_audiences, target_locations, metric_formulas).

        Args:
            media_plan: The media plan data to validate.

        Returns:
            List of array structure validation errors.
        """
        errors = []

        campaign = media_plan.get("campaign", {})

        # Validate target_audiences array
        target_audiences = campaign.get("target_audiences", [])
        if target_audiences:
            if not isinstance(target_audiences, list):
                errors.append("campaign.target_audiences must be an array")
            else:
                for i, audience in enumerate(target_audiences):
                    if not isinstance(audience, dict):
                        errors.append(f"campaign.target_audiences[{i}] must be an object")
                        continue

                    # Check required field
                    if not audience.get("name"):
                        errors.append(f"campaign.target_audiences[{i}] missing required field 'name'")

                    # Validate age range if both are present
                    age_start = audience.get("demo_age_start")
                    age_end = audience.get("demo_age_end")
                    if age_start is not None and age_end is not None and age_start > age_end:
                        errors.append(
                            f"campaign.target_audiences[{i}]: demo_age_start ({age_start}) "
                            f"must be <= demo_age_end ({age_end})"
                        )

        # Validate target_locations array
        target_locations = campaign.get("target_locations", [])
        if target_locations:
            if not isinstance(target_locations, list):
                errors.append("campaign.target_locations must be an array")
            else:
                for i, location in enumerate(target_locations):
                    if not isinstance(location, dict):
                        errors.append(f"campaign.target_locations[{i}] must be an object")
                        continue

                    # Check required field
                    if not location.get("name"):
                        errors.append(f"campaign.target_locations[{i}] missing required field 'name'")

                    # Validate population_percent if present
                    pop_percent = location.get("population_percent")
                    if pop_percent is not None:
                        if not isinstance(pop_percent, (int, float)):
                            errors.append(
                                f"campaign.target_locations[{i}]: population_percent must be a number"
                            )
                        elif pop_percent < 0 or pop_percent > 1:
                            errors.append(
                                f"campaign.target_locations[{i}]: population_percent must be between 0 and 1, "
                                f"got: {pop_percent}"
                            )

        # Validate metric_formulas in line items
        lineitems = media_plan.get("lineitems", [])
        for lineitem_idx, lineitem in enumerate(lineitems):
            metric_formulas = lineitem.get("metric_formulas", {})
            if metric_formulas:
                if not isinstance(metric_formulas, dict):
                    errors.append(f"lineitems[{lineitem_idx}].metric_formulas must be an object")
                else:
                    for metric_name, formula in metric_formulas.items():
                        if not isinstance(formula, dict):
                            errors.append(
                                f"lineitems[{lineitem_idx}].metric_formulas[{metric_name}] must be an object"
                            )
                            continue

                        # Check required field
                        if not formula.get("formula_type"):
                            errors.append(
                                f"lineitems[{lineitem_idx}].metric_formulas[{metric_name}] "
                                "missing required field 'formula_type'"
                            )

        return errors

    def validate_file(self, file_path: str, version: Optional[str] = None) -> List[str]:
        """
        Validate a media plan JSON file against a schema with version handling.

        Args:
            file_path: Path to the media plan JSON file.
            version: The schema version to validate against. If None, uses the version
                     specified in the media plan, or the current version if not specified.

        Returns:
            List of validation error messages, empty if validation succeeds.

        Raises:
            SchemaVersionError: If the specified version is not supported.
            SchemaRegistryError: If the schema cannot be loaded.
            ValidationError: If the file cannot be read or parsed.
        """
        try:
            with open(file_path, 'r') as f:
                media_plan = json.load(f)

            # Log the file being validated
            file_version = media_plan.get("meta", {}).get("schema_version", "unknown")
            logger.debug(f"Validating file {file_path} with schema version {file_version}")

            return self.validate(media_plan, version)

        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {file_path}: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error reading file {file_path}: {str(e)}")

    def validate_comprehensive(self, media_plan: Dict[str, Any], version: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Perform comprehensive validation with categorized results.

        Args:
            media_plan: The media plan data to validate.
            version: The schema version to validate against.

        Returns:
            Dictionary with categorized validation results:
            - 'errors': Critical validation errors that prevent usage
            - 'warnings': Non-critical issues that should be addressed
            - 'info': Informational messages about the validation
        """
        result = {
            'errors': [],
            'warnings': [],
            'info': []
        }

        try:
            # Determine version
            if version is None:
                version = media_plan.get("meta", {}).get("schema_version")
                if version is None:
                    version = self.registry.get_current_version()
                    result['info'].append(f"No schema version specified, using current: {version}")

            normalized_version = normalize_version(version)
            result['info'].append(f"Validating against schema version {normalized_version}")

            # Perform validation
            all_errors = self.validate(media_plan, version)

            # Categorize errors and warnings
            for error in all_errors:
                if error.startswith("Warning:"):
                    result['warnings'].append(error)
                else:
                    result['errors'].append(error)

            # Add version-specific information
            if normalized_version.startswith("2.") and "dictionary" in media_plan:
                result['info'].append("Found v2.0 dictionary configuration")

            if normalized_version.startswith("1."):
                result['warnings'].append("Using legacy v1.0 schema - consider upgrading to v3.0")

            if normalized_version.startswith("3."):
                campaign = media_plan.get("campaign", {})
                if "target_audiences" in campaign:
                    result['info'].append(
                        f"Found v3.0 target_audiences array with {len(campaign['target_audiences'])} audience(s)"
                    )
                if "target_locations" in campaign:
                    result['info'].append(
                        f"Found v3.0 target_locations array with {len(campaign['target_locations'])} location(s)"
                    )

                # Check for metric_formulas in line items
                lineitems = media_plan.get("lineitems", [])
                lineitem_with_formulas = sum(1 for li in lineitems if li.get("metric_formulas"))
                if lineitem_with_formulas > 0:
                    result['info'].append(
                        f"Found v3.0 metric_formulas in {lineitem_with_formulas} line item(s)"
                    )

        except Exception as e:
            result['errors'].append(f"Validation failed: {str(e)}")

        return result