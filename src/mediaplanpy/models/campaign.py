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
from mediaplanpy.models.target_audience import TargetAudience
from mediaplanpy.models.target_location import TargetLocation


class Campaign(BaseModel):
    """
    Represents a campaign within a media plan.

    A campaign is a collection of media activities with a common objective,
    audience, or theme, following the Media Plan Open Data Standard v3.0.
    """

    # Required fields per v3.0 schema
    id: str = Field(..., description="Unique identifier for the campaign")
    name: str = Field(..., description="Name of the campaign")
    start_date: date = Field(..., description="Start date of the campaign")
    end_date: date = Field(..., description="End date of the campaign")
    budget_total: Decimal = Field(..., description="Total budget amount for the campaign")

    # Optional field (not required per v3.0 schema)
    objective: Optional[str] = Field(None, description="Objective of the campaign")

    # Optional fields from v1.0 schema (maintained for backward compatibility)
    product_name: Optional[str] = Field(None, description="Name of the product being advertised")
    product_description: Optional[str] = Field(None, description="Description of the product being advertised")

    # DEPRECATED v3.0: Audience fields from v1.0/v2.0 (maintained for backward compatibility)
    # Use target_audiences array in v3.0
    audience_name: Optional[str] = Field(None, description="DEPRECATED: Use target_audiences array instead. Name or label for the target audience")
    audience_age_start: Optional[int] = Field(None, description="DEPRECATED: Use target_audiences array instead. Starting age for target audience range")
    audience_age_end: Optional[int] = Field(None, description="DEPRECATED: Use target_audiences array instead. Ending age for target audience range")
    audience_gender: Optional[str] = Field(None, description="DEPRECATED: Use target_audiences array instead. Target gender", enum=["Male", "Female", "Any"])
    audience_interests: Optional[List[str]] = Field(None, description="DEPRECATED: Use target_audiences array instead. List of audience interests")

    # DEPRECATED v3.0: Location fields from v1.0/v2.0 (maintained for backward compatibility)
    # Use target_locations array in v3.0
    location_type: Optional[str] = Field(None, description="DEPRECATED: Use target_locations array instead. Type of location targeting", enum=["Country", "State"])
    locations: Optional[List[str]] = Field(None, description="DEPRECATED: Use target_locations array instead. List of targeted locations")

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

    # NEW v3.0 FIELDS - All optional for backward compatibility

    # Target audiences (replaces deprecated audience_* fields)
    target_audiences: Optional[List[TargetAudience]] = Field(None, description="List of target audiences for this campaign")

    # Target locations (replaces deprecated location_* fields)
    target_locations: Optional[List[TargetLocation]] = Field(None, description="List of target locations for this campaign")

    # KPI fields for tracking key performance indicators
    kpi_name1: Optional[str] = Field(None, description="Name of KPI 1")
    kpi_value1: Optional[Decimal] = Field(None, description="Value for KPI 1")
    kpi_name2: Optional[str] = Field(None, description="Name of KPI 2")
    kpi_value2: Optional[Decimal] = Field(None, description="Value for KPI 2")
    kpi_name3: Optional[str] = Field(None, description="Name of KPI 3")
    kpi_value3: Optional[Decimal] = Field(None, description="Value for KPI 3")
    kpi_name4: Optional[str] = Field(None, description="Name of KPI 4")
    kpi_value4: Optional[Decimal] = Field(None, description="Value for KPI 4")
    kpi_name5: Optional[str] = Field(None, description="Name of KPI 5")
    kpi_value5: Optional[Decimal] = Field(None, description="Value for KPI 5")

    # Custom dimension fields for campaign-specific dimensions
    dim_custom1: Optional[str] = Field(None, description="Custom dimension 1 for campaign")
    dim_custom2: Optional[str] = Field(None, description="Custom dimension 2 for campaign")
    dim_custom3: Optional[str] = Field(None, description="Custom dimension 3 for campaign")
    dim_custom4: Optional[str] = Field(None, description="Custom dimension 4 for campaign")
    dim_custom5: Optional[str] = Field(None, description="Custom dimension 5 for campaign")

    # Custom properties as key-value pairs
    custom_properties: Optional[Dict[str, Any]] = Field(None, description="Additional custom properties as key-value pairs")

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
        Enhanced for v2.0 schema support.

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

        # NEW v2.0 validation: Check ID and name field consistency
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
