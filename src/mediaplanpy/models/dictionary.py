"""
Dictionary model for mediaplanpy.

This module provides the Dictionary model class for configuring custom fields
in media plan line items, following the Media Plan Open Data Standard v2.0.
"""

from typing import Dict, Any, List, Optional, ClassVar

from pydantic import Field, field_validator, model_validator

from mediaplanpy.models.base import BaseModel


class CustomFieldConfig(BaseModel):
    """
    Configuration for a single custom field.

    Defines whether a custom field is enabled and what caption to display.
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


class Dictionary(BaseModel):
    """
    Configuration dictionary for custom fields in media plan line items.

    Defines which custom fields are enabled and their display captions.
    Following the Media Plan Open Data Standard v2.0.
    """

    custom_dimensions: Optional[Dict[str, CustomFieldConfig]] = Field(
        None,
        description="Configuration for custom dimension fields (dim_custom1-10)"
    )
    custom_metrics: Optional[Dict[str, CustomFieldConfig]] = Field(
        None,
        description="Configuration for custom metric fields (metric_custom1-10)"
    )
    custom_costs: Optional[Dict[str, CustomFieldConfig]] = Field(
        None,
        description="Configuration for custom cost fields (cost_custom1-10)"
    )

    # Valid custom field names
    VALID_DIMENSION_FIELDS: ClassVar[set] = {
        f"dim_custom{i}" for i in range(1, 11)
    }
    VALID_METRIC_FIELDS: ClassVar[set] = {
        f"metric_custom{i}" for i in range(1, 11)
    }
    VALID_COST_FIELDS: ClassVar[set] = {
        f"cost_custom{i}" for i in range(1, 11)
    }

    @field_validator("custom_dimensions")
    @classmethod
    def validate_custom_dimensions(cls, v: Optional[Dict[str, CustomFieldConfig]]) -> Optional[
        Dict[str, CustomFieldConfig]]:
        """Validate custom dimensions field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_DIMENSION_FIELDS:
                raise ValueError(
                    f"Invalid custom dimension field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_DIMENSION_FIELDS))}")
        return v

    @field_validator("custom_metrics")
    @classmethod
    def validate_custom_metrics(cls, v: Optional[Dict[str, CustomFieldConfig]]) -> Optional[
        Dict[str, CustomFieldConfig]]:
        """Validate custom metrics field names."""
        if v is None:
            return v

        for field_name in v.keys():
            if field_name not in cls.VALID_METRIC_FIELDS:
                raise ValueError(
                    f"Invalid custom metric field name: {field_name}. Must be one of: {', '.join(sorted(cls.VALID_METRIC_FIELDS))}")
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

    def is_field_enabled(self, field_name: str) -> bool:
        """
        Check if a custom field is enabled.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1')

        Returns:
            True if the field is enabled, False otherwise.
        """
        if field_name in self.VALID_DIMENSION_FIELDS:
            return (self.custom_dimensions and
                    field_name in self.custom_dimensions and
                    self.custom_dimensions[field_name].status == "enabled")
        elif field_name in self.VALID_METRIC_FIELDS:
            return (self.custom_metrics and
                    field_name in self.custom_metrics and
                    self.custom_metrics[field_name].status == "enabled")
        elif field_name in self.VALID_COST_FIELDS:
            return (self.custom_costs and
                    field_name in self.custom_costs and
                    self.custom_costs[field_name].status == "enabled")
        return False

    def get_field_caption(self, field_name: str) -> Optional[str]:
        """
        Get the caption for a custom field.

        Args:
            field_name: Name of the custom field (e.g., 'dim_custom1')

        Returns:
            The field caption if enabled, None otherwise.
        """
        if field_name in self.VALID_DIMENSION_FIELDS:
            if (self.custom_dimensions and
                    field_name in self.custom_dimensions and
                    self.custom_dimensions[field_name].status == "enabled"):
                return self.custom_dimensions[field_name].caption
        elif field_name in self.VALID_METRIC_FIELDS:
            if (self.custom_metrics and
                    field_name in self.custom_metrics and
                    self.custom_metrics[field_name].status == "enabled"):
                return self.custom_metrics[field_name].caption
        elif field_name in self.VALID_COST_FIELDS:
            if (self.custom_costs and
                    field_name in self.custom_costs and
                    self.custom_costs[field_name].status == "enabled"):
                return self.custom_costs[field_name].caption
        return None

    def get_enabled_fields(self) -> Dict[str, str]:
        """
        Get all enabled custom fields and their captions.

        Returns:
            Dictionary mapping field names to captions for all enabled fields.
        """
        enabled_fields = {}

        # Add enabled dimension fields
        if self.custom_dimensions:
            for field_name, config in self.custom_dimensions.items():
                if config.status == "enabled":
                    enabled_fields[field_name] = config.caption

        # Add enabled metric fields
        if self.custom_metrics:
            for field_name, config in self.custom_metrics.items():
                if config.status == "enabled":
                    enabled_fields[field_name] = config.caption

        # Add enabled cost fields
        if self.custom_costs:
            for field_name, config in self.custom_costs.items():
                if config.status == "enabled":
                    enabled_fields[field_name] = config.caption

        return enabled_fields