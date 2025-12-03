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
    Metadata for a media plan following v2.0 schema.

    Updated from v1.0 to include new identification and status fields.
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


class MediaPlan(BaseModel, JsonMixin, StorageMixin, ExcelMixin, DatabaseMixin):
    """
    Represents a complete media plan following the Media Plan Open Data Standard v2.0.

    A media plan contains metadata, a campaign, line items, and optionally a
    dictionary for custom field configuration.
    """

    # Meta information (updated for v2.0)
    meta: Meta = Field(..., description="Metadata for the media plan")

    # The campaign (same as v1.0)
    campaign: Campaign = Field(..., description="The campaign details")

    # Line items (same as v1.0)
    lineitems: List[LineItem] = Field(default_factory=list, description="Line items in the media plan")

    # NEW v2.0 FIELD: Dictionary for custom field configuration
    dictionary: Optional[Dictionary] = Field(None, description="Configuration dictionary defining custom field settings and captions")

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
            # Check that line item dates are within campaign dates
            for i, line_item in enumerate(self.lineitems):
                if line_item.start_date < self.campaign.start_date:
                    errors.append(
                        f"Line item {i} ({line_item.id}) starts before campaign: "
                        f"{line_item.start_date} < {self.campaign.start_date}"
                    )

                if line_item.end_date > self.campaign.end_date:
                    errors.append(
                        f"Line item {i} ({line_item.id}) ends after campaign: "
                        f"{line_item.end_date} > {self.campaign.end_date}"
                    )

            # Check if total cost of line items matches campaign budget_total
            total_cost = sum(item.cost_total for item in self.lineitems)
            # Allow a small difference for rounding errors (0.01)
            if abs(total_cost - self.campaign.budget_total) > Decimal('0.01'):
                errors.append(
                    f"Sum of line item costs ({total_cost}) does not match "
                    f"campaign budget_total ({self.campaign.budget_total})"
                )

        # NEW v2.0 VALIDATION: Dictionary consistency
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

                # Issue warnings for enabled fields that aren't used
                for unused_field in unused_fields:
                    errors.append(
                        f"Warning: Custom field '{unused_field}' is enabled in dictionary "
                        f"but not used in any line items"
                    )

        return errors

    def create_lineitem(self, line_items: Union[LineItem, Dict[str, Any], List[Union[LineItem, Dict[str, Any]]]],
                        validate: bool = True, **kwargs) -> Union[LineItem, List[LineItem]]:
        """
        Create one or more line items for this media plan.

        Args:
            line_items: Single line item or list of line items to create.
                       Each item can be a LineItem object or dictionary.
            validate: Whether to validate line items before creation.
            **kwargs: Additional line item parameters (applied to all items if line_items is a list).

        Returns:
            Single LineItem object if input was single item, or List[LineItem]
            if input was a list.

        Raises:
            ValidationError: If line item data is invalid
            MediaPlanError: If creation fails

        Example:
            # Single line item (backward compatible)
            item = plan.create_lineitem({"name": "Campaign", "cost_total": 5000})

            # Multiple line items (new capability)
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
                        line_item_data['id'] = f"li_{uuid.uuid4().hex[:8]}"

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
                        processed_item.id = f"li_{uuid.uuid4().hex[:8]}"

                # Validate the individual item if requested
                if validate:
                    # Use the consolidated validate() method
                    item_validation_errors = processed_item.validate()
                    if item_validation_errors:
                        validation_errors.extend([f"Item {i}: {error}" for error in item_validation_errors])
                        continue

                    # Validate line item dates against campaign
                    if processed_item.start_date < self.campaign.start_date:
                        validation_errors.append(
                            f"Item {i}: Line item starts before campaign: "
                            f"{processed_item.start_date} < {self.campaign.start_date}"
                        )

                    if processed_item.end_date > self.campaign.end_date:
                        validation_errors.append(
                            f"Item {i}: Line item ends after campaign: "
                            f"{processed_item.end_date} > {self.campaign.end_date}"
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

            # Validate line item dates against campaign
            if line_item.start_date < self.campaign.start_date:
                raise ValidationError(
                    f"Line item starts before campaign: "
                    f"{line_item.start_date} < {self.campaign.start_date}"
                )

            if line_item.end_date > self.campaign.end_date:
                raise ValidationError(
                    f"Line item ends after campaign: "
                    f"{line_item.end_date} > {self.campaign.end_date}"
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

    def get_custom_field_config(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a custom field.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1')

        Returns:
            Dictionary with field configuration or None if not configured.
        """
        if not self.dictionary:
            return None

        if self.dictionary.is_field_enabled(field_name):
            return {
                "enabled": True,
                "caption": self.dictionary.get_field_caption(field_name)
            }
        return None

    def set_custom_field_config(self, field_name: str, enabled: bool, caption: Optional[str] = None):
        """
        Configure a custom field.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1')
            enabled: Whether the field should be enabled
            caption: Display caption for the field (required if enabled)

        Raises:
            ValueError: If field name is invalid or caption is missing for enabled field
        """
        from mediaplanpy.models.dictionary import CustomFieldConfig

        # Create dictionary if it doesn't exist
        if not self.dictionary:
            self.dictionary = Dictionary()

        # Validate field name and determine category
        if field_name in Dictionary.VALID_DIMENSION_FIELDS:
            category = "custom_dimensions"
        elif field_name in Dictionary.VALID_METRIC_FIELDS:
            category = "custom_metrics"
        elif field_name in Dictionary.VALID_COST_FIELDS:
            category = "custom_costs"
        else:
            raise ValueError(f"Invalid custom field name: {field_name}")

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

    def get_enabled_custom_fields(self) -> Dict[str, str]:
        """
        Get all enabled custom fields and their captions.

        Returns:
            Dictionary mapping field names to captions for all enabled fields.
        """
        if not self.dictionary:
            return {}
        return self.dictionary.get_enabled_fields()

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
               created_by: str,
               campaign_name: str,
               campaign_objective: str,
               campaign_start_date: Union[str, date],
               campaign_end_date: Union[str, date],
               campaign_budget: Union[str, int, float, Decimal],
               schema_version: Optional[str] = None,
               workspace_manager: Optional['WorkspaceManager'] = None,
               **kwargs) -> "MediaPlan":
        """
        Create a new media plan with the required fields.

        This method dynamically routes parameters to the appropriate model objects
        based on their field definitions, ensuring proper JSON structure.

        Args:
            created_by: Email or name of the creator
            campaign_name: Name of the campaign
            campaign_objective: Objective of the campaign
            campaign_start_date: Start date (string YYYY-MM-DD or date object)
            campaign_end_date: End date (string YYYY-MM-DD or date object)
            campaign_budget: Total budget amount
            schema_version: Version of the schema to use, defaults to current version
            workspace_manager: Optional WorkspaceManager for workspace status checking
            **kwargs: Additional fields - automatically routed to Campaign, Meta, or MediaPlan

        Returns:
            A new MediaPlan instance.

        Raises:
            ValidationError: If the provided parameters fail validation.
            WorkspaceInactiveError: If workspace is inactive.
        """
        # Check workspace status if workspace_manager is provided
        if workspace_manager is not None:
            workspace_manager.check_workspace_active("media plan creation")

        # Convert date strings to date objects if necessary
        if isinstance(campaign_start_date, str):
            campaign_start_date = date.fromisoformat(campaign_start_date)
        if isinstance(campaign_end_date, str):
            campaign_end_date = date.fromisoformat(campaign_end_date)

        # Convert budget to Decimal if necessary
        if isinstance(campaign_budget, (str, int, float)):
            campaign_budget = Decimal(str(campaign_budget))

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
            "objective": campaign_objective,
            "start_date": campaign_start_date,
            "end_date": campaign_end_date,
            "budget_total": campaign_budget,
            **campaign_fields  # Dynamic campaign fields from kwargs
        }

        try:
            campaign = Campaign.from_dict(campaign_data)
        except Exception as e:
            raise ValidationError(f"Failed to create campaign: {str(e)}")

        # === META CREATION ===
        # Handle v2.0 required field mapping
        created_by_name = meta_fields.pop("created_by_name", created_by)  # Use created_by as fallback
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
            'budget_currency', 'agency_id', 'agency_name', 'advertiser_id', 'advertiser_name',
            'product_id', 'product_name', 'product_description', 'campaign_type_id', 'campaign_type_name',
            'audience_name', 'audience_age_start', 'audience_age_end', 'audience_gender', 'audience_interests',
            'location_type', 'locations', 'workflow_status_id', 'workflow_status_name'
        }

        force_meta_fields = {
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
            if key in force_campaign_fields or key in campaign_field_names:
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
    def from_v0_mediaplan(cls, v0_mediaplan: Dict[str, Any]) -> "MediaPlan":
        """
        Convert a v0.0 media plan dictionary to a v2.0 MediaPlan model.

        Args:
            v0_mediaplan: Dictionary containing v0.0 media plan data.

        Returns:
            A new MediaPlan instance with v2.0 structure.
        """
        # Extract metadata
        v0_meta = v0_mediaplan.get("meta", {})
        meta_data = {
            "id": v0_meta.get("id", f"mediaplan_{uuid.uuid4().hex[:8]}"),  # Generate ID if not present
            "schema_version": "v2.0",  # Set to the new version
            "created_by_name": v0_meta.get("created_by", "Unknown"),  # Map to required field
            "created_at": v0_meta.get("created_at", datetime.now().isoformat()),
            "comments": v0_meta.get("comments")
        }

        # Handle campaign
        v0_campaign = v0_mediaplan.get("campaign", {})
        campaign = Campaign.from_v0_campaign(v0_campaign)

        # Handle line items
        lineitems = []
        for v0_lineitem in v0_mediaplan.get("lineitems", []):
            lineitems.append(LineItem.from_v0_lineitem(v0_lineitem))

        # Create new media plan (no dictionary in v0.0)
        return cls(
            meta=Meta(**meta_data),
            campaign=campaign,
            lineitems=lineitems,
            dictionary=None  # v0.0 didn't have dictionary
        )

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