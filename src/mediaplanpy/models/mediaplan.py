"""
Media Plan model for mediaplanpy.

This module provides the MediaPlan model class representing a complete
media plan with campaigns and line items, following the Media Plan Open
Data Standard v1.0.0.
"""

import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Union, ClassVar

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel
from mediaplanpy.models.campaign import Campaign, Budget, TargetAudience
from mediaplanpy.models.lineitem import LineItem
from mediaplanpy.exceptions import ValidationError, SchemaVersionError, SchemaError, MediaPlanError
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
    Metadata for a media plan.
    """
    id: str = Field(..., description="Unique identifier for the media plan")
    schema_version: str = Field(..., description="Version of the schema being used")
    created_by: str = Field(..., description="Creator of the media plan")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    name: Optional[str] = Field(None, description="Name of the media plan")
    comments: Optional[str] = Field(None, description="Comments about the media plan")


class MediaPlan(BaseModel):
    """
    Represents a complete media plan following the Media Plan Open Data Standard v1.0.0.

    A media plan contains metadata, a campaign, and a list of line items.
    """

    # Meta information
    meta: Meta = Field(..., description="Metadata for the media plan")

    # The campaign
    campaign: Campaign = Field(..., description="The campaign details")

    # Line items
    lineitems: List[LineItem] = Field(default_factory=list, description="Line items in the media plan")

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
        Validate the media plan against the schema.

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

        Args:
            created_by: Email or name of the creator
            campaign_name: Name of the campaign
            campaign_objective: Objective of the campaign
            campaign_start_date: Start date (string YYYY-MM-DD or date object)
            campaign_end_date: End date (string YYYY-MM-DD or date object)
            campaign_budget: Total budget amount
            schema_version: Version of the schema to use, defaults to current version
            workspace_manager: Optional WorkspaceManager for workspace status checking
            **kwargs: Additional fields to set on the media plan

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
            schema_version = cls.SCHEMA_VERSION

        # Generate a campaign ID if not provided
        campaign_id = kwargs.pop("campaign_id", f"campaign_{uuid.uuid4().hex[:8]}")

        # Generate a media plan ID if not provided
        mediaplan_id = kwargs.pop("mediaplan_id", f"mediaplan_{uuid.uuid4().hex[:8]}")

        # Handle audience-related parameters for v1.0.0
        audience_fields = {}
        target_audience = kwargs.pop("target_audience", None)

        if target_audience:
            # Extract audience fields from target_audience
            if isinstance(target_audience, dict):
                # Extract age range
                age_range = target_audience.get("age_range")
                if age_range and "-" in age_range:
                    try:
                        start, end = age_range.split("-")
                        audience_fields["audience_age_start"] = int(start.strip())
                        audience_fields["audience_age_end"] = int(end.strip())
                    except (ValueError, TypeError):
                        pass

                # Extract other audience fields
                if "location" in target_audience:
                    audience_fields["location_type"] = "Country"
                    audience_fields["locations"] = [target_audience["location"]]

                if "interests" in target_audience:
                    audience_fields["audience_interests"] = target_audience["interests"]

        # Create the campaign
        campaign = Campaign(
            id=campaign_id,
            name=campaign_name,
            objective=campaign_objective,
            start_date=campaign_start_date,
            end_date=campaign_end_date,
            budget_total=campaign_budget,
            **audience_fields
        )

        # Extract media plan name if provided
        media_plan_name = kwargs.pop("media_plan_name", campaign_name)

        # Create meta information
        meta = Meta(
            id=mediaplan_id,
            schema_version=schema_version,
            created_by=created_by,
            created_at=datetime.now(),
            name=media_plan_name,
            comments=kwargs.pop("comments", None)
        )

        # Extract line items if provided
        lineitems_data = kwargs.pop("lineitems", [])
        lineitems = []
        for item_data in lineitems_data:
            try:
                if isinstance(item_data, dict):
                    # For v1.0.0, ensure budget is renamed to cost_total
                    if "budget" in item_data and "cost_total" not in item_data:
                        item_data["cost_total"] = item_data.pop("budget")

                    # Ensure line item has a name
                    if "name" not in item_data:
                        item_data["name"] = item_data.get("id", f"Item {len(lineitems) + 1}")

                    lineitems.append(LineItem.from_dict(item_data))
                else:
                    lineitems.append(item_data)
            except ValidationError as e:
                raise ValidationError(f"Invalid line item in lineitems: {str(e)}")

        # Create the media plan
        media_plan = cls(
            meta=meta,
            campaign=campaign,
            lineitems=lineitems,
            **kwargs
        )

        # Validate the complete media plan
        media_plan.assert_valid()

        return media_plan

    @classmethod
    def from_v0_mediaplan(cls, v0_mediaplan: Dict[str, Any]) -> "MediaPlan":
        """
        Convert a v0.0.0 media plan dictionary to a v1.0.0 MediaPlan model.

        Args:
            v0_mediaplan: Dictionary containing v0.0.0 media plan data.

        Returns:
            A new MediaPlan instance with v1.0.0 structure.
        """
        # Extract metadata
        v0_meta = v0_mediaplan.get("meta", {})
        meta_data = {
            "id": v0_meta.get("id", f"mediaplan_{uuid.uuid4().hex[:8]}"),  # Generate ID if not present
            "schema_version": "v1.0.0",  # Set to the new version
            "created_by": v0_meta.get("created_by", ""),
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

        # Create new media plan
        return cls(
            meta=Meta(**meta_data),
            campaign=campaign,
            lineitems=lineitems
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
        return cls.model_validate(data)

    except SchemaVersionError:
        # Re-raise schema version errors as-is
        raise
    except Exception as e:
        raise ValidationError(f"Validation failed for {cls.__name__}: {str(e)}")