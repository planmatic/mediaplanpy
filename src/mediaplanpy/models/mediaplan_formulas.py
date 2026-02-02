"""
Formula management methods for MediaPlan.
Provides methods to update formula definitions at the MediaPlan level
with automatic propagation to all lineitems.
"""

from decimal import Decimal
from typing import Dict, Optional, List, Literal
from mediaplanpy.models.metric_formula import MetricFormula


class FormulasMixin:
    """Mixin providing formula management methods for MediaPlan."""

    def select_metric_formula(
        self,
        metric_name: str,
        formula_type: Optional[Literal["cost_per_unit", "conversion_rate", "constant", "power_function"]] = None,
        base_metric: Optional[str] = None,
        default_coefficient: Optional[Decimal] = None,
        default_parameter1: Optional[Decimal] = None,
        default_parameter2: Optional[Decimal] = None,
        propagate_to_lineitems: bool = True,
        preserve_values: bool = True
    ) -> Dict[str, int]:
        """
        Select and configure the formula definition for a metric at the MediaPlan level.

        This method:
        1. Selects the formula definition in the dictionary (formula_type, base_metric)
        2. Optionally propagates changes to all lineitems with this metric
        3. When preserve_values=True (default), reverse-calculates new coefficients
           to maintain existing metric values when formula_type or base_metric changes

        Use this method to change WHICH formula a metric uses (e.g., switching from
        cost_per_unit to conversion_rate). To configure formula parameters (coefficient,
        parameter1, parameter2) at the lineitem level, use lineitem.configure_metric_formula().

        Args:
            metric_name: Name of the metric to select formula for (e.g., "metric_impressions")
            formula_type: Formula type to select (cost_per_unit, conversion_rate, constant, power_function)
            base_metric: Base metric for the selected formula
            default_coefficient: Optional default coefficient for new formulas
            default_parameter1: Optional default parameter1 for power_function
            default_parameter2: Optional default parameter2 for power_function
            propagate_to_lineitems: If True, update formulas on all lineitems
            preserve_values: If True, reverse-calculate coefficients to maintain values

        Returns:
            Dict with counts: {
                "dictionary_updated": 1 if dictionary was updated else 0,
                "lineitems_updated": count of lineitems with formulas updated,
                "coefficients_recalculated": count of coefficients reverse-calculated
            }

        Example:
            # Select conversion_rate formula for clicks (instead of cost_per_unit)
            # All lineitem click values will be preserved by recalculating coefficients
            results = mediaplan.select_metric_formula(
                "metric_clicks",
                formula_type="conversion_rate",
                base_metric="metric_impressions"
            )
        """
        results = {
            "dictionary_updated": 0,
            "lineitems_updated": 0,
            "coefficients_recalculated": 0
        }

        # Step 1: Ensure dictionary exists, create if needed
        if self.dictionary is None:
            from mediaplanpy.models.dictionary import Dictionary
            self.dictionary = Dictionary()

        # Step 2: Update dictionary formula definition
        dictionary_updated = False

        # Check if this is a standard metric
        if self.dictionary.standard_metrics is not None and metric_name in self.dictionary.standard_metrics:
            config = self.dictionary.standard_metrics[metric_name]
            if formula_type is not None:
                config.formula_type = formula_type
                dictionary_updated = True
            if base_metric is not None:
                config.base_metric = base_metric
                dictionary_updated = True

        # Check if this is a custom metric (handle None case)
        elif self.dictionary.custom_metrics is not None and metric_name in self.dictionary.custom_metrics:
            config = self.dictionary.custom_metrics[metric_name]
            if formula_type is not None:
                config.formula_type = formula_type
                dictionary_updated = True
            if base_metric is not None:
                config.base_metric = base_metric
                dictionary_updated = True

        else:
            # Metric not in dictionary - add it
            # Determine if it's a standard or custom metric
            if metric_name.startswith("metric_custom"):
                # Add to custom_metrics
                if self.dictionary.custom_metrics is None:
                    self.dictionary.custom_metrics = {}

                # Create new config dict with provided or default values
                self.dictionary.custom_metrics[metric_name] = {
                    "status": "enabled",
                    "caption": metric_name.replace("metric_custom", "Custom Metric "),
                    "formula_type": formula_type or "cost_per_unit",
                    "base_metric": base_metric or "cost_total"
                }
                dictionary_updated = True
            else:
                # Add to standard_metrics
                if self.dictionary.standard_metrics is None:
                    self.dictionary.standard_metrics = {}

                from mediaplanpy.models.dictionary import MetricFormulaConfig
                self.dictionary.standard_metrics[metric_name] = MetricFormulaConfig(
                    formula_type=formula_type or "cost_per_unit",
                    base_metric=base_metric or "cost_total"
                )
                dictionary_updated = True

        if dictionary_updated:
            results["dictionary_updated"] = 1

        # Step 2: Propagate to lineitems if requested
        if propagate_to_lineitems:
            for lineitem in self.lineitems:
                # Check if lineitem has this metric (either value or formula)
                has_value = hasattr(lineitem, metric_name) and getattr(lineitem, metric_name) is not None
                has_formula = (
                    lineitem.metric_formulas is not None and
                    metric_name in lineitem.metric_formulas
                )

                if not has_value and not has_formula:
                    # This lineitem doesn't use this metric - skip
                    continue

                # Track whether formula was created or changed
                created_new_formula = False
                formula_changed = False

                # Get current formula or create new one
                if has_formula:
                    formula = lineitem.metric_formulas[metric_name]

                    # Update formula_type and base_metric if they changed
                    if formula_type is not None and formula.formula_type != formula_type:
                        formula.formula_type = formula_type
                        formula_changed = True
                    if base_metric is not None and formula.base_metric != base_metric:
                        formula.base_metric = base_metric
                        formula_changed = True
                else:
                    # Create new formula with defaults
                    if lineitem.metric_formulas is None:
                        lineitem.metric_formulas = {}
                    formula = MetricFormula(
                        formula_type=formula_type or "cost_per_unit",
                        base_metric=base_metric or "cost_total"
                    )
                    lineitem.metric_formulas[metric_name] = formula
                    created_new_formula = True

                # Count updates
                if created_new_formula or formula_changed:
                    results["lineitems_updated"] += 1

                # CRITICAL: Preserve metric values by reverse-calculating coefficients
                # This applies when: (1) formula was changed, OR (2) new formula was created
                if (created_new_formula or formula_changed) and preserve_values and has_value:
                    current_value = getattr(lineitem, metric_name)
                    if current_value is not None:
                        # Reverse-calculate NEW coefficient using NEW formula definition
                        new_coefficient = lineitem._reverse_calculate_coefficient(
                            metric_name,
                            current_value,
                            self.dictionary
                        )

                        if new_coefficient is not None:
                            formula.coefficient = new_coefficient
                            results["coefficients_recalculated"] += 1

                # Apply default coefficient/parameters if provided and not preserving values
                if not preserve_values or not has_value:
                    if default_coefficient is not None:
                        formula.coefficient = default_coefficient
                    if default_parameter1 is not None:
                        formula.parameter1 = default_parameter1
                    if default_parameter2 is not None:
                        formula.parameter2 = default_parameter2

        return results
