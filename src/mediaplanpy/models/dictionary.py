"""
Dictionary model for mediaplanpy.

This module provides the Dictionary model class for configuring custom fields
and formula settings across meta, campaign, and line item levels, following
the Media Plan Open Data Standard v3.0.
"""

from typing import Dict, Any, List, Optional, ClassVar

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel


class CustomFieldConfig(BaseModel):
    """
    Configuration for a single custom field (dimensions and costs).

    Defines whether a custom field is enabled and what caption to display.
    Used for dim_custom and cost_custom fields.
    """

    status: str = Field(..., description="Whether this custom field is enabled or disabled")
    caption: Optional[str] = Field(None, description="Display caption for this custom field")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is either 'enabled' or 'disabled'."""
        if v not in ["enabled", "disabled"]:
            raise ValueError("Status must be either 'enabled' or 'disabled'")
        return v

    @field_validator("caption")
    @classmethod
    def validate_caption(cls, v: Optional[str]) -> Optional[str]:
        """Validate caption length if provided."""
        if v is not None and len(v.strip()) > 100:
            raise ValueError("Caption must be 100 characters or less")
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_caption_required_when_enabled(self) -> "CustomFieldConfig":
        """Validate that caption is required when status is enabled."""
        if self.status == "enabled" and not self.caption:
            raise ValueError("Caption is required when status is 'enabled'")
        return self


class MetricFormulaConfig(BaseModel):
    """
    Formula configuration for standard metrics that support formula-based calculations.

    NEW in v3.0: Allows standard metrics to use formulas for calculation.
    """

    formula_type: Optional[str] = Field(None, description="Type of formula function (e.g., cost_per_unit, conversion_rate, constant, power_function)")
    base_metric: Optional[str] = Field(None, description="The metric or cost field used as input for the formula calculation")

    @field_validator("formula_type")
    @classmethod
    def validate_formula_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate formula_type if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("formula_type cannot be empty string")
        return v.strip() if v else v

    @field_validator("base_metric")
    @classmethod
    def validate_base_metric(cls, v: Optional[str]) -> Optional[str]:
        """Validate base_metric if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("base_metric cannot be empty string")
        return v.strip() if v else v


class CustomMetricConfig(BaseModel):
    """
    Configuration for custom metric fields including status, caption, and optional formula support.

    ENHANCED in v3.0: Adds formula_type and base_metric fields to support formula-based calculations.
    Combines CustomFieldConfig fields with MetricFormulaConfig fields.
    """

    status: str = Field(..., description="Whether this custom metric field is enabled or disabled")
    caption: Optional[str] = Field(None, description="Display caption for this custom metric")
    formula_type: Optional[str] = Field(None, description="Type of formula function (e.g., cost_per_unit, conversion_rate, constant, power_function)")
    base_metric: Optional[str] = Field(None, description="The metric or cost field used as input for the formula calculation")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is either 'enabled' or 'disabled'."""
        if v not in ["enabled", "disabled"]:
            raise ValueError("Status must be either 'enabled' or 'disabled'")
        return v

    @field_validator("caption")
    @classmethod
    def validate_caption(cls, v: Optional[str]) -> Optional[str]:
        """Validate caption length if provided."""
        if v is not None and len(v.strip()) > 100:
            raise ValueError("Caption must be 100 characters or less")
        return v.strip() if v else v

    @field_validator("formula_type")
    @classmethod
    def validate_formula_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate formula_type if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("formula_type cannot be empty string")
        return v.strip() if v else v

    @field_validator("base_metric")
    @classmethod
    def validate_base_metric(cls, v: Optional[str]) -> Optional[str]:
        """Validate base_metric if provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("base_metric cannot be empty string")
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_caption_required_when_enabled(self) -> "CustomMetricConfig":
        """Validate that caption is required when status is enabled."""
        if self.status == "enabled" and not self.caption:
            raise ValueError("Caption is required when status is 'enabled'")
        return self


class Dictionary(BaseModel):
    """
    Configuration dictionary for custom fields and formula settings across
    meta, campaign, and line item levels.

    Defines which custom fields are enabled, their display captions, and
    formula configurations for metrics. Following the Media Plan Open Data Standard v3.0.
    """

    # NEW v3.0: Meta-level custom dimensions
    meta_custom_dimensions: Optional[Dict[str, CustomFieldConfig]] = Field(
        None,
        description="Configuration for meta-level custom dimension fields (dim_custom1-5)"
    )

    # NEW v3.0: Campaign-level custom dimensions
    campaign_custom_dimensions: Optional[Dict[str, CustomFieldConfig]] = Field(
        None,
        description="Configuration for campaign-level custom dimension fields (dim_custom1-5)"
    )

    # RENAMED v3.0: custom_dimensions → lineitem_custom_dimensions
    lineitem_custom_dimensions: Optional[Dict[str, CustomFieldConfig]] = Field(
        None,
        description="Configuration for line item-level custom dimension fields (dim_custom1-10)"
    )

    # NEW v3.0: Standard metrics with formula support
    standard_metrics: Optional[Dict[str, MetricFormulaConfig]] = Field(
        None,
        description="Formula configuration for standard metrics that support formula-based calculations"
    )

    # ENHANCED v3.0: Custom metrics now include formula support
    custom_metrics: Optional[Dict[str, CustomMetricConfig]] = Field(
        None,
        description="Configuration for custom metric fields (metric_custom1-10) including formula support"
    )

    # UNCHANGED: Custom costs
    custom_costs: Optional[Dict[str, CustomFieldConfig]] = Field(
        None,
        description="Configuration for custom cost fields (cost_custom1-10)"
    )

    # Valid custom field names
    VALID_META_DIMENSION_FIELDS: ClassVar[set] = {
        f"dim_custom{i}" for i in range(1, 6)  # dim_custom1-5 for meta
    }
    VALID_CAMPAIGN_DIMENSION_FIELDS: ClassVar[set] = {
        f"dim_custom{i}" for i in range(1, 6)  # dim_custom1-5 for campaign
    }
    VALID_LINEITEM_DIMENSION_FIELDS: ClassVar[set] = {
        f"dim_custom{i}" for i in range(1, 11)  # dim_custom1-10 for line items
    }
    VALID_STANDARD_METRIC_FIELDS: ClassVar[set] = {
        # v1.0 and v2.0 metrics
        "metric_impressions", "metric_clicks", "metric_views",
        "metric_engagements", "metric_followers", "metric_visits", "metric_leads", "metric_sales",
        "metric_add_to_cart", "metric_app_install", "metric_application_start", "metric_application_complete",
        "metric_contact_us", "metric_download", "metric_signup",
        # NEW v3.0 metrics
        "metric_view_starts", "metric_view_completions", "metric_reach", "metric_units",
        "metric_impression_share", "metric_page_views", "metric_likes", "metric_shares",
        "metric_comments", "metric_conversions"
    }
    VALID_CUSTOM_METRIC_FIELDS: ClassVar[set] = {
        f"metric_custom{i}" for i in range(1, 11)  # metric_custom1-10
    }
    VALID_COST_FIELDS: ClassVar[set] = {
        f"cost_custom{i}" for i in range(1, 11)  # cost_custom1-10
    }

    @field_validator("meta_custom_dimensions")
    @classmethod
    def validate_meta_custom_dimensions(cls, v: Optional[Dict[str, CustomFieldConfig]]) -> Optional[Dict[str, CustomFieldConfig]]:
        """Validate meta custom dimensions field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_META_DIMENSION_FIELDS:
                raise ValueError(
                    f"Invalid meta custom dimension field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_META_DIMENSION_FIELDS))}")
        return v

    @field_validator("campaign_custom_dimensions")
    @classmethod
    def validate_campaign_custom_dimensions(cls, v: Optional[Dict[str, CustomFieldConfig]]) -> Optional[Dict[str, CustomFieldConfig]]:
        """Validate campaign custom dimensions field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_CAMPAIGN_DIMENSION_FIELDS:
                raise ValueError(
                    f"Invalid campaign custom dimension field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_CAMPAIGN_DIMENSION_FIELDS))}")
        return v

    @field_validator("lineitem_custom_dimensions")
    @classmethod
    def validate_lineitem_custom_dimensions(cls, v: Optional[Dict[str, CustomFieldConfig]]) -> Optional[Dict[str, CustomFieldConfig]]:
        """Validate line item custom dimensions field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_LINEITEM_DIMENSION_FIELDS:
                raise ValueError(
                    f"Invalid line item custom dimension field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_LINEITEM_DIMENSION_FIELDS))}")
        return v

    @field_validator("standard_metrics")
    @classmethod
    def validate_standard_metrics(cls, v: Optional[Dict[str, MetricFormulaConfig]]) -> Optional[Dict[str, MetricFormulaConfig]]:
        """Validate standard metrics field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_STANDARD_METRIC_FIELDS:
                raise ValueError(
                    f"Invalid standard metric field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_STANDARD_METRIC_FIELDS))}")
        return v

    @field_validator("custom_metrics")
    @classmethod
    def validate_custom_metrics(cls, v: Optional[Dict[str, CustomMetricConfig]]) -> Optional[Dict[str, CustomMetricConfig]]:
        """Validate custom metrics field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_CUSTOM_METRIC_FIELDS:
                raise ValueError(
                    f"Invalid custom metric field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_CUSTOM_METRIC_FIELDS))}")
        return v

    @field_validator("custom_costs")
    @classmethod
    def validate_custom_costs(cls, v: Optional[Dict[str, CustomFieldConfig]]) -> Optional[Dict[str, CustomFieldConfig]]:
        """Validate custom costs field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_COST_FIELDS:
                raise ValueError(
                    f"Invalid custom cost field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_COST_FIELDS))}")
        return v

    @model_validator(mode="before")
    @classmethod
    def migrate_custom_dimensions_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-migrate v2.0 'custom_dimensions' field to v3.0 'lineitem_custom_dimensions'.

        This validator runs before field validation and renames the field if it exists.
        """
        if isinstance(values, dict) and "custom_dimensions" in values:
            # Only migrate if lineitem_custom_dimensions is not already set
            if "lineitem_custom_dimensions" not in values:
                values["lineitem_custom_dimensions"] = values["custom_dimensions"]
            # Remove the old field name
            del values["custom_dimensions"]
        return values

    def validate_model(self) -> List[str]:
        """
        Perform additional validation beyond what Pydantic provides.

        Returns:
            A list of validation error messages, if any.
        """
        errors = super().validate_model()

        # Additional business logic validation can be added here
        # For example, checking for conflicting configurations

        return errors

    def is_field_enabled(self, field_name: str, scope: Optional[str] = None) -> bool:
        """
        Check if a custom field is enabled.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1', 'metric_custom1')
            scope: Optional scope to limit search ('meta', 'campaign', 'lineitem').
                   If None, searches all scopes for dimension fields.

        Returns:
            True if the field is enabled, False otherwise.
        """
        # Handle dimension fields with scope
        if field_name in self.VALID_META_DIMENSION_FIELDS or field_name in self.VALID_CAMPAIGN_DIMENSION_FIELDS or field_name in self.VALID_LINEITEM_DIMENSION_FIELDS:
            # Check meta scope
            if (scope is None or scope == "meta") and self.meta_custom_dimensions:
                if field_name in self.meta_custom_dimensions and self.meta_custom_dimensions[field_name].status == "enabled":
                    return True

            # Check campaign scope
            if (scope is None or scope == "campaign") and self.campaign_custom_dimensions:
                if field_name in self.campaign_custom_dimensions and self.campaign_custom_dimensions[field_name].status == "enabled":
                    return True

            # Check lineitem scope
            if (scope is None or scope == "lineitem") and self.lineitem_custom_dimensions:
                if field_name in self.lineitem_custom_dimensions and self.lineitem_custom_dimensions[field_name].status == "enabled":
                    return True

        # Handle custom metric fields
        elif field_name in self.VALID_CUSTOM_METRIC_FIELDS:
            return (self.custom_metrics and
                    field_name in self.custom_metrics and
                    self.custom_metrics[field_name].status == "enabled")

        # Handle cost fields
        elif field_name in self.VALID_COST_FIELDS:
            return (self.custom_costs and
                    field_name in self.custom_costs and
                    self.custom_costs[field_name].status == "enabled")

        return False

    def get_field_caption(self, field_name: str, scope: Optional[str] = None) -> Optional[str]:
        """
        Get the caption for a custom field.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1')
            scope: Optional scope to limit search ('meta', 'campaign', 'lineitem').
                   If None, searches all scopes for dimension fields.

        Returns:
            The field caption if enabled, None otherwise.
        """
        # Handle dimension fields with scope
        if field_name in self.VALID_META_DIMENSION_FIELDS or field_name in self.VALID_CAMPAIGN_DIMENSION_FIELDS or field_name in self.VALID_LINEITEM_DIMENSION_FIELDS:
            # Check meta scope
            if (scope is None or scope == "meta") and self.meta_custom_dimensions:
                if field_name in self.meta_custom_dimensions and self.meta_custom_dimensions[field_name].status == "enabled":
                    return self.meta_custom_dimensions[field_name].caption

            # Check campaign scope
            if (scope is None or scope == "campaign") and self.campaign_custom_dimensions:
                if field_name in self.campaign_custom_dimensions and self.campaign_custom_dimensions[field_name].status == "enabled":
                    return self.campaign_custom_dimensions[field_name].caption

            # Check lineitem scope
            if (scope is None or scope == "lineitem") and self.lineitem_custom_dimensions:
                if field_name in self.lineitem_custom_dimensions and self.lineitem_custom_dimensions[field_name].status == "enabled":
                    return self.lineitem_custom_dimensions[field_name].caption

        # Handle custom metric fields
        elif field_name in self.VALID_CUSTOM_METRIC_FIELDS:
            if (self.custom_metrics and
                    field_name in self.custom_metrics and
                    self.custom_metrics[field_name].status == "enabled"):
                return self.custom_metrics[field_name].caption

        # Handle cost fields
        elif field_name in self.VALID_COST_FIELDS:
            if (self.custom_costs and
                    field_name in self.custom_costs and
                    self.custom_costs[field_name].status == "enabled"):
                return self.custom_costs[field_name].caption

        return None

    def get_enabled_fields(self, scope: Optional[str] = None) -> Dict[str, str]:
        """
        Get all enabled custom fields and their captions.

        Args:
            scope: Optional scope to filter results ('meta', 'campaign', 'lineitem', 'all').
                   If None or 'all', returns all enabled fields from all scopes.

        Returns:
            Dictionary mapping field names to captions for all enabled fields.
        """
        enabled_fields = {}

        # Add enabled meta dimension fields
        if (scope is None or scope == "all" or scope == "meta") and self.meta_custom_dimensions:
            for field_name, config in self.meta_custom_dimensions.items():
                if config.status == "enabled":
                    enabled_fields[f"meta.{field_name}"] = config.caption

        # Add enabled campaign dimension fields
        if (scope is None or scope == "all" or scope == "campaign") and self.campaign_custom_dimensions:
            for field_name, config in self.campaign_custom_dimensions.items():
                if config.status == "enabled":
                    enabled_fields[f"campaign.{field_name}"] = config.caption

        # Add enabled lineitem dimension fields
        if (scope is None or scope == "all" or scope == "lineitem") and self.lineitem_custom_dimensions:
            for field_name, config in self.lineitem_custom_dimensions.items():
                if config.status == "enabled":
                    enabled_fields[f"lineitem.{field_name}"] = config.caption

        # Add enabled custom metric fields
        if (scope is None or scope == "all" or scope == "lineitem") and self.custom_metrics:
            for field_name, config in self.custom_metrics.items():
                if config.status == "enabled":
                    enabled_fields[field_name] = config.caption

        # Add enabled cost fields
        if (scope is None or scope == "all" or scope == "lineitem") and self.custom_costs:
            for field_name, config in self.custom_costs.items():
                if config.status == "enabled":
                    enabled_fields[field_name] = config.caption

        return enabled_fields