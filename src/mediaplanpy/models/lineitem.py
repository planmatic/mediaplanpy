"""
Line Item model for mediaplanpy.

This module provides the LineItem model class representing a line item
within a media plan, following the Media Plan Open Data Standard v2.0.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, ClassVar, Union

from pydantic import Field, PrivateAttr, field_validator, model_validator

from mediaplanpy.models.base import BaseModel
from mediaplanpy.models.metric_formula import MetricFormula


class LineItem(BaseModel):
    """
    Represents a line item within a media plan.

    A line item is the most granular level of a media plan, representing
    a specific placement, ad format, targeting, or other executable unit.
    Following the Media Plan Open Data Standard v3.0.
    """

    # Private parent reference (not serialized, used for smart methods)
    _mediaplan: Optional["MediaPlan"] = PrivateAttr(default=None)

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

    # ========================================================================
    # Formula Recalculation Methods (v3.0 - NEW)
    # ========================================================================

    def get_dictionary(self) -> "Dictionary":
        """
        Get the dictionary from the parent MediaPlan.

        This method provides access to the MediaPlan's dictionary for smart
        metric methods without requiring users to pass it as a parameter.

        Returns:
            Dictionary object from the parent MediaPlan

        Raises:
            ValueError: If this LineItem is not attached to a MediaPlan

        Example:
            >>> mediaplan = MediaPlan(...)
            >>> lineitem = mediaplan.lineitems[0]
            >>> dictionary = lineitem.get_dictionary()  # Auto-retrieves from parent
        """
        from mediaplanpy.models.dictionary import Dictionary

        if self._mediaplan is None:
            raise ValueError(
                "This LineItem is not attached to a MediaPlan. "
                "Smart metric methods require the LineItem to be part of a MediaPlan. "
                "Please add this LineItem to a MediaPlan's lineitems list first."
            )

        return self._mediaplan.dictionary

    def _get_relevant_metrics(self) -> Set[str]:
        """
        Get set of metrics that are relevant for this lineitem.

        A metric is considered relevant if it either:
        - Has a non-None value set on this lineitem, OR
        - Has a formula defined in metric_formulas for this lineitem

        This is used to filter dependency graphs to only process metrics that
        are actually used, improving performance when a mediaplan only uses
        a subset of the 25+ available standard metrics.

        Returns:
            Set of metric names (both standard and custom) that are relevant
            for this lineitem.

        Example:
            >>> lineitem.metric_impressions = Decimal("1000000")
            >>> lineitem.metric_clicks = Decimal("5000")
            >>> lineitem.metric_custom1 = Decimal("100")
            >>> lineitem._get_relevant_metrics()
            {"metric_impressions", "metric_clicks", "metric_custom1"}
        """
        from mediaplanpy.models.dictionary import Dictionary

        relevant = set()

        # Get all valid standard metric field names
        valid_standard_metrics = Dictionary.VALID_STANDARD_METRIC_FIELDS

        # Check each standard metric
        for metric_name in valid_standard_metrics:
            # Check if has value
            has_value = getattr(self, metric_name, None) is not None

            # Check if has formula defined
            has_formula = (
                self.metric_formulas is not None and
                metric_name in self.metric_formulas
            )

            # Include if either condition is true
            if has_value or has_formula:
                relevant.add(metric_name)

        # Check custom metrics (metric_custom1-10) - same logic as standard metrics
        custom_metric_fields = Dictionary.VALID_CUSTOM_METRIC_FIELDS
        for metric_name in custom_metric_fields:
            # Check if has value
            has_value = getattr(self, metric_name, None) is not None

            # Check if has formula defined
            has_formula = (
                self.metric_formulas is not None and
                metric_name in self.metric_formulas
            )

            # Include if either condition is true
            if has_value or has_formula:
                relevant.add(metric_name)

        return relevant

    def _topological_sort(
        self,
        dependency_graph: Dict[str, Set[str]],
        start_metrics: List[str]
    ) -> List[str]:
        """
        Topologically sort metrics to determine calculation order.

        Uses depth-first search to visit metrics in dependency order, ensuring
        that base metrics are calculated before their dependents.

        Args:
            dependency_graph: Dict mapping base_metric -> set of dependent metrics
            start_metrics: List of metrics that changed (starting points for traversal)

        Returns:
            List of metric names in calculation order (dependencies before dependents)

        Raises:
            ValueError: If circular dependency detected

        Example:
            >>> graph = {
            ...     "cost_total": {"metric_impressions", "metric_clicks"},
            ...     "metric_clicks": {"metric_conversions"}
            ... }
            >>> lineitem._topological_sort(graph, ["cost_total"])
            ["metric_impressions", "metric_clicks", "metric_conversions"]
        """
        result = []
        visited = set()
        visiting = set()  # Track nodes currently being visited (for cycle detection)

        def visit(metric: str) -> None:
            """
            Recursively visit a metric and its dependents.

            Args:
                metric: Metric name to visit

            Raises:
                ValueError: If circular dependency detected
            """
            if metric in visited:
                return  # Already processed

            if metric in visiting:
                # We're visiting a node that's already in our current path
                raise ValueError(
                    f"Circular dependency detected involving metric: {metric}. "
                    f"Please check your metric formulas for circular references."
                )

            # Mark as currently being visited
            visiting.add(metric)

            # Visit all dependents of this metric
            dependents = dependency_graph.get(metric, set())
            for dependent in dependents:
                visit(dependent)

            # Done visiting this metric and its dependents
            visiting.remove(metric)
            visited.add(metric)
            result.append(metric)

        # Start DFS from each starting metric
        for metric in start_metrics:
            # Visit each dependent of the starting metric
            dependents = dependency_graph.get(metric, set())
            for dependent in dependents:
                visit(dependent)

        # Reverse the result to get correct topological order
        # (DFS post-order gives us reverse order)
        return list(reversed(result))

    def _calculate_metric_from_formula(
        self,
        metric_name: str,
        dictionary: "Dictionary"
    ) -> Optional[Decimal]:
        """
        Calculate a metric's value from its formula.

        Uses the formula definition from the dictionary and the coefficient/parameters
        from this lineitem's metric_formulas.

        Args:
            metric_name: Name of the metric to calculate
            dictionary: Dictionary object containing formula definitions

        Returns:
            Calculated Decimal value, or None if calculation fails

        Raises:
            ValueError: If formula_type is invalid or circular dependency detected
        """
        from decimal import Decimal, InvalidOperation
        from mediaplanpy.models.dictionary import Dictionary

        # Get formula definition from dictionary
        formula_def = dictionary.get_metric_formula_definition(metric_name)
        if formula_def is None:
            # Metric has no formula definition
            return None

        formula_type = formula_def.get("formula_type", "cost_per_unit")
        base_metric = formula_def.get("base_metric", "cost_total")

        # Get coefficient and parameters from lineitem's metric_formulas
        coefficient = Decimal("0")
        parameter1 = Decimal("1.0")

        if self.metric_formulas and metric_name in self.metric_formulas:
            formula = self.metric_formulas[metric_name]
            if formula.coefficient is not None:
                # Ensure coefficient is a Decimal (convert if needed)
                coefficient = Decimal(str(formula.coefficient))
            if formula.parameter1 is not None:
                # Ensure parameter1 is a Decimal (convert if needed)
                parameter1 = Decimal(str(formula.parameter1))

        # Handle constant formula type (no base metric needed)
        if formula_type == "constant":
            return coefficient

        # Get base metric value
        base_value = getattr(self, base_metric, None)
        if base_value is None:
            # Base metric has no value, cannot calculate
            return None

        # Apply formula based on formula_type
        try:
            if formula_type == "cost_per_unit":
                # metric_value = base / coefficient
                # Example: cost_total = 10000, coefficient = 0.008 → impressions = 1,250,000
                if coefficient == 0:
                    # Division by zero, cannot calculate
                    return None
                return base_value / coefficient

            elif formula_type == "conversion_rate":
                # metric_value = base * coefficient
                # Example: clicks = 5000, coefficient = 0.02 → conversions = 100
                return base_value * coefficient

            elif formula_type == "power_function":
                # metric_value = coefficient * (base ^ parameter1)
                # Example: base = 1000, coeff = 2.0, param1 = 0.5 → metric = 63.24
                try:
                    # Convert to float for power operation, then back to Decimal
                    base_float = float(base_value)
                    param_float = float(parameter1)
                    coeff_float = float(coefficient)

                    result_float = coeff_float * (base_float ** param_float)
                    return Decimal(str(result_float))
                except (ValueError, OverflowError, InvalidOperation):
                    # Power operation failed (negative base with fractional exponent, etc.)
                    return None

            else:
                raise ValueError(
                    f"Invalid formula_type '{formula_type}' for metric '{metric_name}'. "
                    f"Valid types: cost_per_unit, conversion_rate, constant, power_function"
                )

        except (InvalidOperation, ZeroDivisionError, ValueError) as e:
            # Calculation failed, return None
            return None

    def _reverse_calculate_coefficient(
        self,
        metric_name: str,
        metric_value: Decimal,
        dictionary: "Dictionary"
    ) -> Optional[Decimal]:
        """
        Reverse-calculate the coefficient from a metric value and base metric.

        Used when a user sets a metric value and we need to calculate what
        coefficient would produce that value given the base metric.

        Args:
            metric_name: Name of the metric
            metric_value: The desired metric value
            dictionary: Dictionary object containing formula definitions

        Returns:
            Calculated coefficient as Decimal, or None if calculation fails

        Raises:
            ValueError: If formula_type is invalid
        """
        from decimal import Decimal, InvalidOperation
        from mediaplanpy.models.dictionary import Dictionary

        # Get formula definition from dictionary
        formula_def = dictionary.get_metric_formula_definition(metric_name)
        if formula_def is None:
            # Metric has no formula definition
            return None

        formula_type = formula_def.get("formula_type", "cost_per_unit")
        base_metric = formula_def.get("base_metric", "cost_total")

        # Ensure metric_value is a Decimal
        if not isinstance(metric_value, Decimal):
            metric_value = Decimal(str(metric_value))

        # Handle constant formula type (coefficient = metric_value)
        if formula_type == "constant":
            return metric_value

        # Get base metric value
        base_value = getattr(self, base_metric, None)
        if base_value is None:
            # Base metric has no value, cannot calculate
            return None

        # Get parameter1 if needed (for power_function)
        parameter1 = Decimal("1.0")
        if self.metric_formulas and metric_name in self.metric_formulas:
            formula = self.metric_formulas[metric_name]
            if formula.parameter1 is not None:
                parameter1 = Decimal(str(formula.parameter1))

        # Apply reverse formula based on formula_type
        try:
            if formula_type == "cost_per_unit":
                # coefficient = base / metric
                # Example: cost_total = 10000, impressions = 1,250,000 → CPU = 0.008
                if metric_value == 0:
                    # Division by zero, cannot calculate
                    return None
                return base_value / metric_value

            elif formula_type == "conversion_rate":
                # coefficient = metric / base
                # Example: conversions = 100, clicks = 5000 → rate = 0.02
                if base_value == 0:
                    # Division by zero, cannot calculate
                    return None
                return metric_value / base_value

            elif formula_type == "power_function":
                # coefficient = metric / (base ^ parameter1)
                # Example: metric = 2000, base = 1000, param1 = 0.5 → coeff = 63.24
                try:
                    # Convert to float for power operation, then back to Decimal
                    base_float = float(base_value)
                    param_float = float(parameter1)
                    metric_float = float(metric_value)

                    denominator = base_float ** param_float
                    if denominator == 0:
                        return None

                    result_float = metric_float / denominator
                    return Decimal(str(result_float))
                except (ValueError, OverflowError, InvalidOperation, ZeroDivisionError):
                    # Power operation failed
                    return None

            else:
                raise ValueError(
                    f"Invalid formula_type '{formula_type}' for metric '{metric_name}'. "
                    f"Valid types: cost_per_unit, conversion_rate, constant, power_function"
                )

        except (InvalidOperation, ZeroDivisionError, ValueError) as e:
            # Calculation failed, return None
            return None

    def _recalculate_dependent_metrics(
        self,
        start_metrics: List[str],
        dictionary: "Dictionary"
    ) -> Dict[str, Decimal]:
        """
        Recalculate all metrics that depend on the given start_metrics.

        This is the orchestration method that:
        1. Gets relevant metrics from this lineitem
        2. Gets the dependency graph from the dictionary (filtered)
        3. Performs topological sort to determine calculation order
        4. Recalculates each dependent metric in order
        5. Updates metric values on this lineitem

        Args:
            start_metrics: List of metric names that changed (triggers recalculation)
                          These metrics were explicitly set and won't be recalculated.
                          Only their dependents will be recalculated.
            dictionary: Dictionary object containing formula definitions

        Returns:
            Dictionary mapping metric names to their new calculated values

        Raises:
            ValueError: If circular dependency detected
        """
        from decimal import Decimal
        from mediaplanpy.models.dictionary import Dictionary

        # Get relevant metrics for this lineitem (only process metrics that are used)
        relevant_metrics = self._get_relevant_metrics()

        # Get dependency graph from dictionary, filtered by relevant metrics
        dependency_graph = dictionary.get_dependency_graph(relevant_metrics=relevant_metrics)

        # Perform topological sort to determine calculation order
        try:
            sorted_metrics = self._topological_sort(dependency_graph, start_metrics)
        except ValueError as e:
            # Circular dependency detected, re-raise with context
            raise ValueError(f"Cannot recalculate metrics: {e}") from e

        # Recalculate each metric in order and collect results
        recalculated = {}

        for metric_name in sorted_metrics:
            # Calculate new value from formula
            new_value = self._calculate_metric_from_formula(metric_name, dictionary)

            if new_value is not None:
                # Update the metric value on this lineitem
                setattr(self, metric_name, new_value)
                recalculated[metric_name] = new_value

        return recalculated

    def set_metric_value(
        self,
        metric_name: str,
        value: Decimal,
        recalculate_dependents: bool = True,
        update_coefficient: bool = True
    ) -> Dict[str, Decimal]:
        """
        Set a metric value with optional automatic recalculation.

        This is the primary method for setting metric values when you want
        automatic recalculation of dependent metrics. The dictionary is
        automatically retrieved from the parent MediaPlan.

        Args:
            metric_name: Name of the metric to set (e.g., "metric_impressions")
            value: The value to set (must be Decimal)
            recalculate_dependents: If True (default), recalculate metrics that
                                   depend on this metric
            update_coefficient: If True (default), reverse-calculate and update
                               the coefficient for this metric's formula. Set to
                               False only when loading data or for metrics without formulas.

        Returns:
            Dictionary mapping metric names to their new calculated values
            (empty dict if recalculate_dependents=False)

        Raises:
            ValueError: If metric_name is invalid, LineItem not attached to MediaPlan,
                       or circular dependency detected

        Example:
            >>> mediaplan = MediaPlan(...)
            >>> lineitem = mediaplan.lineitems[0]
            >>>
            >>> # Set cost_total and recalculate all dependents
            >>> lineitem.set_metric_value("cost_total", Decimal("15000"))
            {"metric_impressions": Decimal("1875000"), "metric_clicks": Decimal("46875")}
            >>>
            >>> # Set impressions and update its coefficient (default behavior)
            >>> lineitem.set_metric_value("metric_impressions", Decimal("2000000"))
            {"metric_conversions": Decimal("2000")}  # Conversions depends on impressions
        """
        from decimal import Decimal
        from mediaplanpy.models.dictionary import Dictionary

        # Get dictionary from parent MediaPlan
        dictionary = self.get_dictionary()

        # Validate metric name exists as an attribute
        if not hasattr(self, metric_name):
            raise ValueError(
                f"Invalid metric name '{metric_name}'. "
                f"Metric must be a valid LineItem attribute."
            )

        # Ensure value is a Decimal
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        # Set the metric value
        setattr(self, metric_name, value)

        # Optionally update the coefficient (reverse-calculate)
        if update_coefficient:
            new_coefficient = self._reverse_calculate_coefficient(
                metric_name, value, dictionary
            )
            if new_coefficient is not None:
                # Update or create the formula with the new coefficient
                if self.metric_formulas is None:
                    self.metric_formulas = {}
                
                if metric_name in self.metric_formulas:
                    # Update existing formula's coefficient
                    self.metric_formulas[metric_name].coefficient = new_coefficient
                else:
                    # Create new formula with calculated coefficient
                    from mediaplanpy.models.metric_formula import MetricFormula
                    formula_def = dictionary.get_metric_formula_definition(metric_name)
                    if formula_def:
                        self.metric_formulas[metric_name] = MetricFormula(
                            formula_type=formula_def.get("formula_type"),
                            base_metric=formula_def.get("base_metric"),
                            coefficient=new_coefficient
                        )

        # Optionally recalculate dependent metrics
        if recalculate_dependents:
            recalculated = self._recalculate_dependent_metrics([metric_name], dictionary)
            return recalculated
        
        return {}

    def set_metric_formula(
        self,
        metric_name: str,
        coefficient: Optional[Decimal] = None,
        parameter1: Optional[Decimal] = None,
        parameter2: Optional[Decimal] = None,
        comments: Optional[str] = None,
        recalculate_value: bool = True,
        recalculate_dependents: bool = True
    ) -> Dict[str, Decimal]:
        """
        Set or update formula parameters for a metric.

        This method allows updating the coefficient, parameter1, parameter2, and
        comments for a metric's formula. The formula_type and base_metric are
        managed at the dictionary level and cannot be changed here.

        Args:
            metric_name: Name of the metric to update formula for
            coefficient: New coefficient value (None = no change)
            parameter1: New parameter1 value (None = no change)
            parameter2: New parameter2 value (None = no change)
            comments: New comments (None = no change)
            recalculate_value: If True (default), recalculate this metric's value
                              from the new formula
            recalculate_dependents: If True (default), recalculate metrics that
                                   depend on this metric

        Returns:
            Dictionary mapping metric names to their new calculated values

        Raises:
            ValueError: If metric_name is invalid, LineItem not attached to MediaPlan,
                       or circular dependency detected

        Example:
            >>> mediaplan = MediaPlan(...)
            >>> lineitem = mediaplan.lineitems[0]
            >>>
            >>> # Update CPM coefficient for impressions
            >>> lineitem.set_metric_formula("metric_impressions", 
            ...                             coefficient=Decimal("0.010"))
            {"metric_impressions": Decimal("1000000"), "metric_conversions": Decimal("10")}
            >>>
            >>> # Update power function parameter
            >>> lineitem.set_metric_formula("metric_custom1",
            ...                             parameter1=Decimal("0.5"))
        """
        from decimal import Decimal
        from mediaplanpy.models.metric_formula import MetricFormula

        # Get dictionary from parent MediaPlan
        dictionary = self.get_dictionary()

        # Validate metric name exists as an attribute
        if not hasattr(self, metric_name):
            raise ValueError(
                f"Invalid metric name '{metric_name}'. "
                f"Metric must be a valid LineItem attribute."
            )

        # Get formula definition from dictionary (for formula_type and base_metric)
        formula_def = dictionary.get_metric_formula_definition(metric_name)
        if formula_def is None:
            raise ValueError(
                f"Metric '{metric_name}' has no formula definition in the dictionary. "
                f"Cannot set formula parameters."
            )

        # Initialize metric_formulas dict if needed
        if self.metric_formulas is None:
            self.metric_formulas = {}

        # Get existing formula or create new one
        if metric_name in self.metric_formulas:
            # Update existing formula
            formula = self.metric_formulas[metric_name]
            if coefficient is not None:
                formula.coefficient = Decimal(str(coefficient))
            if parameter1 is not None:
                formula.parameter1 = Decimal(str(parameter1))
            if parameter2 is not None:
                formula.parameter2 = Decimal(str(parameter2))
            if comments is not None:
                formula.comments = comments
        else:
            # Create new formula with dictionary's formula_type and base_metric
            self.metric_formulas[metric_name] = MetricFormula(
                formula_type=formula_def.get("formula_type"),
                base_metric=formula_def.get("base_metric"),
                coefficient=Decimal(str(coefficient)) if coefficient is not None else None,
                parameter1=Decimal(str(parameter1)) if parameter1 is not None else None,
                parameter2=Decimal(str(parameter2)) if parameter2 is not None else None,
                comments=comments
            )

        recalculated = {}

        # Optionally recalculate this metric's value from the new formula
        if recalculate_value:
            new_value = self._calculate_metric_from_formula(metric_name, dictionary)
            if new_value is not None:
                setattr(self, metric_name, new_value)
                recalculated[metric_name] = new_value

        # Optionally recalculate dependent metrics
        if recalculate_dependents:
            dependent_recalculated = self._recalculate_dependent_metrics([metric_name], dictionary)
            recalculated.update(dependent_recalculated)

        return recalculated
