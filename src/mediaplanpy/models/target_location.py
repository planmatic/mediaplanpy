"""
Target Location model for mediaplanpy schema v3.0.

This module provides the TargetLocation model representing a geographic
target location for a campaign.
"""

from typing import Optional, List
from pydantic import Field, field_validator

from mediaplanpy.models.base import BaseModel
from mediaplanpy.exceptions import ValidationError


class TargetLocation(BaseModel):
    """
    Represents a geographic target location for a campaign.

    A target location defines the geographic regions where the campaign
    should be delivered, including inclusions and exclusions.

    Attributes:
        name: Name of the target location (required)
        description: Detailed description of the target location
        location_type: Type of geographic targeting (e.g., "Country", "State", "DMA")
        location_list: List of specific locations to target
        exclusion_type: Type of geographic exclusion
        exclusion_list: List of specific locations to exclude
        population_percent: Percentage of target population (0-1 decimal, e.g., 0.452 = 45.2%)
    """

    # Required fields
    name: str = Field(..., description="Name of the target location")

    # Optional fields
    description: Optional[str] = Field(None, description="Detailed description of the target location")
    location_type: Optional[str] = Field(None, description="Type of geographic targeting")
    location_list: Optional[List[str]] = Field(None, description="List of specific locations to target (based on location_type)")
    exclusion_type: Optional[str] = Field(None, description="Type of geographic exclusion")
    exclusion_list: Optional[List[str]] = Field(None, description="List of specific locations to exclude (based on exclusion_type)")
    population_percent: Optional[float] = Field(None, description="Estimated percentage of the total target population (0-1 decimal)")

    @field_validator('location_type', 'exclusion_type')
    @classmethod
    def validate_location_type(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that location types are one of the allowed values."""
        if v is not None:
            allowed_values = ["Country", "State", "DMA", "County", "Postcode", "Radius", "POI"]
            if v not in allowed_values:
                raise ValidationError(
                    f"{info.field_name} must be one of {allowed_values}, got: {v}"
                )
        return v

    @field_validator('population_percent')
    @classmethod
    def validate_population_percent(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate that population_percent is between 0 and 1.

        The schema defines population_percent as a decimal between 0 and 1
        (e.g., 0.452 represents 45.2%).

        Raises:
            ValidationError: If population_percent is outside valid range
        """
        if v is not None:
            if v < 0 or v > 1:
                raise ValidationError(
                    f"population_percent must be between 0 and 1 (decimal format), got: {v}"
                )
        return v
