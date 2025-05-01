"""
Media Plan model for mediaplanpy.

This module provides the MediaPlan model class representing a complete
media plan with campaigns and line items, following the Media Plan Open
Data Standard.
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
from mediaplanpy.exceptions import ValidationError, SchemaVersionError, SchemaError
from mediaplanpy.schema import get_current_version, SchemaValidator, SchemaMigrator


class Meta(BaseModel):
    """
    Metadata for a media plan.
    """
    schema_version: str = Field(..., description="Version of the schema being used")
    created_by: str = Field(..., description="Creator of the media plan")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    comments: Optional[str] = Field(None, description="Comments about the media plan")


class MediaPlan(BaseModel):
    """
    Represents a complete media plan following the Media Plan Open Data Standard.

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
        Check that the schema version in the data is supported.

        Args:
            data: The data to check.

        Raises:
            SchemaVersionError: If the schema version is not supported.
        """
        version = data.get("meta", {}).get("schema_version")
        if not version:
            # If no version specified, assume it's compatible
            return

        # Check if version matches the expected version
        if version != cls.SCHEMA_VERSION:
            raise SchemaVersionError(
                f"Schema version mismatch: got {version}, expected {cls.SCHEMA_VERSION}"
            )

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

        return errors

    def add_lineitem(self, line_item: Union[LineItem, Dict[str, Any]]) -> LineItem:
        """
        Add a line item to the media plan.

        Args:
            line_item: The line item to add, either as a LineItem instance
                      or a dictionary of parameters.

        Returns:
            The added LineItem instance.

        Raises:
            ValidationError: If the line item fails validation.
        """
        # Convert dict to LineItem if necessary
        if isinstance(line_item, dict):
            line_item = LineItem.from_dict(line_item)

        # Validate the line item
        try:
            line_item.assert_valid()
        except ValidationError as e:
            raise ValidationError(f"Invalid line item: {str(e)}")

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

        # Add to the line items list
        self.lineitems.append(line_item)

        return line_item

    def get_lineitem(self, line_item_id: str) -> Optional[LineItem]:
        """
        Get a line item by ID.

        Args:
            line_item_id: The ID of the line item to retrieve.

        Returns:
            The LineItem instance if found, None otherwise.
        """
        for line_item in self.lineitems:
            if line_item.id == line_item_id:
                return line_item
        return None

    def remove_lineitem(self, line_item_id: str) -> bool:
        """
        Remove a line item by ID.

        Args:
            line_item_id: The ID of the line item to remove.

        Returns:
            True if the line item was removed, False if it wasn't found.
        """
        for i, line_item in enumerate(self.lineitems):
            if line_item.id == line_item_id:
                self.lineitems.pop(i)
                return True
        return False

    def calculate_total_budget(self) -> Decimal:
        """
        Calculate the total budget from all line items.

        Returns:
            The total budget.
        """
        return sum(item.budget for item in self.lineitems)

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

    @classmethod
    def create_new(cls,
                   created_by: str,
                   campaign_name: str,
                   campaign_objective: str,
                   campaign_start_date: Union[str, date],
                   campaign_end_date: Union[str, date],
                   campaign_budget: Union[str, int, float, Decimal],
                   schema_version: Optional[str] = None,
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
            **kwargs: Additional fields to set on the media plan

        Returns:
            A new MediaPlan instance.

        Raises:
            ValidationError: If the provided parameters fail validation.
        """
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

        # Create budget object
        budget = Budget(
            total=campaign_budget,
            by_channel=kwargs.pop("budget_by_channel", None)
        )

        # Create target audience if provided
        target_audience = None
        ta_data = kwargs.pop("target_audience", None)
        if ta_data:
            target_audience = TargetAudience(**ta_data)

        # Create the campaign
        campaign = Campaign(
            id=campaign_id,
            name=campaign_name,
            objective=campaign_objective,
            start_date=campaign_start_date,
            end_date=campaign_end_date,
            budget=budget,
            target_audience=target_audience
        )

        # Create meta information
        meta = Meta(
            schema_version=schema_version,
            created_by=created_by,
            created_at=datetime.now(),
            comments=kwargs.pop("comments", None)
        )

        # Extract line items if provided
        lineitems_data = kwargs.pop("lineitems", [])
        lineitems = []
        for item_data in lineitems_data:
            try:
                if isinstance(item_data, dict):
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