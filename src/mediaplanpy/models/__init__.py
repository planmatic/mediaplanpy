"""
Models module for mediaplanpy.

This module provides the Pydantic models for media plans, campaigns,
and line items following the Media Plan Open Data Standard v3.0.
"""

from mediaplanpy.models.base import BaseModel
from mediaplanpy.models.lineitem import LineItem
from mediaplanpy.models.campaign import Campaign
from mediaplanpy.models.target_audience import TargetAudience
from mediaplanpy.models.target_location import TargetLocation
from mediaplanpy.models.metric_formula import MetricFormula
from mediaplanpy.models.dictionary import Dictionary, CustomFieldConfig
from mediaplanpy.models.mediaplan import MediaPlan, Meta

# Storage integration now uses StorageMixin inheritance (no monkey patching needed)
# JSON integration now uses JsonMixin inheritance (no monkey patching needed)
# Excel integration now uses ExcelMixin inheritance (no monkey patching needed)

__all__ = [
    'BaseModel',
    'LineItem',
    'Campaign',
    'TargetAudience',
    'TargetLocation',
    'MetricFormula',
    'Dictionary',
    'CustomFieldConfig',
    'MediaPlan',
    'Meta'
]