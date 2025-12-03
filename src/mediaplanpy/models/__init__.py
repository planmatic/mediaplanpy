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

# Import storage integration (which patches MediaPlan with storage methods)
import mediaplanpy.models.mediaplan_storage

# Import JSON integration (which patches MediaPlan with JSON methods)
import mediaplanpy.models.mediaplan_json

# Import Excel integration (which patches MediaPlan with Excel methods)
import mediaplanpy.models.mediaplan_excel

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