"""
Line Item model for mediaplanpy.

This module provides the LineItem model class representing a line item
within a media plan, following the Media Plan Open Data Standard v2.0.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, ClassVar, Union

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel
from mediaplanpy.models.metric_formula import MetricFormula


class LineItem(BaseModel):
    """
    Represents a line item within a media plan.

    A line item is the most granular level of a media plan, representing
    a specific placement, ad format, targeting, or other executable unit.
    Following the Media Plan Open Data Standard v3.0.
    """

    # Required fields per v3.0 schema (same as v2.0)
    id: str = Field(..., description="Unique identifier for the line item")
    name: str = Field(..., description="Name of the line item")
    start_date: date = Field(..., description="Start date of the line item")
    end_date: date = Field(..., description="End date of the line item")
    cost_total: Decimal = Field(..., description="Total cost for the line item")

    # Channel-related fields (from v1.0)
    channel: Optional[str] = Field(None, description="Primary channel category")
    channel_custom: Optional[str] = Field(None, description="Custom channel label if standard category doesn't apply")
    vehicle: Optional[str] = Field(None, description="Vehicle or platform where ads will run")
    vehicle_custom: Optional[str] = Field(None, description="Custom vehicle label if standard name doesn't apply")
    partner: Optional[str] = Field(None, description="Partner or publisher")
    partner_custom: Optional[str] = Field(None, description="Custom partner name if standard name doesn't apply")
    media_product: Optional[str] = Field(None, description="Media product offering")
    media_product_custom: Optional[str] = Field(None, description="Custom media product if standard name doesn't apply")

    # Targeting-related fields (from v1.0)
    location_type: Optional[str] = Field(None, description="Type of location targeting")
    location_name: Optional[str] = Field(None, description="Name of targeted location")
    target_audience: Optional[str] = Field(None, description="Description of target audience")

    # Ad format and performance fields (from v1.0)
    adformat: Optional[str] = Field(None, description="Format of the advertisement")
    adformat_custom: Optional[str] = Field(None, description="Custom ad format if standard format doesn't apply")
    kpi: Optional[str] = Field(None, description="Key Performance Indicator")
    kpi_custom: Optional[str] = Field(None, description="Custom KPI if standard KPI doesn't apply")

    # NEW v2.0 FIELDS - All optional for backward compatibility

    # Currency field for costs
    cost_currency: Optional[str] = Field(None, description="Currency code for all cost fields in this line item (e.g., USD, EUR, GBP)")

    # Dayparts and scheduling fields
    dayparts: Optional[str] = Field(None, description="Time periods when the ad should run (e.g., Primetime, Morning, All Day)")
    dayparts_custom: Optional[str] = Field(None, description="Custom daypart specification when standard dayparts don't apply")

    # Inventory fields
    inventory: Optional[str] = Field(None, description="Type of inventory or placement being purchased")
    inventory_custom: Optional[str] = Field(None, description="Custom inventory specification when standard inventory types don't apply")

    # Custom dimension fields (from v1.0)
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

    # Cost breakdown fields (from v1.0)
    cost_media: Optional[Decimal] = Field(None, description="Cost of media")
    cost_buying: Optional[Decimal] = Field(None, description="Cost of buying or trading desk fees")
    cost_platform: Optional[Decimal] = Field(None, description="Cost of platform or tech fees")
    cost_data: Optional[Decimal] = Field(None, description="Cost of data")
    cost_creative: Optional[Decimal] = Field(None, description="Cost of creative")

    # Custom cost fields (from v1.0)
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

    # Standard metric fields (from v1.0)
    metric_impressions: Optional[Decimal] = Field(None, description="Number of impressions")
    metric_clicks: Optional[Decimal] = Field(None, description="Number of clicks")
    metric_views: Optional[Decimal] = Field(None, description="Number of views for video")

    # NEW v2.0 STANDARD METRICS - 17 new standard metrics
    metric_engagements: Optional[Decimal] = Field(None, description="Number of user engagements (likes, shares, comments, etc.)")
    metric_followers: Optional[Decimal] = Field(None, description="Number of new followers gained")
    metric_visits: Optional[Decimal] = Field(None, description="Number of website visits or page visits")
    metric_leads: Optional[Decimal] = Field(None, description="Number of leads generated")
    metric_sales: Optional[Decimal] = Field(None, description="Number of sales or purchases")
    metric_add_to_cart: Optional[Decimal] = Field(None, description="Number of add-to-cart actions")
    metric_app_install: Optional[Decimal] = Field(None, description="Number of app installations")
    metric_application_start: Optional[Decimal] = Field(None, description="Number of application forms started")
    metric_application_complete: Optional[Decimal] = Field(None, description="Number of application forms completed")
    metric_contact_us: Optional[Decimal] = Field(None, description="Number of contact form submissions or contact actions")
    metric_download: Optional[Decimal] = Field(None, description="Number of downloads (files, apps, content)")
    metric_signup: Optional[Decimal] = Field(None, description="Number of signups or registrations")
    metric_max_daily_spend: Optional[Decimal] = Field(None, description="Maximum daily spend limit for the line item")
    metric_max_daily_impressions: Optional[Decimal] = Field(None, description="Maximum daily impressions limit for the line item")
    metric_audience_size: Optional[Decimal] = Field(None, description="Size of the targetable audience for this line item")

    # Custom metric fields (from v1.0)
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

    # NEW v3.0 FIELDS - All optional for backward compatibility

    # Buy information - how the media is purchased
    kpi_value: Optional[Decimal] = Field(None, description="Target value for the KPI")
    buy_type: Optional[str] = Field(None, description="Type of media buy (e.g., Direct, Programmatic, Auction)")
    buy_commitment: Optional[str] = Field(None, description="Commitment level of the buy (e.g., Guaranteed, Non-Guaranteed)")

    # Aggregation fields
    is_aggregate: Optional[bool] = Field(None, description="Whether this line item is an aggregate of other line items")
    aggregation_level: Optional[str] = Field(None, description="Level at which metrics are aggregated (e.g., Campaign, LineItem, Creative)")

    # Multi-currency support
    cost_currency_exchange_rate: Optional[Decimal] = Field(None, description="Exchange rate if costs are in different currency than campaign budget")

    # Budget constraints
    cost_minimum: Optional[Decimal] = Field(None, description="Minimum expected cost for this line item")
    cost_maximum: Optional[Decimal] = Field(None, description="Maximum expected cost for this line item")

    # NEW v3.0 STANDARD METRICS - 10 new metrics
    metric_view_starts: Optional[Decimal] = Field(None, description="Number of video view starts")
    metric_view_completions: Optional[Decimal] = Field(None, description="Number of video view completions")
    metric_reach: Optional[Decimal] = Field(None, description="Total unique users reached")
    metric_units: Optional[Decimal] = Field(None, description="Number of units (generic counter)")
    metric_impression_share: Optional[Decimal] = Field(None, description="Impression share (percentage of available impressions)")
    metric_page_views: Optional[Decimal] = Field(None, description="Number of page views")
    metric_likes: Optional[Decimal] = Field(None, description="Number of likes")
    metric_shares: Optional[Decimal] = Field(None, description="Number of shares")
    metric_comments: Optional[Decimal] = Field(None, description="Number of comments")
    metric_conversions: Optional[Decimal] = Field(None, description="Number of conversions")

    # Metric formulas - for custom calculated metrics
    metric_formulas: Optional[Dict[str, MetricFormula]] = Field(None, description="Dictionary mapping metric names to formula configurations")

    # Custom properties as key-value pairs
    custom_properties: Optional[Dict[str, Any]] = Field(None, description="Additional custom properties as key-value pairs")

    # Constants and reference data for validation
    VALID_CHANNELS: ClassVar[Set[str]] = {
        "social", "search", "display", "video", "audio", "tv", "ooh", "print", "other"
    }

    VALID_KPIS: ClassVar[Set[str]] = {
        "cpm", "cpc", "cpa", "ctr", "cpv", "cpl", "roas", "other"
    }

    # New v2.0 constants for dayparts and inventory
    COMMON_DAYPARTS: ClassVar[Set[str]] = {
        "All Day", "Morning", "Afternoon", "Evening", "Primetime", "Late Night", "Weekdays", "Weekends"
    }

    COMMON_INVENTORY_TYPES: ClassVar[Set[str]] = {
        "Premium", "Remnant", "Private Marketplace", "Open Exchange", "Direct", "Programmatic", "Reserved", "Unreserved"
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
                    "cost_custom6", "cost_custom7", "cost_custom8", "cost_custom9", "cost_custom10",
                    # Add v3.0 cost fields
                    "cost_minimum", "cost_maximum", "cost_currency_exchange_rate")
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
                    # Add all the new v2.0 standard metrics
                    "metric_engagements", "metric_followers", "metric_visits", "metric_leads", "metric_sales",
                    "metric_add_to_cart", "metric_app_install", "metric_application_start", "metric_application_complete",
                    "metric_contact_us", "metric_download", "metric_signup", "metric_max_daily_spend",
                    "metric_max_daily_impressions", "metric_audience_size",
                    # Add all the new v3.0 standard metrics
                    "metric_view_starts", "metric_view_completions", "metric_reach", "metric_units",
                    "metric_impression_share", "metric_page_views", "metric_likes", "metric_shares",
                    "metric_comments", "metric_conversions",
                    # Add v3.0 kpi_value
                    "kpi_value",
                    # Custom metrics
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

    # New v2.0 field validators
    @field_validator("cost_currency")
    @classmethod
    def validate_cost_currency(cls, v: Optional[str]) -> Optional[str]:
        """Validate cost currency code format (basic validation)."""
        if v is not None:
            v = v.strip().upper()
            if len(v) != 3:
                raise ValueError(f"Cost currency should be a 3-letter code (e.g., USD, EUR, GBP), got: {v}")
        return v

    def validate(self) -> List[str]:
        """
        Perform comprehensive validation of the line item.
        Enhanced for v2.0 schema support.

        This method consolidates all validation logic including date validation,
        cost validation, metric validation, and business rule validation.

        Returns:
            List of validation error messages, empty if validation succeeds.
        """
        errors = []

        # Date validation
        if self.start_date > self.end_date:
            errors.append(f"start_date ({self.start_date}) must be before or equal to end_date ({self.end_date})")

        # Cost validation
        # cost_fields = [
        #     ("cost_total", self.cost_total),
        #     ("cost_media", self.cost_media),
        #     ("cost_buying", self.cost_buying),
        #     ("cost_platform", self.cost_platform),
        #     ("cost_data", self.cost_data),
        #     ("cost_creative", self.cost_creative),
        # ]

        # Add custom cost fields
        # for i in range(1, 11):
        #     field_name = f"cost_custom{i}"
        #     field_value = getattr(self, field_name)
        #     cost_fields.append((field_name, field_value))

        # Validate all cost fields are non-negative
        # for field_name, field_value in cost_fields:
        #     if field_value is not None and field_value < 0:
        #         errors.append(f"{field_name} must be non-negative, got: {field_value}")

        # Metric validation - includes all v1.0 and new v2.0 metrics
        # metric_fields = [
        #     ("metric_impressions", self.metric_impressions),
        #     ("metric_clicks", self.metric_clicks),
        #     ("metric_views", self.metric_views),
        #     # New v2.0 standard metrics
        #     ("metric_engagements", self.metric_engagements),
        #     ("metric_followers", self.metric_followers),
        #     ("metric_visits", self.metric_visits),
        #     ("metric_leads", self.metric_leads),
        #     ("metric_sales", self.metric_sales),
        #     ("metric_add_to_cart", self.metric_add_to_cart),
        #     ("metric_app_install", self.metric_app_install),
        #     ("metric_application_start", self.metric_application_start),
        #     ("metric_application_complete", self.metric_application_complete),
        #     ("metric_contact_us", self.metric_contact_us),
        #     ("metric_download", self.metric_download),
        #     ("metric_signup", self.metric_signup),
        #     ("metric_max_daily_spend", self.metric_max_daily_spend),
        #     ("metric_max_daily_impressions", self.metric_max_daily_impressions),
        #     ("metric_audience_size", self.metric_audience_size),
        # ]

        # Add custom metric fields
        # for i in range(1, 11):
        #     field_name = f"metric_custom{i}"
        #     field_value = getattr(self, field_name)
        #     metric_fields.append((field_name, field_value))

        # Validate all metric fields are non-negative
        # for field_name, field_value in metric_fields:
        #     if field_value is not None and field_value < 0:
        #         errors.append(f"{field_name} must be non-negative, got: {field_value}")

        # Custom field validation - ensure custom fields only have values when main field is 'other'
        # custom_field_validations = [
        #     (self.channel, self.channel_custom, "channel_custom", "channel"),
        #     (self.vehicle, self.vehicle_custom, "vehicle_custom", "vehicle"),
        #     (self.partner, self.partner_custom, "partner_custom", "partner"),
        #     (self.media_product, self.media_product_custom, "media_product_custom", "media_product"),
        #     (self.adformat, self.adformat_custom, "adformat_custom", "adformat"),
        #     (self.kpi, self.kpi_custom, "kpi_custom", "kpi"),
        #     # New v2.0 custom field validations
        #     (self.dayparts, self.dayparts_custom, "dayparts_custom", "dayparts"),
        #     (self.inventory, self.inventory_custom, "inventory_custom", "inventory"),
        # ]

        # for main_field, custom_field, custom_field_name, main_field_name in custom_field_validations:
        #     if main_field and main_field.lower() != 'other' and custom_field:
        #         errors.append(f"{custom_field_name} should only be set when {main_field_name} is 'other'")

        # Cost breakdown validation - check if all cost breakdown fields sum to total cost
        # cost_breakdown_fields = [
        #     self.cost_media, self.cost_buying, self.cost_platform,
        #     self.cost_data, self.cost_creative
        # ]

        # Only check if all cost breakdown fields are provided
        # if all(cost is not None for cost in cost_breakdown_fields):
        #     cost_sum = sum(cost_breakdown_fields)
        #     # Allow small rounding differences (0.01)
        #     if abs(cost_sum - self.cost_total) > Decimal('0.01'):
        #         errors.append(f"Sum of cost breakdowns ({cost_sum}) does not match cost_total ({self.cost_total})")

        # NEW v2.0 validation: Application funnel consistency
        # if (self.metric_application_start is not None and
        #         self.metric_application_complete is not None and
        #         self.metric_application_complete > self.metric_application_start):
        #     errors.append("metric_application_complete cannot be greater than metric_application_start")

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
        Convert a v0.0 line item dictionary to a v2.0 LineItem model.

        Args:
            v0_lineitem: Dictionary containing v0.0 line item data.

        Returns:
            A new LineItem instance with v2.0 structure.
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