"""
Metric Formula model for mediaplanpy schema v3.0.

This module provides the MetricFormula model representing a custom calculation
formula for a metric in a line item.
"""

from typing import Optional
from pydantic import Field, field_validator

from mediaplanpy.models.base import BaseModel
from mediaplanpy.exceptions import ValidationError


class MetricFormula(BaseModel):
    """
    Represents a custom calculation formula for a metric.

    Metric formulas allow line items to define custom calculations for metrics
    instead of using direct values. The formula configuration includes the formula
    type, base metric, and parameters for the calculation.

    Note: In the schema, metric_formulas is stored as a dictionary where keys are
    metric names and values are MetricFormula objects.

    Attributes:
        formula_type: Type of formula function (e.g., 'cost_per_unit', 'conversion_rate', 'constant')
        base_metric: The metric or cost field used as input for calculation
        coefficient: Coefficient value for the formula
        parameter1: First parameter for the formula function
        parameter2: Second parameter for the formula function
        parameter3: Third parameter for the formula function
        comments: Additional notes about the formula configuration

    Example:
        >>> formula = MetricFormula(
        ...     formula_type="cost_per_unit",
        ...     base_metric="cost_total",
        ...     coefficient=1.0
        ... )
    """

    # Required field (based on plan specification)
    formula_type: str = Field(..., description="Type of formula function (e.g., 'cost_per_unit', 'conversion_rate', 'constant', 'power_function')")

    # Optional fields
    base_metric: Optional[str] = Field(None, description="The metric or cost field used as input for the formula calculation (e.g., cost_total, cost_media, metric_impressions, metric_clicks)")
    coefficient: Optional[float] = Field(None, description="Coefficient value for the formula")
    parameter1: Optional[float] = Field(None, description="First parameter for the formula function")
    parameter2: Optional[float] = Field(None, description="Second parameter for the formula function")
    parameter3: Optional[float] = Field(None, description="Third parameter for the formula function")
    comments: Optional[str] = Field(None, description="Additional notes about the formula configuration (e.g., calibration source, assumptions)")

    @field_validator('formula_type')
    @classmethod
    def validate_formula_type(cls, v: str) -> str:
        """
        Validate that formula_type is not empty.

        Common formula types include: 'cost_per_unit', 'conversion_rate',
        'constant', 'power_function'. The specific types should be defined
        in the dictionary schema.

        Raises:
            ValidationError: If formula_type is empty
        """
        if not v or not v.strip():
            raise ValidationError("formula_type cannot be empty")
        return v.strip()
