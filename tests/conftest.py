"""
Shared fixtures for MediaPlanPy test suite.

This module provides pytest fixtures for testing v3.0 functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any

from mediaplanpy.models import (
    MediaPlan, Campaign, LineItem, Meta, Dictionary,
    TargetAudience, TargetLocation, MetricFormula
)


# ============================================================================
# Test Data Directory Fixtures
# ============================================================================

@pytest.fixture
def fixtures_dir():
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after the test."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


# ============================================================================
# v3.0 Model Fixtures
# ============================================================================

@pytest.fixture
def target_audience_adults():
    """Create a sample TargetAudience for adults 25-54."""
    return TargetAudience(
        name="Adults 25-54",
        description="Core adult demographic",
        demo_age_start=25,
        demo_age_end=54,
        demo_gender="Any",
        demo_attributes="HHI $75k+",
        interest_attributes="Technology, Travel, Entertainment"
    )


@pytest.fixture
def target_audience_millennials():
    """Create a sample TargetAudience for millennials."""
    return TargetAudience(
        name="Millennials 25-34",
        description="Young adult demographic",
        demo_age_start=25,
        demo_age_end=34,
        demo_gender="Any",
        interest_attributes="Social Media, Gaming, Streaming"
    )


@pytest.fixture
def target_location_california():
    """Create a sample TargetLocation for California."""
    return TargetLocation(
        name="California",
        description="California state targeting",
        location_type="State",
        location_list=["California"],
        population_percent=0.12
    )


@pytest.fixture
def target_location_northeast():
    """Create a sample TargetLocation for Northeast US."""
    return TargetLocation(
        name="Northeast US",
        description="Northeast region",
        location_type="State",
        location_list=["New York", "New Jersey", "Massachusetts", "Connecticut"],
        population_percent=0.18
    )


@pytest.fixture
def metric_formula_cpm():
    """Create a sample MetricFormula for CPM calculation."""
    return MetricFormula(
        formula_type="cost_per_unit",
        base_metric="cost_total",
        coefficient=1000.0,
        comments="CPM = (cost_total / impressions) * 1000"
    )


@pytest.fixture
def campaign_v3_minimal():
    """Create a minimal v3.0 Campaign with required fields only."""
    return Campaign(
        id="CAM001",
        name="Test Campaign",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        budget_total=Decimal("100000")
    )


@pytest.fixture
def campaign_v3_full(target_audience_adults, target_location_california):
    """Create a complete v3.0 Campaign with all optional fields."""
    return Campaign(
        id="CAM002",
        name="Complete Campaign",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        budget_total=Decimal("500000"),
        budget_currency="USD",
        advertiser_id="ADV001",
        advertiser_name="Acme Corp",
        agency_id="AG001",
        agency_name="Media Agency LLC",
        product_name="Product X",
        product_description="Premium product offering",
        # v3.0 fields
        target_audiences=[target_audience_adults],
        target_locations=[target_location_california],
        kpi_name1="CPM",
        kpi_value1=15.0,
        kpi_name2="CTR",
        kpi_value2=2.5,
        dim_custom1="Vertical: Tech",
        dim_custom2="Region: West"
    )


@pytest.fixture
def lineitem_v3_minimal():
    """Create a minimal v3.0 LineItem with required fields only."""
    return LineItem(
        id="LI001",
        name="Test Line Item",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        cost_total=Decimal("10000"),
        channel="display",
        vehicle="Programmatic",
        partner="DSP Partner"
    )


@pytest.fixture
def lineitem_v3_full(metric_formula_cpm):
    """Create a complete v3.0 LineItem with all optional fields."""
    return LineItem(
        id="LI002",
        name="Complete Line Item",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        cost_total=Decimal("50000"),
        cost_currency="USD",
        channel="display",
        vehicle="Programmatic",
        partner="DSP Partner",
        kpi="cpm",
        # v3.0 buy fields
        kpi_value=Decimal("16.67"),
        buy_type="Programmatic",
        buy_commitment="Non-Guaranteed",
        aggregation_level="LineItem",
        cost_currency_exchange_rate=Decimal("1.0"),
        cost_minimum=Decimal("45000"),
        cost_maximum=Decimal("55000"),
        # Standard metrics
        metric_impressions=Decimal("3000000"),
        metric_clicks=Decimal("75000"),
        metric_views=Decimal("50000"),
        # v3.0 new metrics
        metric_view_starts=Decimal("60000"),
        metric_view_completions=Decimal("50000"),
        metric_reach=Decimal("500000"),
        metric_conversions=Decimal("1500"),
        metric_likes=Decimal("5000"),
        metric_shares=Decimal("1200"),
        metric_comments=Decimal("800"),
        # v3.0 metric formulas
        metric_formulas={"cpm": metric_formula_cpm},
        # v3.0 custom properties
        custom_properties={"campaign_type": "awareness", "creative_rotation": "optimized"}
    )


@pytest.fixture
def meta_v3():
    """Create a v3.0 Meta object."""
    return Meta(
        id="MP001",
        schema_version="v3.0",
        name="Test Media Plan",
        created_by_name="Test User",
        created_at=datetime(2025, 1, 1, 0, 0, 0),
        is_current=True,
        is_archived=False,
        # v3.0 fields
        dim_custom1="Project: Q1 Launch",
        dim_custom2="Market: US"
    )


@pytest.fixture
def dictionary_v3():
    """Create a v3.0 Dictionary with renamed field."""
    return Dictionary(
        lineitem_custom_dimensions={
            "dim_custom1": {"status": "enabled", "caption": "Placement Type"},
            "dim_custom2": {"status": "enabled", "caption": "Creative Format"}
        },
        campaign_custom_dimensions={
            "dim_custom1": {"status": "enabled", "caption": "Business Unit"},
            "dim_custom2": {"status": "enabled", "caption": "Campaign Type"}
        },
        meta_custom_dimensions={
            "dim_custom1": {"status": "enabled", "caption": "Project Code"}
        }
    )


@pytest.fixture
def mediaplan_v3_minimal(meta_v3, campaign_v3_minimal, lineitem_v3_minimal):
    """Create a minimal v3.0 MediaPlan."""
    return MediaPlan(
        meta=meta_v3,
        campaign=campaign_v3_minimal,
        lineitems=[lineitem_v3_minimal]
    )


@pytest.fixture
def mediaplan_v3_full(meta_v3, campaign_v3_full, lineitem_v3_full, dictionary_v3):
    """Create a complete v3.0 MediaPlan with all features."""
    return MediaPlan(
        meta=meta_v3,
        campaign=campaign_v3_full,
        lineitems=[lineitem_v3_full],
        dictionary=dictionary_v3
    )


# ============================================================================
# v2.0 Fixtures (for migration testing)
# ============================================================================

@pytest.fixture
def mediaplan_v2_dict():
    """Return a v2.0 media plan as a dictionary for migration testing."""
    return {
        "meta": {
            "id": "MP002",
            "schema_version": "v2.0",
            "name": "v2.0 Media Plan for Migration",
            "created_by_name": "Test User",
            "created_at": "2025-01-01T00:00:00Z",
            "is_current": True
        },
        "campaign": {
            "id": "CAM003",
            "name": "v2.0 Campaign",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "budget_total": 100000,
            # v2.0 deprecated fields
            "audience_name": "Adults 25-54",
            "audience_age_start": 25,
            "audience_age_end": 54,
            "audience_gender": "Any",
            "location_type": "State",
            "locations": ["California", "New York"]
        },
        "lineitems": [
            {
                "id": "LI003",
                "name": "v2.0 Line Item",
                "start_date": "2025-01-01",
                "end_date": "2025-03-31",
                "cost_total": 10000,
                "channel": "display",
                "vehicle": "Programmatic",
                "partner": "DSP Partner"
            }
        ]
    }


# ============================================================================
# Workspace Fixtures
# ============================================================================

@pytest.fixture
def workspace_config_v3():
    """Return a v3.0 workspace configuration dictionary."""
    return {
        "workspace_id": "test_workspace_v3",
        "schema_version": "3.0",
        "storage": {
            "type": "local",
            "path": "/tmp/mediaplanpy_test"
        },
        "database": {
            "enabled": False
        }
    }
