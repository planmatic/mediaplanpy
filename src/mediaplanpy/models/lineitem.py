"""
Line Item model for mediaplanpy.

This module provides the LineItem model class representing a line item
within a media plan, following the Media Plan Open Data Standard v1.0.0.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, ClassVar, Union

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel


class LineItem(BaseModel):
    """
    Represents a line item within a media plan.

    A line item is the most granular level of a media plan, representing
    a specific placement, ad format, targeting, or other executable unit.
    """

    # Required fields per v1.0.0 schema
    id: str = Field(..., description="Unique identifier for the line item")
    name: str = Field(..., description="Name of the line item")
    start_date: date = Field(..., description="Start date of the line item")
    end_date: date = Field(..., description="End date of the line item")
    cost_total: Decimal = Field(..., description="Total cost for the line item")

    # Channel-related fields
    channel: Optional[str] = Field(None, description="Primary channel category")
    channel_custom: Optional[str] = Field(None, description="Custom channel label if standard category doesn't apply")
    vehicle: Optional[str] = Field(None, description="Vehicle or platform where ads will run")
    vehicle_custom: Optional[str] = Field(None, description="Custom vehicle label if standard name doesn't apply")
    partner: Optional[str] = Field(None, description="Partner or publisher")
    partner_custom: Optional[str] = Field(None, description="Custom partner name if standard name doesn't apply")
    media_product: Optional[str] = Field(None, description="Media product offering")
    media_product_custom: Optional[str] = Field(None, description="Custom media product if standard name doesn't apply")

    # Targeting-related fields
    location_type: Optional[str] = Field(None, description="Type of location targeting")
    location_name: Optional[str] = Field(None, description="Name of targeted location")
    target_audience: Optional[str] = Field(None, description="Description of target audience")

    # Ad format and performance fields
    adformat: Optional[str] = Field(None, description="Format of the advertisement")
    adformat_custom: Optional[str] = Field(None, description="Custom ad format if standard format doesn't apply")
    kpi: Optional[str] = Field(None, description="Key Performance Indicator")
    kpi_custom: Optional[str] = Field(None, description="Custom KPI if standard KPI doesn't apply")

    # Custom dimension fields
    dim_custom1: Optional[str] = Field(None, description="Custom dimension 1")
    dim_custom2: Optional[str] = Field(None, description="Custom dimension 2")
    dim_custom3: Optional[str] = Field(None, description="Custom dimension 3")
    dim_custom4: Optional[str] = Field(None, description="Custom dimension 4")
    dim_custom5: Optional[str] = Field(None, description="Custom dimension 5")
    dim_custom6: Optional[str] = Field(None, description="Custom dimension 6")
    dim_custom7: Optional[str] = Field(None, description="Custom dimension 7")
    dim_custom8: Optional[str] = Field(None, description="Custom dimension 8")
    dim_custom9: Optional[str] = Field(None, description="Custom dimension 9")
    dim_custom10: Optional[str] = Field(None, description="Custom dimension 10")

    # Cost breakdown fields
    cost_media: Optional[Decimal] = Field(None, description="Cost of media")
    cost_buying: Optional[Decimal] = Field(None, description="Cost of buying or trading desk fees")
    cost_platform: Optional[Decimal] = Field(None, description="Cost of platform or tech fees")
    cost_data: Optional[Decimal] = Field(None, description="Cost of data")
    cost_creative: Optional[Decimal] = Field(None, description="Cost of creative")

    # Custom cost fields
    cost_custom1: Optional[Decimal] = Field(None, description="Custom cost field 1")
    cost_custom2: Optional[Decimal] = Field(None, description="Custom cost field 2")
    cost_custom3: Optional[Decimal] = Field(None, description="Custom cost field 3")
    cost_custom4: Optional[Decimal] = Field(None, description="Custom cost field 4")
    cost_custom5: Optional[Decimal] = Field(None, description="Custom cost field 5")
    cost_custom6: Optional[Decimal] = Field(None, description="Custom cost field 6")
    cost_custom7: Optional[Decimal] = Field(None, description="Custom cost field 7")
    cost_custom8: Optional[Decimal] = Field(None, description="Custom cost field 8")
    cost_custom9: Optional[Decimal] = Field(None, description="Custom cost field 9")
    cost_custom10: Optional[Decimal] = Field(None, description="Custom cost field 10")

    # Metric fields
    metric_impressions: Optional[Decimal] = Field(None, description="Number of impressions")
    metric_clicks: Optional[Decimal] = Field(None, description="Number of clicks")
    metric_views: Optional[Decimal] = Field(None, description="Number of views for video")

    # Custom metric fields
    metric_custom1: Optional[Decimal] = Field(None, description="Custom metric field 1")
    metric_custom2: Optional[Decimal] = Field(None, description="Custom metric field 2")
    metric_custom3: Optional[Decimal] = Field(None, description="Custom metric field 3")
    metric_custom4: Optional[Decimal] = Field(None, description="Custom metric field 4")
    metric_custom5: Optional[Decimal] = Field(None, description="Custom metric field 5")
    metric_custom6: Optional[Decimal] = Field(None, description="Custom metric field 6")
    metric_custom7: Optional[Decimal] = Field(None, description="Custom metric field 7")
    metric_custom8: Optional[Decimal] = Field(None, description="Custom metric field 8")
    metric_custom9: Optional[Decimal] = Field(None, description="Custom metric field 9")
    metric_custom10: Optional[Decimal] = Field(None, description="Custom metric field 10")

    # Constants and reference data for validation
    VALID_CHANNELS: ClassVar[Set[str]] = {
        "social", "search", "display", "video", "audio", "tv", "ooh", "print", "other"
    }

    VALID_KPIS: ClassVar[Set[str]] = {
        "cpm", "cpc", "cpa", "ctr", "cpv", "cpl", "roas", "other"
    }

    @model_validator(mode="after")
    def _validate_dates_internal(self) -> "LineItem":
        """
        Internal method to validate that start_date is before or equal to end_date.
        This is called automatically by Pydantic during model validation.

        Returns:
            The validated LineItem instance.

        Raises:
            ValueError: If start_date is after end_date.
        """
        if self.start_date > self.end_date:
            raise ValueError(f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})")
        return self

    @field_validator("cost_total", "cost_media", "cost_buying", "cost_platform", "cost_data", "cost_creative",
                    "cost_custom1", "cost_custom2", "cost_custom3", "cost_custom4", "cost_custom5",
                    "cost_custom6", "cost_custom7", "cost_custom8", "cost_custom9", "cost_custom10")
    @classmethod
    def _validate_cost_internal(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """
        Internal method to validate that cost fields are positive numbers.
        This is called automatically by Pydantic during field validation.

        Args:
            v: The cost value to validate.

        Returns:
            The validated cost value.

        Raises:
            ValueError: If cost is negative.
        """
        if v is not None and v < 0:
            raise ValueError("Cost values must be non-negative")
        return v

    @field_validator("metric_impressions", "metric_clicks", "metric_views",
                    "metric_custom1", "metric_custom2", "metric_custom3", "metric_custom4", "metric_custom5",
                    "metric_custom6", "metric_custom7", "metric_custom8", "metric_custom9", "metric_custom10")
    @classmethod
    def _validate_metric_internal(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """
        Internal method to validate that metric fields are non-negative.
        This is called automatically by Pydantic during field validation.

        Args:
            v: The metric value to validate.

        Returns:
            The validated metric value.

        Raises:
            ValueError: If metric is negative.
        """
        if v is not None and v < 0:
            raise ValueError("Metric values must be non-negative")
        return v

    def validate(self) -> List[str]:
        """
        Perform comprehensive validation of the line item.

        This method consolidates all validation logic including date validation,
        cost validation, metric validation, and business rule validation.

        Returns:
            List of validation error messages, empty if validation succeeds.
        """
        errors = []

        # Date validation (consolidated from old validate_dates method)
        if self.start_date > self.end_date:
            errors.append(f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})")

        # Cost validation
        cost_fields = [
            ("cost_total", self.cost_total),
            ("cost_media", self.cost_media),
            ("cost_buying", self.cost_buying),
            ("cost_platform", self.cost_platform),
            ("cost_data", self.cost_data),
            ("cost_creative", self.cost_creative),
        ]

        # Add custom cost fields
        for i in range(1, 11):
            field_name = f"cost_custom{i}"
            field_value = getattr(self, field_name)
            cost_fields.append((field_name, field_value))

        # Validate all cost fields are non-negative
        for field_name, field_value in cost_fields:
            if field_value is not None and field_value < 0:
                errors.append(f"{field_name} must be non-negative, got: {field_value}")

        # Metric validation
        metric_fields = [
            ("metric_impressions", self.metric_impressions),
            ("metric_clicks", self.metric_clicks),
            ("metric_views", self.metric_views),
        ]

        # Add custom metric fields
        for i in range(1, 11):
            field_name = f"metric_custom{i}"
            field_value = getattr(self, field_name)
            metric_fields.append((field_name, field_value))

        # Validate all metric fields are non-negative
        for field_name, field_value in metric_fields:
            if field_value is not None and field_value < 0:
                errors.append(f"{field_name} must be non-negative, got: {field_value}")

        # Channel validation
        if self.channel and self.channel.lower() not in self.VALID_CHANNELS:
            errors.append(f"Unrecognized channel: {self.channel}. "
                        f"Valid channels are: {', '.join(self.VALID_CHANNELS)}")

        # KPI validation
        if self.kpi and self.kpi.lower() not in self.VALID_KPIS:
            errors.append(f"Unrecognized KPI: {self.kpi}. "
                        f"Valid KPIs are: {', '.join(self.VALID_KPIS)}")

        # Custom field validation - ensure custom fields only have values when main field is 'other'
        custom_field_validations = [
            (self.channel, self.channel_custom, "channel_custom", "channel"),
            (self.vehicle, self.vehicle_custom, "vehicle_custom", "vehicle"),
            (self.partner, self.partner_custom, "partner_custom", "partner"),
            (self.media_product, self.media_product_custom, "media_product_custom", "media_product"),
            (self.adformat, self.adformat_custom, "adformat_custom", "adformat"),
            (self.kpi, self.kpi_custom, "kpi_custom", "kpi"),
        ]

        for main_field, custom_field, custom_field_name, main_field_name in custom_field_validations:
            if main_field and main_field.lower() != 'other' and custom_field:
                errors.append(f"{custom_field_name} should only be set when {main_field_name} is 'other'")

        # Cost breakdown validation - check if all cost breakdown fields sum to total cost
        cost_breakdown_fields = [
            self.cost_media, self.cost_buying, self.cost_platform,
            self.cost_data, self.cost_creative
        ]

        # Only check if all cost breakdown fields are provided
        if all(cost is not None for cost in cost_breakdown_fields):
            cost_sum = sum(cost_breakdown_fields)
            # Allow small rounding differences (0.01)
            if abs(cost_sum - self.cost_total) > Decimal('0.01'):
                errors.append(f"Sum of cost breakdowns ({cost_sum}) does not match cost_total ({self.cost_total})")

        return errors

    # Legacy method support - keeping the old validate_model method as internal API
    def validate_model(self) -> List[str]:
        """
        Legacy method - use validate() instead.

        This method is kept for internal compatibility and calls the new validate() method.

        Returns:
            List of validation error messages, empty if validation succeeds.
        """
        return self.validate()

    @classmethod
    def from_v0_lineitem(cls, v0_lineitem: Dict[str, Any]) -> "LineItem":
        """
        Convert a v0.0.0 line item dictionary to a v1.0.0 LineItem model.

        Args:
            v0_lineitem: Dictionary containing v0.0.0 line item data.

        Returns:
            A new LineItem instance with v1.0.0 structure.
        """
        # Extract the required fields
        lineitem_data = {
            "id": v0_lineitem["id"],
            "name": v0_lineitem.get("id", ""),  # Use id as name if not available
            "start_date": v0_lineitem["start_date"],
            "end_date": v0_lineitem["end_date"],
            "cost_total": v0_lineitem["budget"],  # Rename budget to cost_total
        }

        # Map optional fields
        if "channel" in v0_lineitem:
            lineitem_data["channel"] = v0_lineitem["channel"]

        if "platform" in v0_lineitem:
            lineitem_data["vehicle"] = v0_lineitem["platform"]

        if "publisher" in v0_lineitem:
            lineitem_data["partner"] = v0_lineitem["publisher"]

        if "kpi" in v0_lineitem:
            lineitem_data["kpi"] = v0_lineitem["kpi"]

        # Handle creative_ids as a custom dimension
        if "creative_ids" in v0_lineitem and v0_lineitem["creative_ids"]:
            creative_ids_str = ",".join(v0_lineitem["creative_ids"])
            lineitem_data["dim_custom1"] = f"creative_ids:{creative_ids_str}"

        return cls(**lineitem_data)