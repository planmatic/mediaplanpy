"""
Target Audience model for mediaplanpy schema v3.0.

This module provides the TargetAudience model representing a target audience
segment for a campaign.
"""

from typing import Optional
from pydantic import Field, field_validator

from mediaplanpy.models.base import BaseModel
from mediaplanpy.exceptions import ValidationError


class TargetAudience(BaseModel):
    """
    Represents a target audience segment for a campaign.

    A target audience defines demographic, psychographic, and behavioral
    characteristics of the audience the campaign is trying to reach.

    Attributes:
        name: Name of the target audience (required)
        description: Detailed description of the target audience
        demo_age_start: Minimum age of the target audience (inclusive)
        demo_age_end: Maximum age of the target audience (inclusive)
        demo_gender: Target gender ("Male", "Female", or "Any")
        demo_attributes: Additional demographic attributes (e.g., income, education)
        interest_attributes: Interest-based attributes and behaviors
        intent_attributes: Purchase intent and behavioral intent signals
        purchase_attributes: Purchase behavior and transaction history
        content_attributes: Content consumption and engagement attributes
        exclusion_list: List of segments or attributes to exclude
        extension_approach: Approach for audience extension (e.g., lookalike)
        population_size: Estimated size of the target audience population
    """

    # Required fields
    name: str = Field(..., description="Name of the target audience")

    # Optional fields
    description: Optional[str] = Field(None, description="Detailed description of the target audience")
    demo_age_start: Optional[int] = Field(None, description="Minimum age of the target audience (inclusive)")
    demo_age_end: Optional[int] = Field(None, description="Maximum age of the target audience (inclusive)")
    demo_gender: Optional[str] = Field(None, description="Target gender for the audience")
    demo_attributes: Optional[str] = Field(None, description="Additional demographic attributes (e.g., income level, education, occupation)")
    interest_attributes: Optional[str] = Field(None, description="Interest-based attributes and behaviors that define the audience")
    intent_attributes: Optional[str] = Field(None, description="Purchase intent and behavioral intent signals")
    purchase_attributes: Optional[str] = Field(None, description="Purchase behavior and transaction history attributes")
    content_attributes: Optional[str] = Field(None, description="Content consumption and engagement attributes")
    exclusion_list: Optional[str] = Field(None, description="List of segments or attributes to exclude from the audience")
    extension_approach: Optional[str] = Field(None, description="Approach for audience extension (e.g., lookalike, similar audiences)")
    population_size: Optional[int] = Field(None, description="Estimated size of the target audience population")

    @field_validator('demo_gender')
    @classmethod
    def validate_demo_gender(cls, v: Optional[str]) -> Optional[str]:
        """Validate that demo_gender is one of the allowed values."""
        if v is not None:
            allowed_values = ["Male", "Female", "Any"]
            if v not in allowed_values:
                raise ValidationError(
                    f"demo_gender must be one of {allowed_values}, got: {v}"
                )
        return v

    @field_validator('demo_age_start', 'demo_age_end')
    @classmethod
    def validate_age(cls, v: Optional[int], info) -> Optional[int]:
        """Validate that age values are non-negative."""
        if v is not None and v < 0:
            raise ValidationError(
                f"{info.field_name} must be non-negative, got: {v}"
            )
        return v

    @field_validator('population_size')
    @classmethod
    def validate_population_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate that population_size is non-negative."""
        if v is not None and v < 0:
            raise ValidationError(
                f"population_size must be non-negative, got: {v}"
            )
        return v

    def validate_age_range(self) -> None:
        """
        Validate that demo_age_start <= demo_age_end.

        Raises:
            ValidationError: If age range is invalid
        """
        if (
            self.demo_age_start is not None
            and self.demo_age_end is not None
            and self.demo_age_start > self.demo_age_end
        ):
            raise ValidationError(
                f"demo_age_start ({self.demo_age_start}) must be <= demo_age_end ({self.demo_age_end})"
            )

    def __init__(self, **data):
        """Initialize and validate age range."""
        super().__init__(**data)
        self.validate_age_range()
