"""
Unit tests for v3.0 models.

Tests all model classes including new v3.0 models (TargetAudience, TargetLocation,
MetricFormula) and updated models (Campaign, LineItem, Dictionary) with v3.0 fields.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from mediaplanpy.models import (
    TargetAudience, TargetLocation, MetricFormula,
    Campaign, LineItem, Meta, Dictionary, MediaPlan
)
from mediaplanpy.exceptions import ValidationError


class TestTargetAudience:
    """Test TargetAudience model (new in v3.0)."""

    def test_create_with_required_fields_only(self):
        """Test creating TargetAudience with only required field (name)."""
        audience = TargetAudience(name="Adults 25-54")

        assert audience.name == "Adults 25-54"
        assert audience.description is None
        assert audience.demo_age_start is None
        assert audience.demo_age_end is None

    def test_create_with_all_fields(self, target_audience_adults):
        """Test creating TargetAudience with all fields populated."""
        assert target_audience_adults.name == "Adults 25-54"
        assert target_audience_adults.description == "Core adult demographic"
        assert target_audience_adults.demo_age_start == 25
        assert target_audience_adults.demo_age_end == 54
        assert target_audience_adults.demo_gender == "Any"
        assert "Technology" in target_audience_adults.interest_attributes

    def test_age_range_validation_valid(self):
        """Test that valid age ranges are accepted."""
        audience = TargetAudience(
            name="Young Adults",
            demo_age_start=18,
            demo_age_end=34
        )
        assert audience.demo_age_start == 18
        assert audience.demo_age_end == 34

    def test_age_range_validation_invalid(self):
        """Test that invalid age ranges (start > end) are rejected."""
        with pytest.raises(ValidationError, match="demo_age_start.*must be <=.*demo_age_end"):
            TargetAudience(
                name="Invalid",
                demo_age_start=50,
                demo_age_end=25
            )

    def test_age_range_validation_same_age(self):
        """Test that same start and end age is valid."""
        audience = TargetAudience(
            name="Age 25",
            demo_age_start=25,
            demo_age_end=25
        )
        assert audience.demo_age_start == 25
        assert audience.demo_age_end == 25

    def test_negative_age_rejected(self):
        """Test that negative ages are rejected."""
        with pytest.raises(ValidationError, match="must be non-negative"):
            TargetAudience(
                name="Invalid",
                demo_age_start=-5,
                demo_age_end=25
            )

    def test_gender_validation_valid(self):
        """Test that valid gender values are accepted."""
        for gender in ["Male", "Female", "Any"]:
            audience = TargetAudience(name="Test", demo_gender=gender)
            assert audience.demo_gender == gender

    def test_gender_validation_invalid(self):
        """Test that invalid gender values are rejected."""
        with pytest.raises(ValidationError, match="demo_gender must be one of"):
            TargetAudience(name="Test", demo_gender="Unknown")

    def test_population_size_validation(self):
        """Test that population_size must be non-negative."""
        # Valid
        audience = TargetAudience(name="Test", population_size=1000000)
        assert audience.population_size == 1000000

        # Invalid
        with pytest.raises(ValidationError, match="population_size must be non-negative"):
            TargetAudience(name="Test", population_size=-100)

    def test_to_dict_roundtrip(self, target_audience_adults):
        """Test serialization and deserialization."""
        data = target_audience_adults.to_dict()

        assert data["name"] == "Adults 25-54"
        assert data["demo_age_start"] == 25
        assert data["demo_age_end"] == 54

        # Recreate from dict
        audience_copy = TargetAudience.from_dict(data)
        assert audience_copy.name == target_audience_adults.name
        assert audience_copy.demo_age_start == target_audience_adults.demo_age_start


class TestTargetLocation:
    """Test TargetLocation model (new in v3.0)."""

    def test_create_with_required_fields_only(self):
        """Test creating TargetLocation with only required field (name)."""
        location = TargetLocation(name="California")

        assert location.name == "California"
        assert location.description is None
        assert location.location_type is None
        assert location.population_percent is None

    def test_create_with_all_fields(self, target_location_california):
        """Test creating TargetLocation with all fields populated."""
        assert target_location_california.name == "California"
        assert target_location_california.description == "California state targeting"
        assert target_location_california.location_type == "State"
        assert target_location_california.location_list == ["California"]
        assert target_location_california.population_percent == 0.12

    def test_population_percent_validation_valid(self):
        """Test that valid population_percent values (0-1) are accepted."""
        for value in [0.0, 0.5, 1.0, 0.12, 0.999]:
            location = TargetLocation(name="Test", population_percent=value)
            assert location.population_percent == value

    def test_population_percent_validation_invalid_negative(self):
        """Test that negative population_percent is rejected."""
        with pytest.raises(ValidationError, match="population_percent must be between 0 and 1"):
            TargetLocation(name="Test", population_percent=-0.1)

    def test_population_percent_validation_invalid_too_high(self):
        """Test that population_percent > 1 is rejected."""
        with pytest.raises(ValidationError, match="population_percent must be between 0 and 1"):
            TargetLocation(name="Test", population_percent=1.5)

    def test_location_type_validation_valid(self):
        """Test that valid location_type values are accepted."""
        valid_types = ["Country", "State", "DMA", "County", "Postcode", "Radius", "POI"]
        for loc_type in valid_types:
            location = TargetLocation(name="Test", location_type=loc_type)
            assert location.location_type == loc_type

    def test_location_type_validation_invalid(self):
        """Test that invalid location_type values are rejected."""
        with pytest.raises(ValidationError, match="location_type must be one of"):
            TargetLocation(name="Test", location_type="InvalidType")

    def test_location_list_array(self):
        """Test that location_list accepts array of strings."""
        location = TargetLocation(
            name="Multi-State",
            location_type="State",
            location_list=["California", "New York", "Texas"]
        )
        assert len(location.location_list) == 3
        assert "New York" in location.location_list

    def test_to_dict_roundtrip(self, target_location_california):
        """Test serialization and deserialization."""
        data = target_location_california.to_dict()

        assert data["name"] == "California"
        assert data["location_type"] == "State"
        assert data["population_percent"] == 0.12

        # Recreate from dict
        location_copy = TargetLocation.from_dict(data)
        assert location_copy.name == target_location_california.name
        assert location_copy.population_percent == target_location_california.population_percent


class TestMetricFormula:
    """Test MetricFormula model (new in v3.0)."""

    def test_create_with_required_fields_only(self):
        """Test creating MetricFormula with only required field (formula_type)."""
        formula = MetricFormula(formula_type="cost_per_unit")

        assert formula.formula_type == "cost_per_unit"
        assert formula.base_metric is None
        assert formula.coefficient is None

    def test_create_with_all_fields(self, metric_formula_cpm):
        """Test creating MetricFormula with all fields populated."""
        assert metric_formula_cpm.formula_type == "cost_per_unit"
        assert metric_formula_cpm.base_metric == "cost_total"
        assert metric_formula_cpm.coefficient == 1000.0
        assert "CPM" in metric_formula_cpm.comments

    def test_formula_type_validation_not_empty(self):
        """Test that formula_type cannot be empty."""
        with pytest.raises(ValidationError, match="formula_type cannot be empty"):
            MetricFormula(formula_type="   ")

    def test_formula_type_trimmed(self):
        """Test that formula_type is trimmed of whitespace."""
        formula = MetricFormula(formula_type="  cost_per_unit  ")
        assert formula.formula_type == "cost_per_unit"

    def test_parameters_optional(self):
        """Test that parameter fields are optional."""
        formula = MetricFormula(
            formula_type="power_function",
            parameter1=2.0,
            parameter2=0.5
        )
        assert formula.parameter1 == 2.0
        assert formula.parameter2 == 0.5
        assert formula.parameter3 is None

    def test_to_dict_roundtrip(self, metric_formula_cpm):
        """Test serialization and deserialization."""
        data = metric_formula_cpm.to_dict()

        assert data["formula_type"] == "cost_per_unit"
        assert data["base_metric"] == "cost_total"
        assert data["coefficient"] == 1000.0

        # Recreate from dict
        formula_copy = MetricFormula.from_dict(data)
        assert formula_copy.formula_type == metric_formula_cpm.formula_type
        assert formula_copy.coefficient == metric_formula_cpm.coefficient


class TestCampaignV3:
    """Test Campaign model with v3.0 features."""

    def test_create_with_target_audiences_array(self, target_audience_adults, target_audience_millennials):
        """Test creating Campaign with target_audiences array."""
        campaign = Campaign(
            id="CAM001",
            name="Test Campaign",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            target_audiences=[target_audience_adults, target_audience_millennials]
        )

        assert len(campaign.target_audiences) == 2
        assert campaign.target_audiences[0].name == "Adults 25-54"
        assert campaign.target_audiences[1].name == "Millennials 25-34"

    def test_create_with_target_locations_array(self, target_location_california, target_location_northeast):
        """Test creating Campaign with target_locations array."""
        campaign = Campaign(
            id="CAM002",
            name="Test Campaign",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            target_locations=[target_location_california, target_location_northeast]
        )

        assert len(campaign.target_locations) == 2
        assert campaign.target_locations[0].name == "California"
        assert campaign.target_locations[1].name == "Northeast US"

    def test_kpi_fields(self):
        """Test v3.0 KPI fields."""
        campaign = Campaign(
            id="CAM003",
            name="Test Campaign",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            kpi_name1="CPM",
            kpi_value1=15.0,
            kpi_name2="CTR",
            kpi_value2=2.5,
            kpi_name3="CPA",
            kpi_value3=50.0
        )

        assert campaign.kpi_name1 == "CPM"
        assert campaign.kpi_value1 == 15.0
        assert campaign.kpi_name2 == "CTR"
        assert campaign.kpi_value2 == 2.5

    def test_custom_dimension_fields(self):
        """Test v3.0 custom dimension fields."""
        campaign = Campaign(
            id="CAM004",
            name="Test Campaign",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            dim_custom1="Vertical: Tech",
            dim_custom2="Region: West"
        )

        assert campaign.dim_custom1 == "Vertical: Tech"
        assert campaign.dim_custom2 == "Region: West"

    def test_deprecated_audience_fields_still_work(self):
        """Test that deprecated v2.0 audience fields still work for backward compatibility."""
        campaign = Campaign(
            id="CAM005",
            name="Test Campaign",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            audience_name="Adults 25-54",
            audience_age_start=25,
            audience_age_end=54,
            audience_gender="Any"
        )

        assert campaign.audience_name == "Adults 25-54"
        assert campaign.audience_age_start == 25
        assert campaign.audience_age_end == 54
        assert campaign.audience_gender == "Any"

    def test_deprecated_location_fields_still_work(self):
        """Test that deprecated v2.0 location fields still work for backward compatibility."""
        campaign = Campaign(
            id="CAM006",
            name="Test Campaign",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            budget_total=Decimal("100000"),
            location_type="State",
            locations=["California", "New York"]
        )

        assert campaign.location_type == "State"
        assert len(campaign.locations) == 2
        assert "California" in campaign.locations


class TestLineItemV3:
    """Test LineItem model with v3.0 features."""

    def test_create_with_buy_fields(self):
        """Test creating LineItem with v3.0 buy fields."""
        lineitem = LineItem(
            id="LI001",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            buy_type="Programmatic",
            buy_commitment="Non-Guaranteed"
        )

        assert lineitem.buy_type == "Programmatic"
        assert lineitem.buy_commitment == "Non-Guaranteed"

    def test_new_v3_metrics(self):
        """Test v3.0 new metric fields."""
        lineitem = LineItem(
            id="LI002",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            metric_view_starts=Decimal("60000"),
            metric_view_completions=Decimal("50000"),
            metric_reach=Decimal("500000"),
            metric_conversions=Decimal("1500"),
            metric_likes=Decimal("5000"),
            metric_shares=Decimal("1200"),
            metric_comments=Decimal("800")
        )

        assert lineitem.metric_view_starts == Decimal("60000")
        assert lineitem.metric_view_completions == Decimal("50000")
        assert lineitem.metric_reach == Decimal("500000")
        assert lineitem.metric_conversions == Decimal("1500")

    def test_metric_formulas(self, metric_formula_cpm):
        """Test v3.0 metric_formulas field."""
        lineitem = LineItem(
            id="LI003",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            metric_formulas={"cpm": metric_formula_cpm}
        )

        assert "cpm" in lineitem.metric_formulas
        assert lineitem.metric_formulas["cpm"].formula_type == "cost_per_unit"

    def test_custom_properties(self):
        """Test v3.0 custom_properties field."""
        lineitem = LineItem(
            id="LI004",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            custom_properties={"campaign_type": "awareness", "creative_rotation": "optimized"}
        )

        assert lineitem.custom_properties["campaign_type"] == "awareness"
        assert lineitem.custom_properties["creative_rotation"] == "optimized"

    def test_currency_exchange_rate(self):
        """Test v3.0 currency exchange rate field."""
        lineitem = LineItem(
            id="LI005",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            cost_currency_exchange_rate=Decimal("1.25")
        )

        assert lineitem.cost_currency_exchange_rate == Decimal("1.25")

    def test_cost_minimum_maximum(self):
        """Test v3.0 cost_minimum and cost_maximum fields."""
        lineitem = LineItem(
            id="LI006",
            name="Test Line Item",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 31),
            cost_total=Decimal("10000"),
            cost_minimum=Decimal("9000"),
            cost_maximum=Decimal("11000")
        )

        assert lineitem.cost_minimum == Decimal("9000")
        assert lineitem.cost_maximum == Decimal("11000")


class TestDictionaryV3:
    """Test Dictionary model with v3.0 renamed field."""

    def test_lineitem_custom_dimensions(self):
        """Test v3.0 renamed field: lineitem_custom_dimensions."""
        dictionary = Dictionary(
            lineitem_custom_dimensions={
                "dim_custom1": {"status": "enabled", "caption": "Placement Type"}
            }
        )

        assert "dim_custom1" in dictionary.lineitem_custom_dimensions
        assert dictionary.lineitem_custom_dimensions["dim_custom1"]["status"] == "enabled"

    def test_campaign_custom_dimensions(self):
        """Test v3.0 new field: campaign_custom_dimensions."""
        dictionary = Dictionary(
            campaign_custom_dimensions={
                "dim_custom1": {"status": "enabled", "caption": "Business Unit"}
            }
        )

        assert "dim_custom1" in dictionary.campaign_custom_dimensions
        assert dictionary.campaign_custom_dimensions["dim_custom1"]["caption"] == "Business Unit"

    def test_meta_custom_dimensions(self):
        """Test v3.0 new field: meta_custom_dimensions."""
        dictionary = Dictionary(
            meta_custom_dimensions={
                "dim_custom1": {"status": "enabled", "caption": "Project Code"}
            }
        )

        assert "dim_custom1" in dictionary.meta_custom_dimensions
        assert dictionary.meta_custom_dimensions["dim_custom1"]["caption"] == "Project Code"


class TestMetaV3:
    """Test Meta model with v3.0 fields."""

    def test_create_with_custom_dimensions(self):
        """Test Meta with v3.0 custom dimension fields."""
        meta = Meta(
            id="MP001",
            schema_version="v3.0",
            name="Test Media Plan",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0),
            dim_custom1="Project: Q1 Launch",
            dim_custom2="Market: US"
        )

        assert meta.dim_custom1 == "Project: Q1 Launch"
        assert meta.dim_custom2 == "Market: US"

    def test_custom_properties(self):
        """Test Meta with v3.0 custom_properties field."""
        meta = Meta(
            id="MP002",
            schema_version="v3.0",
            name="Test Media Plan",
            created_by_name="Test User",
            created_at=datetime(2025, 1, 1, 0, 0, 0),
            custom_properties={"business_unit": "digital", "market_segment": "B2C"}
        )

        assert meta.custom_properties["business_unit"] == "digital"
        assert meta.custom_properties["market_segment"] == "B2C"


class TestMediaPlanV3Integration:
    """Integration tests for complete v3.0 MediaPlan."""

    def test_create_minimal_mediaplan(self, mediaplan_v3_minimal):
        """Test creating minimal v3.0 MediaPlan."""
        assert mediaplan_v3_minimal.meta.id == "MP001"
        assert mediaplan_v3_minimal.meta.schema_version == "v3.0"
        assert mediaplan_v3_minimal.campaign.id == "CAM001"
        assert len(mediaplan_v3_minimal.lineitems) == 1

    def test_create_full_mediaplan(self, mediaplan_v3_full):
        """Test creating complete v3.0 MediaPlan with all features."""
        # Check meta
        assert mediaplan_v3_full.meta.schema_version == "v3.0"
        assert mediaplan_v3_full.meta.dim_custom1 == "Project: Q1 Launch"

        # Check campaign with arrays
        assert len(mediaplan_v3_full.campaign.target_audiences) == 1
        assert len(mediaplan_v3_full.campaign.target_locations) == 1
        assert mediaplan_v3_full.campaign.kpi_name1 == "CPM"

        # Check lineitem with v3.0 features
        lineitem = mediaplan_v3_full.lineitems[0]
        assert lineitem.buy_type == "Programmatic"
        assert "cpm" in lineitem.metric_formulas
        assert lineitem.custom_properties is not None

        # Check dictionary
        assert "lineitem_custom_dimensions" in mediaplan_v3_full.dictionary.to_dict()

    def test_to_dict_roundtrip(self, mediaplan_v3_full):
        """Test serialization and deserialization of complete v3.0 MediaPlan."""
        data = mediaplan_v3_full.to_dict()

        # Verify structure
        assert data["meta"]["schema_version"] == "v3.0"
        assert "target_audiences" in data["campaign"]
        assert "target_locations" in data["campaign"]
        assert "metric_formulas" in data["lineitems"][0]

        # Recreate from dict
        mediaplan_copy = MediaPlan.from_dict(data)
        assert mediaplan_copy.meta.id == mediaplan_v3_full.meta.id
        assert len(mediaplan_copy.campaign.target_audiences) == len(mediaplan_v3_full.campaign.target_audiences)
