"""
Campaign model for mediaplanpy.

This module provides the Campaign model class representing a campaign
within a media plan, following the Media Plan Open Data Standard.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, ClassVar

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel


class TargetAudience(BaseModel):
    """
    Represents a target audience specification for a campaign.
    """
    age_range: Optional[str] = Field(None, description="Target age range (e.g. '18-34')")
    location: Optional[str] = Field(None, description="Target location (e.g. 'United States')")
    interests: Optional[List[str]] = Field(None, description="List of target interests")


class Budget(BaseModel):
    """
    Represents a campaign budget structure.
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


class Campaign(BaseModel):
    """
    Represents a campaign within a media plan.

    A campaign is a collection of media activities with a common objective,
    audience, or theme.
    """

    # Required fields per ODS schema
    id: str = Field(..., description="Unique identifier for the campaign")
    name: str = Field(..., description="Name of the campaign")
    objective: str = Field(..., description="Objective of the campaign")
    start_date: date = Field(..., description="Start date of the campaign")
    end_date: date = Field(..., description="End date of the campaign")

    # Budget is a nested object
    budget: Budget = Field(..., description="Budget information")

    # Optional fields
    target_audience: Optional[TargetAudience] = Field(
        None, description="Target audience information"
    )

    # Constants and reference data
    VALID_OBJECTIVES: ClassVar[Set[str]] = {
        "awareness", "consideration", "conversion", "retention", "loyalty", "other"
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

        return errors