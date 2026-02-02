"""
Unit tests for v3.0 formula functionality.

Tests the dynamic formula calculation system including:
- Dictionary dependency graph and formula definitions
- LineItem formula calculation and recalculation
- LineItem public API methods (set_metric_value, configure_metric_formula, get_metric_object)
- MediaPlan formula selection and propagation
- MetricValue wrapper class
"""

import pytest
from datetime import date
from decimal import Decimal

from mediaplanpy.models import (
    MediaPlan, Campaign, LineItem, Meta, Dictionary,
    MetricFormula, MetricFormulaConfig
)
from mediaplanpy.models.lineitem import MetricValue
from mediaplanpy.exceptions import ValidationError


class TestDictionaryFormulaMethods:
    """Test Dictionary formula-related methods."""

    def test_get_metric_formula_definition_standard_metric(self):
        """Test getting formula definition for standard metric."""
        dictionary = Dictionary(
            standard_metrics={
                "metric_impressions": MetricFormulaConfig(
                    formula_type="cost_per_unit",
                    base_metric="cost_total"
                )
            }
        )

        definition = dictionary.get_metric_formula_definition("metric_impressions")

        assert definition["formula_type"] == "cost_per_unit"
        assert definition["base_metric"] == "cost_total"

    def test_get_metric_formula_definition_custom_metric(self):
        """Test getting formula definition for custom metric."""
        dictionary = Dictionary(
            custom_metrics={
                "metric_custom1": {
                    "status": "enabled",
                    "caption": "Custom Metric",
                    "formula_type": "conversion_rate",
                    "base_metric": "metric_impressions"
                }
            }
        )

        definition = dictionary.get_metric_formula_definition("metric_custom1")

        assert definition["formula_type"] == "conversion_rate"
        assert definition["base_metric"] == "metric_impressions"

    def test_get_metric_formula_definition_defaults(self):
        """Test default formula definition when metric not in dictionary."""
        dictionary = Dictionary()

        definition = dictionary.get_metric_formula_definition("metric_impressions")

        # Should return defaults
        assert definition["formula_type"] == "cost_per_unit"
        assert definition["base_metric"] == "cost_total"

    def test_get_dependency_graph_basic(self):
        """Test building basic dependency graph."""
        dictionary = Dictionary(
            standard_metrics={
                "metric_impressions": MetricFormulaConfig(
                    formula_type="cost_per_unit",
                    base_metric="cost_total"
                ),
                "metric_clicks": MetricFormulaConfig(
                    formula_type="conversion_rate",
                    base_metric="metric_impressions"
                )
            }
        )

        graph = dictionary.get_dependency_graph()

        assert "cost_total" in graph
        assert "metric_impressions" in graph["cost_total"]
        assert "metric_impressions" in graph
        assert "metric_clicks" in graph["metric_impressions"]

    def test_get_dependency_graph_filtered(self):
        """Test building filtered dependency graph."""
        dictionary = Dictionary(
            standard_metrics={
                "metric_impressions": MetricFormulaConfig(
                    formula_type="cost_per_unit",
                    base_metric="cost_total"
                ),
                "metric_clicks": MetricFormulaConfig(
                    formula_type="conversion_rate",
                    base_metric="metric_impressions"
                ),
                "metric_conversions": MetricFormulaConfig(
                    formula_type="conversion_rate",
                    base_metric="metric_clicks"
                )
            }
        )

        # Only filter for impressions and clicks (not conversions)
        graph = dictionary.get_dependency_graph(
            relevant_metrics={"metric_impressions", "metric_clicks"}  # Set, not list
        )

        assert "cost_total" in graph
        assert "metric_impressions" in graph["cost_total"]
        assert "metric_impressions" in graph
        assert "metric_clicks" in graph["metric_impressions"]
        # metric_conversions should not appear because it wasn't in relevant_metrics
        assert "metric_clicks" not in graph or "metric_conversions" not in graph.get("metric_clicks", [])


class TestLineItemSetMetricValue:
    """Test LineItem.set_metric_value() method."""

    def test_set_base_metric_recalculates_dependents(self):
        """Test setting base metric recalculates dependent metrics."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")  # CPM $8.00
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]

        # Set cost_total to new value
        result = lineitem.set_metric_value("cost_total", Decimal("20000"))

        # Impressions should be recalculated
        expected_impressions = Decimal("20000") / Decimal("0.008")
        assert lineitem.cost_total == Decimal("20000")
        assert lineitem.metric_impressions == expected_impressions
        assert "metric_impressions" in result

    def test_set_metric_value_updates_coefficient(self):
        """Test setting metric value updates coefficient by default."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1250000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]
        old_coefficient = lineitem.metric_formulas["metric_impressions"].coefficient

        # Set impressions to new value (should update coefficient)
        lineitem.set_metric_value("metric_impressions", Decimal("2000000"))

        expected_coefficient = Decimal("10000") / Decimal("2000000")
        assert lineitem.metric_impressions == Decimal("2000000")
        assert Decimal(str(lineitem.metric_formulas["metric_impressions"].coefficient)) == expected_coefficient
        assert lineitem.metric_formulas["metric_impressions"].coefficient != old_coefficient

    def test_set_metric_value_without_coefficient_update(self):
        """Test setting metric value without updating coefficient."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1250000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]
        old_coefficient = lineitem.metric_formulas["metric_impressions"].coefficient

        # Set impressions without updating coefficient
        lineitem.set_metric_value(
            "metric_impressions",
            Decimal("2000000"),
            update_coefficient=False
        )

        assert lineitem.metric_impressions == Decimal("2000000")
        assert lineitem.metric_formulas["metric_impressions"].coefficient == old_coefficient

    def test_set_metric_value_chained_recalculation(self):
        """Test chained recalculation through multiple dependencies."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    ),
                    "metric_clicks": MetricFormulaConfig(
                        formula_type="conversion_rate",
                        base_metric="metric_impressions"
                    ),
                    "metric_conversions": MetricFormulaConfig(
                        formula_type="conversion_rate",
                        base_metric="metric_clicks"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        ),
                        "metric_clicks": MetricFormula(
                            formula_type="conversion_rate",
                            base_metric="metric_impressions",
                            coefficient=Decimal("0.025")  # 2.5% CTR
                        ),
                        "metric_conversions": MetricFormula(
                            formula_type="conversion_rate",
                            base_metric="metric_clicks",
                            coefficient=Decimal("0.10")  # 10% conversion rate
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]

        # Set cost_total - should recalculate impressions, clicks, AND conversions
        result = lineitem.set_metric_value("cost_total", Decimal("20000"))

        expected_impressions = Decimal("20000") / Decimal("0.008")
        expected_clicks = expected_impressions * Decimal("0.025")
        expected_conversions = expected_clicks * Decimal("0.10")

        assert lineitem.cost_total == Decimal("20000")
        assert lineitem.metric_impressions == expected_impressions
        assert lineitem.metric_clicks == expected_clicks
        assert lineitem.metric_conversions == expected_conversions
        assert len(result) == 3  # All 3 metrics recalculated


class TestLineItemConfigureMetricFormula:
    """Test LineItem.configure_metric_formula() method."""

    def test_configure_coefficient_recalculates_value(self):
        """Test configuring coefficient recalculates metric value."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]

        # Configure new coefficient (CPM $10 instead of $8)
        result = lineitem.configure_metric_formula(
            "metric_impressions",
            coefficient=Decimal("0.010")
        )

        expected_impressions = Decimal("10000") / Decimal("0.010")
        assert Decimal(str(lineitem.metric_formulas["metric_impressions"].coefficient)) == Decimal("0.010")
        assert lineitem.metric_impressions == expected_impressions
        assert "metric_impressions" in result

    def test_configure_coefficient_without_recalculation(self):
        """Test configuring coefficient without recalculating value."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1250000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]
        old_value = lineitem.metric_impressions

        # Configure coefficient without recalculation
        result = lineitem.configure_metric_formula(
            "metric_impressions",
            coefficient=Decimal("0.010"),
            recalculate_value=False
        )

        assert Decimal(str(lineitem.metric_formulas["metric_impressions"].coefficient)) == Decimal("0.010")
        assert lineitem.metric_impressions == old_value  # Value unchanged
        assert "metric_impressions" not in result  # Not recalculated

    def test_configure_multiple_parameters(self):
        """Test configuring multiple formula parameters at once."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                custom_metrics={
                    "metric_custom1": {
                        "status": "enabled",
                        "caption": "Custom Metric",
                        "formula_type": "power_function",
                        "base_metric": "metric_impressions"
                    }
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),  # Required field
                    metric_impressions=Decimal("1000000"),
                    metric_formulas={
                        "metric_custom1": MetricFormula(
                            formula_type="power_function",
                            base_metric="metric_impressions",
                            coefficient=Decimal("1.0"),
                            parameter1=Decimal("1.0"),
                            comments="Old comment"
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]

        # Configure multiple parameters
        lineitem.configure_metric_formula(
            "metric_custom1",
            coefficient=Decimal("2.0"),
            parameter1=Decimal("0.5"),  # Square root
            comments="Updated formula"
        )

        formula = lineitem.metric_formulas["metric_custom1"]
        assert formula.coefficient == Decimal("2.0")
        assert formula.parameter1 == Decimal("0.5")
        assert formula.comments == "Updated formula"


class TestLineItemGetMetricObject:
    """Test LineItem.get_metric_object() method and MetricValue wrapper."""

    def test_get_metric_object_with_formula(self):
        """Test getting metric object for metric with formula."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1250000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008"),
                            comments="Test formula"
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]
        metric_obj = lineitem.get_metric_object("metric_impressions")

        assert isinstance(metric_obj, MetricValue)
        assert metric_obj.value == Decimal("1250000")
        assert metric_obj.formula_type == "cost_per_unit"
        assert metric_obj.base_metric == "cost_total"
        assert Decimal(str(metric_obj.coefficient)) == Decimal("0.008")
        assert Decimal(str(metric_obj.cpm)) == Decimal("8.0")  # Coefficient * 1000
        assert metric_obj.comments == "Test formula"

    def test_get_metric_object_without_formula(self):
        """Test getting metric object for metric without formula."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1000000")  # No formula
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]
        metric_obj = lineitem.get_metric_object("metric_impressions")

        assert isinstance(metric_obj, MetricValue)
        assert metric_obj.value == Decimal("1000000")
        assert metric_obj.formula_type == "cost_per_unit"  # From dictionary
        assert metric_obj.base_metric == "cost_total"  # From dictionary
        assert metric_obj.coefficient is None  # No formula on lineitem
        assert metric_obj.cpm is None

    def test_metric_value_is_read_only(self):
        """Test that MetricValue properties are read-only."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1000000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.010")
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]
        metric_obj = lineitem.get_metric_object("metric_impressions")

        # Try to set value (should fail)
        with pytest.raises(AttributeError):
            metric_obj.value = Decimal("999")

        # Try to set coefficient (should fail)
        with pytest.raises(AttributeError):
            metric_obj.coefficient = Decimal("0.01")


class TestMediaPlanSelectMetricFormula:
    """Test MediaPlan.select_metric_formula() method."""

    def test_select_formula_updates_dictionary(self):
        """Test selecting formula updates dictionary definition."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[]
        )

        result = mediaplan.select_metric_formula(
            "metric_impressions",
            formula_type="constant"
        )

        assert mediaplan.dictionary.standard_metrics["metric_impressions"].formula_type == "constant"
        assert result["dictionary_updated"] == 1

    def test_select_formula_preserves_values(self):
        """Test selecting formula preserves metric values by reverse-calculating coefficients."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="Test LineItem",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1250000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        )
                    }
                )
            ]
        )

        lineitem = mediaplan.lineitems[0]
        old_value = lineitem.metric_impressions

        # Change to constant formula (value should be preserved)
        result = mediaplan.select_metric_formula(
            "metric_impressions",
            formula_type="constant"
        )

        assert lineitem.metric_impressions == old_value  # Value preserved
        assert lineitem.metric_formulas["metric_impressions"].formula_type == "constant"
        assert lineitem.metric_formulas["metric_impressions"].coefficient == Decimal("1250000")
        assert result["coefficients_recalculated"] == 1

    def test_select_formula_propagates_to_all_lineitems(self):
        """Test selecting formula propagates to all lineitems."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="LineItem 1",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1250000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        )
                    }
                ),
                LineItem(
                    id="li_002",
                    name="LineItem 2",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("20000"),
                    metric_impressions=Decimal("2000000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.010")
                        )
                    }
                )
            ]
        )

        result = mediaplan.select_metric_formula(
            "metric_impressions",
            formula_type="constant"
        )

        # Both lineitems should have updated formulas
        assert mediaplan.lineitems[0].metric_formulas["metric_impressions"].formula_type == "constant"
        assert mediaplan.lineitems[1].metric_formulas["metric_impressions"].formula_type == "constant"
        # Values should be preserved
        assert mediaplan.lineitems[0].metric_impressions == Decimal("1250000")
        assert mediaplan.lineitems[1].metric_impressions == Decimal("2000000")
        # Coefficients should be reverse-calculated
        assert result["lineitems_updated"] == 2
        assert result["coefficients_recalculated"] == 2

    def test_select_formula_without_propagation(self):
        """Test selecting formula without propagating to lineitems."""
        mediaplan = MediaPlan(
            meta=Meta(
                id="mp_001",
                schema_version="v3.0",
                created_by_name="Test User"
            ),
            campaign=Campaign(
                id="camp_001",
                name="Test Campaign",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                budget_total=Decimal("100000")
            ),
            dictionary=Dictionary(
                standard_metrics={
                    "metric_impressions": MetricFormulaConfig(
                        formula_type="cost_per_unit",
                        base_metric="cost_total"
                    )
                }
            ),
            lineitems=[
                LineItem(
                    id="li_001",
                    name="LineItem 1",
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                    cost_total=Decimal("10000"),
                    metric_impressions=Decimal("1250000"),
                    metric_formulas={
                        "metric_impressions": MetricFormula(
                            formula_type="cost_per_unit",
                            base_metric="cost_total",
                            coefficient=Decimal("0.008")
                        )
                    }
                )
            ]
        )

        result = mediaplan.select_metric_formula(
            "metric_impressions",
            formula_type="constant",
            propagate_to_lineitems=False
        )

        # Dictionary updated
        assert mediaplan.dictionary.standard_metrics["metric_impressions"].formula_type == "constant"
        # But lineitem NOT updated
        assert mediaplan.lineitems[0].metric_formulas["metric_impressions"].formula_type == "cost_per_unit"
        assert result["dictionary_updated"] == 1
        assert result["lineitems_updated"] == 0
