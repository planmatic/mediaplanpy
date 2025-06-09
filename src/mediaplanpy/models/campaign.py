"""
Campaign model for mediaplanpy.

This module provides the Campaign model class representing a campaign
within a media plan, following the Media Plan Open Data Standard v2.0.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, ClassVar, Union

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel


class Campaign(BaseModel):
    """
    Represents a campaign within a media plan.

    A campaign is a collection of media activities with a common objective,
    audience, or theme, following the Media Plan Open Data Standard v2.0.
    """

    # Required fields per v2.0 schema (same as v1.0)
    id: str = Field(..., description="Unique identifier for the campaign")
    name: str = Field(..., description="Name of the campaign")
    objective: str = Field(..., description="Objective of the campaign")
    start_date: date = Field(..., description="Start date of the campaign")
    end_date: date = Field(..., description="End date of the campaign")
    budget_total: Decimal = Field(..., description="Total budget amount for the campaign")

    # Optional fields from v1.0 schema (maintained for backward compatibility)
    product_name: Optional[str] = Field(None, description="Name of the product being advertised")
    product_description: Optional[str] = Field(None, description="Description of the product being advertised")

    # Audience fields from v1.0 (maintained for backward compatibility)
    audience_name: Optional[str] = Field(None, description="Name or label for the target audience")
    audience_age_start: Optional[int] = Field(None, description="Starting age for target audience range")
    audience_age_end: Optional[int] = Field(None, description="Ending age for target audience range")
    audience_gender: Optional[str] = Field(None, description="Target gender", enum=["Male", "Female", "Any"])
    audience_interests: Optional[List[str]] = Field(None, description="List of audience interests")

    # Location fields from v1.0 (maintained for backward compatibility)
    location_type: Optional[str] = Field(None, description="Type of location targeting", enum=["Country", "State"])
    locations: Optional[List[str]] = Field(None, description="List of targeted locations")

    # NEW v2.0 FIELDS - All optional for backward compatibility

    # Budget and currency fields
    budget_currency: Optional[str] = Field(None, description="Currency in which the budget of this campaign is expressed")

    # Agency identification fields
    agency_id: Optional[str] = Field(None, description="Unique identifier for the agency managing the campaign")
    agency_name: Optional[str] = Field(None, description="Name of the agency managing the campaign")

    # Advertiser/client identification fields
    advertiser_id: Optional[str] = Field(None, description="Unique identifier for the advertiser/client")
    advertiser_name: Optional[str] = Field(None, description="Name of the advertiser/client organization")

    # Product identification (in addition to existing product_name)
    product_id: Optional[str] = Field(None, description="Unique identifier for the product being advertised")

    # Campaign type classification
    campaign_type_id: Optional[str] = Field(None, description="Unique identifier for the campaign type classification")
    campaign_type_name: Optional[str] = Field(None, description="Name of the campaign type (e.g., Brand Awareness, Performance, Retargeting)")

    # Workflow status tracking
    workflow_status_id: Optional[str] = Field(None, description="Unique identifier for the current workflow status")
    workflow_status_name: Optional[str] = Field(None, description="Human-readable name of the current workflow status (e.g., Draft, Approved, Live, Paused, Completed)")

    # Constants and reference data
    VALID_OBJECTIVES: ClassVar[Set[str]] = {
        "awareness", "consideration", "conversion", "retention", "loyalty", "other"
    }

    VALID_GENDERS: ClassVar[Set[str]] = {
        "Male", "Female", "Any"
    }

    VALID_LOCATION_TYPES: ClassVar[Set[str]] = {
        "Country", "State"
    }

    # New v2.0 constants for campaign types and workflow statuses
    COMMON_CAMPAIGN_TYPES: ClassVar[Set[str]] = {
        "Brand Awareness", "Performance", "Retargeting", "Launch", "Seasonal", "Always On", "Tactical"
    }

    COMMON_WORKFLOW_STATUSES: ClassVar[Set[str]] = {
        "Draft", "In Review", "Approved", "Live", "Paused", "Completed", "Cancelled"
    }

    @model_validator(mode="after")
    def validate_dates(self) -> "Campaign":
        """
        Validate that start_date is before or equal to end_date.

        Returns:
            The validated Campaign instance.

        Raises:
            ValueError: If start_date is after end_date.
        """
        if self.start_date > self.end_date:
            raise ValueError(f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})")
        return self

    @field_validator("budget_total")
    @classmethod
    def validate_budget_total(cls, v: Decimal) -> Decimal:
        """Validate budget_total is positive."""
        if v <= 0:
            raise ValueError("Budget total must be positive")
        return v

    @field_validator("audience_gender")
    @classmethod
    def validate_audience_gender(cls, v: Optional[str]) -> Optional[str]:
        """Validate audience_gender is a valid value."""
        if v is not None and v not in cls.VALID_GENDERS:
            raise ValueError(f"Invalid audience_gender: {v}. Must be one of: {', '.join(cls.VALID_GENDERS)}")
        return v

    @field_validator("location_type")
    @classmethod
    def validate_location_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate location_type is a valid value."""
        if v is not None and v not in cls.VALID_LOCATION_TYPES:
            raise ValueError(f"Invalid location_type: {v}. Must be one of: {', '.join(cls.VALID_LOCATION_TYPES)}")
        return v

    @field_validator("audience_age_start", "audience_age_end")
    @classmethod
    def validate_audience_age(cls, v: Optional[int]) -> Optional[int]:
        """Validate audience age is a reasonable value."""
        if v is not None and (v < 0 or v > 120):
            raise ValueError(f"Invalid audience age: {v}. Must be between 0 and 120.")
        return v

    # New v2.0 field validators
    @field_validator("budget_currency")
    @classmethod
    def validate_budget_currency(cls, v: Optional[str]) -> Optional[str]:
        """Validate budget currency code format (basic validation)."""
        if v is not None:
            v = v.strip().upper()
            if len(v) != 3:
                raise ValueError(f"Budget currency should be a 3-letter code (e.g., USD, EUR, GBP), got: {v}")
        return v

    def validate_model(self) -> List[str]:
        """
        Perform additional validation beyond what Pydantic provides.

        Returns:
            A list of validation error messages, if any.
        """
        errors = super().validate_model()

        # Validate objective
        lower_objective = self.objective.lower()
        if not any(obj in lower_objective for obj in self.VALID_OBJECTIVES):
            errors.append(
                f"Objective '{self.objective}' does not contain any recognized terms. "
                f"Recognized terms include: {', '.join(self.VALID_OBJECTIVES)}"
            )

        # Validate audience age range
        if self.audience_age_start is not None and self.audience_age_end is not None:
            if self.audience_age_start > self.audience_age_end:
                errors.append(
                    f"audience_age_start ({self.audience_age_start}) must be less than or equal to "
                    f"audience_age_end ({self.audience_age_end})"
                )

        # Validate locations if location_type is provided
        if self.location_type is not None and not self.locations:
            errors.append("locations must be provided when location_type is specified")

        # New v2.0 validation: Check ID and name field consistency
        id_name_pairs = [
            (self.agency_id, self.agency_name, "agency"),
            (self.advertiser_id, self.advertiser_name, "advertiser"),
            (self.campaign_type_id, self.campaign_type_name, "campaign_type"),
            (self.workflow_status_id, self.workflow_status_name, "workflow_status")
        ]

        for id_field, name_field, field_type in id_name_pairs:
            # If both ID and name are provided, that's fine
            # If only one is provided, issue a warning (not an error for flexibility)
            if id_field and not name_field:
                errors.append(f"Warning: {field_type}_id provided without {field_type}_name")
            elif name_field and not id_field:
                errors.append(f"Warning: {field_type}_name provided without {field_type}_id")

        return errors

    @classmethod
    def from_v0_campaign(cls, v0_campaign: Dict[str, Any]) -> "Campaign":
        """
        Convert a v0.0 campaign dictionary to a v2.0 Campaign model.

        Args:
            v0_campaign: Dictionary containing v0.0 campaign data.

        Returns:
            A new Campaign instance with v2.0 structure.
        """
        # Extract basic fields
        campaign_data = {
            "id": v0_campaign["id"],
            "name": v0_campaign["name"],
            "objective": v0_campaign["objective"],
            "start_date": v0_campaign["start_date"],
            "end_date": v0_campaign["end_date"],
        }

        # Extract budget
        if "budget" in v0_campaign and "total" in v0_campaign["budget"]:
            campaign_data["budget_total"] = v0_campaign["budget"]["total"]

        # Extract audience information
        target_audience = v0_campaign.get("target_audience", {})
        if target_audience:
            # Try to parse age range
            age_range = target_audience.get("age_range")
            if age_range and "-" in age_range:
                try:
                    start, end = age_range.split("-")
                    campaign_data["audience_age_start"] = int(start.strip())
                    campaign_data["audience_age_end"] = int(end.strip())
                except (ValueError, TypeError):
                    # If parsing fails, don't set the age fields
                    pass

            # Extract location
            location = target_audience.get("location")
            if location:
                campaign_data["location_type"] = "Country"  # Assume country as default
                campaign_data["locations"] = [location]

            # Extract interests
            interests = target_audience.get("interests")
            if interests:
                campaign_data["audience_interests"] = interests

        return cls(**campaign_data)


class Budget(BaseModel):
    """
    Legacy Budget model for backward compatibility with v0.0 schema.

    In v1.0+, the budget is represented as a simple budget_total field in Campaign.
    This class is kept for backward compatibility with existing code.
    """

    total: Decimal = Field(..., description="Total budget amount")
    by_channel: Optional[Dict[str, Decimal]] = Field(
        default=None, description="Budget breakdown by channel"
    )

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: Decimal) -> Decimal:
        """Validate total budget is positive."""
        if v <= 0:
            raise ValueError("Budget total must be positive")
        return v

    def validate_model(self) -> List[str]:
        """Validate budget consistency."""
        errors = super().validate_model()

        # If by_channel is provided, validate each amount and check the total
        if self.by_channel:
            channel_sum = Decimal(0)

            for channel, amount in self.by_channel.items():
                if amount <= 0:
                    errors.append(f"Budget for channel '{channel}' must be positive")
                channel_sum += amount

            if channel_sum > self.total:
                errors.append(
                    f"Sum of channel budgets ({channel_sum}) exceeds total budget ({self.total})"
                )

        return errors


class TargetAudience(BaseModel):
    """
    Legacy TargetAudience model for backward compatibility with v0.0 schema.

    In v1.0+, audience fields are represented directly in the Campaign model.
    This class is kept for backward compatibility with existing code.
    """
    age_range: Optional[str] = Field(None, description="Target age range (e.g. '18-34')")
    location: Optional[str] = Field(None, description="Target location (e.g. 'United States')")
    interests: Optional[List[str]] = Field(None, description="List of target interests")