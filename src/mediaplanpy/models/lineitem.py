"""
Line Item model for mediaplanpy.

This module provides the LineItem model class representing a line item
within a media plan, following the Media Plan Open Data Standard.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, ClassVar

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel


class LineItem(BaseModel):
    """
    Represents a line item within a media plan.

    A line item is the most granular level of a media plan, representing
    a specific placement, ad format, targeting, or other executable unit.
    """

    # Required fields per ODS schema
    id: str = Field(..., description="Unique identifier for the line item")
    channel: str = Field(..., description="Channel for the line item (e.g., social, search)")
    platform: str = Field(..., description="Platform for the line item (e.g., Facebook, Google)")
    publisher: str = Field(..., description="Publisher or vendor (e.g., Meta, Google)")
    start_date: date = Field(..., description="Start date of the line item")
    end_date: date = Field(..., description="End date of the line item")
    budget: Decimal = Field(..., description="Budget amount for the line item")
    kpi: str = Field(..., description="Key Performance Indicator (e.g., CPM, CPC)")

    # Optional fields
    creative_ids: Optional[List[str]] = Field(default=None, description="List of creative asset IDs")

    # Constants and reference data
    VALID_CHANNELS: ClassVar[Set[str]] = {
        "social", "search", "display", "video", "audio", "tv", "ooh", "print", "other"
    }

    VALID_KPIS: ClassVar[Set[str]] = {
        "cpm", "cpc", "cpa", "ctr", "cpv", "cpl", "roas", "other"
    }

    @model_validator(mode="after")
    def validate_dates(self) -> "LineItem":
        """
        Validate that start_date is before or equal to end_date.

        Returns:
            The validated LineItem instance.

        Raises:
            ValueError: If start_date is after end_date.
        """
        if self.start_date > self.end_date:
            raise ValueError(f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})")
        return self

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: Decimal) -> Decimal:
        """
        Validate that budget is a positive number.

        Args:
            v: The budget value to validate.

        Returns:
            The validated budget value.

        Raises:
            ValueError: If budget is negative or zero.
        """
        if v <= 0:
            raise ValueError("budget must be a positive number")
        return v

    def validate_model(self) -> List[str]:
        """
        Perform additional validation beyond what Pydantic provides.

        Returns:
            A list of validation error messages, if any.
        """
        errors = super().validate_model()

        # Validate channel
        if self.channel.lower() not in self.VALID_CHANNELS:
            errors.append(f"Unrecognized channel: {self.channel}. "
                          f"Valid channels are: {', '.join(self.VALID_CHANNELS)}")

        # Validate KPI
        if self.kpi.lower() not in self.VALID_KPIS:
            errors.append(f"Unrecognized KPI: {self.kpi}. "
                          f"Valid KPIs are: {', '.join(self.VALID_KPIS)}")

        return errors