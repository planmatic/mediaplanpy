"""
Media Plan model for mediaplanpy.

This module provides the MediaPlan model class representing a complete
media plan with campaigns and line items, following the Media Plan Open
Data Standard v2.0.
"""

import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Union, ClassVar

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel
from mediaplanpy.models.campaign import Campaign
from mediaplanpy.models.target_audience import TargetAudience
from mediaplanpy.models.lineitem import LineItem
from mediaplanpy.models.dictionary import Dictionary
from mediaplanpy.models.mediaplan_json import JsonMixin
from mediaplanpy.models.mediaplan_storage import StorageMixin
from mediaplanpy.models.mediaplan_excel import ExcelMixin
from mediaplanpy.models.mediaplan_database import DatabaseMixin
from mediaplanpy.models.mediaplan_formulas import FormulasMixin
from mediaplanpy.exceptions import ValidationError, SchemaVersionError, SchemaError, MediaPlanError, StorageError
from mediaplanpy.schema import get_current_version, SchemaValidator, SchemaMigrator

import logging
from mediaplanpy.schema.version_utils import (
    is_backwards_compatible,
    is_forward_minor,
    is_unsupported,
    normalize_version,
    get_compatibility_type,
    get_migration_recommendation
)

logger = logging.getLogger("mediaplanpy.models.mediaplan")


class Meta(BaseModel):
    """
    Metadata for a media plan following v3.0 schema.

    Updated from v2.0 to include custom dimensions and properties.
    """
    id: str = Field(..., description="Unique identifier for the media plan")
    schema_version: str = Field(..., description="Version of the schema being used")

    # UPDATED v2.0: created_by_name is now required (vs optional created_by in v1.0)
    created_by_name: str = Field(..., description="Full name of the user who created this media plan")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

    # Optional fields from v1.0 (maintained for backward compatibility)
    name: Optional[str] = Field(None, description="Name of the media plan")
    comments: Optional[str] = Field(None, description="Comments about the media plan")

    # NEW v2.0 FIELDS - All optional for backward compatibility
    created_by_id: Optional[str] = Field(None, description="Unique identifier of the user who created this media plan")
    is_current: Optional[bool] = Field(None, description="Whether this is the current/active version of the media plan")
    is_archived: Optional[bool] = Field(None, description="Whether this media plan has been archived")
    parent_id: Optional[str] = Field(None, description="Identifier of the parent media plan if this is a revision or copy")

    # NEW v3.0 FIELDS - All optional for backward compatibility
    dim_custom1: Optional[str] = Field(None, description="Custom dimension 1 for meta")
    dim_custom2: Optional[str] = Field(None, description="Custom dimension 2 for meta")
    dim_custom3: Optional[str] = Field(None, description="Custom dimension 3 for meta")
    dim_custom4: Optional[str] = Field(None, description="Custom dimension 4 for meta")
    dim_custom5: Optional[str] = Field(None, description="Custom dimension 5 for meta")
    custom_properties: Optional[Dict[str, Any]] = Field(None, description="Additional custom properties as key-value pairs")

    def validate_model(self) -> List[str]:
        """
        Perform additional validation beyond what Pydantic provides.

        Returns:
            A list of validation error messages, if any.
        """
        errors = super().validate_model()

        # Validate schema version format
        if self.schema_version:
            try:
                from mediaplanpy.schema.version_utils import validate_version_format
                if not validate_version_format(self.schema_version):
                    errors.append(f"Invalid schema_version format: {self.schema_version}")
            except ImportError:
                # Fallback validation
                import re
                if not re.match(r'^v?[0-9]+\.[0-9]+(\.[0-9]+)?$', self.schema_version):
                    errors.append(f"Invalid schema_version format: {self.schema_version}")

        # Validate status consistency
        if self.is_current is True and self.is_archived is True:
            errors.append("Media plan cannot be both current and archived")

        # Validate parent_id format if provided
        if self.parent_id and self.parent_id == self.id:
            errors.append("parent_id cannot be the same as the media plan id")

        return errors


class MediaPlan(JsonMixin, StorageMixin, ExcelMixin, DatabaseMixin, FormulasMixin, BaseModel):
    """
    Represents a complete media plan following the Media Plan Open Data Standard v3.0.

    A media plan contains metadata, a campaign, line items, and optionally a
    dictionary for custom field configuration.

    Note: BaseModel is placed last in the inheritance order to allow mixin methods
    (like export_to_json) to take precedence over BaseModel's simple implementations.
    """

    # Meta information (updated for v2.0)
    meta: Meta = Field(..., description="Metadata for the media plan")

    # The campaign (same as v1.0)
    campaign: Campaign = Field(..., description="The campaign details")

    # Line items (same as v1.0)
    lineitems: List[LineItem] = Field(default_factory=list, description="Line items in the media plan")

    # NEW v2.0 FIELD: Dictionary for custom field configuration
    dictionary: Optional[Dictionary] = Field(None, description="Configuration dictionary defining custom field settings and captions")

    def model_post_init(self, __context: Any) -> None:
        """
        Post-initialization hook to set parent references on child objects.

        This ensures that lineitems have a reference to their parent MediaPlan,
        enabling smart metric methods to access the dictionary automatically.

        Note: This creates a circular reference (MediaPlan ↔ LineItem), but it's
        safe because _mediaplan is excluded from serialization.
        """
        # Set parent reference on all lineitems
        for lineitem in self.lineitems:
            lineitem._mediaplan = self

    @classmethod
    def check_schema_version(cls, data: Dict[str, Any]) -> None:
        """
        Check schema version compatibility and handle version differences.

        Args:
            data: The data to check (will be modified if migration needed).

        Raises:
            SchemaVersionError: If the schema version is not supported.
        """
        # Get version from data
        file_version = data.get("meta", {}).get("schema_version")
        if not file_version:
            # If no version specified, assume current version and add it
            from mediaplanpy import __schema_version__
            logger.warning("No schema version found in data, assuming current version")
            if "meta" not in data:
                data["meta"] = {}
            data["meta"]["schema_version"] = f"v{__schema_version__}"
            return

        # Normalize version to 2-digit format for comparison
        try:
            normalized_file_version = normalize_version(file_version)
        except Exception as e:
            raise SchemaVersionError(f"Invalid schema version format '{file_version}': {e}")

        # Get compatibility type
        compatibility = get_compatibility_type(normalized_file_version)

        # Handle each compatibility case
        if compatibility == "native":
            # Native support - no action needed
            logger.debug(f"Schema version {file_version} is natively supported")
            return

        elif compatibility == "forward_minor":
            # Forward compatible - log warning about potential data loss
            from mediaplanpy import __schema_version__
            current_version = f"v{__schema_version__}"
            logger.warning(
                f"⚠️ Media plan uses schema {file_version}. Current SDK supports up to {current_version}. "
                f"File imported and downgraded to {current_version} - new fields preserved but may be inactive."
            )
            # Update version to current (Pydantic will preserve unknown fields)
            data["meta"]["schema_version"] = current_version
            return

        elif compatibility == "backward_compatible":
            # Backward compatible - version bump needed
            from mediaplanpy import __schema_version__
            current_version = f"v{__schema_version__}"
            logger.info(f"ℹ️ Media plan migrated from schema {file_version} to {current_version}")

            # Perform version bump (update version field)
            data["meta"]["schema_version"] = current_version
            return

        elif compatibility == "deprecated":
            # Deprecated but supported - migrate with warning
            from mediaplanpy import __schema_version__
            current_version = f"v{__schema_version__}"

            # Import migration logic
            from mediaplanpy.schema import SchemaMigrator
            migrator = SchemaMigrator()

            try:
                # Perform migration
                migrated_data = migrator.migrate(data, file_version, current_version)

                # Update original data dict in place
                data.clear()
                data.update(migrated_data)

                logger.warning(
                    f"⚠️ Media plan migrated from deprecated schema {file_version} to {current_version}. "
                    f"Support for this version may be removed in future releases."
                )
                return

            except Exception as e:
                raise SchemaVersionError(f"Failed to migrate from {file_version} to {current_version}: {e}")

        elif compatibility == "unsupported":
            # Unsupported version
            recommendation = get_migration_recommendation(normalized_file_version)
            error_msg = recommendation.get("error", f"Schema version {file_version} is not supported")
            raise SchemaVersionError(f"❌ {error_msg}")

        else:
            # Unknown compatibility type
            raise SchemaVersionError(f"❌ Cannot determine compatibility for schema version {file_version}")

    def validate_model(self) -> List[str]:
        """
        Perform additional validation beyond what Pydantic provides.
        Updated to work seamlessly with v2.0 schema validation.

        Returns:
            A list of validation error messages, if any.
        """
        errors = super().validate_model()

        # Validate line items
        if self.lineitems:
            # INFORMATIONAL: Check that line item dates are within campaign dates
            # Log warnings but don't block creation
            for i, line_item in enumerate(self.lineitems):
                if line_item.start_date < self.campaign.start_date:
                    logger.warning(
                        f"Line item {i} ({line_item.id}) starts before campaign: "
                        f"{line_item.start_date} < {self.campaign.start_date}"
                    )

                if line_item.end_date > self.campaign.end_date:
                    logger.warning(
                        f"Line item {i} ({line_item.id}) ends after campaign: "
                        f"{line_item.end_date} > {self.campaign.end_date}"
                    )

            # Budget matching validation removed - it's valid to have unallocated/over-allocated budget

        # INFORMATIONAL: Dictionary consistency check
        # Log warnings but don't block creation
        if self.dictionary:
            # Validate that enabled custom fields in dictionary have corresponding data in line items
            enabled_fields = self.dictionary.get_enabled_fields()

            if enabled_fields and self.lineitems:
                # Check if any line items use the enabled custom fields
                unused_fields = set(enabled_fields.keys())

                for lineitem in self.lineitems:
                    for field_name in list(unused_fields):
                        field_value = getattr(lineitem, field_name, None)
                        if field_value is not None and str(field_value).strip():
                            unused_fields.discard(field_name)

                # Log informational warnings for enabled fields that aren't used
                for unused_field in unused_fields:
                    logger.info(
                        f"Custom field '{unused_field}' is enabled in dictionary "
                        f"but not used in any line items"
                    )

        return errors

    def create_lineitem(self, line_items: Union[LineItem, Dict[str, Any], List[Union[LineItem, Dict[str, Any]]]],
                        validate: bool = True, **kwargs) -> Union[LineItem, List[LineItem]]:
        """
        Create one or more line items for this media plan.

        Automatically inherits start_date, end_date from campaign if not provided.
        All v3.0 LineItem fields are supported.

        Args:
            line_items: Single line item or list of line items to create.
                       Each item can be a LineItem object or dictionary.
            validate: Whether to validate line items before creation.
            **kwargs: Additional line item parameters (applied to all items if line_items is a list).

                      Common v3.0 kwargs examples:
                      - kpi_value: Target KPI value
                      - buy_type, buy_commitment: Buy information
                      - is_aggregate, aggregation_level: Aggregation settings
                      - cost_currency_exchange_rate: Multi-currency support
                      - cost_minimum, cost_maximum: Budget constraints
                      - metric_view_starts, metric_reach, etc.: New v3.0 metrics
                      - metric_formulas: Dict[str, MetricFormula] for calculated metrics
                      - custom_properties: Dict for extensibility

        Returns:
            Single LineItem object if input was single item, or List[LineItem]
            if input was a list.

        Raises:
            ValidationError: If line item data is invalid
            MediaPlanError: If creation fails

        Examples:
            # Single line item (backward compatible)
            item = plan.create_lineitem({
                "name": "Social Campaign",
                "cost_total": 5000,
                "channel": "social"
            })

            # v3.0 line item with new fields
            item = plan.create_lineitem({
                "name": "Display Campaign",
                "cost_total": 10000,
                "buy_type": "Programmatic",
                "kpi_value": 2.5,
                "metric_reach": 100000,
                "custom_properties": {"audience_segment": "premium"}
            })

            # Multiple line items
            items = plan.create_lineitem([item1_dict, item2_dict])
        """
        from datetime import date
        from decimal import Decimal
        import copy

        # Step 1: Input Processing - Determine if input is single item or list
        is_single_input = not isinstance(line_items, list)

        # Normalize to list for uniform processing
        if is_single_input:
            items_to_process = [line_items]
        else:
            items_to_process = line_items

        # Step 2: Pre-process and validate all items before creating any
        processed_items = []
        validation_errors = []

        for i, line_item in enumerate(items_to_process):
            try:
                # Convert dict to LineItem if necessary
                if isinstance(line_item, dict):
                    # Create a copy to avoid modifying the original
                    line_item_data = line_item.copy()
                    line_item_data.update(kwargs)  # Merge any additional kwargs

                    # Generate ID if not provided
                    if 'id' not in line_item_data or not line_item_data['id']:
                        line_item_data['id'] = f"pli_{uuid.uuid4().hex[:8]}"

                    # Inherit start date from campaign if not provided
                    if 'start_date' not in line_item_data or not line_item_data['start_date']:
                        line_item_data['start_date'] = self.campaign.start_date

                    # Inherit end date from campaign if not provided
                    if 'end_date' not in line_item_data or not line_item_data['end_date']:
                        line_item_data['end_date'] = self.campaign.end_date

                    # Set default cost_total to 0 if not provided
                    if 'cost_total' not in line_item_data or line_item_data['cost_total'] is None:
                        line_item_data['cost_total'] = Decimal('0')

                    # Convert string dates to date objects if necessary
                    for date_field in ['start_date', 'end_date']:
                        if isinstance(line_item_data.get(date_field), str):
                            line_item_data[date_field] = date.fromisoformat(line_item_data[date_field])

                    # Convert cost_total to Decimal if necessary
                    if isinstance(line_item_data.get('cost_total'), (int, float, str)):
                        line_item_data['cost_total'] = Decimal(str(line_item_data['cost_total']))

                    # Create LineItem instance
                    processed_item = LineItem.from_dict(line_item_data)
                else:
                    # For LineItem instances, apply kwargs if any provided
                    if kwargs:
                        line_item_dict = line_item.to_dict()
                        line_item_dict.update(kwargs)
                        processed_item = LineItem.from_dict(line_item_dict)
                    else:
                        processed_item = line_item

                    # Generate ID if missing
                    if not processed_item.id:
                        processed_item.id = f"pli_{uuid.uuid4().hex[:8]}"

                # Validate the individual item if requested
                if validate:
                    # Use the consolidated validate() method
                    item_validation_errors = processed_item.validate()
                    if item_validation_errors:
                        validation_errors.extend([f"Item {i}: {error}" for error in item_validation_errors])
                        continue

                    # Check line item dates against campaign (warnings only)
                    # Users may have legitimate reasons for dates outside campaign bounds
                    import warnings

                    if processed_item.start_date < self.campaign.start_date:
                        warnings.warn(
                            f"Line item '{processed_item.name}' starts before campaign: "
                            f"{processed_item.start_date} < {self.campaign.start_date}",
                            UserWarning,
                            stacklevel=2
                        )

                    if processed_item.end_date > self.campaign.end_date:
                        warnings.warn(
                            f"Line item '{processed_item.name}' ends after campaign: "
                            f"{processed_item.end_date} > {self.campaign.end_date}",
                            UserWarning,
                            stacklevel=2
                        )

                processed_items.append(processed_item)

            except Exception as e:
                validation_errors.append(f"Item {i}: {str(e)}")

        # Step 3: Check all validation errors before proceeding
        if validation_errors:
            raise ValidationError(f"Batch validation failed: {'; '.join(validation_errors)}")

        # Step 4: Atomic Operations - backup current state before making changes
        original_lineitems = copy.deepcopy(self.lineitems)

        try:
            # Add all items to the line items list
            for processed_item in processed_items:
                self.lineitems.append(processed_item)

            # Step 5: Return Value Logic - return in format matching input type
            if is_single_input:
                return processed_items[0]
            else:
                return processed_items

        except Exception as e:
            # Rollback: restore original state if anything fails during addition
            self.lineitems = original_lineitems
            raise MediaPlanError(f"Failed to create line items: {str(e)}")

    def load_lineitem(self, line_item_id: str) -> Optional[LineItem]:
        """
        Load a line item by ID.

        Args:
            line_item_id: The ID of the line item to retrieve.

        Returns:
            The LineItem instance if found, None otherwise.
        """
        for line_item in self.lineitems:
            if line_item.id == line_item_id:
                return line_item
        return None

    def update_lineitem(self, line_item: LineItem, validate: bool = True) -> LineItem:
        """
        Update an existing line item in the media plan.

        Note: Changes are only made to the in-memory media plan.
        Call mediaplan.save() to persist changes to storage.

        Args:
            line_item: The LineItem instance to update (must have existing ID)
            validate: Whether to validate the line item before updating

        Returns:
            The updated LineItem instance
        """
        # Find the existing line item by ID
        existing_index = None
        for i, existing_item in enumerate(self.lineitems):
            if existing_item.id == line_item.id:
                existing_index = i
                break

        if existing_index is None:
            raise ValueError(f"Line item with ID '{line_item.id}' not found in media plan")

        # Validate if requested
        if validate:
            # Use the new consolidated validate() method
            validation_errors = line_item.validate()
            if validation_errors:
                raise ValidationError(f"Invalid line item: {'; '.join(validation_errors)}")

            # Check line item dates against campaign (warnings only)
            # Users may have legitimate reasons for dates outside campaign bounds
            import warnings

            if line_item.start_date < self.campaign.start_date:
                warnings.warn(
                    f"Line item '{line_item.name}' starts before campaign: "
                    f"{line_item.start_date} < {self.campaign.start_date}",
                    UserWarning,
                    stacklevel=2
                )

            if line_item.end_date > self.campaign.end_date:
                warnings.warn(
                    f"Line item '{line_item.name}' ends after campaign: "
                    f"{line_item.end_date} > {self.campaign.end_date}",
                    UserWarning,
                    stacklevel=2
                )

        # Replace the existing line item (only if validation passed)
        self.lineitems[existing_index] = line_item

        return line_item

    def delete_lineitem(self, line_item_id: str, validate: bool = False) -> bool:
        """
        Delete a line item by ID.

        Args:
            line_item_id: The ID of the line item to remove.
            validate: Whether to validate media plan consistency after deletion (default: True).

        Returns:
            True if the line item was deleted, False if it wasn't found.

        Raises:
            ValidationError: If post-deletion validation fails.
        """
        # Find and remove the line item
        for i, line_item in enumerate(self.lineitems):
            if line_item.id == line_item_id:
                # Store the item for potential rollback
                removed_item = self.lineitems.pop(i)

                # Validate the media plan consistency after deletion if requested
                if validate:
                    try:
                        # Check that total costs still make sense (optional validation)
                        # This is media plan level validation, not line item validation
                        total_cost = sum(item.cost_total for item in self.lineitems)

                        # We could add validation here if needed, but for now
                        # we focus on line item validation only as requested
                        pass

                    except Exception as e:
                        # If validation fails, rollback the deletion
                        self.lineitems.insert(i, removed_item)
                        raise ValidationError(f"Cannot delete line item: validation failed after deletion: {str(e)}")

                return True

        return False

    def copy_lineitem(
        self,
        source_id: str,
        modifications: Optional[Dict[str, Any]] = None,
        new_name: Optional[str] = None,
        validate: bool = True
    ) -> LineItem:
        """
        Copy an existing line item with optional modifications.

        Use Case:
            Duplicate a line item and modify specific fields without manually
            copying all fields. Useful for creating similar campaigns with
            different dates, budgets, or targeting.

        Pattern: Load source → deepcopy → modify → create new

        Args:
            source_id: ID of the line item to copy
            modifications: Dictionary of fields to modify (optional)
            new_name: New name for the copied line item (optional, defaults to "Original Name (Copy)")
            validate: Whether to validate the copied line item (default: True)

        Returns:
            Newly created LineItem (copy)

        Raises:
            ValueError: If source line item not found
            ValidationError: If validation fails

        Example:
            # Simple copy with new name
            copied = plan.copy_lineitem("pli_12345", new_name="Q2 Campaign")

            # Copy with multiple modifications
            copied = plan.copy_lineitem(
                "pli_12345",
                modifications={
                    "name": "Q2 Campaign",
                    "start_date": date(2025, 4, 1),
                    "end_date": date(2025, 6, 30),
                    "cost_total": Decimal("8000")
                }
            )

            # Copy and scale down
            copied = plan.copy_lineitem(
                "pli_12345",
                modifications={
                    "cost_total": source.cost_total * 0.8,
                    "metric_impressions": source.metric_impressions * 0.8
                }
            )
        """
        import copy as copy_module

        # Load source line item
        source_li = self.load_lineitem(source_id)
        if not source_li:
            raise ValueError(f"Source line item '{source_id}' not found in media plan")

        # Deep copy to dictionary
        copied_dict = copy_module.deepcopy(source_li.to_dict())

        # Remove ID (will auto-generate new one)
        copied_dict.pop('id', None)

        # Set name
        if new_name:
            copied_dict['name'] = new_name
        elif modifications and 'name' in modifications:
            # Name will be set via modifications
            pass
        else:
            # Default: append " (Copy)"
            copied_dict['name'] = f"{source_li.name} (Copy)"

        # Apply modifications
        if modifications:
            for key, value in modifications.items():
                # Convert special types to serializable format
                if isinstance(value, (Decimal, date)):
                    copied_dict[key] = str(value) if isinstance(value, date) else float(value)
                else:
                    copied_dict[key] = value

        # Create the copy
        # Note: Date validation warnings may be issued if dates extend beyond campaign
        return self.create_lineitem(copied_dict, validate=validate)

    def archive(self, workspace_manager: 'WorkspaceManager') -> None:
        """
        Archive this media plan by setting is_archived=True and saving to storage.

        Archived media plans are kept in storage but marked as inactive. They can
        still be loaded, exported, and restored later. Archived media plans are
        included in list operations by default.

        Args:
            workspace_manager: The WorkspaceManager instance for saving.

        Raises:
            ValidationError: If the media plan is currently marked as current (is_current=True).
            StorageError: If saving fails.
            WorkspaceInactiveError: If the workspace is inactive.

        Example:
            >>> media_plan.archive(workspace_manager)
            >>> print(media_plan.meta.is_archived)  # True
        """
        # Validation: Cannot archive a current media plan
        if self.meta.is_current is True:
            raise ValidationError(
                f"Cannot archive media plan '{self.meta.id}': it is marked as current (is_current=True). "
                f"Please set is_current=False before archiving."
            )

        # Set archived status
        old_status = self.meta.is_archived
        self.meta.is_archived = True

        try:
            # Save with overwrite=True to preserve ID and sync to database
            saved_path = self.save(
                workspace_manager=workspace_manager,
                overwrite=True,
                include_parquet=True,
                include_database=True
            )

            logger.info(f"Media plan '{self.meta.id}' archived successfully (saved to {saved_path})")

        except Exception as e:
            # Rollback the status change if save failed
            self.meta.is_archived = old_status
            raise StorageError(f"Failed to archive media plan '{self.meta.id}': {str(e)}")

    def restore(self, workspace_manager: 'WorkspaceManager') -> None:
        """
        Restore this media plan by setting is_archived=False and saving to storage.

        This makes the media plan active again after being archived. The media plan
        will be updated in storage and synchronized to the database if enabled.

        Args:
            workspace_manager: The WorkspaceManager instance for saving.

        Raises:
            StorageError: If saving fails.
            WorkspaceInactiveError: If the workspace is inactive.

        Example:
            >>> media_plan.restore(workspace_manager)
            >>> print(media_plan.meta.is_archived)  # False or None
        """
        # Set archived status to False
        old_status = self.meta.is_archived
        self.meta.is_archived = False

        try:
            # Save with overwrite=True to preserve ID and sync to database
            saved_path = self.save(
                workspace_manager=workspace_manager,
                overwrite=True,
                include_parquet=True,
                include_database=True
            )

            logger.info(f"Media plan '{self.meta.id}' restored successfully (saved to {saved_path})")

        except Exception as e:
            # Rollback the status change if save failed
            self.meta.is_archived = old_status
            raise StorageError(f"Failed to restore media plan '{self.meta.id}': {str(e)}")

    def _find_campaign_current_plans(self, workspace_manager: 'WorkspaceManager') -> List['MediaPlan']:
        """
        Find all media plans in the same campaign that are currently set as current.

        OPTIMIZED: Uses workspace.list_mediaplans() with filters instead of scanning all files.

        Args:
            workspace_manager: The WorkspaceManager instance

        Returns:
            List of MediaPlan instances that are current for the same campaign
            (should normally be 0 or 1 plans due to business constraint)
        """
        try:

            logger.debug(f"Querying for current plans in campaign {self.campaign.id}")

            # Query using the optimized list_mediaplans method
            filters = {
                "campaign_id": [self.campaign.id],
                "meta_is_current": [True]
            }
            matching_plan_metadata = workspace_manager.list_mediaplans(
                filters=filters,
                include_stats=False,  # We don't need statistics, just metadata
                return_dataframe=False  # We want list of dicts
            )

            logger.debug(f"Found {len(matching_plan_metadata)} current plan(s) for campaign {self.campaign.id}")

            # Load only the specific MediaPlan objects that match our criteria
            current_plans = []
            for plan_metadata in matching_plan_metadata:
                try:
                    media_plan_id = plan_metadata['meta_id']

                    # Load the full MediaPlan object by ID
                    plan = MediaPlan.load(
                        workspace_manager,
                        media_plan_id=media_plan_id,
                        validate_version=True,
                        auto_migrate=True
                    )
                    current_plans.append(plan)
                    logger.debug(f"Loaded current plan for campaign {self.campaign.id}: {plan.meta.id}")

                except Exception as e:
                    logger.warning(f"Could not load media plan with ID {plan_metadata.get('meta_id', 'unknown')}: {e}")
                    continue

            logger.info(f"Successfully loaded {len(current_plans)} current media plans for campaign {self.campaign.id}")
            return current_plans

        except Exception as e:
            logger.error(f"Failed to find campaign current plans using optimized query: {e}")
            return []

    def set_as_current(self, workspace_manager: 'WorkspaceManager', update_self: bool = True) -> Dict[str, Any]:
        """
        Set this media plan as the current plan for its campaign.

        Automatically sets all other current media plans in the same campaign as non-current.
        This ensures the business rule that only one media plan per campaign can be current.

        Args:
            workspace_manager: The WorkspaceManager instance for saving
            update_self: If True (default), saves this plan with is_current=True.
                        If False, only updates other plans (assumes this plan is already saved).

        Returns:
            Dictionary with operation results:
            - success: bool
            - plan_set_as_current: str (this plan's ID)
            - plans_unset_as_current: List[str] (IDs of plans that were unset)
            - total_affected: int

        Raises:
            ValidationError: If the media plan is archived
            StorageError: If saving fails
            WorkspaceInactiveError: If the workspace is inactive

        Example:
            >>> # Standard usage - updates this plan and others
            >>> result = media_plan.set_as_current(workspace_manager)

            >>> # Coordination only - this plan already saved elsewhere
            >>> result = media_plan.set_as_current(workspace_manager, update_self=False)
        """
        # Check if workspace is active
        workspace_manager.check_workspace_active("set media plan as current")

        # Validation: Cannot set archived plan as current
        if self.meta.is_archived is True:
            raise ValidationError(
                f"Cannot set archived media plan '{self.meta.id}' as current. "
                f"Please restore the media plan first using restore() method."
            )

        # Find all current plans for the same campaign
        current_plans = self._find_campaign_current_plans(workspace_manager)

        # Filter out this plan if it's already in the list (avoid duplicate processing)
        other_current_plans = [plan for plan in current_plans if plan.meta.id != self.meta.id]

        # Prepare result tracking
        result = {
            "success": False,
            "plan_set_as_current": self.meta.id,
            "plans_unset_as_current": [],
            "total_affected": 0
        }

        # Backup original states for rollback
        backup_states = []

        # Backup this plan's state (if we're updating it)
        if update_self:
            original_is_current = self.meta.is_current
            backup_states.append((self, original_is_current))

        # Backup other plans' states
        for plan in other_current_plans:
            backup_states.append((plan, plan.meta.is_current))

        try:
            # Step 1: Set this plan as current (if requested)
            if update_self:
                self.meta.is_current = True

            # Step 2: Set other current plans as non-current
            for plan in other_current_plans:
                plan.meta.is_current = False
                result["plans_unset_as_current"].append(plan.meta.id)

            # Step 3: Save affected plans
            plans_to_save = []
            if update_self:
                plans_to_save.append(self)
            plans_to_save.extend(other_current_plans)

            # Save all affected plans
            for plan in plans_to_save:
                # Prevent recursion by ensuring set_as_current=False in recursive save calls
                plan.save(
                    workspace_manager=workspace_manager,
                    overwrite=True,
                    include_parquet=True,
                    include_database=True,
                    # set_as_current=False  # Prevent recursion
                )

            # Success!
            result["success"] = True
            result["total_affected"] = len(plans_to_save)

            if update_self:
                logger.info(f"Set media plan '{self.meta.id}' as current for campaign '{self.campaign.id}'. "
                            f"Unset {len(other_current_plans)} other plans as current.")
            else:
                logger.info(f"Coordinated current status for campaign '{self.campaign.id}': "
                            f"Plan '{self.meta.id}' is current, unset {len(other_current_plans)} other plans.")

            return result

        except Exception as e:
            # Rollback: restore original states
            logger.error(f"Failed to set media plan as current, rolling back: {e}")

            for plan, original_state in backup_states:
                plan.meta.is_current = original_state

            raise StorageError(f"Failed to set media plan '{self.meta.id}' as current: {str(e)}")

    def calculate_total_cost(self) -> Decimal:
        """
        Calculate the total cost from all line items.

        Returns:
            The total cost.
        """
        return sum(item.cost_total for item in self.lineitems)

    def validate_against_schema(self, validator: Optional[SchemaValidator] = None,
                                version: Optional[str] = None) -> List[str]:
        """
        Validate the media plan against the schema with enhanced v2.0 support.

        Args:
            validator: Schema validator to use. If None, creates a new one.
            version: Schema version to validate against. If None, uses the
                     version from the media plan.

        Returns:
            A list of validation error messages, if any.
        """
        if validator is None:
            validator = SchemaValidator()

        if version is None:
            version = self.meta.schema_version

        return validator.validate(self.to_dict(), version)

    def validate_comprehensive(self, validator: Optional[SchemaValidator] = None,
                               version: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Perform comprehensive validation with categorized results.

        Args:
            validator: Schema validator to use. If None, creates a new one.
            version: Schema version to validate against. If None, uses the
                     version from the media plan.

        Returns:
            Dictionary with categorized validation results including errors, warnings, and info.
        """
        if validator is None:
            validator = SchemaValidator()

        if version is None:
            version = self.meta.schema_version

        return validator.validate_comprehensive(self.to_dict(), version)

    def migrate_to_version(self, migrator: Optional[SchemaMigrator] = None,
                           to_version: Optional[str] = None) -> "MediaPlan":
        """
        Migrate the media plan to a new schema version.

        Args:
            migrator: Schema migrator to use. If None, creates a new one.
            to_version: Target schema version. If None, uses the current version.

        Returns:
            A new MediaPlan instance with the migrated data.

        Raises:
            SchemaError: If migration fails.
        """
        if migrator is None:
            migrator = SchemaMigrator()

        if to_version is None:
            to_version = get_current_version()

        # Get current version
        from_version = self.meta.schema_version

        # If already at target version, return a copy
        if from_version == to_version:
            return self.deep_copy()

        # Migrate the data
        migrated_data = migrator.migrate(self.to_dict(), from_version, to_version)

        # Create new instance
        return MediaPlan.from_dict(migrated_data)

    # NEW v2.0 METHODS: Dictionary management
    # ENHANCED v3.0: Added support for standard_metrics and scoped dimensions

    def get_custom_field_config(self, field_name: str, scope: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a custom field.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1', 'metric_custom1')
            scope: Optional scope for dimension fields ('meta', 'campaign', 'lineitem')

        Returns:
            Dictionary with field configuration or None if not configured.

        Example:
            # Get lineitem dimension config
            config = mp.get_custom_field_config("dim_custom1", scope="lineitem")
            # {'enabled': True, 'caption': 'Brand Category'}

            # Get custom metric config
            config = mp.get_custom_field_config("metric_custom1")
            # {'enabled': True, 'caption': 'Brand Lift %', 'formula_type': None, 'base_metric': None}
        """
        if not self.dictionary:
            return None

        if self.dictionary.is_field_enabled(field_name, scope=scope):
            caption = self.dictionary.get_field_caption(field_name, scope=scope)

            # For custom metrics, include formula info if available
            if field_name in Dictionary.VALID_CUSTOM_METRIC_FIELDS:
                if self.dictionary.custom_metrics and field_name in self.dictionary.custom_metrics:
                    config = self.dictionary.custom_metrics[field_name]
                    return {
                        "enabled": True,
                        "caption": caption,
                        "formula_type": config.formula_type,
                        "base_metric": config.base_metric
                    }

            return {
                "enabled": True,
                "caption": caption
            }
        return None

    def set_custom_field_config(
        self,
        field_name: str,
        enabled: bool,
        caption: Optional[str] = None,
        scope: Optional[str] = "lineitem",
        formula_type: Optional[str] = None,
        base_metric: Optional[str] = None
    ):
        """
        Configure a custom field (dimensions, costs, or custom metrics).

        ENHANCED v3.0: Now supports scoped dimensions and custom metrics with formulas.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1', 'metric_custom1', 'cost_custom1')
            enabled: Whether the field should be enabled
            caption: Display caption for the field (required if enabled)
            scope: Scope for dimension fields ('meta', 'campaign', 'lineitem'). Default: 'lineitem'
            formula_type: Optional formula type for custom metrics (e.g., 'cost_per_unit')
            base_metric: Optional base metric for custom metrics (e.g., 'cost_total')

        Raises:
            ValueError: If field name is invalid or caption is missing for enabled field

        Examples:
            # Enable lineitem dimension (default scope)
            mp.set_custom_field_config("dim_custom1", enabled=True, caption="Brand Category")

            # Enable meta dimension
            mp.set_custom_field_config("dim_custom1", enabled=True, caption="Region", scope="meta")

            # Enable campaign dimension
            mp.set_custom_field_config("dim_custom2", enabled=True, caption="Segment", scope="campaign")

            # Enable custom metric with formula
            mp.set_custom_field_config(
                "metric_custom1",
                enabled=True,
                caption="Custom CPM",
                formula_type="cost_per_unit",
                base_metric="cost_total"
            )

            # Enable custom cost
            mp.set_custom_field_config("cost_custom1", enabled=True, caption="Vendor Fee")
        """
        from mediaplanpy.models.dictionary import CustomFieldConfig, CustomMetricConfig

        # Create dictionary if it doesn't exist
        if not self.dictionary:
            self.dictionary = Dictionary()

        # Determine field type and category
        is_dimension = (field_name in Dictionary.VALID_META_DIMENSION_FIELDS or
                       field_name in Dictionary.VALID_CAMPAIGN_DIMENSION_FIELDS or
                       field_name in Dictionary.VALID_LINEITEM_DIMENSION_FIELDS)
        is_custom_metric = field_name in Dictionary.VALID_CUSTOM_METRIC_FIELDS
        is_cost = field_name in Dictionary.VALID_COST_FIELDS

        if not (is_dimension or is_custom_metric or is_cost):
            raise ValueError(
                f"Invalid custom field name: {field_name}. "
                f"Must be dim_custom1-10, metric_custom1-10, or cost_custom1-10"
            )

        # Handle dimension fields with scope
        if is_dimension:
            if scope == "meta":
                category = "meta_custom_dimensions"
            elif scope == "campaign":
                category = "campaign_custom_dimensions"
            elif scope == "lineitem":
                category = "lineitem_custom_dimensions"
            else:
                raise ValueError(f"Invalid scope: {scope}. Must be 'meta', 'campaign', or 'lineitem'")

            # Create the category dict if it doesn't exist
            category_dict = getattr(self.dictionary, category) or {}

            if enabled:
                if not caption:
                    raise ValueError("Caption is required when enabling a custom field")
                category_dict[field_name] = CustomFieldConfig(status="enabled", caption=caption)
            else:
                category_dict[field_name] = CustomFieldConfig(status="disabled", caption=caption)

            # Update the dictionary
            setattr(self.dictionary, category, category_dict)

        # Handle custom metric fields (may have formula)
        elif is_custom_metric:
            category = "custom_metrics"
            category_dict = getattr(self.dictionary, category) or {}

            if enabled:
                if not caption:
                    raise ValueError("Caption is required when enabling a custom field")
                category_dict[field_name] = CustomMetricConfig(
                    status="enabled",
                    caption=caption,
                    formula_type=formula_type,
                    base_metric=base_metric
                )
            else:
                category_dict[field_name] = CustomMetricConfig(
                    status="disabled",
                    caption=caption,
                    formula_type=formula_type,
                    base_metric=base_metric
                )

            # Update the dictionary
            setattr(self.dictionary, category, category_dict)

        # Handle cost fields
        elif is_cost:
            category = "custom_costs"
            category_dict = getattr(self.dictionary, category) or {}

            if enabled:
                if not caption:
                    raise ValueError("Caption is required when enabling a custom field")
                category_dict[field_name] = CustomFieldConfig(status="enabled", caption=caption)
            else:
                category_dict[field_name] = CustomFieldConfig(status="disabled", caption=caption)

            # Update the dictionary
            setattr(self.dictionary, category, category_dict)

    def set_standard_metric_formula(
        self,
        metric_name: str,
        formula_type: str,
        base_metric: str
    ) -> None:
        """
        Configure a formula for a standard metric.

        NEW v3.0: Allows standard metrics to use formulas for calculation.

        Args:
            metric_name: Standard metric name (e.g., 'metric_impressions', 'metric_clicks')
            formula_type: Type of formula ('cost_per_unit', 'conversion_rate', 'constant', etc.)
            base_metric: Base metric for calculation (e.g., 'cost_total', 'metric_impressions')

        Raises:
            ValueError: If metric_name is not a valid standard metric

        Example:
            # Configure impressions to calculate from cost and CPM
            mp.set_standard_metric_formula(
                "metric_impressions",
                formula_type="cost_per_unit",
                base_metric="cost_total"
            )

            # Configure CTR to calculate from clicks and impressions
            mp.set_standard_metric_formula(
                "metric_clicks",
                formula_type="conversion_rate",
                base_metric="metric_impressions"
            )
        """
        from mediaplanpy.models.dictionary import MetricFormulaConfig

        # Create dictionary if it doesn't exist
        if not self.dictionary:
            self.dictionary = Dictionary()

        # Validate metric name
        if metric_name not in Dictionary.VALID_STANDARD_METRIC_FIELDS:
            raise ValueError(
                f"Invalid standard metric: {metric_name}. "
                f"Must be one of: {', '.join(sorted(Dictionary.VALID_STANDARD_METRIC_FIELDS))}"
            )

        # Create standard_metrics dict if it doesn't exist
        if self.dictionary.standard_metrics is None:
            self.dictionary.standard_metrics = {}

        # Set the formula configuration
        self.dictionary.standard_metrics[metric_name] = MetricFormulaConfig(
            formula_type=formula_type,
            base_metric=base_metric
        )

    def get_standard_metric_formula(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Get formula configuration for a standard metric.

        Args:
            metric_name: Standard metric name (e.g., 'metric_impressions')

        Returns:
            Dictionary with formula configuration or None if not configured

        Example:
            config = mp.get_standard_metric_formula("metric_impressions")
            # {'formula_type': 'cost_per_unit', 'base_metric': 'cost_total'}
        """
        if not self.dictionary or not self.dictionary.standard_metrics:
            return None

        config = self.dictionary.standard_metrics.get(metric_name)
        if config:
            return {
                "formula_type": config.formula_type,
                "base_metric": config.base_metric
            }
        return None

    def remove_standard_metric_formula(self, metric_name: str) -> bool:
        """
        Remove formula configuration for a standard metric.

        Args:
            metric_name: Standard metric name

        Returns:
            True if formula was removed, False if it didn't exist

        Example:
            removed = mp.remove_standard_metric_formula("metric_impressions")
        """
        if not self.dictionary or not self.dictionary.standard_metrics:
            return False

        if metric_name in self.dictionary.standard_metrics:
            del self.dictionary.standard_metrics[metric_name]
            return True
        return False

    def get_enabled_custom_fields(self, scope: Optional[str] = None) -> Dict[str, str]:
        """
        Get all enabled custom fields and their captions.

        Args:
            scope: Optional scope filter ('meta', 'campaign', 'lineitem', 'all')

        Returns:
            Dictionary mapping field names to captions for all enabled fields.

        Example:
            # Get all enabled fields
            fields = mp.get_enabled_custom_fields()

            # Get only lineitem fields
            fields = mp.get_enabled_custom_fields(scope="lineitem")
        """
        if not self.dictionary:
            return {}
        return self.dictionary.get_enabled_fields(scope=scope)

    # Legacy method support - keeping old methods for any internal usage
    def add_lineitem(self, line_item: Union[LineItem, Dict[str, Any]], **kwargs) -> LineItem:
        """
        Legacy method - use create_lineitem() instead.

        This method is kept for internal compatibility and calls the new create_lineitem() method.
        """
        return self.create_lineitem(line_item, **kwargs)

    def get_lineitem(self, line_item_id: str) -> Optional[LineItem]:
        """
        Legacy method - use load_lineitem() instead.

        This method is kept for internal compatibility and calls the new load_lineitem() method.
        """
        return self.load_lineitem(line_item_id)

    def remove_lineitem(self, line_item_id: str) -> bool:
        """
        Legacy method - use delete_lineitem() instead.

        This method is kept for internal compatibility and calls the new delete_lineitem() method.
        """
        return self.delete_lineitem(line_item_id)

    @classmethod
    def create(cls,
               campaign_name: str,
               campaign_start_date: Union[str, date],
               campaign_end_date: Union[str, date],
               workspace_manager: Optional['WorkspaceManager'] = None,
               schema_version: Optional[str] = None,
               # Dual parameter support for backwards compatibility
               campaign_budget: Optional[Union[str, int, float, Decimal]] = None,
               campaign_budget_total: Optional[Union[str, int, float, Decimal]] = None,
               created_by: Optional[str] = None,
               created_by_name: Optional[str] = None,
               campaign_objective: Optional[str] = None,
               **kwargs) -> "MediaPlan":
        """
        Create a new media plan with schema-aligned required fields.

        This method dynamically routes parameters to the appropriate model objects
        based on their field definitions, ensuring proper JSON structure.

        NEW v3.0:
        - Signature aligned with schema v3.0 requirements
        - Supports dual parameter names for backwards compatibility:
          * campaign_budget (v2.0) OR campaign_budget_total (v3.0)
          * created_by (v2.0) OR created_by_name (v3.0)
        - Supports prefixed parameters for disambiguation of fields that exist
          at multiple levels (e.g., dim_custom1 exists in Meta, Campaign, and LineItem):
          * Use meta_* prefix for Meta fields (e.g., meta_dim_custom1, meta_custom_properties)
          * Use campaign_* prefix for Campaign fields (e.g., campaign_dim_custom1, campaign_custom_properties)
        - Unprefixed fields are routed automatically based on field definitions

        Args:
            campaign_name: Name of the campaign (required by schema)
            campaign_start_date: Start date (required by schema) - string YYYY-MM-DD or date object
            campaign_end_date: End date (required by schema) - string YYYY-MM-DD or date object
            workspace_manager: Optional WorkspaceManager for workspace status checking
            schema_version: Version of the schema to use, defaults to current version (v3.0)
            campaign_budget: Total budget amount (v2.0 parameter name, prefer campaign_budget_total)
            campaign_budget_total: Total budget amount (v3.0 parameter name, schema-correct)
            created_by: Email or name of the creator (v2.0 parameter name, prefer created_by_name)
            created_by_name: Name of the creator (v3.0 parameter name, schema-correct)
            campaign_objective: Objective of the campaign (optional)
            **kwargs: Additional fields - automatically routed to Campaign, Meta, or MediaPlan

                      Common v3.0 kwargs examples:
                      - target_audiences: List[Dict] or List[TargetAudience] (Campaign)
                      - target_locations: List[Dict] or List[TargetLocation] (Campaign)
                      - kpi_name1, kpi_value1: KPI tracking (Campaign)
                      - meta_dim_custom1: Custom dimension for Meta (use meta_ prefix)
                      - campaign_dim_custom1: Custom dimension for Campaign (use campaign_ prefix)
                      - meta_custom_properties: Dict (use meta_ prefix)
                      - campaign_custom_properties: Dict (use campaign_ prefix)

        Returns:
            A new MediaPlan instance.

        Raises:
            ValidationError: If the provided parameters fail validation.
            WorkspaceInactiveError: If workspace is inactive.
            ValueError: If required parameters are missing.

        Example:
            plan = MediaPlan.create(
                campaign_name="Q1 Campaign",
                campaign_start_date="2025-01-01",
                campaign_end_date="2025-03-31",
                campaign_budget_total=100000,  # or campaign_budget=100000
                created_by_name="John Doe",    # or created_by="john@example.com"
                campaign_objective="awareness",
                target_audiences=[{"name": "Young Adults", "demo_age_start": 18, "demo_age_end": 34}],
                kpi_name1="CTR",
                kpi_value1=2.5,
                meta_dim_custom1="Region: North America",
                campaign_dim_custom1="Segment: Digital"
            )
        """
        # === DUAL PARAMETER NAME HANDLING ===
        # Handle campaign budget (prefer schema-correct name)
        if campaign_budget_total is None and campaign_budget is not None:
            campaign_budget_total = campaign_budget
        elif campaign_budget_total is None:
            raise ValueError(
                "campaign_budget_total is required (or use campaign_budget for backwards compatibility). "
                "This is required by the v3.0 schema."
            )

        # Handle creator name (prefer schema-correct name)
        if created_by_name is None and created_by is not None:
            created_by_name = created_by
        elif created_by_name is None:
            raise ValueError(
                "created_by_name is required (or use created_by for backwards compatibility). "
                "This is required by the v3.0 schema."
            )

        # Check workspace status if workspace_manager is provided
        if workspace_manager is not None:
            workspace_manager.check_workspace_active("media plan creation")

        # Convert date strings to date objects if necessary
        if isinstance(campaign_start_date, str):
            campaign_start_date = date.fromisoformat(campaign_start_date)
        if isinstance(campaign_end_date, str):
            campaign_end_date = date.fromisoformat(campaign_end_date)

        # Convert budget to Decimal if necessary
        if isinstance(campaign_budget_total, (str, int, float)):
            campaign_budget_total = Decimal(str(campaign_budget_total))

        # Use current schema version if not specified
        if schema_version is None:
            from mediaplanpy import __schema_version__
            schema_version = f"v{__schema_version__}"

        # Generate IDs if not provided
        campaign_id = kwargs.pop("campaign_id", f"campaign_{uuid.uuid4().hex[:8]}")
        mediaplan_id = kwargs.pop("mediaplan_id", f"mediaplan_{uuid.uuid4().hex[:8]}")

        # === DYNAMIC FIELD ROUTING ===
        # Get the field definitions for each model to route kwargs appropriately
        campaign_fields, meta_fields, mediaplan_fields = cls._route_creation_fields(kwargs, schema_version)

        # === CAMPAIGN CREATION ===
        # Build campaign with core required fields plus dynamic fields
        campaign_data = {
            "id": campaign_id,
            "name": campaign_name,
            "start_date": campaign_start_date,
            "end_date": campaign_end_date,
            "budget_total": campaign_budget_total,
            **campaign_fields  # Dynamic campaign fields from kwargs
        }

        # Add objective if provided (optional in v3.0)
        if campaign_objective is not None:
            campaign_data["objective"] = campaign_objective

        try:
            campaign = Campaign.from_dict(campaign_data)
        except Exception as e:
            raise ValidationError(f"Failed to create campaign: {str(e)}")

        # === META CREATION ===
        # created_by_name already validated and resolved from parameters above
        # Check if it was also provided in kwargs (allow kwargs to override)
        if "created_by_name" in meta_fields:
            created_by_name = meta_fields.pop("created_by_name")

        # Get plan name from kwargs or use campaign name as fallback
        media_plan_name = mediaplan_fields.pop("media_plan_name", campaign_name)  # Use campaign name as fallback

        meta_data = {
            "id": mediaplan_id,
            "schema_version": schema_version,
            "created_by_name": created_by_name,  # Required in v2.0
            "created_at": datetime.now(),
            "name": media_plan_name,
            **meta_fields  # Dynamic meta fields from kwargs
        }

        try:
            meta = Meta.from_dict(meta_data)
        except Exception as e:
            raise ValidationError(f"Failed to create meta: {str(e)}")

        # === LINE ITEMS CREATION ===
        lineitems_data = mediaplan_fields.pop("lineitems", [])
        lineitems = []
        for i, item_data in enumerate(lineitems_data):
            try:
                if isinstance(item_data, dict):
                    # For v1.0 compatibility, ensure budget is renamed to cost_total
                    if "budget" in item_data and "cost_total" not in item_data:
                        item_data["cost_total"] = item_data.pop("budget")

                    # Auto-generate ID if not provided (consistent with create_lineitem())
                    if 'id' not in item_data or not item_data['id']:
                        item_data['id'] = f"pli_{uuid.uuid4().hex[:8]}"

                    # Inherit dates from campaign if not provided (consistent with create_lineitem())
                    if 'start_date' not in item_data or not item_data['start_date']:
                        item_data['start_date'] = campaign_start_date
                    if 'end_date' not in item_data or not item_data['end_date']:
                        item_data['end_date'] = campaign_end_date

                    # Set default cost_total if not provided (consistent with create_lineitem())
                    if 'cost_total' not in item_data or item_data['cost_total'] is None:
                        item_data['cost_total'] = Decimal('0')

                    # Ensure line item has a name
                    if "name" not in item_data:
                        item_data["name"] = item_data.get("id", f"Item {i + 1}")

                    lineitems.append(LineItem.from_dict(item_data))
                else:
                    lineitems.append(item_data)
            except ValidationError as e:
                raise ValidationError(f"Invalid line item {i}: {str(e)}")

        # === DICTIONARY CREATION ===
        dictionary_data = mediaplan_fields.pop("dictionary", None)
        dictionary = None
        if dictionary_data:
            try:
                if isinstance(dictionary_data, dict):
                    dictionary = Dictionary.from_dict(dictionary_data)
                else:
                    dictionary = dictionary_data
            except Exception as e:
                raise ValidationError(f"Failed to create dictionary: {str(e)}")

        # === MEDIA PLAN CREATION ===
        # Create the media plan with remaining mediaplan-specific fields
        try:
            media_plan = cls(
                meta=meta,
                campaign=campaign,
                lineitems=lineitems,
                dictionary=dictionary,
                **mediaplan_fields  # Any remaining MediaPlan-specific fields
            )

            # Validate the complete media plan
            media_plan.assert_valid()

            return media_plan

        except Exception as e:
            raise ValidationError(f"Failed to create media plan: {str(e)}")

    @classmethod
    def _route_creation_fields(cls, kwargs: Dict[str, Any], schema_version: str) -> tuple[
        Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Dynamically route kwargs to appropriate model objects based on their field definitions.

        This method inspects the actual model field definitions to determine where
        each parameter should go, making it schema-aware and maintainable.

        NEW v3.0: Supports prefixed parameters for disambiguation:
        - meta_* parameters (e.g., meta_dim_custom1) → Meta fields
        - campaign_* parameters (e.g., campaign_dim_custom1) → Campaign fields

        Args:
            kwargs: All the extra parameters passed to create()
            schema_version: Schema version being used

        Returns:
            Tuple of (campaign_fields, meta_fields, mediaplan_fields)
        """
        # Get field definitions from the models
        campaign_field_names = cls._get_model_field_names(Campaign)
        meta_field_names = cls._get_model_field_names(Meta)

        # MediaPlan fields are the ones defined directly on MediaPlan (excluding nested objects)
        mediaplan_field_names = cls._get_model_field_names(cls, exclude_nested=['meta', 'campaign', 'lineitems',
                                                                                'dictionary'])

        # Special handling for certain fields that might be ambiguous
        # These fields should always go to specific models regardless of field name overlaps
        force_campaign_fields = {
            # v2.0 campaign fields
            'budget_currency', 'agency_id', 'agency_name', 'advertiser_id', 'advertiser_name',
            'product_id', 'product_name', 'product_description', 'campaign_type_id', 'campaign_type_name',
            'workflow_status_id', 'workflow_status_name',
            # v2.0 deprecated audience fields (still supported for backward compatibility)
            'audience_name', 'audience_age_start', 'audience_age_end', 'audience_gender', 'audience_interests',
            # v2.0 deprecated location fields (still supported for backward compatibility)
            'location_type', 'locations',
            # NEW v3.0 campaign fields
            'target_audiences', 'target_locations',
            'kpi_name1', 'kpi_value1', 'kpi_name2', 'kpi_value2', 'kpi_name3', 'kpi_value3',
            'kpi_name4', 'kpi_value4', 'kpi_name5', 'kpi_value5'
        }

        force_meta_fields = {
            # v2.0 meta fields
            'created_by_name', 'created_by_id', 'is_current', 'is_archived', 'parent_id', 'comments'
        }

        force_mediaplan_fields = {
            'media_plan_name', 'lineitems', 'dictionary'
        }

        # Route the fields
        campaign_fields = {}
        meta_fields = {}
        mediaplan_fields = {}

        for key, value in kwargs.items():
            # NEW v3.0: Handle prefixed parameters for disambiguation
            if key.startswith('meta_'):
                # Strip prefix and route to meta
                actual_field_name = key[5:]  # Remove 'meta_' prefix
                if actual_field_name in meta_field_names:
                    meta_fields[actual_field_name] = value
                else:
                    logger.warning(f"Unknown meta field '{actual_field_name}' from parameter '{key}'")
                    meta_fields[actual_field_name] = value  # Add anyway for flexibility
            elif key.startswith('campaign_'):
                # Strip prefix and route to campaign
                actual_field_name = key[9:]  # Remove 'campaign_' prefix
                if actual_field_name in campaign_field_names:
                    campaign_fields[actual_field_name] = value
                else:
                    logger.warning(f"Unknown campaign field '{actual_field_name}' from parameter '{key}'")
                    campaign_fields[actual_field_name] = value  # Add anyway for flexibility
            # Standard routing logic (without prefix)
            elif key in force_campaign_fields or key in campaign_field_names:
                campaign_fields[key] = value
            elif key in force_meta_fields or key in meta_field_names:
                meta_fields[key] = value
            elif key in force_mediaplan_fields or key in mediaplan_field_names:
                mediaplan_fields[key] = value
            else:
                # Unknown field - log warning and put in mediaplan fields as fallback
                logger.warning(f"Unknown field '{key}' in MediaPlan.create(), adding to MediaPlan level")
                mediaplan_fields[key] = value

        return campaign_fields, meta_fields, mediaplan_fields

    @classmethod
    def _get_model_field_names(cls, model_class: type, exclude_nested: Optional[List[str]] = None) -> Set[str]:
        """
        Get the field names defined on a Pydantic model.

        Args:
            model_class: The Pydantic model class to inspect
            exclude_nested: List of field names to exclude (for nested objects)

        Returns:
            Set of field names defined on the model
        """
        exclude_nested = exclude_nested or []

        try:
            # For Pydantic v2
            if hasattr(model_class, 'model_fields'):
                field_names = set(model_class.model_fields.keys())
            # For Pydantic v1 fallback
            elif hasattr(model_class, '__fields__'):
                field_names = set(model_class.__fields__.keys())
            else:
                # Manual fallback - inspect the class annotations
                field_names = set(getattr(model_class, '__annotations__', {}).keys())

            # Remove excluded nested fields
            return field_names - set(exclude_nested)

        except Exception as e:
            logger.warning(f"Could not inspect fields for {model_class.__name__}: {e}")
            return set()

    @classmethod
    def _get_campaign_fields_from_schema(cls, schema_version: str) -> Set[str]:
        """
        Get campaign field names from the JSON schema (alternative approach).

        This method can be used as a fallback or primary method if you prefer
        to use the JSON schema as the source of truth.

        Args:
            schema_version: Schema version to use

        Returns:
            Set of campaign field names from the schema
        """
        try:
            from mediaplanpy.schema import SchemaRegistry

            registry = SchemaRegistry()
            schema = registry.get_schema(schema_version)

            # Navigate to campaign properties in the schema
            campaign_properties = schema.get('properties', {}).get('campaign', {}).get('properties', {})
            return set(campaign_properties.keys())

        except Exception as e:
            logger.warning(f"Could not load campaign fields from schema {schema_version}: {e}")
            return set()

    @classmethod
    def _get_meta_fields_from_schema(cls, schema_version: str) -> Set[str]:
        """
        Get meta field names from the JSON schema (alternative approach).

        Args:
            schema_version: Schema version to use

        Returns:
            Set of meta field names from the schema
        """
        try:
            from mediaplanpy.schema import SchemaRegistry

            registry = SchemaRegistry()
            schema = registry.get_schema(schema_version)

            # Navigate to meta properties in the schema
            meta_properties = schema.get('properties', {}).get('meta', {}).get('properties', {})
            return set(meta_properties.keys())

        except Exception as e:
            logger.warning(f"Could not load meta fields from schema {schema_version}: {e}")
            return set()


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaPlan":
        """
        Create a MediaPlan instance from a dictionary with version handling.

        Args:
            data: Dictionary containing the media plan data.

        Returns:
            A new MediaPlan instance.

        Raises:
            ValidationError: If the data fails validation.
            SchemaVersionError: If the data uses an incompatible schema version.
        """
        try:
            # Check and handle schema version compatibility
            cls.check_schema_version(data)

            # Create instance using Pydantic
            media_plan = cls.model_validate(data)

            return media_plan

        except SchemaVersionError:
            # Re-raise schema version errors as-is
            raise
        except Exception as e:
            raise ValidationError(f"Validation failed for {cls.__name__}: {str(e)}")